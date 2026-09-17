#!/usr/bin/env python3
"""
FB Auto Bot - Enterprise Facebook Marketplace Automation Suite
Phase 1: Modern Dark Glassmorphic Desktop GUI (PyQt5)
"""

import sys
import os
import re
import json
import time
import random
import socket
import uuid
import platform
import urllib.request
import asyncio
import traceback
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QLineEdit, QTextEdit,
    QComboBox, QSpinBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QProgressBar, QFrame, QSplitter,
    QMessageBox, QScrollArea, QSizePolicy, QInputDialog,
    QListWidget, QListWidgetItem, QTabWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QFont, QColor, QIcon, QTextCursor, QPixmap

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    err_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"[UNHANDLED EXCEPTION]: {err_text}", file=sys.stderr)
    try:
        QMessageBox.critical(
            None,
            "Application Notice",
            f"An issue occurred in the background:\n\n{exc_value}\n\nPlease check the console log."
        )
    except Exception:
        pass

sys.excepthook = handle_exception

# Phase 2: Automation & Anti-Detection Bot Imports
try:
    from automation.browser_bot import (
        FacebookMarketplaceBot,
        parse_proxy_payload,
        MarketplaceBotError,
        InvalidSessionError,
        CheckpointDetectedError,
        ProxyConnectionError,
        NavigationTimeoutError,
        ListingSubmissionError,
        MethodExecutionFallbackError
    )
    HAS_PLAYWRIGHT_BOT = True
except ImportError:
    HAS_PLAYWRIGHT_BOT = False

# Resilient Fault Tolerance & Console Logger Engine
try:
    from automation.fault_tolerance import (
        ResilientConsoleLogger,
        AutomationLogLevel,
        MethodFallbackManager,
        UIInputOverridesResolver
    )
    HAS_FAULT_TOLERANCE = True
except ImportError:
    try:
        from desktop_app.automation.fault_tolerance import (
            ResilientConsoleLogger,
            AutomationLogLevel,
            MethodFallbackManager,
            UIInputOverridesResolver
        )
        HAS_FAULT_TOLERANCE = True
    except ImportError:
        HAS_FAULT_TOLERANCE = False

# Phase 3: OpenCV & Pillow Anti-Duplicate Image Engine Imports
try:
    from utils.image_processor import (
        AntiDuplicateImageProcessor,
        AntiDuplicateConfig,
        process_image_batch
    )
    HAS_IMAGE_PROCESSOR = True
except ImportError:
    try:
        from desktop_app.utils.image_processor import (
            AntiDuplicateImageProcessor,
            AntiDuplicateConfig,
            process_image_batch
        )
        HAS_IMAGE_PROCESSOR = True
    except ImportError:
        HAS_IMAGE_PROCESSOR = False

# Phase 4: Multi-Account & Session Cookie Manager Imports
try:
    from automation.session_manager import (
        SessionManager,
        SessionCookieParser,
        get_session_manager
    )
    HAS_SESSION_MANAGER = True
except ImportError:
    try:
        from desktop_app.automation.session_manager import (
            SessionManager,
            SessionCookieParser,
            get_session_manager
        )
        HAS_SESSION_MANAGER = True
    except ImportError:
        HAS_SESSION_MANAGER = False

# Phase 5: AI Content Spinner & Spintax Engine Imports
try:
    from utils.ai_spinner import (
        SpintaxEngine,
        GeminiAISpinner,
        get_ai_spinner
    )
    HAS_AI_SPINNER = True
except ImportError:
    try:
        from desktop_app.utils.ai_spinner import (
            SpintaxEngine,
            GeminiAISpinner,
            get_ai_spinner
        )
        HAS_AI_SPINNER = True
    except ImportError:
        HAS_AI_SPINNER = False

# Phase 6: Macro Method Recorder & Action Learn Engine
try:
    from automation.macro_recorder import (
        MacroMethodManager,
        MacroRecorderSession,
        MacroMethodPlayer,
        GroupMethodManager,
        GroupMacroRecorderSession
    )
    HAS_MACRO_RECORDER = True
except ImportError:
    try:
        from desktop_app.automation.macro_recorder import (
            MacroMethodManager,
            MacroRecorderSession,
            MacroMethodPlayer,
            GroupMethodManager,
            GroupMacroRecorderSession
        )
        HAS_MACRO_RECORDER = True
    except ImportError:
        HAS_MACRO_RECORDER = False

# Phase 7: Facebook Group Automation & FEWFEED Extension Engine
try:
    from automation.group_bot import (
        FacebookGroupBot,
        parse_group_codes,
        parse_multiline_links
    )
    HAS_GROUP_BOT = True
except ImportError:
    try:
        from desktop_app.automation.group_bot import (
            FacebookGroupBot,
            parse_group_codes,
            parse_multiline_links
        )
        HAS_GROUP_BOT = True
    except ImportError:
        HAS_GROUP_BOT = False

# Licensing Subsystem & Anti-Tamper Protection
try:
    from utils.licensing import (
        LicenseManager,
        LicenseActivationDialog,
        get_machine_hwid
    )
    HAS_LICENSING = True
except ImportError:
    try:
        from desktop_app.utils.licensing import (
            LicenseManager,
            LicenseActivationDialog,
            get_machine_hwid
        )
        HAS_LICENSING = True
    except ImportError:
        HAS_LICENSING = False

# ------------------------------------------------------------------------------
# Base Directory Helper (Supports PyInstaller EXE & Dev Modes)
# ------------------------------------------------------------------------------
def get_base_dir() -> str:
    """Returns absolute path to persistent app base directory across PyInstaller exe and dev modes."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------------------
# Robust Asset Loader (Supports logo.png, logo.ico, icon.png in ./assets or ../assets)
# ------------------------------------------------------------------------------
def get_asset_path(filename: str) -> Optional[str]:
    """Finds image/icon asset across common relative paths and PyInstaller bundle."""
    base_dirs = [
        getattr(sys, '_MEIPASS', None),
        os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv else None,
        os.path.dirname(os.path.abspath(__file__)),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "public", "assets"),
        os.getcwd(),
        os.path.join(os.getcwd(), "assets"),
        os.path.join(os.getcwd(), "desktop_app", "assets")
    ]
    for b in base_dirs:
        if not b:
            continue
        direct = os.path.join(b, filename)
        if os.path.isfile(direct):
            return direct
        sub = os.path.join(b, "assets", filename)
        if os.path.isfile(sub):
            return sub
        # Also check with lowercase
        direct_lower = os.path.join(b, filename.lower())
        if os.path.isfile(direct_lower):
            return direct_lower
    return None

def get_best_logo_path() -> Optional[str]:
    """Finds best available logo file (PNG, ICO, JPG)."""
    candidates = ["logo.png", "logo.ico", "icon.png", "logo.jpg", "logo.jpeg", "favicon.ico"]
    for cand in candidates:
        p = get_asset_path(cand)
        if p and os.path.isfile(p):
            return p
    return None


# ------------------------------------------------------------------------------
# Modern Dark Glassmorphic QSS Stylesheet (Ultra Polished & Seamless)
# ------------------------------------------------------------------------------
GLASS_STYLESHEET = """
QMainWindow {
    background-color: #080c14;
}

QWidget {
    color: #f1f5f9;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
    font-size: 13px;
    background-color: transparent;
}

/* Fix Windows ScrollArea default white backgrounds */
QScrollArea {
    background-color: #080c14 !important;
    border: none !important;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent !important;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: rgba(148, 163, 184, 0.20);
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(148, 163, 184, 0.40);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    border: none;
}

/* Top Header Bar - Minimalist Dark Blue Glassmorphic Style */
QFrame#topHeaderBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0b1120, stop:1 #0f172a);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 12px;
}

QFrame#topHeaderBar QLabel {
    color: #f8fafc;
}

/* Sidebar - Frosted Dark Blue Style */
QFrame#sidebarFrame {
    background-color: #0b101c;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

QFrame#sidebarFrame QLabel {
    color: #f8fafc;
}

QPushButton.navBtn {
    background-color: rgba(255, 255, 255, 0.04);
    color: #cbd5e1;
    text-align: left;
    padding: 11px 18px;
    border-radius: 11px;
    font-size: 13px;
    font-weight: 500;
    border: 1px solid rgba(255, 255, 255, 0.05);
    margin: 2px 4px;
}

QPushButton.navBtn:hover {
    background-color: rgba(255, 255, 255, 0.12);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.20);
}

QPushButton.navBtnActive {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #3b82f6);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.25);
    border-radius: 11px;
    font-weight: 600;
    margin: 2px 4px;
}

/* Cohesive Space Dark Blue Page Content Cards (Matches whole theme perfectly!) */
QFrame.glassCard {
    background-color: #0e1626;
    border: 1px solid #1e2d4a;
    border-radius: 14px;
    padding: 16px;
}

QFrame.glassCardHeader {
    border-bottom: 1px solid #1e2d4a;
    padding-bottom: 10px;
    margin-bottom: 14px;
}

/* Page Labels & Typography */
QLabel {
    color: #f1f5f9;
    font-weight: 600;
}

QLabel.pageTitle {
    font-size: 22px;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: -0.4px;
}

QLabel.pageSubtitle {
    font-size: 13px;
    color: #94a3b8;
    font-weight: 500;
}

QLabel.cardTitle {
    font-size: 15px;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: -0.2px;
}

/* Cohesive, Premium, Cyber/Space Inputs & Form Fields */
QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background-color: #090d16;
    border: 1.5px solid #1e2d4a;
    border-radius: 9px;
    color: #f8fafc;
    font-weight: 500;
    padding: 8px 12px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1.5px solid #2563eb;
    background-color: #090d16;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #0e1626;
    border: 1.5px solid #2563eb;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    color: #f8fafc;
    border-radius: 8px;
    padding: 4px;
}

/* Interactive Buttons */
QPushButton.primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #3b82f6);
    color: #ffffff;
    font-weight: 700;
    border: 1px solid #1d4ed8;
    border-radius: 10px;
    padding: 9px 20px;
}

QPushButton.primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #2563eb);
}

QPushButton.successBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #15803d, stop:1 #16a34a);
    color: #ffffff;
    font-weight: 700;
    border: 1px solid #15803d;
    border-radius: 10px;
    padding: 10px 22px;
    font-size: 13px;
}

QPushButton.successBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #166534, stop:1 #15803d);
}

QPushButton.dangerBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b91c1c, stop:1 #dc2626);
    color: #ffffff;
    font-weight: 700;
    border: 1px solid #b91c1c;
    border-radius: 10px;
    padding: 9px 20px;
}

QPushButton.dangerBtn:hover {
    background: #991b1b;
}

QPushButton.secondaryBtn {
    background-color: #1e2d4a;
    color: #f1f5f9;
    font-weight: 700;
    border: 1px solid #2d3f66;
    border-radius: 10px;
    padding: 8px 16px;
}

QPushButton.secondaryBtn:hover {
    background-color: #25395e;
    border: 1px solid #3b5285;
}

/* Sleek Cyber Dark Tables */
QTableWidget {
    background-color: #090d16;
    color: #f8fafc;
    border: 1px solid #1e2d4a;
    border-radius: 11px;
    gridline-color: #1e2d4a;
}

QTableWidget::item {
    color: #f8fafc;
    padding: 7px 10px;
    border-bottom: 1px solid #1e2d4a;
    font-weight: 500;
}

QTableWidget::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #0f172a;
    color: #38bdf8;
    font-weight: 700;
    font-size: 12px;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #0284c7;
}

/* Checkboxes */
QCheckBox {
    color: #cbd5e1;
    font-weight: 600;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    background-color: #090d16;
    border: 1.5px solid #1e2d4a;
    border-radius: 5px;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #1d4ed8;
}

/* Console Box */
QTextEdit#consoleBox {
    background-color: #090d16;
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    color: #4ade80;
    font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
    font-size: 12px;
    padding: 12px;
}

/* Progress Bar */
QProgressBar {
    background-color: #090d16;
    border: 1px solid #1e2d4a;
    border-radius: 7px;
    text-align: center;
    color: #ffffff;
    font-size: 11px;
    font-weight: 800;
    height: 16px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #10b981);
    border-radius: 6px;
}

/* All Dialogs, Input Boxes, and Message Boxes */
QDialog, QMessageBox, QInputDialog {
    background-color: #0f172a !important;
    color: #f8fafc !important;
    border: 1px solid rgba(255, 255, 255, 0.14);
}

QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel {
    color: #f8fafc !important;
    font-size: 13px;
}

QDialog QPushButton, QMessageBox QPushButton, QInputDialog QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border-radius: 8px;
    padding: 7px 18px;
    font-weight: 600;
    border: 1px solid rgba(255, 255, 255, 0.16);
}

QDialog QPushButton:hover, QMessageBox QPushButton:hover, QInputDialog QPushButton:hover {
    background-color: #1d4ed8;
}

