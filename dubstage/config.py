"""
DubStage Studio - Configuration & System Constants
"""

import os
import sys
from pathlib import Path

# Application Metadata
APP_NAME = "DubStage"
APP_DISPLAY_NAME = "DubStage - AI Audio Dubbing & ADR Studio"
APP_VERSION = "1.0.4.0"
APP_PUBLISHER = "CN=DubStageStudioDev"
APP_DESCRIPTION = "Professional On-Device Video Dubbing, Neural Stem Separation, and ADR Studio for Windows"

# Audio Engineering Constants
SAMPLE_RATE = 44100
CHANNELS = 2  # Stereo
AUDIO_FORMAT = "PCM_16"
BYTES_PER_SAMPLE = 2
BYTES_PER_FRAME = CHANNELS * BYTES_PER_SAMPLE  # 4 bytes per frame

# Demucs v4 ONNX Inference Constants
DEMUCS_SEGMENT_FRAMES = 343980  # ~7.80 seconds at 44.1kHz
OVERLAP_FRAMES = 85995          # 25% overlap
HOP_FRAMES = DEMUCS_SEGMENT_FRAMES - OVERLAP_FRAMES  # 257985 frames (~5.85s hop)
MIN_MODEL_SIZE_BYTES = 50_000_000  # 50 MB

# Peak Envelope Buckets for Waveform Display
PEAK_BUCKET_COUNT = 1200

# VAD Defaults
DEFAULT_VAD_SENSITIVITY = 0.60
VAD_FRAME_DURATION_MS = 25

# Workspace Storage
def get_app_data_dir() -> Path:
    """Returns persistent application directory under %LOCALAPPDATA%/DubStage"""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base_dir = Path(local_app_data) / "DubStage"
    else:
        base_dir = Path.home() / ".dubstage"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir

def get_models_dir() -> Path:
    """Returns directory where ONNX separation models are stored"""
    models_dir = get_app_data_dir() / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir

def get_projects_dir() -> Path:
    """Returns directory where project databases and audio stems are stored"""
    projects_dir = get_app_data_dir() / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    return projects_dir
