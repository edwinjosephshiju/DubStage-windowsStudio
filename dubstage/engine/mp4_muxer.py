"""
DubStage MP4 Video Exporter & Subtitle Muxer
Renders multi-take master dub mix, muxes into MP4 via FFmpeg, and exports SRT/VTT subtitles
"""

import math
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional
import numpy as np

from ..config import SAMPLE_RATE, CHANNELS, BYTES_PER_FRAME
from ..models import ClipEntity, MixTakeTrack
from .audio_extractor import find_binary
from .demucs_engine import write_wav_header

@dataclass
class MuxerExportProgress:
    stage: str
    percent: int
    current_frame: int = 0
    total_frames: int = 0

def format_srt_time(ms: int) -> str:
    """Format milliseconds to SRT timestamp 00:00:00,000"""
    total_sec = ms // 1000
    msec = ms % 1000
    hrs = total_sec // 3600
    mins = (total_sec % 3600) // 60
    secs = total_sec % 60
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{msec:03d}"

def format_vtt_time(ms: int) -> str:
    """Format milliseconds to WebVTT timestamp 00:00:00.000"""
    total_sec = ms // 1000
    msec = ms % 1000
    hrs = total_sec // 3600
    mins = (total_sec % 3600) // 60
    secs = total_sec % 60
    return f"{hrs:02d}:{mins:02d}:{secs:02d}.{msec:03d}"

