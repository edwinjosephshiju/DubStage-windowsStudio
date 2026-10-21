"""
DubStage Demucs v4 ONNX Neural Stem Separation Engine
High-performance local inference with chunk overlap-add crossfading and phase-perfect residual subtraction
"""

import math
import os
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple
import numpy as np

try:
    import onnxruntime as ort
except ImportError:
    ort = None

from ..config import (
    SAMPLE_RATE,
    CHANNELS,
    DEMUCS_SEGMENT_FRAMES,
    OVERLAP_FRAMES,
    HOP_FRAMES,
    PEAK_BUCKET_COUNT,
    MIN_MODEL_SIZE_BYTES,
)
from ..models import (
    ModelPreset,
    ExecutionBackend,
    KaraokeMode,
    DemucsSeparationProgress,
)

@dataclass
class SeparationResult:
    vocals_wav_path: str
    backing_wav_path: str
    vocal_peaks: np.ndarray
    backing_peaks: np.ndarray

def write_wav_header(f, total_pcm_bytes: int, sample_rate: int = SAMPLE_RATE, channels: int = CHANNELS, bits_per_sample: int = 16):
    """Writes standard 44-byte RIFF/WAV header"""
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    data_size = total_pcm_bytes
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE",
        b"fmt ", 16, 1, channels,
        sample_rate, byte_rate, block_align, bits_per_sample,
        b"data", data_size
    )
    f.seek(0)
    f.write(header)

