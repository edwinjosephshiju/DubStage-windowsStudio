"""
DubStage Presets, Enums, and Execution Backends
"""

from enum import Enum
from dataclasses import dataclass

class ModelPreset(Enum):
    HTDEMUCS_FT_VOCALS = (
        "htdemucs_ft_vocals",
        "HT-Demucs FT Vocals Specialist (166 MB)",
        "htdemucs_ft_vocals_fp16weights.onnx",
        "https://huggingface.co/StemSplitio/htdemucs-ft-vocals-onnx/resolve/main/htdemucs_ft_vocals_fp16weights.onnx",
        "Fine-tuned vocal extraction specialist. Uses phase-perfect residual (Original - Vocals) for pristine backing.",
        True  # is_vocals_only_trained
    )
    HTDEMUCS_4STEM = (
        "htdemucs_4stem",
        "HT-Demucs 4-Stem All-Trained (166 MB)",
        "htdemucs_fp16weights.onnx",
        "https://huggingface.co/StemSplitio/htdemucs-onnx/resolve/main/htdemucs_fp16weights.onnx",
        "Trained on all 4 stems (Drums, Bass, Other, Vocals). Supports both Residual and Neural Sum backing.",
        False  # is_vocals_only_trained
    )

    def __init__(self, preset_id: str, display_name: str, file_name: str, download_url: str, description: str, is_vocals_only_trained: bool):
        self.preset_id = preset_id
        self.display_name = display_name
        self.file_name = file_name
        self.download_url = download_url
        self.description = description
        self.is_vocals_only_trained = is_vocals_only_trained

class ExecutionBackend(Enum):
    CPU_LOW_RAM = ("cpu", "CPU (Optimized Sequential)", "Low-memory sequential inference (prevents RAM spikes)")
    DIRECTML_GPU = ("directml", "DirectML (GPU / NPU)", "DirectX 12 GPU acceleration for Windows (with CPU fallback)")
    CUDA_GPU = ("cuda", "NVIDIA CUDA (GPU)", "NVIDIA GPU acceleration (requires CUDA runtime)")

    def __init__(self, backend_id: str, label: str, subtitle: str):
        self.backend_id = backend_id
        self.label = label
        self.subtitle = subtitle

class KaraokeMode(Enum):
    RESIDUAL_SUBTRACTION = (
        "residual",
        "Residual Backing (Original - Vocals)",
        "Phase-perfect cancellation. Zero noise/drone. Mandatory for Vocals Specialist model."
    )
    NEURAL_SUM = (
        "neural_sum",
        "Neural Sum (Drums + Bass + Other)",
        "Sums non-vocal stems. Only available for 4-Stem models."
    )

    def __init__(self, mode_id: str, label: str, description: str):
        self.mode_id = mode_id
        self.label = label
        self.description = description

class StudioAuditionMode(Enum):
    FULL_DUB_MIX = "FULL_DUB_MIX"                     # Backing + Active user takes (original vocals for missing cues)
    ORIGINAL_WITH_RESIDUAL = "ORIGINAL_WITH_RESIDUAL" # Original reference vocals + backing
    RECORDED_WITH_RESIDUAL = "RECORDED_WITH_RESIDUAL" # Recorded user take + backing
    SOLO_ORIGINAL = "SOLO_ORIGINAL"                   # Reference vocals only
    SOLO_ACTIVE_TAKE = "SOLO_ACTIVE_TAKE"             # Active user take only
    BACKING_ONLY = "BACKING_ONLY"                     # Instrumental backing only

@dataclass
class DemucsSeparationProgress:
    current_chunk: int = 0
    total_chunks: int = 0
    percent: int = 0
    status_text: str = "Ready"
    active_backend: str = "CPU"
    last_chunk_inference_ms: int = 0
    elapsed_seconds: int = 0
    eta_seconds: int = 0

@dataclass
class MixTakeTrack:
    take_id: str
    pcm_file_path: str
    start_ms: int
    duration_ms: int
    gain_db: float = 0.0
    time_offset_ms: int = 0
