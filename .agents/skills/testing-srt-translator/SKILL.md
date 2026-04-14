# Testing: SRT Translator Pro

## Overview
The SRT Translator Pro is a tab within the VideoEditor Pro PySide6 desktop application. It provides multi-AI subtitle translation (Gemini, OpenAI, DeepL, Groq) with API key management, format checking, and debug logging.

## Setup

### Dependencies
```bash
pip install -r requirements.txt
```
Key dependencies: PySide6, openai, google-generativeai, groq, httpx

### Launch
```bash
cd /home/ubuntu/repos/All_tool
python main.py
```

### Navigate to Translator Tab
The app opens on the "Editor" tab. The Translator tab is in the **right panel** tab bar (not the top navigation). Click "Translator" in the right panel's QTabWidget (3rd tab, index 2).

## Testing Patterns

### Programmatic Widget Verification
For quick checks without launching the full GUI:
```python
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
app = QApplication(sys.argv)
from ui.tabs.subtitle_translator_tab import SubtitleTranslatorTab
tab = SubtitleTranslatorTab()
# Check widgets...
print(f'Model status: {tab.lbl_model_status.text()}')
print(f'Models count: {tab.cmb_model.count()}')
QTimer.singleShot(0, app.quit)
app.exec()
```

### Sample SRT File
Create a test file at `/tmp/test_sample.srt`:
```
1
00:00:01,000 --> 00:00:04,000
Hello, welcome to the show.

2
00:00:05,000 --> 00:00:08,500
Today we will learn about Python.
```

### Key Test Areas
1. **Startup** — App launches without crash (watch for `AttributeError` on missing widgets)
2. **Default models** — Each engine loads correct default models (Gemini: 3, OpenAI: 3, Groq: 3, DeepL: 1)
3. **Engine switching** — Changing AI Engine dropdown updates model dropdown
4. **Load SRT** — File loads with correct block count in preview and debug log
5. **Format check** — Valid SRT returns "Format check: OK"
6. **API key validation** — Invalid keys reported correctly with error classification
7. **Translation** — Requires real API keys to test (see Devin Secrets Needed)

## Known UI Layout Issues
- **Narrow sidebar:** The right panel sidebar is narrow, causing:
  - "+" button for API key add may be hidden/squeezed
  - Action buttons (Format, Dich, Dung, Xuat) truncated to single letters
  - Performance and Format Options sections may be below visible scroll area
- **Combo box scroll interference:** Scrolling over dropdowns changes their value instead of scrolling the sidebar. Scroll on labels/group headers instead.
- **Confirmation dialogs:** `_remove_selected_key()` shows a QMessageBox confirmation that might block programmatic testing. Use `QTimer.singleShot` for async testing.

## Key Files
- `ui/tabs/subtitle_translator_tab.py` — Main UI tab (~886 lines)
- `services/translator_service.py` — Translation backend (~1100 lines)
- `config.json` — App config (translator section: batch_size, num_threads, strict_mode)
- `~/.srt_translator_keys.json` — API key storage (created at runtime)

## Devin Secrets Needed
For full translation testing, the following API keys would be needed:
- `GEMINI_API_KEY` — From https://ai.google.dev/
- `OPENAI_API_KEY` — From https://platform.openai.com/api-keys
- `DEEPL_API_KEY` — From https://www.deepl.com/pro-api
- `GROQ_API_KEY` — From https://console.groq.com/keys

Note: Basic UI testing (startup, engine switching, SRT loading, format checking) does NOT require API keys.
