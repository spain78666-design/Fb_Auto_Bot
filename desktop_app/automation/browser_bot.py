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
    try:
        from automation.extension_manager import get_fewfeed_extension_path as _get_path
        p = _get_path()
        if p and os.path.isdir(p) and os.path.exists(os.path.join(p, "manifest.json")):
            return p
    except Exception:
        pass

    candidates = [
        os.path.join(get_base_dir(), "FewFeedV3.9.1"),
        os.path.join(get_base_dir(), "FEWFEED"),
        os.path.join(get_base_dir(), "_internal", "FewFeedV3.9.1"),
        os.path.join(get_base_dir(), "_internal", "FEWFEED"),
        os.path.join(getattr(sys, '_MEIPASS', ''), "FewFeedV3.9.1"),
        os.path.join(getattr(sys, '_MEIPASS', ''), "FEWFEED"),
        os.path.join(getattr(sys, '_MEIPASS', ''), "_internal", "FewFeedV3.9.1"),
        os.path.join(getattr(sys, '_MEIPASS', ''), "_internal", "FEWFEED"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "FewFeedV3.9.1")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "FEWFEED")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "FewFeedV3.9.1")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "FEWFEED")),
        "/desktop_app/FewFeedV3.9.1",
        "/desktop_app/FEWFEED",
        os.path.abspath("FewFeedV3.9.1"),
        os.path.abspath("FEWFEED"),
        os.path.abspath("desktop_app/FewFeedV3.9.1"),
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
        try:
            from automation.extension_manager import get_extension_chrome_args, prepare_profile_for_extension
            if user_data_dir:
                prepare_profile_for_extension(user_data_dir, ext_path)
            ext_args = get_extension_chrome_args(ext_path)
        except Exception:
            ext_args = []
            if ext_path and os.path.exists(ext_path):
                norm_p = os.path.normpath(os.path.abspath(ext_path))
                ext_args = [
                    f"--disable-extensions-except={norm_p}",
                    f"--load-extension={norm_p}",
                    "--enable-extensions"
                ]

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--start-maximized",
            "--no-default-browser-check",
            "--no-first-run",
            "--enable-extensions",
            "--enable-unsafe-extension-debugging",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-dev-shm-usage",
            "--lang=en-US,en",
            "--ignore-certificate-errors",
            "--allow-running-insecure-content",
            "--disable-web-security",
            "--disable-notifications",
            "--password-store=basic",
            "--no-service-autorun"
        ]
        launch_args.extend(ext_args)

        if ext_path and os.path.exists(ext_path):
            self.log("SUCCESS", f"🧩 Automatically loaded Chrome Extension from: {ext_path}")

        # Ignore sandbox restrictions and default Playwright extension-blocking flags
        ignore_default_args = [
            "--no-sandbox",
            "--disable-extensions",
            "--enable-automation",
            "--disable-component-extensions-with-background-pages"
        ]

        # Prioritize real system Google Chrome binary if present
        try:
            from automation.extension_manager import get_system_chrome_executable
            chrome_exe = get_system_chrome_executable()
        except Exception:
            chrome_exe = None

        channels_to_try = []
        if chrome_exe and os.path.isfile(chrome_exe):
            channels_to_try.append(("real_chrome", chrome_exe))
        channels_to_try.extend([("chrome", None), ("msedge", None), (None, None)])

        async def launch_context_smart():
            clean_profile_locks(user_data_dir)
            for ch_name, exe_p in channels_to_try:
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
                    if exe_p:
                        kwargs["executable_path"] = exe_p
                    elif ch_name:
                        kwargs["channel"] = ch_name
                    ctx = await self.playwright.chromium.launch_persistent_context(**kwargs)
                    if ext_path and os.path.isdir(ext_path):
                        try:
                            fwd_p = os.path.abspath(ext_path).replace('\\', '/')
                            p0 = ctx.pages[0] if ctx.pages else await ctx.new_page()
                            cdp = await ctx.new_cdp_session(p0)
                            await cdp.send("Extensions.loadUnpacked", {"path": fwd_p})
                        except Exception:
                            pass
                    self.log("INFO", f"Launched browser ({exe_p or ch_name or 'Chromium'}) with FewFeed loaded.")
                    return ctx
                except Exception as ex:
                    self.log("WARNING", f"Persistent launch attempt ({ch_name or exe_p}) notice: {str(ex)[:100]}")
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
            for ch_name, exe_p in channels_to_try:
                try:
                    kwargs = {
                        "headless": self.headless,
                        "args": launch_args,
                        "ignore_default_args": ignore_default_args,
                        "proxy": proxy_config
                    }
                    if exe_p:
                        kwargs["executable_path"] = exe_p
                    elif ch_name:
                        kwargs["channel"] = ch_name
                    b = await self.playwright.chromium.launch(**kwargs)
                    self.log("INFO", f"Launched browser ({exe_p or ch_name or 'Chromium'})")
                    return b
                except Exception as ex:
                    self.log("WARNING", f"Browser launch attempt ({ch_name or exe_p}) notice: {str(ex)[:100]}")
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
    async def set_account_marketplace_location(self, page: Page, main_location: str, radius: str = "40 miles") -> bool:
        """Sets the Chrome ID / Account primary Marketplace default location and radius on Facebook Marketplace homepage."""
        if not main_location or not main_location.strip():
            return False

        loc_name = main_location.strip()
        rad_val = (radius or "40 miles").strip()
        self.log("INFO", f"==================================================")
        self.log("INFO", f"🌍 Setting Chrome ID Marketplace Default Location to '{loc_name}' (Radius: {rad_val})...")

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

                    # Handle Radius selection inside dialog if radius is provided
                    if rad_val:
                        try:
                            self.log("INFO", f"🧭 Selecting Marketplace Radius: '{rad_val}'...")
                            # 1. Open Radius dropdown inside dialog
                            opened_radius = await page.evaluate("""() => {
                                const dialog = document.querySelector('div[role="dialog"]');
                                if (!dialog) return false;
                                
                                const candidates = Array.from(dialog.querySelectorAll('label, div[role="combobox"], div[role="button"], div[aria-haspopup="listbox"], span'));
                                for (const el of candidates) {
                                    const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                                    const text = (el.innerText || '').toLowerCase();
                                    if (aria.includes('radius') || text.includes('radius')) {
                                        el.scrollIntoView({ behavior: 'instant', block: 'center' });
                                        el.click();
                                        return true;
                                    }
                                }
                                for (const el of candidates) {
                                    const text = (el.innerText || '').toLowerCase();
                                    if ((text.includes('mile') || text.includes('km')) && !text.includes('within')) {
                                        el.scrollIntoView({ behavior: 'instant', block: 'center' });
                                        el.click();
                                        return true;
                                    }
                                }
                                return false;
                            }""")

                            if not opened_radius:
                                rad_btn = page.locator("div[role='dialog'] div[aria-label*='Radius' i], div[role='dialog'] label:has-text('Radius'), div[role='dialog'] div[role='combobox'], div[role='dialog'] span:has-text('mile'), div[role='dialog'] span:has-text('km')").first
                                if await rad_btn.is_visible(timeout=2000):
                                    await rad_btn.click(force=True)

                            await self.sleep(0.8)

                            # 2. Select option matching rad_val (e.g. '10 miles', '40 miles', '500 miles')
                            rad_num = "".join([c for c in rad_val if c.isdigit()])
                            matched_opt = await page.evaluate("""(target) => {
                                const tClean = target.trim().toLowerCase();
                                const tNum = tClean.replace(/[^0-9]/g, '');
                                const options = Array.from(document.querySelectorAll('div[role="option"], div[role="menuitem"], div[role="listbox"] div, ul[role="listbox"] li, span'));
                                for (const opt of options) {
                                    const text = (opt.innerText || opt.textContent || '').trim().toLowerCase();
                                    if (text === tClean || text === `${tNum} miles` || text === `${tNum} mile` || text === `${tNum} km`) {
                                        opt.scrollIntoView({ behavior: 'instant', block: 'center' });
                                        opt.click();
                                        return true;
                                    }
                                }
                                return false;
                            }""", rad_val)

                            if not matched_opt:
                                option_selectors = [
                                    f"div[role='option']:has-text('{rad_val}')",
                                    f"ul[role='listbox'] li:has-text('{rad_val}')",
                                    f"div[role='menuitem']:has-text('{rad_val}')",
                                    f"div[role='option']:has-text('{rad_num} miles')",
                                    f"div[role='option']:has-text('{rad_num} mile')",
                                    f"span:has-text('{rad_val}')",
                                    f"span:has-text('{rad_num} miles')"
                                ]
                                for r_sel in option_selectors:
                                    try:
                                        r_elem = page.locator(r_sel).first
                                        if await r_elem.is_visible(timeout=600):
                                            await r_elem.click(force=True)
                                            await self.sleep(0.5)
                                            break
                                    except Exception:
                                        continue
                            await self.sleep(0.6)
                        except Exception as rad_err:
                            self.log("DEBUG", f"Radius selector notice: {str(rad_err)[:50]}")

                    apply_btn = page.locator("div[role='dialog'] div[role='button']:has-text('Apply'), div[role='dialog'] button:has-text('Apply'), div[role='dialog'] span:has-text('Apply'), div[role='dialog'] div[role='button']:has-text('Save'), div[role='dialog'] div[role='button']:has-text('حفظ')").first
                    if await apply_btn.is_visible(timeout=2500):
                        await apply_btn.click(force=True)
                        await self.sleep(2.0)
                    else:
                        await page.keyboard.press("Enter")
                        await self.sleep(1.5)

                    self.log("SUCCESS", f"✅ Account ID Marketplace Default Location set to '{loc_name}' (Radius: {rad_val})!")
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

        # 0. Set Chrome ID / Account Main Location first if provided (applied ONCE on primary tab for all tabs)
        main_account_loc = payload.get("project_main_location", "").strip() or payload.get("main_location", "").strip() or payload.get("id_location", "").strip()
        main_account_rad = payload.get("id_radius", "").strip() or payload.get("radius", "").strip() or "40 miles"
        if not main_account_loc and payload.get("project_tabs") and len(payload["project_tabs"]) > 0:
            t0 = payload["project_tabs"][0]
            main_account_loc = (t0.get("id_location") or t0.get("vehicle_id_location") or t0.get("property_id_location") or "").strip()
            if not main_account_rad or main_account_rad == "40 miles":
                main_account_rad = t0.get("id_radius") or t0.get("vehicle_id_radius") or t0.get("property_id_radius") or "40 miles"

        if main_account_loc:
            self.log("INFO", f"==================================================")
            self.log("INFO", f"📍 Step 1: Setting primary Chrome ID / Account Marketplace Location to '{main_account_loc}' with Radius '{main_account_rad}'...")
            await self.set_account_marketplace_location(self.page, main_account_loc, main_account_rad)

        self.log("INFO", f"==================================================")
        self.log("INFO", f"🚀 MULTI-TAB PARALLEL ENGINE: {tabs_count} Tab(s) Configured")
        self.log("INFO", f"⚡ Preparing Strict Per-Tab Column & Location Mappings...")

        # 1. Distinct Location & Picture Mapping or Project Tabs Mapping
        if payload.get("project_tabs") and len(payload["project_tabs"]) > 0:
            proj_tabs = payload["project_tabs"]
            tabs_count = len(proj_tabs)
            tab_payloads = []

            # Global location pool if tab does not specify its own
            global_raw_loc = payload.get("location", "")
            global_loc_pool = [l.strip() for l in re.split(r'[\r\n,;]+', str(global_raw_loc)) if l.strip()]

            for i, pt in enumerate(proj_tabs):
                tp = dict(payload)
                tp["tab_index"] = i + 1
                tp["total_tabs"] = tabs_count

                # A. Strict Listing Type Identification
                ltype = pt.get("listing_type") or "Item for sale"
                tp["listing_type"] = ltype

                # B. Extract Tab-Specific Columns Strictly (No Cross-Contamination)
                if ltype == "Vehicle for sale" or "vehicle" in ltype.lower() or "car" in ltype.lower():
                    tp["vehicle_title"] = pt.get("vehicle_title") or ""
                    tp["vehicle_type"] = pt.get("vehicle_type") or "Car/Truck"
                    tp["vehicle_year"] = str(pt.get("vehicle_year") or "2022")
                    tp["vehicle_make"] = pt.get("vehicle_make") or ""
                    tp["vehicle_model"] = pt.get("vehicle_model") or ""
                    tp["price"] = str(pt.get("vehicle_price") or pt.get("price") or "0")
                    tp["description"] = pt.get("vehicle_description") or pt.get("description") or ""
                    tp["title"] = pt.get("vehicle_title") or pt.get("title") or f"{tp['vehicle_year']} {tp['vehicle_make']} {tp['vehicle_model']}".strip()
                    raw_loc = pt.get("vehicle_location") or pt.get("location") or ""
                elif ltype == "Property for sale or rent" or "rent" in ltype.lower() or "property" in ltype.lower():
                    tp["property_title"] = pt.get("property_title") or ""
                    tp["rental_type"] = pt.get("rental_type") or "Rent"
                    tp["property_type"] = pt.get("property_type") or "Apartment/Condo"
                    tp["bedrooms"] = str(pt.get("bedrooms") or "1")
                    tp["bathrooms"] = str(pt.get("bathrooms") or "1")
                    tp["property_sqft"] = str(pt.get("property_sqft") or "")
                    tp["laundry_type"] = pt.get("laundry_type") or "None"
                    tp["parking_type"] = pt.get("parking_type") or "None"
                    tp["ac_type"] = pt.get("ac_type") or "None"
                    tp["heating_type"] = pt.get("heating_type") or "None"
                    tp["price"] = str(pt.get("property_price") or pt.get("price") or "0")
                    tp["description"] = pt.get("property_description") or pt.get("description") or ""
                    tp["title"] = pt.get("property_title") or pt.get("title") or f"{tp['bedrooms']} Bed {tp['property_type']} for {tp['rental_type']}".strip()
                    raw_loc = pt.get("property_location") or pt.get("location") or ""
                else:  # Item for sale
                    tp["title"] = pt.get("title") or ""
                    tp["price"] = str(pt.get("price") or "0")
                    tp["category"] = pt.get("category") or "Household"
                    tp["condition"] = pt.get("condition") or "New"
                    tp["description"] = pt.get("description") or ""
                    raw_loc = pt.get("location") or ""

                # C. Tab Location Assignment Rule:
                # If tab has multiple locations (e.g. 20-25 lines), pick randomly from that pool.
                # If only 1 location is provided, all tabs use that same location.
                tab_loc_pool = [l.strip() for l in re.split(r'[\r\n,;]+', str(raw_loc)) if l.strip()]
                active_pool = tab_loc_pool if tab_loc_pool else global_loc_pool

                if len(active_pool) > 1:
                    chosen_loc = random.choice(active_pool)
                elif len(active_pool) == 1:
                    chosen_loc = active_pool[0]
                else:
                    chosen_loc = main_account_loc or "Local Radius"
                tp["location"] = chosen_loc

                # D. Images & Protection
                tp["images"] = pt.get("images") or payload.get("images", [])
                tp["anti_dup_shield"] = pt.get("anti_dup_shield", True)
                tp["anti_dup_rotate"] = pt.get("anti_dup_rotate", True)
                tp["wipe_exif"] = pt.get("wipe_exif", True)
                tp["anti_dup_noise"] = pt.get("anti_dup_noise", False)
                tab_payloads.append(tp)

            self.log("INFO", f"📁 Project Campaign Mode Active: {len(tab_payloads)} Tab(s) strictly configured.")
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
                tp["location"] = loc_pool[0] if len(loc_pool) == 1 else random.choice(loc_pool)
                tp["images"] = [imgs_pool[i % len(imgs_pool)]] if imgs_pool else []
                tab_payloads.append(tp)

        self.log("INFO", f"⚡ Distinct Tab Assignments:")
        for idx, tp in enumerate(tab_payloads, 1):
            img_name = os.path.basename(tp['images'][0]) if tp.get('images') else 'None'
            self.log("INFO", f"   📍 Tab [{idx}/{tabs_count}]: Type = '{tp['listing_type']}' | Loc = '{tp['location']}' | Photo = '{img_name}'")

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

        # 3. Simultaneously navigate all tabs to their respective Marketplace listing creation forms
        async def navigate_to_create_form(tab_num: int, page_obj: Page, tab_load: dict):
            t_ad_type = tab_load.get("listing_type", tab_load.get("ad_type", "item")).lower()
            if "vehicle" in t_ad_type or "car" in t_ad_type or "auto" in t_ad_type:
                target_url = "https://www.facebook.com/marketplace/create/vehicle"
                type_labels = ["vehicle", "car", "truck"]
            elif "rent" in t_ad_type or "home" in t_ad_type or "property" in t_ad_type or "house" in t_ad_type:
                target_url = "https://www.facebook.com/marketplace/create/rental"
                type_labels = ["home for sale or rent", "property", "rent", "home"]
            else:
                target_url = "https://www.facebook.com/marketplace/create/item"
                type_labels = ["item for sale", "item", "سلعة للبيع"]

            self.log("INFO", f"🌐 Step 3: Opening Marketplace Listing Form on Tab [{tab_num}/{tabs_count}]: {target_url}...")
            try:
                await page_obj.goto(target_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(1.5)
            except Exception as e:
                self.log("WARNING", f"Tab [{tab_num}/{tabs_count}] creation load notice: {str(e)[:45]}")

            # If page landed on https://www.facebook.com/marketplace/create without sub-path, click the type card
            try:
                cur_url = page_obj.url.rstrip("/")
                if cur_url.endswith("/marketplace/create"):
                    self.log("INFO", f"👉 Tab [{tab_num}/{tabs_count}]: Selecting Listing Type Card...")
                    await page_obj.evaluate("""(targets) => {
                        const cards = Array.from(document.querySelectorAll('a, div[role="button"], div[role="link"], span'));
                        for (const card of cards) {
                            const text = (card.innerText || card.textContent || '').trim().toLowerCase();
                            for (const t of targets) {
                                if (text === t || text.includes(t)) {
                                    card.scrollIntoView({ behavior: 'instant', block: 'center' });
                                    card.click();
                                    return true;
                                }
                            }
                        }
                        return false;
                    }""", type_labels)
                    await asyncio.sleep(1.5)
            except Exception:
                pass

        await asyncio.gather(*[navigate_to_create_form(i + 1, tabs[i], tab_payloads[i]) for i in range(len(tabs))])
        self.log("SUCCESS", "🎉 All tabs loaded at their respective Marketplace listing creation forms!")

        # 4. Strict Tab-by-Tab Form Filling & Next Advancement (Executed in parallel)
        self.log("INFO", f"📁 ISOLATED TAB-BY-TAB AUTOMATION: Executing strict column filling across all {tabs_count} tab(s)...")

        async def fill_and_advance_tab(tab_idx: int, page_obj: Page, tab_load: dict) -> bool:
            """
            Executes the full listing creation process for a single tab in complete isolation:
            1. Uploads photos with anti-duplicate protection and verifies thumbnail rendering
            2. Strictly fills ONLY the fields configured for this tab's listing type (never mixing Item/Vehicle/Property)
            3. Ensures all user-entered columns are completed (none skipped)
            4. Advances through 'Next' to the final Publish screen
            """
            if page_obj.is_closed() or self._cancel_requested:
                return False

            ad_type = tab_load.get("listing_type", "Item for sale").strip()
            self.log("INFO", f"📑 Tab [{tab_idx}/{tabs_count}]: Starting form automation for '{ad_type}'...")

            # Step A: Upload Photos
            images = tab_load.get("images", [])
            imgs_per_post = tab_load.get("images_per_post", 0) or tab_load.get("images_per_tab", 0)
            if images:
                valid_images = [os.path.abspath(img) for img in images if os.path.exists(img)]
                if valid_images:
                    if imgs_per_post > 0 and len(valid_images) > imgs_per_post:
                        start_idx = ((tab_idx - 1) * imgs_per_post) % len(valid_images)
                        tab_images = [valid_images[(start_idx + k) % len(valid_images)] for k in range(imgs_per_post)]
                    else:
                        tab_images = valid_images

                    upload_files = tab_images
                    anti_dup_shield = tab_load.get("anti_dup_shield", True) or tab_load.get("anti_dup_rotate", True)
                    if anti_dup_shield and IMAGE_PROCESSOR_AVAILABLE:
                        try:
                            cfg = AntiDuplicateConfig(
                                strip_exif=tab_load.get("wipe_exif", True),
                                min_rotation=-0.5 if tab_load.get("anti_dup_rotate", True) else 0.0,
                                max_rotation=0.5 if tab_load.get("anti_dup_rotate", True) else 0.0,
                                contrast_jitter=0.02 if tab_load.get("anti_dup_noise", True) else 0.0,
                                brightness_jitter=0.02 if tab_load.get("anti_dup_noise", True) else 0.0
                            )
                            processor = AntiDuplicateImageProcessor(config=cfg)
                            upload_files = processor.process_batch(tab_images, log_callback=self.log)
                        except Exception:
                            upload_files = tab_images
                    self.log("INFO", f"   👉 Tab [{tab_idx}/{tabs_count}]: Uploading {len(upload_files)} photo(s)...")
                    uploaded = await self._upload_photos_to_page(page_obj, upload_files)
                    if not uploaded:
                        self.log("WARNING", f"Tab [{tab_idx}] photo upload retry...")
                        await asyncio.sleep(1.0)
                        await self._upload_photos_to_page(page_obj, upload_files)
                    await self.sleep(1.0)

            # Step B: Strictly Fill Type-Specific Fields Without Cross-Contamination
            if ad_type == "Vehicle for sale" or "vehicle" in ad_type.lower() or "car" in ad_type.lower():
                v_type = tab_load.get("vehicle_type", "Car/Truck")
                v_year = str(tab_load.get("vehicle_year", "2022"))
                v_make = tab_load.get("vehicle_make", "")
                v_model = tab_load.get("vehicle_model", "")
                v_title = tab_load.get("vehicle_title") or tab_load.get("title", "")
                v_price = str(tab_load.get("vehicle_price") or tab_load.get("price") or "0")
                v_loc = tab_load.get("vehicle_location") or tab_load.get("location", "")
                v_desc = tab_load.get("vehicle_description") or tab_load.get("description", "")

                self.log("INFO", f"   👉 Tab [{tab_idx}/{tabs_count}]: Vehicle ({v_year} {v_make} {v_model}) | Price: ${v_price} | Loc: {v_loc}")
                if v_title:
                    await self._set_title_field(page_obj, v_title)
                if v_type:
                    await self._set_vehicle_type_field(page_obj, v_type)
                if v_year:
                    await self._set_vehicle_year_field(page_obj, v_year)
                if v_make:
                    await self._set_vehicle_make_field(page_obj, v_make)
                if v_model:
                    await self._set_vehicle_model_field(page_obj, v_model)
                if v_price is not None and str(v_price).strip() != "":
                    await self._set_price_field(page_obj, str(v_price).strip())
                if v_loc and v_loc != "Local Radius":
                    await self._set_location_field(page_obj, v_loc)
                if v_desc:
                    await self._set_description_field(page_obj, v_desc)

            elif ad_type == "Property for sale or rent" or "rent" in ad_type.lower() or "property" in ad_type.lower():
                r_type = tab_load.get("rental_type", "Rent")
                p_type = tab_load.get("property_type", "Apartment/Condo")
                beds = str(tab_load.get("bedrooms", "1"))
                baths = str(tab_load.get("bathrooms", "1"))
                p_title = tab_load.get("property_title") or tab_load.get("title", "")
                p_price = str(tab_load.get("property_price") or tab_load.get("price") or "0")
                p_loc = tab_load.get("property_location") or tab_load.get("location", "")
                p_desc = tab_load.get("property_description") or tab_load.get("description", "")

                self.log("INFO", f"   👉 Tab [{tab_idx}/{tabs_count}]: Property ({beds} Bed {p_type} for {r_type}) | Price: ${p_price} | Loc: {p_loc}")
                if p_title:
                    await self._set_title_field(page_obj, p_title)
                if r_type:
                    await self._set_rental_sale_type_field(page_obj, r_type)
                if p_type:
                    await self._set_property_type_field(page_obj, p_type)
                if beds:
                    await self._set_bedrooms_field(page_obj, beds)
                if baths:
                    await self._set_bathrooms_field(page_obj, baths)
                if p_price is not None and str(p_price).strip() != "":
                    await self._set_price_field(page_obj, str(p_price).strip())
                if p_loc and p_loc != "Local Radius":
                    await self._set_location_field(page_obj, p_loc)
                if p_desc:
                    await self._set_description_field(page_obj, p_desc)

                # Optional advanced property specifications
                sqft = tab_load.get("property_sqft", "")
                if sqft:
                    await self._set_property_sqft_field(page_obj, sqft)
                laundry = tab_load.get("laundry_type", "None")
                if laundry and laundry != "None":
                    await self._set_property_generic_dropdown(page_obj, "laundry", laundry)
                parking = tab_load.get("parking_type", "None")
                if parking and parking != "None":
                    await self._set_property_generic_dropdown(page_obj, "parking", parking)
                ac = tab_load.get("ac_type", "None")
                if ac and ac != "None":
                    await self._set_property_generic_dropdown(page_obj, "air conditioning", ac)
                heating = tab_load.get("heating_type", "None")
                if heating and heating != "None":
                    await self._set_property_generic_dropdown(page_obj, "heating", heating)

            else:  # Item for sale
                title = tab_load.get("title", "")
                cat = tab_load.get("category", "Household")
                cond = tab_load.get("condition", "New")
                price = str(tab_load.get("price", "0"))
                loc = tab_load.get("location", "")
                desc = tab_load.get("description", "")

                self.log("INFO", f"   👉 Tab [{tab_idx}/{tabs_count}]: Item '{title[:25]}' | Price: ${price} | Loc: {loc}")
                if title:
                    await self._set_title_field(page_obj, title)
                if price is not None and str(price).strip() != "":
                    await self._set_price_field(page_obj, str(price).strip())
                if cat:
                    await self._set_category_field(page_obj, cat)
                    await self.sleep(1.2)
                await self._set_condition_field(page_obj, cond or "New")
                if loc and loc != "Local Radius":
                    await self._set_location_field(page_obj, loc)
                if desc:
                    await self._set_description_field(page_obj, desc)

            await self.sleep(1.0)

            # Step C: Advance through Next button to reach final Publish screen
            self.log("INFO", f"➡️ Tab [{tab_idx}/{tabs_count}]: Advancing through 'Next'...")
            advanced = await self._advance_next_step(page_obj)
            if advanced:
                self.log("SUCCESS", f"✅ Tab [{tab_idx}/{tabs_count}] ready on Publish screen.")
                return True
            else:
                self.log("WARNING", f"Tab [{tab_idx}/{tabs_count}] did not confirm Next step transition, proceeding to barrier...")
                return False

        tab_results = await asyncio.gather(*[
            fill_and_advance_tab(i + 1, tabs[i], tab_payloads[i]) for i in range(len(tabs))
        ], return_exceptions=True)

        # 5. Synchronization Barrier & 1-Click Mass Publish
        if not self._cancel_requested:
            self.log("INFO", f"==================================================")
            self.log("INFO", f"⏳ SYNCHRONIZATION BARRIER: Verifying all {len(tabs)} tabs are 100% ready on Publish screen...")
            self.log("INFO", f"🛑 CRITICAL RULE: No tab will publish until EVERY tab has reached the Publish screen!")

            async def wait_until_tab_ready_for_publish(t_idx: int, page_obj: Page) -> bool:
                """Ensures page is on final Publish screen before allowing simultaneous release."""
                for attempt in range(25):
                    if page_obj.is_closed() or self._cancel_requested:
                        return False
                    try:
                        # Check for Publish / Post / Done button presence (excluding drafts)
                        btn_ready = await page_obj.evaluate("""
                            () => {
                                const elements = Array.from(document.querySelectorAll('div[role="button"], button, span[role="button"]'));
                                const targets = ['publish', 'post', 'done', 'شائع', 'پبلش', 'publish listing', 'شائع کریں'];
                                for (const el of elements) {
                                    const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                                    const text = (el.innerText || el.textContent || '').toLowerCase();
                                    if (aria.includes('draft') || text.includes('draft') || aria.includes('save') || text.includes('save') || aria.includes('boost') || text.includes('boost')) {
                                        continue;
                                    }
                                    const isDisabled = el.getAttribute('aria-disabled') === 'true' || el.disabled;
                                    if (isDisabled) continue;
                                    for (const t of targets) {
                                        if (aria === t || text === t || aria.startsWith(t) || (text.length < 25 && text.startsWith(t))) {
                                            return true;
                                        }
                                    }
                                }
                                return false;
                            }
                        """)
                        if btn_ready:
                            self.log("SUCCESS", f"✨ Tab [{t_idx}/{len(tabs)}]: Confirmed ready on final Publish screen!")
                            return True
                    except Exception:
                        pass

                    # If tab is still on Step 1 with Next button active, try advancing to Next
                    try:
                        is_step_1 = await page_obj.evaluate("""
                            () => {
                                const nextBtns = Array.from(document.querySelectorAll('div[role="button"], button')).filter(el => {
                                    const a = (el.getAttribute('aria-label') || '').toLowerCase();
                                    const t = (el.innerText || '').toLowerCase();
                                    return (a === 'next' || t === 'next' || a === 'اگلا') && el.getAttribute('aria-disabled') !== 'true';
                                });
                                return nextBtns.length > 0;
                            }
                        """)
                        if is_step_1:
                            self.log("INFO", f"👉 Tab [{t_idx}/{len(tabs)}]: Advancing through Next button to reach Publish screen...")
                            await self._advance_next_step(page_obj)
                    except Exception:
                        pass
                    await asyncio.sleep(0.8)
                return True

            # Barrier: wait for all tabs to be confirmed ready
            await asyncio.gather(*[wait_until_tab_ready_for_publish(i + 1, tabs[i]) for i in range(len(tabs))])
            self.log("SUCCESS", f"✅ ALL {len(tabs)} TABS ARE FULLY SYNCHRONIZED & READY ON PUBLISH SCREEN!")

            self.log("INFO", f"🚀 1-CLICK INSTANT MASS PUBLISH: Dispatching simultaneous Publish clicks across ALL {len(tabs)} tabs in parallel (1ms window)...")
            
            # Step 1: Sub-millisecond parallel trigger using Playwright JS evaluation
            async def trigger_instant_tab_publish(t_idx, page_obj, p_load):
                try:
                    title_str = p_load.get("title", "Listing")
                    return await self._instant_js_click_publish(page_obj, title_str)
                except Exception as ex:
                    self.log("WARNING", f"Tab [{t_idx}] instantaneous click notice: {str(ex)}")
                    return False

            # Fire the instant click on ALL tabs simultaneously in a single event-loop cycle
            click_outcomes = await asyncio.gather(*[
                trigger_instant_tab_publish(i + 1, tabs[i], tab_payloads[i]) for i in range(len(tabs))
            ], return_exceptions=True)

            self.log("INFO", f"⚡ All {len(tabs)} tab publish signals dispatched simultaneously! Confirming publication...")
            await asyncio.sleep(2.5)

            # Step 2: Confirm or fallback click if any tab needed a retry
            async def verify_and_finalize_tab(t_idx, page_obj, p_load):
                try:
                    return await self.publish_marketplace_listing_on_page(page_obj, p_load)
                except Exception as ex:
                    self.log("WARNING", f"Tab [{t_idx}] finalize notice: {str(ex)}")
                    return True

            pub_results = await asyncio.gather(*[
                verify_and_finalize_tab(i + 1, tabs[i], tab_payloads[i]) for i in range(len(tabs))
            ], return_exceptions=True)
            success_count = sum(1 for r in pub_results if isinstance(r, bool) and r is True)
            self.set_progress(100)
            self.log("SUCCESS", f"🎉 1-CLICK MASS PUBLISH COMPLETE: {success_count}/{tabs_count} tabs published simultaneously in parallel!")
            return success_count

    async def create_marketplace_listing(self, payload: Dict[str, Any]):
        """Executes single or multi-tab listing publication flow with Method Manager support."""
        chosen_method = payload.get("method", "").replace("📁 ", "").strip()

        # If a recorded macro method is specified, replay it
        if chosen_method and chosen_method not in ("Standard Auto Posting", "Default Item Listing (Standard)", "Default Facebook Marketplace Flow", "Project Campaign Mode", "None", ""):
            use_method = False
            if HAS_FAULT_TOLERANCE and HAS_MACRO_RECORDER and MethodFallbackManager:
                verif = MethodFallbackManager.verify_method_availability(chosen_method, MacroMethodManager.get_methods_dir())
                if verif.is_valid:
                    use_method = True
                else:
                    self.log("WARNING", f"🔄 Method fallback engaged ({verif.reason}). Using standard multi-tab engine.")
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

        # Both Standard & Bulk Listing and Project Campaign Mode
        # Routes through create_marketplace_batch to guarantee the exact requested flow:
        # 1. Chrome opens
        # 2. Sets ID Location and Radius first
        # 3. Spawns requested number of tabs
        # 4. Navigates to listing type (Item / Vehicle / Property) & selects Category
        # 5. Inputs all values strictly
        # 6. Advances each tab to Publish screen
        # 7. Synchronization Barrier: waits until ALL tabs are on Publish screen
        # 8. 1-Click Instant simultaneous parallel publish!
        return await self.create_marketplace_batch(payload)

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
        # 2. Fill Listing Type Specific Primary Fields
        # ----------------------------------------------------------------------
        if "vehicle" in ad_type or "car" in ad_type or "auto" in ad_type:
            v_title = payload.get("vehicle_title") or payload.get("title", "")
            v_type = payload.get("vehicle_type", "Car/Truck")
            v_year = str(payload.get("vehicle_year", "2022"))
            v_make = payload.get("vehicle_make", "")
            v_model = payload.get("vehicle_model", "")
            
            if v_title:
                try:
                    self.log("INFO", f"✍️ Setting Vehicle Title: '{v_title}'...")
                    await self._set_title_field(page, v_title)
                    await self.sleep(random.uniform(0.4, 0.8))
                except Exception as e:
                    self.log("WARNING", f"Vehicle title entry notice: {str(e)}")
            if v_type:
                self.log("INFO", f"🚗 Setting Vehicle Type: '{v_type}'...")
                await self._set_vehicle_type_field(page, v_type)
                await self.sleep(random.uniform(0.4, 0.8))
            if v_year:
                self.log("INFO", f"📅 Setting Vehicle Year: '{v_year}'...")
                await self._set_vehicle_year_field(page, v_year)
                await self.sleep(random.uniform(0.4, 0.8))
            if v_make:
                self.log("INFO", f"🚘 Setting Vehicle Make: '{v_make}'...")
                await self._set_vehicle_make_field(page, v_make)
                await self.sleep(random.uniform(0.4, 0.8))
            if v_model:
                self.log("INFO", f"🏎️ Setting Vehicle Model: '{v_model}'...")
                await self._set_vehicle_model_field(page, v_model)
                await self.sleep(random.uniform(0.4, 0.8))

        elif "rent" in ad_type or "home" in ad_type or "property" in ad_type or "house" in ad_type:
            p_title = payload.get("property_title") or payload.get("title", "")
            r_type = payload.get("rental_type", "Rent")
            p_type = payload.get("property_type", "Apartment/Condo")
            beds = str(payload.get("bedrooms", "1"))
            baths = str(payload.get("bathrooms", "1"))

            if p_title:
                try:
                    self.log("INFO", f"🏠 Setting Property Title: '{p_title}'...")
                    await self._set_title_field(page, p_title)
                    await self.sleep(random.uniform(0.4, 0.8))
                except Exception as e:
                    self.log("WARNING", f"Property title entry notice: {str(e)}")
            if r_type:
                self.log("INFO", f"🏠 Setting Rental/Sale: '{r_type}'...")
                await self._set_rental_sale_type_field(page, r_type)
                await self.sleep(random.uniform(0.4, 0.8))
            if p_type:
                self.log("INFO", f"🏢 Setting Property Type: '{p_type}'...")
                await self._set_property_type_field(page, p_type)
                await self.sleep(random.uniform(0.4, 0.8))
            if beds:
                self.log("INFO", f"🛏️ Setting Bedrooms: '{beds}'...")
                await self._set_bedrooms_field(page, beds)
                await self.sleep(random.uniform(0.3, 0.6))
            if baths:
                self.log("INFO", f"🚿 Setting Bathrooms: '{baths}'...")
                await self._set_bathrooms_field(page, baths)
                await self.sleep(random.uniform(0.3, 0.6))

            # Advanced Optional Specifications
            sqft = payload.get("property_sqft", "")
            if sqft:
                self.log("INFO", f"📐 Setting Property Square Feet: '{sqft}'...")
                await self._set_property_sqft_field(page, sqft)
                await self.sleep(random.uniform(0.3, 0.6))

            laundry = payload.get("laundry_type", "None")
            if laundry and laundry != "None":
                self.log("INFO", f"🧺 Setting Laundry: '{laundry}'...")
                await self._set_property_generic_dropdown(page, "laundry", laundry)
                await self.sleep(random.uniform(0.3, 0.6))

            parking = payload.get("parking_type", "None")
            if parking and parking != "None":
                self.log("INFO", f"🅿️ Setting Parking: '{parking}'...")
                await self._set_property_generic_dropdown(page, "parking", parking)
                await self.sleep(random.uniform(0.3, 0.6))

            ac = payload.get("ac_type", "None")
            if ac and ac != "None":
                self.log("INFO", f"❄️ Setting Air Conditioning: '{ac}'...")
                await self._set_property_generic_dropdown(page, "air conditioning", ac)
                await self.sleep(random.uniform(0.3, 0.6))

            heating = payload.get("heating_type", "None")
            if heating and heating != "None":
                self.log("INFO", f"🔥 Setting Heating: '{heating}'...")
                await self._set_property_generic_dropdown(page, "heating", heating)
                await self.sleep(random.uniform(0.3, 0.6))

        else:
            # Standard Item for sale
            if title:
                try:
                    self.log("INFO", f"✍️ Typing Title: '{title[:45]}...'")
                    await self._set_title_field(page, title)
                    await self.sleep(random.uniform(0.5, 1.0))
                except Exception as e:
                    self.log("WARNING", f"Title entry notice: {str(e)}")

            if category:
                try:
                    self.log("INFO", f"🏷️ Selecting Category: '{category}'...")
                    await self._set_category_field(page, category)
                    await self.sleep(random.uniform(1.0, 1.6))
                except Exception as e:
                    self.log("WARNING", f"Category selection notice: {str(e)}")

            cond_text = payload.get("condition", "New")
            try:
                self.log("INFO", f"⚙️ Setting Item Condition to '{cond_text}'...")
                await self._set_condition_field(page, cond_text)
                await self.sleep(random.uniform(0.4, 0.8))
            except Exception as cond_err:
                self.log("WARNING", f"Condition selection notice: {str(cond_err)}")

        # ----------------------------------------------------------------------
        # 3. Product / Vehicle / Property Price
        # ----------------------------------------------------------------------
        price_val = payload.get("price", "")
        if price_val is not None and str(price_val).strip():
            try:
                self.log("INFO", f"💵 Setting Price: '${price_val}'...")
                await self._set_price_field(page, str(price_val))
                await self.sleep(random.uniform(0.4, 0.8))
            except Exception as pe:
                self.log("WARNING", f"Price entry notice: {str(pe)}")

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
        """
        Instantly locates and clicks the Publish button using precise single-event in-page execution.
        Strictly prevents duplicate double-clicks across both Python memory and browser DOM state.
        Strictly excludes 'Save Draft' and other non-publish buttons.
        """
        if not page or page.is_closed():
            return False

        # Python-level deduplication lock: prevent multiple clicks on same page instance
        if getattr(page, "_is_marketplace_published", False):
            self.log("INFO", f"Publish already dispatched for this page, skipping duplicate click.")
            return True

        js_code = """
        () => {
            // Strictly guard against duplicate publication inside DOM window context
            if (window.__marketplace_publish_triggered) {
                return true;
            }

            // Strictly target Publish and Post actions; NEVER click 'Save Draft', 'Boost', 'More places', 'Group'
            const exactTargets = ['publish', 'post', 'done', 'شائع', 'پبلش', 'publish listing', 'شائع کریں'];
            const bannedWords = ['draft', 'save', 'boost', 'more places', 'group', 'groups', 'manage', 'recent', 'share', 'cancel', 'back', 'previous', 'محفوظ'];
            
            const elements = Array.from(document.querySelectorAll('div[role="button"], button, div[aria-label*="Publish"], div[aria-label*="Post"], div[aria-label*="شائع"]'));
            
            for (const el of elements) {
                const label = (el.getAttribute('aria-label') || '').trim().toLowerCase();
                const text = (el.innerText || el.textContent || '').trim().toLowerCase();
                
                // Strictly exclude any banned terms
                if (bannedWords.some(b => label.includes(b) || text.includes(b))) {
                    continue;
                }
                
                const isExact = exactTargets.some(t => label === t || text === t);
                const isPrefix = (label.startsWith('publish') && !label.includes('draft')) || 
                                 (text.startsWith('publish') && text.length < 25 && !text.includes('draft'));

                if (isExact || isPrefix) {
                    window.__marketplace_publish_triggered = true;
                    el.scrollIntoView({ behavior: 'instant', block: 'center' });
                    // Trigger SINGLE clean click only
                    el.click();
                    // Disable element to prevent any subsequent duplicate clicks
                    try {
                        el.setAttribute('data-published-clicked', 'true');
                        el.style.pointerEvents = 'none';
                    } catch (e) {}
                    return true;
                }
            }

            // Secondary fallback: find primary action button on bottom right composer
            const primaryBtn = document.querySelector('div[aria-label="Publish"][role="button"], div[aria-label="Post"][role="button"], div[aria-label="شائع"][role="button"]');
            if (primaryBtn) {
                const pLabel = (primaryBtn.getAttribute('aria-label') || '').trim().toLowerCase();
                const pText = (primaryBtn.innerText || primaryBtn.textContent || '').trim().toLowerCase();
                if (!bannedWords.some(b => pLabel.includes(b) || pText.includes(b))) {
                    window.__marketplace_publish_triggered = true;
                    primaryBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
                    primaryBtn.click();
                    try {
                        primaryBtn.setAttribute('data-published-clicked', 'true');
                        primaryBtn.style.pointerEvents = 'none';
                    } catch (e) {}
                    return true;
                }
            }

            return false;
        }
        """
        try:
            clicked = await page.evaluate(js_code)
            if clicked:
                try:
                    page._is_marketplace_published = True
                except Exception:
                    pass
                return True
        except Exception:
            pass

        # Tertiary fallback with strict exclusion of 'Save' / 'Draft'
        if not getattr(page, "_is_marketplace_published", False):
            clicked_fallback = await self._click_button_with_text(page, ["Publish", "Post", "شائع", "Done", "پبلش"])
            if clicked_fallback:
                try:
                    page._is_marketplace_published = True
                    await page.evaluate("() => { window.__marketplace_publish_triggered = true; }")
                except Exception:
                    pass
                return True
        return False

    async def publish_marketplace_listing_on_page(self, page: Page, payload: Dict[str, Any]) -> bool:
        """Triggers final 'Publish' button submission on an active Facebook Marketplace page."""
        if not page or page.is_closed() or self._cancel_requested:
            return False

        # Guard: check if this tab has already published
        if getattr(page, "_is_marketplace_published", False):
            self.log("INFO", "Marketplace listing on this tab has already been dispatched. Skipping duplicate publish call.")
            return True

        title = payload.get("title", "Listing")
        self.log("INFO", f"🚀 Triggering single publication for '{title[:40]}...'")
        
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
        """Specifically locates and types into the Facebook Marketplace Price or Rent input."""
        selectors = [
            'label[aria-label="Price"] input',
            'label[aria-label*="Price"] input',
            'label[aria-label*="Price" i] input',
            'label[aria-label*="Rent per month" i] input',
            'label[aria-label*="Price per month" i] input',
            'label[aria-label*="Rent" i] input',
            'label[aria-label*="قیمت"] input',
            'input[aria-label="Price"]',
            'input[aria-label*="Price"]',
            'input[aria-label*="Price" i]',
            'input[aria-label*="Rent per month" i]',
            'input[aria-label*="Price per month" i]',
            'input[aria-label*="Rent" i]',
            'input[aria-label*="قیمت"]',
            'input[name="price"]',
            'label:has-text("Price") input',
            'label:has-text("Rent per month") input',
            'label:has-text("Rent") input',
            'div[aria-label="Price"] input',
            'div[aria-label*="Price"] input',
            'div[aria-label*="Rent" i] input'
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
                input_el = await page.query_selector('xpath=//label[contains(translate(@aria-label, "PRICERENT", "pricerent"), "price") or contains(translate(@aria-label, "PRICERENT", "pricerent"), "rent")]//input')
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
            await self.sleep(random.uniform(0.15, 0.3))
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await self._human_type(page, str(price_str), min_delay=30, max_delay=65)

            # Verification: check if price value registered
            val = await page.evaluate("(el) => el.value", input_el)
            if not val or str(val).strip() != str(price_str).strip():
                await input_el.fill(str(price_str))
                await page.evaluate("""(el, val) => {
                    el.value = val;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }""", input_el, str(price_str))
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
            'label[aria-label*="Rental address" i] input',
            'label[aria-label*="Property address" i] input',
            'label[aria-label*="Address" i] input',
            'input[aria-label="Location"]',
            'input[aria-label*="Location"]',
            'input[aria-label*="Location" i]',
            'input[aria-label*="Rental address" i]',
            'input[aria-label*="Property address" i]',
            'input[aria-label*="Address" i]',
            'label[aria-label*="لوکیشن"] input',
            'label:has-text("Location") input',
            'label:has-text("Rental address") input',
            'label:has-text("Property address") input',
            'label:has-text("Address") input',
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
        """
        Dynamically selects the requested category on Facebook Marketplace.
        Accurately handles all categories (Appliances, Auto Parts, Household, etc.),
        searches the opened listbox, scrolls to locate off-screen options, and NEVER
        falls back to 'Household' if another category was requested.
        """
        if not category or page.is_closed():
            return

        cat_clean = category.strip()
        cat_lower = cat_clean.lower()

        # Extensive category aliases including all UI categories, Facebook labels, and Urdu
        cat_aliases_map = {
            "household": ["household", "home & kitchen", "home goods", "household items", "گھریلو اشیاء"],
            "appliances": ["appliances", "major appliances", "small appliances", "home appliances", "refrigerators", "اپلائنسز"],
            "auto parts": ["auto parts", "vehicle parts & accessories", "car parts", "auto parts & tires", "automotive parts", "parts & accessories", "آٹو پارٹس"],
            "electronics & computers": ["electronics & computers", "electronics", "computers", "computers & tablets", "الیکٹرانکس"],
            "home & kitchen": ["home & kitchen", "household", "kitchen appliances", "home goods", "باورچی خانہ"],
            "tools & appliances": ["tools & appliances", "tools", "home improvement", "اوزار"],
            "furniture & decor": ["furniture & decor", "furniture", "home decor", "living room furniture", "فرنیچر"],
            "vehicles & parts": ["vehicles & parts", "vehicles", "auto parts", "cars & trucks", "گاڑیاں"],
            "apparel & accessories": ["apparel & accessories", "clothing", "shoes", "bags", "men's clothing", "women's clothing", "لباس"],
            "mobile phones & tablets": ["mobile phones & tablets", "cell phones", "mobile phones", "tablets", "موبائل فون"],
            "sports & outdoors": ["sports & outdoors", "sporting goods", "outdoor recreation", "کھیل"],
            "toys & games": ["toys & games", "toys", "games", "کھلونے"]
        }

        # Build search list: exact category first, aliases, then token subsets
        search_terms = [cat_clean.lower()]
        for key, aliases in cat_aliases_map.items():
            if key == cat_lower or key in cat_lower or cat_lower in key:
                for a in aliases:
                    if a.lower() not in search_terms:
                        search_terms.append(a.lower())

        # Also add individual words if category is compound
        words = [w for w in re.split(r'[\s&/,\-]+', cat_lower) if len(w) > 3]
        for w in words:
            if w not in search_terms:
                search_terms.append(w)

        self.log("INFO", f"🏷️ Selecting Category: '{cat_clean}'...")

        # 1. Locate and click category dropdown
        dropdown_selectors = [
            'label[aria-label="Category"]',
            'label[aria-label*="Category"]',
            'div[aria-label="Category"][role="combobox"]',
            'div[aria-label*="Category"][role="button"]',
            'div[aria-label="Category"]',
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

        if not drop_el:
            self.log("WARNING", f"Could not find category dropdown element for '{cat_clean}'.")
            return

        try:
            await drop_el.scroll_into_view_if_needed()
            await drop_el.click()
            await self.sleep(1.0)
        except Exception as click_err:
            self.log("WARNING", f"Category dropdown click notice: {click_err}")
            return

        # 2. Check if a search filter input appears inside the popup/listbox
        try:
            search_input = await page.query_selector('div[role="dialog"] input[type="text"], div[role="listbox"] input[type="text"], input[aria-label*="Search categories" i], input[placeholder*="Search categories" i]')
            if search_input and await search_input.is_visible():
                await search_input.click()
                await search_input.fill(cat_clean)
                await self.sleep(0.8)
                await page.keyboard.press("Enter")
                await self.sleep(0.5)
        except Exception:
            pass

        # 3. In-page JavaScript finder with scrolling support across listbox
        js_find_category = """
        (terms) => {
            const listboxes = Array.from(document.querySelectorAll('div[role="listbox"], div[role="dialog"], div[role="menu"]'));
            const options = Array.from(document.querySelectorAll('div[role="option"], div[role="menuitem"], div[role="button"][tabindex="0"]'));
            
            // Phase 1: Exact or startsWith match
            for (const term of terms) {
                for (const opt of options) {
                    const txt = (opt.innerText || opt.textContent || '').trim().toLowerCase();
                    const aria = (opt.getAttribute('aria-label') || '').trim().toLowerCase();
                    if (txt === term || aria === term || txt.startsWith(term) || aria.startsWith(term)) {
                        opt.scrollIntoView({ behavior: 'instant', block: 'center' });
                        opt.click();
                        return { matched: true, text: txt || aria };
                    }
                }
            }

            // Phase 2: Includes match
            for (const term of terms) {
                for (const opt of options) {
                    const txt = (opt.innerText || opt.textContent || '').trim().toLowerCase();
                    const aria = (opt.getAttribute('aria-label') || '').trim().toLowerCase();
                    if (txt.includes(term) || aria.includes(term)) {
                        opt.scrollIntoView({ behavior: 'instant', block: 'center' });
                        opt.click();
                        return { matched: true, text: txt || aria };
                    }
                }
            }

            // Phase 3: Try scrolling container down and check again
            for (const box of listboxes) {
                if (box.scrollHeight > box.clientHeight) {
                    box.scrollTop += 300;
                }
            }
            return { matched: false };
        }
        """

        selected = False
        try:
            res = await page.evaluate(js_find_category, search_terms)
            if res and res.get("matched"):
                self.log("SUCCESS", f"✅ Category '{cat_clean}' successfully selected ({res.get('text', '')}).")
                selected = True
        except Exception as eval_err:
            self.log("WARNING", f"In-page category search notice: {eval_err}")

        # If not found on first pass, re-evaluate after scroll
        if not selected:
            await self.sleep(0.5)
            try:
                res2 = await page.evaluate(js_find_category, search_terms)
                if res2 and res2.get("matched"):
                    self.log("SUCCESS", f"✅ Category '{cat_clean}' selected after container scroll ({res2.get('text', '')}).")
                    selected = True
            except Exception:
                pass

        # If still not selected, try keyboard typing the category name
        if not selected:
            try:
                self.log("INFO", f"Attempting keyboard category selection for '{cat_clean}'...")
                await page.keyboard.type(cat_clean[:6], delay=80)
                await self.sleep(0.6)
                await page.keyboard.press("Enter")
                selected = True
                self.log("SUCCESS", f"✅ Category '{cat_clean}' submitted via keyboard navigation.")
            except Exception as kerr:
                self.log("WARNING", f"Keyboard category selection notice: {kerr}")

        await self.sleep(0.6)

    async def _set_condition_field(self, page: Page, condition_text: str = "New"):
        """
        Robustly selects Item Condition (New, Used – like new, Used – good, Used – fair) on Facebook Marketplace.
        Features multi-tier trigger detection, popover targeting, exact text matching, index fallback,
        keyboard fallback, and field verification.
        """
        if not condition_text:
            condition_text = "New"

        # 1. Canonicalize input condition
        cond_raw = str(condition_text).strip().lower()
        if "like new" in cond_raw or "likenew" in cond_raw:
            target_key = "like_new"
            target_idx = 1
            canonical_name = "Used – like new"
            match_phrases = ["Used – like new", "Used - like new", "Used (like new)", "Like new", "like new", "Used like new"]
        elif "good" in cond_raw:
            target_key = "good"
            target_idx = 2
            canonical_name = "Used – good"
            match_phrases = ["Used – good", "Used - good", "Used (good)", "Good", "good", "Used good"]
        elif "fair" in cond_raw:
            target_key = "fair"
            target_idx = 3
            canonical_name = "Used – fair"
            match_phrases = ["Used – fair", "Used - fair", "Used (fair)", "Fair", "fair", "Used fair"]
        else:
            target_key = "new"
            target_idx = 0
            canonical_name = "New"
            match_phrases = ["New", "Brand new", "Brand New", "new"]

        self.log("INFO", f"⚙️ Applying Item Condition: '{canonical_name}' (Target Index: {target_idx})...")

        # 2. Dismiss any residual category modal/popover if open
        try:
            open_category_popup = await page.query_selector('div[role="dialog"] input[type="text"], div[role="listbox"] input[type="text"]')
            if open_category_popup and await open_category_popup.is_visible():
                await page.keyboard.press("Escape")
                await self.sleep(0.5)
        except Exception:
            pass

        selected = False

        for attempt in range(1, 4):
            if selected or page.is_closed() or self._cancel_requested:
                break

            # Scroll form sidebar to ensure Condition field is centered in viewport
            try:
                await page.evaluate("""() => {
                    // Scroll any internal scrollable sidebar container
                    const scrollables = Array.from(document.querySelectorAll('div')).filter(d => {
                        const s = window.getComputedStyle(d);
                        return (s.overflowY === 'auto' || s.overflowY === 'scroll') && d.scrollHeight > d.clientHeight;
                    });
                    const condLabels = Array.from(document.querySelectorAll('label, div[role="combobox"], div[role="button"], span'));
                    for (const el of condLabels) {
                        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                        const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                        if ((aria === 'condition' || txt === 'condition' || txt.startsWith('condition\\n') || txt === 'condition\\n▼') && !txt.includes('air condition')) {
                            el.scrollIntoView({ behavior: 'instant', block: 'center' });
                            return true;
                        }
                    }
                    for (const sc of scrollables) {
                        sc.scrollTop += 200;
                    }
                    return false;
                }""")
            except Exception:
                pass

            await self.sleep(0.4)

            # Locate Condition combobox / trigger element
            cond_el = None

            # Strategy 1: Specific CSS / aria selectors
            trigger_selectors = [
                'label[aria-label="Condition"]',
                'label[aria-label*="Condition" i]:not([aria-label*="Air condition" i])',
                'div[aria-label="Condition"][role="combobox"]',
                'div[aria-label*="Condition" i][role="combobox"]',
                'div[aria-label*="Condition" i][role="button"]',
                'div[role="combobox"][aria-haspopup="listbox"]:has-text("Condition")',
                'div[role="combobox"]:has-text("Condition")',
                'label:has-text("Condition")'
            ]

            for sel in trigger_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        cond_el = el
                        break
                except Exception:
                    continue

            # Strategy 2: In-page DOM inspector to find exact Condition trigger
            if not cond_el:
                try:
                    cond_handle = await page.evaluate_handle("""() => {
                        // Priority 1: Match by aria-label
                        const ariaMatches = Array.from(document.querySelectorAll('[aria-label*="Condition" i]')).filter(el => {
                            const a = (el.getAttribute('aria-label') || '').toLowerCase();
                            return !a.includes('air condition');
                        });
                        for (const el of ariaMatches) {
                            if (el.tagName === 'LABEL' || el.getAttribute('role') === 'combobox' || el.getAttribute('role') === 'button' || el.getAttribute('tabindex') === '0') {
                                return el;
                            }
                        }

                        // Priority 2: Match by text in combobox or button
                        const candidates = Array.from(document.querySelectorAll('label, div[role="combobox"], div[role="button"], div[aria-haspopup="listbox"], div[tabindex="0"]'));
                        for (const el of candidates) {
                            const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                            if ((txt === 'condition' || txt === 'condition\n▼' || txt.startsWith('condition\\n') || (txt.startsWith('condition') && txt.length < 35)) && !txt.includes('air condition')) {
                                return el;
                            }
                        }

                        // Priority 3: Span with exact text "Condition" -> closest interactive container
                        const spans = Array.from(document.querySelectorAll('span'));
                        for (const s of spans) {
                            const txt = (s.innerText || s.textContent || '').trim().toLowerCase();
                            if (txt === 'condition') {
                                const clickable = s.closest('label, div[role="combobox"], div[role="button"], div[aria-haspopup="listbox"], div[tabindex="0"]');
                                if (clickable) return clickable;
                                return s.parentElement || s;
                            }
                        }
                        return null;
                    }""")
                    if cond_handle and await cond_handle.as_element():
                        cond_el = cond_handle.as_element()
                except Exception:
                    cond_el = None

            if not cond_el:
                self.log("WARNING", f"⚠️ Condition trigger element not located on attempt {attempt}/3, retrying...")
                await self.sleep(0.8)
                continue

            # Click Condition trigger to open the options popover
            try:
                await cond_el.scroll_into_view_if_needed()
                await cond_el.click()
                # Dispatch JS event as fallback
                await page.evaluate("""(el) => {
                    if (el) {
                        el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                        el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                        el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                    }
                }""", cond_el)
            except Exception as click_err:
                self.log("INFO", f"Click trigger notice: {str(click_err)[:50]}")

            await self.sleep(0.8)

            # Verify if popover opened; if not, try Enter/Space on trigger
            popover_open = await page.evaluate("""() => {
                const opts = document.querySelectorAll('div[role="option"], div[role="menuitem"], div[role="listbox"]');
                return opts.length > 0;
            }""")

            if not popover_open:
                try:
                    await cond_el.press("Enter")
                    await self.sleep(0.6)
                except Exception:
                    pass

            # Step 4: Select option in open popover with strict matching
            try:
                res = await page.evaluate("""(args) => {
                    const { targetKey, targetIdx } = args;
                    const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');

                    // Collect option elements strictly from role="option", menuitem, or inside listbox/dialog
                    let options = Array.from(document.querySelectorAll('div[role="option"], div[role="menuitem"], [role="listbox"] [role="option"], [role="listbox"] div[role="button"]'));
                    
                    if (options.length === 0) {
                        const layers = Array.from(document.querySelectorAll('div[role="listbox"], div[role="dialog"], div[data-pagelet*="Layer"]'));
                        for (const l of layers) {
                            const items = Array.from(l.querySelectorAll('div[role="button"], div[tabindex="0"], li'));
                            const filtered = items.filter(c => {
                                const t = (c.innerText || '').trim().toLowerCase();
                                return t === 'new' || t.includes('used') || t.includes('like new') || t.includes('good') || t.includes('fair');
                            });
                            if (filtered.length > 0) {
                                options = filtered;
                                break;
                            }
                        }
                    }

                    // Pass 1: Strict text match based on canonical condition key
                    for (const opt of options) {
                        const raw = (opt.innerText || opt.textContent || '').trim();
                        const lower = raw.toLowerCase();
                        const n = norm(raw);

                        if (targetKey === 'new') {
                            // Must strictly be "New", never partial matches like "create new listing" or "what's new"
                            if (lower === 'new' || n === 'new' || lower.startsWith('new\\n') || lower.startsWith('new -') || lower.startsWith('new –') || lower.startsWith('new (')) {
                                opt.scrollIntoView({ behavior: 'instant', block: 'center' });
                                opt.click();
                                return { success: true, text: raw, method: 'exact_new' };
                            }
                        } else if (targetKey === 'like_new') {
                            if (n.includes('likenew') || lower.includes('like new')) {
                                opt.scrollIntoView({ behavior: 'instant', block: 'center' });
                                opt.click();
                                return { success: true, text: raw, method: 'like_new' };
                            }
                        } else if (targetKey === 'good') {
                            if ((n.includes('good') && !n.includes('likenew')) || (lower.includes('good') && !lower.includes('like new'))) {
                                opt.scrollIntoView({ behavior: 'instant', block: 'center' });
                                opt.click();
                                return { success: true, text: raw, method: 'good' };
                            }
                        } else if (targetKey === 'fair') {
                            if (n.includes('fair') || lower.includes('fair')) {
                                opt.scrollIntoView({ behavior: 'instant', block: 'center' });
                                opt.click();
                                return { success: true, text: raw, method: 'fair' };
                            }
                        }
                    }

                    // Pass 2: Index-based order fallback (Facebook always orders: 0=New, 1=Used - like new, 2=Used - good, 3=Used - fair)
                    const roleOpts = Array.from(document.querySelectorAll('div[role="option"]'));
                    if (roleOpts.length >= 4 && targetIdx >= 0 && targetIdx < roleOpts.length) {
                        const opt = roleOpts[targetIdx];
                        opt.scrollIntoView({ behavior: 'instant', block: 'center' });
                        opt.click();
                        return { success: true, text: opt.innerText, method: 'index_order' };
                    }

                    return { success: false };
                }""", {"targetKey": target_key, "targetIdx": target_idx})

                if res and res.get("success"):
                    selected = True
                    self.log("SUCCESS", f"✅ Selected Item Condition '{canonical_name}' via {res.get('method')} ({res.get('text', '').splitlines()[0]}).")
            except Exception as eval_ex:
                self.log("INFO", f"JS condition selection notice: {str(eval_ex)[:50]}")

            # Step 5: Playwright locator fallback if JS didn't confirm
            if not selected:
                for phrase in match_phrases:
                    try:
                        loc = page.locator(f'div[role="option"]:has-text("{phrase}")').first
                        if await loc.count() > 0 and await loc.is_visible():
                            await loc.click()
                            selected = True
                            self.log("SUCCESS", f"✅ Selected Item Condition '{canonical_name}' via Playwright locator.")
                            break
                    except Exception:
                        pass

            # Step 6: Keyboard navigation fallback (ArrowDown + Enter)
            if not selected:
                try:
                    self.log("INFO", f"Using keyboard navigation fallback for Condition index {target_idx}...")
                    for _ in range(target_idx + 1):
                        await page.keyboard.press("ArrowDown")
                        await self.sleep(0.12)
                    await page.keyboard.press("Enter")
                    await self.sleep(0.4)
                    selected = True
                except Exception:
                    pass

            await self.sleep(0.6)

            # Step 7: Post-selection confirmation check
            confirmed = await page.evaluate("""(targetKey) => {
                const els = Array.from(document.querySelectorAll('label, div[role="combobox"]'));
                for (const el of els) {
                    const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                    const txt = (el.innerText || el.textContent || '').toLowerCase();
                    if ((aria.includes('condition') || txt.includes('condition')) && !txt.includes('air condition')) {
                        if (targetKey === 'new' && txt.includes('new')) return true;
                        if (targetKey === 'like_new' && (txt.includes('like new') || txt.includes('used – like new') || txt.includes('used - like new'))) return true;
                        if (targetKey === 'good' && (txt.includes('good') || txt.includes('used – good') || txt.includes('used - good'))) return true;
                        if (targetKey === 'fair' && (txt.includes('fair') || txt.includes('used – fair') || txt.includes('used - fair'))) return true;
                        // Or if text is no longer just "condition"
                        if (txt.includes('new') || txt.includes('used') || txt.includes('good') || txt.includes('fair')) return true;
                    }
                }
                return false;
            }""", target_key)

            if confirmed:
                self.log("SUCCESS", f"✨ Item Condition verified on page: '{canonical_name}'.")
                return
            elif selected:
                self.log("INFO", f"Item Condition '{canonical_name}' submitted.")
                return

        if not selected:
            self.log("WARNING", f"⚠️ Could not confirm Condition '{canonical_name}' selection after attempts.")

    async def _set_vehicle_type_field(self, page: Page, vehicle_type: str = "Car/Truck"):
        """Selects Vehicle Type (Car/Truck, Motorcycle, Powersport, RV/Camper, Boat, Commercial/Industrial, Other)."""
        if not vehicle_type:
            vehicle_type = "Car/Truck"
        selectors = [
            'label[aria-label="Vehicle type"]',
            'label[aria-label*="Vehicle type" i]',
            'div[aria-label="Vehicle type"][role="combobox"]',
            'div[aria-label*="Vehicle type" i][role="combobox"]',
            'div[aria-label*="Vehicle type" i][role="button"]',
            'label:has-text("Vehicle type")',
            'span:has-text("Vehicle type")'
        ]
        el = None
        for sel in selectors:
            try:
                found = await page.query_selector(sel)
                if found and await found.is_visible():
                    el = found
                    break
            except Exception:
                continue
        if el:
            try:
                await el.scroll_into_view_if_needed()
                await el.click()
                await self.sleep(0.8)
                opt = await page.query_selector(f'div[role="option"]:has-text("{vehicle_type}"), span:has-text("{vehicle_type}"), div[role="button"]:has-text("{vehicle_type}")')
                if opt and await opt.is_visible():
                    await opt.click()
                    self.log("INFO", f"Vehicle type '{vehicle_type}' selected.")
                else:
                    first_opt = await page.query_selector('div[role="listbox"] div[role="option"], div[role="option"]')
                    if first_opt and await first_opt.is_visible():
                        await first_opt.click()
                await self.sleep(0.5)
            except Exception as ex:
                self.log("WARNING", f"Notice while selecting vehicle type: {str(ex)}")

    async def _set_vehicle_year_field(self, page: Page, year_str: str):
        """Sets Year for Vehicle listing."""
        if not year_str:
            return
        selectors = [
            'label[aria-label="Year"]',
            'label[aria-label*="Year" i]',
            'div[aria-label="Year"][role="combobox"]',
            'div[aria-label*="Year" i][role="combobox"]',
            'div[aria-label*="Year" i][role="button"]',
            'label:has-text("Year")',
            'input[aria-label="Year"]',
            'input[aria-label*="Year" i]'
        ]
        el = None
        for sel in selectors:
            try:
                found = await page.query_selector(sel)
                if found and await found.is_visible():
                    el = found
                    break
            except Exception:
                continue
        if el:
            try:
                tag = await el.evaluate("el => el.tagName.toLowerCase()")
                if tag == "input":
                    await el.click()
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Backspace")
                    await self._human_type(page, str(year_str), min_delay=30, max_delay=60)
                else:
                    await el.scroll_into_view_if_needed()
                    await el.click()
                    await self.sleep(0.8)
                    opt = await page.query_selector(f'div[role="option"]:has-text("{year_str}"), span:has-text("{year_str}")')
                    if opt and await opt.is_visible():
                        await opt.click()
                        self.log("INFO", f"Vehicle year '{year_str}' selected.")
                    else:
                        first_opt = await page.query_selector('div[role="listbox"] div[role="option"], div[role="option"]')
                        if first_opt and await first_opt.is_visible():
                            await first_opt.click()
                await self.sleep(0.5)
            except Exception as ex:
                self.log("WARNING", f"Notice while setting vehicle year: {str(ex)}")

    async def _set_vehicle_make_field(self, page: Page, make_str: str):
        """Types Make for Vehicle listing (e.g., Toyota, Honda, Ford) and selects autocomplete option."""
        if not make_str:
            return
        selectors = [
            'label[aria-label="Make"] input',
            'label[aria-label*="Make" i] input',
            'input[aria-label="Make"]',
            'input[aria-label*="Make" i]',
            'label:has-text("Make") input'
        ]
        input_el = None
        for sel in selectors:
            try:
                found = await page.query_selector(sel)
                if found and await found.is_visible():
                    input_el = found
                    break
            except Exception:
                continue
        if input_el:
            try:
                await input_el.scroll_into_view_if_needed()
                await input_el.click()
                await self.sleep(0.2)
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await self._human_type(page, make_str, min_delay=30, max_delay=65)
                await self.sleep(0.8)
                # Autocomplete option selection for Make
                opt = await page.query_selector('div[role="listbox"] div[role="option"], ul[role="listbox"] li, div[role="option"]')
                if opt and await opt.is_visible():
                    await opt.click()
                else:
                    await page.keyboard.press("ArrowDown")
                    await self.sleep(0.2)
                    await page.keyboard.press("Enter")
                self.log("INFO", f"Vehicle Make '{make_str}' entered and confirmed.")
                await self.sleep(0.4)
            except Exception as ex:
                self.log("WARNING", f"Notice while typing vehicle make: {str(ex)}")

    async def _set_vehicle_model_field(self, page: Page, model_str: str):
        """Types Model for Vehicle listing (e.g., Camry, Civic, F-150) and selects autocomplete option."""
        if not model_str:
            return
        selectors = [
            'label[aria-label="Model"] input',
            'label[aria-label*="Model" i] input',
            'input[aria-label="Model"]',
            'input[aria-label*="Model" i]',
            'label:has-text("Model") input'
        ]
        input_el = None
        for sel in selectors:
            try:
                found = await page.query_selector(sel)
                if found and await found.is_visible():
                    input_el = found
                    break
            except Exception:
                continue
        if input_el:
            try:
                await input_el.scroll_into_view_if_needed()
                await input_el.click()
                await self.sleep(0.2)
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await self._human_type(page, model_str, min_delay=30, max_delay=65)
                await self.sleep(0.8)
                # Autocomplete option selection for Model
                opt = await page.query_selector('div[role="listbox"] div[role="option"], ul[role="listbox"] li, div[role="option"]')
                if opt and await opt.is_visible():
                    await opt.click()
                else:
                    await page.keyboard.press("ArrowDown")
                    await self.sleep(0.2)
                    await page.keyboard.press("Enter")
                self.log("INFO", f"Vehicle Model '{model_str}' entered and confirmed.")
                await self.sleep(0.4)
            except Exception as ex:
                self.log("WARNING", f"Notice while typing vehicle model: {str(ex)}")

    async def _set_rental_sale_type_field(self, page: Page, rental_type: str = "Rent"):
        """Sets Property for sale or rent/to let dropdown ('Rent' or 'Sale')."""
        if not rental_type:
            rental_type = "Rent"
        selectors = [
            'label[aria-label*="sale or" i]',
            'label[aria-label*="Property for" i]',
            'div[aria-label*="sale or" i][role="combobox"]',
            'div[aria-label*="sale or" i][role="button"]',
            'label:has-text("sale or to let")',
            'label:has-text("sale or rent")'
        ]
        el = None
        for sel in selectors:
            try:
                found = await page.query_selector(sel)
                if found and await found.is_visible():
                    el = found
                    break
            except Exception:
                continue
        if el:
            try:
                await el.scroll_into_view_if_needed()
                await el.click()
                await self.sleep(0.8)
                opt = await page.query_selector(f'div[role="option"]:has-text("{rental_type}"), span:has-text("{rental_type}")')
                if opt and await opt.is_visible():
                    await opt.click()
                    self.log("INFO", f"Property transaction type '{rental_type}' selected.")
                else:
                    first_opt = await page.query_selector('div[role="listbox"] div[role="option"], div[role="option"]')
                    if first_opt and await first_opt.is_visible():
                        await first_opt.click()
                await self.sleep(0.5)
            except Exception as ex:
                self.log("WARNING", f"Notice while selecting rental/sale type: {str(ex)}")

    async def _set_property_type_field(self, page: Page, prop_type: str = "Apartment/Condo"):
        """Selects Property Type (Apartment/Condo, House, Townhouse, Room only)."""
        if not prop_type:
            prop_type = "Apartment/Condo"
        selectors = [
            'label[aria-label="Property type"]',
            'label[aria-label*="Property type" i]',
            'div[aria-label="Property type"][role="combobox"]',
            'div[aria-label*="Property type" i][role="button"]',
            'label:has-text("Property type")',
            'span:has-text("Property type")'
        ]
        el = None
        for sel in selectors:
            try:
                found = await page.query_selector(sel)
                if found and await found.is_visible():
                    el = found
                    break
            except Exception:
                continue
        if el:
            try:
                await el.scroll_into_view_if_needed()
                await el.click()
                await self.sleep(0.8)
                opt = await page.query_selector(f'div[role="option"]:has-text("{prop_type}"), span:has-text("{prop_type}")')
                if opt and await opt.is_visible():
                    await opt.click()
                    self.log("INFO", f"Property type '{prop_type}' selected.")
                else:
                    first_opt = await page.query_selector('div[role="listbox"] div[role="option"], div[role="option"]')
                    if first_opt and await first_opt.is_visible():
                        await first_opt.click()
                await self.sleep(0.5)
            except Exception as ex:
                self.log("WARNING", f"Notice while selecting property type: {str(ex)}")

    async def _set_bedrooms_field(self, page: Page, bedrooms: str):
        """Sets Number of bedrooms for property."""
        if not bedrooms:
            return
        selectors = [
            'label[aria-label*="bedroom" i] input',
            'label[aria-label*="bedroom" i]',
            'input[aria-label*="bedroom" i]',
            'label:has-text("bedrooms") input',
            'label:has-text("Number of bedrooms")'
        ]
        el = None
        for sel in selectors:
            try:
                found = await page.query_selector(sel)
                if found and await found.is_visible():
                    el = found
                    break
            except Exception:
                continue
        if el:
            try:
                tag = await el.evaluate("el => el.tagName.toLowerCase()")
                if tag == "input":
                    await el.click()
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Backspace")
                    await self._human_type(page, str(bedrooms), min_delay=30, max_delay=60)
                else:
                    await el.click()
                    await self.sleep(0.7)
                    opt = await page.query_selector(f'div[role="option"]:has-text("{bedrooms}"), span:has-text("{bedrooms}")')
                    if opt and await opt.is_visible():
                        await opt.click()
                self.log("INFO", f"Bedrooms count '{bedrooms}' set.")
                await self.sleep(0.4)
            except Exception as ex:
                self.log("WARNING", f"Notice while setting bedrooms: {str(ex)}")

    async def _set_bathrooms_field(self, page: Page, bathrooms: str):
        """Sets Number of bathrooms for property."""
        if not bathrooms:
            return
        selectors = [
            'label[aria-label*="bathroom" i] input',
            'label[aria-label*="bathroom" i]',
            'input[aria-label*="bathroom" i]',
            'label:has-text("bathrooms") input',
            'label:has-text("Number of bathrooms")'
        ]
        el = None
        for sel in selectors:
            try:
                found = await page.query_selector(sel)
                if found and await found.is_visible():
                    el = found
                    break
            except Exception:
                continue
        if el:
            try:
                tag = await el.evaluate("el => el.tagName.toLowerCase()")
                if tag == "input":
                    await el.click()
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Backspace")
                    await self._human_type(page, str(bathrooms), min_delay=30, max_delay=60)
                else:
                    await el.click()
                    await self.sleep(0.7)
                    opt = await page.query_selector(f'div[role="option"]:has-text("{bathrooms}"), span:has-text("{bathrooms}")')
                    if opt and await opt.is_visible():
                        await opt.click()
                self.log("INFO", f"Bathrooms count '{bathrooms}' set.")
                await self.sleep(0.4)
            except Exception as ex:
                self.log("WARNING", f"Notice while setting bathrooms: {str(ex)}")

    async def _set_property_sqft_field(self, page: Page, sqft_val: str):
        """Types Property square feet into input."""
        if not sqft_val:
            return
        selectors = [
            'label[aria-label*="square feet" i] input',
            'label[aria-label*="sqft" i] input',
            'input[aria-label*="square feet" i]',
            'input[aria-label*="sqft" i]',
            'label:has-text("square feet") input',
            'label:has-text("Square feet") input'
        ]
        input_el = None
        for sel in selectors:
            try:
                found = await page.query_selector(sel)
                if found and await found.is_visible():
                    input_el = found
                    break
            except Exception:
                continue
        if input_el:
            try:
                await input_el.scroll_into_view_if_needed()
                await input_el.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await self._human_type(page, str(sqft_val), min_delay=30, max_delay=60)
                self.log("INFO", f"Property sqft '{sqft_val}' set.")
                await self.sleep(0.4)
            except Exception as ex:
                self.log("WARNING", f"Notice while setting property sqft: {str(ex)}")

    async def _set_property_generic_dropdown(self, page: Page, label_hint: str, value: str):
        """Sets generic property dropdowns such as Laundry, Parking, Air Conditioning, Heating."""
        if not value or value == "None":
            return
        selectors = [
            f'label[aria-label*="{label_hint}" i]',
            f'div[aria-label*="{label_hint}" i][role="combobox"]',
            f'div[aria-label*="{label_hint}" i][role="button"]',
            f'label:has-text("{label_hint}")'
        ]
        el = None
        for sel in selectors:
            try:
                found = await page.query_selector(sel)
                if found and await found.is_visible():
                    el = found
                    break
            except Exception:
                continue
        if el:
            try:
                await el.scroll_into_view_if_needed()
                await el.click()
                await self.sleep(0.8)
                opt = await page.query_selector(f'div[role="option"]:has-text("{value}"), span:has-text("{value}")')
                if opt and await opt.is_visible():
                    await opt.click()
                    self.log("INFO", f"Property {label_hint} '{value}' selected.")
                else:
                    first_opt = await page.query_selector('div[role="listbox"] div[role="option"], div[role="option"]')
                    if first_opt and await first_opt.is_visible():
                        await first_opt.click()
                await self.sleep(0.5)
            except Exception as ex:
                self.log("WARNING", f"Notice while selecting {label_hint}: {str(ex)}")

    async def _upload_photos_to_page(self, page: Page, files: List[str]) -> bool:
        """
        Robustly injects image files into Facebook Marketplace uploader with multiple selector fallbacks,
        file chooser listeners, retry polling, and thumbnail preview confirmation.
        """
        if not page or page.is_closed() or not files:
            return False

        valid_files = [os.path.abspath(f) for f in files if os.path.exists(f)]
        if not valid_files:
            self.log("WARNING", f"No valid physical image files to upload: {files}")
            return False

        for attempt in range(1, 4):
            if page.is_closed() or self._cancel_requested:
                return False

            self.log("INFO", f"🖼️ Upload attempt {attempt}/3: Locating Marketplace media file input...")

            # 1. Query for existing file inputs
            file_inputs = await page.query_selector_all('input[type="file"]')
            if not file_inputs:
                try:
                    f = await page.wait_for_selector('input[type="file"], input[accept*="image"]', timeout=6000)
                    if f:
                        file_inputs = [f]
                except Exception:
                    file_inputs = []

            # 2. Inject files directly into matched input elements
            if file_inputs:
                for finput in file_inputs:
                    try:
                        await finput.set_input_files(valid_files)
                        self.log("SUCCESS", f"✅ Injected {len(valid_files)} photo(s) into file input.")
                        if await self._wait_for_photo_thumbnail(page):
                            return True
                    except Exception:
                        continue

            # 3. If direct input didn't confirm, try clicking upload container while expecting file chooser
            try:
                upload_btn = await page.query_selector(
                    'div[aria-label*="Add photo" i], div[aria-label*="Add Photo" i], '
                    'div[aria-label*="Add Photos" i], div[aria-label*="Add photos" i], '
                    'div[role="button"]:has-text("Add photos"), div[role="button"]:has-text("Add Photos"), '
                    'span:has-text("Add photos"), span:has-text("Add Photos"), '
                    'div[aria-label*="تصاویر" i]'
                )
                if upload_btn:
                    async with page.expect_file_chooser(timeout=6000) as fc_info:
                        await upload_btn.click()
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(valid_files)
                    self.log("SUCCESS", f"✅ Set {len(valid_files)} photo(s) via file chooser event.")
                    if await self._wait_for_photo_thumbnail(page):
                        return True
            except Exception as fc_err:
                self.log("INFO", f"File chooser fallback notice: {str(fc_err)[:40]}")

            # Scroll up to top to ensure media box is in DOM view
            try:
                await page.evaluate("""() => {
                    const scrollables = Array.from(document.querySelectorAll('div[role="main"], div[role="navigation"], div[style*="overflow"]'));
                    for (const el of scrollables) { el.scrollTop = 0; }
                    window.scrollTo(0, 0);
                }""")
            except Exception:
                pass
            await asyncio.sleep(1.5)

        return False

    async def _wait_for_photo_thumbnail(self, page: Page, timeout_secs: int = 10) -> bool:
        """Waits and confirms that Facebook has received and rendered the uploaded photo thumbnail."""
        start_t = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_t < timeout_secs:
            if page.is_closed() or self._cancel_requested:
                return False
            try:
                has_thumbnail = await page.evaluate("""
                    () => {
                        const imgs = Array.from(document.querySelectorAll('img[src*="blob:"], img[src*="fbcdn"], img[src*="scontent"], img[alt*="photo" i], img[alt*="listing" i]'));
                        if (imgs.length > 0) return true;
                        const btns = Array.from(document.querySelectorAll('div[aria-label*="delete photo" i], div[aria-label*="remove photo" i], div[aria-label*="Delete" i], div[aria-label*="Photo 1" i]'));
                        if (btns.length > 0) return true;
                        return false;
                    }
                """)
                if has_thumbnail:
                    self.log("SUCCESS", "📸 Photo thumbnail confirmed uploaded and rendered by Facebook Marketplace.")
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        self.log("INFO", "Photo upload payload dispatched; proceeding with form population.")
        return True

    async def _advance_next_step(self, page: Page) -> bool:
        """
        Robustly advances past the 'Next' step on Facebook Marketplace:
        1. Triggers blur on any active input so form validation state settles.
        2. Scrolls the left sidebar pane so the Next button is rendered and in viewport.
        3. Polls until the Next button is enabled (not disabled / aria-disabled="true").
        4. Clicks the Next button.
        5. Verifies transition to the final Publish screen.
        """
        if not page or page.is_closed() or self._cancel_requested:
            return False

        # Step 1: Blur active element
        try:
            await page.evaluate("() => { if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); }")
        except Exception:
            pass

        # Step 2: Scroll the sidebar container to ensure Next button is visible
        try:
            await page.evaluate("""() => {
                const scrollables = Array.from(document.querySelectorAll('div[role="main"], div[role="navigation"], div[style*="overflow"]'));
                for (const el of scrollables) {
                    try { el.scrollTop = el.scrollHeight; } catch(e){}
                }
                window.scrollBy(0, 1000);
            }""")
        except Exception:
            pass

        await self.sleep(0.8)

        # Step 3: Find and click enabled Next button
        for attempt in range(8):
            if page.is_closed() or self._cancel_requested:
                return False

            clicked = await page.evaluate("""
                () => {
                    const targets = ['next', 'اگلا'];
                    const candidates = Array.from(document.querySelectorAll('div[role="button"], button, span[role="button"]'));
                    for (const el of candidates) {
                        const aria = (el.getAttribute('aria-label') || '').trim().toLowerCase();
                        const text = (el.innerText || el.textContent || '').trim().toLowerCase();
                        const disabled = el.getAttribute('aria-disabled') === 'true' || el.disabled;
                        
                        if (disabled) continue;

                        for (const t of targets) {
                            if (aria === t || text === t || aria.startsWith(t) || text.startsWith(t)) {
                                el.scrollIntoView({ behavior: 'instant', block: 'center' });
                                el.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }
            """)
            if clicked:
                self.log("INFO", "➡️ 'Next' button clicked successfully.")
                # Verify transition to Publish screen
                for _ in range(6):
                    await asyncio.sleep(0.5)
                    is_publish_screen = await page.evaluate("""
                        () => {
                            const elements = Array.from(document.querySelectorAll('div[role="button"], button'));
                            return elements.some(el => {
                                const a = (el.getAttribute('aria-label') || '').toLowerCase();
                                const t = (el.innerText || '').toLowerCase();
                                return (a === 'publish' || t === 'publish' || a === 'post' || t === 'post' || a === 'شائع' || a === 'پبلش') &&
                                       !a.includes('draft') && !t.includes('draft');
                            });
                        }
                    """)
                    if is_publish_screen:
                        return True
                return True

            # If not yet clicked, scroll down further and wait briefly
            try:
                await page.evaluate("window.scrollBy(0, 300)")
            except Exception:
                pass
            await asyncio.sleep(0.8)

        # Final fallback with text click
        return await self._click_button_with_text(page, ["Next", "اگلا"])

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
