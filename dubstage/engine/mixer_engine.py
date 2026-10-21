"""
DubStage Multi-Track Software DAW Mixer Engine
Low-latency stem playback, soft-clipping sum bus, take auditioning, and real-time playhead sync
"""

import math
import os
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

from ..config import SAMPLE_RATE, CHANNELS, BYTES_PER_FRAME
from ..models import MixTakeTrack, StudioAuditionMode

class PcmSoftwareMixerEngine:
    def __init__(self):
        self._is_playing = False
        self._play_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._playback_pos_ms = 0

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def playback_position_ms(self) -> int:
        return self._playback_pos_ms

    def stop(self):
        self._stop_event.set()
        self._is_playing = False
        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join(timeout=0.3)

    def play_mix(
        self,
        backing_wav_path: Optional[str],
        original_vocals_wav_path: Optional[str],
        takes: List[MixTakeTrack],
        start_position_ms: int = 0,
        end_position_ms: int = 100000000,
        audition_mode: StudioAuditionMode = StudioAuditionMode.FULL_DUB_MIX,
        active_take_id: Optional[str] = None,
        backing_gain_db: float = 0.0,
        on_playhead_update: Optional[Callable[[int], None]] = None,
        on_finished: Optional[Callable[[], None]] = None
    ):
        self.stop()
        self._stop_event.clear()
        self._is_playing = True
        self._playback_pos_ms = start_position_ms

        def run_player():
            backing_f = open(backing_wav_path, "rb") if (backing_wav_path and os.path.exists(backing_wav_path)) else None
            vocals_f = open(original_vocals_wav_path, "rb") if (original_vocals_wav_path and os.path.exists(original_vocals_wav_path)) else None

            take_files: Dict[str, any] = {}
            for t in takes:
                if os.path.exists(t.pcm_file_path):
                    try:
                        take_files[t.take_id] = open(t.pcm_file_path, "rb")
                    except Exception:
                        pass

            block_frames = 2048
            start_frame = int((start_position_ms * SAMPLE_RATE) / 1000)
            end_frame = int((end_position_ms * SAMPLE_RATE) / 1000)
            current_frame = start_frame

            backing_gain_lin = 10.0 ** (backing_gain_db / 20.0)

            # Pre-calculate active take spans
            active_take_track = next((t for t in takes if t.take_id == active_take_id), None)

            # WAV RIFF header offset = 44 bytes
            wav_offset = 44

            stream = None
            if sd is not None:
                try:
                    stream = sd.OutputStream(
                        samplerate=SAMPLE_RATE,
                        channels=CHANNELS,
                        dtype='float32',
                        blocksize=block_frames
                    )
                    stream.start()
                except Exception:
                    stream = None

            try:
                while not self._stop_event.is_set() and current_frame < end_frame:
                    frames_in_block = min(block_frames, end_frame - current_frame)
                    if frames_in_block <= 0:
                        break

                    mix_bus_L = np.zeros(frames_in_block, dtype=np.float32)
                    mix_bus_R = np.zeros(frames_in_block, dtype=np.float32)

                    pos_ms = int((current_frame * 1000) / SAMPLE_RATE)
                    self._playback_pos_ms = pos_ms
                    if on_playhead_update:
                        on_playhead_update(pos_ms)

                    # 1. Backing Track
                    include_backing = audition_mode in [
                        StudioAuditionMode.FULL_DUB_MIX,
                        StudioAuditionMode.ORIGINAL_WITH_RESIDUAL,
                        StudioAuditionMode.RECORDED_WITH_RESIDUAL,
                        StudioAuditionMode.BACKING_ONLY
                    ]
                    if include_backing and backing_f:
                        backing_f.seek(wav_offset + current_frame * BYTES_PER_FRAME)
                        raw_b = backing_f.read(frames_in_block * BYTES_PER_FRAME)
                        if raw_b:
                            b_samples = np.frombuffer(raw_b, dtype=np.int16)
                            b_len = len(b_samples) // 2
                            mix_bus_L[:b_len] += (b_samples[0::2].astype(np.float32) / 32768.0) * backing_gain_lin
                            mix_bus_R[:b_len] += (b_samples[1::2].astype(np.float32) / 32768.0) * backing_gain_lin

                    # 2. Original Reference Vocals
                    include_original = audition_mode in [
                        StudioAuditionMode.ORIGINAL_WITH_RESIDUAL,
                        StudioAuditionMode.SOLO_ORIGINAL
                    ] or (audition_mode == StudioAuditionMode.FULL_DUB_MIX and not takes)

                    if include_original and vocals_f:
                        vocals_f.seek(wav_offset + current_frame * BYTES_PER_FRAME)
                        raw_v = vocals_f.read(frames_in_block * BYTES_PER_FRAME)
                        if raw_v:
                            v_samples = np.frombuffer(raw_v, dtype=np.int16)
                            v_len = len(v_samples) // 2
                            mix_bus_L[:v_len] += (v_samples[0::2].astype(np.float32) / 32768.0)
                            mix_bus_R[:v_len] += (v_samples[1::2].astype(np.float32) / 32768.0)

                    # 3. User Recorded Takes
                    if audition_mode == StudioAuditionMode.RECORDED_WITH_RESIDUAL or audition_mode == StudioAuditionMode.SOLO_ACTIVE_TAKE:
                        active_takes_to_play = [active_take_track] if active_take_track else []
                    elif audition_mode == StudioAuditionMode.FULL_DUB_MIX:
                        active_takes_to_play = takes
                    else:
                        active_takes_to_play = []

                    for t in active_takes_to_play:
                        if t and t.take_id in take_files:
                            take_f = take_files[t.take_id]
                            take_start_frame = int(((t.start_ms + t.time_offset_ms) * SAMPLE_RATE) / 1000)
                            take_end_frame = take_start_frame + int((t.duration_ms * SAMPLE_RATE) / 1000)

                            # Check overlap with current block
                            if current_frame + frames_in_block > take_start_frame and current_frame < take_end_frame:
                                rel_start = max(0, take_start_frame - current_frame)
                                rel_end = min(frames_in_block, take_end_frame - current_frame)
                                take_read_offset = max(0, current_frame - take_start_frame)
                                read_frames = rel_end - rel_start

                                take_f.seek(take_read_offset * BYTES_PER_FRAME)
                                raw_t = take_f.read(read_frames * BYTES_PER_FRAME)
                                if raw_t:
                                    t_samples = np.frombuffer(raw_t, dtype=np.int16)
                                    t_len = min(read_frames, len(t_samples) // 2)
                                    gain_lin = 10.0 ** (t.gain_db / 20.0)
                                    mix_bus_L[rel_start:rel_start + t_len] += (t_samples[0::2][:t_len].astype(np.float32) / 32768.0) * gain_lin
                                    mix_bus_R[rel_start:rel_start + t_len] += (t_samples[1::2][:t_len].astype(np.float32) / 32768.0) * gain_lin

                    # 4. Soft-Clipping Saturation Master Bus
                    mix_bus_L = np.tanh(mix_bus_L)
                    mix_bus_R = np.tanh(mix_bus_R)

                    out_block = np.empty((frames_in_block, CHANNELS), dtype=np.float32)
                    out_block[:, 0] = mix_bus_L
                    out_block[:, 1] = mix_bus_R

                    if stream:
                        stream.write(out_block)
                    else:
                        time.sleep(frames_in_block / SAMPLE_RATE)

                    current_frame += frames_in_block

            finally:
                if stream:
                    try:
                        stream.stop()
                        stream.close()
                    except Exception:
                        pass
                if backing_f:
                    backing_f.close()
                if vocals_f:
                    vocals_f.close()
                for tf in take_files.values():
                    tf.close()

                self._is_playing = False
                if on_finished and not self._stop_event.is_set():
                    on_finished()

        self._play_thread = threading.Thread(target=run_player, daemon=True)
        self._play_thread.start()
