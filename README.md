# VideoEditor Pro

A professional desktop video editor with subtitle, TTS, OCR, and download tools built with Python and PySide6.

## Features

- **Video Editor** - Import, preview, timeline editing with multi-track support
- **Cloud TTS** - Multi-engine text-to-speech (Edge TTS, OpenAI, Vbee, Minimax)
- **Local TTS** - Offline text-to-speech synthesis
- **Video Downloader** - Download from TikTok, Douyin, Facebook, Instagram, Bilibili, Kuaishou
- **OCR** - Text recognition from images/video frames (PaddleOCR / Tesseract)
- **Audio Transcription** - Whisper-based transcription with V1/V2/V3 configurations
- **Subtitle Translator** - AI-powered subtitle translation (OpenAI, Gemini, Groq)
- **AI Agent** - AI-powered editing assistant

## Requirements

- Python 3.10+
- PySide6

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Project Structure

```
video-editor-app/
├── main.py                 # Entry point
├── config.json             # App configuration
├── requirements.txt        # Dependencies
├── ui/                     # UI components
│   ├── main_window.py      # Main window layout
│   ├── timeline_widget.py  # Timeline with tracks
│   ├── styles/
│   │   └── dark_theme.py   # Dark theme QSS
│   ├── widgets/
│   │   ├── toast.py        # Toast notifications
│   │   ├── loading_spinner.py
│   │   └── animated_button.py
│   └── tabs/
│       ├── editor_tab.py
│       ├── cloud_tts_tab.py
│       ├── local_tts_tab.py
│       ├── download_tab.py
│       ├── ocr_setting_tab.py
│       ├── audio_panel.py
│       ├── subtitle_translator_tab.py
│       ├── inspector_tab.py
│       ├── captions_tab.py
│       ├── ai_agent_tab.py
│       ├── music_tab.py
│       └── export_options_tab.py
├── core/
│   ├── project_manager.py
│   └── timeline_model.py
├── services/
│   ├── tts_service.py
│   ├── ocr_service.py
│   ├── audio_service.py
│   ├── download_service.py
│   ├── subtitle_service.py
│   └── translator_service.py
└── utils/
    ├── config.py
    ├── logger.py
    └── error_handler.py
```
