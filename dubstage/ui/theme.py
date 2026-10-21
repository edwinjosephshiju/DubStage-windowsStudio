"""
DubStage Dark Studio DAW Design System & Stylesheet (QSS)
Vibrant accents, high-contrast readability, and responsive DPI viewport styling
"""

STUDIO_QSS = """
/* Global Window & Typography */
QMainWindow, QWidget#CentralWidget {
    background-color: #0D0E11;
    color: #F1F5F9;
    font-family: "Segoe UI Variable Display", "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: transparent;
    color: #F1F5F9;
    selection-background-color: #8B5CF6;
    selection-color: #FFFFFF;
}

/* Panels & Cards */
QFrame.StudioCard, QWidget.StudioCard {
    background-color: #161922;
    border: 1px solid #232736;
    border-radius: 8px;
}

QFrame.StudioCardElevated {
    background-color: #1C202C;
    border: 1px solid #2F354A;
    border-radius: 8px;
}

/* Tab Navigation */
QTabWidget::pane {
    border: none;
    background-color: #0D0E11;
}

QTabBar::tab {
    background-color: #161922;
    color: #94A3B8;
    padding: 10px 24px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border: 1px solid #232736;
    border-bottom: none;
    font-weight: 600;
    font-size: 13px;
}

QTabBar::tab:selected {
    background-color: #1C202C;
    color: #8B5CF6;
    border-top: 3px solid #8B5CF6;
    border-left: 1px solid #2F354A;
    border-right: 1px solid #2F354A;
}

QTabBar::tab:hover:!selected {
    background-color: #1F2432;
    color: #F1F5F9;
}

/* Buttons */
QPushButton {
    background-color: #242938;
    color: #F1F5F9;
    border: 1px solid #333A4F;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #2F364B;
    border-color: #49536F;
}

QPushButton:pressed {
    background-color: #1C212E;
}

QPushButton:disabled {
    background-color: #151821;
    color: #555E75;
    border-color: #1F2433;
}

/* Primary Accent Button */
QPushButton.PrimaryButton {
    background-color: #8B5CF6;
    color: #FFFFFF;
    border: 1px solid #A78BFA;
}

QPushButton.PrimaryButton:hover {
    background-color: #7C3AED;
    border-color: #C4B5FD;
}

QPushButton.PrimaryButton:pressed {
    background-color: #6D28D9;
}

/* Record Button */
QPushButton.RecordButton {
    background-color: #DC2626;
    color: #FFFFFF;
    border: 1px solid #EF4444;
    border-radius: 20px;
    font-weight: 700;
}

QPushButton.RecordButton:hover {
    background-color: #B91C1C;
}

QPushButton.RecordingActive {
    background-color: #EF4444;
    border: 2px solid #FCA5A5;
}

/* Play/Pause Button */
QPushButton.PlayButton {
    background-color: #10B981;
    color: #FFFFFF;
    border: 1px solid #34D399;
}

QPushButton.PlayButton:hover {
    background-color: #059669;
}

/* Inputs & Text Fields */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #12151D;
    border: 1px solid #293043;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F1F5F9;
    selection-background-color: #8B5CF6;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #8B5CF6;
}

/* Dropdown ComboBox */
QComboBox {
    background-color: #1C202C;
    border: 1px solid #2F354A;
    border-radius: 6px;
    padding: 6px 12px;
    color: #F1F5F9;
    font-weight: 500;
}

QComboBox:hover {
    border-color: #8B5CF6;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #2F354A;
}

QComboBox QAbstractItemView {
    background-color: #161922;
    border: 1px solid #2F354A;
    selection-background-color: #8B5CF6;
    color: #F1F5F9;
    padding: 4px;
}

/* Lists & Tables */
QListWidget, QTableWidget {
    background-color: #12151D;
    border: 1px solid #232736;
    border-radius: 6px;
    outline: none;
}

QListWidget::item {
    padding: 8px 12px;
    border-radius: 4px;
    margin-bottom: 2px;
}

QListWidget::item:selected {
    background-color: #272C3E;
    color: #F8FAFC;
    border-left: 3px solid #8B5CF6;
}

QListWidget::item:hover:!selected {
    background-color: #1A1E2B;
}

/* Sliders */
QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background-color: #2A3043;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background-color: #8B5CF6;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background-color: #FFFFFF;
    border: 2px solid #8B5CF6;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background-color: #A78BFA;
}

/* Progress Bar */
QProgressBar {
    background-color: #12151D;
    border: 1px solid #232736;
    border-radius: 4px;
    text-align: center;
    color: #F1F5F9;
    font-size: 11px;
    font-weight: 600;
    min-height: 14px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8B5CF6, stop:1 #10B981);
    border-radius: 3px;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #0D0E11;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #2F354A;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4A5373;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0D0E11;
    height: 8px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #2F354A;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #4A5373;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Splitters */
QSplitter::handle {
    background-color: #1F2432;
}

QSplitter::handle:hover {
    background-color: #8B5CF6;
}

/* Status Bar */
QStatusBar {
    background-color: #12151E;
    color: #94A3B8;
    border-top: 1px solid #1E2330;
    font-size: 12px;
}

/* Tooltips */
QToolTip {
    background-color: #1E2332;
    color: #F1F5F9;
    border: 1px solid #3B435C;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}
"""

def format_timecode(ms: int) -> str:
    """Format milliseconds to SMPTE timecode MM:SS.mmm"""
    total_sec = max(0, ms) // 1000
    msec = max(0, ms) % 1000
    mins = total_sec // 60
    secs = total_sec % 60
    return f"{mins:02d}:{secs:02d}.{msec:03d}"

def parse_timecode(tc_str: str) -> int:
    """Parse MM:SS.mmm timecode back to milliseconds"""
    try:
        parts = tc_str.strip().split(":")
        mins = int(parts[0])
        sec_parts = parts[1].split(".")
        secs = int(sec_parts[0])
        msec = int(sec_parts[1]) if len(sec_parts) > 1 else 0
        return (mins * 60 + secs) * 1000 + msec
    except Exception:
        return 0
