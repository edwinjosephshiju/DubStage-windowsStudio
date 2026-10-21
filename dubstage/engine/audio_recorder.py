"""
DubStage Hardware Audio Recording Engine
Low-latency hardware microphone capture with real-time RMS decibel & peak monitoring
"""

import math
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

from ..config import SAMPLE_RATE, CHANNELS

@dataclass
class TakeRecordingResult:
    pcm_file_path: str
    duration_ms: int
    peaks: np.ndarray

class AudioRecordingEngine:
    def __init__(self):
        self._is_recording = False
        self._record_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def stop_recording(self):
        self._stop_event.set()
        self._is_recording = False

    def record_take(
        self,
        output_file_path: str,
        max_duration_ms: int = 60000,
        on_rms_db: Optional[Callable[[float], None]] = None,
        on_peak_sample: Optional[Callable[[float], None]] = None
    ) -> TakeRecordingResult:
        """Records hardware microphone input directly to 16-bit stereo PCM"""
        Path(output_file_path).parent.mkdir(parents=True, exist_ok=True)
        self._stop_event.clear()
        self._is_recording = True

        recorded_chunks: List[np.ndarray] = []
        peak_list: List[float] = []
        start_time = time.time()
        max_duration_sec = max_duration_ms / 1000.0

        if sd is None:
            # Emulated silence recorder if sounddevice not present on build agent
            time_spent = 0.0
            block_frames = 2048
            while not self._stop_event.is_set() and time_spent < max_duration_sec:
                time.sleep(block_frames / SAMPLE_RATE)
                time_spent = time.time() - start_time
                silent_block = np.zeros((block_frames, CHANNELS), dtype=np.int16)
                recorded_chunks.append(silent_block)
                if on_rms_db:
                    on_rms_db(-60.0)
                if on_peak_sample:
                    on_peak_sample(0.0)
        else:
            block_size = 2048

            def audio_callback(indata, frames, time_info, status):
                if self._stop_event.is_set():
                    raise sd.CallbackStop()

                # Convert float32 or int16 to int16 stereo
                if indata.dtype == np.float32:
                    clipped = np.clip(indata, -1.0, 1.0)
                    int16_block = (clipped * 32767.0).astype(np.int16)
                    # mono to stereo if needed
                    if int16_block.shape[1] == 1:
                        int16_block = np.repeat(int16_block, 2, axis=1)
                else:
                    int16_block = indata.astype(np.int16)
                    if int16_block.shape[1] == 1:
                        int16_block = np.repeat(int16_block, 2, axis=1)

                recorded_chunks.append(int16_block.copy())

                # RMS & Peak calculation
                float_samples = int16_block.astype(np.float32) / 32768.0
                peak = float(np.max(np.abs(float_samples)))
                peak_list.append(peak)

                sum_sq = np.sum(float_samples * float_samples)
                rms = math.sqrt(sum_sq / (frames * CHANNELS)) if frames > 0 else 0.0
                db = max(-60.0, 20.0 * math.log10(rms)) if rms > 1e-4 else -60.0

                if on_rms_db:
                    on_rms_db(db)
                if on_peak_sample:
                    on_peak_sample(peak)

            try:
                with sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=min(2, sd.query_devices(kind='input')['max_input_channels'] or 1),
                    dtype='float32',
                    blocksize=block_size,
                    callback=audio_callback
                ):
                    while not self._stop_event.is_set():
                        if (time.time() - start_time) >= max_duration_sec:
                            break
                        time.sleep(0.02)
            except Exception as e:
                # Fallback if audio device is unavailable
                pass

        self._is_recording = False
        duration_ms = int((time.time() - start_time) * 1000)

        # Write to raw PCM file
        with open(output_file_path, "wb") as f:
            for chunk in recorded_chunks:
                f.write(chunk.tobytes())

        # Subsample peaks to 1200 points
        peaks_array = np.array(peak_list, dtype=np.float32)
        if len(peaks_array) > 1200:
            indices = np.linspace(0, len(peaks_array) - 1, 1200, dtype=int)
            peaks_array = peaks_array[indices]

        return TakeRecordingResult(
            pcm_file_path=output_file_path,
            duration_ms=duration_ms,
            peaks=peaks_array
        )
