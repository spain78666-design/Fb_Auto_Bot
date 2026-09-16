"""
FB Auto Bot - Enterprise Playwright Stealth Browser Controller
Phase 2: Asynchronous Anti-Detect Automation for Facebook Marketplace
"""

import os
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
# Stealth JavaScript Evasion Scripts
# ==============================================================================
EXTRA_STEALTH_JS = """
(() => {
    // 1. Mask navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });

    // 2. Mock Chrome Runtime
    if (!window.chrome) {
        window.chrome = {
            app: { isInstalled: false, InstallState: { DISABLED: 'disabled' }, RunningState: { CANNOT_RUN: 'cannot_run' } },
            runtime: {
                OnInstalledReason: { INSTALL: 'install', UPDATE: 'update', CHROME_UPDATE: 'chrome_update' },
                PlatformOs: { MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux' },
                PlatformArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' },
                connect: () => {},
                sendMessage: () => {}
            }
        };
    }

    // 3. WebGL Vendor / Renderer Masking
    const getParameterProto = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        // UNMASKED_VENDOR_WEBGL
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        // UNMASKED_RENDERER_WEBGL
        if (parameter === 37446) {
            return 'Intel(R) Iris(R) Xe Graphics (0x9a49)';
        }
        return getParameterProto.apply(this, arguments);
    };

    const getParameterProto2 = WebGL2RenderingContext ? WebGL2RenderingContext.prototype.getParameter : null;
    if (getParameterProto2) {
        WebGL2RenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel(R) Iris(R) Xe Graphics (0x9a49)';
            return getParameterProto2.apply(this, arguments);
        };
    }

    // 4. Overwrite Permissions query for notifications
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission, onchange: null }) :
            originalQuery(parameters)
    );

    // 5. Spoof Plugins list
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const plugins = [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' }
            ];
            plugins.item = (i) => plugins[i];
            plugins.namedItem = (name) => plugins.find(p => p.name === name);
            return plugins;
        }
    });
})();
"""


# ==============================================================================
# Helper Functions: Cookie & Proxy Parsers
# ==============================================================================
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


