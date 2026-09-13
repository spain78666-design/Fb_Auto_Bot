export const browserBotCodeSnippet = `#!/usr/bin/env python3
"""
FB Auto Bot - Facebook Marketplace Automation Suite
automation/browser_bot.py - Playwright Async Controller with Stealth & Anti-Detection
"""

import asyncio
import random
import os
import json
import logging
from typing import List, Dict, Any, Optional, Callable

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

# Attempt to import playwright-stealth if installed
try:
    from playwright_stealth import stealth_async
    PLAYWRIGHT_STEALTH_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_STEALTH_AVAILABLE = False

logger = logging.getLogger("FBAutoBot.BrowserBot")

EXTRA_STEALTH_JS = """
// 1. Mask navigator.webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. Mock Chrome runtime
window.chrome = {
    app: { isInstalled: false, InstallState: { DISABLED: 'disabled' } },
    runtime: { OnInstalledReason: { INSTALL: 'install' } },
    loadTimes: function() {},
    csi: function() {}
};

// 3. Mock WebGL Vendor / Renderer (Intel Iris Xe Graphics)
const getParameterOrig = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel(R) Iris(R) Xe Graphics (0x9a49)';
    return getParameterOrig.apply(this, arguments);
};

// 4. Permissions API mock
const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        origQuery(parameters)
);
"""

class FacebookMarketplaceBot:
    """Production-grade Playwright async automation engine for Facebook Marketplace."""

    def __init__(
        self,
        account_data: Dict[str, Any],
        speed_mode: str = "Normal",
        headless: bool = False,
        log_callback: Optional[Callable[[str, str], None]] = None,
        progress_callback: Optional[Callable[[int], None]] = None
    ):
        self.account_data = account_data
        self.speed_mode = speed_mode
        self.headless = headless
        self.log_cb = log_callback or (lambda lvl, msg: None)
        self.prog_cb = progress_callback or (lambda p: None)
        self._is_cancelled = False
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def cancel(self):
        self._is_cancelled = True

    async def run_listing_workflow(self, payload: Dict[str, Any]) -> bool:
        """Executes the complete end-to-end Facebook Marketplace listing automation."""
        self.prog_cb(5)
        await self._init_browser_and_context()

        # Step 1: Inject cookies
        self.prog_cb(20)
        await self._inject_cookies()

        # Step 2: Validate session
        self.prog_cb(35)
        await self._verify_session_health()

        # Step 3: Navigate to Marketplace Create
        self.prog_cb(50)
        await self._navigate_to_marketplace_create()

        # Step 4: Upload images
        self.prog_cb(65)
        await self._upload_images(payload.get("images", []))

        # Step 5: Fill listing form fields with human typing
        self.prog_cb(80)
        await self._fill_listing_fields(payload)

        # Step 6: Advance Next & Publish
        self.prog_cb(95)
        await self._advance_and_publish(payload.get("title", ""))

        self.prog_cb(100)
        return True
`;

export const appPyCodeSnippet = `#!/usr/bin/env python3
"""
FB Auto Bot - Enterprise Facebook Marketplace Automation Suite
desktop_app/app.py - Modern Dark Glassmorphic Desktop GUI (PyQt5)
"""

import sys
import os
import json
import asyncio
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QLineEdit, QTextEdit,
    QComboBox, QSpinBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QProgressBar, QFrame, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QTextCursor

try:
    from automation.browser_bot import FacebookMarketplaceBot, BotAutomationError
except ImportError:
    FacebookMarketplaceBot = None

class AutomationWorker(QThread):
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, payload, speed_mode="Normal", headless=False):
        super().__init__()
        self.payload = payload
        self.speed_mode = speed_mode
        self.headless = headless
        self.bot = None

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if FacebookMarketplaceBot:
                self.bot = FacebookMarketplaceBot(
                    account_data=self.payload.get("account_data", {}),
                    speed_mode=self.speed_mode,
                    headless=self.headless,
                    log_callback=lambda lvl, msg: self.log_signal.emit(lvl, msg),
                    progress_callback=lambda p: self.progress_signal.emit(p)
                )
                loop.run_until_complete(self.bot.run_listing_workflow(self.payload))
                self.finished_signal.emit(True, "Marketplace listing published successfully!")
        except Exception as e:
            self.finished_signal.emit(False, str(e))
        finally:
            loop.close()
`;

