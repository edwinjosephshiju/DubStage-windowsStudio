"""
DubStage Audio Extraction Engine
Extracts 44.1kHz stereo 16-bit PCM/WAV from video files and computes peak envelope
"""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple
import numpy as np

from ..config import SAMPLE_RATE, CHANNELS, PEAK_BUCKET_COUNT

@dataclass
class AudioExtractionResult:
    pcm_path: str
    duration_ms: int
    sample_rate: int
    channels: int
    waveform_peaks: np.ndarray
    width: int
    height: int

def find_binary(binary_name: str) -> Optional[str]:
    """Finds ffmpeg or ffprobe in MEIPASS, local app directory, or system PATH"""
    # 1. PyInstaller bundled path
    if hasattr(sys, "_MEIPASS"):
        bundled = Path(sys._MEIPASS) / f"{binary_name}.exe"
        if bundled.exists():
            return str(bundled)

    # 2. Alongside application executable
    app_dir = Path(sys.executable).parent
    app_bin = app_dir / f"{binary_name}.exe"
    if app_bin.exists():
        return str(app_bin)

    # 3. Project root directory
    root_bin = Path(__file__).resolve().parent.parent.parent / f"{binary_name}.exe"
    if root_bin.exists():
        return str(root_bin)

    # 4. System PATH
    found = shutil.which(binary_name)
    if found:
        return found
    found_exe = shutil.which(f"{binary_name}.exe")
    if found_exe:
        return found_exe

    return None

class AudioExtractionEngine:
    def __init__(self):
        self.ffmpeg_path = find_binary("ffmpeg")
        self.ffprobe_path = find_binary("ffprobe")

    def probe_video(self, video_path: str) -> Tuple[int, int, int]:
        """Returns (duration_ms, width, height) of the video"""
        if not self.ffprobe_path:
            return (0, 1920, 1080)

        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, startupinfo=startupinfo)
            data = json.loads(result.stdout)

            duration_sec = 0.0
            if "format" in data and "duration" in data["format"]:
                duration_sec = float(data["format"]["duration"])

            width, height = 1920, 1080
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    width = int(stream.get("width", 1920))
                    height = int(stream.get("height", 1080))
                    if duration_sec == 0.0 and "duration" in stream:
                        duration_sec = float(stream["duration"])
                    break

            return (int(duration_sec * 1000), width, height)
        except Exception:
            return (0, 1920, 1080)

    def extract_and_decode_audio(
        self,
        video_path: str,
        output_pcm_path: str,
        on_progress: Optional[Callable[[int, str], None]] = None
    ) -> AudioExtractionResult:
        """Extracts audio to 44.1kHz stereo 16-bit raw PCM little-endian"""
        if not self.ffmpeg_path:
            raise RuntimeError("ffmpeg binary not found. Please ensure ffmpeg is available in PATH or app directory.")

        duration_ms, width, height = self.probe_video(video_path)

        if on_progress:
            on_progress(10, "Extracting audio track from video container...")

        # Output raw PCM s16le 44100Hz stereo
        out_path = Path(output_pcm_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", video_path,
            "-vn",
            "-ar", str(SAMPLE_RATE),
            "-ac", str(CHANNELS),
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            output_pcm_path
        ]

        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        if on_progress:
            on_progress(30, "Decoding audio stream to 44.1kHz 16-bit stereo PCM...")

        proc = subprocess.run(cmd, capture_output=True, startupinfo=startupinfo)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg audio extraction failed: {proc.stderr.decode('utf-8', errors='ignore')}")

        if on_progress:
            on_progress(70, "Computing waveform peak envelope...")

        # Compute waveform envelope peaks from PCM
        pcm_size = os.path.getsize(output_pcm_path)
        total_frames = pcm_size // (CHANNELS * 2)

        if duration_ms <= 0:
            duration_ms = int((total_frames / SAMPLE_RATE) * 1000)

        # Read samples in blocks to compute peaks without loading entire huge file into RAM
        peaks = np.zeros(PEAK_BUCKET_COUNT, dtype=np.float32)
        if total_frames > 0:
            block_frames = max(1, total_frames // PEAK_BUCKET_COUNT)
            with open(output_pcm_path, "rb") as f:
                for i in range(PEAK_BUCKET_COUNT):
                    raw = f.read(block_frames * CHANNELS * 2)
                    if not raw:
                        break
                    samples = np.frombuffer(raw, dtype=np.int16)
                    if len(samples) > 0:
                        peaks[i] = np.max(np.abs(samples)) / 32768.0

        if on_progress:
            on_progress(100, "Audio extraction complete.")

        return AudioExtractionResult(
            pcm_path=output_pcm_path,
            duration_ms=duration_ms,
            sample_rate=SAMPLE_RATE,
            channels=CHANNELS,
            waveform_peaks=peaks,
            width=width,
            height=height
        )