class DemucsOnnxSeparationEngine:
    def __init__(self):
        self._session: Optional[ort.InferenceSession] = None if ort else None
        self._current_model_path: Optional[str] = None
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _create_session(self, model_path: str, backend: ExecutionBackend) -> ort.InferenceSession:
        if ort is None:
            raise RuntimeError("onnxruntime is not installed. Please install onnxruntime to run stem separation.")

        opts = ort.SessionOptions()
        opts.enable_mem_pattern = False
        opts.enable_cpu_mem_arena = False
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        opts.intra_op_num_threads = min(4, os.cpu_count() or 2)
        opts.inter_op_num_threads = 1

        providers = ["CPUExecutionProvider"]
        if backend == ExecutionBackend.DIRECTML_GPU and "DmlExecutionProvider" in ort.get_available_providers():
            providers.insert(0, "DmlExecutionProvider")
        elif backend == ExecutionBackend.CUDA_GPU and "CUDAExecutionProvider" in ort.get_available_providers():
            providers.insert(0, "CUDAExecutionProvider")

        return ort.InferenceSession(model_path, sess_options=opts, providers=providers)

    def separate_stems(
        self,
        model_path: str,
        input_pcm_path: str,
        output_vocals_wav: str,
        output_backing_wav: str,
        preset: ModelPreset = ModelPreset.HTDEMUCS_FT_VOCALS,
        karaoke_mode: KaraokeMode = KaraokeMode.RESIDUAL_SUBTRACTION,
        backend: ExecutionBackend = ExecutionBackend.CPU_LOW_RAM,
        on_progress: Optional[Callable[[DemucsSeparationProgress], None]] = None
    ) -> SeparationResult:
        self._cancelled = False

        if not os.path.exists(model_path) or os.path.getsize(model_path) < MIN_MODEL_SIZE_BYTES:
            raise FileNotFoundError(f"Demucs ONNX model not found or incomplete (<50MB): {model_path}")

        if not os.path.exists(input_pcm_path) or os.path.getsize(input_pcm_path) == 0:
            raise FileNotFoundError(f"Input audio PCM file missing or empty: {input_pcm_path}")

        total_bytes = os.path.getsize(input_pcm_path)
        total_frames = total_bytes // (CHANNELS * 2)
        if total_frames <= 0:
            raise ValueError(f"Invalid audio length: total_frames = {total_frames}")

        # Compute chunk frame offsets
        chunk_offsets = []
        offset = 0
        while offset < total_frames:
            chunk_offsets.append(offset)
            if offset + DEMUCS_SEGMENT_FRAMES >= total_frames:
                break
            offset += HOP_FRAMES

        total_chunks = max(1, len(chunk_offsets))

        # Create session
        try:
            session = self._create_session(model_path, backend)
        except Exception:
            session = self._create_session(model_path, ExecutionBackend.CPU_LOW_RAM)

        input_name = session.get_inputs()[0].name

        Path(output_vocals_wav).parent.mkdir(parents=True, exist_ok=True)
        Path(output_backing_wav).parent.mkdir(parents=True, exist_ok=True)

        # Temporary raw PCM for vocals & backing
        temp_voc_pcm = str(Path(output_vocals_wav).with_suffix(".tmp_voc.pcm"))
        temp_back_pcm = str(Path(output_backing_wav).with_suffix(".tmp_back.pcm"))

        voc_file = open(temp_voc_pcm, "wb")
        back_file = open(temp_back_pcm, "wb")
        src_file = open(input_pcm_path, "rb")

        # Overlap buffers
        trailing_voc_L = np.zeros(OVERLAP_FRAMES, dtype=np.float32)
        trailing_voc_R = np.zeros(OVERLAP_FRAMES, dtype=np.float32)
        trailing_back_L = np.zeros(OVERLAP_FRAMES, dtype=np.float32)
        trailing_back_R = np.zeros(OVERLAP_FRAMES, dtype=np.float32)

        start_time = time.time()
        last_chunk_ms = 0

        vocal_peaks = np.zeros(PEAK_BUCKET_COUNT, dtype=np.float32)
        backing_peaks = np.zeros(PEAK_BUCKET_COUNT, dtype=np.float32)

        try:
            for chunk_idx, frame_offset in enumerate(chunk_offsets):
                if self._cancelled:
                    raise InterruptedError("Separation cancelled by user")

                frames_to_read = min(DEMUCS_SEGMENT_FRAMES, total_frames - frame_offset)
                elapsed_sec = int(time.time() - start_time)
                eta_sec = int((elapsed_sec / chunk_idx) * (total_chunks - chunk_idx)) if chunk_idx > 0 else 0

                if on_progress:
                    on_progress(
                        DemucsSeparationProgress(
                            current_chunk=chunk_idx + 1,
                            total_chunks=total_chunks,
                            percent=int((chunk_idx / total_chunks) * 100),
                            status_text=f"Separating Chunk {chunk_idx + 1} of {total_chunks}",
                            active_backend=backend.label,
                            last_chunk_inference_ms=last_chunk_ms,
                            elapsed_seconds=elapsed_sec,
                            eta_seconds=eta_sec
                        )
                    )

                # 1. Read PCM chunk from disk
                src_file.seek(frame_offset * CHANNELS * 2)
                raw_chunk = src_file.read(frames_to_read * CHANNELS * 2)
                int16_samples = np.frombuffer(raw_chunk, dtype=np.int16)

                # 2. De-interleave to planar stereo [1, 2, DEMUCS_SEGMENT_FRAMES]
                tensor_input = np.zeros((1, 2, DEMUCS_SEGMENT_FRAMES), dtype=np.float32)
                left_ch = int16_samples[0::2].astype(np.float32) / 32768.0
                right_ch = int16_samples[1::2].astype(np.float32) / 32768.0

                tensor_input[0, 0, :frames_to_read] = left_ch
                tensor_input[0, 1, :frames_to_read] = right_ch

                # 3. ONNX Inference
                chunk_t0 = time.time()
                outputs = session.run(None, {input_name: tensor_input})
                last_chunk_ms = int((time.time() - chunk_t0) * 1000)

                out_tensor = outputs[0]  # Shape typically [1, 4, 2, frames] or [1, 2, frames]
                out_shape = out_tensor.shape

                # Inspect stems
                is_4stem = (len(out_shape) == 4 and out_shape[1] == 4) or (len(out_shape) == 3 and out_shape[0] == 4)
                is_2stem = (len(out_shape) == 4 and out_shape[1] == 2) or (len(out_shape) == 3 and out_shape[0] == 2)
                use_neural_sum = is_4stem and (not preset.is_vocals_only_trained) and (karaoke_mode == KaraokeMode.NEURAL_SUM)

                if is_4stem:
                    # In Demucs: 0=Drums, 1=Bass, 2=Other, 3=Vocals
                    raw_voc_L = out_tensor[0, 3, 0, :frames_to_read]
                    raw_voc_R = out_tensor[0, 3, 1, :frames_to_read]
                    if use_neural_sum:
                        raw_back_L = out_tensor[0, 0, 0, :frames_to_read] + out_tensor[0, 1, 0, :frames_to_read] + out_tensor[0, 2, 0, :frames_to_read]
                        raw_back_R = out_tensor[0, 0, 1, :frames_to_read] + out_tensor[0, 1, 1, :frames_to_read] + out_tensor[0, 2, 1, :frames_to_read]
                    else:
                        raw_back_L = left_ch - raw_voc_L
                        raw_back_R = right_ch - raw_voc_R
                elif is_2stem:
                    raw_voc_L = out_tensor[0, 1, 0, :frames_to_read]
                    raw_voc_R = out_tensor[0, 1, 1, :frames_to_read]
                    raw_back_L = out_tensor[0, 0, 0, :frames_to_read]
                    raw_back_R = out_tensor[0, 0, 1, :frames_to_read]
                else:
                    # 1-stem Vocal Specialist
                    raw_voc_L = out_tensor[0, 0, :frames_to_read]
                    raw_voc_R = out_tensor[0, 1, :frames_to_read]
                    raw_back_L = left_ch - raw_voc_L
                    raw_back_R = right_ch - raw_voc_R

                is_last_chunk = (chunk_idx == total_chunks - 1)
                finalized_frames = frames_to_read if is_last_chunk else min(HOP_FRAMES, frames_to_read)

                # Overlap-add crossfade
                final_voc_L = raw_voc_L[:finalized_frames].copy()
                final_voc_R = raw_voc_R[:finalized_frames].copy()
                final_back_L = raw_back_L[:finalized_frames].copy()
                final_back_R = raw_back_R[:finalized_frames].copy()

                if chunk_idx > 0:
                    overlap_len = min(OVERLAP_FRAMES, finalized_frames)
                    fade_weights = np.linspace(0.0, 1.0, OVERLAP_FRAMES, endpoint=False)[:overlap_len]

                    final_voc_L[:overlap_len] = trailing_voc_L[:overlap_len] + final_voc_L[:overlap_len] * fade_weights
                    final_voc_R[:overlap_len] = trailing_voc_R[:overlap_len] + final_voc_R[:overlap_len] * fade_weights

                    if use_neural_sum:
                        final_back_L[:overlap_len] = trailing_back_L[:overlap_len] + final_back_L[:overlap_len] * fade_weights
                        final_back_R[:overlap_len] = trailing_back_R[:overlap_len] + final_back_R[:overlap_len] * fade_weights
                    else:
                        # Phase-perfect residual: original minus final crossfaded vocal
                        orig_L = left_ch[:overlap_len]
                        orig_R = right_ch[:overlap_len]
                        final_back_L[:overlap_len] = orig_L - final_voc_L[:overlap_len]
                        final_back_R[:overlap_len] = orig_R - final_voc_R[:overlap_len]

                # Store trailing overlap
                if not is_last_chunk and frames_to_read > HOP_FRAMES:
                    trailing_len = min(OVERLAP_FRAMES, frames_to_read - HOP_FRAMES)
                    fade_out = np.linspace(1.0, 0.0, OVERLAP_FRAMES, endpoint=False)[:trailing_len]

                    trailing_voc_L[:trailing_len] = raw_voc_L[HOP_FRAMES:HOP_FRAMES + trailing_len] * fade_out
                    trailing_voc_R[:trailing_len] = raw_voc_R[HOP_FRAMES:HOP_FRAMES + trailing_len] * fade_out

                    if use_neural_sum:
                        trailing_back_L[:trailing_len] = raw_back_L[HOP_FRAMES:HOP_FRAMES + trailing_len] * fade_out
                        trailing_back_R[:trailing_len] = raw_back_R[HOP_FRAMES:HOP_FRAMES + trailing_len] * fade_out

                # Clamp and interleave to 16-bit PCM
                final_voc_L = np.clip(final_voc_L, -1.0, 1.0)
                final_voc_R = np.clip(final_voc_R, -1.0, 1.0)
                final_back_L = np.clip(final_back_L, -1.0, 1.0)
                final_back_R = np.clip(final_back_R, -1.0, 1.0)

                voc_interleaved = np.empty((finalized_frames * 2,), dtype=np.int16)
                voc_interleaved[0::2] = (final_voc_L * 32767.0).astype(np.int16)
                voc_interleaved[1::2] = (final_voc_R * 32767.0).astype(np.int16)
                voc_file.write(voc_interleaved.tobytes())

                back_interleaved = np.empty((finalized_frames * 2,), dtype=np.int16)
                back_interleaved[0::2] = (final_back_L * 32767.0).astype(np.int16)
                back_interleaved[1::2] = (final_back_R * 32767.0).astype(np.int16)
                back_file.write(back_interleaved.tobytes())

                # Collect peak envelope
                for f in range(0, finalized_frames, max(1, finalized_frames // 50)):
                    global_frame = frame_offset + f
                    pidx = min(PEAK_BUCKET_COUNT - 1, int((global_frame / total_frames) * PEAK_BUCKET_COUNT))
                    vocal_peaks[pidx] = max(vocal_peaks[pidx], float(np.abs(final_voc_L[f])))
                    backing_peaks[pidx] = max(backing_peaks[pidx], float(np.abs(final_back_L[f])))

        finally:
            src_file.close()
            voc_file.close()
            back_file.close()

        # Wrap raw PCM into standard WAV files with proper 44-byte RIFF header
        total_pcm_bytes = os.path.getsize(temp_voc_pcm)

        with open(output_vocals_wav, "wb") as out_voc, open(temp_voc_pcm, "rb") as in_voc:
            write_wav_header(out_voc, total_pcm_bytes)
            shutil.copyfileobj(in_voc, out_voc)

        with open(output_backing_wav, "wb") as out_back, open(temp_back_pcm, "rb") as in_back:
            write_wav_header(out_back, total_pcm_bytes)
            shutil.copyfileobj(in_back, out_back)

        # Cleanup temporary files
        try:
            os.remove(temp_voc_pcm)
            os.remove(temp_back_pcm)
        except Exception:
            pass

        if on_progress:
            on_progress(
                DemucsSeparationProgress(
                    current_chunk=total_chunks,
                    total_chunks=total_chunks,
                    percent=100,
                    status_text="Separation Complete",
                    active_backend=backend.label,
                    elapsed_seconds=int(time.time() - start_time)
                )
            )

        return SeparationResult(
            vocals_wav_path=output_vocals_wav,
            backing_wav_path=output_backing_wav,
            vocal_peaks=vocal_peaks,
            backing_peaks=backing_peaks
        )