export const imageProcessorSnippet = `#!/usr/bin/env python3
"""
FB Auto Bot - Facebook Marketplace Automation Suite
utils/image_processor.py - OpenCV & Pillow Anti-Duplicate Image Processing Engine

Prevents Facebook Marketplace from detecting and flagging duplicate images across
multiple posts through a comprehensive pixel & metadata manipulation pipeline:
  1. Micro-Rotation & Zoom Crop (random angle ±0.2° to ±0.8° to break perceptual grid hashing)
  2. Complete EXIF / Metadata Stripping (eliminates camera, GPS, software, and timestamp tags)
  3. Microscopic Color, Brightness & Contrast Jitter (±1-2% shifts)
  4. Subtle Pixel Noise Injection (RGB micro-variations for unique cryptographic hash)
  5. Micro-Canvas Resizing & Border Padding (alters physical dimension signatures)
  6. Secure Batch Output to temp_uploads/ with randomized hash filenames
"""

import os
import sys
import uuid
import random
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple, Callable

# PIL is the primary image manipulation library
try:
    from PIL import Image, ImageEnhance, ImageOps, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Piexif for thorough EXIF deletion
try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False

# OpenCV for computer vision affine transformations
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

logger = logging.getLogger("FBAutoBot.ImageProcessor")


class AntiDuplicateConfig:
    """Configuration parameters for the anti-duplicate image alteration pipeline."""

    def __init__(
        self,
        min_rotation: float = -0.6,
        max_rotation: float = 0.6,
        brightness_jitter: float = 0.02,   # ±2%
        contrast_jitter: float = 0.02,     # ±2%
        color_jitter: float = 0.02,        # ±2%
        micro_noise_level: float = 1.5,    # Imperceptible RGB noise amplitude (0-255 scale)
        micro_pad_px: int = 2,             # 1-2px border padding
        strip_exif: bool = True,
        output_format: str = "JPEG",
        jpeg_quality: int = 94,
        temp_dir_name: str = "temp_uploads"
    ):
        self.min_rotation = min_rotation
        self.max_rotation = max_rotation
        self.brightness_jitter = brightness_jitter
        self.contrast_jitter = contrast_jitter
        self.color_jitter = color_jitter
        self.micro_noise_level = micro_noise_level
        self.micro_pad_px = micro_pad_px
        self.strip_exif = strip_exif
        self.output_format = output_format
        self.jpeg_quality = jpeg_quality
        self.temp_dir_name = temp_dir_name


class AntiDuplicateImageProcessor:
    """
    Production-grade image transformation engine designed to defeat duplicate image
    hashing algorithms (MD5/SHA256 file hashes, block-mean hashing, dHash, and pHash).
    """

    def __init__(self, config: Optional[AntiDuplicateConfig] = None, base_dir: Optional[str] = None):
        self.config = config or AntiDuplicateConfig()
        if base_dir:
            self.temp_dir = os.path.join(base_dir, self.config.temp_dir_name)
        else:
            self.temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", self.config.temp_dir_name))

        os.makedirs(self.temp_dir, exist_ok=True)

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calculates MD5 hash of a local file."""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def process_single_image(
        self,
        input_image_path: str,
        log_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, Any]:
        log = log_callback or (lambda lvl, msg: logger.info(f"[{lvl}] {msg}"))

        if not os.path.exists(input_image_path):
            raise FileNotFoundError(f"Input image not found: {input_image_path}")

        filename = os.path.basename(input_image_path)
        original_hash = self.calculate_file_hash(input_image_path)
        log("INFO", f"Anti-Duplicate Engine: Processing '{filename}' (Original MD5: {original_hash[:10]}...)")

        with Image.open(input_image_path) as img:
            img = img.convert("RGB")
            orig_w, orig_h = img.size

            # 1. Micro-Rotation & Crop
            angle = random.uniform(self.config.min_rotation, self.config.max_rotation)
            if abs(angle) < 0.1:
                angle = 0.25 if angle >= 0 else -0.25

            rotated_img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
            rot_w, rot_h = rotated_img.size
            crop_x = max(0, (rot_w - orig_w) // 2)
            crop_y = max(0, (rot_h - orig_h) // 2)
            cropped_img = rotated_img.crop((crop_x, crop_y, crop_x + orig_w, crop_y + orig_h))

            # 2. Color, Brightness & Contrast Micro-Jitter
            b_factor = 1.0 + random.uniform(-self.config.brightness_jitter, self.config.brightness_jitter)
            bright_img = ImageEnhance.Brightness(cropped_img).enhance(b_factor)

            c_factor = 1.0 + random.uniform(-self.config.contrast_jitter, self.config.contrast_jitter)
            contrast_img = ImageEnhance.Contrast(bright_img).enhance(c_factor)

            col_factor = 1.0 + random.uniform(-self.config.color_jitter, self.config.color_jitter)
            enhanced_img = ImageEnhance.Color(contrast_img).enhance(col_factor)

            # 3. Microscopic Noise Injection
            if CV2_AVAILABLE and np:
                arr = np.array(enhanced_img, dtype=np.float32)
                noise = np.random.normal(0, self.config.micro_noise_level, arr.shape).astype(np.float32)
                arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
                noisy_img = Image.fromarray(arr)
            else:
                noisy_img = enhanced_img

            # 4. Watermark & Micro-Canvas Resizing / Border Padding
            pad = random.choice([1, 2])
            padded_img = ImageOps.expand(noisy_img, border=pad, fill=(245, 245, 245))
            final_w, final_h = padded_img.size

            # 5. Save & EXIF Stripping
            random_id = uuid.uuid4().hex[:8]
            clean_name = f"fbv_{random_id}.jpg"
            output_path = os.path.join(self.temp_dir, clean_name)
            dyn_quality = random.randint(self.config.jpeg_quality - 2, self.config.jpeg_quality + 1)
            
            padded_img.save(output_path, format="JPEG", quality=dyn_quality, subsampling=0, optimize=True)

            if PIEXIF_AVAILABLE:
                try:
                    piexif.remove(output_path)
                except Exception:
                    pass

        new_hash = self.calculate_file_hash(output_path)
        log(
            "SUCCESS",
            f"Image '{filename}' processed: Micro-rotated ({angle:+.2f}°), EXIF stripped, "
            f"Dimensions: {orig_w}x{orig_h} -> {final_w}x{final_h}, New MD5: {new_hash[:10]}... (100% Unique)"
        )

        return {
            "original_path": input_image_path,
            "processed_path": output_path,
            "original_hash": original_hash,
            "new_hash": new_hash,
            "angle": round(angle, 3),
            "dimension_shift": (final_w - orig_w, final_h - orig_h)
        }

    def process_batch(self, image_paths: List[str], log_callback=None) -> List[str]:
        processed_files = []
        log = log_callback or (lambda lvl, msg: logger.info(f"[{lvl}] {msg}"))
        for img in image_paths:
            try:
                res = self.process_single_image(img, log_callback=log)
                processed_files.append(res["processed_path"])
            except Exception as e:
                log("ERROR", f"Failed {img}: {str(e)}")
                processed_files.append(img)
        return processed_files
`;

