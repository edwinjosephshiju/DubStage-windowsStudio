"""
DubStage Voice Activity Detection (VAD) & Turn Segmentation Engine
Adaptive noise floor profiling, dual-threshold hysteresis, pitch autocorrelation, and speaker-aware turn segmentation
"""

import math
import os
import struct
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import numpy as np

from ..config import SAMPLE_RATE, CHANNELS, VAD_FRAME_DURATION_MS

@dataclass
class DetectedDialogueClip:
    id: str
    clip_index: int
    start_ms: int
    end_ms: int
    speaker_name: str = "Speaker 1"
    script_text: str = ""

@dataclass
class RawSegment:
    start_frame: int
    end_frame: int
    median_pitch: float = 0.0
    mean_centroid: float = 0.0

class VadEngine:
    def detect_dialogue_clips(
        self,
        audio_file_path: str,
        is_wav_file: bool = True,
        sensitivity: float = 0.60
    ) -> List[DetectedDialogueClip]:
        """Detects dialogue cues and segments speaker turns from vocal stem or original PCM"""
        p = Path(audio_file_path)
        if not p.exists() or p.stat().st_size <= 44:
            return []

        frame_samples = (SAMPLE_RATE * VAD_FRAME_DURATION_MS) // 1000  # 1102 samples per channel
        bytes_per_frame = frame_samples * CHANNELS * 2  # 4408 bytes per frame

        frame_rms_list = []
        frame_zcr_list = []
        frame_pitch_list = []
        frame_centroid_list = []

        ds_len = frame_samples // 2  # 551 samples @ 22050Hz
        downsampled_mono = np.zeros(ds_len, dtype=np.float32)

        with open(audio_file_path, "rb") as f:
            if is_wav_file:
                f.seek(44)  # Skip standard RIFF header

            while raw_bytes := f.read(bytes_per_frame):
                if len(raw_bytes) < 4:
                    break

                samples = np.frombuffer(raw_bytes, dtype=np.int16)
                if len(samples) < 2:
                    break

                # Mono downmix
                left = samples[0::2].astype(np.float32) / 32768.0
                right = samples[1::2].astype(np.float32) / 32768.0
                min_len = min(len(left), len(right))
                mono = (left[:min_len] + right[:min_len]) * 0.5

                sample_count = len(mono)
                if sample_count == 0:
                    continue

                # RMS
                sum_sq = np.sum(mono * mono)
                rms = math.sqrt(sum_sq / sample_count)

                # Zero crossing rate
                zcr = np.mean(mono[:-1] * mono[1:] < 0)

                # Spectral centroid proxy
                diff = np.diff(mono)
                diff_sum = np.sum(diff * diff)
                centroid = float(diff_sum / (sum_sq + 1e-6))

                # Pitch estimation via autocorrelation on downsampled mono
                ds_actual_len = min(ds_len, sample_count // 2)
                downsampled_mono[:ds_actual_len] = mono[::2][:ds_actual_len]

                pitch_hz = 0.0
                if rms > 0.015 and ds_actual_len >= 280:
                    min_lag = 55   # ~400 Hz at 22050 Hz
                    max_lag = 275  # ~80 Hz at 22050 Hz
                    win_len = ds_actual_len - max_lag

                    if win_len > 0:
                        ref = downsampled_mono[:win_len]
                        energy0 = np.sum(ref * ref)
                        if energy0 > 1e-5:
                            best_lag = -1
                            max_corr = 0.0
                            for lag in range(min_lag, max_lag + 1, 2):
                                target = downsampled_mono[lag:lag + win_len]
                                dot = np.sum(ref * target)
                                energy_lag = np.sum(target * target)
                                norm_corr = dot / (math.sqrt(energy0 * energy_lag) + 1e-6)
                                if norm_corr > max_corr:
                                    max_corr = norm_corr
                                    best_lag = lag

                            if max_corr > 0.32 and best_lag > 0:
                                pitch_hz = 22050.0 / float(best_lag)

                frame_rms_list.append(rms)
                frame_zcr_list.append(zcr)
                frame_pitch_list.append(pitch_hz)
                frame_centroid_list.append(centroid)

        total_frames = len(frame_rms_list)
        if total_frames == 0:
            return []

        # Adaptive noise floor profiling (15th percentile) and dynamic range (95th percentile)
        sorted_rms = sorted(frame_rms_list)
        noise_floor = sorted_rms[int(total_frames * 0.15)]
        peak_rms = sorted_rms[min(total_frames - 1, int(total_frames * 0.95))]
        dynamic_range = max(0.01, peak_rms - noise_floor)

        # Threshold tuning
        clamped_sens = max(0.1, min(1.0, sensitivity))
        threshold_factor = max(0.02, 0.24 - (clamped_sens * 0.21))
        attack_thresh = noise_floor + (dynamic_range * threshold_factor)
        sustain_thresh = attack_thresh * 0.65

        is_speech = np.zeros(total_frames, dtype=bool)
        currently_voicing = False

        for i in range(total_frames):
            r = frame_rms_list[i]
            z = frame_zcr_list[i]

            if not currently_voicing:
                if r >= attack_thresh or (r >= sustain_thresh and 0.02 <= z <= 0.55):
                    currently_voicing = True
                    is_speech[i] = True
            else:
                if r >= sustain_thresh or (r >= (noise_floor + 0.002) and 0.03 <= z <= 0.60):
                    is_speech[i] = True
                else:
                    currently_voicing = False

        # Apply hangover (250ms = 10 frames)
        hangover_frames = 250 // VAD_FRAME_DURATION_MS
        trailing_hangover = 0
        for i in range(total_frames):
            if is_speech[i]:
                trailing_hangover = hangover_frames
            elif trailing_hangover > 0:
                is_speech[i] = True
                trailing_hangover -= 1

        # Aggregate consecutive speech frames
        raw_segments: List[RawSegment] = []
        in_seg = False
        seg_start = 0

        def calc_acoustics(seg: RawSegment):
            pitches = [frame_pitch_list[f] for f in range(seg.start_frame, seg.end_frame) if 75.0 <= frame_pitch_list[f] <= 450.0]
            centroids = [frame_centroid_list[f] for f in range(seg.start_frame, seg.end_frame)]
            seg.median_pitch = float(np.median(pitches)) if pitches else 0.0
            seg.mean_centroid = float(np.mean(centroids)) if centroids else 0.0

        for i in range(total_frames):
            if is_speech[i]:
                if not in_seg:
                    in_seg = True
                    seg_start = i
            else:
                if in_seg:
                    in_seg = False
                    seg = RawSegment(seg_start, i)
                    calc_acoustics(seg)
                    raw_segments.append(seg)

        if in_seg:
            seg = RawSegment(seg_start, total_frames)
            calc_acoustics(seg)
            raw_segments.append(seg)

        # Speaker-aware bridging
        max_gap_frames = 600 // VAD_FRAME_DURATION_MS
        bridged_segments: List[RawSegment] = []

        for seg in raw_segments:
            if not bridged_segments:
                bridged_segments.append(seg)
            else:
                prev = bridged_segments[-1]
                gap = seg.start_frame - prev.end_frame

                is_same_speaker = True
                if prev.median_pitch > 0 and seg.median_pitch > 0:
                    pdiff = abs(prev.median_pitch - seg.median_pitch)
                    rel_diff = pdiff / max(prev.median_pitch, seg.median_pitch)
                    if rel_diff > 0.18 or pdiff > 28.0:
                        is_same_speaker = False
                elif gap > (180 // VAD_FRAME_DURATION_MS) and abs(prev.mean_centroid - seg.mean_centroid) > 0.8:
                    is_same_speaker = False

                if gap <= max_gap_frames and is_same_speaker:
                    prev.end_frame = seg.end_frame
                    calc_acoustics(prev)
                else:
                    bridged_segments.append(seg)

        # Filter out tiny noise clicks (< 200ms)
        min_seg_frames = 200 // VAD_FRAME_DURATION_MS
        final_segments = [s for s in bridged_segments if (s.end_frame - s.start_frame) >= min_seg_frames]

        # Speaker clustering for auto-labeling Speaker 1, Speaker 2, etc.
        speaker_profiles: List[float] = []

        detected_clips = []
        for idx, seg in enumerate(final_segments):
            start_ms = max(0, seg.start_frame * VAD_FRAME_DURATION_MS - 40)  # Subtle 40ms attack padding
            end_ms = seg.end_frame * VAD_FRAME_DURATION_MS + 80              # 80ms release padding

            speaker_tag = "Speaker 1"
            if seg.median_pitch > 0:
                assigned = False
                for spk_idx, ref_pitch in enumerate(speaker_profiles):
                    if abs(seg.median_pitch - ref_pitch) / max(seg.median_pitch, ref_pitch) < 0.15:
                        speaker_tag = f"Speaker {spk_idx + 1}"
                        speaker_profiles[spk_idx] = (ref_pitch * 0.7) + (seg.median_pitch * 0.3)
                        assigned = True
                        break
                if not assigned:
                    speaker_profiles.append(seg.median_pitch)
                    speaker_tag = f"Speaker {len(speaker_profiles)}"

            detected_clips.append(
                DetectedDialogueClip(
                    id=str(uuid.uuid4()),
                    clip_index=idx + 1,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    speaker_name=speaker_tag,
                    script_text=""
                )
            )

        return detected_clips