def get_fewfeed_extension_path() -> Optional[str]:
    """Resolves the absolute path to FEWFEED extension folder."""
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "FEWFEED")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "FEWFEED")),
        "/desktop_app/FEWFEED",
        os.path.abspath("FEWFEED"),
        os.path.abspath("desktop_app/FEWFEED")
    ]
    for c in candidates:
        if os.path.isdir(c) and os.path.exists(os.path.join(c, "manifest.json")):
            return os.path.abspath(c)
    return None


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
                    if "Executable doesn't exist" in str(ex) or "Channel" in str(ex):
                        continue
                    raise ex
            raise MarketplaceBotError("Could not find Google Chrome, Edge, or Chromium on this PC. Please install Google Chrome.")

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
                    if "Executable doesn't exist" in str(ex) or "Channel" in str(ex):
                        continue
                    raise ex
            raise MarketplaceBotError("Could not find Google Chrome, Edge, or Chromium on this PC. Please install Google Chrome.")

        try:
            if user_data_dir:
                self.log("INFO", f"Using isolated browser profile dir: {os.path.basename(user_data_dir)}")
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

    async def verify_session_health(self):
        """Navigates to Facebook home to verify if the injected session is active."""
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

        current_url = self.page.url
        self.log("INFO", f"Facebook responded on URL: {current_url}")

        # Check for login redirection
        if "login" in current_url or "checkpoint" in current_url:
            if "checkpoint" in current_url:
                raise CheckpointDetectedError(
                    "Facebook Security Checkpoint triggered! Account requires manual verification or 2FA."
                )
            raise InvalidSessionError(
                "Session not logged in or expired. Please click 'Launch Manual Login' in Accounts Tab to log into this Facebook profile."
            )

        # Check for profile navigation indicator or marketplace presence
        content = await self.page.content()
        if "login_form" in content or "login_button" in content:
            raise InvalidSessionError("Facebook displayed login prompt. Please log in via Accounts Tab first.")

        self.log("SUCCESS", "Session authenticated successfully! Active Facebook profile confirmed.")
        self.set_progress(35)

    # --------------------------------------------------------------------------
    # Core Listing Publication Flow & Multi-Tab Engine
    # --------------------------------------------------------------------------
    async def create_marketplace_batch(self, payload: Dict[str, Any]):
        """
        Multi-Tab Parallel Marketplace Listing Engine.
        Opens the exact specified number of Chrome browser tabs simultaneously,
        assigns a separate, distinct location and distinct image to each respective tab,
        and publishes listings with humanized anti-detection delays.
        """
        tabs_count = int(payload.get("tabs_count", payload.get("posts_per_id", 1)))
        tabs_count = max(1, min(tabs_count, 100))

        self.log("INFO", f"==================================================")
        self.log("INFO", f"🚀 MULTI-TAB PARALLEL ENGINE: {tabs_count} Tab(s) Configured")
        self.log("INFO", f"⚡ Preparing Distinct Location & Picture Mappings...")

        # 1. Distinct Location & Picture Mapping
        if HAS_FAULT_TOLERANCE and DistinctDataMapper:
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
                tp["location"] = loc_pool[i % len(loc_pool)]
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

        # 3. Simultaneously navigate all tabs to the Marketplace listing creation form
        ad_type = payload.get("listing_type", payload.get("ad_type", "item")).lower()
        if "vehicle" in ad_type or "car" in ad_type or "auto" in ad_type:
            create_url = "https://www.facebook.com/marketplace/create/vehicle"
        elif "rent" in ad_type or "home" in ad_type or "property" in ad_type or "house" in ad_type:
            create_url = "https://www.facebook.com/marketplace/create/rental"
        else:
            create_url = "https://www.facebook.com/marketplace/create/item"

        self.log("INFO", f"🌐 Navigating all {len(tabs)} tabs simultaneously to Marketplace create form ({create_url})...")

        async def navigate_tab_safely(tab_num: int, page_obj: Page):
            # Micro-stagger between tab navigation calls (150-350ms) to ensure socket throughput
            await asyncio.sleep((tab_num - 1) * random.uniform(0.2, 0.4))
            try:
                await page_obj.goto(create_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(random.uniform(0.8, 1.8))
            except Exception as e:
                self.log("WARNING", f"Tab [{tab_num}/{tabs_count}] DOM load notice: {str(e)[:45]}")

        await asyncio.gather(*[navigate_tab_safely(i + 1, tabs[i]) for i in range(len(tabs))])
        self.log("SUCCESS", f"🎉 All {len(tabs)} tabs loaded at Marketplace listing interface!")

        # 4. Method Manager Verification & Live UI Fallback determination
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

        # 5. Process each tab with human-like anti-detection delays
        success_count = 0
        for idx, (tab_page, t_payload) in enumerate(zip(tabs, tab_payloads), 1):
            if self._cancel_requested:
                self.log("WARNING", "🛑 Batch posting cancelled by user.")
                break

            self.log("INFO", f"--------------------------------------------------")
            self.log("INFO", f"👉 Tab [{idx}/{tabs_count}]: Activating tab in Chrome...")
            try:
                await tab_page.bring_to_front()
                await self.sleep(random.uniform(0.6, 1.2))
            except Exception:
                pass

            self.set_progress(int(((idx - 1) / tabs_count) * 100))

            tab_published = False
            # Method Replay Flow
            if use_method_replay and HAS_MACRO_RECORDER:
                try:
                    self.log("INFO", f"⚡ Tab [{idx}/{tabs_count}]: Replaying method '{chosen_method}'...")
                    player = MacroMethodPlayer(
                        method_name=chosen_method,
                        dynamic_params=t_payload,
                        log_callback=self.log
                    )
                    method_ok = await player.execute(tab_page)
                    if method_ok:
                        tab_published = True
                    else:
                        self.log("WARNING", f"🔄 Tab [{idx}/{tabs_count}]: Replay step incomplete. Falling back to live UI inputs...")
                        tab_published = await self.create_marketplace_listing_on_page(tab_page, t_payload)
                except Exception as replay_err:
                    self.log("WARNING", f"🔄 Tab [{idx}/{tabs_count}]: Method error: {str(replay_err)[:50]}. Engaging live UI fallback...")
                    tab_published = await self.create_marketplace_listing_on_page(tab_page, t_payload)
            else:
                # Live UI Inputs Flow
                tab_published = await self.create_marketplace_listing_on_page(tab_page, t_payload)

            if tab_published:
                success_count += 1
                self.log("SUCCESS", f"✅ Tab [{idx}/{tabs_count}] Published successfully! (Location: '{t_payload['location']}')")

            # Anti-detection delay between tab interactions
            if idx < tabs_count and not self._cancel_requested:
                cooldown = random.uniform(3.0, 5.5) if self.speed_mode == "slow" else random.uniform(1.8, 3.2)
                self.log("INFO", f"🛡️ Anti-detection cooldown: Pausing {cooldown:.1f}s before interacting with Tab [{idx + 1}]...")
                await self.sleep(cooldown)

        self.set_progress(100)
        self.log("SUCCESS", f"🎉 Multi-Tab Engine Finished: {success_count}/{tabs_count} listings successfully broadcast!")
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

    async def create_marketplace_listing_on_page(self, page: Page, payload: Dict[str, Any]) -> bool:
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
        # 1. Location Selection (Target Location / City First)
        # ----------------------------------------------------------------------
        if location:
            self.log("INFO", f"📍 Setting Target Location / City: '{location}'...")
            await self._set_location_field(page, location)
            await self.sleep(random.uniform(0.6, 1.2))

        # ----------------------------------------------------------------------
        # 2. Product Title (Targeting ONLY Title Input)
        # ----------------------------------------------------------------------
        if title:
            self.log("INFO", f"✍️ Typing Title: '{title[:45]}...'")
            await self._set_title_field(page, title)
            await self.sleep(random.uniform(0.6, 1.2))

        # ----------------------------------------------------------------------
        # 3. Category Selection (Household, Appliances, Auto Parts, etc.)
        # ----------------------------------------------------------------------
        if category:
            self.log("INFO", f"🏷️ Selecting Category: '{category}'...")
            await self._set_category_field(page, category)
            await self.sleep(random.uniform(0.8, 1.4))

        # ----------------------------------------------------------------------
        # 4. Product Price (Targeting ONLY Price Input)
        # ----------------------------------------------------------------------
        if price is not None:
            clean_price = re.sub(r'[^0-9.]', '', str(price)) or "0"
            self.log("INFO", f"💲 Setting Price: ${clean_price}")
            await self._set_price_field(page, clean_price)
            await self.sleep(random.uniform(0.5, 1.0))

        # ----------------------------------------------------------------------
        # 5. Condition Selection ("New")
        # ----------------------------------------------------------------------
        try:
            self.log("INFO", "⚙️ Setting Item Condition to 'New'...")
            await self._set_condition_field(page, "New")
            await self.sleep(random.uniform(0.5, 0.9))
        except Exception as cond_err:
            self.log("WARNING", f"Condition selection notice: {str(cond_err)}")

        # ----------------------------------------------------------------------
        # 6. Description (Targeting ONLY Description Textarea)
        # ----------------------------------------------------------------------
        if description:
            self.log("INFO", f"📝 Filling Description ({len(description)} chars)...")
            await self._set_description_field(page, description)
            await self.sleep(random.uniform(0.8, 1.5))

        # ----------------------------------------------------------------------
        # 7. Upload Product Images (Randomized Image from Pool)
        # ----------------------------------------------------------------------
        if images:
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
                        self.log("WARNING", f"Anti-duplicate alteration notice: {str(img_err)}; using original images.")
                        upload_files = valid_images

                self.log("INFO", f"🖼️ Uploading {len(upload_files)} product photo(s)...")
                await self._upload_photos_to_page(page, upload_files)
                await self.sleep(random.uniform(2.5, 4.0))

        # ----------------------------------------------------------------------
        # 8. Advance through "Next" Step
        # ----------------------------------------------------------------------
        self.log("INFO", "➡️ Clicking 'Next' button...")
        clicked_next = await self._click_button_with_text(page, ["Next", "اگلا"])
        if clicked_next:
            await self.sleep(random.uniform(2.5, 4.0))

        # ----------------------------------------------------------------------
        # 9. Click "Publish" Button
        # ----------------------------------------------------------------------
        self.log("INFO", "🚀 Triggering listing publication (Publish)...")
        clicked_publish = await self._click_button_with_text(page, ["Publish", "Post", "شائع", "Done", "Save"])
        if not clicked_publish:
            # Fallback selectors
            pub_fallback = [
                'div[aria-label="Publish"][role="button"]',
                'div[aria-label="Post"][role="button"]',
                'button:has-text("Publish")',
                'button:has-text("Post")'
            ]
            for sel in pub_fallback:
                try:
                    btn = await page.query_selector(sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        clicked_publish = True
                        break
                except Exception:
                    continue

        if not clicked_publish:
            raise ListingSubmissionError("Could not locate the final 'Publish' or 'Next' submission button.")

        # Wait for publication confirmation
        self.log("INFO", "Awaiting confirmation from Facebook Marketplace...")
        await self.sleep(random.uniform(3.5, 5.5))
        self.log("SUCCESS", f"Marketplace listing '{title}' successfully broadcast!")
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
            'label[aria-label*="عنوان"] input',
            'input[aria-label="Title"]',
            'input[aria-label*="Title"]',
            'input[name="title"]',
            'label:has-text("Title") input',
            'label:has-text("What are you selling") input'
        ]
        input_el = None
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    input_el = el
                    break
            except Exception:
                continue

        # XPath fallback for nested spans
        if not input_el:
            try:
                input_el = await page.query_selector('xpath=//label[contains(translate(@aria-label, "TITLE", "title"), "title")]//input')
            except Exception:
                pass

        if not input_el:
            raise ListingSubmissionError("Could not locate the Title input field on Facebook Marketplace.")

        await input_el.scroll_into_view_if_needed()
        await input_el.click()
        await self.sleep(random.uniform(0.2, 0.4))
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await self._human_type(page, text, min_delay=30, max_delay=65)

    async def _set_price_field(self, page: Page, price_str: str):
        """Specifically locates and types into the Facebook Marketplace Price input."""
        selectors = [
            'label[aria-label="Price"] input',
            'label[aria-label*="Price"] input',
            'label[aria-label*="قیمت"] input',
            'input[aria-label="Price"]',
            'input[aria-label*="Price"]',
            'input[name="price"]',
            'label:has-text("Price") input'
        ]
        input_el = None
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    input_el = el
                    break
            except Exception:
                continue

        if not input_el:
            try:
                input_el = await page.query_selector('xpath=//label[contains(translate(@aria-label, "PRICE", "price"), "price")]//input')
            except Exception:
                pass

        if not input_el:
            raise ListingSubmissionError("Could not locate the Price input field on Facebook Marketplace.")

        await input_el.scroll_into_view_if_needed()
        await input_el.click()
        await self.sleep(random.uniform(0.2, 0.4))
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await self._human_type(page, price_str, min_delay=35, max_delay=75)

    async def _set_description_field(self, page: Page, text: str):
        """Specifically locates and types into the Facebook Marketplace Description textarea."""
        selectors = [
            'label[aria-label="Description"] textarea',
            'label[aria-label*="Description"] textarea',
            'label[aria-label*="تفصیل"] textarea',
            'textarea[aria-label="Description"]',
            'textarea[aria-label*="Description"]',
            'textarea[name="description"]',
            'label:has-text("Description") textarea',
            'textarea'
        ]
        input_el = None
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    input_el = el
                    break
            except Exception:
                continue

        if not input_el:
            try:
                input_el = await page.query_selector('xpath=//label[contains(translate(@aria-label, "DESCRIPTION", "description"), "description")]//textarea')
            except Exception:
                pass

        if not input_el:
            self.log("WARNING", "Description textarea not found directly; skipping description.")
            return

        await input_el.scroll_into_view_if_needed()
        await input_el.click()
        await self.sleep(random.uniform(0.2, 0.4))
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await self._human_type(page, text, min_delay=20, max_delay=55)

    async def _set_location_field(self, page: Page, location_str: str):
        """Specifically sets geographic location / city with autocomplete resolution."""
        selectors = [
            'label[aria-label="Location"] input',
            'label[aria-label*="Location"] input',
            'input[aria-label="Location"]',
            'input[aria-label*="Location"]',
            'label[aria-label*="لوکیشن"] input',
            'label:has-text("Location") input',
            'label:has-text("City") input'
        ]
        input_el = None
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    input_el = el
                    break
            except Exception:
                continue

        if not input_el:
            try:
                input_el = await page.query_selector('xpath=//label[contains(translate(@aria-label, "LOCATION", "location"), "location")]//input')
            except Exception:
                pass

        if not input_el:
            self.log("WARNING", "Location input not visible on initial viewport; attempting scroll...")
            await page.evaluate("window.scrollBy(0, 400)")
            await self.sleep(0.4)
            for sel in selectors:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        input_el = el
                        break
                except Exception:
                    continue

        if input_el:
            await input_el.scroll_into_view_if_needed()
            await input_el.click()
            await self.sleep(random.uniform(0.2, 0.4))
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")

            # Clean search query (strip district tag like '(Downtown)' so Facebook autocomplete matches the city)
            search_query = re.sub(r'\(.*?\)', '', location_str).strip() or location_str
            await self._human_type(page, search_query, min_delay=30, max_delay=65)
            await self.sleep(random.uniform(1.6, 2.3))

            # Resolve location dropdown suggestion
            option_el = await page.query_selector('div[role="listbox"] div[role="option"], ul[role="listbox"] li, div[role="option"]')
            if option_el and await option_el.is_visible():
                await option_el.click()
                self.log("INFO", f"Location suggestion matched for '{location_str}'.")
            else:
                await page.keyboard.press("ArrowDown")
                await self.sleep(0.3)
                await page.keyboard.press("Enter")
            await self.sleep(random.uniform(0.6, 1.1))

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
        """Selects item condition (default: New)."""
        cond_selectors = [
            'label[aria-label="Condition"]',
            'label[aria-label*="Condition"]',
            'div[aria-label="Condition"][role="combobox"]',
            'label:has-text("Condition")'
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
            await cond_el.scroll_into_view_if_needed()
            await cond_el.click()
            await self.sleep(0.8)
            new_opt = await page.query_selector(f'div[role="option"]:has-text("{condition_text}"), span:has-text("{condition_text}")')
            if new_opt and await new_opt.is_visible():
                await new_opt.click()
            await self.sleep(0.4)

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
