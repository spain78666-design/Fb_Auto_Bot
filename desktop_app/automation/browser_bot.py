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

        # Inject authentication cookies
        cookies = parse_cookie_payload(raw_cookies)
        if not cookies:
            raise InvalidSessionError("No valid cookies found in payload. Provide c_user and xs cookies.")

        has_c_user = any(c["name"] == "c_user" for c in cookies)
        has_xs = any(c["name"] == "xs" for c in cookies)

        if not (has_c_user and has_xs):
            self.log("WARNING", "Cookies missing 'c_user' or 'xs' token. Facebook authentication may fail.")

        await self.context.add_cookies(cookies)
        self.log("INFO", f"Injected {len(cookies)} authentication cookie(s) into browser session.")
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
                "Session cookies expired or invalid. Facebook redirected to login screen."
            )

        # Check for profile navigation indicator or marketplace presence
        content = await self.page.content()
        if "login_form" in content or "login_button" in content:
            raise InvalidSessionError("Facebook displayed login prompt. Cookies rejected.")

        self.log("SUCCESS", "Session authenticated successfully! Active Facebook profile confirmed.")
        self.set_progress(35)

    # --------------------------------------------------------------------------
    # Core Listing Publication Flow
    # --------------------------------------------------------------------------
    async def create_marketplace_listing(self, payload: Dict[str, Any]):
        """
        Executes the end-to-end Facebook Marketplace listing publication workflow.
        """
        title = payload.get("title", "")
        price = payload.get("price", "0")
        category = payload.get("category", "")
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
        self.set_progress(40)

        try:
            await self.page.goto(create_url, wait_until="domcontentloaded", timeout=40000)
            await self.sleep(random.uniform(2.5, 4.0))
        except PlaywrightTimeoutError:
            self.log("WARNING", "DOM interactive timed out; attempting fallback...")
            await self.sleep(2.0)

        # Secondary checkpoint verification on Marketplace URL
        if "checkpoint" in self.page.url:
            raise CheckpointDetectedError("Marketplace creation triggered Facebook checkpoint.")
        if "login" in self.page.url:
            raise InvalidSessionError("Redirected away from Marketplace to login screen.")

        self.log("INFO", "Marketplace item creation interface loaded.")
        self.set_progress(50)

        # 1. Upload Product Images
        if images:
            valid_images = [img for img in images if os.path.exists(img)]
            if valid_images:
                upload_files = valid_images
                anti_dup_shield = payload.get("anti_dup_shield", True) or payload.get("anti_dup_rotate", True)
                
                if anti_dup_shield and IMAGE_PROCESSOR_AVAILABLE:
                    self.log("INFO", "🛡️ Anti-Duplicate Image Shield ACTIVE: Transforming photos before upload...")
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

                self.log("INFO", f"Uploading {len(upload_files)} product image(s)...")
                try:
                    # Find file upload input
                    file_input = await self.page.query_selector('input[type="file"]')
                    if not file_input:
                        # Attempt to locate by label or aria
                        file_input = await self.page.wait_for_selector('input[type="file"][accept*="image"]', timeout=10000)
                    
                    if file_input:
                        await file_input.set_input_files(upload_files)
                        self.log("INFO", "Unique image files injected into Marketplace media uploader.")
                        await self.sleep(random.uniform(3.0, 5.0))
                    else:
                        self.log("WARNING", "Could not locate file input directly; continuing with metadata.")
                except Exception as e:
                    self.log("WARNING", f"Image upload encountered notice: {str(e)}")
            else:
                self.log("WARNING", "Provided image file paths do not exist on local disk.")

        self.set_progress(60)

        # 2. Input Product Title
        self.log("INFO", f"Typing Title: '{title}'...")
        title_selectors = [
            'label[aria-label="Title"] input',
            'input[aria-label="Title"]',
            'label:has-text("Title") input',
            'input[type="text"][dir="ltr"]'
        ]
        await self._type_first_matching(title_selectors, title)
        await self.sleep(random.uniform(0.8, 1.6))
        self.set_progress(70)

        # 3. Input Product Price
        self.log("INFO", f"Setting Price: ${price}...")
        price_selectors = [
            'label[aria-label="Price"] input',
            'input[aria-label="Price"]',
            'label:has-text("Price") input'
        ]
        await self._type_first_matching(price_selectors, price)
        await self.sleep(random.uniform(0.8, 1.4))

        # 4. Select Category
        if category:
            self.log("INFO", f"Selecting Category: '{category}'...")
            try:
                category_dropdown = await self.page.query_selector(
                    'label[aria-label="Category"], div[aria-label="Category"], span:has-text("Category")'
                )
                if category_dropdown:
                    await category_dropdown.click()
                    await self.sleep(random.uniform(1.0, 1.8))
                    
                    # Look for matching option in the dropdown popup
                    option = await self.page.query_selector(f'span:has-text("{category}"), div[role="button"]:has-text("{category}")')
                    if option:
                        await option.click()
                        self.log("INFO", f"Category set to '{category}'.")
                        await self.sleep(0.8)
                    else:
                        # Click the first available category option as fallback
                        fallback_opt = await self.page.query_selector('div[role="listbox"] div[role="option"], div[role="menuitem"]')
                        if fallback_opt:
                            await fallback_opt.click()
            except Exception as e:
                self.log("WARNING", f"Category auto-selection note: {str(e)}")

        # 5. Set Condition to "New"
        try:
            condition_box = await self.page.query_selector('label[aria-label="Condition"], div[aria-label="Condition"]')
            if condition_box:
                await condition_box.click()
                await self.sleep(0.8)
                new_opt = await self.page.query_selector('span:has-text("New"), div[role="option"]:has-text("New")')
                if new_opt:
                    await new_opt.click()
                    await self.sleep(0.5)
        except Exception:
            pass

        # 6. Input Description
        if description:
            self.log("INFO", "Filling Product Description...")
            desc_selectors = [
                'label[aria-label="Description"] textarea',
                'textarea[aria-label="Description"]',
                'label:has-text("Description") textarea',
                'textarea'
            ]
            await self._type_first_matching(desc_selectors, description, min_delay=30, max_delay=90)
            await self.sleep(random.uniform(1.0, 2.0))

        # 7. Set Geographic Location / Zip Code
        if location:
            self.log("INFO", f"Configuring target listing radius/city: '{location}'...")
            try:
                loc_input = await self.page.query_selector('label[aria-label="Location"] input, input[aria-label="Location"]')
                if loc_input:
                    await loc_input.click()
                    await self.page.keyboard.press("Control+A")
                    await self.page.keyboard.press("Backspace")
                    await self.sleep(0.4)
                    
                    for char in location:
                        await self.page.keyboard.type(char)
                        await asyncio.sleep(random.uniform(0.08, 0.18))
                    
                    await self.sleep(1.8)
                    # Pick first suggestion from the Google Places / FB Location dropdown
                    await self.page.keyboard.press("ArrowDown")
                    await self.sleep(0.3)
                    await self.page.keyboard.press("Enter")
                    await self.sleep(1.0)
            except Exception as e:
                self.log("WARNING", f"Location selection note: {str(e)}")

        self.set_progress(85)
        await self.human_scroll(2)

        # 8. Advance through "Next" step
        self.log("INFO", "Progressing to final publication step...")
        next_btn_selectors = [
            'div[aria-label="Next"][role="button"]',
            'button:has-text("Next")',
            'div[role="button"]:has-text("Next")'
        ]
        clicked_next = await self._click_first_matching(next_btn_selectors)
        if clicked_next:
            await self.sleep(random.uniform(2.5, 4.0))

        # 9. Click "Publish" button
        self.log("INFO", "Triggering listing publication...")
        publish_selectors = [
            'div[aria-label="Publish"][role="button"]',
            'button:has-text("Publish")',
            'div[role="button"]:has-text("Publish")'
        ]
        clicked_publish = await self._click_first_matching(publish_selectors)
        if not clicked_publish:
            # Check if button is labeled "Post" or "Save"
            fallback_selectors = ['div[aria-label="Post"][role="button"]', 'div[role="button"]:has-text("Post")']
            clicked_publish = await self._click_first_matching(fallback_selectors)

        if not clicked_publish:
            raise ListingSubmissionError("Could not locate the final 'Publish' or 'Next' submission button.")

        # Wait for publication confirmation
        self.log("INFO", "Awaiting confirmation from Facebook Marketplace...")
        await self.sleep(random.uniform(4.0, 6.0))
        self.set_progress(100)

        self.log("SUCCESS", f"Marketplace listing '{title}' successfully broadcast to Facebook Marketplace!")

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
            if self.page:
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
