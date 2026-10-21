"""
DubStage Application Entry Point
High-DPI viewport initialization, dark title bar integration, crash logger, and Qt event loop
"""

import ctypes
import os
import sys
import traceback
from pathlib import Path

# Enable High-DPI Per-Monitor V2 scaling
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from .config import APP_DISPLAY_NAME, APP_NAME, APP_VERSION, get_app_data_dir
from .ui.main_window import MainWindow

def setup_crash_logger():
    """Logs uncaught exceptions into %LOCALAPPDATA%/DubStage/crash.log"""
    log_file = get_app_data_dir() / "crash.log"

    def exception_hook(exctype, value, tb):
        err_msg = "".join(traceback.format_exception(exctype, value, tb))
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n--- CRASH REPORT {APP_NAME} v{APP_VERSION} ---\n")
                f.write(err_msg)
        except Exception:
            pass
        sys.__excepthook__(exctype, value, tb)

    sys.excepthook = exception_hook

def apply_windows_dark_titlebar(window):
    """Enable Windows 10/11 immersive dark mode on native title bar"""
    if os.name == "nt":
        try:
            hwnd = int(window.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(value),
                ctypes.sizeof(value)
            )
        except Exception:
            pass

def main():
    setup_crash_logger()

    # PassThrough High-DPI rounding prevents blurriness on 125%/150%/175% scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setApplicationVersion(APP_VERSION)

    window = MainWindow()
    window.show()
    apply_windows_dark_titlebar(window)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