export const sessionManagerSnippet = `#!/usr/bin/env python3
"""
FB Auto Bot - Facebook Marketplace Automation Suite
automation/session_manager.py - Multi-Account Persistence & Session Cookie Manager
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime
from playwright.async_api import async_playwright

class SessionCookieParser:
    """Parses arbitrary cookie formats into Playwright-compliant dictionaries."""

    @staticmethod
    def normalize_cookies(raw_cookies: Any) -> List[Dict[str, Any]]:
        # Handles both Netscape/EditThisCookie JSON and semicolon 'c_user=...; xs=...'
        ...

    parse_cookies = normalize_cookies


class SessionManager:
    """
    Manages accounts, isolated profiles (profiles/<id>/), proxy bindings,
    session health verification, and interactive manual login.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.config_dir = os.path.join(self.base_dir, "config")
        self.profiles_dir = os.path.join(self.base_dir, "profiles")
        self.db_path = os.path.join(self.config_dir, "accounts_db.json")
        self._init_db()

    def get_profile_dir(self, account_id: str) -> str:
        """Returns isolated browser user data profile directory: profiles/<account_id>/"""
        p_dir = os.path.join(self.profiles_dir, account_id)
        os.makedirs(p_dir, exist_ok=True)
        return p_dir

    async def verify_session_health(self, account_id: str, log_callback=None) -> Tuple[str, str]:
        """Boots headless Playwright check to test if account is logged in."""
        # Detects: 'Healthy', 'Needs Login', 'Checkpoint', 'Proxy Error'
        ...

    async def launch_manual_login(self, account_id: str, log_callback=None, on_cookies_captured=None) -> bool:
        """Launches headful browser to solve 2FA/checkpoint and auto-extract cookies."""
        ...
`;

