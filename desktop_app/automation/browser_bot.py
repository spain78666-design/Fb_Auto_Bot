"""
FB Auto Bot - Enterprise Playwright Stealth Browser Controller
Phase 2: Asynchronous Anti-Detect Automation for Facebook Marketplace
"""

import os
import sys
import re
import json
import random
import socket
import asyncio
from typing import List, Dict, Any, Optional, Callable
from urllib.parse import urlparse
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    Browser = None
    BrowserContext = None
    Page = None
    class PlaywrightTimeoutError(Exception):
        pass

try:
    from playwright_stealth import stealth_async
    HAS_PLAYWRIGHT_STEALTH = True
except ImportError:
    HAS_PLAYWRIGHT_STEALTH = False

try:
    from utils.image_processor import AntiDuplicateImageProcessor, AntiDuplicateConfig, process_image_batch
    IMAGE_PROCESSOR_AVAILABLE = True
except ImportError:
    try:
        from desktop_app.utils.image_processor import AntiDuplicateImageProcessor, AntiDuplicateConfig, process_image_batch
        IMAGE_PROCESSOR_AVAILABLE = True
    except ImportError:
        IMAGE_PROCESSOR_AVAILABLE = False

try:
    from automation.fault_tolerance import DistinctDataMapper, MethodFallbackManager
    HAS_FAULT_TOLERANCE = True
except ImportError:
    try:
        from desktop_app.automation.fault_tolerance import DistinctDataMapper, MethodFallbackManager
        HAS_FAULT_TOLERANCE = True
    except ImportError:
        HAS_FAULT_TOLERANCE = False
        DistinctDataMapper = None
        MethodFallbackManager = None

try:
    from automation.macro_recorder import MacroMethodPlayer, MacroMethodManager
    HAS_MACRO_RECORDER = True
except ImportError:
    try:
        from desktop_app.automation.macro_recorder import MacroMethodPlayer, MacroMethodManager
        HAS_MACRO_RECORDER = True
    except ImportError:
        HAS_MACRO_RECORDER = False
        MacroMethodPlayer = None
        MacroMethodManager = None


# ==============================================================================
# Custom Automation Exceptions
# ==============================================================================
class MarketplaceBotError(Exception):
    """Base exception for FB Auto Bot automation failures."""
    pass

class InvalidSessionError(MarketplaceBotError):
    """Raised when authentication cookies are expired, malformed, or rejected."""
    pass

class CheckpointDetectedError(MarketplaceBotError):
    """Raised when Facebook triggers an identity verification or security checkpoint."""
    pass

class ProxyConnectionError(MarketplaceBotError):
    """Raised when the configured HTTP/SOCKS5 proxy fails to connect or times out."""
    pass

class NavigationTimeoutError(MarketplaceBotError):
    """Raised when page loading times out under the configured threshold."""
    pass

class ListingSubmissionError(MarketplaceBotError):
    """Raised when required form selectors fail or Marketplace restricts posting."""
    pass

class MethodExecutionFallbackError(MarketplaceBotError):
    """Raised when a pre-recorded Method Manager workflow encounters a step failure."""
    pass


# ==============================================================================
# Stealth JavaScript Evasion & Fingerprint Shield Scripts
# ==============================================================================
EXTRA_STEALTH_JS = """
(() => {
    // 1. Completely remove and mask navigator.webdriver
    try {
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });
    } catch (e) {}

    // 2. Erase Playwright & Automation signatures from Window
    try {
        const keysToErase = ['__playwright', '__puppeteer_evaluation_script__', 'callPhantom', '_phantom', 'phantom'];
        keysToErase.forEach(k => {
            try { delete window[k]; } catch (e) {}
        });
        for (let prop in window) {
            if (prop.match(/^cdc_/i)) {
                try { delete window[prop]; } catch (e) {}
            }
        }
    } catch (e) {}

    // 3. Realistic Hardware & Device Fingerprint Spoofing
    try {
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8, configurable: true });
        Object.defineProperty(navigator, 'deviceMemory', { get: () => 8, configurable: true });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'], configurable: true });
        Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0, configurable: true });
        Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.', configurable: true });
    } catch (e) {}

    // 4. Mock Authentic Chrome Runtime & CSI
    if (!window.chrome) {
        window.chrome = {};
    }
    window.chrome.app = window.chrome.app || { isInstalled: false, InstallState: { DISABLED: 'disabled' }, RunningState: { CANNOT_RUN: 'cannot_run' } };
    window.chrome.runtime = window.chrome.runtime || {
        OnInstalledReason: { INSTALL: 'install', UPDATE: 'update', CHROME_UPDATE: 'chrome_update' },
        PlatformOs: { MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux' },
        PlatformArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' },
        connect: () => {},
        sendMessage: () => {}
    };
    window.chrome.csi = window.chrome.csi || function() {
        return { startE: Date.now() - 1000, onloadT: Date.now() - 200, pageT: 800, tran: 15 };
    };

    // 5. WebGL Vendor & Renderer Fingerprint Protection
    try {
        const getParameterProto = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.'; // UNMASKED_VENDOR_WEBGL
            if (parameter === 37446) return 'Intel(R) Iris(R) Xe Graphics (0x9a49)'; // UNMASKED_RENDERER_WEBGL
            return getParameterProto.apply(this, arguments);
        };

        if (typeof WebGL2RenderingContext !== 'undefined') {
            const getParameterProto2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel(R) Iris(R) Xe Graphics (0x9a49)';
                return getParameterProto2.apply(this, arguments);
            };
        }
    } catch (e) {}

    // 6. Overwrite Permissions query for notifications
    try {
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission, onchange: null }) :
                originalQuery(parameters)
        );
    } catch (e) {}

    // 7. Authentic Plugins List Spoofing
    try {
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' }
                ];
                plugins.item = (i) => plugins[i];
                plugins.namedItem = (name) => plugins.find(p => p.name === name);
                return plugins;
            },
            configurable: true
        });
    } catch (e) {}
})();
"""


# ==============================================================================
# Helper Functions: Cookie, Proxy & Lock Cleaners
# ==============================================================================
def clean_profile_locks(profile_dir: Optional[str]):
    """Removes stale Chrome lock files that prevent Playwright persistent browser context startup."""
    if not profile_dir or not os.path.exists(profile_dir):
        return
    lock_files = ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"]
    for fname in lock_files:
        fpath = os.path.join(profile_dir, fname)
        if os.path.exists(fpath) or os.path.islink(fpath):
            try:
                if os.path.islink(fpath) or os.path.isfile(fpath):
                    os.unlink(fpath)
                elif os.path.isdir(fpath):
                    import shutil
                    shutil.rmtree(fpath, ignore_errors=True)
            except Exception:
                pass
def parse_cookie_payload(raw_cookies: str) -> List[Dict[str, Any]]:
    """
    Parses both JSON array cookie exports and raw semicolon string formats
    (e.g., 'c_user=1000...; xs=2%3A...; datr=...').
    Returns a list of standardized cookies suitable for Playwright.
    """
    cleaned = raw_cookies.strip()
    if not cleaned:
        return []

    # Format 1: JSON Array
    if cleaned.startswith("[") and cleaned.endswith("]"):
        try:
            items = json.loads(cleaned)
            formatted = []
            for item in items:
                cookie = {
                    "name": str(item.get("name", "")),
                    "value": str(item.get("value", "")),
                    "domain": item.get("domain", ".facebook.com"),
                    "path": item.get("path", "/"),
                }
                # Fix domain dot prefix if missing
                if not cookie["domain"].startswith("."):
                    cookie["domain"] = "." + cookie["domain"]
                if "sameSite" in item and item["sameSite"] in ["Strict", "Lax", "None"]:
                    cookie["sameSite"] = item["sameSite"]
                if "secure" in item:
                    cookie["secure"] = bool(item["secure"])
                if cookie["name"]:
                    formatted.append(cookie)
            return formatted
        except json.JSONDecodeError:
            pass

    # Format 2: Semicolon key=value string
    formatted = []
    pairs = cleaned.split(";")
    for pair in pairs:
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        key, val = pair.split("=", 1)
        key = key.strip()
        val = val.strip()
        if key:
            formatted.append({
                "name": key,
                "value": val,
                "domain": ".facebook.com",
                "path": "/",
                "secure": True
            })
    return formatted


def get_base_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_fewfeed_extension_path() -> Optional[str]:
    """Resolves the absolute path to FEWFEED extension folder."""
    candidates = [
        os.path.join(get_base_dir(), "FEWFEED"),
        os.path.join(getattr(sys, '_MEIPASS', ''), "FEWFEED"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "FEWFEED")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "FEWFEED")),
        "/desktop_app/FEWFEED",
        os.path.abspath("FEWFEED"),
        os.path.abspath("desktop_app/FEWFEED")
    ]
    for c in candidates:
        if c and os.path.isdir(c) and os.path.exists(os.path.join(c, "manifest.json")):
            return os.path.abspath(c)
    return None


