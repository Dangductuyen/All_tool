"""
VideoEditor Pro - Main Entry Point
A professional desktop video editor with subtitle, TTS, and download tools.

Usage:
    python main.py
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.main_window import MainWindow
from utils.logger import log
from utils.error_handler import global_exception_handler
from utils.config import ConfigManager


def main():
    """Application entry point."""
    log.info("=" * 60)
    log.info("Starting VideoEditor Pro v1.0.0")
    log.info("=" * 60)

    # Initialize config
    config = ConfigManager()
    log.info(f"Config loaded from: {os.path.dirname(os.path.abspath(__file__))}/config.json")

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("VideoEditor Pro")
    app.setApplicationVersion("1.0.0")

    # Set default font
    font = QFont("Segoe UI", 12)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    # Enable high DPI scaling
    app.setStyle("Fusion")

    # Create and show main window
    window = MainWindow()
    window.show()

    log.info("Application window shown")
    window.show_toast("Welcome to VideoEditor Pro!", "info")

    # Run event loop
    exit_code = app.exec()

    log.info(f"Application exiting with code: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
