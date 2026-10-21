"""
DubStage DubStage Workspace
Hardware Recording Booth, Dual-Waveform Sync, Multi-Take Audition Deck, and Master MP4 Exporter
"""

import os
import threading
import time
import uuid
from pathlib import Path
from typing import List, Optional
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..components import VideoMonitor, VuMeter, WaveformCanvas
from ..theme import format_timecode
from ...data.repository import DubStageRepository
from ...engine import (
    AudioRecordingEngine,
    Mp4ExportMuxer,
    MuxerExportProgress,
    PcmSoftwareMixerEngine,
)
from ...models import ClipEntity, MixTakeTrack, ProjectEntity, StudioAuditionMode, TakeEntity

class StageView(QWidget):
    project_updated = pyqtSignal(ProjectEntity)

    def __init__(
        self,
        repository: DubStageRepository,
        video_monitor: VideoMonitor,
        waveform_canvas: WaveformCanvas,
        mixer_engine: PcmSoftwareMixerEngine,
        parent=None
    ):
        super().__init__(parent)
        self.repository = repository
        self.video_monitor = video_monitor
        self.waveform_canvas = waveform_canvas
        self.mixer_engine = mixer_engine
        self.recording_engine = AudioRecordingEngine()
        self.mp4_muxer = Mp4ExportMuxer()

        self._active_project: Optional[ProjectEntity] = None
        self._clips: List[ClipEntity] = []
        self._active_clip: Optional[ClipEntity] = None
        self._takes: List[TakeEntity] = []
        self._active_take: Optional[TakeEntity] = None

        self._audition_mode = StudioAuditionMode.FULL_DUB_MIX
        self._backing_gain_db = 0.0

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        # Upper Section: Splitter with Video Monitor & Waveform Canvas
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.setStyleSheet("QSplitter::handle { background-color: #1F2432; width: 4px; }")

        top_splitter.addWidget(self.video_monitor)

        # Waveform card wrapper
        wave_card = QFrame()
        wave_card.setStyleSheet("background-color: #12151D; border: 1px solid #232736; border-radius: 8px;")
        wave_layout = QVBoxLayout(wave_card)
        wave_layout.setContentsMargins(8, 8, 8, 8)
        wave_layout.addWidget(self.waveform_canvas)

        top_splitter.addWidget(wave_card)
        top_splitter.setStretchFactor(0, 4)
        top_splitter.setStretchFactor(1, 6)

        main_layout.addWidget(top_splitter, 3)

        # Middle Section: Recording & Live Monitor Deck
        record_card = QFrame()
        record_card.setStyleSheet("background-color: #161922; border: 1px solid #232736; border-radius: 8px;")
        rec_layout = QHBoxLayout(record_card)
        rec_layout.setContentsMargins(16, 10, 16, 10)
        rec_layout.setSpacing(16)

        # Countdown Overlay Display
        self.countdown_lbl = QLabel("")
        self.countdown_lbl.setStyleSheet("font-size: 24px; font-weight: 900; color: #EF4444; min-width: 40px;")
        rec_layout.addWidget(self.countdown_lbl)

        # Record Take Button (R)
        self.record_btn = QPushButton("● RECORD TAKE (R)")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: 800;
                font-size: 13px;
                padding: 10px 24px;
                border-radius: 6px;
                border: 1px solid #EF4444;
            }
            QPushButton:hover { background-color: #B91C1C; }
        """)
        self.record_btn.clicked.connect(self.toggle_record_take)
        rec_layout.addWidget(self.record_btn)

        # Play / Pause Button (Space)
        self.play_btn = QPushButton("▶ PLAY (Space)")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: 700;
                padding: 10px 20px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        self.play_btn.clicked.connect(self.toggle_playback)
        rec_layout.addWidget(self.play_btn)

        # Live VU Meter
        vu_box = QVBoxLayout()
        vu_lbl = QLabel("MIC INPUT LEVEL")
        vu_lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B;")
        vu_box.addWidget(vu_lbl)

        self.vu_meter = VuMeter()
        vu_box.addWidget(self.vu_meter)
        rec_layout.addLayout(vu_box, 1)

        # Audition Mode Selector
        mode_box = QVBoxLayout()
        mode_lbl = QLabel("AUDITION MODE (1-6)")
        mode_lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B;")
        mode_box.addWidget(mode_lbl)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("1. Full Dub Mix (Backing + Takes)", StudioAuditionMode.FULL_DUB_MIX)
        self.mode_combo.addItem("2. Original + Residual Backing", StudioAuditionMode.ORIGINAL_WITH_RESIDUAL)
        self.mode_combo.addItem("3. Recorded Take + Residual Backing", StudioAuditionMode.RECORDED_WITH_RESIDUAL)
        self.mode_combo.addItem("4. Solo Original Vocals", StudioAuditionMode.SOLO_ORIGINAL)
        self.mode_combo.addItem("5. Solo Active Take", StudioAuditionMode.SOLO_ACTIVE_TAKE)
        self.mode_combo.addItem("6. Backing Only (Karaoke)", StudioAuditionMode.BACKING_ONLY)
        self.mode_combo.currentIndexChanged.connect(self._on_audition_mode_changed)
        mode_box.addWidget(self.mode_combo)
        rec_layout.addLayout(mode_box)

        # Backing Gain Slider
        gain_box = QVBoxLayout()
        self.gain_lbl = QLabel("Backing: 0.0 dB")
        self.gain_lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B;")
        gain_box.addWidget(self.gain_lbl)

        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(-24, 6)
        self.gain_slider.setValue(0)
        self.gain_slider.valueChanged.connect(self._on_backing_gain_changed)
        gain_box.addWidget(self.gain_slider)
        rec_layout.addLayout(gain_box)

        main_layout.addWidget(record_card)

        # Bottom Section: Multi-Take Selection & Audition Deck
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        bottom_splitter.setStyleSheet("QSplitter::handle { background-color: #1F2432; width: 4px; }")

        # Left: Cue Info & Takes List
        takes_card = QFrame()
        takes_card.setStyleSheet("background-color: #161922; border: 1px solid #232736; border-radius: 8px;")
        takes_layout = QVBoxLayout(takes_card)
        takes_layout.setContentsMargins(12, 10, 12, 10)
        takes_layout.setSpacing(8)

        self.cue_info_lbl = QLabel("Active Cue: None")
        self.cue_info_lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #8B5CF6;")
        takes_layout.addWidget(self.cue_info_lbl)

        self.script_display = QLabel("No script text recorded for this cue.")
        self.script_display.setWordWrap(True)
        self.script_display.setStyleSheet("color: #F1F5F9; font-size: 12px; background-color: #12151D; padding: 6px; border-radius: 4px;")
        takes_layout.addWidget(self.script_display)

        takes_layout.addWidget(QLabel("Recorded Takes:"))
        self.takes_list = QListWidget()
        self.takes_list.itemSelectionChanged.connect(self._on_take_selected)
        takes_layout.addWidget(self.takes_list, 1)

        bottom_splitter.addWidget(takes_card)

        # Right: Take Tuning & Master Export Deck
        tuning_card = QFrame()
        tuning_card.setStyleSheet("background-color: #161922; border: 1px solid #232736; border-radius: 8px;")
        tuning_layout = QVBoxLayout(tuning_card)
        tuning_layout.setContentsMargins(14, 10, 14, 10)
        tuning_layout.setSpacing(12)

        tune_title = QLabel("Take Alignment & Tuning")
        tune_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #F1F5F9;")
        tuning_layout.addWidget(tune_title)

        # Take Gain Slider
        gain_row = QHBoxLayout()
        self.take_gain_lbl = QLabel("Take Gain: 0.0 dB")
        self.take_gain_lbl.setStyleSheet("color: #94A3B8; font-weight: 600;")
        gain_row.addWidget(self.take_gain_lbl)

        self.take_gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.take_gain_slider.setRange(-12, 12)
        self.take_gain_slider.setValue(0)
        self.take_gain_slider.valueChanged.connect(self._on_take_gain_changed)
        gain_row.addWidget(self.take_gain_slider, 1)
        tuning_layout.addLayout(gain_row)

        # Time Slip Offset Slider
        slip_row = QHBoxLayout()
        self.take_slip_lbl = QLabel("Time Slip: 0 ms")
        self.take_slip_lbl.setStyleSheet("color: #94A3B8; font-weight: 600;")
        slip_row.addWidget(self.take_slip_lbl)

        self.take_slip_slider = QSlider(Qt.Orientation.Horizontal)
        self.take_slip_slider.setRange(-200, 200)
        self.take_slip_slider.setValue(0)
        self.take_slip_slider.valueChanged.connect(self._on_take_slip_changed)
        slip_row.addWidget(self.take_slip_slider, 1)
        tuning_layout.addLayout(slip_row)

        # Action Buttons
        take_btn_row = QHBoxLayout()
        self.set_active_take_btn = QPushButton("★ Set as Master Take")
        self.set_active_take_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B5CF6;
                color: #FFFFFF;
                font-weight: 700;
                padding: 6px 14px;
            }
            QPushButton:hover { background-color: #7C3AED; }
        """)
        self.set_active_take_btn.clicked.connect(self.set_selected_take_active)
        take_btn_row.addWidget(self.set_active_take_btn)

        self.del_take_btn = QPushButton("Delete Take (Del)")
        self.del_take_btn.clicked.connect(self.delete_selected_take)
        take_btn_row.addWidget(self.del_take_btn)

        take_btn_row.addStretch()
        tuning_layout.addLayout(take_btn_row)

        tuning_layout.addStretch()

        # Master Export MP4 Button
        self.export_btn = QPushButton("🎬 EXPORT MASTER MP4 & SUBTITLES (Ctrl+E)")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 800;
                padding: 12px 24px;
                border-radius: 6px;
                border: 1px solid #34D399;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        self.export_btn.clicked.connect(self.export_master_mp4)
        tuning_layout.addWidget(self.export_btn)

        bottom_splitter.addWidget(tuning_card)
        bottom_splitter.setStretchFactor(0, 5)
        bottom_splitter.setStretchFactor(1, 5)

        main_layout.addWidget(bottom_splitter, 2)

    def set_project(self, project: ProjectEntity):
        self._active_project = project
        self.load_clips()

    def set_active_clip(self, clip_id: str):
        clip = next((c for c in self._clips if c.id == clip_id), None)
        if clip:
            self._active_clip = clip
            self.cue_info_lbl.setText(f"Active Cue: #{clip.clip_index} - {clip.speaker_name} ({format_timecode(clip.start_ms)} to {format_timecode(clip.end_ms)})")
            self.script_display.setText(clip.script_text.strip() or "[No script dialogue written]")
            self.load_takes_for_clip(clip.id)

    def load_clips(self):
        if not self._active_project:
            return
        self._clips = self.repository.get_clips_for_project(self._active_project.id)
        if self._clips and not self._active_clip:
            self.set_active_clip(self._clips[0].id)

    def load_takes_for_clip(self, clip_id: str):
        self._takes = self.repository.get_takes_for_clip(clip_id)
        self.takes_list.clear()

        active_id = self._active_clip.active_take_id if self._active_clip else None
        active_idx = -1

        for idx, t in enumerate(self._takes):
            is_master = (t.id == active_id)
            star = "★ " if is_master else "   "
            item_text = f"{star}Take #{t.take_number}  ({t.duration_ms / 1000.0:.2f}s)  Gain: {t.gain_db:+.1f}dB  Offset: {t.time_offset_ms:+d}ms"
            item = QListWidgetItem(item_text)
            self.takes_list.addItem(item)
            if is_master:
                active_idx = idx

        if active_idx >= 0:
            self.takes_list.setCurrentRow(active_idx)
        elif self._takes:
            self.takes_list.setCurrentRow(len(self._takes) - 1)

    def _on_take_selected(self):
        row = self.takes_list.currentRow()
        if 0 <= row < len(self._takes):
            self._active_take = self._takes[row]
            self.take_gain_slider.blockSignals(True)
            self.take_gain_slider.setValue(int(self._active_take.gain_db))
            self.take_gain_lbl.setText(f"Take Gain: {self._active_take.gain_db:+.1f} dB")
            self.take_gain_slider.blockSignals(False)

            self.take_slip_slider.blockSignals(True)
            self.take_slip_slider.setValue(self._active_take.time_offset_ms)
            self.take_slip_lbl.setText(f"Time Slip: {self._active_take.time_offset_ms:+d} ms")
            self.take_slip_slider.blockSignals(False)

    def _on_take_gain_changed(self, value: int):
        if self._active_take:
            self._active_take.gain_db = float(value)
            self.take_gain_lbl.setText(f"Take Gain: {self._active_take.gain_db:+.1f} dB")
            self.repository.update_take(self._active_take)
            self.load_takes_for_clip(self._active_take.clip_id)

    def _on_take_slip_changed(self, value: int):
        if self._active_take:
            self._active_take.time_offset_ms = value
            self.take_slip_lbl.setText(f"Time Slip: {self._active_take.time_offset_ms:+d} ms")
            self.repository.update_take(self._active_take)
            self.load_takes_for_clip(self._active_take.clip_id)

    def set_selected_take_active(self):
        if self._active_clip and self._active_take:
            self._active_clip.active_take_id = self._active_take.id
            self.repository.update_clip(self._active_clip)
            self.load_takes_for_clip(self._active_clip.id)

    def delete_selected_take(self):
        if self._active_take:
            self.repository.delete_take(self._active_take)
            self._active_take = None
            if self._active_clip:
                self.load_takes_for_clip(self._active_clip.id)

    def toggle_record_take(self):
        if self.recording_engine.is_recording:
            self.recording_engine.stop_recording()
            self.record_btn.setText("● RECORD TAKE (R)")
            self.record_btn.setStyleSheet("background-color: #DC2626; color: #FFFFFF;")
            self.countdown_lbl.setText("")
            return

        if not self._active_clip or not self._active_project:
            QMessageBox.warning(self, "No Clip Selected", "Select a dialogue cue before recording a take.")
            return

        clip = self._active_clip
        proj = self._active_project
        scene_duration_ms = max(500, clip.end_ms - clip.start_ms)

        # 3-Second Pre-Roll Countdown in Worker Thread
        def run_pre_roll_and_record():
            # Seek 1.5s prior
            cue_context_start = max(0, clip.start_ms - 1500)
            self.video_monitor.seek(cue_context_start)
            self.waveform_canvas.set_playhead(cue_context_start)

            for count in [3, 2, 1]:
                self.countdown_lbl.setText(str(count))
                time.sleep(1.0)

            self.countdown_lbl.setText("REC")
            self.record_btn.setText("■ STOP RECORDING (R)")
            self.record_btn.setStyleSheet("background-color: #EF4444; color: #FFFFFF; border: 2px solid #FCA5A5;")

            # Play backing simultaneously for headphone monitoring
            self.mixer_engine.play_mix(
                backing_wav_path=proj.backing_wav_path,
                original_vocals_wav_path=None,
                takes=[],
                start_position_ms=clip.start_ms,
                end_position_ms=clip.end_ms,
                audition_mode=StudioAuditionMode.BACKING_ONLY
            )

            # Record
            take_id = str(uuid.uuid4())
            takes_dir = self.repository.get_takes_dir(proj.id)
            take_path = str(takes_dir / f"take_{take_id}.pcm")

            res = self.recording_engine.record_take(
                output_file_path=take_path,
                max_duration_ms=scene_duration_ms,
                on_rms_db=lambda db: self.vu_meter.set_level(db),
                on_peak_sample=lambda p: None
            )

            self.mixer_engine.stop()
            self.countdown_lbl.setText("")
            self.record_btn.setText("● RECORD TAKE (R)")
            self.record_btn.setStyleSheet("background-color: #DC2626; color: #FFFFFF;")
            self.vu_meter.set_level(-60.0)

            # Save take
            next_num = len(self._takes) + 1
            new_take = TakeEntity(
                id=take_id,
                clip_id=clip.id,
                take_number=next_num,
                pcm_file_path=take_path,
                duration_ms=res.duration_ms
            )
            self.repository.insert_take(new_take)

            # Auto-set as master take
            clip.active_take_id = new_take.id
            self.repository.update_clip(clip)

            self.waveform_canvas.set_take_peaks(res.peaks)
            self.load_takes_for_clip(clip.id)

        threading.Thread(target=run_pre_roll_and_record, daemon=True).start()

    def toggle_playback(self):
        if self.mixer_engine.is_playing:
            self.mixer_engine.stop()
            self.video_monitor.pause()
            self.play_btn.setText("▶ PLAY (Space)")
            self.play_btn.setStyleSheet("background-color: #10B981; color: #FFFFFF;")
        else:
            if not self._active_project:
                return

            proj = self._active_project
            current_ms = self.waveform_canvas._playhead_ms

            # Gather active takes
            all_takes = self.repository.get_all_takes_for_project(proj.id)
            mix_tracks = []
            for t in all_takes:
                parent_clip = next((c for c in self._clips if c.id == t.clip_id), None)
                if parent_clip and (parent_clip.active_take_id == t.id or (self._active_take and self._active_take.id == t.id)):
                    mix_tracks.append(
                        MixTakeTrack(
                            take_id=t.id,
                            pcm_file_path=t.pcm_file_path,
                            start_ms=parent_clip.start_ms,
                            duration_ms=t.duration_ms,
                            gain_db=t.gain_db,
                            time_offset_ms=t.time_offset_ms
                        )
                    )

            # Start video muted
            self.video_monitor.set_muted(True)
            self.video_monitor.seek(current_ms)
            self.video_monitor.play()

            self.play_btn.setText("❚❚ PAUSE (Space)")
            self.play_btn.setStyleSheet("background-color: #F59E0B; color: #FFFFFF;")

            self.mixer_engine.play_mix(
                backing_wav_path=proj.backing_wav_path,
                original_vocals_wav_path=proj.vocals_wav_path,
                takes=mix_tracks,
                start_position_ms=current_ms,
                audition_mode=self._audition_mode,
                active_take_id=self._active_take.id if self._active_take else None,
                backing_gain_db=self._backing_gain_db,
                on_playhead_update=lambda ms: self._sync_playhead(ms),
                on_finished=lambda: self._on_playback_finished()
            )

    def _sync_playhead(self, ms: int):
        self.waveform_canvas.set_playhead(ms)
        self.video_monitor.seek(ms)

    def _on_playback_finished(self):
        self.video_monitor.pause()
        self.play_btn.setText("▶ PLAY (Space)")
        self.play_btn.setStyleSheet("background-color: #10B981; color: #FFFFFF;")

    def _on_audition_mode_changed(self, idx: int):
        mode = self.mode_combo.currentData()
        if mode:
            self._audition_mode = mode
            if self.mixer_engine.is_playing:
                self.toggle_playback()
                self.toggle_playback()

    def _on_backing_gain_changed(self, value: int):
        self._backing_gain_db = float(value)
        self.gain_lbl.setText(f"Backing: {self._backing_gain_db:+.1f} dB")

    def export_master_mp4(self):
        if not self._active_project:
            return

        proj = self._active_project
        exports_dir = self.repository.get_exports_dir(proj.id)
        default_out = str(exports_dir / f"{proj.title}_Dubbed.mp4")

        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Master Dubbed MP4",
            default_out,
            "MP4 Video (*.mp4)"
        )
        if not out_path:
            return

        srt_path = str(Path(out_path).with_suffix(".srt"))
        vtt_path = str(Path(out_path).with_suffix(".vtt"))

        # Progress Dialog
        prog_dlg = QDialog(self)
        prog_dlg.setWindowTitle("Exporting Master Dubbed MP4")
        prog_dlg.setFixedSize(400, 140)
        dlg_layout = QVBoxLayout(prog_dlg)

        dlg_lbl = QLabel("Preparing master mix & subtitles...")
        dlg_lbl.setStyleSheet("font-weight: 600; color: #F1F5F9;")
        dlg_layout.addWidget(dlg_lbl)

        dlg_bar = QProgressBar()
        dlg_bar.setRange(0, 100)
        dlg_layout.addWidget(dlg_bar)

        prog_dlg.show()

        def worker():
            try:
                # 1. Export Subtitles
                all_clips = self.repository.get_clips_for_project(proj.id)
                self.mp4_muxer.export_srt(all_clips, srt_path)
                self.mp4_muxer.export_vtt(all_clips, vtt_path)

                # 2. Gather master takes
                all_takes = self.repository.get_all_takes_for_project(proj.id)
                mix_tracks = []
                for t in all_takes:
                    parent_clip = next((c for c in all_clips if c.id == t.clip_id), None)
                    if parent_clip and parent_clip.active_take_id == t.id:
                        mix_tracks.append(
                            MixTakeTrack(
                                take_id=t.id,
                                pcm_file_path=t.pcm_file_path,
                                start_ms=parent_clip.start_ms,
                                duration_ms=t.duration_ms,
                                gain_db=t.gain_db,
                                time_offset_ms=t.time_offset_ms
                            )
                        )

                # 3. Export MP4
                def export_progress(prog: MuxerExportProgress):
                    dlg_lbl.setText(f"{prog.stage} ({prog.percent}%)")
                    dlg_bar.setValue(prog.percent)

                final_mp4 = self.mp4_muxer.export_dubbed_video(
                    source_video_path=proj.video_uri,
                    backing_wav_path=proj.backing_wav_path,
                    original_vocals_wav_path=proj.vocals_wav_path or proj.original_pcm_path,
                    takes=mix_tracks,
                    total_duration_ms=proj.video_duration_ms,
                    output_mp4_path=out_path,
                    on_progress=export_progress
                )

                prog_dlg.accept()
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Dubbed master video and subtitles successfully exported to:\n\n{final_mp4}\n{srt_path}\n{vtt_path}"
                )
            except Exception as e:
                prog_dlg.reject()
                QMessageBox.critical(self, "Export Failed", f"Export error: {e}")

        threading.Thread(target=worker, daemon=True).start()
