"""
DubStage DubForge Workspace
Video Ingestion, Demucs v4 Neural Stem Separation, Acoustic VAD Detection, Dialogue Cue & Script Editor
"""

import os
import threading
from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..components import ModelDownloaderCard, VideoMonitor, WaveformCanvas
from ..theme import format_timecode, parse_timecode
from ...data.repository import DubStageRepository
from ...engine import (
    AudioExtractionEngine,
    DemucsOnnxSeparationEngine,
    ModelManager,
    VadEngine,
)
from ...models import ClipEntity, ProjectEntity

class ForgeView(QWidget):
    project_updated = pyqtSignal(ProjectEntity)
    clip_selected = pyqtSignal(str)
    request_switch_to_stage = pyqtSignal()

    def __init__(
        self,
        repository: DubStageRepository,
        model_manager: ModelManager,
        video_monitor: VideoMonitor,
        waveform_canvas: WaveformCanvas,
        parent=None
    ):
        super().__init__(parent)
        self.repository = repository
        self.model_manager = model_manager
        self.video_monitor = video_monitor
        self.waveform_canvas = waveform_canvas

        self.audio_extractor = AudioExtractionEngine()
        self.demucs_engine = DemucsOnnxSeparationEngine()
        self.vad_engine = VadEngine()

        self._active_project: Optional[ProjectEntity] = None
        self._clips: List[ClipEntity] = []
        self._active_clip: Optional[ClipEntity] = None

        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #1F2432; width: 4px; }")

        # Left Column: Video, Separation, VAD
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Video Monitor Container
        left_layout.addWidget(self.video_monitor, 3)

        # Video Import & Project Info Bar
        info_bar = QFrame()
        info_bar.setStyleSheet("background-color: #161922; border: 1px solid #232736; border-radius: 6px; padding: 6px;")
        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(8, 4, 8, 4)

        self.project_title_lbl = QLabel("No Video Loaded")
        self.project_title_lbl.setStyleSheet("font-weight: 700; color: #F1F5F9; font-size: 13px;")
        info_layout.addWidget(self.project_title_lbl)

        info_layout.addStretch()

        self.import_btn = QPushButton("Import Video (Ctrl+O)")
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #242938;
                border: 1px solid #3B435C;
                color: #F1F5F9;
                font-weight: 600;
                padding: 6px 14px;
            }
            QPushButton:hover { background-color: #31384D; }
        """)
        self.import_btn.clicked.connect(self.prompt_import_video)
        info_layout.addWidget(self.import_btn)

        left_layout.addWidget(info_bar)

        # Model Downloader Card
        self.model_card = ModelDownloaderCard(self.model_manager)
        left_layout.addWidget(self.model_card)

        # Stem Separation Card
        sep_card = QFrame()
        sep_card.setStyleSheet("background-color: #161922; border: 1px solid #232736; border-radius: 8px; padding: 10px;")
        sep_layout = QVBoxLayout(sep_card)
        sep_layout.setContentsMargins(12, 8, 12, 8)
        sep_layout.setSpacing(8)

        sep_header = QHBoxLayout()
        sep_title = QLabel("Demucs v4 Neural Stem Separation")
        sep_title.setStyleSheet("font-weight: 700; color: #F1F5F9;")
        sep_header.addWidget(sep_title)

        sep_header.addStretch()

        self.sep_status_lbl = QLabel("Ready")
        self.sep_status_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        sep_header.addWidget(self.sep_status_lbl)
        sep_layout.addLayout(sep_header)

        self.sep_progress = QProgressBar()
        self.sep_progress.setVisible(False)
        sep_layout.addWidget(self.sep_progress)

        sep_btn_row = QHBoxLayout()
        self.separate_btn = QPushButton("Separate Stems (Ctrl+D)")
        self.separate_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B5CF6;
                color: #FFFFFF;
                font-weight: 700;
                padding: 8px 18px;
            }
            QPushButton:hover { background-color: #7C3AED; }
            QPushButton:disabled { background-color: #222634; color: #555E75; }
        """)
        self.separate_btn.clicked.connect(self.start_demucs_separation)
        self.separate_btn.setEnabled(False)
        sep_btn_row.addWidget(self.separate_btn)

        self.cancel_sep_btn = QPushButton("Cancel")
        self.cancel_sep_btn.setVisible(False)
        self.cancel_sep_btn.clicked.connect(self.demucs_engine.cancel)
        sep_btn_row.addWidget(self.cancel_sep_btn)

        sep_btn_row.addStretch()
        sep_layout.addLayout(sep_btn_row)

        left_layout.addWidget(sep_card)

        # Acoustic VAD Card
        vad_card = QFrame()
        vad_card.setStyleSheet("background-color: #161922; border: 1px solid #232736; border-radius: 8px; padding: 10px;")
        vad_layout = QVBoxLayout(vad_card)
        vad_layout.setContentsMargins(12, 8, 12, 8)
        vad_layout.setSpacing(8)

        vad_header = QHBoxLayout()
        vad_title = QLabel("Acoustic Dialogue Cue Detection (VAD)")
        vad_title.setStyleSheet("font-weight: 700; color: #F1F5F9;")
        vad_header.addWidget(vad_title)

        vad_header.addStretch()

        self.vad_sens_label = QLabel("Sensitivity: 60%")
        self.vad_sens_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        vad_header.addWidget(self.vad_sens_label)
        vad_layout.addLayout(vad_header)

        # Sensitivity Slider
        self.vad_slider = QSlider(Qt.Orientation.Horizontal)
        self.vad_slider.setRange(10, 100)
        self.vad_slider.setValue(60)
        self.vad_slider.valueChanged.connect(lambda v: self.vad_sens_label.setText(f"Sensitivity: {v}%"))
        vad_layout.addWidget(self.vad_slider)

        vad_btn_row = QHBoxLayout()
        self.run_vad_btn = QPushButton("Detect Dialogue Cues (Ctrl+Shift+V)")
        self.run_vad_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: 700;
                padding: 6px 16px;
            }
            QPushButton:hover { background-color: #059669; }
            QPushButton:disabled { background-color: #222634; color: #555E75; }
        """)
        self.run_vad_btn.clicked.connect(self.run_auto_vad)
        self.run_vad_btn.setEnabled(False)
        vad_btn_row.addWidget(self.run_vad_btn)

        vad_btn_row.addStretch()
        vad_layout.addLayout(vad_btn_row)

        left_layout.addWidget(vad_card)

        splitter.addWidget(left_widget)

        # Right Column: Dialogue Cues & Script List
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Header
        cue_header_card = QFrame()
        cue_header_card.setStyleSheet("background-color: #161922; border: 1px solid #232736; border-radius: 6px;")
        cue_hdr_layout = QHBoxLayout(cue_header_card)
        cue_hdr_layout.setContentsMargins(12, 8, 12, 8)

        cue_title = QLabel("Dialogue Cues & Script Lines")
        cue_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #F1F5F9;")
        cue_hdr_layout.addWidget(cue_title)

        cue_hdr_layout.addStretch()

        self.cue_count_lbl = QLabel("0 Cues")
        self.cue_count_lbl.setStyleSheet("color: #94A3B8; font-weight: 600;")
        cue_hdr_layout.addWidget(self.cue_count_lbl)

        right_layout.addWidget(cue_header_card)

        # Cue Table
        self.cue_table = QTableWidget()
        self.cue_table.setColumnCount(5)
        self.cue_table.setHorizontalHeaderLabels(["#", "Speaker", "Timecode", "Duration", "Script Text"])
        self.cue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.cue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.cue_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.cue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.cue_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.cue_table.verticalHeader().setVisible(False)
        self.cue_table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.cue_table.itemChanged.connect(self._on_table_item_changed)
        right_layout.addWidget(self.cue_table, 1)

        # Cue Action Toolbar
        action_bar = QFrame()
        action_bar.setStyleSheet("background-color: #161922; border: 1px solid #232736; border-radius: 6px;")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(8, 6, 8, 6)

        self.slice_btn = QPushButton("Slice at Playhead (S)")
        self.slice_btn.clicked.connect(self.slice_clip_at_playhead)
        action_layout.addWidget(self.slice_btn)

        self.add_cue_btn = QPushButton("+ Manual Cue")
        self.add_cue_btn.clicked.connect(self.add_manual_cue)
        action_layout.addWidget(self.add_cue_btn)

        self.del_cue_btn = QPushButton("Delete Cue")
        self.del_cue_btn.clicked.connect(self.delete_selected_cue)
        action_layout.addWidget(self.del_cue_btn)

        action_layout.addStretch()

        self.to_stage_btn = QPushButton("Open in DubStage ➔")
        self.to_stage_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B5CF6;
                color: #FFFFFF;
                font-weight: 700;
                padding: 6px 16px;
            }
            QPushButton:hover { background-color: #7C3AED; }
        """)
        self.to_stage_btn.clicked.connect(lambda: self.request_switch_to_stage.emit())
        action_layout.addWidget(self.to_stage_btn)

        right_layout.addWidget(action_bar)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)

        main_layout.addWidget(splitter)

    def set_project(self, project: ProjectEntity):
        self._active_project = project
        self.project_title_lbl.setText(project.title)
        self.video_monitor.load_video(project.video_uri, project.video_width, project.video_height)
        self.waveform_canvas.set_duration(project.video_duration_ms)

        # Enable actions
        self.separate_btn.setEnabled(bool(project.original_pcm_path and os.path.exists(project.original_pcm_path)))
        has_stems = bool(project.vocals_wav_path and os.path.exists(project.vocals_wav_path))
        self.run_vad_btn.setEnabled(has_stems or bool(project.original_pcm_path and os.path.exists(project.original_pcm_path)))

        self.load_clips()

    def prompt_import_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File to Ingest",
            "",
            "Video Files (*.mp4 *.mkv *.mov *.avi *.webm);;All Files (*.*)"
        )
        if file_path:
            self.import_video(file_path)

    def import_video(self, video_path: str):
        title = Path(video_path).stem
        duration_ms, width, height = self.audio_extractor.probe_video(video_path)

        project = self.repository.create_project(
            title=title,
            video_uri=video_path,
            video_duration_ms=duration_ms,
            width=width,
            height=height
        )

        self.set_project(project)
        self.project_updated.emit(project)

        # Background extraction
        self.sep_status_lbl.setText("Extracting 44.1kHz stereo audio...")
        self.sep_progress.setVisible(True)
        self.sep_progress.setValue(10)

        def worker():
            try:
                res = self.audio_extractor.extract_and_decode_audio(
                    video_path,
                    project.original_pcm_path,
                    on_progress=lambda pct, msg: self.sep_progress.setValue(pct)
                )
                self.waveform_canvas.set_reference_peaks(res.waveform_peaks)
                project.status = ProjectEntity.STATUS_AUDIO_EXTRACTED
                project.video_duration_ms = res.duration_ms
                self.repository.update_project(project)
                self.set_project(project)
                self.sep_status_lbl.setText("Audio extracted.")
            except Exception as e:
                self.sep_status_lbl.setText(f"Extraction error: {e}")
            finally:
                self.sep_progress.setVisible(False)

        threading.Thread(target=worker, daemon=True).start()

    def start_demucs_separation(self):
        if not self._active_project:
            return

        model_status = self.model_manager.check_status()
        if not model_status.is_ready:
            QMessageBox.warning(self, "Model Missing", "Demucs ONNX model not found. Please download or sideload it first.")
            return

        self.separate_btn.setEnabled(False)
        self.cancel_sep_btn.setVisible(True)
        self.sep_progress.setVisible(True)
        self.sep_progress.setValue(0)
        self.sep_status_lbl.setText("Separating stems via ONNX Runtime...")

        proj = self._active_project

        def progress_callback(prog):
            self.sep_progress.setValue(prog.percent)
            self.sep_status_lbl.setText(f"Chunk {prog.current_chunk}/{prog.total_chunks} ({prog.percent}%) - ETA {prog.eta_seconds}s")

        def worker():
            try:
                res = self.demucs_engine.separate_stems(
                    model_path=model_status.model_path,
                    input_pcm_path=proj.original_pcm_path,
                    output_vocals_wav=proj.vocals_wav_path,
                    output_backing_wav=proj.backing_wav_path,
                    preset=self.model_manager.active_preset,
                    karaoke_mode=self.model_manager.active_karaoke_mode,
                    backend=self.model_manager.active_backend,
                    on_progress=progress_callback
                )
                self.waveform_canvas.set_reference_peaks(res.vocal_peaks)
                proj.status = ProjectEntity.STATUS_SEPARATED
                self.repository.update_project(proj)
                self.set_project(proj)
                self.sep_status_lbl.setText("Separation complete.")
                # Run automatic initial VAD
                self.run_auto_vad()
            except Exception as e:
                self.sep_status_lbl.setText(f"Separation failed: {e}")
            finally:
                self.separate_btn.setEnabled(True)
                self.cancel_sep_btn.setVisible(False)
                self.sep_progress.setVisible(False)

        threading.Thread(target=worker, daemon=True).start()

    def run_auto_vad(self):
        if not self._active_project:
            return

        proj = self._active_project
        audio_file = proj.vocals_wav_path if (proj.vocals_wav_path and os.path.exists(proj.vocals_wav_path)) else proj.original_pcm_path
        is_wav = audio_file.endswith(".wav")

        sensitivity = self.vad_slider.value() / 100.0

        def worker():
            detected = self.vad_engine.detect_dialogue_clips(audio_file, is_wav_file=is_wav, sensitivity=sensitivity)
            if detected:
                new_clips = [
                    ClipEntity(
                        id=d.id,
                        project_id=proj.id,
                        clip_index=d.clip_index,
                        start_ms=d.start_ms,
                        end_ms=d.end_ms,
                        speaker_name=d.speaker_name,
                        script_text=""
                    )
                    for d in detected
                ]
                self.repository.replace_clips_for_project(proj.id, new_clips)
                self.load_clips()

        threading.Thread(target=worker, daemon=True).start()

    def load_clips(self):
        if not self._active_project:
            return
        self._clips = self.repository.get_clips_for_project(self._active_project.id)
        self.waveform_canvas.set_clips(self._clips, self._active_clip.id if self._active_clip else None)
        self.cue_count_lbl.setText(f"{len(self._clips)} Cues")

        self.cue_table.blockSignals(True)
        self.cue_table.setRowCount(len(self._clips))

        for row, clip in enumerate(self._clips):
            item_idx = QTableWidgetItem(f"#{clip.clip_index}")
            item_idx.setFlags(item_idx.flags() & ~Qt.ItemFlag.ItemIsEditable)

            item_speaker = QTableWidgetItem(clip.speaker_name)
            item_tc = QTableWidgetItem(f"{format_timecode(clip.start_ms)} - {format_timecode(clip.end_ms)}")
            item_tc.setFlags(item_tc.flags() & ~Qt.ItemFlag.ItemIsEditable)

            dur_ms = clip.end_ms - clip.start_ms
            item_dur = QTableWidgetItem(f"{dur_ms / 1000.0:.2f}s")
            item_dur.setFlags(item_dur.flags() & ~Qt.ItemFlag.ItemIsEditable)

            item_script = QTableWidgetItem(clip.script_text)

            self.cue_table.setItem(row, 0, item_idx)
            self.cue_table.setItem(row, 1, item_speaker)
            self.cue_table.setItem(row, 2, item_tc)
            self.cue_table.setItem(row, 3, item_dur)
            self.cue_table.setItem(row, 4, item_script)

        self.cue_table.blockSignals(False)

    def _on_table_selection_changed(self):
        rows = self.cue_table.selectedIndexes()
        if rows:
            idx = rows[0].row()
            if 0 <= idx < len(self._clips):
                self._active_clip = self._clips[idx]
                self.video_monitor.seek(self._active_clip.start_ms)
                self.waveform_canvas.set_playhead(self._active_clip.start_ms)
                self.waveform_canvas.set_clips(self._clips, self._active_clip.id)
                self.clip_selected.emit(self._active_clip.id)

    def _on_table_item_changed(self, item: QTableWidgetItem):
        row = item.row()
        col = item.column()
        if 0 <= row < len(self._clips):
            clip = self._clips[row]
            if col == 1:
                clip.speaker_name = item.text().strip()
                self.repository.update_clip(clip)
            elif col == 4:
                clip.script_text = item.text().strip()
                self.repository.update_clip(clip)

    def slice_clip_at_playhead(self):
        if not self._active_clip or not self._active_project:
            return

        playhead_ms = self.waveform_canvas._playhead_ms
        active = self._active_clip

        if not (active.start_ms + 50 <= playhead_ms <= active.end_ms - 50):
            playhead_ms = (active.start_ms + active.end_ms) // 2

        import uuid
        old_end = active.end_ms
        active.end_ms = playhead_ms
        self.repository.update_clip(active)

        new_clip = ClipEntity(
            id=str(uuid.uuid4()),
            project_id=self._active_project.id,
            clip_index=active.clip_index + 1,
            start_ms=playhead_ms,
            end_ms=old_end,
            speaker_name=active.speaker_name,
            script_text=""
        )

        all_clips = self.repository.get_clips_for_project(self._active_project.id)
        # reindex
        reindexed = []
        for i, c in enumerate(all_clips):
            c.clip_index = i + 1
            reindexed.append(c)

        self.repository.replace_clips_for_project(self._active_project.id, reindexed)
        self.load_clips()

    def add_manual_cue(self):
        if not self._active_project:
            return
        import uuid
        playhead_ms = self.waveform_canvas._playhead_ms
        new_clip = ClipEntity(
            id=str(uuid.uuid4()),
            project_id=self._active_project.id,
            clip_index=len(self._clips) + 1,
            start_ms=playhead_ms,
            end_ms=min(self._active_project.video_duration_ms, playhead_ms + 3000),
            speaker_name="Speaker 1",
            script_text=""
        )
        self.repository.insert_clips([new_clip])
        self.load_clips()

    def delete_selected_cue(self):
        if self._active_clip:
            self.repository.delete_clip(self._active_clip.id)
            self._active_clip = None
            self.load_clips()
