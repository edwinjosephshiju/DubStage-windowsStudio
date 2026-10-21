"""
DubStage SQLite Database Manager
"""

import sqlite3
import threading
from pathlib import Path
from typing import List, Optional
from ..config import get_app_data_dir
from ..models import ProjectEntity, ClipEntity, TakeEntity

class DubStageDatabase:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = get_app_data_dir() / "dubstage.db"
        self.db_path = db_path
        self._local = threading.local()
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            self._local.conn = conn
        return self._local.conn

    def _init_tables(self):
        conn = self._get_connection()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    video_uri TEXT NOT NULL,
                    video_duration_ms INTEGER NOT NULL,
                    video_width INTEGER DEFAULT 1920,
                    video_height INTEGER DEFAULT 1080,
                    sample_rate INTEGER DEFAULT 44100,
                    channels INTEGER DEFAULT 2,
                    original_pcm_path TEXT,
                    vocals_wav_path TEXT,
                    backing_wav_path TEXT,
                    model_checksum TEXT,
                    status TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS clips (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    clip_index INTEGER NOT NULL,
                    start_ms INTEGER NOT NULL,
                    end_ms INTEGER NOT NULL,
                    speaker_name TEXT DEFAULT 'Speaker 1',
                    script_text TEXT DEFAULT '',
                    active_take_id TEXT,
                    is_muted INTEGER DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS takes (
                    id TEXT PRIMARY KEY,
                    clip_id TEXT NOT NULL,
                    take_number INTEGER NOT NULL,
                    pcm_file_path TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    gain_db REAL DEFAULT 0.0,
                    time_offset_ms INTEGER DEFAULT 0,
                    noise_gate_threshold_db REAL DEFAULT -60.0,
                    recorded_at INTEGER NOT NULL,
                    FOREIGN KEY(clip_id) REFERENCES clips(id) ON DELETE CASCADE
                );
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_clips_project ON clips(project_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_takes_clip ON takes(clip_id);")

    # Project Operations
    def insert_project(self, project: ProjectEntity):
        conn = self._get_connection()
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO projects (
                    id, title, video_uri, video_duration_ms, video_width, video_height,
                    sample_rate, channels, original_pcm_path, vocals_wav_path,
                    backing_wav_path, model_checksum, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.id, project.title, project.video_uri, project.video_duration_ms,
                project.video_width, project.video_height, project.sample_rate,
                project.channels, project.original_pcm_path, project.vocals_wav_path,
                project.backing_wav_path, project.model_checksum, project.status,
                project.created_at, project.updated_at
            ))

    def get_project(self, project_id: str) -> Optional[ProjectEntity]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
        if not row:
            return None
        return ProjectEntity(
            id=row["id"], title=row["title"], video_uri=row["video_uri"],
            video_duration_ms=row["video_duration_ms"], video_width=row["video_width"],
            video_height=row["video_height"], sample_rate=row["sample_rate"],
            channels=row["channels"], original_pcm_path=row["original_pcm_path"] or "",
            vocals_wav_path=row["vocals_wav_path"] or "",
            backing_wav_path=row["backing_wav_path"] or "",
            model_checksum=row["model_checksum"] or "", status=row["status"],
            created_at=row["created_at"], updated_at=row["updated_at"]
        )

    def get_all_projects(self) -> List[ProjectEntity]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM projects ORDER BY updated_at DESC")
        return [
            ProjectEntity(
                id=r["id"], title=r["title"], video_uri=r["video_uri"],
                video_duration_ms=r["video_duration_ms"], video_width=r["video_width"],
                video_height=r["video_height"], sample_rate=r["sample_rate"],
                channels=r["channels"], original_pcm_path=r["original_pcm_path"] or "",
                vocals_wav_path=r["vocals_wav_path"] or "",
                backing_wav_path=r["backing_wav_path"] or "",
                model_checksum=r["model_checksum"] or "", status=r["status"],
                created_at=r["created_at"], updated_at=r["updated_at"]
            )
            for r in cur.fetchall()
        ]

    def delete_project(self, project_id: str):
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    # Clip Operations
    def insert_clips(self, clips: List[ClipEntity]):
        conn = self._get_connection()
        with conn:
            for clip in clips:
                conn.execute("""
                    INSERT OR REPLACE INTO clips (
                        id, project_id, clip_index, start_ms, end_ms, speaker_name,
                        script_text, active_take_id, is_muted, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    clip.id, clip.project_id, clip.clip_index, clip.start_ms, clip.end_ms,
                    clip.speaker_name, clip.script_text, clip.active_take_id,
                    1 if clip.is_muted else 0, clip.created_at
                ))

    def update_clip(self, clip: ClipEntity):
        conn = self._get_connection()
        with conn:
            conn.execute("""
                UPDATE clips SET
                    clip_index = ?, start_ms = ?, end_ms = ?, speaker_name = ?,
                    script_text = ?, active_take_id = ?, is_muted = ?
                WHERE id = ?
            """, (
                clip.clip_index, clip.start_ms, clip.end_ms, clip.speaker_name,
                clip.script_text, clip.active_take_id, 1 if clip.is_muted else 0,
                clip.id
            ))

    def get_clips_for_project(self, project_id: str) -> List[ClipEntity]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM clips WHERE project_id = ? ORDER BY clip_index ASC", (project_id,))
        return [
            ClipEntity(
                id=r["id"], project_id=r["project_id"], clip_index=r["clip_index"],
                start_ms=r["start_ms"], end_ms=r["end_ms"], speaker_name=r["speaker_name"],
                script_text=r["script_text"], active_take_id=r["active_take_id"],
                is_muted=bool(r["is_muted"]), created_at=r["created_at"]
            )
            for r in cur.fetchall()
        ]

    def replace_clips_for_project(self, project_id: str, clips: List[ClipEntity]):
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM clips WHERE project_id = ?", (project_id,))
            for clip in clips:
                conn.execute("""
                    INSERT INTO clips (
                        id, project_id, clip_index, start_ms, end_ms, speaker_name,
                        script_text, active_take_id, is_muted, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    clip.id, clip.project_id, clip.clip_index, clip.start_ms, clip.end_ms,
                    clip.speaker_name, clip.script_text, clip.active_take_id,
                    1 if clip.is_muted else 0, clip.created_at
                ))

    def delete_clip(self, clip_id: str):
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM clips WHERE id = ?", (clip_id,))

    # Take Operations
    def insert_take(self, take: TakeEntity):
        conn = self._get_connection()
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO takes (
                    id, clip_id, take_number, pcm_file_path, duration_ms,
                    gain_db, time_offset_ms, noise_gate_threshold_db, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                take.id, take.clip_id, take.take_number, take.pcm_file_path,
                take.duration_ms, take.gain_db, take.time_offset_ms,
                take.noise_gate_threshold_db, take.recorded_at
            ))

    def update_take(self, take: TakeEntity):
        conn = self._get_connection()
        with conn:
            conn.execute("""
                UPDATE takes SET
                    take_number = ?, pcm_file_path = ?, duration_ms = ?,
                    gain_db = ?, time_offset_ms = ?, noise_gate_threshold_db = ?
                WHERE id = ?
            """, (
                take.take_number, take.pcm_file_path, take.duration_ms,
                take.gain_db, take.time_offset_ms, take.noise_gate_threshold_db,
                take.id
            ))

    def get_takes_for_clip(self, clip_id: str) -> List[TakeEntity]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM takes WHERE clip_id = ? ORDER BY take_number ASC", (clip_id,))
        return [
            TakeEntity(
                id=r["id"], clip_id=r["clip_id"], take_number=r["take_number"],
                pcm_file_path=r["pcm_file_path"], duration_ms=r["duration_ms"],
                gain_db=r["gain_db"], time_offset_ms=r["time_offset_ms"],
                noise_gate_threshold_db=r["noise_gate_threshold_db"],
                recorded_at=r["recorded_at"]
            )
            for r in cur.fetchall()
        ]

    def get_all_takes_for_project(self, project_id: str) -> List[TakeEntity]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT t.* FROM takes t
            JOIN clips c ON t.clip_id = c.id
            WHERE c.project_id = ?
            ORDER BY t.recorded_at ASC
        """, (project_id,))
        return [
            TakeEntity(
                id=r["id"], clip_id=r["clip_id"], take_number=r["take_number"],
                pcm_file_path=r["pcm_file_path"], duration_ms=r["duration_ms"],
                gain_db=r["gain_db"], time_offset_ms=r["time_offset_ms"],
                noise_gate_threshold_db=r["noise_gate_threshold_db"],
                recorded_at=r["recorded_at"]
            )
            for r in cur.fetchall()
        ]

    def delete_take(self, take_id: str):
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM takes WHERE id = ?", (take_id,))