export const aiSpinnerSnippet = `#!/usr/bin/env python3
"""
FB Auto Bot - Facebook Marketplace Automation Suite
utils/ai_spinner.py - AI Content Spinner & Title/Description Generator
Powered by Gemini API with Offline Spintax & Synonym Replacement Engine
"""

import os
import re
import json
import random
import logging
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger("FBAutoBot.AISpinner")

class SpintaxEngine:
    """
    Offline spintax parser and synonym replacement engine.
    Parses nested expressions: '{Option A|Option B|{C1|C2}}'
    and applies contextual Marketplace sales transformations.
    """

    SYNONYMS = {
        "brand new": ["100% brand new", "factory sealed", "unopened in box", "never used", "sealed box"],
        "like new": ["flawless condition", "mint condition", "barely used", "near perfect"],
        "fast shipping": ["same-day dispatch", "ships within 24h", "tracked express postage"],
        "local pickup": ["in-person pickup available", "safe public meetup", "front porch collection"],
        "authentic": ["100% genuine", "verified authentic", "receipt available on request"]
    }

    TITLE_PREFIXES = [
        "{🔥 Deal! |⚡ Special: |Brand New |Sealed |Authentic |Original }",
        "{[Must Go!] |[SALE] |[Verified Genuine] |[Ready for Pickup] }",
        "{New In Box: |Factory Sealed: |Best Price: }"
    ]

    TITLE_SUFFIXES = [
        " {- Fast Pickup / Shipping Available}",
        " {- Sealed Box (Never Opened)}",
        " { [Mint Condition / Warranty Ready]}",
        " {- Best Deal Around}",
        " {- Priced to Sell Quickly}"
    ]

    @classmethod
    def parse_spintax(cls, text: str) -> str:
        """Recursively parses and resolves spintax like '{A|B|{C|D}}'."""
        pattern = re.compile(r"\\{([^{}]+)\\}")
        while True:
            match = pattern.search(text)
            if not match:
                break
            choices = match.group(1).split("|")
            text = text[:match.start()] + random.choice(choices) + text[match.end():]
        return text

    @classmethod
    def spin_title(cls, seed_title: str, count: int = 5) -> List[str]:
        """Generates distinct, high-CTR title variants using offline heuristics."""
        clean_seed = seed_title.strip()
        variants = set()
        variants.add(cls.parse_spintax(f"{random.choice(cls.TITLE_PREFIXES)}{clean_seed}"))
        variants.add(cls.parse_spintax(f"{clean_seed}{random.choice(cls.TITLE_SUFFIXES)}"))
        variants.add(cls.parse_spintax(f"{random.choice(cls.TITLE_PREFIXES)}{clean_seed}{random.choice(cls.TITLE_SUFFIXES)}"))
        return list(variants)[:count]

    @classmethod
    def spin_description(cls, base_desc: str, title: str = "", tone: str = "Professional", count: int = 3) -> List[str]:
        """Generates rich, structured description variants offline with bullet points & specs."""
        ...


class GeminiAISpinner:
    """
    AI Content Generator & Rewriter leveraging the Google Gemini API.
    Falls back cleanly to the SpintaxEngine when offline or if API errors occur.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model_name

    def generate_titles(self, seed_keyword: str, tone: str = "Casual", count: int = 5, log_callback=None) -> List[str]:
        """Generates 3 to 5 click-worthy Facebook Marketplace titles."""
        if not self.api_key:
            return SpintaxEngine.spin_title(seed_keyword, count=count)
        # Calls Gemini model with JSON response schema and returns list of strings
        ...

    def rewrite_description(self, base_description: str, title: str = "", tone: str = "Professional", count: int = 3, log_callback=None) -> List[str]:
        """Rewrites product descriptions into unique variants to evade duplicate text detection."""
        if not self.api_key:
            return SpintaxEngine.spin_description(base_description, title=title, tone=tone, count=count)
        # Generates structured copy with specifications, condition, and logistics
        ...
`;

