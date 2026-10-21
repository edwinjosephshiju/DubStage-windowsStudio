"""
DubStage Model Manager
Hugging Face HTTP resumable downloader, SHA-256 verification, model sideloading, and settings persistence
"""

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
import requests

from ..config import get_models_dir, get_app_data_dir, MIN_MODEL_SIZE_BYTES
from ..models import ModelPreset, ExecutionBackend, KaraokeMode

@dataclass
class ModelStatus:
    is_ready: bool = False
    is_downloading: bool = False
    percent: int = 0
    speed_mb_s: float = 0.0
    bytes_read: int = 0
    total_bytes: int = 0
    message: str = "Model missing"
    model_path: str = ""
    sha256: str = ""

class ModelManager:
    def __init__(self):
        self.models_dir = get_models_dir()
        self.settings_file = get_app_data_dir() / "settings.json"

        # Defaults
        self.active_preset = ModelPreset.HTDEMUCS_FT_VOCALS
        self.active_backend = ExecutionBackend.CPU_LOW_RAM
        self.active_karaoke_mode = KaraokeMode.RESIDUAL_SUBTRACTION
        self.persist_backend = True
        self.persist_algorithm = True

        self._cancelled = False
        self._load_settings()

    def _load_settings(self):
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.persist_backend = data.get("persist_backend", True)
                self.persist_algorithm = data.get("persist_algorithm", True)

                backend_name = data.get("default_backend")
                if backend_name and self.persist_backend:
                    for b in ExecutionBackend:
                        if b.name == backend_name:
                            self.active_backend = b
                            break

                algo_name = data.get("default_algorithm")
                if algo_name and self.persist_algorithm:
                    for m in KaraokeMode:
                        if m.name == algo_name:
                            self.active_karaoke_mode = m
                            break

                preset_name = data.get("default_preset")
                if preset_name:
                    for p in ModelPreset:
                        if p.name == preset_name:
                            self.active_preset = p
                            break
            except Exception:
                pass

    def save_settings(self):
        try:
            data = {
                "persist_backend": self.persist_backend,
                "persist_algorithm": self.persist_algorithm,
                "default_backend": self.active_backend.name if self.persist_backend else None,
                "default_algorithm": self.active_karaoke_mode.name if self.persist_algorithm else None,
                "default_preset": self.active_preset.name
            }
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def set_model_preset(self, preset: ModelPreset):
        self.active_preset = preset
        self.save_settings()

    def set_execution_backend(self, backend: ExecutionBackend):
        self.active_backend = backend
        self.save_settings()

    def set_karaoke_mode(self, mode: KaraokeMode):
        self.active_karaoke_mode = mode
        self.save_settings()

    def get_model_file_path(self, preset: Optional[ModelPreset] = None) -> Path:
        target = preset or self.active_preset
        return self.models_dir / target.file_name

    def check_status(self, preset: Optional[ModelPreset] = None) -> ModelStatus:
        target_path = self.get_model_file_path(preset)
        if target_path.exists() and target_path.stat().st_size >= MIN_MODEL_SIZE_BYTES:
            size_mb = target_path.stat().st_size / (1024 * 1024)
            return ModelStatus(
                is_ready=True,
                is_downloading=False,
                percent=100,
                bytes_read=target_path.stat().st_size,
                total_bytes=target_path.stat().st_size,
                message=f"Ready ({size_mb:.1f} MB)",
                model_path=str(target_path)
            )
        return ModelStatus(
            is_ready=False,
            is_downloading=False,
            percent=0,
            message="Model missing or incomplete (<50MB)"
        )

    def cancel_download(self):
        self._cancelled = True

    def download_model(
        self,
        preset: Optional[ModelPreset] = None,
        on_progress: Optional[Callable[[ModelStatus], None]] = None
    ) -> Path:
        self._cancelled = False
        target_preset = preset or self.active_preset
        dest_path = self.get_model_file_path(target_preset)
        part_path = dest_path.with_suffix(".part")

        # Resume download if partial file exists
        initial_bytes = 0
        headers = {}
        if part_path.exists():
            initial_bytes = part_path.stat().st_size
            headers["Range"] = f"bytes={initial_bytes}-"

        url = target_preset.download_url

        try:
            with requests.get(url, headers=headers, stream=True, timeout=30) as r:
                r.raise_for_status()

                total_size = initial_bytes
                content_range = r.headers.get("Content-Range")
                if content_range:
                    total_size = int(content_range.split("/")[-1])
                elif "Content-Length" in r.headers:
                    total_size += int(r.headers["Content-Length"])

                bytes_read = initial_bytes
                mode = "ab" if initial_bytes > 0 else "wb"

                start_time = time.time()
                last_update = time.time()
                bytes_since_last = 0

                with open(part_path, mode) as f:
                    for chunk in r.iter_content(chunk_size=128 * 1024):
                        if self._cancelled:
                            raise InterruptedError("Download cancelled by user")
                        if chunk:
                            f.write(chunk)
                            bytes_read += len(chunk)
                            bytes_since_last += len(chunk)

                            now = time.time()
                            if now - last_update >= 0.25:
                                speed_mb = (bytes_since_last / (now - last_update)) / (1024 * 1024)
                                pct = int((bytes_read / total_size) * 100) if total_size > 0 else 0
                                if on_progress:
                                    on_progress(
                                        ModelStatus(
                                            is_ready=False,
                                            is_downloading=True,
                                            percent=pct,
                                            speed_mb_s=speed_mb,
                                            bytes_read=bytes_read,
                                            total_bytes=total_size,
                                            message=f"Downloading {pct}% ({speed_mb:.1f} MB/s)"
                                        )
                                    )
                                last_update = now
                                bytes_since_last = 0

            # Atomic rename after download completes
            if part_path.exists():
                if dest_path.exists():
                    dest_path.unlink()
                part_path.rename(dest_path)

            # Compute SHA-256
            sha = hashlib.sha256()
            with open(dest_path, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    sha.update(chunk)
            sha_hex = sha.hexdigest()

            status = ModelStatus(
                is_ready=True,
                is_downloading=False,
                percent=100,
                bytes_read=dest_path.stat().st_size,
                total_bytes=dest_path.stat().st_size,
                message=f"Verified SHA-256 ({dest_path.stat().st_size / (1024*1024):.1f} MB)",
                model_path=str(dest_path),
                sha256=sha_hex
            )
            if on_progress:
                on_progress(status)

            return dest_path

        except Exception as e:
            if on_progress:
                on_progress(ModelStatus(is_ready=False, is_downloading=False, message=f"Error: {e}"))
            raise

    def sideload_model(self, source_path: str, preset: Optional[ModelPreset] = None) -> Path:
        target_preset = preset or self.active_preset
        src = Path(source_path)
        if not src.exists() or src.stat().st_size < MIN_MODEL_SIZE_BYTES:
            raise ValueError(f"Sideloaded file is too small or invalid: {src}")

        dest = self.get_model_file_path(target_preset)
        shutil.copy2(src, dest)
        return dest
