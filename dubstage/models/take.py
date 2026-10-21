"""
DubStage Actor Take Entity Model
"""

from dataclasses import dataclass, field
import time

@dataclass
class TakeEntity:
    id: str
    clip_id: str
    take_number: int
    pcm_file_path: str
    duration_ms: int
    gain_db: float = 0.0
    time_offset_ms: int = 0
    noise_gate_threshold_db: float = -60.0
    recorded_at: int = field(default_factory=lambda: int(time.time() * 1000))
