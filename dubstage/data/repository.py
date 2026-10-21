"""
DubStage Repository - High-Level Data & File System Management
"""

import shutil
import uuid
from pathlib import Path
from typing import List, Optional
from ..config import get_projects_dir
from ..models import ProjectEntity, ClipEntity, TakeEntity
from .database import DubStageDatabase

class DubStageRepository:
    def __init__(self, db: Optional[DubStageDatabase] = None):
        self.db = db or DubStageDatabase()

    def get_project_dir(self, project_id: str) -> Path:
        pdir = get_projects_dir() / project_id
        pdir.mkdir(parents=True, exist_ok=True)
        return pdir

    def get_takes_dir(self, project_id: str) -> Path:
        tdir = self.get_project_dir(project_id) / "takes"
        tdir.mkdir(parents=True, exist_ok=True)
        return tdir

    def get_exports_dir(self, project_id: str) -> Path:
        edir = self.get_project_dir(project_id) / "exports"
        edir.mkdir(parents=True, exist_ok=True)
        return edir

    def create_project(self, title: str, video_uri: str, video_duration_ms: int, width: int = 1920, height: int = 1080) -> ProjectEntity:
        project_id = str(uuid.uuid4())
        pdir = self.get_project_dir(project_id)

        original_pcm = str(pdir / "original.pcm")
        vocals_wav = str(pdir / "vocals.wav")
        backing_wav = str(pdir / "backing.wav")

        project = ProjectEntity(
            id=project_id,
            title=title,
            video_uri=video_uri,
            video_duration_ms=video_duration_ms,
            video_width=width,
            video_height=height,
            original_pcm_path=original_pcm,
            vocals_wav_path=vocals_wav,
            backing_wav_path=backing_wav,
            status=ProjectEntity.STATUS_CREATED
        )

        self.db.insert_project(project)
        return project

    def update_project(self, project: ProjectEntity):
        self.db.insert_project(project)

    def get_project(self, project_id: str) -> Optional[ProjectEntity]:
        return self.db.get_project(project_id)

    def get_all_projects(self) -> List[ProjectEntity]:
        return self.db.get_all_projects()

    def delete_project(self, project_id: str):
        # Delete files on disk
        pdir = self.get_project_dir(project_id)
        if pdir.exists():
            shutil.rmtree(pdir, ignore_errors=True)
        # Delete from database (cascades to clips and takes)
        self.db.delete_project(project_id)

    # Clips
    def get_clips_for_project(self, project_id: str) -> List[ClipEntity]:
        return self.db.get_clips_for_project(project_id)

    def insert_clips(self, clips: List[ClipEntity]):
        self.db.insert_clips(clips)

    def replace_clips_for_project(self, project_id: str, clips: List[ClipEntity]):
        self.db.replace_clips_for_project(project_id, clips)

    def update_clip(self, clip: ClipEntity):
        self.db.update_clip(clip)

    def delete_clip(self, clip_id: str):
        self.db.delete_clip(clip_id)

    # Takes
    def get_takes_for_clip(self, clip_id: str) -> List[TakeEntity]:
        return self.db.get_takes_for_clip(clip_id)

    def get_all_takes_for_project(self, project_id: str) -> List[TakeEntity]:
        return self.db.get_all_takes_for_project(project_id)

    def insert_take(self, take: TakeEntity):
        self.db.insert_take(take)

    def update_take(self, take: TakeEntity):
        self.db.update_take(take)

    def delete_take(self, take: TakeEntity):
        # Remove audio file
        try:
            pcm_path = Path(take.pcm_file_path)
            if pcm_path.exists():
                pcm_path.unlink()
        except Exception:
            pass
        self.db.delete_take(take.id)
