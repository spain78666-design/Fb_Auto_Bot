# FB Auto Bot - Enterprise Facebook Marketplace Automation Suite

## Overview
FB Auto Bot is an enterprise automation tool built with Python, PyQt5, and Playwright for high-volume, anti-ban Facebook Marketplace listings.

### Directory Layout
```text
fb_auto_bot/
│
├── app.py                      # Main PyQt5 application entry point with dark glassmorphic GUI
├── admin_key_generator.py      # Standalone Admin tool for HWID key generation
├── requirements.txt            # Python dependencies (PyQt5, Playwright, OpenCV, Pillow, etc.)
│
├── config/
│   ├── __init__.py
│   └── settings.py             # App configurations, stealth parameters, and API keys
│
├── gui/
│   ├── __init__.py
│   └── styles.py               # Glassmorphic QSS stylesheets and design tokens
│
├── automation/
│   ├── __init__.py
│   ├── browser_bot.py          # Playwright stealth browser controller
│   └── session_manager.py      # Cookie injection and session persistence
│
└── utils/
    ├── __init__.py
    ├── licensing.py            # HWID calculation and cryptographic validation
    ├── image_processor.py      # OpenCV / Pillow anti-duplicate algorithms
    └── ai_spinner.py           # Gemini & OpenAI content rewriters
```

### Installation & Execution
```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browser binaries
playwright install chromium

# 4. Launch Desktop Application
python app.py
```