export const requirementsSnippet = `# FB Auto Bot - Dependencies
PyQt5>=5.15.9
playwright>=1.41.0
playwright-stealth>=1.0.6
opencv-python>=4.9.0
Pillow>=10.2.0
piexif>=1.1.3
numpy>=1.26.0
google-genai>=0.1.1
requests>=2.31.0
`;

export const landingPageSnippet = `<!-- 
  FB Auto Bot - High-Converting Glassmorphic Landing Page
  Single-file HTML with Tailwind CSS (CDN) + Vanilla JS Accordion
  Host for free on Cloudflare Pages or Vercel
-->
<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FB Auto Bot - AI-Powered Facebook Marketplace Automation Software</title>
  <meta name="description" content="Dominate Facebook Marketplace with FB Auto Bot. Multi-account isolation, OpenCV image duplicate shield, Playwright anti-detect browser, and Gemini AI spintax copywriting.">
  
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"><\/script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: {
            sans: ['"Plus Jakarta Sans"', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'monospace']
          },
          colors: {
            dark: { 950: '#070a12', 900: '#0b0f19', 850: '#0f172a', 800: '#131d33', 700: '#1e293b' }
          }
        }
      }
    }
  <\/script>

  <style>
    body { background-color: #0b0f19; color: #f1f5f9; font-family: 'Plus Jakarta Sans', sans-serif; overflow-x: hidden; }
    .glass-panel { background: rgba(17, 24, 39, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); }
    .glass-panel-hover:hover { background: rgba(22, 30, 49, 0.85); border-color: rgba(99, 102, 241, 0.35); transform: translateY(-3px); }
    .glass-nav { background: rgba(11, 15, 25, 0.85); backdrop-filter: blur(20px); border-bottom: 1px solid rgba(255, 255, 255, 0.07); }
    .glow-indigo { box-shadow: 0 0 50px -10px rgba(99, 102, 241, 0.3); }
  </style>
</head>
<body class="min-h-screen relative selection:bg-indigo-500 selection:text-white">
  <!-- Sticky Navbar, Hero Section, Features Grid, Architecture Comparison, Pricing, FAQ Accordion & WhatsApp CTAs -->
  <!-- See full index.html file in /landing_page/index.html -->
</body>
</html>
`;