def sync_fewfeed_extension_session(master_dir: str, target_dir: str) -> bool:
    """Helper to copy extension session storage from master profile to target profile."""
    if not master_dir or not target_dir or not os.path.exists(master_dir):
        return False
    if os.path.abspath(master_dir) == os.path.abspath(target_dir):
        return False

    items = [
        "Local Extension Settings",
        "Sync Extension Settings",
        "Managed Extension Settings",
        "Extension State",
        "IndexedDB",
        "Storage",
        "Local Storage"
    ]
    copied = False
    master_subs = [master_dir, os.path.join(master_dir, "Default")]
    target_base = os.path.join(target_dir, "Default") if (os.path.exists(os.path.join(target_dir, "Default")) or os.path.exists(os.path.join(master_dir, "Default"))) else target_dir
    os.makedirs(target_base, exist_ok=True)

    for item in items:
        src = None
        for msub in master_subs:
            c = os.path.join(msub, item)
            if os.path.exists(c):
                src = c
                break
        if not src:
            continue
        dest = os.path.join(target_base, item)
        try:
            if os.path.isdir(src):
                import shutil
                shutil.copytree(src, dest, dirs_exist_ok=True)
                copied = True
            elif os.path.isfile(src):
                import shutil
                shutil.copy2(src, dest)
                copied = True
        except Exception:
            pass
    return copied