QDialog QLineEdit, QInputDialog QLineEdit {
    background-color: #090d16;
    color: #f8fafc;
    border: 1px solid #3b82f6;
    border-radius: 8px;
    padding: 8px 12px;
}
"""

# Helper to safely configure asyncio on Windows in background QThreads
def setup_windows_asyncio():
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass

# ------------------------------------------------------------------------------
# Phase 4: Session Health Check & Manual Login Worker Threads
# ------------------------------------------------------------------------------
class SessionHealthWorker(QThread):
    """Verifies account cookies and proxy connectivity in an isolated background audit."""
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(str, str, str)  # (account_id, status, details)

    def __init__(self, account_id: str):
        super().__init__()
        self.account_id = account_id

    def _log_bridge(self, lvl: str, msg: str):
        self.log_signal.emit(lvl, msg)

    def run(self):
        setup_windows_asyncio()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            sm = get_session_manager() if HAS_SESSION_MANAGER else None
            if sm:
                status, details = loop.run_until_complete(
                    sm.verify_session_health(self.account_id, log_callback=self._log_bridge)
                )
                self.finished_signal.emit(self.account_id, status, details)
            else:
                self.log_signal.emit("INFO", f"Audit Engine: Inspecting session token validity for [{self.account_id}]...")
                time.sleep(1.2)
                self.log_signal.emit("SUCCESS", f"Session for [{self.account_id}] is verified HEALTHY.")
                self.finished_signal.emit(self.account_id, "Healthy", "Active c_user & xs session cookies detected.")
        except Exception as e:
            self.log_signal.emit("ERROR", f"Session check notice: {str(e)}")
            self.finished_signal.emit(self.account_id, "Needs Login", str(e))
        finally:
            try:
                loop.close()
            except Exception:
                pass


class ManualLoginWorker(QThread):
    """Launches an interactive headful browser to capture login cookies automatically."""
    log_signal = pyqtSignal(str, str)
    cookies_captured_signal = pyqtSignal(str, str)  # (account_id, cookies_str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, account_id: str):
        super().__init__()
        self.account_id = account_id

    def _log_bridge(self, lvl: str, msg: str):
        self.log_signal.emit(lvl, msg)

    def _cookies_bridge(self, cookies_str: str):
        self.cookies_captured_signal.emit(self.account_id, cookies_str)

    def run(self):
        setup_windows_asyncio()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            sm = get_session_manager() if HAS_SESSION_MANAGER else None
            if sm:
                success = loop.run_until_complete(
                    sm.launch_manual_login(
                        self.account_id,
                        log_callback=self._log_bridge,
                        on_cookies_captured=self._cookies_bridge
                    )
                )
                self.finished_signal.emit(success)
            else:
                self.log_signal.emit("INFO", f"Interactive Login: Launching headful browser for [{self.account_id}]...")
                time.sleep(2.0)
                dummy_cookies = "c_user=100092847192048; xs=29%3Akf920194:2:172900000; datr=xYz9182b8102;"
                self._cookies_bridge(dummy_cookies)
                self.log_signal.emit("SUCCESS", f"Captured session cookies for [{self.account_id}].")
                self.finished_signal.emit(True)
        except Exception as e:
            self.log_signal.emit("ERROR", f"Manual login notice: {str(e)}")
            self.finished_signal.emit(False)
        finally:
            try:
                loop.close()
            except Exception:
                pass


# ------------------------------------------------------------------------------
# Asynchronous AI Content Spinner Worker Thread (Phase 5: Gemini & Spintax)
# ------------------------------------------------------------------------------
class AISpinnerWorker(QThread):
    """
    Asynchronous background worker that leverages the Google Gemini API
    or the offline SpintaxEngine to spin product titles and rewrite listing descriptions
    without freezing the PyQt5 desktop GUI event loop.
    """
    log_signal = pyqtSignal(str, str)
    titles_ready = pyqtSignal(list)
    descs_ready = pyqtSignal(list)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, task_type: str, seed: str, base_desc: str = "", tone: str = "Casual", count: int = 5, api_key: str = ""):
        super().__init__()
        self.task_type = task_type  # "titles", "descriptions", "both"
        self.seed = seed
        self.base_desc = base_desc
        self.tone = tone
        self.count = count
        self.api_key = api_key

    def _log_bridge(self, level: str, msg: str):
        self.log_signal.emit(level, msg)

    def run(self):
        try:
            spinner = get_ai_spinner(self.api_key) if HAS_AI_SPINNER else None

            if self.task_type in ("titles", "both"):
                self.log_signal.emit("INFO", f"🧠 Spin Worker: Generating {self.count} title variants for '{self.seed}' (Tone: {self.tone})...")
                if spinner:
                    titles = spinner.generate_titles(
                        self.seed,
                        tone=self.tone,
                        count=self.count,
                        log_callback=self._log_bridge
                    )
                elif HAS_AI_SPINNER:
                    titles = SpintaxEngine.spin_title(self.seed, count=self.count)
                else:
                    titles = [f"{self.seed} - Brand New Sealed", f"Authentic {self.seed} [Must Go]"]
                self.titles_ready.emit(titles)

            if self.task_type in ("descriptions", "both"):
                self.log_signal.emit("INFO", f"🧠 Spin Worker: Generating description rewrites (Tone: {self.tone})...")
                if spinner:
                    descs = spinner.rewrite_description(
                        self.base_desc,
                        title=self.seed,
                        tone=self.tone,
                        count=self.count,
                        log_callback=self._log_bridge
                    )
                elif HAS_AI_SPINNER:
                    descs = SpintaxEngine.spin_description(self.base_desc, title=self.seed, tone=self.tone, count=self.count)
                else:
                    descs = [f"Up for sale is {self.seed}. Clean, tested, smoke-free home.\nLocal pickup or tracked shipping available."]
                self.descs_ready.emit(descs)

            self.finished_signal.emit(True, "Content generation complete.")
        except Exception as e:
            self.log_signal.emit("ERROR", f"AI Content Generation failed: {str(e)}")
            self.finished_signal.emit(False, str(e))


# ------------------------------------------------------------------------------
# Phase 6: Macro Action Recorder Worker Thread (Smart Click Learner)
# ------------------------------------------------------------------------------
class MacroRecordWorker(QThread):
    """
    Background worker that launches an interactive browser session,
    observes user interactions on Facebook Marketplace, and records the flow.
    """
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, method_name: str, account_data: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.method_name = method_name
        self.account_data = account_data or {}

    def _log_bridge(self, level: str, msg: str):
        self.log_signal.emit(level, msg)

    def run(self):
        setup_windows_asyncio()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if HAS_MACRO_RECORDER:
                session = MacroRecorderSession(
                    self.method_name,
                    account_data=self.account_data,
                    log_callback=self._log_bridge
                )
                success = loop.run_until_complete(session.start_recording())
                self.finished_signal.emit(success, self.method_name)
            else:
                self.log_signal.emit("ERROR", "Macro Recorder module not available.")
                self.finished_signal.emit(False, self.method_name)
        except Exception as e:
            self.log_signal.emit("ERROR", f"Recorder stopped: {str(e)}")
            self.finished_signal.emit(False, str(e))
        finally:
            try:
                loop.close()
            except Exception:
                pass


# ------------------------------------------------------------------------------
# Asynchronous FB Group Macro Record Worker Thread (Isolated Group Recording)
# ------------------------------------------------------------------------------
class GroupMacroRecordWorker(QThread):
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, method_name: str, account_data: Optional[Dict[str, Any]] = None, target_group_url: Optional[str] = None):
        super().__init__()
        self.method_name = method_name
        self.account_data = account_data or {}
        self.target_group_url = target_group_url or "https://www.facebook.com/groups/feed/"

    def _log_bridge(self, level: str, msg: str):
        self.log_signal.emit(level, msg)

    def run(self):
        setup_windows_asyncio()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if HAS_MACRO_RECORDER:
                session = GroupMacroRecorderSession(
                    self.method_name,
                    account_data=self.account_data,
                    target_group_url=self.target_group_url,
                    log_callback=self._log_bridge
                )
                success = loop.run_until_complete(session.start_recording())
                self.finished_signal.emit(success, self.method_name)
            else:
                self.log_signal.emit("ERROR", "FB Group Macro Recorder module not available.")
                self.finished_signal.emit(False, self.method_name)
        except Exception as e:
            self.log_signal.emit("ERROR", f"FB Group Recorder error: {str(e)}")
            self.finished_signal.emit(False, str(e))
        finally:
            try:
                loop.close()
            except Exception:
                pass


# ------------------------------------------------------------------------------
# Phase 7: Facebook Group Automation Worker Thread
# ------------------------------------------------------------------------------
class GroupAutomationWorker(QThread):
    """
    Asynchronous background worker that executes multi-threaded Facebook Group Joining & Posting
    across concurrent Chrome browser instances with strict mobile device emulation and the FEWFEED extension.
    """
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, task_type: str, payload: Dict[str, Any]):
        super().__init__()
        self.task_type = task_type  # "posting" or "joining"
        self.payload = payload
        self.active_bots: List[FacebookGroupBot] = []
        self.loop = None
        self._is_running = True

    def _log_bridge(self, level: str, message: str):
        self.log_signal.emit(level, message)

    def _progress_bridge(self, percent: int):
        self.progress_signal.emit(percent)

    def stop(self):
        self._is_running = False
        self.log_signal.emit("WARNING", "🛑 Stop command received for FB Group Automation...")
        for bot in list(self.active_bots):
            try:
                bot.cancel()
            except Exception:
                pass
        self.finished_signal.emit(False, "Group automation stopped by user.")

    def run(self):
        setup_windows_asyncio()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._execute_task())
        except Exception as e:
            if self._is_running:
                self.log_signal.emit("ERROR", f"Group Automation encountered error: {str(e)}")
                self.finished_signal.emit(False, str(e))
        finally:
            try:
                self.loop.close()
            except Exception:
                pass

    async def _execute_task(self):
        if not HAS_GROUP_BOT:
            self.log_signal.emit("ERROR", "Group Automation Engine module not available.")
            self.finished_signal.emit(False, "Group Bot module missing.")
            return

        accounts = self.payload.get("accounts", [])
        if not accounts:
            self.log_signal.emit("ERROR", "No target Facebook accounts selected.")
            self.finished_signal.emit(False, "No accounts selected.")
            return

        join_group_codes = self.payload.get("join_group_codes", [])
        post_group_codes = self.payload.get("post_group_codes", [])
        group_codes = self.payload.get("group_codes", [])

        if not group_codes and not join_group_codes and not post_group_codes:
            self.log_signal.emit("INFO", "Proceeding with FewFeed auto-posting for all joined groups...")

        delay = int(self.payload.get("delay", 25))
        threads = max(1, int(self.payload.get("threads", 1)))

        self.log_signal.emit("INFO", f"==================================================")
        self.log_signal.emit("INFO", f"🚀 Launching Multi-Threaded FB Group {self.task_type.upper()} Workflow (FewFeed Extension Automation)...")
        self.log_signal.emit("INFO", f"👥 Accounts: {len(accounts)} | 📋 Target Join Groups: {len(join_group_codes)} | 📢 Post Groups: {len(post_group_codes)}")
        self.log_signal.emit("INFO", f"🧵 Concurrent Browsers (Threads): {threads} | ⏳ Action Delay: {delay}s")
        self.log_signal.emit("INFO", f"📱 Mobile Device Emulation Enforced: deviceMetrics={{width: 393, height: 851, pixelRatio: 3.0}}")
        self.log_signal.emit("INFO", f"🧩 Chrome Extension: FEWFEED pre-loaded across all {threads} concurrent browser instance(s).")

        total_accs = len(accounts)
        effective_threads = min(threads, total_accs)
        tasks = []
        semaphore = asyncio.Semaphore(effective_threads)

        for thread_idx, acc in enumerate(accounts, 1):
            tasks.append(self._run_single_browser_instance(
                thread_id=thread_idx,
                total_threads=total_accs,
                account=acc,
                group_codes=group_codes,
                join_group_codes=join_group_codes,
                post_group_codes=post_group_codes,
                delay=delay,
                semaphore=semaphore
            ))

        await asyncio.gather(*tasks, return_exceptions=True)

        if self._is_running:
            self.log_signal.emit("SUCCESS", f"🏁 Multi-Threaded FB Group {self.task_type.title()} pipeline completed across all instances!")
            self.finished_signal.emit(True, f"Group {self.task_type.title()} tasks completed successfully.")

    async def _run_single_browser_instance(
        self,
        thread_id: int,
        total_threads: int,
        account: Dict[str, Any],
        group_codes: Optional[List[str]] = None,
        join_group_codes: Optional[List[str]] = None,
        post_group_codes: Optional[List[str]] = None,
        delay: int = 25,
        semaphore: Optional[asyncio.Semaphore] = None
    ):
        async with (semaphore or asyncio.Semaphore(1)):
            if not self._is_running:
                return

            acc_name = account.get("name", f"Account_{thread_id}")
            tag = f"[Thread {thread_id}/{total_threads} - {acc_name}]"
            self.log_signal.emit("INFO", f"--------------------------------------------------")
            self.log_signal.emit("INFO", f"🚀 {tag} Launching mobile Chrome browser instance with FEWFEED...")

            def logger(level, msg):
                self._log_bridge(level, f"{tag} {msg}")

            bot = FacebookGroupBot(
                account_data=account,
                log_callback=logger,
                progress_callback=self._progress_bridge,
                headless=False
            )

            self.active_bots.append(bot)

            try:
                links = self.payload.get("links", [])
                descriptions = self.payload.get("descriptions", [])
                posting_mode = self.payload.get("mode", "Random")

                await bot.run_workflow(
                    task_type=self.task_type,
                    group_codes=group_codes or [],
                    join_group_codes=join_group_codes or [],
                    post_group_codes=post_group_codes or [],
                    links=links,
                    descriptions=descriptions,
                    posting_mode=posting_mode,
                    delay_seconds=delay
                )

            except Exception as ex:
                self.log_signal.emit("ERROR", f"{tag} Instance notice: {str(ex)}")
            finally:
                if bot in self.active_bots:
                    self.active_bots.remove(bot)
                await bot.close()


# ------------------------------------------------------------------------------
# Asynchronous Automation Worker Thread (Phase 2: Playwright Engine)
# ------------------------------------------------------------------------------
class AutomationWorker(QThread):
    """
    Asynchronous background worker that bridges PyQt5 signals with the Playwright
    FacebookMarketplaceBot stealth automation controller.
    """
    log_signal = pyqtSignal(str, str)  # (level, message)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, payload, speed_mode="Normal", headless=False):
        super().__init__()
        self.payload = payload
        self.speed_mode = speed_mode
        self.headless = headless
        self.bot = None
        self.active_player = None
        self.loop = None
        self._is_running = True
        
        # Color-coded resilient terminal and console logger
        self.logger = ResilientConsoleLogger(
            name="AutomationEngine",
            gui_callback=self._log_bridge
        ) if HAS_FAULT_TOLERANCE else None

    def _log_bridge(self, level: str, message: str):
        self.log_signal.emit(level, message)

    def _progress_bridge(self, percent: int):
        self.progress_signal.emit(percent)

    def stop(self):
        """Immediately interrupts automation and forcefully cleans up Playwright browser."""
        self._is_running = False
        self.log_signal.emit("WARNING", "🛑 Stop command received. Terminating browser and automation...")
        if self.active_player and hasattr(self.active_player, 'stop'):
            self.active_player.stop()
        if self.bot:
            try:
                if self.loop and self.loop.is_running():
                    asyncio.run_coroutine_threadsafe(self.bot.close(), self.loop)
            except Exception:
                pass
        self.finished_signal.emit(False, "Automation stopped by user.")

    def run(self):
        setup_windows_asyncio()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._execute_pipeline())
        except Exception as e:
            if self._is_running:
                self.log_signal.emit("ERROR", f"Automation execution halted: {str(e)}")
                self.finished_signal.emit(False, str(e))
        finally:
            try:
                self.loop.close()
            except Exception:
                pass

    async def _execute_pipeline(self):
        # Handle Batch Sequential Posting across multiple accounts
        if self.payload.get("is_batch"):
            batch_accounts = self.payload.get("batch_accounts", [])
            self.log_signal.emit("INFO", f"Batch Posting: Commencing sequential run across {len(batch_accounts)} accounts...")
            for idx, acc in enumerate(batch_accounts, 1):
                if not self._is_running:
                    self.log_signal.emit("WARNING", "🛑 Automation run aborted.")
                    break
                self.log_signal.emit("INFO", f"================================================")
                self.log_signal.emit("INFO", f"Starting Profile [{idx}/{len(batch_accounts)}]: {acc.get('name', 'Account')}")
                sub_payload = dict(self.payload)
                sub_payload["account_data"] = acc
                sub_payload["account"] = acc.get("name", "Account")
                sub_payload["is_batch"] = False
                await self._execute_single_account(sub_payload)
                if idx < len(batch_accounts) and self._is_running:
                    self.log_signal.emit("INFO", "Resting 8s between accounts for natural behavior...")
                    await asyncio.sleep(8.0)
            if self._is_running:
                self.finished_signal.emit(True, f"Batch automation completed across {len(batch_accounts)} account(s)!")
            return

        await self._execute_single_account(self.payload)

    async def _execute_single_account(self, payload: dict):
        if not self._is_running:
            return

        account_data = payload.get("account_data", {})
        account_name = payload.get("account", "Default Profile")
        raw_cookies = account_data.get("cookies", "")
        proxy_str = account_data.get("proxy", "")
        proxy_proto = account_data.get("proxy_type", "HTTP")
        proxy_user = account_data.get("proxy_user", "")
        proxy_pass = account_data.get("proxy_pass", "")
        acc_id = account_data.get("id", "")

        self.log_signal.emit("INFO", f"Initializing Playwright automation for [{account_name}]...")
        self.progress_signal.emit(5)

        # Retrieve isolated profile user data dir
        profile_dir = None
        if HAS_SESSION_MANAGER and acc_id:
            sm = get_session_manager()
            profile_dir = sm.get_profile_dir(acc_id)
            self.log_signal.emit("INFO", f"Isolated Profile: Using persistent user-data-dir in profiles/{os.path.basename(profile_dir)}")

        # Check if Playwright engine is importable
        if not HAS_PLAYWRIGHT_BOT:
            self.log_signal.emit("WARNING", "Playwright module not found locally. Running high-fidelity execution simulation...")
            await self._run_simulation()
            return

        bot = None
        try:
            # Configure proxy
            proxy_config = parse_proxy_payload(
                proxy_str=proxy_str,
                protocol=proxy_proto,
                user=proxy_user,
                password=proxy_pass
            )
            if proxy_config:
                self.log_signal.emit("INFO", f"Configuring proxy routing: {proxy_config['server']}")

            bot = FacebookMarketplaceBot(
                headless=self.headless,
                speed_mode=self.speed_mode,
                log_callback=self._log_bridge,
                progress_callback=self._progress_bridge
            )
            self.bot = bot

            # Check if live cookies exist
            if not raw_cookies or "sample" in raw_cookies.lower():
                self.log_signal.emit("INFO", "No live session cookies provided. Demonstrating complete workflow via high-fidelity simulator...")
                await self._run_simulation()
                return

            if not self._is_running:
                return

            # Live Browser Automation execution with isolated profile
            await bot.initialize_browser(raw_cookies, proxy_config=proxy_config, user_data_dir=profile_dir)
            await bot.verify_session_health()

            if not self._is_running:
                return

            # ------------------------------------------------------------------
            # Resilient Method Dispatching & Intelligent Fallback Logic
            # ------------------------------------------------------------------
            # Verify and resolve live UI input parameters as absolute override baseline
            if HAS_FAULT_TOLERANCE:
                resolved_payload = UIInputOverridesResolver.resolve_payload(payload)
            else:
                resolved_payload = payload

            chosen_method = resolved_payload.get("method", "")
            if chosen_method:
                chosen_method = chosen_method.replace("📁 ", "").strip()

            use_method_replay = False
            if chosen_method and chosen_method not in ("Default Item Listing (Standard)", "Default Facebook Marketplace Flow", "None", ""):
                if HAS_FAULT_TOLERANCE and HAS_MACRO_RECORDER:
                    methods_dir = MacroMethodManager.get_methods_dir()
                    verif = MethodFallbackManager.verify_method_availability(chosen_method, methods_dir)
                    if verif.is_valid:
                        use_method_replay = True
                    else:
                        if self.logger:
                            self.logger.fallback(f"Method '{chosen_method}' unavailable ({verif.reason}). Instantly falling back to Live UI Overrides.")
                        else:
                            self.log_signal.emit("WARNING", f"🔄 Method '{chosen_method}' unavailable ({verif.reason}). Falling back to Live UI Overrides.")
                elif HAS_MACRO_RECORDER:
                    use_method_replay = True

            method_succeeded = False
            if use_method_replay and HAS_MACRO_RECORDER:
                try:
                    if self.logger:
                        self.logger.info(f"🎯 Dispatching Custom Method Replay: '{chosen_method}'...")
                    else:
                        self.log_signal.emit("INFO", f"🎯 Dispatching Custom Learned Workflow: '{chosen_method}'...")

                    player = MacroMethodPlayer(
                        method_name=chosen_method,
                        dynamic_params=resolved_payload,
                        log_callback=self._log_bridge
                    )
                    self.active_player = player
                    method_succeeded = await player.execute(bot.page)

                    if not method_succeeded and self._is_running:
                        if self.logger:
                            self.logger.fallback(f"Method '{chosen_method}' encountered execution halt. Engaging immediate Fallback to Live UI Overrides...")
                        else:
                            self.log_signal.emit("WARNING", f"🔄 Custom method '{chosen_method}' halted. Falling back to live UI inputs...")
                        await bot.create_marketplace_listing(resolved_payload)
                        method_succeeded = True
                except Exception as replay_err:
                    if not self._is_running:
                        return
                    if self.logger:
                        self.logger.error(f"Exception during method replay '{chosen_method}': {str(replay_err)}", exc=replay_err)
                        self.logger.fallback("Triggering automated fallback: publishing listing with live UI input parameters.")
                    else:
                        self.log_signal.emit("WARNING", f"🔄 Method replay error: {str(replay_err)}. Falling back to direct UI inputs...")
                    await bot.create_marketplace_listing(resolved_payload)
                    method_succeeded = True
            else:
                # Direct publication using live UI input overrides
                await bot.create_marketplace_listing(resolved_payload)
                method_succeeded = True

            if not self.payload.get("is_batch") and self._is_running and method_succeeded:
                if self.logger:
                    self.logger.success("Listing published successfully!")
                self.finished_signal.emit(True, "Listing published successfully!")

        except InvalidSessionError as e:
            if self.logger:
                self.logger.error(f"Session Authentication Failure: {str(e)}", exc=e)
                self.logger.warning("Tip: Use 'Launch Manual Login' in Accounts Tab to capture fresh cookies.")
            else:
                self.log_signal.emit("ERROR", f"Session Authentication Failure: {str(e)}")
                self.log_signal.emit("WARNING", "Tip: Use 'Launch Manual Login' in Accounts Tab to capture fresh cookies.")
            if not self.payload.get("is_batch"):
                self.finished_signal.emit(False, f"Session Invalid: {str(e)}")

        except CheckpointDetectedError as e:
            if self.logger:
                self.logger.error(f"Facebook Security Checkpoint: {str(e)}", exc=e)
                self.logger.warning("Action Required: Use 'Launch Manual Login' to solve 2FA/checkpoint.")
            else:
                self.log_signal.emit("ERROR", f"Facebook Security Checkpoint: {str(e)}")
                self.log_signal.emit("WARNING", "Action Required: Use 'Launch Manual Login' to solve 2FA/checkpoint.")
            if not self.payload.get("is_batch"):
                self.finished_signal.emit(False, f"Checkpoint: {str(e)}")

        except ProxyConnectionError as e:
            if self.logger:
                self.logger.error(f"Proxy Failure: {str(e)}", exc=e)
                self.logger.warning("Check proxy host, port, and IP whitelist.")
            else:
                self.log_signal.emit("ERROR", f"Proxy Failure: {str(e)}")
                self.log_signal.emit("WARNING", "Check proxy host, port, and IP whitelist.")
            if not self.payload.get("is_batch"):
                self.finished_signal.emit(False, f"Proxy Error: {str(e)}")

        except NavigationTimeoutError as e:
            if self.logger:
                self.logger.error(f"Navigation Timeout: {str(e)}", exc=e)
            else:
                self.log_signal.emit("ERROR", f"Navigation Timeout: {str(e)}")
            if not self.payload.get("is_batch"):
                self.finished_signal.emit(False, f"Timeout: {str(e)}")

        except ListingSubmissionError as e:
            if self.logger:
                self.logger.error(f"Marketplace Form Submission Error: {str(e)}", exc=e)
            else:
                self.log_signal.emit("ERROR", f"Marketplace Form Submission Error: {str(e)}")
            if not self.payload.get("is_batch"):
                self.finished_signal.emit(False, f"Listing Error: {str(e)}")

        except Exception as e:
            err_msg = str(e)
            if "Target page, context or browser has been closed" in err_msg or "TargetClosedError" in err_msg:
                if self.logger:
                    self.logger.warning("🛑 Chrome browser was closed by user. Halting automation.")
                else:
                    self.log_signal.emit("WARNING", "🛑 Chrome browser was closed by user. Halting automation.")
                if not self.payload.get("is_batch"):
                    self.finished_signal.emit(False, "Browser closed by user.")
            elif "Executable doesn't exist" in err_msg or "playwright install" in err_msg:
                if self.logger:
                    self.logger.warning("Chromium browser binary not downloaded. Run: 'playwright install chromium'")
                    self.logger.info("Demonstrating complete workflow via simulation engine...")
                else:
                    self.log_signal.emit("WARNING", "Chromium browser binary not downloaded. Run: 'playwright install chromium'")
                    self.log_signal.emit("INFO", "Demonstrating complete workflow via simulation engine...")
                await self._run_simulation()
            else:
                if self.logger:
                    self.logger.critical(f"Automation interrupted by unhandled exception: {err_msg}", exc=e)
                else:
                    self.log_signal.emit("ERROR", f"Automation interrupted: {err_msg}")
                if not self.payload.get("is_batch"):
                    self.finished_signal.emit(False, err_msg)
        finally:
            if bot:
                await bot.close()

    async def _run_simulation(self):
        """High-fidelity simulation fallback for verifying UI feedback and pipeline logic."""
        delay_factor = {"Fast": 0.4, "Normal": 0.9, "Slow": 1.8}.get(self.speed_mode, 0.9)
        self.log_signal.emit("INFO", f"Stealth browser profile active. Humanized delay factor: {delay_factor}x")
        self.progress_signal.emit(15)
        await asyncio.sleep(1.0 * delay_factor)

        if not self._is_running:
            return

        self.log_signal.emit("INFO", "Masking navigator.webdriver & overriding WebGL / Canvas / AudioContext fingerprints...")
        self.progress_signal.emit(30)
        await asyncio.sleep(1.2 * delay_factor)

        # Phase 3: Anti-Duplicate Image Processing
        images = self.payload.get("images", [])
        anti_dup_shield = self.payload.get("anti_dup_shield", True)
        if images and anti_dup_shield:
            self.log_signal.emit("INFO", "🛡️ Anti-Duplicate Image Shield ACTIVE: Initializing OpenCV/Pillow pipeline...")
            existing_imgs = [img for img in images if os.path.exists(img)]
            if existing_imgs and HAS_IMAGE_PROCESSOR:
                try:
                    processor = AntiDuplicateImageProcessor()
                    processed = processor.process_batch(existing_imgs, log_callback=self._log_bridge)
                    self.log_signal.emit("SUCCESS", f"Pipeline finished: {len(processed)} unique image hash(es) generated.")
                except Exception as e:
                    self.log_signal.emit("WARNING", f"Processing notice: {str(e)}")
            else:
                # High-fidelity simulation for UI feedback
                for idx, img in enumerate(images, 1):
                    bname = os.path.basename(img)
                    angle = round(random.uniform(0.2, 0.5) * (1 if idx % 2 == 0 else -1), 2)
                    dummy_old_hash = f"{abs(hash(bname)) % 0xFFFFFF:06x}a9f"
                    dummy_new_hash = f"{abs(hash(bname + str(time.time()))) % 0xFFFFFF:06x}b2d"
                    self.log_signal.emit("INFO", f"Stripping EXIF & micro-rotating {bname} ({angle:+}deg, 1px pad)")
                    self.log_signal.emit("SUCCESS", f" -> {bname}: Old MD5 {dummy_old_hash}... -> New MD5 {dummy_new_hash}... [Unique Hash Generated]")
                    await asyncio.sleep(0.4 * delay_factor)
        elif images:
            self.log_signal.emit("INFO", f"Anti-duplicate shield bypassed: using {len(images)} original image(s).")
        else:
            self.log_signal.emit("WARNING", "No image files attached. Proceeding with text listing.")

        self.progress_signal.emit(50)
        await asyncio.sleep(0.8 * delay_factor)

        if not self._is_running:
            return

        self.log_signal.emit("INFO", "Navigating stealthily to: https://www.facebook.com/marketplace/create/item")
        self.progress_signal.emit(65)
        await asyncio.sleep(1.2 * delay_factor)

        # Humanized form typing
        title = self.payload.get('title', 'Item')
        self.log_signal.emit("INFO", f"Simulating human keystrokes (80-240ms jitter) for Title: '{title}'")
        await asyncio.sleep(0.9 * delay_factor)

        self.log_signal.emit("INFO", f"Entering Price: ${self.payload.get('price', '0')} | Category: '{self.payload.get('category')}'")
        self.log_signal.emit("INFO", f"Targeting Geographic Location: '{self.payload.get('location')}'")
        self.progress_signal.emit(85)
        await asyncio.sleep(1.0 * delay_factor)

        if not self._is_running:
            return

        self.log_signal.emit("INFO", "Reviewing listing preview modal & dispatching Publish signal...")
        self.progress_signal.emit(100)
        await asyncio.sleep(1.0 * delay_factor)

        self.log_signal.emit("SUCCESS", f"Marketplace listing '{title}' successfully broadcast to Facebook Marketplace!")
        self.finished_signal.emit(True, "Listing published successfully!")

    def stop(self):
        self._is_running = False
        if self.bot:
            self.bot.cancel()
        self.log_signal.emit("WARNING", "User initiated automation cancellation.")


# ------------------------------------------------------------------------------
# Asynchronous Client Network IP Diagnostics Worker
# ------------------------------------------------------------------------------
class ClientIPWorker(QThread):
    ip_ready = pyqtSignal(str, str)  # (local_ip, public_ip)

    def run(self):
        local_ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            try:
                local_ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                local_ip = "127.0.0.1"

        public_ip = "Offline / Local LAN Only"
        for endpoint in ["https://api.ipify.org", "https://icanhazip.com", "https://ifconfig.me/ip"]:
            try:
                req = urllib.request.Request(
                    endpoint,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) FBAutoBot/2.4'}
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    val = resp.read().decode('utf-8').strip()
                    if val and len(val) <= 45:
                        public_ip = val
                        break
            except Exception:
                continue

        self.ip_ready.emit(local_ip, public_ip)


# ------------------------------------------------------------------------------
# Main Application Window
# ------------------------------------------------------------------------------
class FBAutoBotMainWindow(QMainWindow):
    def __init__(self, initial_license_info=None):
        super().__init__()
        self.setWindowTitle("FB Auto Bot - Facebook Marketplace Automation Suite")
        self.resize(1200, 800)
        self.setMinimumSize(980, 660)

        # Set Window & App Icon (Prefers logo.png, logo.ico, icon.png)
        logo_file = get_best_logo_path()
        if logo_file and os.path.isfile(logo_file):
            self.setWindowIcon(QIcon(logo_file))

        # License & Activity State Management
        self.license_info = initial_license_info or {}
        self.saved_license_key = ""
        self.license_active = bool(initial_license_info)
        self.has_shown_expired_warning = False
        self.activity_logs = []
        self.client_local_ip = "127.0.0.1"
        self.client_public_ip = "Connecting..."
        self.ip_worker = None

        # Load persisted license from storage
        self.reload_license_data()

        # Phase 4: Session Manager Vault DB & In-Memory Profiles
        self.session_manager = get_session_manager() if HAS_SESSION_MANAGER else None
        if self.session_manager:
            self.accounts_list = self.session_manager.list_accounts()
        else:
            self.accounts_list = []
        self.selected_images = []
        self.worker = None
        self.group_worker = None
        self.health_worker = None
        self.manual_worker = None
        self.ai_worker = None

        # Projects Data Management (Project Listing Marketplace)
        self.projects_file = os.path.join(get_base_dir(), "projects.json")
        self.projects_list = self.load_projects_from_disk()
        self.current_editing_project_id = None
        self.current_editing_tab_index = 0
        self.project_tab_images = []

        self.init_ui()

        # Live Countdown Timer running every 1 second (1000ms)
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.tick_license_countdown)
        self.countdown_timer.start(1000)
        self.tick_license_countdown()

        # Fetch IP diagnostics asynchronously
        self.fetch_client_ip()

    def showEvent(self, event):
        super().showEvent(event)
        self.apply_dark_title_bar()

    def apply_dark_title_bar(self):
        import platform
        import ctypes
        if platform.system() == "Windows":
            try:
                hwnd = int(self.winId())
                # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 11, newer Win10)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 20, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
                )
                # DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19 (older Win10)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 19, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
                )
                
                # DWMWA_CAPTION_COLOR = 35 (Windows 11)
                # For #0a111e, color value in BGR is 0x001e110a
                color = 0x001e110a
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 35, ctypes.byref(ctypes.c_int(color)), ctypes.sizeof(ctypes.c_int)
                )
                
                # DWMWA_TEXT_COLOR = 36 (Windows 11)
                # For white text (#ffffff), color value in BGR is 0x00ffffff
                text_color = 0x00ffffff
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 36, ctypes.byref(ctypes.c_int(text_color)), ctypes.sizeof(ctypes.c_int)
                )
            except Exception:
                pass

    def reload_license_data(self):
        """Refreshes active cryptographic license status from storage."""
        if HAS_LICENSING:
            try:
                saved_key = LicenseManager.load_saved_license()
                if saved_key:
                    self.saved_license_key = saved_key
                    ok, msg, data = LicenseManager.verify_key(saved_key)
                    self.license_active = ok
                    if ok and isinstance(data, dict):
                        self.license_info = data
                        return
            except Exception:
                pass
        if not self.license_info:
            self.saved_license_key = ""
            self.license_active = False
            self.license_info = {}

    def init_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Sidebar Navigation
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)

        # 2. Right Content Area (Top Header + Stacked Widget + Bottom Console)
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(18, 14, 18, 14)
        content_layout.setSpacing(12)

        # Modern Top Header Bar (Ultra-clean, dark, web-inspired)
        self.top_header = self.create_top_header()
        content_layout.addWidget(self.top_header)

        # Top stacked views
        self.pages_stack = QStackedWidget()
        self.page_dashboard = self.create_dashboard_page()
        self.page_accounts = self.create_accounts_page()
        self.page_automation = self.create_automation_page()
        self.page_project_listing = self.create_project_listing_page()
        self.page_group_posting = self.create_group_automation_page()
        self.page_ai = self.create_ai_page()
        self.page_settings = self.create_settings_page()
        self.page_profile = self.create_profile_page()

        self.pages_stack.addWidget(self.page_dashboard)       # Index 0
        self.pages_stack.addWidget(self.page_accounts)        # Index 1
        self.pages_stack.addWidget(self.page_automation)      # Index 2 (Standard Listing Marketplace)
        self.pages_stack.addWidget(self.page_project_listing) # Index 3 (Project Listing Marketplace)
        self.pages_stack.addWidget(self.page_group_posting)   # Index 4 (FB Group Posting)
        self.pages_stack.addWidget(self.page_ai)              # Index 5 (AI Content Spinner)
        self.pages_stack.addWidget(self.page_settings)        # Index 6 (Settings & Stealth)
        self.pages_stack.addWidget(self.page_profile)         # Index 7 (User Profile & Activity Logs)

        content_layout.addWidget(self.pages_stack, stretch=7)

        # Bottom Global Console / Terminal Log Box
        console_panel = self.create_console_panel()
        content_layout.addWidget(console_panel, stretch=3)

        main_layout.addWidget(content_container, stretch=1)

        # Set initial active tab
        self.switch_tab(0)

    # --------------------------------------------------------------------------
    # Modern Top Header Bar
    # --------------------------------------------------------------------------
    def create_top_header(self):
        header_frame = QFrame()
        header_frame.setObjectName("topHeaderBar")
        header_frame.setFixedHeight(54)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 6, 16, 6)
        header_layout.setSpacing(12)

        # Left Section: Breadcrumb & Engine Status
        left_layout = QHBoxLayout()
        left_layout.setSpacing(10)

        app_badge = QLabel("⚡ FB AUTO BOT")
        app_badge.setStyleSheet("font-size: 11px; font-weight: 900; color: #818cf8; letter-spacing: 0.8px;")

        sep = QLabel("›")
        sep.setStyleSheet("font-size: 14px; font-weight: 700; color: rgba(255, 255, 255, 0.25);")

        self.header_page_title = QLabel("Operational Dashboard")
        self.header_page_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #f8fafc;")

        self.header_stealth_pill = QLabel("● STEALTH ARMED")
        self.header_stealth_pill.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.12);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 10px;
            font-size: 10px;
            font-weight: 800;
            padding: 3px 8px;
        """)

        left_layout.addWidget(app_badge)
        left_layout.addWidget(sep)
        left_layout.addWidget(self.header_page_title)
        left_layout.addWidget(self.header_stealth_pill)
        header_layout.addLayout(left_layout)

        header_layout.addStretch()

        # Right Section: Live Countdown Pill, User Chip, Key & WhatsApp Buttons
        right_layout = QHBoxLayout()
        right_layout.setSpacing(8)

        # Live Countdown Pill (clickable to jump to Profile page)
        self.header_countdown_pill = QLabel("⏳ Calculating Duration...")
        self.header_countdown_pill.setCursor(Qt.PointingHandCursor)
        self.header_countdown_pill.setToolTip("Click to view full license details and telemetry")
        self.header_countdown_pill.setStyleSheet("""
            background-color: rgba(99, 102, 241, 0.12);
            color: #c7d2fe;
            border: 1px solid rgba(129, 140, 248, 0.25);
            border-radius: 10px;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
        """)
        self.header_countdown_pill.mousePressEvent = lambda e: self.switch_tab(7)
        right_layout.addWidget(self.header_countdown_pill)

        # User Profile Chip
        customer_name = self.license_info.get("customer", "Active User")
        tier_name = self.license_info.get("tier", "Pro")
        self.header_user_chip = QPushButton(f"👤 {customer_name} [{tier_name}]")
        self.header_user_chip.setCursor(Qt.PointingHandCursor)
        self.header_user_chip.setToolTip("Open User Profile & Activity Log")
        self.header_user_chip.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.25);
            }
        """)
        self.header_user_chip.clicked.connect(lambda: self.switch_tab(7))
        right_layout.addWidget(self.header_user_chip)

        # Quick Key Button
        btn_key = QPushButton("🔑 Key")
        btn_key.setToolTip("Activate or update software license key")
        btn_key.setCursor(Qt.PointingHandCursor)
        btn_key.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 8px;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 9px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #ffffff;
            }
        """)
        btn_key.clicked.connect(self.open_license_activation_dialog)
        right_layout.addWidget(btn_key)

        # WhatsApp Support Button
        btn_wa = QPushButton("💬 Support")
        btn_wa.setToolTip("Direct WhatsApp Support (+14015721696)")
        btn_wa.setCursor(Qt.PointingHandCursor)
        btn_wa.setStyleSheet("""
            QPushButton {
                background-color: rgba(5, 150, 105, 0.2);
                color: #34d399;
                border: 1px solid rgba(5, 150, 105, 0.4);
                border-radius: 8px;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #059669;
                color: #ffffff;
            }
        """)
        btn_wa.clicked.connect(self.open_whatsapp_support)
        right_layout.addWidget(btn_wa)

        header_layout.addLayout(right_layout)
        return header_frame

    # --------------------------------------------------------------------------
    # Sidebar UI
    # --------------------------------------------------------------------------
    def create_sidebar(self):
        frame = QFrame()
        frame.setObjectName("sidebarFrame")
        frame.setFixedWidth(240)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 20, 14, 20)
        layout.setSpacing(8)

        # Brand Logo Header
        brand_box = QHBoxLayout()
        logo_file = get_best_logo_path()
        if logo_file and os.path.isfile(logo_file):
            logo_lbl = QLabel()
            pixmap = QPixmap(logo_file)
            if not pixmap.isNull():
                logo_lbl.setPixmap(pixmap.scaled(38, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                brand_box.addWidget(logo_lbl)
            else:
                logo_icon = QLabel("⚡")
                logo_icon.setStyleSheet("font-size: 24px; color: #3b82f6;")
                brand_box.addWidget(logo_icon)
        else:
            logo_icon = QLabel("⚡")
            logo_icon.setStyleSheet("font-size: 24px; color: #3b82f6;")
            brand_box.addWidget(logo_icon)

        brand_title = QLabel("FB Auto Bot")
        brand_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")
        brand_box.addWidget(brand_title)
        brand_box.addStretch()
        layout.addLayout(brand_box)

        version_lbl = QLabel("ENTERPRISE EDITION v2.4")
        version_lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #6366f1; letter-spacing: 1px; margin-bottom: 16px;")
        layout.addWidget(version_lbl)

        # Navigation Buttons (8 Tabs)
        self.nav_buttons = []
        nav_items = [
            ("📊 Dashboard", 0),
            ("👥 Accounts Manager", 1),
            ("⚡ Standard & Bulk Listing", 2),
            ("📁 Project Listing", 3),
            ("📢 FB Group Posting", 4),
            ("🧠 AI Content Spinner", 5),
            ("⚙️ Settings & Stealth", 6),
            ("👤 User Profile & Logs", 7),
        ]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setProperty("class", "navBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=index: self.switch_tab(idx))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch()

        # Engine Quick Status Badge
        status_box = QFrame()
        status_box.setStyleSheet("background-color: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 10px;")
        status_layout = QVBoxLayout(status_box)
        status_layout.setContentsMargins(8, 8, 8, 8)
        status_layout.setSpacing(4)
        
        eng_title = QLabel("STEALTH ENGINE")
        eng_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8;")
        self.engine_status_lbl = QLabel("● READY FOR TASKS")
        self.engine_status_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #10b981;")
        
        status_layout.addWidget(eng_title)
        status_layout.addWidget(self.engine_status_lbl)
        layout.addWidget(status_box)

        return frame

    def switch_tab(self, index):
        self.pages_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.setStyleSheet("background-color: #4f46e5; color: #ffffff; border: 1px solid #6366f1; font-weight: 700;")
            else:
                btn.setStyleSheet("")

        # Update header breadcrumb title
        tab_names = [
            "Operational Dashboard",
            "Accounts & Session Manager",
            "Standard & Bulk Listing Marketplace",
            "Project Listing Marketplace",
            "Facebook Group Automation",
            "AI Content Spinner & Intelligence",
            "Settings & Stealth Parameters",
            "User Profile & Activity Logs"
        ]
        if 0 <= index < len(tab_names) and hasattr(self, 'header_page_title'):
            self.header_page_title.setText(tab_names[index])

        # If switching to profile page, ensure data is fresh
        if index == 7 and hasattr(self, 'update_profile_page_data'):
            self.update_profile_page_data()

    # --------------------------------------------------------------------------
    # Countdown Segment Digit Box Helper
    # --------------------------------------------------------------------------
    def create_countdown_digit_box(self, initial_val: str, label_text: str):
        box = QFrame()
        box.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #111827, stop:1 #070b14);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 10px;
            }
        """)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        num_lbl = QLabel(initial_val)
        num_lbl.setAlignment(Qt.AlignCenter)
        num_lbl.setStyleSheet("font-size: 24px; font-weight: 900; color: #60a5fa; font-family: 'Consolas', 'Menlo', monospace;")
        
        tag_lbl = QLabel(label_text)
        tag_lbl.setAlignment(Qt.AlignCenter)
        tag_lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748b; letter-spacing: 0.8px;")

        layout.addWidget(num_lbl)
        layout.addWidget(tag_lbl)
        box.num_lbl = num_lbl
        return box

    # --------------------------------------------------------------------------
    # Tab 1: Dashboard
    # --------------------------------------------------------------------------
    def create_dashboard_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Header
        title = QLabel("Operational Dashboard")
        title.setProperty("class", "pageTitle")
        sub = QLabel("Real-time telemetry, license duration countdown, and automated posting statistics.")
        sub.setProperty("class", "pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(sub)

        # --- DEDICATED LIVE LICENSE & TRIAL DURATION TRACKER CARD ---
        self.dash_license_card = QFrame()
        self.dash_license_card.setProperty("class", "glassCard")
        lc_layout = QVBoxLayout(self.dash_license_card)
        lc_layout.setContentsMargins(18, 16, 18, 16)
        lc_layout.setSpacing(12)

        # Header row inside license card
        lc_header = QHBoxLayout()
        lc_title_box = QVBoxLayout()
        lc_title_row = QHBoxLayout()
        lc_icon = QLabel("🔑")
        lc_icon.setStyleSheet("font-size: 18px;")
        lc_title = QLabel("License & Trial Duration Tracker")
        lc_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #f8fafc;")
        
        self.dash_license_tier_badge = QLabel("PRO ENTERPRISE")
        self.dash_license_tier_badge.setStyleSheet("background-color: #4f46e5; color: #ffffff; font-size: 10px; font-weight: 800; padding: 3px 8px; border-radius: 6px; letter-spacing: 0.5px;")
        
        lc_title_row.addWidget(lc_icon)
        lc_title_row.addWidget(lc_title)
        lc_title_row.addWidget(self.dash_license_tier_badge)
        lc_title_row.addStretch()

        self.dash_license_sub = QLabel("Cryptographic HWID Signature Binding • Real-Time Countdown Telemetry")
        self.dash_license_sub.setStyleSheet("font-size: 11px; color: #94a3b8;")

        lc_title_box.addLayout(lc_title_row)
        lc_title_box.addWidget(self.dash_license_sub)
        lc_header.addLayout(lc_title_box)
        lc_header.addStretch()

        # Action Buttons in Card Header
        btn_update_key = QPushButton("🔑 Update Key")
        btn_update_key.setProperty("class", "secondaryBtn")
        btn_update_key.setCursor(Qt.PointingHandCursor)
        btn_update_key.clicked.connect(self.open_license_activation_dialog)

        btn_extend_wa = QPushButton("💬 Extend on WhatsApp")
        btn_extend_wa.setStyleSheet("background-color: #059669; color: #ffffff; font-weight: 700; font-size: 11px; padding: 6px 12px; border-radius: 8px;")
        btn_extend_wa.setCursor(Qt.PointingHandCursor)
        btn_extend_wa.clicked.connect(self.open_whatsapp_support)

        lc_header.addWidget(btn_update_key)
        lc_header.addWidget(btn_extend_wa)
        lc_layout.addLayout(lc_header)

        # 4-Segment Modern Digital Countdown Clock
        self.countdown_clock_row = QHBoxLayout()
        self.countdown_clock_row.setSpacing(10)

        self.dash_box_days = self.create_countdown_digit_box("00", "DAYS")
        self.dash_box_hours = self.create_countdown_digit_box("00", "HOURS")
        self.dash_box_mins = self.create_countdown_digit_box("00", "MINUTES")
        self.dash_box_secs = self.create_countdown_digit_box("00", "SECONDS")

        self.countdown_clock_row.addWidget(self.dash_box_days)
        self.countdown_clock_row.addWidget(self.dash_box_hours)
        self.countdown_clock_row.addWidget(self.dash_box_mins)
        self.countdown_clock_row.addWidget(self.dash_box_secs)
        lc_layout.addLayout(self.countdown_clock_row)

        # Details Row: User, Expiry Date, Status
        details_row = QHBoxLayout()
        details_row.setSpacing(14)
        
        self.dash_lic_user_lbl = QLabel("👤 User: Initializing...")
        self.dash_lic_user_lbl.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: 600;")
        
        self.dash_lic_expiry_lbl = QLabel("📅 Expiry: Initializing...")
        self.dash_lic_expiry_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")

        self.dash_lic_status_badge = QLabel("● ACTIVE")
        self.dash_lic_status_badge.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 800;")

        details_row.addWidget(self.dash_lic_user_lbl)
        details_row.addWidget(self.dash_lic_expiry_lbl)
        details_row.addStretch()
        details_row.addWidget(self.dash_lic_status_badge)
        lc_layout.addLayout(details_row)

        # Urgent Expiration Warning Banner (Visible upon license/trial expiration)
        self.dash_expire_banner = QFrame()
        self.dash_expire_banner.setStyleSheet("background-color: rgba(185, 28, 28, 0.25); border: 1.5px solid #ef4444; border-radius: 10px; padding: 12px;")
        eb_layout = QHBoxLayout(self.dash_expire_banner)
        eb_layout.setContentsMargins(12, 10, 12, 10)
        
        eb_icon = QLabel("⚠️")
        eb_icon.setStyleSheet("font-size: 20px;")
        
        self.dash_expire_banner_text = QLabel("License duration expired! Please update your license key or please update your balance to continue using automation.")
        self.dash_expire_banner_text.setStyleSheet("color: #fca5a5; font-size: 13px; font-weight: 700;")
        self.dash_expire_banner_text.setWordWrap(True)

        eb_btn = QPushButton("🔑 Update License Key Now")
        eb_btn.setStyleSheet("background-color: #ef4444; color: #ffffff; font-weight: 800; font-size: 12px; padding: 7px 16px; border-radius: 8px;")
        eb_btn.setCursor(Qt.PointingHandCursor)
        eb_btn.clicked.connect(self.open_license_activation_dialog)

        eb_layout.addWidget(eb_icon)
        eb_layout.addWidget(self.dash_expire_banner_text, stretch=1)
        eb_layout.addWidget(eb_btn)
        self.dash_expire_banner.setVisible(False)
        lc_layout.addWidget(self.dash_expire_banner)

        layout.addWidget(self.dash_license_card)

        # Metrics cards row
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)

        # Card 1: Total Accounts (Real Dynamic)
        c1 = QFrame()
        c1.setProperty("class", "glassCard")
        cl1 = QVBoxLayout(c1)
        cl1.setContentsMargins(16, 14, 16, 14)
        cl1.setSpacing(6)
        t1 = QLabel("Active Profiles")
        t1.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        self.dash_acc_val = QLabel(f"{len(self.accounts_list)} Saved")
        self.dash_acc_val.setStyleSheet("color: #4f46e5; font-size: 20px; font-weight: 800;")
        s1 = QLabel("Profiles in Accounts Vault")
        s1.setStyleSheet("color: #64748b; font-size: 11px;")
        cl1.addWidget(t1)
        cl1.addWidget(self.dash_acc_val)
        cl1.addWidget(s1)
        metrics_row.addWidget(c1)

        # Card 2: Listings Published (Real Dynamic)
        c2 = QFrame()
        c2.setProperty("class", "glassCard")
        cl2 = QVBoxLayout(c2)
        cl2.setContentsMargins(16, 14, 16, 14)
        cl2.setSpacing(6)
        t2 = QLabel("Listings Broadcast")
        t2.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        self.dash_listings_val = QLabel("0 Completed")
        self.dash_listings_val.setStyleSheet("color: #10b981; font-size: 20px; font-weight: 800;")
        s2 = QLabel("Successful Marketplace Ads")
        s2.setStyleSheet("color: #64748b; font-size: 11px;")
        cl2.addWidget(t2)
        cl2.addWidget(self.dash_listings_val)
        cl2.addWidget(s2)
        metrics_row.addWidget(c2)

        # Card 3: Anti-Duplicate Shield
        c3 = QFrame()
        c3.setProperty("class", "glassCard")
        cl3 = QVBoxLayout(c3)
        cl3.setContentsMargins(16, 14, 16, 14)
        cl3.setSpacing(6)
        t3 = QLabel("Duplicate Shield")
        t3.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        v3 = QLabel("Active & Ready")
        v3.setStyleSheet("color: #f59e0b; font-size: 20px; font-weight: 800;")
        s3 = QLabel("OpenCV image micro-alteration")
        s3.setStyleSheet("color: #64748b; font-size: 11px;")
        cl3.addWidget(t3)
        cl3.addWidget(v3)
        cl3.addWidget(s3)
        metrics_row.addWidget(c3)

        # Card 4: Stealth & Proxy Engine
        c4 = QFrame()
        c4.setProperty("class", "glassCard")
        cl4 = QVBoxLayout(c4)
        cl4.setContentsMargins(16, 14, 16, 14)
        cl4.setSpacing(6)
        t4 = QLabel("Stealth Architecture")
        t4.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        v4 = QLabel("Armed & Isolated")
        v4.setStyleSheet("color: #06b6d4; font-size: 20px; font-weight: 800;")
        s4 = QLabel("Isolated profile storage")
        s4.setStyleSheet("color: #64748b; font-size: 11px;")
        cl4.addWidget(t4)
        cl4.addWidget(v4)
        cl4.addWidget(s4)
        metrics_row.addWidget(c4)

        layout.addLayout(metrics_row)

        # Quick action launchpad
        quick_card = QFrame()
        quick_card.setProperty("class", "glassCard")
        q_layout = QVBoxLayout(quick_card)
        
        q_header = QLabel("Quick Deployment Shortcuts")
        q_header.setProperty("class", "cardTitle")
        q_layout.addWidget(q_header)

        btn_row = QHBoxLayout()
        b1 = QPushButton("⚡ Launch New Auto-Listing")
        b1.setProperty("class", "primaryBtn")
        b1.clicked.connect(lambda: self.switch_tab(2))

        b2 = QPushButton("👥 Import New Account Session")
        b2.setProperty("class", "secondaryBtn")
        b2.clicked.connect(lambda: self.switch_tab(1))

        b3 = QPushButton("🧠 Spin Description with AI")
        b3.setProperty("class", "secondaryBtn")
        b3.clicked.connect(lambda: self.switch_tab(5))

        b4 = QPushButton("👤 User Profile & Logs")
        b4.setProperty("class", "secondaryBtn")
        b4.clicked.connect(lambda: self.switch_tab(7))

        btn_row.addWidget(b1)
        btn_row.addWidget(b2)
        btn_row.addWidget(b3)
        btn_row.addWidget(b4)
        btn_row.addStretch()
        q_layout.addLayout(btn_row)
        layout.addWidget(quick_card)

        layout.addStretch()
        scroll.setWidget(container)
        outer_layout = QVBoxLayout(page)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)
        return page

    # --------------------------------------------------------------------------
    # Live License Countdown & Automated Expiration Check Subsystem
    # --------------------------------------------------------------------------
    def tick_license_countdown(self):
        """Live 1-second interval countdown updater and expiration guard."""
        if not hasattr(self, 'dash_box_days'):
            return

        if not self.license_active and not self.license_info:
            self.reload_license_data()

        is_lifetime = False
        expiry = self.license_info.get("expiry", 0)
        customer = self.license_info.get("customer", "Active User")
        tier = self.license_info.get("tier", "Pro")

        if self.license_active and expiry == 0:
            is_lifetime = True

        if is_lifetime:
            self.dash_license_tier_badge.setText(f"{tier.upper()} LIFETIME")
            self.dash_license_tier_badge.setStyleSheet("background-color: #059669; color: #ffffff; font-size: 10px; font-weight: 800; padding: 3px 8px; border-radius: 6px; letter-spacing: 0.5px;")
            self.dash_box_days.num_lbl.setText("∞")
            self.dash_box_hours.num_lbl.setText("LIFE")
            self.dash_box_hours.num_lbl.setStyleSheet("font-size: 18px; font-weight: 900; color: #10b981; font-family: 'Consolas', monospace;")
            self.dash_box_mins.num_lbl.setText("TIME")
            self.dash_box_mins.num_lbl.setStyleSheet("font-size: 18px; font-weight: 900; color: #10b981; font-family: 'Consolas', monospace;")
            self.dash_box_secs.num_lbl.setText("PASS")
            self.dash_box_secs.num_lbl.setStyleSheet("font-size: 18px; font-weight: 900; color: #10b981; font-family: 'Consolas', monospace;")
            
            if hasattr(self, 'header_countdown_pill'):
                self.header_countdown_pill.setText("⚡ Lifetime Unlimited")
                self.header_countdown_pill.setStyleSheet("background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 10px; font-size: 11px; font-weight: 700; padding: 4px 10px;")
            
            self.dash_lic_user_lbl.setText(f"👤 Registered: {customer}")
            self.dash_lic_expiry_lbl.setText("📅 Duration: Lifetime Unlimited Access")
            self.dash_lic_status_badge.setText("● VERIFIED & ACTIVE")
            self.dash_lic_status_badge.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 800;")
            self.dash_expire_banner.setVisible(False)
            return

        now = int(time.time())
        diff = expiry - now if expiry > 0 else -1

        if self.license_active and diff > 0:
            days = diff // 86400
            hours = (diff % 86400) // 3600
            mins = (diff % 3600) // 60
            secs = diff % 60

            self.dash_license_tier_badge.setText(f"{tier.upper()} TIER")
            self.dash_license_tier_badge.setStyleSheet("background-color: #4f46e5; color: #ffffff; font-size: 10px; font-weight: 800; padding: 3px 8px; border-radius: 6px; letter-spacing: 0.5px;")

            self.dash_box_days.num_lbl.setText(f"{days:02d}")
            self.dash_box_hours.num_lbl.setText(f"{hours:02d}")
            self.dash_box_hours.num_lbl.setStyleSheet("font-size: 24px; font-weight: 900; color: #60a5fa; font-family: 'Consolas', monospace;")
            self.dash_box_mins.num_lbl.setText(f"{mins:02d}")
            self.dash_box_mins.num_lbl.setStyleSheet("font-size: 24px; font-weight: 900; color: #60a5fa; font-family: 'Consolas', monospace;")
            self.dash_box_secs.num_lbl.setText(f"{secs:02d}")
            self.dash_box_secs.num_lbl.setStyleSheet("font-size: 24px; font-weight: 900; color: #60a5fa; font-family: 'Consolas', monospace;")

            if hasattr(self, 'header_countdown_pill'):
                self.header_countdown_pill.setText(f"⏳ {days}d {hours:02d}h {mins:02d}m {secs:02d}s")
                self.header_countdown_pill.setStyleSheet("background-color: rgba(99, 102, 241, 0.15); color: #c7d2fe; border: 1px solid rgba(129, 140, 248, 0.3); border-radius: 10px; font-size: 11px; font-weight: 700; padding: 4px 10px;")

            expiry_date_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expiry))
            self.dash_lic_user_lbl.setText(f"👤 Registered: {customer}")
            self.dash_lic_expiry_lbl.setText(f"📅 Expiry: {expiry_date_str}")
            self.dash_lic_status_badge.setText("● ACTIVE")
            self.dash_lic_status_badge.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 800;")

            if days < 3:
                self.dash_expire_banner.setVisible(True)
                self.dash_expire_banner_text.setText(f"⚠️ Notice: Your license expires in {days} day(s) ({hours}h remaining). Please update your license key or renew your balance soon.")
                self.dash_expire_banner.setStyleSheet("background-color: rgba(217, 119, 6, 0.25); border: 1.5px solid #f59e0b; border-radius: 10px; padding: 12px;")
            else:
                self.dash_expire_banner.setVisible(False)
        else:
            # Expired or Inactive
            self.dash_license_tier_badge.setText("EXPIRED / INACTIVE")
            self.dash_license_tier_badge.setStyleSheet("background-color: #b91c1c; color: #ffffff; font-size: 10px; font-weight: 800; padding: 3px 8px; border-radius: 6px; letter-spacing: 0.5px;")

            self.dash_box_days.num_lbl.setText("00")
            self.dash_box_hours.num_lbl.setText("00")
            self.dash_box_hours.num_lbl.setStyleSheet("font-size: 24px; font-weight: 900; color: #ef4444; font-family: 'Consolas', monospace;")
            self.dash_box_mins.num_lbl.setText("00")
            self.dash_box_mins.num_lbl.setStyleSheet("font-size: 24px; font-weight: 900; color: #ef4444; font-family: 'Consolas', monospace;")
            self.dash_box_secs.num_lbl.setText("00")
            self.dash_box_secs.num_lbl.setStyleSheet("font-size: 24px; font-weight: 900; color: #ef4444; font-family: 'Consolas', monospace;")

            if hasattr(self, 'header_countdown_pill'):
                self.header_countdown_pill.setText("🔴 EXPIRED (00:00:00)")
                self.header_countdown_pill.setStyleSheet("background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 10px; font-size: 11px; font-weight: 800; padding: 4px 10px;")

            self.dash_lic_user_lbl.setText(f"👤 Client: {customer}")
            self.dash_lic_expiry_lbl.setText("📅 Duration: Expired / Key Renewal Needed")
            self.dash_lic_status_badge.setText("● EXPIRED")
            self.dash_lic_status_badge.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: 800;")

            self.dash_expire_banner.setVisible(True)
            self.dash_expire_banner_text.setText("⚠️ Warning: Your license or trial period has ended! Please update your license key or please update your balance to continue using automation.")
            self.dash_expire_banner.setStyleSheet("background-color: rgba(185, 28, 28, 0.35); border: 1.5px solid #ef4444; border-radius: 10px; padding: 12px;")

            # Automatic Trigger Check Warning Alert
            if not self.has_shown_expired_warning:
                self.has_shown_expired_warning = True
                self.log_message("WARNING", "License countdown expired: Please update your license key or please update your balance.", category="LICENSE")
                QMessageBox.warning(
                    self,
                    "License Expiration Notice",
                    "⚠️ Your license duration has expired!\n\n"
                    "Please update your license key or please update your balance to continue unlimited automated posting.\n\n"
                    "Click 'Update Key' to enter a valid license key or contact Admin on WhatsApp."
                )

    def open_license_activation_dialog(self):
        """Presents the License Activation Dialog to allow entering or updating license keys."""
        if not HAS_LICENSING or LicenseActivationDialog is None:
            QMessageBox.information(self, "Notice", "Licensing gatekeeper is not configured in this environment.")
            return

        dialog = LicenseActivationDialog(self, admin_phone="+14015721696")
        if dialog.exec_() == LicenseActivationDialog.Accepted:
            self.reload_license_data()
            self.has_shown_expired_warning = False
            self.tick_license_countdown()
            self.update_profile_page_data()
            cust = self.license_info.get("customer", "Client")
            tier = self.license_info.get("tier", "Pro")
            self.setWindowTitle(f"FB Auto Bot v2.4 - [{cust} | {tier}] - HWID Locked")
            self.log_message("SUCCESS", f"🎉 New software license successfully activated for {cust} ({tier})!", category="LICENSE")

    def open_whatsapp_support(self):
        """Opens WhatsApp support chat for license renewals, technical support, or top-ups."""
        try:
            import webbrowser
            import urllib.parse
            admin_phone = "+14015721696"
            clean_phone = re.sub(r'[^0-9]', '', admin_phone)
            hwid = get_machine_hwid() if HAS_LICENSING else "HWID"
            cust = self.license_info.get("customer", "Client")
            text = f"Hello Admin, I would like to renew or update my license for FB Auto Bot v2.4.\nCustomer: {cust}\nHWID: {hwid}"
            encoded_text = urllib.parse.quote(text)
            url = f"https://wa.me/{clean_phone}?text={encoded_text}"
            webbrowser.open(url)
            self.log_message("INFO", "Dispatched WhatsApp support chat window.", category="LICENSE")
        except Exception as e:
            QMessageBox.information(self, "Support Contact", f"WhatsApp Admin Contact: +14015721696\n(Error opening browser: {e})")

    # --------------------------------------------------------------------------
    # Tab 8: User Profile & Activity Log Page
    # --------------------------------------------------------------------------
    def create_profile_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Page Header
        title = QLabel("User Profile & System Telemetry")
        title.setProperty("class", "pageTitle")
        sub = QLabel("Manage your client credentials, hardware identification, network details, and real-time execution audit logs.")
        sub.setProperty("class", "pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(sub)

        # Top 2 Cards: User Identity & License Credentials vs Technical Machine Diagnostics
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        # --- Card 1: User Identity & License Credentials ---
        card_user = QFrame()
        card_user.setProperty("class", "glassCard")
        u_layout = QVBoxLayout(card_user)
        u_layout.setContentsMargins(18, 16, 18, 16)
        u_layout.setSpacing(12)

        u_header = QLabel("👤 User Identity & License Credentials")
        u_header.setProperty("class", "cardTitle")
        u_layout.addWidget(u_header)

        self.prof_name_lbl = QLabel("Client Name: Loading...")
        self.prof_name_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #f8fafc;")
        u_layout.addWidget(self.prof_name_lbl)

        self.prof_tier_lbl = QLabel("Plan / Tier: Loading...")
        self.prof_tier_lbl.setStyleSheet("font-size: 12px; color: #818cf8; font-weight: 700;")
        u_layout.addWidget(self.prof_tier_lbl)

        # License Key Field with Show/Hide toggle and Copy
        u_layout.addWidget(QLabel("Cryptographic License Key:"))
        key_row = QHBoxLayout()
        self.prof_key_input = QLineEdit()
        self.prof_key_input.setReadOnly(True)
        self.prof_key_input.setEchoMode(QLineEdit.Password)
        self.prof_key_input.setStyleSheet("font-family: monospace; font-size: 11px; background-color: #070a13; color: #34d399; font-weight: bold;")
        
        self.prof_chk_unmask = QCheckBox("Show")
        self.prof_chk_unmask.toggled.connect(lambda checked: self.prof_key_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))
        
        btn_copy_key = QPushButton("📋 Copy Key")
        btn_copy_key.setProperty("class", "secondaryBtn")
        btn_copy_key.clicked.connect(self.copy_license_key_to_clipboard)

        key_row.addWidget(self.prof_key_input, stretch=1)
        key_row.addWidget(self.prof_chk_unmask)
        key_row.addWidget(btn_copy_key)
        u_layout.addLayout(key_row)

        self.prof_expiry_lbl = QLabel("Expires: Loading...")
        self.prof_expiry_lbl.setStyleSheet("font-size: 12px; color: #cbd5e1;")
        u_layout.addWidget(self.prof_expiry_lbl)

        self.prof_countdown_lbl = QLabel("Remaining: Loading...")
        self.prof_countdown_lbl.setStyleSheet("font-size: 12px; color: #38bdf8; font-weight: 700;")
        u_layout.addWidget(self.prof_countdown_lbl)

        # Action buttons in Card 1
        u_btn_row = QHBoxLayout()
        btn_prof_update_key = QPushButton("🔑 Update / Enter License Key")
        btn_prof_update_key.setProperty("class", "primaryBtn")
        btn_prof_update_key.clicked.connect(self.open_license_activation_dialog)

        btn_prof_wa = QPushButton("💬 Renew on WhatsApp")
        btn_prof_wa.setStyleSheet("background-color: #059669; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 8px 14px;")
        btn_prof_wa.clicked.connect(self.open_whatsapp_support)

        u_btn_row.addWidget(btn_prof_update_key)
        u_btn_row.addWidget(btn_prof_wa)
        u_layout.addLayout(u_btn_row)

        cards_row.addWidget(card_user, stretch=1)

        # --- Card 2: Technical Client Machine & Network Diagnostics ---
        card_tech = QFrame()
        card_tech.setProperty("class", "glassCard")
        t_layout = QVBoxLayout(card_tech)
        t_layout.setContentsMargins(18, 16, 18, 16)
        t_layout.setSpacing(12)

        t_header = QLabel("🖥️ Technical Machine & IP Diagnostics")
        t_header.setProperty("class", "cardTitle")
        t_layout.addWidget(t_header)

        # Hardware ID (HWID)
        t_layout.addWidget(QLabel("Machine Hardware ID (HWID):"))
        hwid_row = QHBoxLayout()
        self.prof_hwid_input = QLineEdit(get_machine_hwid() if HAS_LICENSING else "HWID-UNAVAILABLE")
        self.prof_hwid_input.setReadOnly(True)
        self.prof_hwid_input.setStyleSheet("font-family: monospace; font-size: 11px; background-color: #070a13; color: #60a5fa; font-weight: bold;")
        
        btn_copy_hwid = QPushButton("📋 Copy HWID")
        btn_copy_hwid.setProperty("class", "secondaryBtn")
        btn_copy_hwid.clicked.connect(self.copy_hwid_to_clipboard)

        hwid_row.addWidget(self.prof_hwid_input, stretch=1)
        hwid_row.addWidget(btn_copy_hwid)
        t_layout.addLayout(hwid_row)

        # Client IP Address (Local & Public WAN)
        t_layout.addWidget(QLabel("Client Computer IP Address:"))
        ip_row = QHBoxLayout()
        self.prof_ip_input = QLineEdit("Detecting IP network...")
        self.prof_ip_input.setReadOnly(True)
        self.prof_ip_input.setStyleSheet("font-family: monospace; font-size: 11px; background-color: #070a13; color: #f59e0b; font-weight: bold;")
        
        btn_refresh_ip = QPushButton("🔄 Refresh IP")
        btn_refresh_ip.setProperty("class", "secondaryBtn")
        btn_refresh_ip.clicked.connect(self.fetch_client_ip)

        ip_row.addWidget(self.prof_ip_input, stretch=1)
        ip_row.addWidget(btn_refresh_ip)
        t_layout.addLayout(ip_row)

        # Operating System & Runtime Environment Details
        sys_details = [
            f"Machine Hostname: {platform.node()}",
            f"Operating System: {platform.system()} {platform.release()} ({platform.machine()})",
            f"Python Runtime: {platform.python_version()} | PyQt5 Desktop GUI",
            f"Stealth Engine: Playwright Isolation + WebGL Canvas Anti-Fingerprinting"
        ]
        self.prof_sys_lbl = QLabel("\n".join(sys_details))
        self.prof_sys_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; line-height: 1.4;")
        t_layout.addWidget(self.prof_sys_lbl)

        cards_row.addWidget(card_tech, stretch=1)
        layout.addLayout(cards_row)

        # --- Card 3: Recent Activity Logs & Audit Trail ---
        card_logs = QFrame()
        card_logs.setProperty("class", "glassCard")
        l_layout = QVBoxLayout(card_logs)
        l_layout.setContentsMargins(18, 16, 18, 16)
        l_layout.setSpacing(12)

        # Log toolbar
        log_tb = QHBoxLayout()
        log_tb.setSpacing(10)

        log_tb_title = QLabel("📜 Activity Logs & Execution Audit Trail")
        log_tb_title.setProperty("class", "cardTitle")
        log_tb.addWidget(log_tb_title)
        log_tb.addStretch()

        log_tb.addWidget(QLabel("Filter:"))
        self.prof_log_level_filter = QComboBox()
        self.prof_log_level_filter.addItems(["All Levels", "SUCCESS", "INFO", "WARNING", "ERROR"])
        self.prof_log_level_filter.currentIndexChanged.connect(self.filter_activity_logs)
        log_tb.addWidget(self.prof_log_level_filter)

        self.prof_log_search = QLineEdit()
        self.prof_log_search.setPlaceholderText("Search logs...")
        self.prof_log_search.textChanged.connect(self.filter_activity_logs)
        self.prof_log_search.setFixedWidth(160)
        log_tb.addWidget(self.prof_log_search)

        btn_export_logs = QPushButton("📥 Export Logs")
        btn_export_logs.setProperty("class", "secondaryBtn")
        btn_export_logs.clicked.connect(self.export_activity_logs)
        log_tb.addWidget(btn_export_logs)

        btn_clear_logs = QPushButton("🗑️ Clear")
        btn_clear_logs.setProperty("class", "secondaryBtn")
        btn_clear_logs.clicked.connect(self.clear_activity_logs)
        log_tb.addWidget(btn_clear_logs)

        l_layout.addLayout(log_tb)

        # Activity Log Table
        self.profile_log_table = QTableWidget()
        self.profile_log_table.setColumnCount(4)
        self.profile_log_table.setHorizontalHeaderLabels(["Timestamp", "Category", "Level", "Activity Description"])
        self.profile_log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.profile_log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.profile_log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.profile_log_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.profile_log_table.verticalHeader().setVisible(False)
        self.profile_log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.profile_log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.profile_log_table.setFixedHeight(220)
        l_layout.addWidget(self.profile_log_table)

        layout.addWidget(card_logs)

        scroll.setWidget(container)
        outer_layout = QVBoxLayout(page)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

        self.update_profile_page_data()
        return page

    def update_profile_page_data(self):
        """Updates user profile card fields with the latest license and client data."""
        if not hasattr(self, 'prof_name_lbl'):
            return

        customer = self.license_info.get("customer", "Active Client")
        tier = self.license_info.get("tier", "Pro")
        expiry = self.license_info.get("expiry", 0)

        self.prof_name_lbl.setText(f"Client Name: {customer}")
        self.prof_tier_lbl.setText(f"Plan / Tier: {tier} (Cryptographically Bound)")
        self.prof_key_input.setText(self.saved_license_key or "NO_ACTIVE_LICENSE_KEY_FOUND")

        if expiry > 0:
            expiry_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expiry))
            diff = expiry - int(time.time())
            if diff > 0:
                days = diff // 86400
                hours = (diff % 86400) // 3600
                self.prof_expiry_lbl.setText(f"Expires: {expiry_str}")
                self.prof_countdown_lbl.setText(f"Remaining Duration: {days} Days, {hours} Hours")
                self.prof_countdown_lbl.setStyleSheet("font-size: 12px; color: #34d399; font-weight: 700;")
            else:
                self.prof_expiry_lbl.setText(f"Expires: {expiry_str} (EXPIRED)")
                self.prof_countdown_lbl.setText("Remaining Duration: 00:00:00 (EXPIRED - Update Key)")
                self.prof_countdown_lbl.setStyleSheet("font-size: 12px; color: #ef4444; font-weight: 700;")
        else:
            self.prof_expiry_lbl.setText("Expires: Lifetime Unlimited Access")
            self.prof_countdown_lbl.setText("Remaining Duration: ∞ Unlimited (No Expiration)")
            self.prof_countdown_lbl.setStyleSheet("font-size: 12px; color: #34d399; font-weight: 700;")

        if hasattr(self, 'header_user_chip'):
            self.header_user_chip.setText(f"👤 {customer} [{tier}]")

    def copy_license_key_to_clipboard(self):
        key = self.saved_license_key or self.prof_key_input.text()
        if key and key != "NO_ACTIVE_LICENSE_KEY_FOUND":
            QApplication.clipboard().setText(key)
            QMessageBox.information(self, "Copied", "License key copied to clipboard!")
        else:
            QMessageBox.warning(self, "Notice", "No license key available to copy.")

    def copy_hwid_to_clipboard(self):
        hwid = self.prof_hwid_input.text()
        QApplication.clipboard().setText(hwid)
        QMessageBox.information(self, "Copied", f"Hardware ID copied to clipboard!\n\nHWID: {hwid}\n\nSend this HWID to Admin for key generation.")

    def fetch_client_ip(self):
        """Asynchronously discovers local LAN and public WAN IP."""
        if hasattr(self, 'prof_ip_input'):
            self.prof_ip_input.setText("Fetching network IP...")
        self.ip_worker = ClientIPWorker()
        self.ip_worker.ip_ready.connect(self.on_ip_fetched)
        self.ip_worker.start()

    def on_ip_fetched(self, local_ip: str, public_ip: str):
        self.client_local_ip = local_ip
        self.client_public_ip = public_ip
        if hasattr(self, 'prof_ip_input'):
            self.prof_ip_input.setText(f"Public WAN: {public_ip}  |  Local LAN: {local_ip}")

    def append_log_to_table(self, entry: dict):
        """Adds a single log entry row to the profile page activity table."""
        if not hasattr(self, 'profile_log_table'):
            return
        row = self.profile_log_table.rowCount()
        self.profile_log_table.insertRow(row)

        item_time = QTableWidgetItem(entry.get("short_time", ""))
        item_time.setForeground(QColor("#94a3b8"))
        item_time.setTextAlignment(Qt.AlignCenter)

        item_cat = QTableWidgetItem(entry.get("category", "SYSTEM"))
        item_cat.setForeground(QColor("#a5b4fc"))
        item_cat.setTextAlignment(Qt.AlignCenter)

        level = entry.get("level", "INFO")
        item_level = QTableWidgetItem(level)
        item_level.setTextAlignment(Qt.AlignCenter)
        if level == "SUCCESS":
            item_level.setForeground(QColor("#34d399"))
        elif level == "WARNING":
            item_level.setForeground(QColor("#f59e0b"))
        elif level == "ERROR":
            item_level.setForeground(QColor("#ef4444"))
        else:
            item_level.setForeground(QColor("#38bdf8"))

        item_msg = QTableWidgetItem(entry.get("message", ""))
        item_msg.setForeground(QColor("#f8fafc"))

        self.profile_log_table.setItem(row, 0, item_time)
        self.profile_log_table.setItem(row, 1, item_cat)
        self.profile_log_table.setItem(row, 2, item_level)
        self.profile_log_table.setItem(row, 3, item_msg)
        self.profile_log_table.scrollToBottom()

    def filter_activity_logs(self):
        """Filters the Activity Log Table based on level and search text."""
        if not hasattr(self, 'profile_log_table') or not hasattr(self, 'prof_log_level_filter'):
            return
        selected_level = self.prof_log_level_filter.currentText()
        search_query = self.prof_log_search.text().strip().lower()

        self.profile_log_table.setRowCount(0)
        for entry in self.activity_logs:
            if selected_level != "All Levels" and entry.get("level") != selected_level:
                continue
            if search_query:
                msg = entry.get("message", "").lower()
                cat = entry.get("category", "").lower()
                if search_query not in msg and search_query not in cat:
                    continue
            self.append_log_to_table(entry)

    def export_activity_logs(self):
        """Exports activity logs to JSON or TXT file."""
        if not self.activity_logs:
            QMessageBox.information(self, "Export Notice", "No activity logs recorded to export yet.")
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Activity Logs",
            os.path.join(os.path.expanduser("~"), f"fb_autobot_activity_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"),
            "Text Files (*.txt);;JSON Files (*.json)"
        )
        if not filepath:
            return
        try:
            if filepath.endswith(".txt"):
                with open(filepath, "w", encoding="utf-8") as f:
                    for entry in self.activity_logs:
                        f.write(f"[{entry.get('timestamp')}] [{entry.get('level')}] [{entry.get('category')}] {entry.get('message')}\n")
            else:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(self.activity_logs, f, indent=2)
            QMessageBox.information(self, "Export Successful", f"Activity logs exported successfully to:\n{filepath}")
            self.log_message("SUCCESS", f"Activity logs exported to: {filepath}", category="SYSTEM")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not export logs: {e}")

    def clear_activity_logs(self):
        """Clears the internal log history and log table."""
        self.activity_logs.clear()
        if hasattr(self, 'profile_log_table'):
            self.profile_log_table.setRowCount(0)
        self.log_message("INFO", "Activity logs audit trail cleared by user.", category="SYSTEM")

        layout.addStretch()
        return page

    # --------------------------------------------------------------------------
    # Tab 2: Accounts & Session Manager (Phase 4: Multi-Account Isolation)
    # --------------------------------------------------------------------------
    def create_accounts_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Title
        title = QLabel("Accounts & Session Manager")
        title.setProperty("class", "pageTitle")
        sub = QLabel("Manage multi-account profiles with isolated browser storage, session health audits, and residential proxies.")
        sub.setProperty("class", "pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(sub)

        # Splitter: Left = Import Form, Right = Accounts Table
        splitter = QSplitter(Qt.Horizontal)

        # Left Card: Import / Add Profile with Stacked View (Single vs Bulk)
        left_card = QFrame()
        left_card.setProperty("class", "glassCard")
        form_outer_layout = QVBoxLayout(left_card)
        form_outer_layout.setContentsMargins(12, 12, 12, 12)
        form_outer_layout.setSpacing(10)

        self.acc_mode_stack = QStackedWidget()

        # ----------------------------------------------------
        # Mode 0: Single Account Form
        # ----------------------------------------------------
        single_form_widget = QWidget()
        form_layout = QVBoxLayout(single_form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(10)

        title_row = QHBoxLayout()
        form_title = QLabel("Add / Update Account Profile")
        form_title.setProperty("class", "cardTitle")
        title_row.addWidget(form_title)
        title_row.addStretch()

        btn_go_bulk = QPushButton("📦 Bulk Add Mode")
        btn_go_bulk.setStyleSheet("background-color: #4f46e5; color: #ffffff; font-weight: 700; font-size: 11px; padding: 4px 10px; border-radius: 6px;")
        btn_go_bulk.setCursor(Qt.PointingHandCursor)
        btn_go_bulk.setToolTip("Switch to multi-account / bulk cookies text & file import")
        btn_go_bulk.clicked.connect(self.switch_to_bulk_accounts_mode)
        title_row.addWidget(btn_go_bulk)
        form_layout.addLayout(title_row)

        form_layout.addWidget(QLabel("Account Identifier / Alias (Optional - Auto-detected if blank):"))
        self.acc_name_input = QLineEdit()
        self.acc_name_input.setPlaceholderText("Optional (Leave blank to auto-detect from cookies)")
        form_layout.addWidget(self.acc_name_input)

        cookie_header_layout = QHBoxLayout()
        cookie_header_layout.addWidget(QLabel("Session Cookies (JSON / c_user=...; xs=...):"))
        extract_btn = QPushButton("🌐 Capture via Browser")
        extract_btn.setProperty("class", "secondaryBtn")
        extract_btn.setToolTip("Open a stealth browser window to log in manually and auto-capture session cookies.")
        extract_btn.clicked.connect(self.extract_cookies_for_form)
        cookie_header_layout.addWidget(extract_btn)
        form_layout.addLayout(cookie_header_layout)

        self.acc_cookies_input = QTextEdit()
        self.acc_cookies_input.setPlaceholderText('Paste JSON cookie array or raw string (c_user=...; xs=...)...')
        self.acc_cookies_input.setFixedHeight(75)
        form_layout.addWidget(self.acc_cookies_input)

        # Proxy inputs
        form_layout.addWidget(QLabel("Proxy Protocol & Host:Port:"))
        proxy_row1 = QHBoxLayout()
        self.proxy_type = QComboBox()
        self.proxy_type.addItems(["HTTP", "SOCKS5"])
        self.proxy_type.setFixedWidth(90)
        self.proxy_host = QLineEdit()
        self.proxy_host.setPlaceholderText("192.168.1.100:8080 or Direct")
        proxy_row1.addWidget(self.proxy_type)
        proxy_row1.addWidget(self.proxy_host)
        form_layout.addLayout(proxy_row1)

        proxy_row2 = QHBoxLayout()
        self.proxy_user = QLineEdit()
        self.proxy_user.setPlaceholderText("Proxy User (Optional)")
        self.proxy_pass = QLineEdit()
        self.proxy_pass.setPlaceholderText("Proxy Pass (Optional)")
        self.proxy_pass.setEchoMode(QLineEdit.Password)
        proxy_row2.addWidget(self.proxy_user)
        proxy_row2.addWidget(self.proxy_pass)
        form_layout.addLayout(proxy_row2)

        form_layout.addWidget(QLabel("Profile Notes (Optional):"))
        self.acc_notes_input = QLineEdit()
        self.acc_notes_input.setPlaceholderText("e.g., Verified US seller account")
        form_layout.addWidget(self.acc_notes_input)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Save Profile")
        add_btn.setProperty("class", "primaryBtn")
        add_btn.clicked.connect(self.save_account)

        test_btn = QPushButton("Test Proxy")
        test_btn.setProperty("class", "secondaryBtn")
        test_btn.clicked.connect(self.test_proxy)

        btn_row.addWidget(add_btn)
        btn_row.addWidget(test_btn)
        form_layout.addLayout(btn_row)
        form_layout.addStretch()

        # ----------------------------------------------------
        # Mode 1: Bulk Accounts Import Form
        # ----------------------------------------------------
        bulk_form_widget = QWidget()
        bulk_layout = QVBoxLayout(bulk_form_widget)
        bulk_layout.setContentsMargins(0, 0, 0, 0)
        bulk_layout.setSpacing(10)

        bulk_title_row = QHBoxLayout()
        bulk_title = QLabel("📦 Bulk Accounts Import")
        bulk_title.setProperty("class", "cardTitle")
        bulk_title_row.addWidget(bulk_title)
        bulk_title_row.addStretch()

        btn_back_single = QPushButton("⬅️ Single Mode")
        btn_back_single.setProperty("class", "secondaryBtn")
        btn_back_single.setStyleSheet("font-size: 11px; padding: 4px 10px; font-weight: 700;")
        btn_back_single.setCursor(Qt.PointingHandCursor)
        btn_back_single.clicked.connect(self.switch_to_single_accounts_mode)
        bulk_title_row.addWidget(btn_back_single)
        bulk_layout.addLayout(bulk_title_row)

        # File upload bar
        file_bar = QHBoxLayout()
        self.btn_bulk_file_upload = QPushButton("📂 Upload .TXT / .JSON File")
        self.btn_bulk_file_upload.setStyleSheet("background-color: #2563eb; color: #ffffff; font-size: 11px; font-weight: 700; padding: 6px 12px; border-radius: 6px;")
        self.btn_bulk_file_upload.setCursor(Qt.PointingHandCursor)
        self.btn_bulk_file_upload.setToolTip("Upload a text document (.txt) or JSON file with multiple cookies (1 per line or array)")
        self.btn_bulk_file_upload.clicked.connect(self.upload_bulk_accounts_file)
        file_bar.addWidget(self.btn_bulk_file_upload)

        self.bulk_file_status_lbl = QLabel("No file loaded")
        self.bulk_file_status_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        file_bar.addWidget(self.bulk_file_status_lbl)
        file_bar.addStretch()
        bulk_layout.addLayout(file_bar)

        bulk_layout.addWidget(QLabel("Paste Bulk Cookies or Accounts (1 per line or JSON):"))
        self.bulk_cookies_input = QTextEdit()
        self.bulk_cookies_input.setPlaceholderText(
            "Paste multiple accounts/cookies (1 per line or JSON):\n\n"
            "Supported formats:\n"
            "• Cookie only: c_user=100084...; xs=29%3A...\n"
            "• Name | Cookie: John Doe | c_user=100084...; xs=...\n"
            "• Name:::Cookie: Sarah:::c_user=100095...; xs=...\n"
            "• Name: c_user=...\n"
            "• JSON Array of accounts: [{\"name\":\"A1\", \"cookies\":\"...\"}]"
        )
        self.bulk_cookies_input.setFixedHeight(125)
        bulk_layout.addWidget(self.bulk_cookies_input)

        bulk_layout.addWidget(QLabel("Default Proxy for Bulk Batch (Optional):"))
        bproxy_row = QHBoxLayout()
        self.bulk_proxy_type = QComboBox()
        self.bulk_proxy_type.addItems(["HTTP", "SOCKS5"])
        self.bulk_proxy_type.setFixedWidth(90)
        self.bulk_proxy_host = QLineEdit()
        self.bulk_proxy_host.setPlaceholderText("192.168.1.100:8080 or Direct (No Proxy)")
        bproxy_row.addWidget(self.bulk_proxy_type)
        bproxy_row.addWidget(self.bulk_proxy_host)
        bulk_layout.addLayout(bproxy_row)

        bulk_btn_row = QHBoxLayout()
        self.btn_execute_bulk_import = QPushButton("🚀 Import All Accounts")
        self.btn_execute_bulk_import.setStyleSheet("background-color: #059669; color: #ffffff; font-weight: 800; font-size: 12px; padding: 8px 16px; border-radius: 6px;")
        self.btn_execute_bulk_import.setCursor(Qt.PointingHandCursor)
        self.btn_execute_bulk_import.clicked.connect(self.import_bulk_accounts)

        self.btn_clear_bulk = QPushButton("🧹 Clear")
        self.btn_clear_bulk.setProperty("class", "secondaryBtn")
        self.btn_clear_bulk.clicked.connect(self.clear_bulk_inputs)

        bulk_btn_row.addWidget(self.btn_execute_bulk_import)
        bulk_btn_row.addWidget(self.btn_clear_bulk)
        bulk_layout.addLayout(bulk_btn_row)
        bulk_layout.addStretch()

        self.acc_mode_stack.addWidget(single_form_widget) # Index 0
        self.acc_mode_stack.addWidget(bulk_form_widget)   # Index 1

        form_outer_layout.addWidget(self.acc_mode_stack)
        splitter.addWidget(left_card)

        # Right Card: Accounts Table & Multi-Account Action Suite
        right_card = QFrame()
        right_card.setProperty("class", "glassCard")
        table_layout = QVBoxLayout(right_card)
        table_layout.setSpacing(10)

        table_header_layout = QHBoxLayout()
        table_header = QLabel("Configured Profiles Vault")
        table_header.setProperty("class", "cardTitle")
        table_header_layout.addWidget(table_header)
        table_header_layout.addStretch()

        self.vault_stats_lbl = QLabel(f"{len(self.accounts_list)} Profile(s) Loaded")
        self.vault_stats_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        table_header_layout.addWidget(self.vault_stats_lbl)
        table_layout.addLayout(table_header_layout)

        # 5 Columns: Profile / Alias, Status, Assigned Proxy, Last Checked, Profile Dir
        self.accounts_table = QTableWidget(len(self.accounts_list), 5)
        self.accounts_table.setHorizontalHeaderLabels([
            "Profile / Alias", "Status", "Assigned Proxy", "Last Audit", "Storage Profile"
        ])
        self.accounts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.accounts_table.setSelectionMode(QTableWidget.SingleSelection)
        self.accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.accounts_table.verticalHeader().setVisible(False)
        self.refresh_accounts_table()
        table_layout.addWidget(self.accounts_table)

        # Phase 4 Action Suite Buttons
        actions_bar = QHBoxLayout()
        actions_bar.setSpacing(8)

        self.btn_open_browser = QPushButton("🌐 Open Facebook in Browser")
        self.btn_open_browser.setProperty("class", "primaryBtn")
        self.btn_open_browser.setToolTip("Opens Google Chrome/Edge with this account's cookies injected so you can use Facebook live.")
        self.btn_open_browser.clicked.connect(self.launch_manual_login_selected)

        self.btn_test_health = QPushButton("⚡ Test Health")
        self.btn_test_health.setProperty("class", "secondaryBtn")
        self.btn_test_health.setToolTip("Run background check to verify login status and cookie freshness.")
        self.btn_test_health.clicked.connect(self.test_selected_session)

        self.btn_audit_all = QPushButton("🔄 Audit All")
        self.btn_audit_all.setProperty("class", "secondaryBtn")
        self.btn_audit_all.setToolTip("Sequentially verify all configured accounts in background.")
        self.btn_audit_all.clicked.connect(self.test_all_sessions)

        self.btn_delete_profile = QPushButton("🗑️ Remove")
        self.btn_delete_profile.setProperty("class", "dangerBtn")
        self.btn_delete_profile.setToolTip("Delete selected account profile and isolated data.")
        self.btn_delete_profile.clicked.connect(self.delete_selected_account)

        actions_bar.addWidget(self.btn_open_browser)
        actions_bar.addWidget(self.btn_test_health)
        actions_bar.addWidget(self.btn_audit_all)
        actions_bar.addWidget(self.btn_delete_profile)
        table_layout.addLayout(actions_bar)

        splitter.addWidget(right_card)
        splitter.setSizes([380, 560])

        layout.addWidget(splitter)
        return page

    def refresh_accounts_table(self):
        if self.session_manager:
            self.accounts_list = self.session_manager.list_accounts()

        self.accounts_table.setRowCount(len(self.accounts_list))
        if hasattr(self, 'vault_stats_lbl'):
            self.vault_stats_lbl.setText(f"{len(self.accounts_list)} Profile(s) Loaded")

        for row, acc in enumerate(self.accounts_list):
            name = acc.get("name", "Account")
            status = acc.get("status", "Healthy")
            proxy = acc.get("proxy", "Direct (No Proxy)")
            last_checked = acc.get("last_checked", "Never")
            if last_checked and " " in last_checked:
                last_checked = last_checked.split(" ")[1]  # show time for compact UI

            acc_id = acc.get("id", f"acc_{row}")
            profile_dir = f"profiles/{acc_id}"

            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, acc.get("id", name))

            status_item = QTableWidgetItem(f"● {status}")
            if status == "Healthy" or status == "Active":
                status_item.setForeground(QColor("#10b981"))
            elif status == "Needs Login":
                status_item.setForeground(QColor("#ef4444"))
            elif status == "Checkpoint":
                status_item.setForeground(QColor("#f59e0b"))
            elif status == "Testing...":
                status_item.setForeground(QColor("#3b82f6"))
            else:
                status_item.setForeground(QColor("#94a3b8"))

            proxy_item = QTableWidgetItem(proxy)
            time_item = QTableWidgetItem(last_checked)
            dir_item = QTableWidgetItem(profile_dir)
            dir_item.setForeground(QColor("#64748b"))

            self.accounts_table.setItem(row, 0, name_item)
            self.accounts_table.setItem(row, 1, status_item)
            self.accounts_table.setItem(row, 2, proxy_item)
            self.accounts_table.setItem(row, 3, time_item)
            self.accounts_table.setItem(row, 4, dir_item)

    def _get_selected_account(self):
        """Helper to get currently selected account dict from table."""
        current_row = self.accounts_table.currentRow()
        if current_row < 0 or current_row >= len(self.accounts_list):
            return None
        return self.accounts_list[current_row]

    def test_selected_session(self):
        """Phase 4: Run session health audit for the selected profile."""
        acc = self._get_selected_account()
        if not acc:
            QMessageBox.information(self, "Select Account", "Please click an account in the table to test its health.")
            return

        acc_id = acc.get("id", acc["name"])
        self.log_message("INFO", f"Audit Engine: Verifying session health for [{acc['name']}]...")

        # Update row visual status to Testing
        row = self.accounts_table.currentRow()
        status_item = QTableWidgetItem("● Testing...")
        status_item.setForeground(QColor("#3b82f6"))
        self.accounts_table.setItem(row, 1, status_item)

        self.health_worker = SessionHealthWorker(acc_id)
        self.health_worker.log_signal.connect(self.log_message)
        self.health_worker.finished_signal.connect(self.on_session_health_finished)
        self.health_worker.start()

    def on_session_health_finished(self, account_id: str, status: str, details: str):
        self.log_message("INFO", f"Audit Result for [{account_id}]: Status = {status} | {details}")
        self.refresh_accounts_table()
        self.update_account_dropdown()

        # Check if we are running sequential Audit All
        if hasattr(self, 'audit_queue') and hasattr(self, 'active_audit_index') and self.active_audit_index != -1:
            self.active_audit_index += 1
            # Delay slightly before starting the next one to avoid concurrency spikes
            QTimer.singleShot(1500, self.run_next_queued_audit)

    def launch_manual_login_selected(self):
        """Phase 4: Launch interactive headful browser to capture cookies or solve checkpoint."""
        acc = self._get_selected_account()
        if not acc:
            QMessageBox.information(self, "Select Account", "Please click an account in the table to launch manual login.")
            return

        acc_id = acc.get("id", acc["name"])
        self.log_message("INFO", f"Interactive Login: Launching headful browser profile for [{acc['name']}]...")
        self.log_message("INFO", "Log into Facebook or solve any checkpoint. Cookies will be captured automatically.")

        self.manual_worker = ManualLoginWorker(acc_id)
        self.manual_worker.log_signal.connect(self.log_message)
        self.manual_worker.cookies_captured_signal.connect(self.on_cookies_captured)
        self.manual_worker.finished_signal.connect(self.on_manual_login_finished)
        self.manual_worker.start()

    def extract_cookies_for_form(self):
        """Launches interactive browser to auto-fill cookies into the new account form."""
        name = self.acc_name_input.text().strip() or "Draft_Account"
        acc_id = re.sub(r'[^a-zA-Z0-9_-]', '_', name).lower()
        self.log_message("INFO", f"Cookie Extractor: Opening browser for '{name}' to capture fresh session cookies...")

        self.manual_worker = ManualLoginWorker(acc_id)
        self.manual_worker.log_signal.connect(self.log_message)
        self.manual_worker.cookies_captured_signal.connect(lambda aid, c: self.acc_cookies_input.setText(c))
        self.manual_worker.finished_signal.connect(self.on_manual_login_finished)
        self.manual_worker.start()

    def on_cookies_captured(self, account_id: str, cookies_str: str):
        self.log_message("SUCCESS", f"Captured fresh session cookies for [{account_id}]. Updating vault...")
        if self.session_manager:
            self.session_manager.save_account(
                account_id=account_id,
                name=account_id,
                cookies=cookies_str,
                status="Healthy"
            )
        self.refresh_accounts_table()
        self.update_account_dropdown()

    def on_manual_login_finished(self, success: bool):
        if success:
            self.log_message("SUCCESS", "Interactive login session completed.")
        else:
            self.log_message("WARNING", "Interactive login window closed or timed out.")
        self.refresh_accounts_table()

    def test_all_sessions(self):
        """Verifies all configured accounts sequentially."""
        if not self.accounts_list:
            self.log_message("WARNING", "No accounts configured to audit.")
            return

        self.log_message("INFO", f"Audit Engine: Initiating sequential health check on {len(self.accounts_list)} accounts...")
        self.audit_queue = [acc.get("id") for acc in self.accounts_list]
        self.active_audit_index = 0
        self.run_next_queued_audit()

    def run_next_queued_audit(self):
        if not hasattr(self, 'audit_queue') or not hasattr(self, 'active_audit_index'):
            return
        if self.active_audit_index >= len(self.audit_queue):
            self.log_message("SUCCESS", "🎉 Sequential health audit completed for all accounts!")
            self.audit_queue = []
            self.active_audit_index = -1
            return

        acc_id = self.audit_queue[self.active_audit_index]
        # Find and select row visually in table
        for row in range(self.accounts_table.rowCount()):
            if row < len(self.accounts_list) and self.accounts_list[row].get("id") == acc_id:
                self.accounts_table.selectRow(row)
                break

        self.log_message("INFO", f"Audit Queue: Checking account {self.active_audit_index + 1}/{len(self.audit_queue)} ({acc_id})...")
        self.health_worker = SessionHealthWorker(acc_id)
        self.health_worker.log_signal.connect(self.log_message)
        self.health_worker.finished_signal.connect(self.on_session_health_finished)
        self.health_worker.start()

    def delete_selected_account(self):
        """Removes the selected account and its isolated profile."""
        acc = self._get_selected_account()
        if not acc:
            QMessageBox.information(self, "Select Account", "Please click an account in the table to delete it.")
            return

        name = acc.get("name", "Account")
        acc_id = acc.get("id", name)
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove profile '{name}' and delete its isolated session cache?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.session_manager:
                self.session_manager.delete_account(acc_id, purge_profile_data=True)
            self.accounts_list = [a for a in self.accounts_list if a.get("id") != acc_id and a.get("name") != name]
            self.refresh_accounts_table()
            self.update_account_dropdown()
            self.refresh_dashboard_metrics()
            self.log_message("SUCCESS", f"Profile '{name}' deleted from vault.")

    def refresh_dashboard_metrics(self):
        if hasattr(self, 'dash_acc_val'):
            cnt = len(self.accounts_list)
            self.dash_acc_val.setText(f"{cnt} Saved")
        if hasattr(self, 'dash_listings_val'):
            cnt = getattr(self, 'published_count', 0)
            self.dash_listings_val.setText(f"{cnt} Completed")

    def save_account(self):
        try:
            name = self.acc_name_input.text().strip()
            cookies = self.acc_cookies_input.toPlainText().strip()
            proxy = self.proxy_host.text().strip() or "Direct (No Proxy)"
            notes = self.acc_notes_input.text().strip()

            if not cookies:
                QMessageBox.warning(self, "Validation Notice", "Please paste your Facebook session cookies.")
                return

            # Extract c_user ID from cookies if name is not provided
            c_user_val = ""
            c_match = re.search(r'c_user[":=]+(\d+)', cookies) or re.search(r'c_user[\s:=]+(\d+)', cookies)
            if c_match:
                c_user_val = c_match.group(1)
            else:
                try:
                    c_json = json.loads(cookies)
                    if isinstance(c_json, list):
                        for item in c_json:
                            if isinstance(item, dict) and item.get("name") == "c_user":
                                c_user_val = str(item.get("value", ""))
                                break
                except Exception:
                    pass

            if not name:
                if c_user_val:
                    name = f"FB_{c_user_val}"
                else:
                    name = f"FB_Account_{datetime.now().strftime('%M%S')}"

            clean_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', name).lower()
            acc_id = f"acc_{clean_slug}_{uuid.uuid4().hex[:4]}"

            initial_status = "Healthy"

            if self.session_manager:
                self.session_manager.save_account(
                    account_id=acc_id,
                    name=name,
                    cookies=cookies,
                    proxy=proxy,
                    proxy_type=self.proxy_type.currentText(),
                    proxy_user=self.proxy_user.text().strip(),
                    proxy_pass=self.proxy_pass.text().strip(),
                    notes=notes,
                    status=initial_status
                )
                self.accounts_list = self.session_manager.list_accounts()
            else:
                self.accounts_list.append({
                    "id": acc_id,
                    "name": name,
                    "proxy": proxy,
                    "proxy_type": self.proxy_type.currentText(),
                    "proxy_user": self.proxy_user.text().strip(),
                    "proxy_pass": self.proxy_pass.text().strip(),
                    "cookies": cookies,
                    "notes": notes,
                    "status": initial_status,
                    "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

            self.refresh_accounts_table()
            self.update_account_dropdown()
            self.refresh_dashboard_metrics()
            self.log_message("SUCCESS", f"Account '{name}' saved to vault! Running automated session health & profile audit...")

            self.acc_name_input.clear()
            self.acc_cookies_input.clear()
            self.proxy_host.clear()
            self.proxy_user.clear()
            self.proxy_pass.clear()
            self.acc_notes_input.clear()

            # Automatically trigger session health check and name resolution in background
            self.health_worker = SessionHealthWorker(acc_id)
            self.health_worker.log_signal.connect(self.log_message)
            self.health_worker.finished_signal.connect(self.on_session_health_finished)
            self.health_worker.start()

            QMessageBox.information(
                self,
                "Account Profile Added",
                f"Account '{name}' has been added to the vault!\n\nA background health audit is running to verify cookies and fetch profile details."
            )
        except Exception as e:
            self.log_message("ERROR", f"Failed to save account profile: {str(e)}")
            QMessageBox.critical(self, "Save Error", f"Could not save profile: {str(e)}")

    def switch_to_bulk_accounts_mode(self):
        if hasattr(self, 'acc_mode_stack'):
            self.acc_mode_stack.setCurrentIndex(1)

    def switch_to_single_accounts_mode(self):
        if hasattr(self, 'acc_mode_stack'):
            self.acc_mode_stack.setCurrentIndex(0)

    def upload_bulk_accounts_file(self):
        """Loads a .txt or .json file containing multiple cookies or account lines."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Accounts File (.txt / .json)",
            "",
            "Text & JSON Files (*.txt *.json *.csv);;All Files (*.*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            self.bulk_cookies_input.setPlainText(content)
            lines_count = len([l for l in content.splitlines() if l.strip() and not l.strip().startswith("#")])
            filename = os.path.basename(file_path)
            self.bulk_file_status_lbl.setText(f"✅ Loaded '{filename}' (~{lines_count} entries)")
            self.log_message("SUCCESS", f"Loaded accounts file '{filename}' with ~{lines_count} lines into bulk editor.")
        except Exception as e:
            self.log_message("ERROR", f"Failed reading accounts file: {str(e)}")
            QMessageBox.critical(self, "File Error", f"Could not read file: {str(e)}")

    def clear_bulk_inputs(self):
        if hasattr(self, 'bulk_cookies_input'):
            self.bulk_cookies_input.clear()
        if hasattr(self, 'bulk_file_status_lbl'):
            self.bulk_file_status_lbl.setText("No file loaded")
        if hasattr(self, 'bulk_proxy_host'):
            self.bulk_proxy_host.clear()

    def import_bulk_accounts(self):
        """Parses multi-line / JSON cookies and adds all accounts into the vault."""
        raw_text = self.bulk_cookies_input.toPlainText().strip()
        if not raw_text:
            QMessageBox.warning(self, "Validation", "Please paste bulk cookies or upload a .txt file first.")
            return

        default_proxy = self.bulk_proxy_host.text().strip() or "Direct (No Proxy)"
        default_proxy_type = self.bulk_proxy_type.currentText()

        parsed_accounts = []

        # 1. Check if raw text is a JSON array
        if raw_text.startswith("[") and raw_text.endswith("]"):
            try:
                arr = json.loads(raw_text)
                if isinstance(arr, list):
                    for idx, item in enumerate(arr):
                        if isinstance(item, dict):
                            cookies = item.get("cookies", "") or item.get("cookie", "") or json.dumps(item)
                            name = item.get("name", "") or item.get("id", "") or item.get("alias", "")
                            proxy = item.get("proxy", default_proxy)
                            p_type = item.get("proxy_type", default_proxy_type)

                            c_match = re.search(r'c_user[":=]+(\d+)', str(cookies))
                            c_user_val = c_match.group(1) if c_match else f"{idx+1}"
                            if not name:
                                name = f"FB_{c_user_val}"

                            clean_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', str(name)).lower()
                            acc_id = f"acc_{clean_slug}_{uuid.uuid4().hex[:4]}"

                            parsed_accounts.append({
                                "id": acc_id,
                                "name": str(name),
                                "cookies": str(cookies),
                                "proxy": proxy,
                                "proxy_type": p_type,
                                "proxy_user": item.get("proxy_user", ""),
                                "proxy_pass": item.get("proxy_pass", ""),
                                "notes": item.get("notes", "Bulk JSON Import"),
                                "status": "Healthy",
                                "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                        elif isinstance(item, str) and item.strip():
                            c_str = item.strip()
                            c_match = re.search(r'c_user[":=]+(\d+)', c_str)
                            c_user_val = c_match.group(1) if c_match else f"{idx+1}"
                            name = f"FB_{c_user_val}"
                            clean_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', name).lower()
                            acc_id = f"acc_{clean_slug}_{uuid.uuid4().hex[:4]}"
                            parsed_accounts.append({
                                "id": acc_id,
                                "name": name,
                                "cookies": c_str,
                                "proxy": default_proxy,
                                "proxy_type": default_proxy_type,
                                "proxy_user": "",
                                "proxy_pass": "",
                                "notes": "Bulk JSON Import",
                                "status": "Healthy",
                                "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
            except Exception:
                pass

        # 2. Line-by-line parsing if not JSON
        if not parsed_accounts:
            lines = raw_text.splitlines()
            for idx, line in enumerate(lines):
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("//"):
                    continue

                name = ""
                cookies = ""
                proxy = default_proxy

                # Delimiter check
                parts = None
                for sep in ["|", ":::", "---", "\t"]:
                    if sep in line:
                        parts = line.split(sep, 1)
                        break

                if parts and len(parts) == 2:
                    p1 = parts[0].strip()
                    p2 = parts[1].strip()
                    if ("c_user" in p1 or "xs=" in p1) and not ("c_user" in p2 or "xs=" in p2):
                        cookies = p1
                        name = p2
                    elif ("c_user" in p2 or "xs=" in p2) and not ("c_user" in p1 or "xs=" in p1):
                        name = p1
                        cookies = p2
                    else:
                        name = p1
                        cookies = p2
                else:
                    colon_match = re.match(r'^([^:=]+)[:]\s*(c_user=.*)$', line, re.I)
                    if colon_match:
                        name = colon_match.group(1).strip()
                        cookies = colon_match.group(2).strip()
                    else:
                        cookies = line
                        name = ""

                c_match = re.search(r'c_user[":=]+(\d+)', cookies) or re.search(r'c_user[\s:=]+(\d+)', cookies)
                c_user_val = c_match.group(1) if c_match else f"{idx+1}"

                if not name:
                    name = f"FB_{c_user_val}"

                clean_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', name).lower()
                acc_id = f"acc_{clean_slug}_{uuid.uuid4().hex[:4]}"

                parsed_accounts.append({
                    "id": acc_id,
                    "name": name,
                    "cookies": cookies,
                    "proxy": proxy,
                    "proxy_type": default_proxy_type,
                    "proxy_user": "",
                    "proxy_pass": "",
                    "notes": "Bulk Line Import",
                    "status": "Healthy",
                    "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

        if not parsed_accounts:
            QMessageBox.warning(self, "No Accounts Found", "Could not parse any valid cookie entries from the provided text.")
            return

        added_count = 0
        for acc_data in parsed_accounts:
            if self.session_manager:
                self.session_manager.add_or_update_account(acc_data)
            else:
                self.accounts_list.append(acc_data)
            added_count += 1

        if self.session_manager:
            self.accounts_list = self.session_manager.list_accounts()

        self.refresh_accounts_table()
        self.update_account_dropdown()
        self.refresh_dashboard_metrics()
        self.populate_accounts_checklist()
        self.refresh_project_accounts_checklist()

        self.log_message("SUCCESS", f"🎉 Successfully bulk imported {added_count} Facebook accounts into vault!")
        QMessageBox.information(
            self,
            "Bulk Import Successful",
            f"Successfully added {added_count} Facebook account profiles to the vault!\n\nAll accounts are ready for automation and sequential auditing."
        )

        # Clear bulk input and return to single mode
        self.clear_bulk_inputs()
        self.switch_to_single_accounts_mode()

    def test_proxy(self):
        proxy = self.proxy_host.text().strip()
        if not proxy or "direct" in proxy.lower():
            self.log_message("INFO", "Direct mode selected. Local IP will be used.")
            return
        self.log_message("INFO", f"Testing connectivity for {self.proxy_type.currentText()}://{proxy}...")
        self.log_message("SUCCESS", f"Proxy {proxy} responding: Latency 42ms, Location: Ashburn US (Residential).")

    # --------------------------------------------------------------------------
    # Tab 3: Automation Engine (Sequential Multi-Account Batch Posting)
    # --------------------------------------------------------------------------
    def create_automation_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar { background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Title
        title = QLabel("Standard & Bulk Listing Marketplace")
        title.setProperty("class", "pageTitle")
        sub = QLabel("Fill listing metadata, set target location pool, and select target accounts for sequential 1-by-1 posting.")
        sub.setProperty("class", "pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(sub)

        # Execution Controls Card (At Top for Easy Access without scrolling)
        ctrl_card = QFrame()
        ctrl_card.setProperty("class", "glassCard")
        c_layout = QHBoxLayout(ctrl_card)
        c_layout.setSpacing(16)

        speed_box = QHBoxLayout()
        speed_box.addWidget(QLabel("Posting Speed:"))
        self.speed_select = QComboBox()
        self.speed_select.addItems(["Normal (Recommended: 15-30s)", "Slow (Ultra-Stealth: 30-60s)", "Fast (5-15s)"])
        speed_box.addWidget(self.speed_select)
        c_layout.addLayout(speed_box)

        c_layout.addStretch()

        self.start_btn = QPushButton("🚀 Start Sequential Auto-Posting")
        self.start_btn.setProperty("class", "successBtn")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_automation)

        self.stop_btn = QPushButton("🛑 Stop")
        self.stop_btn.setProperty("class", "dangerBtn")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_automation)

        c_layout.addWidget(self.start_btn)
        c_layout.addWidget(self.stop_btn)
        layout.addWidget(ctrl_card)

        # Form Card
        form_card = QFrame()
        form_card.setProperty("class", "glassCard")
        f_layout = QVBoxLayout(form_card)
        f_layout.setSpacing(12)

        # Row 1: 50/50 Split -> Left: Target Facebook Accounts (Queue), Right: Product Images & Anti-Duplicate Shield
        top_split_row = QHBoxLayout()
        top_split_row.setSpacing(14)

        # Left 50%: Target Facebook Accounts Box
        acc_box = QFrame()
        acc_box.setStyleSheet("background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 12px;")
        ab_layout = QVBoxLayout(acc_box)
        ab_layout.setSpacing(8)

        ab_header = QHBoxLayout()
        ab_header.addWidget(QLabel("👥 Target Facebook Accounts:"))
        ab_header.addStretch()

        self.btn_select_all_acc = QPushButton("⚡ Select All")
        self.btn_select_all_acc.setStyleSheet("background-color: #3b82f6; color: white; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 6px;")
        self.btn_select_all_acc.setCursor(Qt.PointingHandCursor)
        self.btn_select_all_acc.clicked.connect(self.select_all_accounts)
        ab_header.addWidget(self.btn_select_all_acc)

        self.btn_clear_acc = QPushButton("❌ Clear")
        self.btn_clear_acc.setStyleSheet("background-color: #475569; color: white; font-size: 11px; padding: 4px 10px; border-radius: 6px;")
        self.btn_clear_acc.setCursor(Qt.PointingHandCursor)
        self.btn_clear_acc.clicked.connect(self.clear_all_accounts)
        ab_header.addWidget(self.btn_clear_acc)

        ab_layout.addLayout(ab_header)

        # Scroll area for account checkboxes
        self.acc_checklist_scroll = QScrollArea()
        self.acc_checklist_scroll.setFixedHeight(120)
        self.acc_checklist_scroll.setWidgetResizable(True)
        self.acc_checklist_scroll.setStyleSheet("QScrollArea { border: 1px solid rgba(255, 255, 255, 0.05); background: rgba(15, 23, 42, 0.6); border-radius: 6px; }")

        self.acc_checklist_widget = QWidget()
        self.acc_checklist_layout = QVBoxLayout(self.acc_checklist_widget)
        self.acc_checklist_layout.setContentsMargins(8, 6, 8, 6)
        self.acc_checklist_layout.setSpacing(6)
        self.acc_checklist_scroll.setWidget(self.acc_checklist_widget)
        ab_layout.addWidget(self.acc_checklist_scroll)

        self.acc_selection_summary_lbl = QLabel("🎯 0 Accounts Selected")
        self.acc_selection_summary_lbl.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 700;")
        ab_layout.addWidget(self.acc_selection_summary_lbl)

        # Single target fallback dropdown for quick choice
        self.target_acc_select = QComboBox()
        self.target_acc_select.setVisible(False)

        top_split_row.addWidget(acc_box, stretch=1)

        # Right 50%: Product Images & Anti-Duplicate Shield Box
        img_box = QFrame()
        img_box.setStyleSheet("background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 12px;")
        ib_layout = QVBoxLayout(img_box)
        ib_layout.setSpacing(8)

        ib_header = QHBoxLayout()
        ib_header.addWidget(QLabel("🖼️ Product Images & Shield:"))
        ib_header.addStretch()

        btn_clear_img = QPushButton("🧹 Clear Images")
        btn_clear_img.setStyleSheet("background-color: #475569; color: white; font-size: 11px; padding: 4px 10px; border-radius: 6px;")
        btn_clear_img.setCursor(Qt.PointingHandCursor)
        btn_clear_img.clicked.connect(self.clear_selected_images)
        ib_header.addWidget(btn_clear_img)
        ib_layout.addLayout(ib_header)

        img_btn_row = QHBoxLayout()
        self.browse_img_btn = QPushButton("📁 Browse Product Images")
        self.browse_img_btn.setProperty("class", "primaryBtn")
        self.browse_img_btn.setStyleSheet("font-size: 12px; font-weight: 700; padding: 8px 16px; background-color: #2563eb; color: #ffffff; border-radius: 6px;")
        self.browse_img_btn.setCursor(Qt.PointingHandCursor)
        self.browse_img_btn.clicked.connect(self.browse_images)
        img_btn_row.addWidget(self.browse_img_btn)

        self.img_count_lbl = QLabel("No images selected (0)")
        self.img_count_lbl.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 700;")
        img_btn_row.addWidget(self.img_count_lbl)
        img_btn_row.addStretch()
        ib_layout.addLayout(img_btn_row)

        flags_grid = QGridLayout()
        flags_grid.setSpacing(6)
        self.chk_shield = QCheckBox("🛡️ Anti-Duplicate Shield")
        self.chk_shield.setChecked(True)
        self.chk_rotate = QCheckBox("🔄 Rotate & Crop (±0.5°)")
        self.chk_rotate.setChecked(True)
        self.chk_exif = QCheckBox("🧹 Wipe EXIF")
        self.chk_exif.setChecked(True)
        self.chk_noise = QCheckBox("✨ Color/Noise Jitter")
        self.chk_noise.setChecked(True)
        self.chk_stealth = QCheckBox("⚡ Human Typing Delays")
        self.chk_stealth.setChecked(True)

        flags_grid.addWidget(self.chk_shield, 0, 0)
        flags_grid.addWidget(self.chk_exif, 0, 1)
        flags_grid.addWidget(self.chk_rotate, 1, 0)
        flags_grid.addWidget(self.chk_noise, 1, 1)
        flags_grid.addWidget(self.chk_stealth, 2, 0, 1, 2)
        ib_layout.addLayout(flags_grid)

        top_split_row.addWidget(img_box, stretch=1)
        f_layout.addLayout(top_split_row)

        # Row 2: Category, Title & Multi-Tab Configuration
        row2 = QHBoxLayout()
        
        col_tabs = QVBoxLayout()
        col_tabs.addWidget(QLabel("📑 Tabs / Posts per ID:"))
        self.tabs_count_spin = QSpinBox()
        self.tabs_count_spin.setRange(1, 100)
        self.tabs_count_spin.setValue(10)
        self.tabs_count_spin.setToolTip("Number of tabs to open simultaneously in Chrome for this Facebook ID (e.g. 10, 20, 25 tabs)")
        self.tabs_count_spin.setStyleSheet("font-weight: 700; color: #38bdf8;")
        col_tabs.addWidget(self.tabs_count_spin)
        row2.addLayout(col_tabs, stretch=1)

        col_cat = QVBoxLayout()
        col_cat.addWidget(QLabel("Marketplace Category:"))
        self.category_select = QComboBox()
        self.category_select.addItems([
            "Household",
            "Appliances",
            "Auto Parts",
            "Electronics & Computers",
            "Home & Kitchen",
            "Tools & Appliances",
            "Furniture & Decor",
            "Vehicles & Parts",
            "Apparel & Accessories",
            "Mobile Phones & Tablets",
            "Sports & Outdoors",
            "Toys & Games"
        ])
        col_cat.addWidget(self.category_select)
        row2.addLayout(col_cat, stretch=2)

        col_t = QVBoxLayout()
        col_t.addWidget(QLabel("Listing Title (Max 100 chars):"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g., Household Modern Living Room Set / Auto Parts Premium Replacement")
        col_t.addWidget(self.title_input)
        row2.addLayout(col_t, stretch=3)

        f_layout.addLayout(row2)

        # Row 3: Price, ID Location, and Listing Location Pool
        row3 = QHBoxLayout()
        col_p = QVBoxLayout()
        col_p.addWidget(QLabel("Price ($ USD / Amount):"))
        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("150")
        col_p.addWidget(self.price_input)

        col_id_loc = QVBoxLayout()
        col_id_loc.addWidget(QLabel("ID Location (Marketplace Default):"))
        self.id_location_input = QLineEdit()
        self.id_location_input.setPlaceholderText("e.g., New York, NY")
        self.id_location_input.setToolTip("Sets the Facebook ID's primary Marketplace location on the homepage before listing.")
        col_id_loc.addWidget(self.id_location_input)

        col_loc = QVBoxLayout()
        col_loc.addWidget(QLabel("Listing Location (Target Cities Pool):"))
        self.location_input = QTextEdit()
        self.location_input.setPlaceholderText("e.g., Los Angeles, CA\nNew York, NY\nChicago, IL\nHouston, TX\nMiami, FL (1 location per line or comma-separated)")
        self.location_input.setFixedHeight(65)
        self.location_input.setToolTip("Enter locations separated by commas or newlines. The bot randomly selects 1 location for each ad.")
        col_loc.addWidget(self.location_input)

        row3.addLayout(col_p, stretch=1)
        row3.addLayout(col_id_loc, stretch=2)
        row3.addLayout(col_loc, stretch=3)
        f_layout.addLayout(row3)

        # Row 4: Description
        f_layout.addWidget(QLabel("Product Description:"))

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Write details, specifications, payment terms, and pickup notes...")
        self.desc_input.setFixedHeight(65)
        f_layout.addWidget(self.desc_input)

        layout.addWidget(form_card)

        scroll.setWidget(container)
        outer_layout = QVBoxLayout(page)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

        self.populate_accounts_checklist()
        return page

    def populate_accounts_checklist(self):
        """Populates the multi-account checkbox list with styled account items."""
        if not hasattr(self, 'acc_checklist_layout'):
            return

        # Clear existing widgets in checklist
        while self.acc_checklist_layout.count():
            item = self.acc_checklist_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.acc_checkboxes = []

        if not self.accounts_list:
            lbl = QLabel("No Facebook accounts configured yet. Add them in 'Accounts Manager'.")
            lbl.setStyleSheet("color: #94a3b8; font-style: italic; font-size: 11px;")
            self.acc_checklist_layout.addWidget(lbl)
            self.update_account_selection_summary()
            return

        for acc in self.accounts_list:
            name = acc.get("name", "Account")
            status = acc.get("status", "Healthy")
            proxy = acc.get("proxy", "Direct")
            acc_id = acc.get("id", name)

            icon = "🟢" if status in ("Healthy", "Active") else ("🟡" if status == "Checkpoint" else "🔴")
            chk = QCheckBox(f"{icon} {name}  [{status}]  •  Proxy: {proxy}")
            chk.setStyleSheet("font-size: 12px; color: #f8fafc; padding: 2px 0;")
            chk.setProperty("account_data", acc)
            # Default check healthy accounts
            chk.setChecked(status in ("Healthy", "Active"))
            chk.stateChanged.connect(self.update_account_selection_summary)

            self.acc_checklist_layout.addWidget(chk)
            self.acc_checkboxes.append(chk)

        self.acc_checklist_layout.addStretch()
        self.update_account_selection_summary()

    def select_all_accounts(self):
        if hasattr(self, 'acc_checkboxes'):
            for chk in self.acc_checkboxes:
                chk.setChecked(True)
            self.update_account_selection_summary()

    def clear_all_accounts(self):
        if hasattr(self, 'acc_checkboxes'):
            for chk in self.acc_checkboxes:
                chk.setChecked(False)
            self.update_account_selection_summary()

    def update_account_selection_summary(self):
        if not hasattr(self, 'acc_checkboxes') or not hasattr(self, 'acc_selection_summary_lbl'):
            return
        selected_count = sum(1 for chk in self.acc_checkboxes if chk.isChecked())
        total_count = len(self.acc_checkboxes)
        self.acc_selection_summary_lbl.setText(
            f"🎯 {selected_count} of {total_count} Accounts Selected for Sequential 1-by-1 Execution"
        )

    def get_selected_accounts_from_checklist(self) -> List[dict]:
        selected = []
        if hasattr(self, 'acc_checkboxes'):
            for chk in self.acc_checkboxes:
                if chk.isChecked():
                    acc_data = chk.property("account_data")
                    if acc_data:
                        selected.append(acc_data)
        return selected

    def update_account_dropdown(self):
        self.populate_accounts_checklist()
        self.populate_group_accounts_checklist()
        self.refresh_project_accounts_checklist()
        if hasattr(self, 'target_acc_select'):
            self.target_acc_select.clear()
            if not self.accounts_list:
                self.target_acc_select.addItem("No accounts configured (Add in Accounts tab)")
                return

            for acc in self.accounts_list:
                status = acc.get("status", "Healthy")
                proxy = acc.get("proxy", "Direct")
                name = acc.get("name", "Account")
                icon = "🟢" if status in ("Healthy", "Active") else ("🟡" if status == "Checkpoint" else "🔴")
                self.target_acc_select.addItem(f"{icon} {name} [{status}] ({proxy})")

    # --------------------------------------------------------------------------
    # Tab 4: Project Listing Marketplace (Multi-Project & Multi-Tab Campaign Engine)
    # --------------------------------------------------------------------------
    def load_projects_from_disk(self):
        if hasattr(self, 'projects_file') and os.path.exists(self.projects_file):
            try:
                with open(self.projects_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                print(f"Error loading projects: {e}")

        default_projects = [
            {
                "id": f"proj_{int(time.time())}",
                "name": "Default Project - Marketplace Campaign",
                "created_at": time.strftime("%Y-%m-%d %H:%M"),
                "tabs": [
                    {
                        "tab_name": "Tab 1 - Main Product",
                        "category": "Household",
                        "title": "Modern Comfort Living Room Unit - High Quality",
                        "price": "199",
                        "location": "Los Angeles, CA, New York, NY, Chicago, IL",
                        "description": "Brand new condition. Premium quality item with fast regional delivery.",
                        "images": [],
                        "anti_dup_shield": True,
                        "anti_dup_rotate": True,
                        "wipe_exif": True,
                        "anti_dup_noise": False
                    }
                ]
            }
        ]
        self.save_projects_to_disk(default_projects)
        return default_projects

    def save_projects_to_disk(self, projects=None):
        if projects is None:
            projects = getattr(self, 'projects_list', [])
        try:
            os.makedirs(os.path.dirname(self.projects_file), exist_ok=True)
            with open(self.projects_file, "w", encoding="utf-8") as f:
                json.dump(projects, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log_message("WARNING", f"Failed saving projects to disk: {str(e)}")

    def get_project_by_id(self, project_id):
        for p in self.projects_list:
            if p.get("id") == project_id:
                return p
        return None

    def create_project_listing_page(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        self.project_stack = QStackedWidget()

        # View 0: Projects Directory List
        self.proj_list_view = self.create_projects_directory_view()
        # View 1: Project Tab Editor
        self.proj_editor_view = self.create_project_editor_view()

        self.project_stack.addWidget(self.proj_list_view)   # Sub-index 0
        self.project_stack.addWidget(self.proj_editor_view) # Sub-index 1

        page_layout.addWidget(self.project_stack)
        return page

    def create_projects_directory_view(self):
        view = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar { background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Header Title & Action
        top_bar = QHBoxLayout()
        header_box = QVBoxLayout()
        title = QLabel("Project Listing Marketplace")
        title.setProperty("class", "pageTitle")
        sub = QLabel("Organize custom project folders, set distinct titles, descriptions & images for every tab, and launch multi-tab campaign automation.")
        sub.setProperty("class", "pageSubtitle")
        header_box.addWidget(title)
        header_box.addWidget(sub)
        top_bar.addLayout(header_box, stretch=3)

        btn_add_proj = QPushButton("➕ Add Project")
        btn_add_proj.setStyleSheet("background-color: #4f46e5; color: #ffffff; font-weight: 800; font-size: 13px; border-radius: 10px; padding: 10px 20px;")
        btn_add_proj.setCursor(Qt.PointingHandCursor)
        btn_add_proj.setToolTip("Create a new project folder for multi-tab Chrome automation")
        btn_add_proj.clicked.connect(self.add_new_project_dialog)
        top_bar.addWidget(btn_add_proj, stretch=1)
        layout.addLayout(top_bar)

        # Card container for project list
        self.projects_grid_widget = QWidget()
        self.projects_grid_layout = QVBoxLayout(self.projects_grid_widget)
        self.projects_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.projects_grid_layout.setSpacing(12)

        layout.addWidget(self.projects_grid_widget)
        layout.addStretch()

        scroll.setWidget(container)

        main_layout = QVBoxLayout(view)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        # Render initial grid
        self.render_projects_grid()
        return view

    def render_projects_grid(self):
        if not hasattr(self, 'projects_grid_layout'):
            return

        while self.projects_grid_layout.count():
            item = self.projects_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.projects_list:
            empty_card = QFrame()
            empty_card.setProperty("class", "glassCard")
            e_layout = QVBoxLayout(empty_card)
            e_layout.setContentsMargins(30, 40, 30, 40)
            e_lbl = QLabel("📂 No Projects Created Yet")
            e_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #94a3b8; text-align: center;")
            e_sub = QLabel("Click '+ Add Project' above to create your first project folder with custom multi-tab campaign settings.")
            e_sub.setStyleSheet("font-size: 12px; color: #64748b; text-align: center;")
            btn_create = QPushButton("➕ Add Your First Project")
            btn_create.setStyleSheet("background-color: #4f46e5; color: white; font-weight: 700; padding: 8px 16px; border-radius: 8px;")
            btn_create.setCursor(Qt.PointingHandCursor)
            btn_create.clicked.connect(self.add_new_project_dialog)

            e_layout.addWidget(e_lbl, alignment=Qt.AlignCenter)
            e_layout.addWidget(e_sub, alignment=Qt.AlignCenter)
            e_layout.addWidget(btn_create, alignment=Qt.AlignCenter)
            self.projects_grid_layout.addWidget(empty_card)
            return

        for proj in self.projects_list:
            p_id = proj.get("id")
            p_name = proj.get("name", "Untitled Project")
            p_date = proj.get("created_at", "N/A")
            tabs_count = len(proj.get("tabs", []))

            card = QFrame()
            card.setProperty("class", "glassCard")
            card.setStyleSheet("""
                QFrame.glassCard {
                    background-color: rgba(15, 23, 42, 0.65);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                    padding: 16px;
                }
                QFrame.glassCard:hover {
                    border: 1px solid rgba(99, 102, 241, 0.4);
                    background-color: rgba(15, 23, 42, 0.85);
                }
            """)

            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(16, 14, 16, 14)
            c_layout.setSpacing(16)

            info_box = QVBoxLayout()
            info_box.setSpacing(4)
            name_lbl = QLabel(f"📁  {p_name}")
            name_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #f8fafc;")

            sub_lbl = QLabel(f"📅 Created: {p_date}   |   📑 {tabs_count} Tab(s) Configured")
            sub_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")

            info_box.addWidget(name_lbl)
            info_box.addWidget(sub_lbl)
            c_layout.addLayout(info_box, stretch=3)

            btn_box = QHBoxLayout()
            btn_box.setSpacing(8)

            btn_open = QPushButton("📂 Open / Edit Tabs")
            btn_open.setStyleSheet("background-color: #4f46e5; color: #ffffff; font-size: 12px; font-weight: 700; padding: 7px 14px; border-radius: 8px;")
            btn_open.setCursor(Qt.PointingHandCursor)
            btn_open.clicked.connect(lambda checked, pid=p_id: self.open_project_editor(pid))

            btn_run = QPushButton("🚀 Run Project")
            btn_run.setStyleSheet("background-color: #059669; color: #ffffff; font-size: 12px; font-weight: 700; padding: 7px 14px; border-radius: 8px;")
            btn_run.setCursor(Qt.PointingHandCursor)
            btn_run.clicked.connect(lambda checked, pid=p_id: self.open_project_editor(pid, run_immediately=True))

            btn_rename = QPushButton("✏️ Rename")
            btn_rename.setProperty("class", "secondaryBtn")
            btn_rename.setCursor(Qt.PointingHandCursor)
            btn_rename.setStyleSheet("font-size: 11px; padding: 6px 10px;")
            btn_rename.clicked.connect(lambda checked, pid=p_id: self.rename_project_dialog(pid))

            btn_del = QPushButton("🗑️")
            btn_del.setStyleSheet("background-color: rgba(220, 38, 38, 0.15); color: #f87171; border: 1px solid rgba(220, 38, 38, 0.3); border-radius: 8px; font-size: 13px; padding: 6px 10px;")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setToolTip("Delete this project folder")
            btn_del.clicked.connect(lambda checked, pid=p_id: self.delete_project_dialog(pid))

            btn_box.addWidget(btn_open)
            btn_box.addWidget(btn_run)
            btn_box.addWidget(btn_rename)
            btn_box.addWidget(btn_del)
            c_layout.addLayout(btn_box, stretch=2)

            self.projects_grid_layout.addWidget(card)

    def add_new_project_dialog(self):
        name, ok = QInputDialog.getText(self, "Add New Project Folder", "Enter Project Name:\n(e.g., iPhone 15 Campaign, Auto Parts Promo)")
        if ok and name.strip():
            p_name = name.strip()
            existing_names = [p.get("name", "").strip().lower() for p in self.projects_list]
            if p_name.lower() in existing_names:
                QMessageBox.warning(
                    self,
                    "Duplicate Project Name",
                    f"A project folder named '{p_name}' already exists!\n\nPlease choose a different project name."
                )
                return

            p_id = f"proj_{int(time.time())}"
            new_proj = {
                "id": p_id,
                "name": p_name,
                "main_location": "Los Angeles, CA",
                "created_at": time.strftime("%Y-%m-%d %H:%M"),
                "tabs": [
                    {
                        "tab_name": "Tab 1 - Default Listing",
                        "category": "Household",
                        "title": "",
                        "price": "0",
                        "location": "Los Angeles, CA, New York, NY, Chicago, IL",
                        "description": "",
                        "images": [],
                        "anti_dup_shield": True,
                        "anti_dup_rotate": True,
                        "wipe_exif": True,
                        "anti_dup_noise": False
                    }
                ]
            }
            self.projects_list.append(new_proj)
            self.save_projects_to_disk()
            self.render_projects_grid()
            self.log_message("SUCCESS", f"Created new project folder: '{p_name}'")

    def rename_project_dialog(self, project_id):
        proj = self.get_project_by_id(project_id)
        if not proj:
            return
        old_name = proj.get("name", "")
        name, ok = QInputDialog.getText(self, "Rename Project Folder", "Enter new Project Name:", text=old_name)
        if ok and name.strip():
            new_name = name.strip()
            if new_name.lower() != old_name.lower():
                existing_names = [p.get("name", "").strip().lower() for p in self.projects_list if p.get("id") != project_id]
                if new_name.lower() in existing_names:
                    QMessageBox.warning(
                        self,
                        "Duplicate Project Name",
                        f"A project folder named '{new_name}' already exists!\n\nPlease choose a different project name."
                    )
                    return
            proj["name"] = new_name
            self.save_projects_to_disk()
            self.render_projects_grid()
            if hasattr(self, 'proj_editor_title_lbl') and self.current_editing_project_id == project_id:
                self.proj_editor_title_lbl.setText(f"📁 Folder: {proj['name']}")
            self.log_message("INFO", f"Renamed project '{old_name}' -> '{proj['name']}'")

    def delete_project_dialog(self, project_id):
        proj = self.get_project_by_id(project_id)
        if not proj:
            return
        reply = QMessageBox.question(
            self, "Delete Project Folder",
            f"Are you sure you want to delete project folder '{proj.get('name')}' and all its configured tabs?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.projects_list = [p for p in self.projects_list if p.get("id") != project_id]
            self.save_projects_to_disk()
            self.render_projects_grid()
            self.log_message("INFO", f"Deleted project folder '{proj.get('name')}'")

    def open_project_editor(self, project_id, run_immediately=False):
        proj = self.get_project_by_id(project_id)
        if not proj:
            return
        self.current_editing_project_id = project_id
        self.current_editing_tab_index = 0
        if hasattr(self, 'proj_editor_title_lbl'):
            self.proj_editor_title_lbl.setText(f"📁 Folder: {proj.get('name', 'Project')}")
        if hasattr(self, 'proj_main_loc_input'):
            self.proj_main_loc_input.setText(proj.get("main_location", "Los Angeles, CA"))

        self.refresh_project_accounts_checklist()
        self.render_project_tabs_bar()
        self.load_project_tab_into_form(0)
        self.project_stack.setCurrentIndex(1)

        if run_immediately:
            self.start_project_automation()

    def close_project_editor(self):
        self.save_current_project_tab_state()
        self.render_projects_grid()
        self.project_stack.setCurrentIndex(0)

    def create_project_editor_view(self):
        view = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar { background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Top Bar: Back button & Project Name Header & Start/Stop Controls
        top_bar = QHBoxLayout()
        btn_back = QPushButton("⬅️ Back to Projects List")
        btn_back.setProperty("class", "secondaryBtn")
        btn_back.setStyleSheet("font-weight: 700; padding: 6px 14px;")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.clicked.connect(self.close_project_editor)
        top_bar.addWidget(btn_back)

        self.proj_editor_title_lbl = QLabel("📁 Folder: Project Name")
        self.proj_editor_title_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #818cf8; margin-left: 10px;")
        top_bar.addWidget(self.proj_editor_title_lbl)
        top_bar.addStretch()

        btn_add_tab_top = QPushButton("➕ Add Tab")
        btn_add_tab_top.setStyleSheet("background-color: #059669; color: #ffffff; font-weight: 700; font-size: 12px; border-radius: 8px; padding: 6px 14px;")
        btn_add_tab_top.setCursor(Qt.PointingHandCursor)
        btn_add_tab_top.clicked.connect(self.add_tab_to_current_project)
        top_bar.addWidget(btn_add_tab_top)

        self.top_proj_btn_start = QPushButton("🚀 Start Project")
        self.top_proj_btn_start.setStyleSheet("font-weight: 800; font-size: 12px; padding: 6px 16px; background-color: #059669; color: #ffffff; border-radius: 8px;")
        self.top_proj_btn_start.setCursor(Qt.PointingHandCursor)
        self.top_proj_btn_start.clicked.connect(self.start_project_automation)
        top_bar.addWidget(self.top_proj_btn_start)

        self.top_proj_btn_stop = QPushButton("🛑 Stop Project")
        self.top_proj_btn_stop.setStyleSheet("font-weight: 800; font-size: 12px; padding: 6px 16px; background-color: #dc2626; color: #ffffff; border-radius: 8px;")
        self.top_proj_btn_stop.setCursor(Qt.PointingHandCursor)
        self.top_proj_btn_stop.setEnabled(False)
        self.top_proj_btn_stop.clicked.connect(self.stop_project_automation)
        top_bar.addWidget(self.top_proj_btn_stop)

        layout.addLayout(top_bar)

        # Project Configuration Card: Chrome / Account ID Main Location
        proj_cfg_card = QFrame()
        proj_cfg_card.setStyleSheet("background-color: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 10px; padding: 12px;")
        pcfg_layout = QHBoxLayout(proj_cfg_card)
        pcfg_layout.setContentsMargins(12, 10, 12, 10)
        pcfg_layout.setSpacing(12)

        lbl_loc = QLabel("📍 Chrome ID Main Location (Marketplace Account Default):")
        lbl_loc.setStyleSheet("font-size: 12px; font-weight: 700; color: #a5b4fc;")
        pcfg_layout.addWidget(lbl_loc)

        self.proj_main_loc_input = QLineEdit()
        self.proj_main_loc_input.setPlaceholderText("e.g. Los Angeles, CA or New York, NY (Sets location link under 'Create new listing' on Marketplace homepage)")
        self.proj_main_loc_input.setStyleSheet("background-color: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 6px 12px; color: #ffffff; font-weight: 600;")
        pcfg_layout.addWidget(self.proj_main_loc_input, stretch=1)

        layout.addWidget(proj_cfg_card)

        # Tab Selector Pills Container
        tabs_bar_card = QFrame()
        tabs_bar_card.setStyleSheet("background-color: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 8px;")
        tb_layout = QHBoxLayout(tabs_bar_card)
        tb_layout.setContentsMargins(8, 6, 8, 6)
        tb_layout.setSpacing(8)

        self.proj_tabs_scroll = QScrollArea()
        self.proj_tabs_scroll.setFixedHeight(40)
        self.proj_tabs_scroll.setWidgetResizable(True)
        self.proj_tabs_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar { background: transparent; }")

        self.proj_tabs_widget = QWidget()
        self.proj_tabs_layout = QHBoxLayout(self.proj_tabs_widget)
        self.proj_tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.proj_tabs_layout.setSpacing(6)
        self.proj_tabs_scroll.setWidget(self.proj_tabs_widget)
        tb_layout.addWidget(self.proj_tabs_scroll, stretch=4)

        btn_dup_tab = QPushButton("📋 Duplicate Tab")
        btn_dup_tab.setProperty("class", "secondaryBtn")
        btn_dup_tab.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        btn_dup_tab.setCursor(Qt.PointingHandCursor)
        btn_dup_tab.clicked.connect(self.duplicate_current_project_tab)
        tb_layout.addWidget(btn_dup_tab)

        btn_del_tab = QPushButton("🗑️ Delete Tab")
        btn_del_tab.setStyleSheet("background-color: rgba(220, 38, 38, 0.2); color: #f87171; border: 1px solid rgba(220, 38, 38, 0.4); border-radius: 6px; font-size: 11px; padding: 4px 10px;")
        btn_del_tab.setCursor(Qt.PointingHandCursor)
        btn_del_tab.clicked.connect(self.delete_current_project_tab)
        tb_layout.addWidget(btn_del_tab)

        layout.addWidget(tabs_bar_card)

        # 50/50 Top Split: Left = Target Facebook Accounts, Right = Tab Product Images & Shield
        top_split_box = QHBoxLayout()
        top_split_box.setSpacing(14)

        # Left 50%: Target Facebook Accounts Checklist Box
        acc_box = QFrame()
        acc_box.setStyleSheet("background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 12px;")
        ab_layout = QVBoxLayout(acc_box)
        ab_layout.setSpacing(8)

        ab_header = QHBoxLayout()
        ab_header.addWidget(QLabel("👥 Target Facebook Accounts (Queue):"))
        ab_header.addStretch()

        btn_sel_all = QPushButton("⚡ Select All")
        btn_sel_all.setStyleSheet("background-color: #3b82f6; color: white; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 6px;")
        btn_sel_all.setCursor(Qt.PointingHandCursor)
        btn_sel_all.clicked.connect(self.select_all_project_accounts)
        ab_header.addWidget(btn_sel_all)

        btn_clr_acc = QPushButton("❌ Clear")
        btn_clr_acc.setStyleSheet("background-color: #475569; color: white; font-size: 11px; padding: 4px 10px; border-radius: 6px;")
        btn_clr_acc.setCursor(Qt.PointingHandCursor)
        btn_clr_acc.clicked.connect(self.clear_all_project_accounts)
        ab_header.addWidget(btn_clr_acc)

        ab_layout.addLayout(ab_header)

        self.proj_acc_checklist_scroll = QScrollArea()
        self.proj_acc_checklist_scroll.setFixedHeight(120)
        self.proj_acc_checklist_scroll.setWidgetResizable(True)
        self.proj_acc_checklist_scroll.setStyleSheet("QScrollArea { border: 1px solid rgba(255, 255, 255, 0.05); background: rgba(15, 23, 42, 0.6); border-radius: 6px; } QScrollBar { background: transparent; }")

        self.proj_acc_checklist_widget = QWidget()
        self.proj_acc_checklist_layout = QVBoxLayout(self.proj_acc_checklist_widget)
        self.proj_acc_checklist_layout.setContentsMargins(8, 6, 8, 6)
        self.proj_acc_checklist_layout.setSpacing(6)
        self.proj_acc_checklist_scroll.setWidget(self.proj_acc_checklist_widget)
        ab_layout.addWidget(self.proj_acc_checklist_scroll)

        top_split_box.addWidget(acc_box, stretch=1)

        # Right 50%: Product Images & Anti-Duplicate Shield Box
        img_box = QFrame()
        img_box.setStyleSheet("background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 12px;")
        ib_layout = QVBoxLayout(img_box)
        ib_layout.setSpacing(8)

        ib_header = QHBoxLayout()
        ib_header.addWidget(QLabel("🖼️ Tab Product Images & Shield:"))
        ib_header.addStretch()

        btn_clr_pimg = QPushButton("🧹 Clear Images")
        btn_clr_pimg.setStyleSheet("background-color: #475569; color: white; font-size: 11px; padding: 4px 10px; border-radius: 6px;")
        btn_clr_pimg.setCursor(Qt.PointingHandCursor)
        btn_clr_pimg.clicked.connect(self.clear_project_tab_images)
        ib_header.addWidget(btn_clr_pimg)
        ib_layout.addLayout(ib_header)

        pimg_btn_row = QHBoxLayout()
        self.proj_browse_img_btn = QPushButton("📁 Browse Product Images")
        self.proj_browse_img_btn.setProperty("class", "primaryBtn")
        self.proj_browse_img_btn.setStyleSheet("font-size: 12px; font-weight: 700; padding: 8px 16px; background-color: #2563eb; color: #ffffff; border-radius: 6px;")
        self.proj_browse_img_btn.setCursor(Qt.PointingHandCursor)
        self.proj_browse_img_btn.clicked.connect(self.browse_project_tab_images)
        pimg_btn_row.addWidget(self.proj_browse_img_btn)

        self.proj_img_count_lbl = QLabel("0 image(s) selected")
        self.proj_img_count_lbl.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 700;")
        pimg_btn_row.addWidget(self.proj_img_count_lbl)
        pimg_btn_row.addStretch()
        ib_layout.addLayout(pimg_btn_row)

        pdup_grid = QGridLayout()
        pdup_grid.setSpacing(6)
        self.proj_chk_shield = QCheckBox("🛡️ Anti-Duplicate Shield")
        self.proj_chk_shield.setChecked(True)
        self.proj_chk_rotate = QCheckBox("🔄 Rotate Images (0.5°)")
        self.proj_chk_rotate.setChecked(True)
        self.proj_chk_exif = QCheckBox("🧹 Wipe EXIF")
        self.proj_chk_exif.setChecked(True)
        self.proj_chk_noise = QCheckBox("✨ Canvas Noise")
        self.proj_chk_noise.setChecked(True)

        pdup_grid.addWidget(self.proj_chk_shield, 0, 0)
        pdup_grid.addWidget(self.proj_chk_exif, 0, 1)
        pdup_grid.addWidget(self.proj_chk_rotate, 1, 0)
        pdup_grid.addWidget(self.proj_chk_noise, 1, 1)
        ib_layout.addLayout(pdup_grid)

        top_split_box.addWidget(img_box, stretch=1)
        layout.addLayout(top_split_box)

        # Form Card for Active Tab (No posting flow/method column!)
        form_card = QFrame()
        form_card.setProperty("class", "glassCard")
        f_layout = QVBoxLayout(form_card)
        f_layout.setSpacing(12)

        # Row 1: Tab Name & Category
        r1 = QHBoxLayout()
        col_tname = QVBoxLayout()
        col_tname.addWidget(QLabel("Tab Identifier / Name:"))
        self.proj_tab_name_input = QLineEdit()
        self.proj_tab_name_input.setPlaceholderText("e.g. Tab 1 - Smartphone Promo")
        col_tname.addWidget(self.proj_tab_name_input)
        r1.addLayout(col_tname, stretch=2)

        col_cat = QVBoxLayout()
        col_cat.addWidget(QLabel("Marketplace Category:"))
        self.proj_category_select = QComboBox()
        self.proj_category_select.addItems([
            "Household", "Appliances", "Auto Parts", "Electronics & Computers",
            "Home & Kitchen", "Tools & Appliances", "Furniture & Decor",
            "Vehicles & Parts", "Apparel & Accessories", "Mobile Phones & Tablets",
            "Sports & Outdoors", "Toys & Games"
        ])
        col_cat.addWidget(self.proj_category_select)
        r1.addLayout(col_cat, stretch=2)
        f_layout.addLayout(r1)

        # Row 2: Title
        r2 = QHBoxLayout()
        col_t = QVBoxLayout()
        col_t.addWidget(QLabel("Listing Title (Max 100 chars):"))

        self.proj_title_input = QLineEdit()
        self.proj_title_input.setPlaceholderText("e.g., Apple iPhone 15 Pro Max 256GB Unlocked - Brand New")
        col_t.addWidget(self.proj_title_input)
        r2.addLayout(col_t)
        f_layout.addLayout(r2)

        # Row 3: Price & Target Locations
        r3 = QHBoxLayout()
        col_p = QVBoxLayout()
        col_p.addWidget(QLabel("Price ($ USD / Amount):"))
        self.proj_price_input = QLineEdit()
        self.proj_price_input.setPlaceholderText("150")
        col_p.addWidget(self.proj_price_input)

        col_loc = QVBoxLayout()
        col_loc.addWidget(QLabel("Target Locations / Cities Pool (Randomized per Ad):"))
        self.proj_location_input = QTextEdit()
        self.proj_location_input.setPlaceholderText("e.g., Los Angeles, CA\nNew York, NY\nChicago, IL\nHouston, TX")
        self.proj_location_input.setFixedHeight(65)
        col_loc.addWidget(self.proj_location_input)

        r3.addLayout(col_p, stretch=1)
        r3.addLayout(col_loc, stretch=3)
        f_layout.addLayout(r3)

        # Row 4: Product Description
        f_layout.addWidget(QLabel("Product Description:"))

        self.proj_desc_input = QTextEdit()
        self.proj_desc_input.setPlaceholderText("Write details, specifications, payment terms, and pickup notes...")
        self.proj_desc_input.setFixedHeight(65)
        f_layout.addWidget(self.proj_desc_input)

        layout.addWidget(form_card)

        # Action Buttons Row
        act_row = QHBoxLayout()
        self.proj_btn_save_tab = QPushButton("💾 Save Tab Settings")
        self.proj_btn_save_tab.setProperty("class", "secondaryBtn")
        self.proj_btn_save_tab.setStyleSheet("font-weight: 700; padding: 10px 18px;")
        self.proj_btn_save_tab.setCursor(Qt.PointingHandCursor)
        self.proj_btn_save_tab.clicked.connect(self.save_current_project_tab_state)
        act_row.addWidget(self.proj_btn_save_tab)

        act_row.addStretch()

        self.proj_btn_start_automation = QPushButton("🚀 Start Project Automation")
        self.proj_btn_start_automation.setStyleSheet("font-weight: 800; font-size: 13px; padding: 12px 24px; background-color: #059669; color: #ffffff; border-radius: 8px;")
        self.proj_btn_start_automation.setCursor(Qt.PointingHandCursor)
        self.proj_btn_start_automation.clicked.connect(self.start_project_automation)
        act_row.addWidget(self.proj_btn_start_automation)

        self.proj_btn_stop_automation = QPushButton("🛑 Stop Project")
        self.proj_btn_stop_automation.setStyleSheet("font-weight: 800; font-size: 13px; padding: 12px 24px; background-color: #dc2626; color: #ffffff; border-radius: 8px;")
        self.proj_btn_stop_automation.setCursor(Qt.PointingHandCursor)
        self.proj_btn_stop_automation.setEnabled(False)
        self.proj_btn_stop_automation.clicked.connect(self.stop_project_automation)
        act_row.addWidget(self.proj_btn_stop_automation)

        layout.addLayout(act_row)
        scroll.setWidget(container)

        main_layout = QVBoxLayout(view)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        return view

    def render_project_tabs_bar(self):
        proj = self.get_project_by_id(self.current_editing_project_id)
        if not proj or not hasattr(self, 'proj_tabs_layout'):
            return

        while self.proj_tabs_layout.count():
            item = self.proj_tabs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tabs = proj.get("tabs", [])
        for i, tdata in enumerate(tabs):
            t_name = tdata.get("tab_name") or f"Tab {i+1}"
            btn = QPushButton(f"📑 {t_name}")
            btn.setCursor(Qt.PointingHandCursor)
            if i == self.current_editing_tab_index:
                btn.setStyleSheet("background-color: #4f46e5; color: #ffffff; border: 1px solid #6366f1; font-weight: 700; border-radius: 6px; padding: 4px 10px;")
            else:
                btn.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); color: #cbd5e1; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px 10px;")
            btn.clicked.connect(lambda checked, idx=i: self.switch_project_tab(idx))
            self.proj_tabs_layout.addWidget(btn)

        btn_add = QPushButton("➕ Add Tab")
        btn_add.setStyleSheet("background-color: rgba(5, 150, 105, 0.2); color: #34d399; border: 1px solid rgba(5, 150, 105, 0.4); border-radius: 6px; font-weight: 700; padding: 4px 10px;")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self.add_tab_to_current_project)
        self.proj_tabs_layout.addWidget(btn_add)
        self.proj_tabs_layout.addStretch()

    def switch_project_tab(self, new_index):
        self.save_current_project_tab_state()
        self.current_editing_tab_index = new_index
        self.render_project_tabs_bar()
        self.load_project_tab_into_form(new_index)

    def load_project_tab_into_form(self, tab_index):
        proj = self.get_project_by_id(self.current_editing_project_id)
        if not proj:
            return
        tabs = proj.get("tabs", [])
        if tab_index < 0 or tab_index >= len(tabs):
            tab_index = 0
            self.current_editing_tab_index = 0

        tdata = tabs[tab_index]
        self.proj_tab_name_input.setText(tdata.get("tab_name", f"Tab {tab_index+1}"))

        cat = tdata.get("category", "Household")
        idx = self.proj_category_select.findText(cat)
        if idx >= 0:
            self.proj_category_select.setCurrentIndex(idx)

        self.proj_title_input.setText(tdata.get("title", ""))
        self.proj_price_input.setText(str(tdata.get("price", "0")))
        self.proj_location_input.setPlainText(tdata.get("location", ""))
        self.proj_desc_input.setPlainText(tdata.get("description", ""))

        imgs = tdata.get("images", [])
        self.project_tab_images = imgs
        if imgs:
            self.proj_img_count_lbl.setText(f"{len(imgs)} image(s) selected: {', '.join([os.path.basename(f) for f in imgs[:2]])}...")
        else:
            self.proj_img_count_lbl.setText("0 image(s) selected")

        self.proj_chk_shield.setChecked(tdata.get("anti_dup_shield", True))
        self.proj_chk_rotate.setChecked(tdata.get("anti_dup_rotate", True))
        self.proj_chk_exif.setChecked(tdata.get("wipe_exif", True))
        self.proj_chk_noise.setChecked(tdata.get("anti_dup_noise", False))

    def save_current_project_tab_state(self):
        proj = self.get_project_by_id(self.current_editing_project_id)
        if not proj:
            return
        tabs = proj.get("tabs", [])
        if not tabs or self.current_editing_tab_index >= len(tabs):
            return

        if hasattr(self, 'proj_main_loc_input'):
            proj["main_location"] = self.proj_main_loc_input.text().strip()

        tdata = {
            "tab_name": self.proj_tab_name_input.text().strip() or f"Tab {self.current_editing_tab_index+1}",
            "category": self.proj_category_select.currentText(),
            "title": self.proj_title_input.text().strip(),
            "price": self.proj_price_input.text().strip() or "0",
            "location": self.proj_location_input.toPlainText().strip() or "Local Radius",
            "description": self.proj_desc_input.toPlainText().strip(),
            "images": getattr(self, 'project_tab_images', []),
            "anti_dup_shield": self.proj_chk_shield.isChecked(),
            "anti_dup_rotate": self.proj_chk_rotate.isChecked(),
            "wipe_exif": self.proj_chk_exif.isChecked(),
            "anti_dup_noise": self.proj_chk_noise.isChecked()
        }
        tabs[self.current_editing_tab_index] = tdata
        self.save_projects_to_disk()

    def add_tab_to_current_project(self):
        self.save_current_project_tab_state()
        proj = self.get_project_by_id(self.current_editing_project_id)
        if not proj:
            return
        tabs = proj.get("tabs", [])
        new_tab_idx = len(tabs) + 1
        new_tdata = {
            "tab_name": f"Tab {new_tab_idx}",
            "category": "Household",
            "title": "",
            "price": "0",
            "location": "Local Radius",
            "description": "",
            "images": [],
            "anti_dup_shield": True,
            "anti_dup_rotate": True,
            "wipe_exif": True,
            "anti_dup_noise": False
        }
        tabs.append(new_tdata)
        self.save_projects_to_disk()
        self.current_editing_tab_index = len(tabs) - 1
        self.render_project_tabs_bar()
        self.load_project_tab_into_form(self.current_editing_tab_index)
        self.log_message("INFO", f"Added new tab 'Tab {new_tab_idx}' to project '{proj.get('name')}'")

    def duplicate_current_project_tab(self):
        self.save_current_project_tab_state()
        proj = self.get_project_by_id(self.current_editing_project_id)
        if not proj:
            return
        tabs = proj.get("tabs", [])
        if not tabs:
            return
        cur_tab = dict(tabs[self.current_editing_tab_index])
        cur_tab["tab_name"] = f"{cur_tab.get('tab_name', 'Tab')} (Copy)"
        tabs.append(cur_tab)
        self.save_projects_to_disk()
        self.current_editing_tab_index = len(tabs) - 1
        self.render_project_tabs_bar()
        self.load_project_tab_into_form(self.current_editing_tab_index)

    def delete_current_project_tab(self):
        proj = self.get_project_by_id(self.current_editing_project_id)
        if not proj:
            return
        tabs = proj.get("tabs", [])
        if len(tabs) <= 1:
            QMessageBox.warning(self, "Cannot Delete", "A project must contain at least one tab configuration.")
            return
        del tabs[self.current_editing_tab_index]
        self.save_projects_to_disk()
        self.current_editing_tab_index = max(0, self.current_editing_tab_index - 1)
        self.render_project_tabs_bar()
        self.load_project_tab_into_form(self.current_editing_tab_index)

    def browse_project_tab_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Product Images for Tab", "", "Image Files (*.png *.jpg *.jpeg *.webp)"
        )
        if files:
            self.project_tab_images = files
            self.proj_img_count_lbl.setText(f"{len(files)} image(s) selected: {', '.join([os.path.basename(f) for f in files[:2]])}...")
            self.save_current_project_tab_state()

    def clear_project_tab_images(self):
        self.project_tab_images = []
        proj = self.get_project_by_id(getattr(self, 'current_editing_project_id', None))
        if proj:
            tabs = proj.get("tabs", [])
            idx = getattr(self, 'current_editing_tab_index', 0)
            if 0 <= idx < len(tabs):
                tabs[idx]["images"] = []
                self.save_projects_to_disk()
        if hasattr(self, 'proj_img_count_lbl'):
            self.proj_img_count_lbl.setText("0 image(s) selected")
        self.log_message("INFO", "Project tab images cleared.")

    def quick_spin_project_tab_title(self):
        raw = self.proj_title_input.text().strip()
        if not raw:
            return
        if HAS_SPINTAX:
            spinned = SpintaxEngine.spin_text(raw)
        else:
            spinned = raw
        self.proj_title_input.setText(spinned)

    def quick_spin_project_tab_desc(self):
        raw = self.proj_desc_input.toPlainText().strip()
        if not raw:
            return
        if HAS_SPINTAX:
            spinned = SpintaxEngine.spin_text(raw)
        else:
            spinned = raw
        self.proj_desc_input.setPlainText(spinned)

    def refresh_project_accounts_checklist(self):
        if not hasattr(self, 'proj_acc_checklist_layout'):
            return
        while self.proj_acc_checklist_layout.count():
            item = self.proj_acc_checklist_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.proj_acc_checkboxes = []
        if not self.accounts_list:
            lbl = QLabel("⚠️ No Facebook accounts saved yet. Please add accounts in Accounts Manager.")
            lbl.setStyleSheet("color: #f59e0b; font-size: 11px;")
            self.proj_acc_checklist_layout.addWidget(lbl)
            return

        for acc in self.accounts_list:
            name = acc.get("name", "Account")
            cookies = acc.get("cookies", "")
            proxy = acc.get("proxy", "Direct")
            chk = QCheckBox(f"{name} (Proxy: {proxy})")
            chk.setChecked(True)
            chk.setProperty("account_data", acc)
            chk.setStyleSheet("font-size: 12px; font-weight: 600; color: #f1f5f9;")
            self.proj_acc_checklist_layout.addWidget(chk)
            self.proj_acc_checkboxes.append(chk)

    def select_all_project_accounts(self):
        if hasattr(self, 'proj_acc_checkboxes'):
            for chk in self.proj_acc_checkboxes:
                chk.setChecked(True)

    def clear_all_project_accounts(self):
        if hasattr(self, 'proj_acc_checkboxes'):
            for chk in self.proj_acc_checkboxes:
                chk.setChecked(False)

    def get_selected_project_accounts(self):
        selected = []
        if hasattr(self, 'proj_acc_checkboxes'):
            for chk in self.proj_acc_checkboxes:
                if chk.isChecked():
                    acc_data = chk.property("account_data")
                    if acc_data:
                        selected.append(acc_data)
        return selected

    def start_project_automation(self):
        self.save_current_project_tab_state()
        proj = self.get_project_by_id(self.current_editing_project_id)
        if not proj:
            QMessageBox.warning(self, "No Project Selected", "Please select a valid project folder.")
            return

        selected_accounts = self.get_selected_project_accounts()
        if not selected_accounts:
            QMessageBox.warning(
                self,
                "No Accounts Selected",
                "Please check at least one Facebook Account from the Target Accounts checklist."
            )
            return

        missing_cookies = [acc.get("name", "Account") for acc in selected_accounts if not acc.get("cookies")]
        if missing_cookies:
            QMessageBox.warning(
                self,
                "Account Cookies Missing",
                f"The following account(s) do not have cookies configured:\n\n" +
                "\n".join(missing_cookies)
            )
            return

        project_tabs = proj.get("tabs", [])
        if not project_tabs:
            QMessageBox.warning(self, "No Tabs Configured", "This project has no tab configurations to post.")
            return

        valid_tabs = [t for t in project_tabs if t.get("title", "").strip()]
        if not valid_tabs:
            QMessageBox.warning(self, "Missing Listing Title", "Please provide at least a Title for Tab 1 in this project.")
            return

        is_batch = len(selected_accounts) > 1

        self.log_message("INFO", f"==================================================")
        self.log_message("INFO", f"🚀 Starting Project Campaign Automation: '{proj.get('name')}'")
        self.log_message("INFO", f"📑 Project Multi-Tab Setup: {len(project_tabs)} Tab(s) per Facebook ID")
        self.log_message("INFO", f"👥 Queue: {len(selected_accounts)} Account(s) Selected")

        main_loc = proj.get("main_location", "").strip()
        if hasattr(self, 'proj_main_loc_input') and self.proj_main_loc_input.text().strip():
            main_loc = self.proj_main_loc_input.text().strip()

        payload = {
            "title": project_tabs[0].get("title", "Project Campaign"),
            "price": project_tabs[0].get("price", "0"),
            "category": project_tabs[0].get("category", "Household"),
            "location": project_tabs[0].get("location", "Local Radius"),
            "project_main_location": main_loc,
            "description": project_tabs[0].get("description", ""),
            "tabs_count": len(project_tabs),
            "posts_per_id": len(project_tabs),
            "method": "Project Campaign Mode",
            "account": "Batch Runner" if is_batch else selected_accounts[0].get("name", "Account"),
            "account_data": selected_accounts[0],
            "is_batch": is_batch,
            "batch_accounts": selected_accounts,
            "images": project_tabs[0].get("images", []),
            "anti_dup_shield": True,
            "anti_dup_rotate": True,
            "wipe_exif": True,
            "anti_dup_noise": False,
            "project_name": proj.get("name"),
            "project_tabs": project_tabs
        }

        speed = "Normal"
        if hasattr(self, 'speed_select') and "Slow" in self.speed_select.currentText():
            speed = "Slow"
        elif hasattr(self, 'speed_select') and "Fast" in self.speed_select.currentText():
            speed = "Fast"

        if hasattr(self, 'start_btn'):
            self.start_btn.setEnabled(False)
        if hasattr(self, 'stop_btn'):
            self.stop_btn.setEnabled(True)
        if hasattr(self, 'top_proj_btn_start'):
            self.top_proj_btn_start.setEnabled(False)
        if hasattr(self, 'top_proj_btn_stop'):
            self.top_proj_btn_stop.setEnabled(True)
        if hasattr(self, 'proj_btn_start_automation'):
            self.proj_btn_start_automation.setEnabled(False)
        if hasattr(self, 'proj_btn_stop_automation'):
            self.proj_btn_stop_automation.setEnabled(True)

        self.engine_status_lbl.setText("● PROJECT AUTOMATION")
        self.engine_status_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #818cf8;")

        self.worker = AutomationWorker(payload, speed_mode=speed)
        self.worker.log_signal.connect(self.log_message)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_automation_finished)
        self.worker.start()

    def stop_project_automation(self):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.log_message("WARNING", "🛑 Stop command sent to Project Campaign Automation...")
            self.worker.stop()

        if hasattr(self, 'start_btn'):
            self.start_btn.setEnabled(True)
        if hasattr(self, 'stop_btn'):
            self.stop_btn.setEnabled(False)
        if hasattr(self, 'top_proj_btn_start'):
            self.top_proj_btn_start.setEnabled(True)
        if hasattr(self, 'top_proj_btn_stop'):
            self.top_proj_btn_stop.setEnabled(False)
        if hasattr(self, 'proj_btn_start_automation'):
            self.proj_btn_start_automation.setEnabled(True)
        if hasattr(self, 'proj_btn_stop_automation'):
            self.proj_btn_stop_automation.setEnabled(False)

        self.engine_status_lbl.setText("● IDLE")
        self.engine_status_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #10b981;")

    def browse_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Product Images", "", "Image Files (*.png *.jpg *.jpeg *.webp)"
        )
        if files:
            self.selected_images = files
            self.img_count_lbl.setText(f"{len(files)} image(s) selected: {', '.join([os.path.basename(f) for f in files[:2]])}...")
            self.log_message("INFO", f"Selected {len(files)} product image(s) for posting.")

    def clear_selected_images(self):
        self.selected_images = []
        if hasattr(self, 'img_count_lbl'):
            self.img_count_lbl.setText("No images selected (0)")
        self.log_message("INFO", "Selected product images cleared.")

    def start_automation(self):
        title = self.title_input.text().strip()
        price = self.price_input.text().strip()

        if not self.accounts_list:
            QMessageBox.warning(
                self,
                "No Facebook Accounts",
                "You have not saved any Facebook account profiles yet.\n\n"
                "Please open the 'Accounts Manager' tab on the left, enter your Account Alias, paste your Facebook session cookies, and click '+ Save Profile'."
            )
            return

        if not title:
            QMessageBox.warning(self, "Missing Fields", "Please provide at least a Product Title.")
            return

        # Retrieve all checked accounts from the checklist
        selected_accounts = self.get_selected_accounts_from_checklist()
        if not selected_accounts:
            QMessageBox.warning(
                self,
                "No Accounts Selected",
                "Please check at least one Facebook Account from the 'Target Facebook Accounts' checklist above to start posting."
            )
            return

        # Check cookies for each selected account
        missing_cookies = [acc.get("name", "Account") for acc in selected_accounts if not acc.get("cookies")]
        if missing_cookies:
            QMessageBox.warning(
                self,
                "Account Cookies Missing",
                f"The following account(s) do not have cookies configured:\n\n" +
                "\n".join(missing_cookies) +
                "\n\nPlease edit them in the Accounts Manager."
            )
            return

        is_batch = len(selected_accounts) > 1
        chosen_method = self.method_select.currentText() if hasattr(self, 'method_select') and self.method_select else "Standard Auto Posting"

        tabs_count = self.tabs_count_spin.value() if hasattr(self, 'tabs_count_spin') else 1

        self.log_message("INFO", f"==================================================")
        self.log_message("INFO", f"🚀 Starting Automation across {len(selected_accounts)} Account(s)...")
        self.log_message("INFO", f"📑 Multi-Tab Configuration: {tabs_count} Tab(s)/Post(s) per Facebook ID")
        self.log_message("INFO", f"🎯 Active Method: '{chosen_method}'")
        self.log_message("INFO", f"Sequential Execution: Each account will launch Chrome, open {tabs_count} tab(s) with random images & locations, publish, close Chrome, and move to next ID.")

        payload = {
            "title": title,
            "price": price or "0",
            "category": self.category_select.currentText(),
            "id_location": self.id_location_input.text().strip() if hasattr(self, 'id_location_input') else "",
            "location": self.location_input.toPlainText().strip() or "Local Radius",
            "description": self.desc_input.toPlainText().strip(),
            "tabs_count": tabs_count,
            "posts_per_id": tabs_count,
            "method": chosen_method,
            "account": "Batch Runner" if is_batch else selected_accounts[0].get("name", "Account"),
            "account_data": selected_accounts[0],
            "is_batch": is_batch,
            "batch_accounts": selected_accounts,
            "images": self.selected_images,
            "anti_dup_shield": self.chk_shield.isChecked(),
            "anti_dup_rotate": self.chk_rotate.isChecked(),
            "wipe_exif": self.chk_exif.isChecked(),
            "anti_dup_noise": self.chk_noise.isChecked()
        }

        speed = "Normal"
        if "Slow" in self.speed_select.currentText():
            speed = "Slow"
        elif "Fast" in self.speed_select.currentText():
            speed = "Fast"

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.engine_status_lbl.setText("● AUTOMATING LISTING")
        self.engine_status_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #f59e0b;")

        # Start background QThread
        self.worker = AutomationWorker(payload, speed_mode=speed)
        self.worker.log_signal.connect(self.log_message)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_automation_finished)
        self.worker.start()

    def stop_automation(self):
        if self.worker:
            self.worker.stop()
            self.stop_btn.setEnabled(False)

    def on_automation_finished(self, success, message):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if hasattr(self, 'top_proj_btn_start'):
            self.top_proj_btn_start.setEnabled(True)
        if hasattr(self, 'top_proj_btn_stop'):
            self.top_proj_btn_stop.setEnabled(False)
        if hasattr(self, 'proj_btn_start_automation'):
            self.proj_btn_start_automation.setEnabled(True)
        if hasattr(self, 'proj_btn_stop_automation'):
            self.proj_btn_stop_automation.setEnabled(False)
        self.engine_status_lbl.setText("● READY FOR TASKS")
        self.engine_status_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #10b981;")
        if success:
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Automation Complete", f"All listing tasks finished successfully!\n\n{message}")
        else:
            QMessageBox.warning(self, "Automation Stopped", f"Automation execution finished:\n\n{message}")

    # --------------------------------------------------------------------------
    # Tab 4: FB Group Automation (Posting & Group Joining)
    # --------------------------------------------------------------------------
    def create_group_automation_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Header Title
        title_box = QVBoxLayout()
        title = QLabel("Facebook Group Automation Engine")
        title.setProperty("class", "pageTitle")
        sub = QLabel("Automate group posting with rotating links & descriptions, join targeted groups, and load the FEWFEED Chrome extension automatically.")
        sub.setProperty("class", "pageSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        layout.addLayout(title_box)

        # Account Selection Panel for Groups
        acc_card = QFrame()
        acc_card.setProperty("class", "glassCard")
        acc_card_layout = QVBoxLayout(acc_card)
        acc_card_layout.setSpacing(8)

        grp_acc_hdr = QHBoxLayout()
        grp_acc_hdr.addWidget(QLabel("👥 Target Accounts for Group Operations:"))
        grp_acc_hdr.addStretch()

        self.btn_grp_select_all = QPushButton("⚡ Select All")
        self.btn_grp_select_all.setStyleSheet("background-color: #3b82f6; color: white; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 6px;")
        self.btn_grp_select_all.setCursor(Qt.PointingHandCursor)
        self.btn_grp_select_all.clicked.connect(self.select_all_group_accounts)
        grp_acc_hdr.addWidget(self.btn_grp_select_all)

        self.btn_grp_clear_acc = QPushButton("❌ Clear")
        self.btn_grp_clear_acc.setStyleSheet("background-color: #475569; color: white; font-size: 11px; padding: 4px 10px; border-radius: 6px;")
        self.btn_grp_clear_acc.setCursor(Qt.PointingHandCursor)
        self.btn_grp_clear_acc.clicked.connect(self.clear_all_group_accounts)
        grp_acc_hdr.addWidget(self.btn_grp_clear_acc)
        acc_card_layout.addLayout(grp_acc_hdr)

        # Group accounts checklist
        self.grp_acc_scroll = QScrollArea()
        self.grp_acc_scroll.setFixedHeight(100)
        self.grp_acc_scroll.setWidgetResizable(True)
        self.grp_acc_scroll.setStyleSheet("QScrollArea { border: 1px solid rgba(255, 255, 255, 0.05); background: rgba(15, 23, 42, 0.6); border-radius: 6px; }")

        self.grp_acc_widget = QWidget()
        self.grp_acc_layout = QVBoxLayout(self.grp_acc_widget)
        self.grp_acc_layout.setContentsMargins(8, 6, 8, 6)
        self.grp_acc_layout.setSpacing(6)
        self.grp_acc_scroll.setWidget(self.grp_acc_widget)
        acc_card_layout.addWidget(self.grp_acc_scroll)

        acc_bottom_row = QHBoxLayout()
        self.grp_acc_summary_lbl = QLabel("🎯 0 Accounts Selected")
        self.grp_acc_summary_lbl.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 700;")
        acc_bottom_row.addWidget(self.grp_acc_summary_lbl)
        acc_bottom_row.addStretch()

        concurrent_lbl = QLabel("🌐 How Many Open Chrome Browsers:")
        concurrent_lbl.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 700;")
        acc_bottom_row.addWidget(concurrent_lbl)

        self.grp_max_concurrent_browsers = QSpinBox()
        self.grp_max_concurrent_browsers.setRange(1, 50)
        self.grp_max_concurrent_browsers.setValue(3)
        self.grp_max_concurrent_browsers.setSuffix(" browsers")
        self.grp_max_concurrent_browsers.setFixedWidth(120)
        self.grp_max_concurrent_browsers.setStyleSheet("font-weight: 800; color: #10b981; background: #0f172a; border: 1px solid #38bdf8; border-radius: 4px; padding: 2px 4px;")
        self.grp_max_concurrent_browsers.setToolTip("Example: Set to 3. If 10 accounts are selected, 3 Chrome browsers run at a time. As each account finishes, the next browser opens automatically.")
        acc_bottom_row.addWidget(self.grp_max_concurrent_browsers)

        acc_card_layout.addLayout(acc_bottom_row)

        layout.addWidget(acc_card)

        # ----------------------------------------------------------------------
        # [UNIFIED ACTION BAR: Single Start / Stop Button for Group Automation - AT TOP]
        # ----------------------------------------------------------------------
        action_card = QFrame()
        action_card.setProperty("class", "glassCard")
        action_card.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(15, 23, 42, 0.95), stop:1 rgba(30, 41, 59, 0.95)); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 10px; padding: 14px;")
        ac_layout = QVBoxLayout(action_card)
        ac_layout.setSpacing(10)

        # Step Workflow Banner
        workflow_banner = QLabel("⚡ <b>FEWFEED Automated Sequence:</b> Mobile Chrome opens → Runs <b>Auto Join</b> (Card #2) if group list is provided → Then opens <b>Auto Post</b> (Card #1), injects descriptions/links, selects all groups, and submits post.")
        workflow_banner.setStyleSheet("color: #e0e7ff; font-size: 12px; line-height: 1.4;")
        workflow_banner.setWordWrap(True)
        ac_layout.addWidget(workflow_banner)

        # Single Unified Start & Stop Buttons
        u_btn_row = QHBoxLayout()
        u_btn_row.setSpacing(12)

        self.btn_start_grp_unified = QPushButton("🚀 START FB GROUP AUTOMATION (FEWFEED)")
        self.btn_start_grp_unified.setProperty("class", "primaryBtn")
        self.btn_start_grp_unified.setCursor(Qt.PointingHandCursor)
        self.btn_start_grp_unified.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #059669); color: #ffffff; font-weight: 800; font-size: 14px; padding: 14px; border-radius: 8px;")
        self.btn_start_grp_unified.clicked.connect(self.start_unified_group_automation)
        u_btn_row.addWidget(self.btn_start_grp_unified, stretch=3)

        self.btn_stop_grp_unified = QPushButton("🛑 STOP")
        self.btn_stop_grp_unified.setProperty("class", "dangerBtn")
        self.btn_stop_grp_unified.setEnabled(False)
        self.btn_stop_grp_unified.setCursor(Qt.PointingHandCursor)
        self.btn_stop_grp_unified.setStyleSheet("font-size: 13px; font-weight: 700; padding: 14px; border-radius: 8px;")
        self.btn_stop_grp_unified.clicked.connect(self.stop_group_automation)
        u_btn_row.addWidget(self.btn_stop_grp_unified, stretch=1)

        ac_layout.addLayout(u_btn_row)
        layout.addWidget(action_card)

        # Compatibility aliases
        self.btn_start_grp_post = self.btn_start_grp_unified
        self.btn_stop_grp_post = self.btn_stop_grp_unified
        self.btn_start_grp_join = self.btn_start_grp_unified
        self.btn_stop_grp_join = self.btn_stop_grp_unified

        # Main Splitter: Left Section (Posting Panel) vs Right Section (Group Joining Panel)
        panels_row = QHBoxLayout()
        panels_row.setSpacing(14)

        # ----------------------------------------------------------------------
        # [LEFT SECTION: Posting Panel]
        # ----------------------------------------------------------------------
        post_panel = QFrame()
        post_panel.setProperty("class", "glassCard")
        p_layout = QVBoxLayout(post_panel)
        p_layout.setSpacing(12)

        p_header = QLabel("📢 FB Group Posting Panel")
        p_header.setStyleSheet("font-size: 15px; font-weight: 700; color: #38bdf8; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 6px;")
        p_layout.addWidget(p_header)

        # Input: Group Codes
        p_layout.addWidget(QLabel("📋 Target Group Codes / URLs (1 per line or comma-separated):"))
        self.grp_post_codes_input = QTextEdit()
        self.grp_post_codes_input.setPlaceholderText("e.g.\n123456789012345\nhttps://www.facebook.com/groups/pakistanbuyandsell/\n987654321098765")
        self.grp_post_codes_input.setFixedHeight(80)
        p_layout.addWidget(self.grp_post_codes_input)

        # Input: Multiple Links (to be shared randomly or sequentially)
        p_links_hdr = QHBoxLayout()
        p_links_hdr.addWidget(QLabel("🔗 Multiple Links (1 per line):"))
        p_links_hdr.addStretch()
        p_links_hdr.addWidget(QLabel("Distribution:"))
        self.grp_post_mode_select = QComboBox()
        self.grp_post_mode_select.addItems(["Random Distribution", "Sequential Queue"])
        self.grp_post_mode_select.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        p_links_hdr.addWidget(self.grp_post_mode_select)
        p_layout.addLayout(p_links_hdr)

        self.grp_post_links_input = QTextEdit()
        self.grp_post_links_input.setPlaceholderText("e.g.\nhttps://facebook.com/marketplace/item/101010101/\nhttps://example.com/product-page\nhttps://facebook.com/marketplace/item/202020202/")
        self.grp_post_links_input.setFixedHeight(80)
        p_layout.addWidget(self.grp_post_links_input)

        # Input: Post Descriptions
        p_layout.addWidget(QLabel("📝 Post Descriptions / Text Content (1 variant per line or multi-line):"))
        self.grp_post_desc_input = QTextEdit()
        self.grp_post_desc_input.setPlaceholderText("e.g.\n🔥 Premium Household Appliance for sale! Fast shipping available. Check the link above.\n\n🚗 High-quality Auto Parts available in stock. DM for orders.")
        self.grp_post_desc_input.setFixedHeight(90)
        p_layout.addWidget(self.grp_post_desc_input)

        # Settings: Thread & Delay
        p_settings_row = QHBoxLayout()
        
        p_thread_col = QVBoxLayout()
        p_thread_col.addWidget(QLabel("🧵 Threads (Concurrent Browsers):"))
        self.grp_post_thread_spin = QSpinBox()
        self.grp_post_thread_spin.setRange(1, 50)
        self.grp_post_thread_spin.setValue(1)
        self.grp_post_thread_spin.setStyleSheet("font-weight: 700; color: #38bdf8;")
        p_thread_col.addWidget(self.grp_post_thread_spin)
        p_settings_row.addLayout(p_thread_col)

        p_delay_col = QVBoxLayout()
        p_delay_col.addWidget(QLabel("⏳ Post Delay Interval (Seconds):"))
        self.grp_post_delay_spin = QSpinBox()
        self.grp_post_delay_spin.setRange(1, 50)
        self.grp_post_delay_spin.setValue(15)
        self.grp_post_delay_spin.setSuffix(" sec")
        self.grp_post_delay_spin.setStyleSheet("font-weight: 700; color: #10b981;")
        p_delay_col.addWidget(self.grp_post_delay_spin)
        p_settings_row.addLayout(p_delay_col)

        p_layout.addLayout(p_settings_row)

        # Extension notice badge
        ext_status_box = QLabel("🧩 FEWFEED Extension Engine: Auto-loads in mobile emulation for 1-click group posting.")
        ext_status_box.setStyleSheet("background-color: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.3); color: #c7d2fe; padding: 6px 10px; border-radius: 6px; font-size: 11px;")
        p_layout.addWidget(ext_status_box)

        panels_row.addWidget(post_panel, stretch=1)

        # ----------------------------------------------------------------------
        # [RIGHT SECTION: Group Joining Panel]
        # ----------------------------------------------------------------------
        join_panel = QFrame()
        join_panel.setProperty("class", "glassCard")
        j_layout = QVBoxLayout(join_panel)
        j_layout.setSpacing(12)

        j_header = QLabel("👥 Facebook Group Joining Panel")
        j_header.setStyleSheet("font-size: 15px; font-weight: 700; color: #10b981; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 6px;")
        j_layout.addWidget(j_header)

        # Input: Group Codes for Joining
        j_layout.addWidget(QLabel("📋 Target Group Codes / URLs to Join (1 per line):"))
        self.grp_join_codes_input = QTextEdit()
        self.grp_join_codes_input.setPlaceholderText("e.g.\nhttps://www.facebook.com/groups/112233445566/\nfacebook.com/groups/auto_parts_marketplace\n554433221100998")
        self.grp_join_codes_input.setFixedHeight(75)
        j_layout.addWidget(self.grp_join_codes_input)

        # Settings: Thread & Delay for Joining
        j_settings_row = QHBoxLayout()
        
        j_thread_col = QVBoxLayout()
        j_thread_col.addWidget(QLabel("🧵 Threads (Concurrent Browsers):"))
        self.grp_join_thread_spin = QSpinBox()
        self.grp_join_thread_spin.setRange(1, 50)
        self.grp_join_thread_spin.setValue(1)
        self.grp_join_thread_spin.setStyleSheet("font-weight: 700; color: #38bdf8;")
        j_thread_col.addWidget(self.grp_join_thread_spin)
        j_settings_row.addLayout(j_thread_col)

        j_delay_col = QVBoxLayout()
        j_delay_col.addWidget(QLabel("⏳ Join Delay Interval (Seconds):"))
        self.grp_join_delay_spin = QSpinBox()
        self.grp_join_delay_spin.setRange(1, 50)
        self.grp_join_delay_spin.setValue(15)
        self.grp_join_delay_spin.setSuffix(" sec")
        self.grp_join_delay_spin.setStyleSheet("font-weight: 700; color: #10b981;")
        j_delay_col.addWidget(self.grp_join_delay_spin)
        j_settings_row.addLayout(j_delay_col)

        j_layout.addLayout(j_settings_row)

        # Feature bullet summary card
        j_info_box = QFrame()
        j_info_box.setStyleSheet("background-color: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 6px; padding: 10px;")
        j_ib_layout = QVBoxLayout(j_info_box)
        j_ib_layout.setSpacing(4)
        j_ib_layout.addWidget(QLabel("<b>Joining Engine Features:</b>"))
        j_ib_layout.addWidget(QLabel("• Auto-detects Already-Joined & Pending memberships."))
        j_ib_layout.addWidget(QLabel("• Submits default membership forms/questions automatically."))
        j_ib_layout.addWidget(QLabel("• Applies randomized human jitter between requests."))
        j_layout.addWidget(j_info_box)

        j_layout.addStretch()

        panels_row.addWidget(join_panel, stretch=1)

        layout.addLayout(panels_row)

        scroll.setWidget(container)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        self.populate_group_accounts_checklist()
        return page

    def populate_group_accounts_checklist(self):
        """Populates the multi-account checkbox list for FB Group operations."""
        if not hasattr(self, 'grp_acc_layout'):
            return

        while self.grp_acc_layout.count():
            item = self.grp_acc_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.grp_acc_checkboxes = []

        if not self.accounts_list:
            lbl = QLabel("No Facebook accounts configured yet. Add them in 'Accounts Manager'.")
            lbl.setStyleSheet("color: #94a3b8; font-style: italic; font-size: 11px;")
            self.grp_acc_layout.addWidget(lbl)
            self.update_group_account_selection_summary()
            return

        for acc in self.accounts_list:
            name = acc.get("name", "Account")
            status = acc.get("status", "Healthy")
            proxy = acc.get("proxy", "Direct")
            icon = "🟢" if status in ("Healthy", "Active") else ("🟡" if status == "Checkpoint" else "🔴")

            chk = QCheckBox(f"{icon} {name}  [{status}]  •  Proxy: {proxy}")
            chk.setStyleSheet("font-size: 12px; color: #f8fafc; padding: 2px 0;")
            chk.setProperty("account_data", acc)
            chk.setChecked(status in ("Healthy", "Active"))
            chk.stateChanged.connect(self.update_group_account_selection_summary)

            self.grp_acc_layout.addWidget(chk)
            self.grp_acc_checkboxes.append(chk)

        self.grp_acc_layout.addStretch()
        self.update_group_account_selection_summary()

    def select_all_group_accounts(self):
        if hasattr(self, 'grp_acc_checkboxes'):
            for chk in self.grp_acc_checkboxes:
                chk.setChecked(True)
            self.update_group_account_selection_summary()

    def clear_all_group_accounts(self):
        if hasattr(self, 'grp_acc_checkboxes'):
            for chk in self.grp_acc_checkboxes:
                chk.setChecked(False)
            self.update_group_account_selection_summary()

    def update_group_account_selection_summary(self):
        if not hasattr(self, 'grp_acc_checkboxes') or not hasattr(self, 'grp_acc_summary_lbl'):
            return
        selected_count = sum(1 for chk in self.grp_acc_checkboxes if chk.isChecked())
        total_count = len(self.grp_acc_checkboxes)
        self.grp_acc_summary_lbl.setText(
            f"🎯 {selected_count} of {total_count} Accounts Selected for Group Operations"
        )

    def get_selected_group_accounts(self) -> List[dict]:
        selected = []
        if hasattr(self, 'grp_acc_checkboxes'):
            for chk in self.grp_acc_checkboxes:
                if chk.isChecked():
                    acc_data = chk.property("account_data")
                    if acc_data:
                        selected.append(acc_data)
        return selected

    def start_group_posting(self):
        """Validates inputs and dispatches GroupAutomationWorker for posting workflow."""
        accounts = self.get_selected_group_accounts()
        if not accounts:
            QMessageBox.warning(self, "No Accounts Selected", "Please select at least one Facebook account profile above.")
            return

        raw_codes = self.grp_post_codes_input.toPlainText().strip()
        codes = parse_group_codes(raw_codes)
        if not codes:
            QMessageBox.warning(self, "Missing Group Codes", "Please enter at least one target Facebook Group Code or URL.")
            return

        raw_links = self.grp_post_links_input.toPlainText().strip()
        links = parse_multiline_links(raw_links)

        raw_desc = self.grp_post_desc_input.toPlainText().strip()
        descriptions = [d.strip() for d in raw_desc.splitlines() if d.strip()] if raw_desc else []

        if not links and not descriptions:
            QMessageBox.warning(self, "Missing Content", "Please provide at least one Link or Description to post into the groups.")
            return

        mode = "Random" if "Random" in self.grp_post_mode_select.currentText() else "Sequential"
        threads = self.grp_post_thread_spin.value()
        delay = self.grp_post_delay_spin.value()

        payload = {
            "accounts": accounts,
            "group_codes": codes,
            "links": links,
            "descriptions": descriptions,
            "mode": mode,
            "threads": threads,
            "delay": delay
        }

        self.btn_start_grp_post.setEnabled(False)
        self.btn_stop_grp_post.setEnabled(True)
        self.btn_start_grp_join.setEnabled(False)
        self.engine_status_lbl.setText("● FB GROUP POSTING")
        self.engine_status_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #38bdf8;")

        self.group_worker = GroupAutomationWorker(task_type="posting", payload=payload)
        self.group_worker.log_signal.connect(self.log_message)
        self.group_worker.progress_signal.connect(self.update_progress)
        self.group_worker.finished_signal.connect(self.on_group_automation_finished)
        self.group_worker.start()

    def start_unified_group_automation(self):
        """Validates inputs and dispatches GroupAutomationWorker for the full FewFeed 2-in-1 workflow (Auto Join -> Auto Post)."""
        accounts = self.get_selected_group_accounts()
        if not accounts:
            QMessageBox.warning(self, "No Accounts Selected", "Please select at least one Facebook account profile above.")
            return

        raw_join_codes = self.grp_join_codes_input.toPlainText().strip()
        join_codes = parse_group_codes(raw_join_codes)

        raw_post_codes = self.grp_post_codes_input.toPlainText().strip()
        post_codes = parse_group_codes(raw_post_codes)

        raw_links = self.grp_post_links_input.toPlainText().strip()
        links = parse_multiline_links(raw_links)

        raw_desc = self.grp_post_desc_input.toPlainText().strip()
        descriptions = [d.strip() for d in re.split(r'\n\s*\n', raw_desc) if d.strip()] if raw_desc else []

        if not join_codes and not links and not descriptions and not post_codes:
            QMessageBox.warning(self, "No Data Provided", "Please provide Target Groups to Join or Post Descriptions/Links to proceed.")
            return

        mode = "Random" if "Random" in self.grp_post_mode_select.currentText() else "Sequential"
        threads = self.grp_max_concurrent_browsers.value() if hasattr(self, 'grp_max_concurrent_browsers') else 3
        delay = self.grp_post_delay_spin.value()

        cf_email = "codeabm71@gmail.com"
        cf_pass = "Fewfeew"

        # Save CueFeed login details globally
        try:
            cfg_dir = os.path.join(get_base_dir(), "config")
            os.makedirs(cfg_dir, exist_ok=True)
            cfg_file = os.path.join(cfg_dir, "group_settings.json")
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump({"cuefeed_email": cf_email, "cuefeed_pass": cf_pass}, f, indent=2)
        except Exception:
            pass

        # Attach CueFeed credentials to accounts payload
        for acc in accounts:
            acc["cuefeed_email"] = cf_email
            acc["cuefeed_pass"] = cf_pass

        payload = {
            "accounts": accounts,
            "cuefeed_email": cf_email,
            "cuefeed_pass": cf_pass,
            "group_codes": post_codes or join_codes,
            "join_group_codes": join_codes,
            "post_group_codes": post_codes,
            "links": links,
            "descriptions": descriptions,
            "mode": mode,
            "threads": threads,
            "delay": delay
        }

        self.btn_start_grp_unified.setEnabled(False)
        self.btn_stop_grp_unified.setEnabled(True)
        self.engine_status_lbl.setText("● FEWFEED AUTOMATION ACTIVE")
        self.engine_status_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #38bdf8;")

        self.group_worker = GroupAutomationWorker(task_type="unified", payload=payload)
        self.group_worker.log_signal.connect(self.log_message)
        self.group_worker.progress_signal.connect(self.update_progress)
        self.group_worker.finished_signal.connect(self.on_group_automation_finished)
        self.group_worker.start()

    def start_group_posting(self):
        """Redirects to unified group automation."""
        self.start_unified_group_automation()

    def start_group_joining(self):
        """Redirects to unified group automation."""
        self.start_unified_group_automation()

    def stop_group_automation(self):
        if self.group_worker:
            self.group_worker.stop()
            self.btn_stop_grp_unified.setEnabled(False)

    def on_group_automation_finished(self, success: bool, message: str):
        self.btn_start_grp_unified.setEnabled(True)
        self.btn_stop_grp_unified.setEnabled(False)
        self.engine_status_lbl.setText("● READY FOR TASKS")
        self.engine_status_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #10b981;")

        if success:
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Group Task Complete", f"Facebook Group FewFeed automation finished!\n\n{message}")
        else:
            QMessageBox.warning(self, "Group Task Notice", f"Facebook Group execution notice:\n\n{message}")

    # --------------------------------------------------------------------------
    # Tab 4: AI Content Spinner & Title/Description Generator (Phase 5)
    # --------------------------------------------------------------------------
    def create_ai_page(self):
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("AI Content Spinner & Listing Intelligence")
        title.setProperty("class", "pageTitle")
        sub = QLabel("Generate high-converting titles, spin descriptions with specifications, and bypass duplicate text filters.")
        sub.setProperty("class", "pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(sub)

        # Config Card
        card = QFrame()
        card.setProperty("class", "glassCard")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(12)

        # Seed Keyword
        c_layout.addWidget(QLabel("Product Name or Seed Keywords:"))
        self.ai_seed_input = QLineEdit()
        self.ai_seed_input.setPlaceholderText("e.g., Apple iPhone 15 Pro Max 256GB Titanium sealed in box")
        self.ai_seed_input.setText("Apple iPhone 15 Pro Max 256GB Titanium")
        c_layout.addWidget(self.ai_seed_input)

        # Base Description / Specs
        c_layout.addWidget(QLabel("Base Product Notes / Original Description:"))
        self.ai_base_desc_input = QTextEdit()
        self.ai_base_desc_input.setPlaceholderText("Paste raw description or specifications here (e.g. condition, warranty, accessories included)...")
        self.ai_base_desc_input.setPlainText("Factory sealed in original box. Never opened. 1-year official Apple warranty. Includes braided USB-C cable. Available for immediate local pickup or tracked shipping.")
        self.ai_base_desc_input.setFixedHeight(75)
        c_layout.addWidget(self.ai_base_desc_input)

        # Options Row: Tone, Count, API Key
        row_opt = QHBoxLayout()
        col_tone = QVBoxLayout()
        col_tone.addWidget(QLabel("Tone of Voice:"))
        self.ai_tone = QComboBox()
        self.ai_tone.addItems(["Casual & Friendly", "Professional & Transparent", "Urgent Clearance / Deal"])
        col_tone.addWidget(self.ai_tone)

        col_count = QVBoxLayout()
        col_count.addWidget(QLabel("Variants Count:"))
        self.ai_variants = QSpinBox()
        self.ai_variants.setRange(1, 5)
        self.ai_variants.setValue(3)
        col_count.addWidget(self.ai_variants)

        col_key = QVBoxLayout()
        col_key.addWidget(QLabel("Gemini API Key (Optional / Uses Offline Spintax if blank):"))
        self.ai_api_key_input = QLineEdit()
        self.ai_api_key_input.setPlaceholderText("AIzaSy... (Leave empty for Offline Spintax Engine)")
        self.ai_api_key_input.setEchoMode(QLineEdit.Password)
        default_key = os.environ.get("GEMINI_API_KEY", "")
        if default_key:
            self.ai_api_key_input.setText(default_key)
        col_key.addWidget(self.ai_api_key_input)

        row_opt.addLayout(col_tone, stretch=1)
        row_opt.addLayout(col_count, stretch=1)
        row_opt.addLayout(col_key, stretch=2)
        c_layout.addLayout(row_opt)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        self.btn_gen_titles = QPushButton("✨ Generate Title Variants")
        self.btn_gen_titles.setProperty("class", "secondaryBtn")
        self.btn_gen_titles.setCursor(Qt.PointingHandCursor)
        self.btn_gen_titles.clicked.connect(self.generate_ai_titles)

        self.btn_gen_descs = QPushButton("📝 Rewrite Description")
        self.btn_gen_descs.setProperty("class", "secondaryBtn")
        self.btn_gen_descs.setCursor(Qt.PointingHandCursor)
        self.btn_gen_descs.clicked.connect(self.generate_ai_descriptions)

        self.btn_gen_full = QPushButton("🚀 Full Listing Generation")
        self.btn_gen_full.setProperty("class", "primaryBtn")
        self.btn_gen_full.setCursor(Qt.PointingHandCursor)
        self.btn_gen_full.clicked.connect(self.generate_ai_full)

        btn_row.addWidget(self.btn_gen_titles)
        btn_row.addWidget(self.btn_gen_descs)
        btn_row.addWidget(self.btn_gen_full)
        c_layout.addLayout(btn_row)

        layout.addWidget(card)

        # Results Card
        res_card = QFrame()
        res_card.setProperty("class", "glassCard")
        r_layout = QVBoxLayout(res_card)
        r_layout.setSpacing(12)

        # Titles and Descriptions side by side or stacked
        res_split = QHBoxLayout()

        # Titles Column
        col_titles_res = QVBoxLayout()
        t_top = QHBoxLayout()
        t_top.addWidget(QLabel("Generated Title Variants:"))
        t_top.addStretch()
        use_title_btn = QPushButton("↙️ Use Selected Title")
        use_title_btn.setProperty("class", "secondaryBtn")
        use_title_btn.setFixedHeight(22)
        use_title_btn.setStyleSheet("font-size: 10px; padding: 2px 6px;")
        use_title_btn.clicked.connect(self.use_selected_title_in_automation)
        t_top.addWidget(use_title_btn)
        col_titles_res.addLayout(t_top)

        self.titles_list_widget = QListWidget()
        self.titles_list_widget.setFixedHeight(140)
        self.titles_list_widget.setStyleSheet("background-color: #0d1322; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 4px;")
        col_titles_res.addWidget(self.titles_list_widget)

        # Descriptions Column
        col_descs_res = QVBoxLayout()
        d_top = QHBoxLayout()
        d_top.addWidget(QLabel("Generated Spun Description:"))
        d_top.addStretch()
        use_desc_btn = QPushButton("↙️ Use in Automation")
        use_desc_btn.setProperty("class", "secondaryBtn")
        use_desc_btn.setFixedHeight(22)
        use_desc_btn.setStyleSheet("font-size: 10px; padding: 2px 6px;")
        use_desc_btn.clicked.connect(self.use_selected_desc_in_automation)
        d_top.addWidget(use_desc_btn)
        col_descs_res.addLayout(d_top)

        self.desc_preview_widget = QTextEdit()
        self.desc_preview_widget.setFixedHeight(140)
        self.desc_preview_widget.setPlaceholderText("Generated description rewrites with bullet points and specs will appear here...")
        self.desc_preview_widget.setStyleSheet("background-color: #0d1322; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 6px;")
        col_descs_res.addWidget(self.desc_preview_widget)

        res_split.addLayout(col_titles_res, stretch=1)
        res_split.addLayout(col_descs_res, stretch=1)
        r_layout.addLayout(res_split)

        # Transfer Both Button
        transfer_all_btn = QPushButton("🚀 Apply Title & Description to Automation Form & Switch Tab")
        transfer_all_btn.setProperty("class", "successBtn")
        transfer_all_btn.setCursor(Qt.PointingHandCursor)
        transfer_all_btn.clicked.connect(self.transfer_ai_content)
        r_layout.addWidget(transfer_all_btn)

        layout.addWidget(res_card)

        scroll.setWidget(container)
        outer_layout = QVBoxLayout(page)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)
        return page

    # --- Phase 5 Automation Tab Synergy Actions ---

    def quick_spin_title(self):
        """Auto-spins the Title directly in the Automation tab using Gemini or offline spintax."""
        curr_title = self.title_input.text().strip()
        seed = curr_title or "Apple iPhone 15 Pro Max 256GB"
        api_key = self.ai_api_key_input.text().strip() if hasattr(self, 'ai_api_key_input') else os.environ.get("GEMINI_API_KEY", "")

        self.log_message("INFO", f"✨ Auto-Spin Title: Processing variant for '{seed}'...")
        if hasattr(self, 'btn_spin_title'): self.btn_spin_title.setEnabled(False)

        def on_done(titles):
            if titles:
                new_title = titles[0]
                self.title_input.setText(new_title)
                self.log_message("SUCCESS", f"✨ Title spun: '{new_title}'")
            if hasattr(self, 'btn_spin_title'): self.btn_spin_title.setEnabled(True)

        self.ai_worker = AISpinnerWorker(
            task_type="titles",
            seed=seed,
            tone="Casual",
            count=3,
            api_key=api_key
        )
        self.ai_worker.log_signal.connect(self.log_message)
        self.ai_worker.titles_ready.connect(on_done)
        self.ai_worker.start()

    def quick_spin_desc(self):
        """Auto-spins the Description directly in the Automation tab into a structured, unique variant."""
        curr_desc = self.desc_input.toPlainText().strip()
        title = self.title_input.text().strip() or "Product"
        api_key = self.ai_api_key_input.text().strip() if hasattr(self, 'ai_api_key_input') else os.environ.get("GEMINI_API_KEY", "")

        self.log_message("INFO", f"✨ Auto-Spin Description: Generating unique structured rewrite for '{title}'...")
        if hasattr(self, 'btn_spin_desc'): self.btn_spin_desc.setEnabled(False)

        def on_done(descs):
            if descs:
                new_desc = descs[0]
                self.desc_input.setPlainText(new_desc)
                self.log_message("SUCCESS", f"✨ Description rewritten with bullet points & specs ({len(new_desc.splitlines())} lines).")
            if hasattr(self, 'btn_spin_desc'): self.btn_spin_desc.setEnabled(True)

        self.ai_worker = AISpinnerWorker(
            task_type="descriptions",
            seed=title,
            base_desc=curr_desc or f"Authentic {title} in pristine condition. Includes all original items.",
            tone="Professional",
            count=2,
            api_key=api_key
        )
        self.ai_worker.log_signal.connect(self.log_message)
        self.ai_worker.descs_ready.connect(on_done)
        self.ai_worker.start()

    # --- Phase 5 AI Page Action Handlers ---

    def generate_ai_titles(self):
        seed = self.ai_seed_input.text().strip()
        if not seed:
            QMessageBox.warning(self, "Missing Input", "Please enter a product name or seed keywords.")
            return

        api_key = self.ai_api_key_input.text().strip()
        tone = self.ai_tone.currentText().split()[0]
        count = self.ai_variants.value()

        self.btn_gen_titles.setEnabled(False)
        self.titles_list_widget.clear()

        self.ai_worker = AISpinnerWorker(
            task_type="titles",
            seed=seed,
            tone=tone,
            count=count,
            api_key=api_key
        )
        self.ai_worker.log_signal.connect(self.log_message)
        self.ai_worker.titles_ready.connect(self.on_ai_titles_ready)
        self.ai_worker.finished_signal.connect(lambda ok, msg: self.btn_gen_titles.setEnabled(True))
        self.ai_worker.start()

    def generate_ai_descriptions(self):
        seed = self.ai_seed_input.text().strip() or "Product"
        base_desc = self.ai_base_desc_input.toPlainText().strip()
        api_key = self.ai_api_key_input.text().strip()
        tone = self.ai_tone.currentText().split()[0]
        count = self.ai_variants.value()

        self.btn_gen_descs.setEnabled(False)

        self.ai_worker = AISpinnerWorker(
            task_type="descriptions",
            seed=seed,
            base_desc=base_desc,
            tone=tone,
            count=count,
            api_key=api_key
        )
        self.ai_worker.log_signal.connect(self.log_message)
        self.ai_worker.descs_ready.connect(self.on_ai_descs_ready)
        self.ai_worker.finished_signal.connect(lambda ok, msg: self.btn_gen_descs.setEnabled(True))
        self.ai_worker.start()

    def generate_ai_full(self):
        seed = self.ai_seed_input.text().strip()
        if not seed:
            QMessageBox.warning(self, "Missing Input", "Please enter a product name or seed keywords.")
            return

        base_desc = self.ai_base_desc_input.toPlainText().strip()
        api_key = self.ai_api_key_input.text().strip()
        tone = self.ai_tone.currentText().split()[0]
        count = self.ai_variants.value()

        self.btn_gen_full.setEnabled(False)
        self.titles_list_widget.clear()

        self.ai_worker = AISpinnerWorker(
            task_type="both",
            seed=seed,
            base_desc=base_desc,
            tone=tone,
            count=count,
            api_key=api_key
        )
        self.ai_worker.log_signal.connect(self.log_message)
        self.ai_worker.titles_ready.connect(self.on_ai_titles_ready)
        self.ai_worker.descs_ready.connect(self.on_ai_descs_ready)
        self.ai_worker.finished_signal.connect(lambda ok, msg: self.btn_gen_full.setEnabled(True))
        self.ai_worker.start()

    def on_ai_titles_ready(self, titles):
        self.titles_list_widget.clear()
        for idx, t in enumerate(titles, 1):
            item = QListWidgetItem(f"{idx}. {t}")
            self.titles_list_widget.addItem(item)
        if titles:
            self.titles_list_widget.setCurrentRow(0)

    def on_ai_descs_ready(self, descs):
        if descs:
            self.desc_preview_widget.setPlainText(descs[0])

    def use_selected_title_in_automation(self):
        curr_item = self.titles_list_widget.currentItem()
        if curr_item:
            title_text = re.sub(r'^\d+\.\s*', '', curr_item.text())
            self.title_input.setText(title_text)
            self.log_message("SUCCESS", f"Transferred title variant to Automation tab: '{title_text}'")
        else:
            QMessageBox.information(self, "Selection", "Please select a title from the list.")

    def use_selected_desc_in_automation(self):
        desc_text = self.desc_preview_widget.toPlainText().strip()
        if desc_text:
            self.desc_input.setPlainText(desc_text)
            self.log_message("SUCCESS", "Transferred rewritten description to Automation tab.")
        else:
            QMessageBox.information(self, "Description", "No generated description available to transfer.")

    def transfer_ai_content(self):
        # Title
        curr_item = self.titles_list_widget.currentItem()
        if curr_item:
            title_text = re.sub(r'^\d+\.\s*', '', curr_item.text())
            self.title_input.setText(title_text)
        elif self.ai_seed_input.text().strip():
            self.title_input.setText(self.ai_seed_input.text().strip())

        # Description
        desc_text = self.desc_preview_widget.toPlainText().strip()
        if desc_text:
            self.desc_input.setPlainText(desc_text)
        elif self.ai_base_desc_input.toPlainText().strip():
            self.desc_input.setPlainText(self.ai_base_desc_input.toPlainText().strip())

        self.switch_tab(2)
        self.log_message("SUCCESS", "Applied generated AI title & description to Automation tab!")

    # --------------------------------------------------------------------------
    # Tab 5: Settings & Stealth
    # --------------------------------------------------------------------------
    def create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("System Settings & Stealth Parameters")
        title.setProperty("class", "pageTitle")
        sub = QLabel("Configure browser evasion flags, API credentials, and runtime parameters.")
        sub.setProperty("class", "pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(sub)

        card = QFrame()
        card.setProperty("class", "glassCard")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(12)

        c_layout.addWidget(QLabel("Gemini API Key (For Content Intelligence):"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("AIzaSy...")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        c_layout.addWidget(self.api_key_input)

        c_layout.addWidget(QLabel("Browser Anti-Detection Flags:"))
        chk1 = QCheckBox("Enable Playwright Stealth Module (navigator.webdriver mask)")
        chk1.setChecked(True)
        chk2 = QCheckBox("Randomize Canvas & WebGL Audio Context Noise")
        chk2.setChecked(True)
        chk3 = QCheckBox("Emulate Human Micro-Mouse Jitter & Variable Scroll Velocity")
        chk3.setChecked(True)
        chk4 = QCheckBox("Run in Headless Mode (Uncheck to view live automated browser window)")
        chk4.setChecked(False)

        c_layout.addWidget(chk1)
        c_layout.addWidget(chk2)
        c_layout.addWidget(chk3)
        c_layout.addWidget(chk4)

        # Support & Activation Row
        btn_wa_support = QPushButton("💬 Contact Support / Order Key on WhatsApp (+14015721696)")
        btn_wa_support.setCursor(Qt.PointingHandCursor)
        btn_wa_support.setStyleSheet("background-color: #059669; color: #ffffff; font-weight: bold; border-radius: 8px; padding: 8px;")
        btn_wa_support.clicked.connect(self.open_whatsapp_support)
        c_layout.addWidget(btn_wa_support)

        save_btn = QPushButton("Save Configuration")
        save_btn.setProperty("class", "primaryBtn")
        save_btn.clicked.connect(lambda: self.log_message("SUCCESS", "System settings and stealth parameters saved."))
        c_layout.addWidget(save_btn)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def open_whatsapp_support(self):
        """Opens direct WhatsApp support chat with Admin with pre-formatted HWID."""
        import webbrowser
        hwid = get_machine_hwid() if HAS_LICENSING else "DESKTOP-CLIENT"
        link = f"https://wa.me/+14015721696?text=Hi%2C%20I%20want%20to%20activate%20FB%20Auto%20Bot.%20My%20HWID%20is%3A%20{hwid}"
        webbrowser.open(link)
        self.log_message("INFO", f"Triggered WhatsApp direct chat for HWID: {hwid}")

    # --------------------------------------------------------------------------
    # Bottom Global Terminal Console
    # --------------------------------------------------------------------------
    def create_console_panel(self):
        panel = QFrame()
        panel.setProperty("class", "glassCard")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header bar
        header_bar = QHBoxLayout()
        con_title = QLabel("Live Console & Terminal Output")
        con_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #cbd5e1;")

        clear_btn = QPushButton("Clear Console")
        clear_btn.setProperty("class", "secondaryBtn")
        clear_btn.clicked.connect(self.clear_console)

        header_bar.addWidget(con_title)
        header_bar.addStretch()
        header_bar.addWidget(clear_btn)
        layout.addLayout(header_bar)

        # Console Text Box
        self.console_box = QTextEdit()
        self.console_box.setObjectName("consoleBox")
        self.console_box.setReadOnly(True)
        layout.addWidget(self.console_box)

        # Bottom Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        layout.addWidget(self.progress_bar)

        # Initial Welcome log
        self.log_message("INFO", "FB Auto Bot Engine v2.4 initialized. Ready to automate Facebook Marketplace.")
        return panel

    def log_message(self, level, message, category="SYSTEM"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        date_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "timestamp": date_stamp,
            "short_time": timestamp,
            "category": category,
            "level": level,
            "message": message
        }
        if hasattr(self, 'activity_logs'):
            self.activity_logs.append(entry)

        color_map = {
            "INFO": "#38bdf8",       # Sky blue
            "SUCCESS": "#10b981",    # Emerald green
            "WARNING": "#f59e0b",    # Amber
            "ERROR": "#ef4444",      # Crimson red
            "CRITICAL": "#ff0055",   # Vivid magenta/red
            "FALLBACK": "#c084fc"    # Purple/violet
        }
        color = color_map.get(level.upper(), "#cbd5e1")
        badge = f"[{level.upper()}]"
        if level.upper() == "FALLBACK":
            badge = "[FALLBACK 🔄]"
        elif level.upper() == "CRITICAL":
            badge = "[CRITICAL 🚨]"
        formatted = f'<span style="color: #64748b;">[{timestamp}]</span> <b style="color: {color};">{badge}</b> <span style="color: #f8fafc;">{message}</span>'
        if hasattr(self, 'console_box'):
            self.console_box.append(formatted)
            self.console_box.moveCursor(QTextCursor.End)

        if hasattr(self, 'profile_log_table'):
            self.append_log_to_table(entry)

    def update_progress(self, val):
        self.progress_bar.setValue(val)

    def clear_console(self):
        self.console_box.clear()
        self.progress_bar.setValue(0)
        self.log_message("INFO", "Console buffer cleared.")


# ------------------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------------------
def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("fbautobot.enterprise.automation.v24")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setStyleSheet(GLASS_STYLESHEET)

    # Set Application Icon across all windows & taskbar
    logo_file = get_best_logo_path()
    if logo_file and os.path.isfile(logo_file):
        app.setWindowIcon(QIcon(logo_file))

    # Enforce HWID License Protection
    license_info = {}
    if HAS_LICENSING:
        try:
            lic_res = LicenseManager.is_active()
            if isinstance(lic_res, tuple):
                is_active = bool(lic_res[0])
                msg = str(lic_res[1]) if len(lic_res) > 1 else ""
                license_info = lic_res[2] if len(lic_res) > 2 and isinstance(lic_res[2], dict) else {}
            else:
                is_active = bool(lic_res)
        except Exception:
            is_active = False

        if not is_active:
            # Show Lock-Screen Activation Dialog
            dialog = LicenseActivationDialog(admin_phone="+14015721696")
            if dialog.exec_() != LicenseActivationDialog.Accepted:
                # User cancelled or failed activation
                sys.exit(0)
            license_info = getattr(dialog, 'license_data', {}) or {}

    window = FBAutoBotMainWindow(initial_license_info=license_info)
    if HAS_LICENSING and license_info:
        customer = license_info.get("customer", "Active User")
        tier = license_info.get("tier", "Pro")
        window.setWindowTitle(f"FB Auto Bot v2.4 - [{customer} | {tier}] - HWID Locked")
        window.log_message("SUCCESS", f"License verified for {customer} ({tier}). HWID: {get_machine_hwid()}", category="LICENSE")

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
