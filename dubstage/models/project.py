"""
DubStage Project Entity Model
"""

from dataclasses import dataclass, field
import time

@dataclass
class ProjectEntity:
    id: str
    title: str
    video_uri: str
    video_duration_ms: int
    video_width: int = 1920
    video_height: int = 1080
    sample_rate: int = 44100
    channels: int = 2
    original_pcm_path: str = ""
    vocals_wav_path: str = ""
    backing_wav_path: str = ""
    model_checksum: str = ""
    status: str = "CREATED"
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    updated_at: int = field(default_factory=lambda: int(time.time() * 1000))

    STATUS_CREATED = "CREATED"
    STATUS_AUDIO_EXTRACTING = "AUDIO_EXTRACTING"
    STATUS_AUDIO_EXTRACTED = "AUDIO_EXTRACTED"
    STATUS_SEPARATING = "SEPARATING"
    STATUS_SEPARATED = "SEPARATED"
    STATUS_READY = "READY"