class Mp4ExportMuxer:
    def __init__(self):
        self.ffmpeg_path = find_binary("ffmpeg")

    def export_srt(self, clips: List[ClipEntity], output_srt_path: str):
        """Exports dialogue cues to standard SubRip (.srt) subtitle file"""
        Path(output_srt_path).parent.mkdir(parents=True, exist_ok=True)
        sorted_clips = sorted(clips, key=lambda c: c.start_ms)
        with open(output_srt_path, "w", encoding="utf-8") as f:
            for idx, clip in enumerate(sorted_clips, 1):
                start_str = format_srt_time(clip.start_ms)
                end_str = format_srt_time(clip.end_ms)
                text = clip.script_text.strip() or f"[{clip.speaker_name}]"
                f.write(f"{idx}\n{start_str} --> {end_str}\n{clip.speaker_name}: {text}\n\n")

    def export_vtt(self, clips: List[ClipEntity], output_vtt_path: str):
        """Exports dialogue cues to WebVTT (.vtt) subtitle file"""
        Path(output_vtt_path).parent.mkdir(parents=True, exist_ok=True)
        sorted_clips = sorted(clips, key=lambda c: c.start_ms)
        with open(output_vtt_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            for idx, clip in enumerate(sorted_clips, 1):
                start_str = format_vtt_time(clip.start_ms)
                end_str = format_vtt_time(clip.end_ms)
                text = clip.script_text.strip() or f"[{clip.speaker_name}]"
                f.write(f"{idx}\n{start_str} --> {end_str}\n<v {clip.speaker_name}>{text}\n\n")

    def export_dubbed_video(
        self,
        source_video_path: str,
        backing_wav_path: Optional[str],
        original_vocals_wav_path: Optional[str],
        takes: List[MixTakeTrack],
        total_duration_ms: int,
        output_mp4_path: str,
        on_progress: Optional[Callable[[MuxerExportProgress], None]] = None
    ) -> str:
        """Pre-renders master mixed audio PCM and muxes with original video stream into MP4"""
        if not self.ffmpeg_path:
            raise RuntimeError("ffmpeg binary not found. Cannot export MP4 video.")

        out_path = Path(output_mp4_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        temp_wav_path = str(out_path.with_suffix(".temp_master.wav"))

        total_frames = int((total_duration_ms * SAMPLE_RATE) / 1000)
        block_frames = 4096

        backing_f = open(backing_wav_path, "rb") if (backing_wav_path and os.path.exists(backing_wav_path)) else None
        vocals_f = open(original_vocals_wav_path, "rb") if (original_vocals_wav_path and os.path.exists(original_vocals_wav_path)) else None

        take_files = {}
        for t in takes:
            if os.path.exists(t.pcm_file_path):
                try:
                    take_files[t.take_id] = open(t.pcm_file_path, "rb")
                except Exception:
                    pass

        # 1. Render Master Mixed WAV
        if on_progress:
            on_progress(MuxerExportProgress(stage="Rendering Master Mix", percent=10))

        wav_offset = 44
        temp_pcm_path = str(out_path.with_suffix(".temp_master.pcm"))

        try:
            with open(temp_pcm_path, "wb") as pcm_out:
                current_frame = 0
                while current_frame < total_frames:
                    frames_in_block = min(block_frames, total_frames - current_frame)
                    mix_L = np.zeros(frames_in_block, dtype=np.float32)
                    mix_R = np.zeros(frames_in_block, dtype=np.float32)

                    # Backing stem
                    if backing_f:
                        backing_f.seek(wav_offset + current_frame * BYTES_PER_FRAME)
                        raw_b = backing_f.read(frames_in_block * BYTES_PER_FRAME)
                        if raw_b:
                            b_samples = np.frombuffer(raw_b, dtype=np.int16)
                            b_len = len(b_samples) // 2
                            mix_L[:b_len] += b_samples[0::2].astype(np.float32) / 32768.0
                            mix_R[:b_len] += b_samples[1::2].astype(np.float32) / 32768.0

                    # Original vocals
                    if vocals_f:
                        vocals_f.seek(wav_offset + current_frame * BYTES_PER_FRAME)
                        raw_v = vocals_f.read(frames_in_block * BYTES_PER_FRAME)
                        if raw_v:
                            v_samples = np.frombuffer(raw_v, dtype=np.int16)
                            v_len = len(v_samples) // 2
                            mix_L[:v_len] += v_samples[0::2].astype(np.float32) / 32768.0
                            mix_R[:v_len] += v_samples[1::2].astype(np.float32) / 32768.0

                    # Actor takes
                    for t in takes:
                        if t.take_id in take_files:
                            take_f = take_files[t.take_id]
                            take_start = int(((t.start_ms + t.time_offset_ms) * SAMPLE_RATE) / 1000)
                            take_end = take_start + int((t.duration_ms * SAMPLE_RATE) / 1000)

                            if current_frame + frames_in_block > take_start and current_frame < take_end:
                                rel_start = max(0, take_start - current_frame)
                                rel_end = min(frames_in_block, take_end - current_frame)
                                take_offset = max(0, current_frame - take_start)
                                read_f = rel_end - rel_start

                                take_f.seek(take_offset * BYTES_PER_FRAME)
                                raw_t = take_f.read(read_f * BYTES_PER_FRAME)
                                if raw_t:
                                    t_samples = np.frombuffer(raw_t, dtype=np.int16)
                                    t_len = min(read_f, len(t_samples) // 2)
                                    gain_lin = 10.0 ** (t.gain_db / 20.0)
                                    mix_L[rel_start:rel_start + t_len] += (t_samples[0::2][:t_len].astype(np.float32) / 32768.0) * gain_lin
                                    mix_R[rel_start:rel_start + t_len] += (t_samples[1::2][:t_len].astype(np.float32) / 32768.0) * gain_lin

                    # Master saturation
                    mix_L = np.tanh(mix_L)
                    mix_R = np.tanh(mix_R)

                    out_int16 = np.empty((frames_in_block * 2,), dtype=np.int16)
                    out_int16[0::2] = (np.clip(mix_L, -1.0, 1.0) * 32767.0).astype(np.int16)
                    out_int16[1::2] = (np.clip(mix_R, -1.0, 1.0) * 32767.0).astype(np.int16)
                    pcm_out.write(out_int16.tobytes())

                    current_frame += frames_in_block
                    if on_progress and total_frames > 0:
                        pct = 10 + int((current_frame / total_frames) * 40)
                        on_progress(MuxerExportProgress(stage="Rendering Master Mix", percent=pct, current_frame=current_frame, total_frames=total_frames))

            # Wrap to WAV
            total_pcm_bytes = os.path.getsize(temp_pcm_path)
            with open(temp_wav_path, "wb") as out_wav, open(temp_pcm_path, "rb") as in_pcm:
                write_wav_header(out_wav, total_pcm_bytes)
                import shutil
                shutil.copyfileobj(in_pcm, out_wav)

        finally:
            if backing_f:
                backing_f.close()
            if vocals_f:
                vocals_f.close()
            for tf in take_files.values():
                tf.close()
            try:
                os.remove(temp_pcm_path)
            except Exception:
                pass

        # 2. Mux with FFmpeg
        if on_progress:
            on_progress(MuxerExportProgress(stage="Muxing MP4 Container", percent=60))

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", source_video_path,
            "-i", temp_wav_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_mp4_path
        ]

        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        proc = subprocess.run(cmd, capture_output=True, startupinfo=startupinfo)
        if proc.returncode != 0:
            # Fallback re-encode video if copy fails
            cmd_fallback = [
                self.ffmpeg_path,
                "-y",
                "-i", source_video_path,
                "-i", temp_wav_path,
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                output_mp4_path
            ]
            proc = subprocess.run(cmd_fallback, capture_output=True, startupinfo=startupinfo)
            if proc.returncode != 0:
                raise RuntimeError(f"FFmpeg MP4 export failed: {proc.stderr.decode('utf-8', errors='ignore')}")

        try:
            os.remove(temp_wav_path)
        except Exception:
            pass

        if on_progress:
            on_progress(MuxerExportProgress(stage="Export Complete", percent=100))

        return output_mp4_path
