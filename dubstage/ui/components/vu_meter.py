"""
DubStage Real-Time Hardware VU Meter & Peak Indicator
Three-zone LED level meter (-60dB to 0dB) with peak hold and smooth decay
"""

from PyQt6.QtCore import QRectF, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

class VuMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(24)
        self.setMaximumHeight(32)

        self._current_db = -60.0
        self._target_db = -60.0
        self._peak_db = -60.0
        self._peak_hold_ticks = 0

        # Smooth animation timer (60 fps)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._decay_animation)
        self._timer.start(16)

    def set_level(self, db: float):
        self._target_db = max(-60.0, min(0.0, db))
        if self._target_db > self._peak_db:
            self._peak_db = self._target_db
            self._peak_hold_ticks = 40  # Hold peak for ~600ms
        self.update()

    def _decay_animation(self):
        # Smooth attack & decay
        if self._current_db < self._target_db:
            self._current_db += (self._target_db - self._current_db) * 0.4
        else:
            self._current_db += (self._target_db - self._current_db) * 0.15

        # Peak hold decay
        if self._peak_hold_ticks > 0:
            self._peak_hold_ticks -= 1
        else:
            self._peak_db = max(-60.0, self._peak_db - 0.8)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()

        # Background slot
        meter_rect = QRectF(0, (h - 12) / 2.0, w - 50, 12)
        painter.fillRect(meter_rect, QColor("#12151D"))
        painter.setPen(QPen(QColor("#232736"), 1))
        painter.drawRoundedRect(meter_rect, 4, 4)

        # Level width
        pct = (self._current_db + 60.0) / 60.0
        bar_w = max(0.0, min(meter_rect.width() * pct, meter_rect.width()))

        # Draw segmented or multi-colored level
        if bar_w > 0:
            # Green segment (-60 to -12 dB -> 0% to 80%)
            green_w = min(bar_w, meter_rect.width() * 0.80)
            painter.fillRect(QRectF(meter_rect.x(), meter_rect.y(), green_w, meter_rect.height()), QColor("#10B981"))

            # Amber segment (-12 to -3 dB -> 80% to 95%)
            if bar_w > meter_rect.width() * 0.80:
                amber_w = min(bar_w - meter_rect.width() * 0.80, meter_rect.width() * 0.15)
                painter.fillRect(QRectF(meter_rect.x() + meter_rect.width() * 0.80, meter_rect.y(), amber_w, meter_rect.height()), QColor("#F59E0B"))

            # Red segment (-3 to 0 dB -> 95% to 100%)
            if bar_w > meter_rect.width() * 0.95:
                red_w = bar_w - meter_rect.width() * 0.95
                painter.fillRect(QRectF(meter_rect.x() + meter_rect.width() * 0.95, meter_rect.y(), red_w, meter_rect.height()), QColor("#EF4444"))

        # Peak indicator line
        peak_pct = (self._peak_db + 60.0) / 60.0
        peak_x = meter_rect.x() + meter_rect.width() * peak_pct
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawLine(int(peak_x), int(meter_rect.y()), int(peak_x), int(meter_rect.y() + meter_rect.height()))

        # Text label (e.g. -14 dB)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(QColor("#94A3B8"))
        db_text = f"{self._current_db:.1f} dB" if self._current_db > -59.5 else "-INF"
        painter.drawText(int(w - 46), int(h / 2.0 + 4), db_text)
