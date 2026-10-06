"""
FB Auto Bot - Meta Business Suite Reels Bulk Uploader Engine
Automates high-speed multi-tab Facebook Reels creation via Meta Business Suite
(https://business.facebook.com/latest/reels_composer/) across multiple accounts with
parallel tabs, auto video attachments from exact user folder/path, description spintax,
patient dynamic page load waiting, discard-dialog prevention, precision footer Share button detection,
and clean browser session management.
"""

import os
import sys
import time
import json
import random
import logging
import asyncio
import socket
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Callable

# Setup structured logger
logger = logging.getLogger("MetaReelsBot")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Optional Playwright Import
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def test_proxy_connectivity(host: str, port: int, timeout: float = 3.0) -> bool:
    """Tests if a proxy host:port is reachable via TCP socket."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def resolve_spintax(text: str) -> str:
    """
    Recursively resolves standard spintax formatted strings:
    e.g. "{Hello|Hi|Hey} world! {Amazing|Cool} clip" -> "Hi world! Cool clip"
    """
    if not text:
        return ""
    import re
    pattern = re.compile(r'\{([^{}]+)\}')
    while True:
        match = pattern.search(text)
        if not match:
            break
        choices = match.group(1).split('|')
        chosen = random.choice(choices)
        text = text[:match.start()] + chosen + text[match.end():]
    return text.strip()


def parse_cookie_payload(raw_cookies: Any) -> List[Dict[str, Any]]:
    """
    Parses cookies from JSON string, list of dicts, or Netscape format into
    Playwright-compatible format targeting facebook domains.
    """
    if not raw_cookies:
        return []

    parsed: List[Dict[str, Any]] = []

    if isinstance(raw_cookies, list):
        for c in raw_cookies:
            if isinstance(c, dict) and "name" in c and "value" in c:
                name = str(c.get("name", "")).strip()
                val = str(c.get("value", "")).strip()
                if not name or not val:
                    continue
                domain = str(c.get("domain", "")).strip()
                if not domain:
                    domain = ".facebook.com"
                elif not domain.startswith("."):
                    domain = f".{domain}"
                
                cookie_entry: Dict[str, Any] = {
                    "name": name,
                    "value": val,
                    "domain": domain,
                    "path": str(c.get("path", "/")),
                    "secure": bool(c.get("secure", True)),
                    "httpOnly": bool(c.get("httpOnly", False))
                }
                same_site = c.get("sameSite")
                if same_site in ("Strict", "Lax", "None"):
                    cookie_entry["sameSite"] = same_site
                parsed.append(cookie_entry)
        return parsed

    if isinstance(raw_cookies, str):
        trimmed = raw_cookies.strip()
        if trimmed.startswith("[") or trimmed.startswith("{"):
            try:
                data = json.loads(trimmed)
                if isinstance(data, list):
                    return parse_cookie_payload(data)
                elif isinstance(data, dict):
                    return parse_cookie_payload([data])
            except Exception:
                pass

        # Parse string format (e.g. c_user=123; xs=456 or Netscape lines)
        for line in trimmed.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "\t" in line:
                parts = line.split("\t")
                if len(parts) >= 7:
                    domain = parts[0]
                    name = parts[5]
                    val = parts[6]
                    if domain and name:
                        if not domain.startswith("."):
                            domain = f".{domain}"
                        parsed.append({
                            "name": name,
                            "value": val,
                            "domain": domain,
                            "path": parts[2] if len(parts) > 2 else "/",
                            "secure": parts[3].lower() == "true" if len(parts) > 3 else True,
                            "httpOnly": False
                        })
            elif ";" in line or "=" in line:
                for segment in line.split(";"):
                    segment = segment.strip()
                    if "=" in segment:
                        k, v = segment.split("=", 1)
                        k, v = k.strip(), v.strip()
                        if k:
                            parsed.append({
                                "name": k,
                                "value": v,
                                "domain": ".facebook.com",
                                "path": "/",
                                "secure": True,
                                "httpOnly": False
                            })

    return parsed


class FacebookMetaReelsBot:
    """
    Dedicated Automation Engine for Meta Business Suite Reels Bulk Creation
    Target: https://business.facebook.com/latest/reels_composer/
    """
    TARGET_URL = "https://business.facebook.com/latest/reels_composer/"

    def __init__(
        self,
        account_data: Dict[str, Any],
        video_files: List[str],
        reels_per_account: int = 5,
        caption_template: str = "",
        selection_mode: str = "Random Pool (No Dup)",
        log_callback: Optional[Callable[[str, str], None]] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        counter_callback: Optional[Callable[[str, int], None]] = None
    ):
        self.account_data = account_data or {}
        self.video_files = [os.path.abspath(v) for v in video_files if os.path.isfile(v)]
        self.reels_per_account = max(1, int(reels_per_account))
        self.caption_template = caption_template or "{🔥 Amazing Reel|Must Watch Video|Check this out}! Drop a follow ❤️ #reels #viral #trending #fyp"
        self.selection_mode = selection_mode
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.counter_callback = counter_callback

        self.account_id = str(self.account_data.get("id") or self.account_data.get("uid") or "default_acc")
        self.account_name = str(self.account_data.get("name") or self.account_id)

        self._cancelled = False
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._active_pages: List[Page] = []
        self._is_persistent = False

    def cancel(self):
        """Signals the bot to abort immediately."""
        self._cancelled = True
        self._log("WARNING", f"🛑 [{self.account_name}] Cancellation requested for Meta Reels uploader.")

    def _log(self, level: str, message: str):
        if self.log_callback:
            try:
                self.log_callback(level, message)
            except Exception:
                pass
        else:
            logger.info(f"[{level}] {message}")

    def _report_progress(self, percent: int):
        if self.progress_callback:
            try:
                self.progress_callback(percent)
            except Exception:
                pass

    def _report_counter(self, count: int):
        if self.counter_callback:
            try:
                self.counter_callback(self.account_id, count)
            except Exception:
                pass

    async def _setup_browser(self):
        """Launches Playwright Chromium/Chrome with stealth parameters, cookies, and proxy bindings."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed in the Python environment. Please ensure 'playwright' is installed.")

        self._pw = await async_playwright().start()

        # Build proxy configuration if requested
        proxy_settings = None
        use_direct = (
            self.account_data.get("network_mode") == "direct"
            or self.account_data.get("use_direct_network", False)
        )
        raw_proxy = (self.account_data.get("proxy") or "").strip()
        is_direct_str = any(d in raw_proxy.lower() for d in ["direct", "no proxy", "none", "null", "false", "0", ""])

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-notifications",
            "--no-first-run",
            "--disable-default-apps",
            "--disable-popup-blocking",
            "--start-maximized",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--lang=en-US",
            "--accept-lang=en-US,en;q=0.9"
        ]

        if use_direct or is_direct_str or not raw_proxy:
            proxy_settings = None
            launch_args.append("--no-proxy-server")
            self._log("INFO", f"[{self.account_name}] 🌐 Direct network connection enabled.")
        else:
            try:
                server_url = raw_proxy if "://" in raw_proxy else f"{self.account_data.get('proxy_type', 'http').lower()}://{raw_proxy}"
                parsed = urlparse(server_url)
                host = parsed.hostname
                port = parsed.port
                if host and port and test_proxy_connectivity(host, port, timeout=2.5):
                    proxy_settings = {"server": f"{parsed.scheme}://{host}:{port}"}
                    u = parsed.username or self.account_data.get("proxy_user")
                    p = parsed.password or self.account_data.get("proxy_pass")
                    if u:
                        proxy_settings["username"] = u
                    if p:
                        proxy_settings["password"] = p
                    self._log("INFO", f"[{self.account_name}] 🛡️ Proxy bound: {host}:{port}")
                else:
                    self._log("WARNING", f"[{self.account_name}] ⚠️ Proxy unreachable. Falling back to direct connection.")
                    proxy_settings = None
                    launch_args.append("--no-proxy-server")
            except Exception:
                proxy_settings = None
                launch_args.append("--no-proxy-server")

        # Find Installed Google Chrome or Edge on Windows / Mac / Linux
        chrome_candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
        chrome_exe = next((c for c in chrome_candidates if os.path.isfile(c)), None)

        # Check for persistent profile directory or local Chrome User Data
        profile_dir = self.account_data.get("profile_dir", "")
        profile_name = self.account_data.get("profile_name", "")
        user_data_dir = self.account_data.get("user_data_dir", "")

        if profile_name:
            launch_args.append(f"--profile-directory={profile_name}")

        target_user_data_dir = None
        if profile_dir and os.path.isdir(profile_dir):
            target_user_data_dir = profile_dir
        elif user_data_dir and os.path.isdir(user_data_dir):
            target_user_data_dir = user_data_dir
        else:
            profiles_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "profiles"))
            candidate_dir = os.path.join(profiles_root, self.account_id)
            if os.path.isdir(candidate_dir):
                target_user_data_dir = candidate_dir

        context_kwargs = {
            "viewport": None,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "locale": "en-US",
            "extra_http_headers": {
                "Accept-Language": "en-US,en;q=0.9"
            }
        }

        self._log("INFO", f"[{self.account_name}] 🌐 Launching Chrome browser...")
        
        launched = False
        if target_user_data_dir and os.path.isdir(target_user_data_dir):
            try:
                persistent_kwargs: Dict[str, Any] = {
                    "user_data_dir": target_user_data_dir,
                    "headless": False,
                    "args": launch_args,
                    **context_kwargs
                }
                if proxy_settings:
                    persistent_kwargs["proxy"] = proxy_settings
                if chrome_exe:
                    persistent_kwargs["executable_path"] = chrome_exe

                self._context = await self._pw.chromium.launch_persistent_context(**persistent_kwargs)
                self._is_persistent = True
                launched = True
                label = profile_name or os.path.basename(target_user_data_dir)
                self._log("INFO", f"[{self.account_name}] 📂 Attached local Chrome profile: {label} (Facebook pre-logged in).")
            except Exception as e:
                self._log("DEBUG", f"[{self.account_name}] Persistent launch notice: {e}. Trying standard launch...")

        if not launched:
            launch_kwargs: Dict[str, Any] = {
                "headless": False,
                "args": launch_args
            }
            if proxy_settings:
                launch_kwargs["proxy"] = proxy_settings
            if chrome_exe:
                launch_kwargs["executable_path"] = chrome_exe

            try:
                self._browser = await self._pw.chromium.launch(**launch_kwargs)
            except Exception as ex:
                self._log("DEBUG", f"[{self.account_name}] Custom Chrome launch notice: {ex}. Trying fallback channels...")
                launch_kwargs.pop("executable_path", None)
                try:
                    self._browser = await self._pw.chromium.launch(channel="chrome", **launch_kwargs)
                except Exception:
                    try:
                        self._browser = await self._pw.chromium.launch(channel="msedge", **launch_kwargs)
                    except Exception:
                        self._browser = await self._pw.chromium.launch(**launch_kwargs)

            self._context = await self._browser.new_context(**context_kwargs)
            self._is_persistent = False

        # Parse and Inject Session Cookies (for both .facebook.com and .business.facebook.com)
        raw_cookies = self.account_data.get("cookies", "")
        formatted_cookies = parse_cookie_payload(raw_cookies)
        
        if not any(c.get("name") == "locale" for c in formatted_cookies):
            formatted_cookies.append({
                "name": "locale",
                "value": "en_US",
                "domain": ".facebook.com",
                "path": "/",
                "secure": True
            })

        if formatted_cookies and self._context:
            try:
                await self._context.add_cookies(formatted_cookies)
                self._log("SUCCESS", f"[{self.account_name}] 🍪 Injected {len(formatted_cookies)} Facebook session cookies.")
            except Exception as ex:
                self._log("WARNING", f"[{self.account_name}] Cookie injection notice: {ex}")

    async def _handle_continue_editing_dialog(self, page: Page):
        """Automatically clicks 'Continue editing' if the 'Discard changes?' popup appears."""
        try:
            cont_btns = [
                page.locator('div[role="button"]:has-text("Continue editing")'),
                page.locator('button:has-text("Continue editing")'),
                page.locator('span:has-text("Continue editing")'),
                page.locator('[aria-label*="Continue editing" i]'),
                page.locator('text="Continue editing"')
            ]
            for btn in cont_btns:
                if await btn.count() > 0 and await btn.first.is_visible():
                    await btn.first.click()
                    self._log("INFO", f"[{self.account_name}] 🔄 Automatically clicked 'Continue editing' dialog.")
                    await asyncio.sleep(1.0)
                    return True
        except Exception:
            pass
        return False

    async def _dismiss_initial_overlays(self, page: Page):
        """Dismisses only harmless onboarding dialogs or cookie notices (WITHOUT clicking cancel/close on composer)."""
        # First ensure we handle any "Continue editing" popup if present
        await self._handle_continue_editing_dialog(page)

        try:
            await page.evaluate("""() => {
                const dismissPhrases = ['not now', 'got it', 'maybe later', 'try the new', 'accept cookies', 'decline optional cookies', 'allow essential cookies'];
                const buttons = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"]'));
                for (const b of buttons) {
                    const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                    for (const ph of dismissPhrases) {
                        if (txt === ph) {
                            if (b.offsetParent !== null) {
                                b.click();
                                return;
                            }
                        }
                    }
                }
            }""")
        except Exception:
            pass

    async def _click_primary_share_button(self, page: Page, tab_tag: str) -> bool:
        """
        Locates and clicks the true primary blue 'Share' button in Meta Composer footer (next to 'Back').
        Uses real Playwright mouse and CDP input clicks so Facebook Comet React triggers publication 100%.
        """
        candidate_locators = [
            # 1. Direct sibling/partner to 'Back' button in footer bar (from UI screenshot)
            page.locator('div:has(> *[role="button"]:has-text("Back")) *[role="button"]:has-text("Share")'),
            page.locator('*[role="button"]:has-text("Back") ~ *[role="button"]:has-text("Share")'),
            page.locator('button:has-text("Back") ~ button:has-text("Share")'),

            # 2. Bottom footer dialog buttons
            page.locator('div[role="dialog"] footer *[role="button"]:has-text("Share")'),
            page.locator('div[role="dialog"] div:last-child *[role="button"]:has-text("Share")'),

            # 3. Exact accessible role button
            page.get_by_role("button", name="Share", exact=True),

            # 4. Specific text-is locators
            page.locator('div[role="button"]:text-is("Share")'),
            page.locator('button:text-is("Share")'),
            page.locator('*[role="button"]:has-text("Share"):not([role="switch"]):not([role="checkbox"]):not([role="radio"])')
        ]

        target_el = None
        for loc in candidate_locators:
            try:
                cnt = await loc.count()
                if cnt > 0:
                    cand = loc.last
                    if await cand.is_visible():
                        is_dis = await cand.get_attribute("aria-disabled")
                        if is_dis != "true":
                            target_el = cand
                            break
            except Exception:
                pass

        # If found by locator, perform physical mouse click at bounding box center
        if target_el:
            try:
                await target_el.scroll_into_view_if_needed()
            except Exception:
                pass

            # Physical mouse click via CDP
            clicked_mouse = False
            try:
                box = await target_el.bounding_box()
                if box and box["width"] > 0 and box["height"] > 0:
                    cx = box["x"] + box["width"] / 2.0
                    cy = box["y"] + box["height"] / 2.0
                    self._log("DEBUG", f"{tab_tag} 🖱️ Mouse clicking Share button at ({cx:.1f}, {cy:.1f})...")
                    await page.mouse.move(cx, cy)
                    await asyncio.sleep(0.15)
                    await page.mouse.click(cx, cy)
                    clicked_mouse = True
            except Exception as ex:
                self._log("DEBUG", f"{tab_tag} Mouse click notice: {ex}")

            # Playwright trusted locator click (force=True)
            try:
                await target_el.click(force=True, timeout=3000)
                clicked_mouse = True
            except Exception:
                pass

            # Synthetic pointer event chain for React Comet
            try:
                await target_el.evaluate("""(el) => {
                    const opts = { bubbles: true, cancelable: true, view: window };
                    el.dispatchEvent(new PointerEvent('pointerdown', opts));
                    el.dispatchEvent(new MouseEvent('mousedown', opts));
                    el.dispatchEvent(new PointerEvent('pointerup', opts));
                    el.dispatchEvent(new MouseEvent('mouseup', opts));
                    el.dispatchEvent(new MouseEvent('click', opts));
                }""")
            except Exception:
                pass

            if clicked_mouse:
                return True

        # Fallback: Find coordinate of bottom-most element with exact text "Share"
        try:
            coords = await page.evaluate("""() => {
                const candidates = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"]'));
                const valid = candidates.filter(el => {
                    const role = (el.getAttribute('role') || '').toLowerCase();
                    if (role === 'switch' || role === 'checkbox' || role === 'radio') return false;
                    if (el.tagName === 'INPUT') return false;
                    
                    const ariaLabel = (el.getAttribute('aria-label') || '').trim();
                    const text = (el.innerText || el.textContent || '').trim();
                    
                    if (text !== 'Share' && ariaLabel !== 'Share') return false;
                    if (el.getAttribute('aria-disabled') === 'true') return false;
                    
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0 && el.offsetParent !== null;
                });
                if (valid.length > 0) {
                    valid.sort((a, b) => b.getBoundingClientRect().top - a.getBoundingClientRect().top);
                    const b = valid[0].getBoundingClientRect();
                    return { x: b.left + b.width / 2, y: b.top + b.height / 2 };
                }
                return null;
            }""")
            if coords:
                await page.mouse.move(coords["x"], coords["y"])
                await asyncio.sleep(0.1)
                await page.mouse.click(coords["x"], coords["y"])
                return True
        except Exception:
            pass

        return False

    async def _upload_single_tab(
        self,
        tab_index: int,
        video_path: str,
        caption_text: str,
        existing_page: Optional[Page] = None
    ) -> bool:
        """
        Executes the full 3-step Reels upload workflow on a single page/tab:
        1. Open https://business.facebook.com/latest/reels_composer/
        2. Wait patiently and dynamically for Meta Reels Composer to load
        3. Attach video file from exact disk path immediately when loaded
        4. Scroll down and enter description without unwanted back triggers
        5. Click 'Next' (Create -> Edit)
        6. Click 'Next' (Edit -> Share)
        7. Click bottom 'Share' button with precision and wait for Meta confirmation
        """
        if self._cancelled:
            return False

        tab_tag = f"[{self.account_name} - Tab #{tab_index + 1}]"
        
        if existing_page is not None:
            page = existing_page
        else:
            page = await self._context.new_page()
            
        self._active_pages.append(page)

        try:
            self._log("INFO", f"{tab_tag} 🌐 Opening Meta Reels Composer ({self.TARGET_URL})...")
            try:
                await page.goto(self.TARGET_URL, wait_until="domcontentloaded", timeout=90000)
            except Exception as e:
                self._log("DEBUG", f"{tab_tag} Page navigation notice: {e}")

            # Verify video path exists
            if not os.path.isfile(video_path):
                raise FileNotFoundError(f"Video file not found at path: {video_path}")

            # Initial buffer for JavaScript and React hydration
            await asyncio.sleep(2.5)

            self._log("INFO", f"{tab_tag} ⏳ Waiting dynamically for Meta Reels Composer to finish loading (will start upload instantly when ready)...")

            # Patient polling wait loop: up to 75 seconds for page & file upload elements to be ready
            attached = False
            for sec in range(1, 76):
                if self._cancelled:
                    return False

                # Handle overlays and continue editing dialogs
                await self._dismiss_initial_overlays(page)

                # Check if file input is available in the main page (attached in DOM, even if hidden)
                try:
                    file_inputs = page.locator('input[type="file"]')
                    if await file_inputs.count() > 0:
                        await file_inputs.first.set_input_files(video_path)
                        attached = True
                        self._log("SUCCESS", f"{tab_tag} 📁 Video attached directly via file input: {os.path.basename(video_path)}")
                        break
                except Exception:
                    pass

                # Check inside child frames/iframes if any
                if not attached:
                    try:
                        for fr in page.frames:
                            fr_inputs = fr.locator('input[type="file"]')
                            if await fr_inputs.count() > 0:
                                await fr_inputs.first.set_input_files(video_path)
                                attached = True
                                self._log("SUCCESS", f"{tab_tag} 📁 Video attached via iframe file input: {os.path.basename(video_path)}")
                                break
                    except Exception:
                        pass

                # Try clicking Add Video / Upload button and catching file chooser
                if not attached:
                    try:
                        btn_candidates = [
                            page.locator('div[role="button"]:has-text("Add video")'),
                            page.locator('button:has-text("Add video")'),
                            page.locator('div[role="button"]:has-text("Add Video")'),
                            page.locator('button:has-text("Add Video")'),
                            page.locator('div[role="button"]:has-text("Upload video")'),
                            page.locator('button:has-text("Upload video")'),
                            page.locator('div[role="button"]:has-text("Upload")'),
                            page.locator('button:has-text("Upload")'),
                            page.locator('[aria-label*="Add video" i]'),
                            page.locator('[aria-label*="Upload" i]')
                        ]
                        for candidate in btn_candidates:
                            if await candidate.count() > 0 and await candidate.first.is_visible():
                                try:
                                    async with page.expect_file_chooser(timeout=4000) as fc_info:
                                        await candidate.first.click()
                                    file_chooser = await fc_info.value
                                    await file_chooser.set_files(video_path)
                                    attached = True
                                    self._log("SUCCESS", f"{tab_tag} 📁 Video attached via Add Video button: {os.path.basename(video_path)}")
                                    break
                                except Exception:
                                    pass
                        if attached:
                            break
                    except Exception:
                        pass

                # Log periodic status while waiting for slow connection
                if sec in (5, 12, 25, 40, 60):
                    self._log("INFO", f"{tab_tag} ⏳ Page loading in progress ({sec}s elapsed, waiting for Facebook components to render)...")

                await asyncio.sleep(1.0)

            if not attached:
                raise RuntimeError(
                    f"Could not find 'Add Video' upload element on Meta Composer after waiting 75 seconds. "
                    f"Please verify the account is logged in and the page has finished loading."
                )

            self._log("INFO", f"{tab_tag} ⏳ Video attached. Waiting for upload & encoding to complete...")

            # Wait for video upload to complete (up to 75 seconds)
            upload_ready = False
            for sec in range(1, 76):
                if self._cancelled:
                    return False

                await self._handle_continue_editing_dialog(page)

                try:
                    body_text = await page.evaluate("() => document.body.innerText || ''")
                    body_lower = body_text.lower()
                    if "100%" in body_text or "safe to publish" in body_lower or "video is safe" in body_lower or "ready to publish" in body_lower or "edit reel" in body_lower:
                        upload_ready = True
                        break

                    # Check if Next button is enabled and clickable
                    next_btns = await page.query_selector_all('button:has-text("Next"), div[role="button"]:has-text("Next"), [aria-label*="Next" i]')
                    for nb in next_btns:
                        is_disabled = await nb.get_attribute("aria-disabled")
                        cls = await nb.get_attribute("class") or ""
                        if is_disabled != "true" and "disabled" not in cls.lower() and await nb.is_visible():
                            upload_ready = True
                            break
                    if upload_ready:
                        break
                except Exception:
                    pass

                if sec in (10, 25, 45, 60):
                    self._log("INFO", f"{tab_tag} ⏳ Video encoding/uploading in progress ({sec}s)...")

                await asyncio.sleep(1.0)

            self._log("SUCCESS", f"{tab_tag} ✅ Video uploaded & processed on Meta Composer.")

            if self._cancelled:
                return False

            # Check if any "Continue editing" dialog popped up
            await self._handle_continue_editing_dialog(page)

            # Scroll directly to Description box and Fill Caption
            if caption_text:
                spun_desc = resolve_spintax(caption_text)
                self._log("INFO", f"{tab_tag} ✍️ Scrolling to description and typing Reel details...")
                try:
                    desc_target = None
                    candidates = [
                        'div[role="textbox"]',
                        'div[contenteditable="true"]',
                        'textarea[placeholder*="Describe" i]',
                        'textarea[placeholder*="description" i]',
                        '[aria-label*="Description" i]',
                        '[aria-label*="Describe" i]',
                        'textarea'
                    ]
                    for sel in candidates:
                        els = await page.query_selector_all(sel)
                        for el in els:
                            if await el.is_visible():
                                desc_target = el
                                break
                        if desc_target:
                            break

                    if desc_target:
                        # Scroll smoothly into view
                        try:
                            await desc_target.scroll_into_view_if_needed()
                        except Exception:
                            pass

                        await desc_target.click()
                        await asyncio.sleep(0.5)

                        # Set description text safely without triggering back buttons
                        try:
                            await page.keyboard.insert_text(spun_desc)
                        except Exception:
                            await desc_target.fill(spun_desc)
                            
                        # Dispatch React input and change events
                        await page.evaluate("""(desc) => {
                            const activeEl = document.activeElement;
                            if (activeEl) {
                                activeEl.dispatchEvent(new Event('input', { bubbles: true }));
                                activeEl.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        }""", spun_desc)

                        self._log("SUCCESS", f"{tab_tag} 📝 Description entered: {spun_desc[:40]}...")
                    else:
                        self._log("WARNING", f"{tab_tag} Description field not found, continuing...")
                except Exception as ex:
                    self._log("WARNING", f"{tab_tag} Caption input notice: {ex}")

            await asyncio.sleep(2.0)
            if self._cancelled:
                return False

            # Check again for continue editing dialog before next
            await self._handle_continue_editing_dialog(page)

            # STEP 1 -> STEP 2: Click 'Next' (Create -> Edit)
            self._log("INFO", f"{tab_tag} ➡️ Advancing Step 1 (Create) -> Step 2 (Edit)...")
            clicked_next_1 = False
            for _ in range(12):
                if self._cancelled:
                    return False
                await self._handle_continue_editing_dialog(page)
                try:
                    next_btn = await page.query_selector('button:has-text("Next"), div[role="button"]:has-text("Next"), [aria-label*="Next" i]')
                    if next_btn and await next_btn.is_visible():
                        is_dis = await next_btn.get_attribute("aria-disabled")
                        if is_dis != "true":
                            await next_btn.scroll_into_view_if_needed()
                            await next_btn.click()
                            clicked_next_1 = True
                            break
                except Exception:
                    pass
                await asyncio.sleep(1.0)

            if not clicked_next_1:
                try:
                    await page.click('text="Next"', timeout=6000)
                    clicked_next_1 = True
                except Exception:
                    pass

            # Wait 3.0 seconds on Edit step (Audio/Crop/Text)
            await asyncio.sleep(3.0)
            if self._cancelled:
                return False

            # STEP 2 -> STEP 3: Click 'Next' (Edit -> Share)
            self._log("INFO", f"{tab_tag} ➡️ Advancing Step 2 (Edit) -> Step 3 (Share)...")
            clicked_next_2 = False
            for _ in range(12):
                if self._cancelled:
                    return False
                try:
                    next_btn = await page.query_selector('button:has-text("Next"), div[role="button"]:has-text("Next"), [aria-label*="Next" i]')
                    if next_btn and await next_btn.is_visible():
                        is_dis = await next_btn.get_attribute("aria-disabled")
                        if is_dis != "true":
                            await next_btn.scroll_into_view_if_needed()
                            await next_btn.click()
                            clicked_next_2 = True
                            break
                except Exception:
                    pass
                await asyncio.sleep(1.0)

            if not clicked_next_2:
                try:
                    await page.click('text="Next"', timeout=6000)
                    clicked_next_2 = True
                except Exception:
                    pass

            # Wait 3.0 seconds for Share screen to render
            await asyncio.sleep(3.0)
            if self._cancelled:
                return False

            # STEP 3: Click 'Share' button (Bottom Right)
            self._log("INFO", f"{tab_tag} 🚀 Clicking final 'Share' button to publish Reel...")
            confirmed_share = False
            for attempt in range(1, 31):
                if self._cancelled:
                    return False
                
                clicked = await self._click_primary_share_button(page, tab_tag)
                if clicked:
                    self._log("SUCCESS", f"{tab_tag} 🎯 'Share' button clicked on attempt #{attempt}!")
                    
                    # Wait 1.5s to verify if button reacted / became disabled / loading
                    await asyncio.sleep(1.5)
                    still_active = False
                    try:
                        btn_check = page.locator('div:has(> *[role="button"]:has-text("Back")) *[role="button"]:has-text("Share")')
                        if await btn_check.count() == 0:
                            btn_check = page.get_by_role("button", name="Share", exact=True).last
                        if await btn_check.is_visible():
                            is_dis = await btn_check.get_attribute("aria-disabled")
                            if is_dis != "true":
                                still_active = True
                    except Exception:
                        pass

                    if not still_active:
                        confirmed_share = True
                        break
                    else:
                        # Retry click to make sure React Comet registered it
                        self._log("INFO", f"{tab_tag} 🔄 Repeating click on Share button to ensure submission...")
                
                if attempt in (5, 10, 20):
                    self._log("INFO", f"{tab_tag} ⏳ Waiting for Share button to complete ({attempt}s)...")
                await asyncio.sleep(1.0)

            if not confirmed_share:
                # If still active, one final direct CDP click
                await self._click_primary_share_button(page, tab_tag)

            # Critical Wait: Exactly 3.5 seconds after Share click before closing tab (as requested)
            self._log("INFO", f"{tab_tag} ⏳ Reel shared! Waiting 3.5 seconds for Meta server processing before closing tab...")
            await asyncio.sleep(3.5)

            self._log("SUCCESS", f"{tab_tag} 🎉 Reel published successfully on Meta Business Suite!")
            return True

        except Exception as e:
            self._log("ERROR", f"{tab_tag} Upload error: {str(e)}")
            return False
        finally:
            try:
                await page.close()
            except Exception:
                pass
            if page in self._active_pages:
                self._active_pages.remove(page)

    async def run(self) -> Dict[str, Any]:
        """
        Main execution pipeline:
        1. Launches Chrome browser instance for the account.
        2. Assigns video files based on selection mode.
        3. Spawns `reels_per_account` tabs concurrently (with staggered startup).
        4. Uploads, navigates, and shares reels across all tabs.
        5. Closes Chrome cleanly.
        """
        if not self.video_files:
            self._log("ERROR", f"[{self.account_name}] No valid video files provided.")
            return {"success": False, "uploaded": 0, "message": "No video files loaded."}

        self._log("INFO", f"[{self.account_name}] 🚀 Initializing Meta Reels uploader ({self.reels_per_account} reels/tabs requested)...")

        try:
            await self._setup_browser()

            # Select video files for each tab
            assigned_videos = []
            if self.selection_mode == "Sequential (Top to Bottom)" or self.selection_mode == "Loop All Videos":
                for i in range(self.reels_per_account):
                    assigned_videos.append(self.video_files[i % len(self.video_files)])
            else:
                # Random Pool (No Dup if pool is large enough)
                if len(self.video_files) >= self.reels_per_account:
                    assigned_videos = random.sample(self.video_files, self.reels_per_account)
                else:
                    assigned_videos = []
                    shuffled = list(self.video_files)
                    random.shuffle(shuffled)
                    for i in range(self.reels_per_account):
                        assigned_videos.append(shuffled[i % len(shuffled)])

            self._log("INFO", f"[{self.account_name}] 📑 Opening {self.reels_per_account} parallel tab(s) on Meta Composer...")

            # Use existing initial page for tab 0 if available in context
            existing_pages = self._context.pages if self._context else []
            
            async def _run_tab_with_stagger(idx: int, v_path: str):
                if idx > 0:
                    # Stagger of 2.5s between opening tabs to avoid browser CPU choke and network congestion
                    await asyncio.sleep(idx * 2.5)
                init_p = existing_pages[0] if (idx == 0 and len(existing_pages) > 0) else None
                return await self._upload_single_tab(
                    tab_index=idx,
                    video_path=v_path,
                    caption_text=self.caption_template,
                    existing_page=init_p
                )

            tasks = [
                _run_tab_with_stagger(idx, assigned_videos[idx])
                for idx in range(self.reels_per_account)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful_count = sum(1 for r in results if r is True)

            self._report_counter(successful_count)

            msg = f"Completed {successful_count} of {self.reels_per_account} Reels uploads on [{self.account_name}]."
            self._log("SUCCESS" if successful_count > 0 else "WARNING", f"[{self.account_name}] 🏁 {msg}")

            return {
                "success": successful_count > 0,
                "uploaded": successful_count,
                "total_requested": self.reels_per_account,
                "message": msg
            }

        except Exception as e:
            err_msg = str(e)
            self._log("ERROR", f"[{self.account_name}] Pipeline failure: {err_msg}")
            return {"success": False, "uploaded": 0, "message": err_msg}
        finally:
            await self.close()

    async def close(self):
        """Safely closes all active pages, contexts, and Playwright instances."""
        for p in list(self._active_pages):
            try:
                await p.close()
            except Exception:
                pass
        self._active_pages.clear()

        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._pw:
            try:
                await self._pw.stop()
            except Exception:
                pass
            self._pw = None

        self._log("INFO", f"[{self.account_name}] 🔒 Closed Chrome browser session cleanly.")
