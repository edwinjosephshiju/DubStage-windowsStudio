"""
DubStage Dialogue Clip Entity Model
"""

from dataclasses import dataclass, field
from typing import Optional
import time

@dataclass
class ClipEntity:
    id: str
    project_id: str
    clip_index: int
    start_ms: int
    end_ms: int
    speaker_name: str = "Speaker 1"
    script_text: str = ""
    active_take_id: Optional[str] = None
    is_muted: bool = False
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