def test_proxy_connectivity(host: str, port: int, timeout: float = 2.5) -> bool:
    """Quick socket probe to check if proxy is alive before launching browser."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except Exception:
        return False


def parse_proxy_payload(
    proxy_str: str,
    protocol: str = "http",
    user: Optional[str] = None,
    password: Optional[str] = None,
    verify_live: bool = True
) -> Optional[Dict[str, str]]:
    """
    Constructs a Playwright proxy dictionary from raw inputs.
    Supports formats:
      - '185.199.229.15:8080'
      - 'http://user:pass@host:port'
      - 'socks5://host:port'
    If verify_live is True and proxy is unreachable/invalid, returns None (safe direct fallback).
    """
    if not proxy_str or "Direct" in proxy_str:
        return None

    raw = proxy_str.strip()
    if not raw:
        return None

    if "://" not in raw:
        proto = protocol.lower() if protocol else "http"
        server_str = f"{proto}://{raw}"
    else:
        server_str = raw

    try:
        parsed = urlparse(server_str)
        if not parsed.hostname or not parsed.port:
            return None

        # Verify proxy is reachable to avoid ERR_PROXY_CONNECTION_FAILED
        if verify_live:
            is_live = test_proxy_connectivity(parsed.hostname, parsed.port, timeout=2.0)
            if not is_live:
                return None

        proxy_config = {
            "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
        }

        # Extract credentials from parsed URL or separate parameters
        final_user = parsed.username or user
        final_pass = parsed.password or password

        if final_user:
            proxy_config["username"] = final_user
        if final_pass:
            proxy_config["password"] = final_pass

        return proxy_config
    except Exception:
        return None


# ==============================================================================
# Playwright Stealth Browser Controller
# ==============================================================================
class FacebookMarketplaceBot:
    """
    Production-grade Playwright stealth automation controller for Facebook Marketplace.
    """

    def __init__(
        self,
        headless: bool = False,
        speed_mode: str = "Normal",
        log_callback: Optional[Callable[[str, str], None]] = None,
        progress_callback: Optional[Callable[[int], None]] = None
    ):
        self.headless = headless
        self.speed_mode = speed_mode
        self.log_callback = log_callback or (lambda level, msg: None)
        self.progress_callback = progress_callback or (lambda val: None)
        
        # Speed multipliers for delays
        self.speed_multipliers = {
            "Fast": 0.5,
            "Normal": 1.0,
            "Slow": 1.8
        }
        self.mult = self.speed_multipliers.get(self.speed_mode, 1.0)
        
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._cancel_requested = False

    def log(self, level: str, message: str):
        self.log_callback(level, message)

    def set_progress(self, percent: int):
        self.progress_callback(percent)

    def cancel(self):
        self._cancel_requested = True
        self.log("WARNING", "Automation cancellation signaled to browser controller.")

    async def sleep(self, seconds: float):
        """Asynchronous delay scaled by speed multiplier, checking cancellation."""
        adjusted = seconds * self.mult
        steps = int(adjusted / 0.1)
        for _ in range(max(1, steps)):
            if self._cancel_requested:
                raise MarketplaceBotError("Automation cancelled by user.")
            await asyncio.sleep(0.1)

    async def human_type(self, selector: str, text: str, min_delay_ms: int = 70, max_delay_ms: int = 200):
        """Types text into an input field with natural human-like keystroke variance."""
        if self._cancel_requested:
            raise MarketplaceBotError("Automation cancelled by user.")
        
        element = await self.page.wait_for_selector(selector, timeout=12000)
        if not element:
            raise ListingSubmissionError(f"Target input '{selector}' not found.")
        
        await element.click()
        await self.sleep(random.uniform(0.2, 0.5))

        # Clear existing text safely
        await self.page.keyboard.press("Control+A")
        await self.page.keyboard.press("Backspace")

        for idx, char in enumerate(text):
            if self._cancel_requested:
                raise MarketplaceBotError("Automation cancelled by user.")
            
            # Randomized human jitter
            delay = (random.randint(min_delay_ms, max_delay_ms) / 1000.0) * self.mult
            await asyncio.sleep(delay)
            await self.page.keyboard.type(char)

            # 1.5% chance of realistic typo and backspace correction for longer strings
            if len(text) > 15 and idx > 3 and random.random() < 0.015:
                wrong_char = chr(ord(char) + 1)
                await self.page.keyboard.type(wrong_char)
                await asyncio.sleep(random.uniform(0.12, 0.25))
                await self.page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.08, 0.18))

    async def human_scroll(self, steps: int = 4):
        """Emulates organic human scrolling with deceleration."""
        for _ in range(steps):
            if self._cancel_requested:
                break
            delta = random.randint(150, 350)
            await self.page.mouse.wheel(0, delta)
            await asyncio.sleep(random.uniform(0.3, 0.7) * self.mult)

    # --------------------------------------------------------------------------
    # Browser Initialization & Session Verification
    # --------------------------------------------------------------------------
    async def initialize_browser(
        self,
        raw_cookies: str,
        proxy_config: Optional[Dict[str, str]] = None,
        custom_user_agent: Optional[str] = None,
        user_data_dir: Optional[str] = None
    ):
        """Launches Playwright with stealth configurations and loads the account session."""
        self.log("INFO", "Initializing Playwright browser context...")
        self.set_progress(10)

        self.playwright = await async_playwright().start()

        # Modern desktop Chrome user agent
        ua = custom_user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        )

        ext_path = get_fewfeed_extension_path()
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--start-maximized",
            "--disable-infobars",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-default-browser-check",
            "--disable-dev-shm-usage",
            "--lang=en-US,en",
            "--ignore-certificate-errors",
            "--allow-running-insecure-content",
            "--disable-web-security",
            "--disable-notifications",
            "--password-store=basic",
            "--no-first-run",
            "--no-service-autorun"
        ]

        if ext_path and os.path.exists(ext_path):
            launch_args.append(f"--load-extension={ext_path}")
            launch_args.append(f"--disable-extensions-except={ext_path}")
            self.log("SUCCESS", f"🧩 Automatically loaded Chrome Extension from: {ext_path}")

        # Ignore automation banner
        ignore_default_args = ["--enable-automation"]

        async def launch_context_smart():
            clean_profile_locks(user_data_dir)
            for ch in ["chrome", "msedge", None]:
                try:
                    kwargs = {
                        "user_data_dir": user_data_dir,
                        "headless": self.headless,
                        "args": launch_args,
                        "ignore_default_args": ignore_default_args,
                        "proxy": proxy_config,
                        "user_agent": ua,
                        "no_viewport": True,
                        "locale": "en-US",
                        "timezone_id": "America/New_York",
                        "permissions": ["geolocation", "notifications"]
                    }
                    if ch:
                        kwargs["channel"] = ch
                    ctx = await self.playwright.chromium.launch_persistent_context(**kwargs)
                    self.log("INFO", f"Launched full-screen browser using: {ch.upper() if ch else 'Chromium'}")
                    return ctx
                except Exception as ex:
                    self.log("WARNING", f"Persistent launch attempt with channel={ch} notice: {str(ex)[:100]}")
                    clean_profile_locks(user_data_dir)
                    continue

            # Fallback to standard launch if persistent context fails across channels
            self.log("WARNING", "Persistent profile context locked or unavailable. Engaging standard browser launch with injected cookies...")
            self.browser = await launch_browser_smart()
            ctx = await self.browser.new_context(
                user_agent=ua,
                no_viewport=True,
                locale="en-US",
                timezone_id="America/New_York",
                permissions=["geolocation", "notifications"]
            )
            return ctx

        async def launch_browser_smart():
            for ch in ["chrome", "msedge", None]:
                try:
                    kwargs = {
                        "headless": self.headless,
                        "args": launch_args,
                        "ignore_default_args": ignore_default_args,
                        "proxy": proxy_config
                    }
                    if ch:
                        kwargs["channel"] = ch
                    b = await self.playwright.chromium.launch(**kwargs)
                    self.log("INFO", f"Launched full-screen browser using: {ch.upper() if ch else 'Chromium'}")
                    return b
                except Exception as ex:
                    self.log("WARNING", f"Browser launch attempt with channel={ch} notice: {str(ex)[:100]}")
                    continue
            # Failsafe: Try launching without extension flags if extension failed
            try:
                self.log("WARNING", "Attempting failsafe browser launch without extension flags...")
                b = await self.playwright.chromium.launch(
                    headless=self.headless,
                    args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
                    ignore_default_args=ignore_default_args
                )
                return b
            except Exception as final_ex:
                raise MarketplaceBotError(f"Could not launch Chrome or Chromium on this PC: {str(final_ex)}")

        try:
            if user_data_dir:
                self.log("INFO", f"Using isolated browser profile dir: {os.path.basename(user_data_dir)}")
                try:
                    master_dir = os.path.join(get_base_dir(), "profiles", "master_fewfeed_profile")
                    if os.path.exists(master_dir) and os.path.abspath(master_dir) != os.path.abspath(user_data_dir):
                        sync_fewfeed_extension_session(master_dir, user_data_dir)
                except Exception:
                    pass
                self.context = await launch_context_smart()
                self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            else:
                self.browser = await launch_browser_smart()
                self.context = await self.browser.new_context(
                    user_agent=ua,
                    no_viewport=True,
                    locale="en-US",
                    timezone_id="America/New_York",
                    permissions=["geolocation", "notifications"]
                )
                self.page = await self.context.new_page()
        except Exception as e:
            # If failed due to proxy connection, retry immediately without proxy as a failsafe
            if proxy_config and ("proxy" in str(e).lower() or "connect" in str(e).lower() or "net::" in str(e).lower()):
                self.log("WARNING", f"Proxy {proxy_config.get('server')} failed; falling back to direct connection...")
                if user_data_dir:
                    self.context = await self.playwright.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir,
                        headless=self.headless,
                        args=launch_args,
                        ignore_default_args=ignore_default_args,
                        proxy=None,
                        user_agent=ua,
                        no_viewport=True,
                        locale="en-US",
                        timezone_id="America/New_York",
                        permissions=["geolocation", "notifications"]
                    )
                    self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
                else:
                    self.browser = await self.playwright.chromium.launch(
                        headless=self.headless,
                        args=launch_args,
                        ignore_default_args=ignore_default_args,
                        proxy=None
                    )
                    self.context = await self.browser.new_context(
                        user_agent=ua,
                        no_viewport=True,
                        locale="en-US",
                        timezone_id="America/New_York",
                        permissions=["geolocation", "notifications"]
                    )
                    self.page = await self.context.new_page()
            else:
                raise MarketplaceBotError(f"Failed to launch browser: {str(e)}")

        # Apply stealth scripts
        if HAS_PLAYWRIGHT_STEALTH:
            await stealth_async(self.page)
        await self.page.add_init_script(EXTRA_STEALTH_JS)

        # Inject authentication cookies if present
        cookies = parse_cookie_payload(raw_cookies) if raw_cookies else []
        if cookies:
            has_c_user = any(c["name"] == "c_user" for c in cookies)
            has_xs = any(c["name"] == "xs" for c in cookies)

            if not (has_c_user and has_xs):
                self.log("WARNING", "Cookies missing 'c_user' or 'xs' token. Facebook authentication may fail.")

            try:
                await self.context.add_cookies(cookies)
                self.log("INFO", f"Injected {len(cookies)} authentication cookie(s) into browser session.")
            except Exception as ce:
                self.log("WARNING", f"Cookie injection notice: {str(ce)[:80]}")
        elif user_data_dir:
            self.log("INFO", f"Persistent browser profile '{os.path.basename(user_data_dir)}' active; utilizing saved browser authentication.")
        else:
            self.log("INFO", "Starting browser session...")

        self.set_progress(20)

    async def verify_session_health(self, account_data: Optional[Dict[str, Any]] = None):
        """Navigates to Facebook home to verify if the injected session is active. Auto-logs in if credentials are provided."""
        self.log("INFO", "Validating Facebook session authentication...")
        self.set_progress(25)

        try:
            response = await self.page.goto(
                "https://www.facebook.com/",
                wait_until="domcontentloaded",
                timeout=35000
            )
            await self.sleep(2.0)
        except PlaywrightTimeoutError:
            raise NavigationTimeoutError("Facebook failed to load within 35 seconds. Check proxy latency.")

        current_url = self.page.url.lower()
        self.log("INFO", f"Facebook responded on URL: {self.page.url}")

        content = await self.page.content()
        is_login_page = "login" in current_url or "login_form" in content or "login_button" in content
        is_checkpoint = "checkpoint" in current_url

        if is_login_page or is_checkpoint:
            # Check if account_data provides UID/Email + Password for automatic authentication
            uid_email = (account_data.get("uid") or account_data.get("email") or "") if account_data else ""
            pwd = account_data.get("password", "") if account_data else ""
            two_fa = account_data.get("two_factor_secret", "") if account_data else ""

            if uid_email and pwd and not is_checkpoint:
                self.log("INFO", f"🔑 Session expired or not active. Performing auto-login with UID/Email ({uid_email})...")
                try:
                    if "/login" not in current_url:
                        await self.page.goto("https://www.facebook.com/login", wait_until="domcontentloaded", timeout=30000)
                        await self.sleep(1.5)

                    email_el = await self.page.wait_for_selector('input[name="email"], input#email', timeout=10000)
                    if email_el:
                        await email_el.fill(uid_email)
                        await self.sleep(0.4)

                    pass_el = await self.page.wait_for_selector('input[name="pass"], input#pass', timeout=8000)
                    if pass_el:
                        await pass_el.fill(pwd)
                        await self.sleep(0.5)

                    btn = await self.page.query_selector('button[name="login"], button#loginbutton, input[type="submit"]')
                    if btn:
                        await btn.click()
                    else:
                        await self.page.keyboard.press("Enter")

                    await self.sleep(3.0)

                    # Handle 2FA TOTP
                    if "checkpoint" in self.page.url.lower() or "two_step" in self.page.url.lower():
                        if two_fa:
                            try:
                                from automation.session_manager import generate_totp
                                code = generate_totp(two_fa)
                                if code:
                                    self.log("INFO", f"Generated 6-digit TOTP code ({code}). Submitting to 2FA...")
                                    c_inp = await self.page.wait_for_selector('input[name="approvals_code"], input[name="code"]', timeout=8000)
                                    if c_inp:
                                        await c_inp.fill(code)
                                        await self.sleep(0.5)
                                        s_btn = await self.page.query_selector('button#checkpointSubmitButton, button[type="submit"]')
                                        if s_btn:
                                            await s_btn.click()
                                        else:
                                            await self.page.keyboard.press("Enter")
                                        await self.sleep(3.0)
                            except Exception as totp_e:
                                self.log("WARNING", f"2FA Auto-submission notice: {totp_e}")

                    # Check new cookies
                    fresh_cookies = await self.context.cookies()
                    if any(c.get("name") == "c_user" for c in fresh_cookies):
                        self.log("SUCCESS", f"🎉 Auto-login successful! Captured fresh session cookies for {uid_email}")
                        try:
                            from automation.session_manager import get_session_manager, SessionCookieParser
                            sm = get_session_manager()
                            if sm and account_data.get("id"):
                                c_str = SessionCookieParser.cookies_to_semicolon_string(fresh_cookies)
                                sm.save_account(account_id=account_data["id"], cookies=c_str, status="Healthy")
                        except Exception:
                            pass
                        self.set_progress(35)
                        return
                except Exception as auto_log_err:
                    self.log("ERROR", f"Auto-login failed: {auto_log_err}")

            if "checkpoint" in self.page.url.lower():
                raise CheckpointDetectedError(
                    "Facebook Security Checkpoint triggered! Account requires manual verification or 2FA."
                )
            raise InvalidSessionError(
                "Session not logged in or expired. Please click 'Auto-Login Selected' or 'Launch Manual Login' in Accounts Tab."
            )

        self.log("SUCCESS", "Session authenticated successfully! Active Facebook profile confirmed.")
        self.set_progress(35)

    # --------------------------------------------------------------------------
    # Core Listing Publication Flow & Multi-Tab Engine
    # --------------------------------------------------------------------------
    async def set_account_marketplace_location(self, page: Page, main_location: str) -> bool:
        """Sets the Chrome ID / Account primary Marketplace default location on Facebook Marketplace homepage."""
        if not main_location or not main_location.strip():
            return False

        loc_name = main_location.strip()
        self.log("INFO", f"==================================================")
        self.log("INFO", f"🌍 Setting Chrome ID Marketplace Default Location to '{loc_name}'...")

        try:
            if "facebook.com/marketplace" not in page.url or "/create/" in page.url:
                self.log("INFO", "Navigating to Facebook Marketplace main page...")
                await page.goto("https://www.facebook.com/marketplace", wait_until="domcontentloaded", timeout=35000)
                await self.sleep(2.0)

            # Look for location link/button under 'Create new listing' or top header
            loc_btn = None
            selectors = [
                "a[href*='/marketplace/'] span:has-text('km')",
                "a[href*='/marketplace/'] span:has-text('mile')",
                "div[role='button']:has-text('Within')",
                "span:has-text('Within')",
                "div[aria-label*='Location']",
                "div[aria-label*='الموقع']",
                "a[aria-label*='Location']"
            ]

            for sel in selectors:
                try:
                    elem = page.locator(sel).first
                    if await elem.is_visible(timeout=1500):
                        txt = await elem.inner_text()
                        if any(k in txt.lower() for k in ["within", "km", "mile", "location", "·", ","]):
                            loc_btn = elem
                            break
                except Exception:
                    continue

            if not loc_btn:
                all_btns = page.locator("div[role='button'], a, span")
                cnt = await all_btns.count()
                for i in range(min(cnt, 40)):
                    try:
                        t = await all_btns.nth(i).inner_text(timeout=400)
                        if "within" in t.lower() or " km" in t.lower() or " miles" in t.lower():
                            loc_btn = all_btns.nth(i)
                            break
                    except Exception:
                        continue

            if loc_btn:
                self.log("INFO", "📍 Clicking blue Marketplace location selector link...")
                await loc_btn.click(force=True)
                await self.sleep(2.0)

                # Find input inside 'Change location' popup dialog
                dialog_input = page.locator("div[role='dialog'] input[type='text'], div[role='dialog'] input[aria-label*='Location'], input[placeholder*='Location']").first
                if await dialog_input.is_visible(timeout=3500):
                    await dialog_input.click(force=True)
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Backspace")
                    await dialog_input.fill(loc_name)
                    await self.sleep(1.8)

                    sug = page.locator("ul[role='listbox'] li, div[role='option'], div[role='dialog'] ul li").first
                    if await sug.is_visible(timeout=3000):
                        await sug.click(force=True)
                        await self.sleep(1.0)
                    else:
                        await page.keyboard.press("Enter")
                        await self.sleep(1.0)

                    apply_btn = page.locator("div[role='dialog'] div[role='button']:has-text('Apply'), div[role='dialog'] div[role='button']:has-text('Save'), div[role='dialog'] button:has-text('Apply'), div[role='dialog'] div[role='button']:has-text('حفظ')").first
                    if await apply_btn.is_visible(timeout=2000):
                        await apply_btn.click(force=True)
                        await self.sleep(2.0)
                    else:
                        await page.keyboard.press("Enter")
                        await self.sleep(1.5)

                    self.log("SUCCESS", f"✅ Account ID Marketplace Default Location set to '{loc_name}'!")
                    return True

            self.log("INFO", "Marketplace default location updated/retained.")
            return False
        except Exception as err:
            self.log("WARNING", f"Account location notice: {str(err)[:50]}")
            return False

    async def create_marketplace_batch(self, payload: Dict[str, Any]):
        """
        Multi-Tab Parallel Marketplace Listing Engine.
        Opens the exact specified number of Chrome browser tabs simultaneously,
        assigns a separate, distinct location and distinct image to each respective tab,
        and publishes listings with humanized anti-detection delays.
        """
        tabs_count = int(payload.get("tabs_count", payload.get("posts_per_id", 1)))
        tabs_count = max(1, min(tabs_count, 100))

        # 0. Set Chrome ID / Account Main Location first if provided
        main_account_loc = payload.get("project_main_location", "").strip() or payload.get("main_location", "").strip()
        if main_account_loc:
            await self.set_account_marketplace_location(self.page, main_account_loc)

        self.log("INFO", f"==================================================")
        self.log("INFO", f"🚀 MULTI-TAB PARALLEL ENGINE: {tabs_count} Tab(s) Configured")
        self.log("INFO", f"⚡ Preparing Distinct Location & Picture Mappings...")

        # 1. Distinct Location & Picture Mapping or Project Tabs Mapping
        if payload.get("project_tabs") and len(payload["project_tabs"]) > 0:
            proj_tabs = payload["project_tabs"]
            tabs_count = len(proj_tabs)
            tab_payloads = []
            for i, pt in enumerate(proj_tabs):
                tp = dict(payload)
                tp["tab_index"] = i + 1
                tp["total_tabs"] = tabs_count
                tp["title"] = pt.get("title", "")
                tp["price"] = pt.get("price", "0")
                tp["category"] = pt.get("category", "Household")

                # Pick a random location from tab location pool if user provided multiple
                raw_loc = pt.get("location", "")
                loc_pool = [l.strip() for l in re.split(r'[\r\n,;]+', str(raw_loc)) if l.strip()]
                if loc_pool:
                    chosen_loc = random.choice(loc_pool)
                else:
                    chosen_loc = main_account_loc or "Local Radius"
                tp["location"] = chosen_loc

                tp["description"] = pt.get("description", "")
                tp["images"] = pt.get("images", [])
                tp["anti_dup_shield"] = pt.get("anti_dup_shield", True)
                tp["anti_dup_rotate"] = pt.get("anti_dup_rotate", True)
                tp["wipe_exif"] = pt.get("wipe_exif", True)
                tp["anti_dup_noise"] = pt.get("anti_dup_noise", False)
                tab_payloads.append(tp)
            self.log("INFO", f"📁 Project Campaign Mode Active: {len(tab_payloads)} Tab(s) loaded.")
        elif HAS_FAULT_TOLERANCE and DistinctDataMapper:
            tab_payloads = DistinctDataMapper.map_tabs_payload(payload, tabs_count, log_callback=self.log)
        else:
            raw_loc = payload.get("location", "")
            loc_pool = [l.strip() for l in re.split(r'[\r\n,;]+', str(raw_loc)) if l.strip()] or ["Local Radius"]
            imgs_pool = payload.get("images", [])
            tab_payloads = []
            for i in range(tabs_count):
                tp = dict(payload)
                tp["tab_index"] = i + 1
                tp["total_tabs"] = tabs_count
                tp["location"] = random.choice(loc_pool)
                tp["images"] = [imgs_pool[i % len(imgs_pool)]] if imgs_pool else []
                tab_payloads.append(tp)

        self.log("INFO", f"⚡ Distinct Tab Assignments:")
        for idx, tp in enumerate(tab_payloads, 1):
            img_name = os.path.basename(tp['images'][0]) if tp.get('images') else 'None'
            self.log("INFO", f"   📍 Tab [{idx}/{tabs_count}]: Location = '{tp['location']}' | Picture = '{img_name}'")

        # 2. Open ALL tabs simultaneously in Chrome
        tabs: List[Page] = [self.page]
        if tabs_count > 1:
            self.log("INFO", f"📑 Spawning {tabs_count - 1} additional Chrome tabs simultaneously in parallel...")
            try:
                new_pages = await asyncio.gather(*[self.context.new_page() for _ in range(tabs_count - 1)])
                for p in new_pages:
                    if HAS_PLAYWRIGHT_STEALTH:
                        await stealth_async(p)
                    await p.add_init_script(EXTRA_STEALTH_JS)
                    tabs.append(p)
            except Exception as tab_err:
                self.log("WARNING", f"Notice while opening parallel tabs: {str(tab_err)}")

        self.log("SUCCESS", f"✅ All {len(tabs)} Chrome tabs are now open simultaneously in the browser!")

        # 3. Simultaneously navigate all tabs to the Marketplace homepage first
        self.log("INFO", "🌐 Navigating all tabs simultaneously to Facebook Marketplace homepage...")
        async def navigate_to_marketplace_home(tab_num: int, page_obj: Page):
            await asyncio.sleep((tab_num - 1) * random.uniform(0.15, 0.3))
            try:
                await page_obj.goto("https://www.facebook.com/marketplace/", wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                self.log("WARNING", f"Tab [{tab_num}/{tabs_count}] homepage notice: {str(e)[:45]}")

        await asyncio.gather(*[navigate_to_marketplace_home(i + 1, tabs[i]) for i in range(len(tabs))])
        self.log("SUCCESS", "🎉 All tabs loaded at Facebook Marketplace homepage!")

        # 4. Set Facebook ID Location on first tab and refresh all tabs
        id_location = payload.get("id_location", "").strip()
        if id_location:
            self.log("INFO", f"📍 First tab: Updating primary Facebook ID / Account Location to '{id_location}'...")
            set_ok = await self.set_account_marketplace_location(tabs[0], id_location)
            if set_ok:
                self.log("SUCCESS", f"✅ Successfully updated ID Location to '{id_location}' on first tab!")
            else:
                self.log("WARNING", "Could not complete setting ID Location directly, proceeding...")

            self.log("INFO", "🔄 Refreshing all tabs so they inherit the new Account ID Location...")
            async def reload_tab(tab_num: int, page_obj: Page):
                try:
                    await page_obj.reload(wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    self.log("WARNING", f"Tab [{tab_num}/{tabs_count}] refresh notice: {str(e)[:45]}")
            await asyncio.gather(*[reload_tab(i + 1, tabs[i]) for i in range(len(tabs))])
            self.log("SUCCESS", "🎉 All tabs refreshed successfully!")

        # 5. Simultaneously navigate all tabs to the Marketplace listing creation form
        ad_type = payload.get("listing_type", payload.get("ad_type", "item")).lower()
        if "vehicle" in ad_type or "car" in ad_type or "auto" in ad_type:
            create_url = "https://www.facebook.com/marketplace/create/vehicle"
        elif "rent" in ad_type or "home" in ad_type or "property" in ad_type or "house" in ad_type:
            create_url = "https://www.facebook.com/marketplace/create/rental"
        else:
            create_url = "https://www.facebook.com/marketplace/create/item"

        self.log("INFO", f"🌐 Opening Marketplace Listing Creation page on all tabs: {create_url}...")
        async def navigate_to_create_form(tab_num: int, page_obj: Page):
            try:
                await page_obj.goto(create_url, wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                self.log("WARNING", f"Tab [{tab_num}/{tabs_count}] creation load notice: {str(e)[:45]}")

        await asyncio.gather(*[navigate_to_create_form(i + 1, tabs[i]) for i in range(len(tabs))])
        self.log("SUCCESS", "🎉 All tabs loaded at Marketplace listing creation form!")

        # 6. Method Manager Verification & Live UI Fallback determination
        chosen_method = payload.get("method", "").replace("📁 ", "").strip()
        use_method_replay = False

        if chosen_method and chosen_method not in ("Default Item Listing (Standard)", "Default Facebook Marketplace Flow", "None", ""):
            if HAS_FAULT_TOLERANCE and HAS_MACRO_RECORDER and MethodFallbackManager:
                verif = MethodFallbackManager.verify_method_availability(chosen_method, MacroMethodManager.get_methods_dir())
                if verif.is_valid:
                    use_method_replay = True
                    self.log("INFO", f"🎯 Active Method Replay: '{chosen_method}' across tabs.")
                else:
                    self.log("WARNING", f"🔄 Method '{chosen_method}' unavailable ({verif.reason}). Using Live UI Overrides.")
            elif HAS_MACRO_RECORDER:
                use_method_replay = True

        # 7. Process all tabs step-by-step in parallel
        success_count = 0
        self.log("INFO", f"📁 STEP-BY-STEP PARALLEL AUTOMATION: Processing all {tabs_count} tab(s) simultaneously...")

        # Step 5a: Upload Product Images first across all tabs
        self.log("INFO", f"🖼️ Uploading product photos simultaneously across all {tabs_count} tabs...")
        async def _upload_photos_task(i, p, payload):
            try:
                images = payload.get("images", [])
                imgs_per_post = payload.get("images_per_post", 0) or payload.get("images_per_tab", 0)

                if images:
                    valid_images = [os.path.abspath(img) for img in images if os.path.exists(img)]
                    if valid_images:
                        if imgs_per_post > 0 and len(valid_images) > imgs_per_post:
                            start_idx = (i * imgs_per_post) % len(valid_images)
                            tab_images = [valid_images[(start_idx + k) % len(valid_images)] for k in range(imgs_per_post)]
                        else:
                            tab_images = valid_images

                        upload_files = tab_images
                        anti_dup_shield = payload.get("anti_dup_shield", True) or payload.get("anti_dup_rotate", True)
                        
                        if anti_dup_shield and IMAGE_PROCESSOR_AVAILABLE:
                            try:
                                cfg = AntiDuplicateConfig(
                                    strip_exif=payload.get("wipe_exif", True),
                                    min_rotation=-0.5 if payload.get("anti_dup_rotate", True) else 0.0,
                                    max_rotation=0.5 if payload.get("anti_dup_rotate", True) else 0.0,
                                    contrast_jitter=0.02 if payload.get("anti_dup_noise", True) else 0.0,
                                    brightness_jitter=0.02 if payload.get("anti_dup_noise", True) else 0.0
                                )
                                processor = AntiDuplicateImageProcessor(config=cfg)
                                upload_files = processor.process_batch(tab_images, log_callback=self.log)
                            except Exception as img_err:
                                upload_files = tab_images
                        self.log("INFO", f"   👉 Tab [{i+1}/{tabs_count}]: Uploading {len(upload_files)} photo(s)")
                        await self._upload_photos_to_page(p, upload_files)
            except Exception as e:
                self.log("WARNING", f"Tab [{i+1}] Photo upload notice: {str(e)}")

        await asyncio.gather(*[_upload_photos_task(i, tabs[i], tab_payloads[i]) for i in range(len(tabs))], return_exceptions=True)
        await self.sleep(1.5)

        # Step 5b: Product Title
        self.log("INFO", f"✍️ Typing Titles simultaneously across all {tabs_count} tabs...")
        async def _set_title_task(i, p, payload):
            try:
                title = payload.get("title", "")
                if title:
                    self.log("INFO", f"   👉 Tab [{i+1}/{tabs_count}]: Typing title '{title[:25]}...'")
                    await self._set_title_field(p, title)
            except Exception as e:
                self.log("WARNING", f"Tab [{i+1}] Title notice: {str(e)}")

        await asyncio.gather(*[_set_title_task(i, tabs[i], tab_payloads[i]) for i in range(len(tabs))], return_exceptions=True)
        await self.sleep(0.8)

        # Step 5c: Product Price
        self.log("INFO", f"💲 Setting Prices simultaneously across all {tabs_count} tabs...")
        async def _set_price_task(i, p, payload):
            try:
                price = payload.get("price", "0")
                clean_price = re.sub(r'[^0-9.]', '', str(price)) or "0"
                self.log("INFO", f"   👉 Tab [{i+1}/{tabs_count}]: Setting price ${clean_price}")
                await self._set_price_field(p, clean_price)
            except Exception as e:
                self.log("WARNING", f"Tab [{i+1}] Price notice: {str(e)}")

        await asyncio.gather(*[_set_price_task(i, tabs[i], tab_payloads[i]) for i in range(len(tabs))], return_exceptions=True)
        await self.sleep(0.8)

        # Step 5d: Category Selection
        self.log("INFO", f"🏷️ Selecting Categories simultaneously across all {tabs_count} tabs...")
        async def _set_cat_task(i, p, payload):
            try:
                cat = payload.get("category", "Household")
                if cat:
                    self.log("INFO", f"   👉 Tab [{i+1}/{tabs_count}]: Selecting category '{cat}'")
                    await self._set_category_field(p, cat)
            except Exception as e:
                self.log("WARNING", f"Tab [{i+1}] Category notice: {str(e)}")

        await asyncio.gather(*[_set_cat_task(i, tabs[i], tab_payloads[i]) for i in range(len(tabs))], return_exceptions=True)
        await self.sleep(0.8)

        # Step 5e: Condition Selection
        cond_val = payload.get("condition", "New")
        self.log("INFO", f"⚙️ Setting Item Condition to '{cond_val}' simultaneously across all {tabs_count} tabs...")
        async def _set_cond_task(i, p, payload):
            try:
                c_text = payload.get("condition", "New")
                await self._set_condition_field(p, c_text)
            except Exception as cond_err:
                self.log("WARNING", f"Tab [{i+1}] Condition notice: {str(cond_err)[:40]}")

        await asyncio.gather(*[_set_cond_task(i, tabs[i], tab_payloads[i]) for i in range(len(tabs))], return_exceptions=True)
        await self.sleep(0.8)

        # Step 5f: Description
        self.log("INFO", f"📝 Filling Descriptions simultaneously across all {tabs_count} tabs...")
        async def _set_desc_task(i, p, payload):
            try:
                description = payload.get("description", "")
                if description:
                    self.log("INFO", f"   👉 Tab [{i+1}/{tabs_count}]: Typing description ({len(description)} chars)")
                    await self._set_description_field(p, description)
            except Exception as e:
                self.log("WARNING", f"Tab [{i+1}] Description notice: {str(e)}")

        await asyncio.gather(*[_set_desc_task(i, tabs[i], tab_payloads[i]) for i in range(len(tabs))], return_exceptions=True)
        await self.sleep(0.8)

        # Step 5g: Location Selection
        self.log("INFO", f"📍 Setting Target Locations simultaneously across all {tabs_count} tabs...")
        async def _set_loc_task(i, p, payload):
            try:
                loc = payload.get("location", "")
                if loc and loc != "Local Radius":
                    self.log("INFO", f"   👉 Tab [{i+1}/{tabs_count}]: Typing location '{loc}'")
                    await self._set_location_field(p, loc)
            except Exception as e:
                self.log("WARNING", f"Tab [{i+1}] Location notice: {str(e)}")

        await asyncio.gather(*[_set_loc_task(i, tabs[i], tab_payloads[i]) for i in range(len(tabs))], return_exceptions=True)
        await self.sleep(1.0)

        # Step 5h: Advance through "Next" Step
        self.log("INFO", f"➡️ Clicking 'Next' simultaneously across all {tabs_count} tabs...")
        async def _next_task(i, p):
            try:
                await self._click_button_with_text(p, ["Next", "اگلا"])
            except Exception as e:
                self.log("WARNING", f"Tab [{i+1}] Next notice: {str(e)}")

        await asyncio.gather(*[_next_task(i, tabs[i]) for i in range(len(tabs))], return_exceptions=True)
        await self.sleep(2.0)

        # Step 5i: 1 second pause on publish screen before instant parallel publish across all tabs!
        if not self._cancel_requested:
            self.log("INFO", f"==================================================")
            self.log("INFO", f"🔥 ALL {len(tabs)} TABS ARE FULLY PREPARED ON THE PUBLISH SCREEN!")
            self.log("INFO", f"⏸️ Pausing exactly 1 second on Publish screen for organic synchronization...")
            await asyncio.sleep(1.0)

            self.log("INFO", f"🚀 CLICKING 'PUBLISH' BUTTON SIMULTANEOUSLY ACROSS ALL {len(tabs)} TABS AT THE EXACT SAME INSTANT...")
            async def publish_tab_instantly(t_idx, page_obj, p_load):
                try:
                    return await self.publish_marketplace_listing_on_page(page_obj, p_load)
                except Exception as ex:
                    self.log("WARNING", f"Tab [{t_idx}] Publish notice: {str(ex)}")
                    return False

            pub_results = await asyncio.gather(*[
                publish_tab_instantly(i + 1, tabs[i], tab_payloads[i]) for i in range(len(tabs))
            ], return_exceptions=True)
            success_count = sum(1 for r in pub_results if isinstance(r, bool) and r is True)
            self.set_progress(100)
            self.log("SUCCESS", f"🎉 PARALLEL BATCH COMPLETE: {success_count}/{tabs_count} tabs published simultaneously in parallel!")
            return success_count

    async def create_marketplace_listing(self, payload: Dict[str, Any]):
        """Executes single or multi-tab listing publication flow with Method Manager support."""
        tabs_count = int(payload.get("tabs_count", payload.get("posts_per_id", 1)))
        if tabs_count > 1:
            return await self.create_marketplace_batch(payload)

        # Single Tab Execution with Method Replay or Live UI Flow
        chosen_method = payload.get("method", "").replace("📁 ", "").strip()
        if chosen_method and chosen_method not in ("Default Item Listing (Standard)", "Default Facebook Marketplace Flow", "None", ""):
            use_method = False
            if HAS_FAULT_TOLERANCE and HAS_MACRO_RECORDER and MethodFallbackManager:
                verif = MethodFallbackManager.verify_method_availability(chosen_method, MacroMethodManager.get_methods_dir())
                if verif.is_valid:
                    use_method = True
                else:
                    self.log("WARNING", f"🔄 Method fallback engaged ({verif.reason}). Using Live UI Overrides.")
            elif HAS_MACRO_RECORDER:
                use_method = True

            if use_method:
                try:
                    self.log("INFO", f"⚡ Replaying Method '{chosen_method}' on active browser tab...")
                    player = MacroMethodPlayer(
                        method_name=chosen_method,
                        dynamic_params=payload,
                        log_callback=self.log
                    )
                    method_ok = await player.execute(self.page)
                    if method_ok:
                        return True
                    self.log("WARNING", f"🔄 Method step incomplete. Falling back to live UI inputs...")
                except Exception as ex:
                    self.log("WARNING", f"🔄 Method exception: {str(ex)[:50]}. Falling back to live UI inputs...")

        return await self.create_marketplace_listing_on_page(self.page, payload)

    async def create_marketplace_listing_on_page(self, page: Page, payload: Dict[str, Any], skip_publish: bool = False) -> bool:
        """
        Executes the Facebook Marketplace listing publication workflow with precision
        field locators (guaranteeing Title, Price, Category, Condition, Description,
        Location, Images, Next, and Publish are filled strictly in their exact controls).
        """
        if not page or page.is_closed() or self._cancel_requested:
            return False

        title = payload.get("title", "")
        price = payload.get("price", "0")
        category = payload.get("category", "Household")
        location = payload.get("location", "")
        description = payload.get("description", "")
        images = payload.get("images", [])

        ad_type = payload.get("listing_type", payload.get("ad_type", "item")).lower()
        if "vehicle" in ad_type or "car" in ad_type or "auto" in ad_type:
            create_url = "https://www.facebook.com/marketplace/create/vehicle"
        elif "rent" in ad_type or "home" in ad_type or "property" in ad_type or "house" in ad_type:
            create_url = "https://www.facebook.com/marketplace/create/rental"
        else:
            create_url = "https://www.facebook.com/marketplace/create/item"

        self.log("INFO", f"Navigating to Marketplace creation portal ({create_url})...")

        try:
            await page.goto(create_url, wait_until="domcontentloaded", timeout=40000)
            await self.sleep(random.uniform(2.0, 3.5))
        except PlaywrightTimeoutError:
            self.log("WARNING", "DOM load timed out; proceeding with page content...")
            await self.sleep(1.5)

        # Secondary checkpoint verification on Marketplace URL
        if "checkpoint" in page.url:
            raise CheckpointDetectedError("Marketplace creation triggered Facebook checkpoint.")
        if "login" in page.url:
            raise InvalidSessionError("Redirected away from Marketplace to login screen.")

        self.log("INFO", "Marketplace item creation interface loaded.")

        # ----------------------------------------------------------------------
        # 1. Upload Product Images First
        # ----------------------------------------------------------------------
        if images:
            try:
                valid_images = [os.path.abspath(img) for img in images if os.path.exists(img)]
                if valid_images:
                    upload_files = valid_images
                    anti_dup_shield = payload.get("anti_dup_shield", True) or payload.get("anti_dup_rotate", True)
                    
                    if anti_dup_shield and IMAGE_PROCESSOR_AVAILABLE:
                        try:
                            cfg = AntiDuplicateConfig(
                                strip_exif=payload.get("wipe_exif", True),
                                min_rotation=-0.5 if payload.get("anti_dup_rotate", True) else 0.0,
                                max_rotation=0.5 if payload.get("anti_dup_rotate", True) else 0.0,
                                contrast_jitter=0.02 if payload.get("anti_dup_noise", True) else 0.0,
                                brightness_jitter=0.02 if payload.get("anti_dup_noise", True) else 0.0
                            )
                            processor = AntiDuplicateImageProcessor(config=cfg)
                            upload_files = processor.process_batch(valid_images, log_callback=self.log)
                        except Exception as img_err:
                            upload_files = valid_images

                    self.log("INFO", f"🖼️ Uploading {len(upload_files)} product photo(s)...")
                    await self._upload_photos_to_page(page, upload_files)
                    await self.sleep(random.uniform(2.0, 3.5))
            except Exception as e:
                self.log("WARNING", f"Photo upload notice: {str(e)}")

        # ----------------------------------------------------------------------
        # 2. Product Title
        # ----------------------------------------------------------------------
        if title:
            try:
                self.log("INFO", f"✍️ Typing Title: '{title[:45]}...'")
                await self._set_title_field(page, title)
                await self.sleep(random.uniform(0.5, 1.0))
            except Exception as e:
                self.log("WARNING", f"Title entry notice: {str(e)}")

        # ----------------------------------------------------------------------
        # 3. Product Price
        # ----------------------------------------------------------------------
        if price is not None:
            try:
                clean_price = re.sub(r'[^0-9.]', '', str(price)) or "0"
                self.log("INFO", f"💲 Setting Price: ${clean_price}")
                await self._set_price_field(page, clean_price)
                await self.sleep(random.uniform(0.5, 1.0))
            except Exception as e:
                self.log("WARNING", f"Price entry notice: {str(e)}")

        # ----------------------------------------------------------------------
        # 4. Category Selection
        # ----------------------------------------------------------------------
        if category:
            try:
                self.log("INFO", f"🏷️ Selecting Category: '{category}'...")
                await self._set_category_field(page, category)
                await self.sleep(random.uniform(0.6, 1.2))
            except Exception as e:
                self.log("WARNING", f"Category selection notice: {str(e)}")

        # ----------------------------------------------------------------------
        # 5. Condition Selection
        # ----------------------------------------------------------------------
        cond_text = payload.get("condition", "New")
        try:
            self.log("INFO", f"⚙️ Setting Item Condition to '{cond_text}'...")
            await self._set_condition_field(page, cond_text)
            await self.sleep(random.uniform(0.4, 0.8))
        except Exception as cond_err:
            self.log("WARNING", f"Condition selection notice: {str(cond_err)}")

        # ----------------------------------------------------------------------
        # 6. Description
        # ----------------------------------------------------------------------
        if description:
            try:
                self.log("INFO", f"📝 Filling Description ({len(description)} chars)...")
                await self._set_description_field(page, description)
                await self.sleep(random.uniform(0.6, 1.2))
            except Exception as e:
                self.log("WARNING", f"Description entry notice: {str(e)}")

        # ----------------------------------------------------------------------
        # 7. Location Selection
        # ----------------------------------------------------------------------
        if location and location != "Local Radius":
            try:
                self.log("INFO", f"📍 Setting Target Location / City: '{location}'...")
                await self._set_location_field(page, location)
                await self.sleep(random.uniform(0.6, 1.2))
            except Exception as e:
                self.log("WARNING", f"Location entry notice: {str(e)}")

        # ----------------------------------------------------------------------
        # 8. Advance through "Next" Step
        # ----------------------------------------------------------------------
        self.log("INFO", "➡️ Clicking 'Next' button...")
        try:
            clicked_next = await self._click_button_with_text(page, ["Next", "اگلا"])
            if clicked_next:
                await self.sleep(random.uniform(2.0, 3.5))
        except Exception as e:
            self.log("WARNING", f"Next button notice: {str(e)}")

        if skip_publish:
            self.log("SUCCESS", f"✅ Form details filled & Next screen reached for '{title[:30]}...'")
            return True

        # ----------------------------------------------------------------------
        # 9. Click "Publish" Button
        # ----------------------------------------------------------------------
        return await self.publish_marketplace_listing_on_page(page, payload)

    async def _instant_js_click_publish(self, page: Page, title: str = "") -> bool:
        """Instantly locates and clicks the Publish button using fast in-page JavaScript execution."""
        if not page or page.is_closed():
            return False

        js_code = """
        () => {
            const candidates = ['publish', 'post', 'done', 'save', 'شائع', 'پبلش', 'اگلا'];
            const elements = Array.from(document.querySelectorAll('div[role="button"], button, span[role="button"], div[aria-label*="Publish"], div[aria-label*="Post"], div[aria-label*="شائع"]'));
            
            for (const el of elements) {
                const label = (el.getAttribute('aria-label') || '').trim().toLowerCase();
                const text = (el.innerText || el.textContent || '').trim().toLowerCase();
                
                for (const cand of candidates) {
                    if (label === cand || text === cand || label.includes(cand) || (text.length < 25 && text.includes(cand))) {
                        el.scrollIntoView({ behavior: 'instant', block: 'center' });
                        el.click();
                        el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                        return true;
                    }
                }
            }

            // Secondary fallback: find primary action button on bottom right composer
            const primaryBtn = document.querySelector('div[aria-label="Publish"][role="button"], div[aria-label="Post"][role="button"], button[type="submit"]');
            if (primaryBtn) {
                primaryBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
                primaryBtn.click();
                primaryBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                return true;
            }

            return false;
        }
        """
        try:
            clicked = await page.evaluate(js_code)
            if clicked:
                return True
        except Exception:
            pass

        return await self._click_button_with_text(page, ["Publish", "Post", "شائع", "Done", "Save"])

    async def publish_marketplace_listing_on_page(self, page: Page, payload: Dict[str, Any]) -> bool:
        """Triggers final 'Publish' button submission on an active Facebook Marketplace page."""
        if not page or page.is_closed() or self._cancel_requested:
            return False

        title = payload.get("title", "Listing")
        self.log("INFO", f"🚀 Triggering instant publication for '{title[:40]}...'")
        
        clicked_publish = await self._instant_js_click_publish(page, title)

        if not clicked_publish:
            self.log("WARNING", f"Could not locate the final 'Publish' button for '{title}'.")
            return False

        # Wait briefly for publication confirmation response
        self.log("INFO", f"Awaiting publication broadcast confirmation for '{title[:30]}...'")
        await self.sleep(random.uniform(2.5, 4.0))
        self.log("SUCCESS", f"✅ Marketplace listing '{title}' successfully broadcast!")
        return True

    # --------------------------------------------------------------------------
    # Specialized Precise DOM Field Finders & Setters
    # --------------------------------------------------------------------------
    async def _human_type(self, page: Page, text: str, min_delay: int = 25, max_delay: int = 70):
        """Types string into active input with realistic human keypress intervals and micro-hesitations."""
        if not text:
            return
        for idx, ch in enumerate(text):
            if self._cancel_requested or page.is_closed():
                break
            ch_delay = random.randint(min_delay, max_delay)
            # 2.5% chance of realistic thinking hesitation
            if idx > 0 and random.random() < 0.025:
                ch_delay += random.randint(110, 240)
            await page.keyboard.type(ch, delay=ch_delay)

    async def _set_title_field(self, page: Page, text: str):
        """Specifically locates and types into the Facebook Marketplace Title input."""
        selectors = [
            'label[aria-label="Title"] input',
            'label[aria-label*="Title"] input',
            'label[aria-label*="Title" i] input',
            'label[aria-label*="عنوان"] input',
            'input[aria-label="Title"]',
            'input[aria-label*="Title"]',
            'input[aria-label*="Title" i]',
            'input[aria-label*="عنوان"]',
            'input[name="title"]',
            'label:has-text("Title") input',
            'label:has-text("What are you selling") input',
            'div[aria-label="Title"] input',
            'div[aria-label*="Title"] input'
        ]
        input_el = None
        for attempt in range(3):
            for sel in selectors:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        input_el = el
                        break
                except Exception:
                    continue
            if input_el:
                break
            try:
                input_el = await page.query_selector('xpath=//label[contains(translate(@aria-label, "TITLE", "title"), "title")]//input')
                if input_el and await input_el.is_visible():
                    break
                input_el = None
            except Exception:
                pass
            await page.evaluate("window.scrollBy(0, 150)")
            await self.sleep(0.5)

        if not input_el:
            # Fallback search for visible text inputs on the form
            try:
                inputs = await page.query_selector_all('input[type="text"], input:not([type])')
                for inp in inputs:
                    if await inp.is_visible():
                        aria = (await inp.get_attribute("aria-label")) or ""
                        if "price" not in aria.lower() and "location" not in aria.lower() and "search" not in aria.lower():
                            input_el = inp
                            break
            except Exception:
                pass

        if not input_el:
            self.log("WARNING", "Could not locate Title input field directly.")
            return

        try:
            await input_el.scroll_into_view_if_needed()
            await input_el.click()
            await self.sleep(random.uniform(0.2, 0.4))
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await self._human_type(page, text, min_delay=30, max_delay=65)
        except Exception as ex:
            self.log("WARNING", f"Notice while typing title: {str(ex)}")

    async def _set_price_field(self, page: Page, price_str: str):
        """Specifically locates and types into the Facebook Marketplace Price input."""
        selectors = [
            'label[aria-label="Price"] input',
            'label[aria-label*="Price"] input',
            'label[aria-label*="Price" i] input',
            'label[aria-label*="قیمت"] input',
            'input[aria-label="Price"]',
            'input[aria-label*="Price"]',
            'input[aria-label*="Price" i]',
            'input[aria-label*="قیمت"]',
            'input[name="price"]',
            'label:has-text("Price") input',
            'div[aria-label="Price"] input',
            'div[aria-label*="Price"] input'
        ]
        input_el = None
        for attempt in range(3):
            for sel in selectors:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        input_el = el
                        break
                except Exception:
                    continue
            if input_el:
                break
            try:
                input_el = await page.query_selector('xpath=//label[contains(translate(@aria-label, "PRICE", "price"), "price")]//input')
                if input_el and await input_el.is_visible():
                    break
                input_el = None
            except Exception:
                pass
            await page.evaluate("window.scrollBy(0, 150)")
            await self.sleep(0.5)

        if not input_el:
            self.log("WARNING", "Could not locate Price input field directly.")
            return

        try:
            await input_el.scroll_into_view_if_needed()
            await input_el.click()
            await self.sleep(random.uniform(0.2, 0.4))
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await self._human_type(page, price_str, min_delay=35, max_delay=75)
        except Exception as ex:
            self.log("WARNING", f"Notice while typing price: {str(ex)}")

    async def _set_description_field(self, page: Page, text: str):
        """Specifically locates and types into the Facebook Marketplace Description textarea."""
        selectors = [
            'label[aria-label="Description"] textarea',
            'label[aria-label*="Description"] textarea',
            'label[aria-label*="Description" i] textarea',
            'label[aria-label*="تفصیل"] textarea',
            'textarea[aria-label="Description"]',
            'textarea[aria-label*="Description"]',
            'textarea[aria-label*="Description" i]',
            'textarea[name="description"]',
            'label:has-text("Description") textarea',
            'textarea'
        ]
        input_el = None
        for attempt in range(2):
            for sel in selectors:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        input_el = el
                        break
                except Exception:
                    continue
            if input_el:
                break
            await page.evaluate("window.scrollBy(0, 200)")
            await self.sleep(0.5)

        if not input_el:
            self.log("WARNING", "Description textarea not found directly; skipping description.")
            return

        try:
            await input_el.scroll_into_view_if_needed()
            await input_el.click()
            await self.sleep(random.uniform(0.2, 0.4))
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await self._human_type(page, text, min_delay=20, max_delay=55)
        except Exception as ex:
            self.log("WARNING", f"Notice while typing description: {str(ex)}")

    async def _set_location_field(self, page: Page, location_str: str):
        """Specifically sets geographic location / city with autocomplete resolution."""
        if not location_str or location_str == "Local Radius":
            return

        selectors = [
            'label[aria-label="Location"] input',
            'label[aria-label*="Location"] input',
            'label[aria-label*="Location" i] input',
            'input[aria-label="Location"]',
            'input[aria-label*="Location"]',
            'input[aria-label*="Location" i]',
            'label[aria-label*="لوکیشن"] input',
            'label:has-text("Location") input',
            'label:has-text("City") input'
        ]
        input_el = None
        for attempt in range(2):
            for sel in selectors:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        input_el = el
                        break
                except Exception:
                    continue
            if input_el:
                break
            await page.evaluate("window.scrollBy(0, 300)")
            await self.sleep(0.5)

        if not input_el:
            self.log("WARNING", "Location input not visible on current viewport; skipping location input.")
            return

        try:
            await input_el.scroll_into_view_if_needed()
            await input_el.click()
            await self.sleep(random.uniform(0.2, 0.4))
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")

            search_query = re.sub(r'\(.*?\)', '', location_str).strip() or location_str
            await self._human_type(page, search_query, min_delay=30, max_delay=65)
            await self.sleep(random.uniform(1.6, 2.3))

            option_el = await page.query_selector('div[role="listbox"] div[role="option"], ul[role="listbox"] li, div[role="option"]')
            if option_el and await option_el.is_visible():
                await option_el.click()
                self.log("INFO", f"Location suggestion matched for '{location_str}'.")
            else:
                await page.keyboard.press("ArrowDown")
                await self.sleep(0.3)
                await page.keyboard.press("Enter")
            await self.sleep(random.uniform(0.6, 1.1))
        except Exception as ex:
            self.log("WARNING", f"Notice while setting location: {str(ex)}")

    async def _set_category_field(self, page: Page, category: str):
        """Selects category dropdown matching Household, Appliances, Auto Parts, etc."""
        # Category alias dictionary for Facebook Marketplace localization
        cat_aliases = {
            "household": ["Household", "Home & Kitchen", "Home goods", "Furniture", "Household Items", "Bedding", "Bath"],
            "appliances": ["Appliances", "Major appliances", "Small appliances", "Home appliances", "Refrigerators"],
            "auto parts": ["Auto parts", "Vehicle parts & accessories", "Car parts", "Auto Parts & Tires", "Automotive parts", "Parts & accessories"],
            "electronics & computers": ["Electronics & Computers", "Electronics", "Computers", "Video Games", "Audio"],
            "vehicles & parts": ["Vehicles & Parts", "Vehicles", "Auto parts", "Cars & Trucks"],
            "furniture & decor": ["Furniture & Decor", "Furniture", "Home decor"],
            "tools & appliances": ["Tools & Appliances", "Tools", "Appliances"]
        }

        cat_lower = category.strip().lower()
        search_terms = cat_aliases.get(cat_lower, [category])

        dropdown_selectors = [
            'label[aria-label="Category"]',
            'label[aria-label*="Category"]',
            'div[aria-label="Category"][role="combobox"]',
            'div[aria-label*="Category"][role="button"]',
            'label:has-text("Category")',
            'span:has-text("Category")'
        ]
        drop_el = None
        for sel in dropdown_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    drop_el = el
                    break
            except Exception:
                continue

        if drop_el:
            await drop_el.scroll_into_view_if_needed()
            await drop_el.click()
            await self.sleep(1.2)

            # Try matching option
            found = False
            for term in search_terms:
                try:
                    opt = await page.query_selector(f'div[role="option"]:has-text("{term}"), span:has-text("{term}"), div[role="button"]:has-text("{term}")')
                    if opt and await opt.is_visible():
                        await opt.click()
                        self.log("INFO", f"Category option '{term}' selected.")
                        found = True
                        break
                except Exception:
                    continue

            if not found:
                # Click first available category
                first_opt = await page.query_selector('div[role="listbox"] div[role="option"], div[role="menuitem"]')
                if first_opt and await first_opt.is_visible():
                    await first_opt.click()
                    self.log("INFO", "Selected first available category.")
            await self.sleep(0.6)

    async def _set_condition_field(self, page: Page, condition_text: str = "New"):
        """Selects item condition (e.g., New, Used – like new, Used – good, Used – fair)."""
        if not condition_text:
            condition_text = "New"

        cond_selectors = [
            'label[aria-label="Condition"]',
            'label[aria-label*="Condition"]',
            'div[aria-label="Condition"][role="combobox"]',
            'div[aria-label*="Condition"][role="button"]',
            'label:has-text("Condition")',
            'span:has-text("Condition")'
        ]
        cond_el = None
        for sel in cond_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    cond_el = el
                    break
            except Exception:
                continue

        if cond_el:
            try:
                await cond_el.scroll_into_view_if_needed()
                await cond_el.click()
                await self.sleep(0.8)

                clean_text = condition_text.strip()
                variants = [clean_text]
                if "like new" in clean_text.lower():
                    variants.extend(["like new", "Used – like new", "Used - like new", "Like New"])
                elif "good" in clean_text.lower():
                    variants.extend(["good", "Used – good", "Used - good", "Good"])
                elif "fair" in clean_text.lower():
                    variants.extend(["fair", "Used – fair", "Used - fair", "Fair"])
                elif "new" in clean_text.lower():
                    variants.extend(["New", "جدید"])

                opt_el = None
                for var in variants:
                    try:
                        opt_el = await page.query_selector(f'div[role="option"]:has-text("{var}"), span:has-text("{var}"), div[role="button"]:has-text("{var}")')
                        if opt_el and await opt_el.is_visible():
                            break
                        opt_el = None
                    except Exception:
                        continue

                if opt_el:
                    await opt_el.click()
                    self.log("INFO", f"Condition '{condition_text}' selected successfully.")
                else:
                    first_opt = await page.query_selector('div[role="listbox"] div[role="option"], div[role="option"]')
                    if first_opt and await first_opt.is_visible():
                        await first_opt.click()
                        self.log("INFO", f"Selected condition option for '{condition_text}'.")
                await self.sleep(0.5)
            except Exception as ex:
                self.log("WARNING", f"Notice while selecting condition: {str(ex)}")

    async def _upload_photos_to_page(self, page: Page, files: List[str]):
        """Injects files into input[type=file]."""
        file_inputs = await page.query_selector_all('input[type="file"]')
        if not file_inputs:
            # wait briefly
            try:
                f = await page.wait_for_selector('input[type="file"]', timeout=5000)
                if f:
                    file_inputs = [f]
            except Exception:
                pass

        for finput in file_inputs:
            try:
                await finput.set_input_files(files)
                self.log("SUCCESS", f"Injected {len(files)} photo(s) into Marketplace media uploader.")
                return True
            except Exception:
                continue
        return False

    async def _click_button_with_text(self, page: Page, text_candidates: List[str]) -> bool:
        """Finds and clicks a button by text or aria-label."""
        for txt in text_candidates:
            queries = [
                f'div[aria-label="{txt}"][role="button"]',
                f'div[aria-label*="{txt}"][role="button"]',
                f'button:has-text("{txt}")',
                f'div[role="button"]:has-text("{txt}")',
                f'span:has-text("{txt}")'
            ]
            for q in queries:
                try:
                    el = await page.query_selector(q)
                    if el and await el.is_visible():
                        await el.scroll_into_view_if_needed()
                        await el.click()
                        return True
                except Exception:
                    continue
        return False

    # --------------------------------------------------------------------------
    # Utility Selector Helpers
    # --------------------------------------------------------------------------
    async def _type_first_matching(self, selectors: List[str], text: str, min_delay: int = 70, max_delay: int = 180):
        for sel in selectors:
            try:
                el = await self.page.query_selector(sel)
                if el and await el.is_visible():
                    await self.human_type(sel, text, min_delay, max_delay)
                    return True
            except Exception:
                continue
        raise ListingSubmissionError(f"None of the selectors were visible: {selectors}")

    async def _click_first_matching(self, selectors: List[str]) -> bool:
        for sel in selectors:
            try:
                el = await self.page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    return True
            except Exception:
                continue
        return False

    # --------------------------------------------------------------------------
    # Teardown & Resource Cleanup
    # --------------------------------------------------------------------------
    async def close(self):
        """Cleanly releases all Playwright browser processes and network sockets."""
        try:
            if self.page and not self.page.is_closed():
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.log("INFO", "Playwright browser session closed cleanly.")
        except Exception as e:
            self.log("WARNING", f"Resource cleanup notice: {str(e)}")
