"""
FB Auto Bot - Facebook Reels Bulk Uploader Engine
Automates high-speed Reels uploading across multiple Facebook accounts with multi-tab support,
intelligent Spintax caption generation, file validation, stealth Playwright browser controls,
and automatic Chrome cleanup.
"""

import os
import sys
import json
import socket
import asyncio
import logging
import random
import re
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger("FBAutoBot.ReelsUploaderBot")

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


def resolve_spintax(text: str) -> str:
    """Recursively resolves nested spintax like '{A|B|{C|D}}'."""
    pattern = re.compile(r'\{([^{}]+)\}')
    max_passes = 20
    passes = 0
    while passes < max_passes:
        match = pattern.search(text)
        if not match:
            break
        choices = match.group(1).split('|')
        text = text[:match.start()] + random.choice(choices) + text[match.end():]
        passes += 1
    return text


def test_proxy_connectivity(host: str, port: int, timeout: float = 2.0) -> bool:
    """Socket probe to verify proxy server responsiveness before launching Chrome."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except Exception:
        return False


def parse_cookie_payload(raw_cookies: str) -> List[Dict[str, Any]]:
    """Parses JSON cookie arrays or semicolon strings into standard Playwright cookie objects."""
    cleaned = (raw_cookies or "").strip()
    if not cleaned:
        return []

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

    formatted = []
    for pair in cleaned.split(";"):
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


class FacebookReelsUploaderBot:
    """
    Automates uploading Reels videos on Facebook for a target account.
    Launches Chrome with persistent stealth profile/cookies, opens the Reels creation wizard,
    attaches the video file, enters spintax captions, clicks next through steps,
    publishes the reel, and gracefully closes Chrome when finished.
    """

    def __init__(
        self,
        account_data: Dict[str, Any],
        video_files: List[str],
        reels_per_account: int = 5,
        delay_seconds: float = 15.0,
        caption_template: str = "",
        selection_mode: str = "Random Pool (No Dup)",
        log_callback: Optional[Callable[[str, str], None]] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        counter_callback: Optional[Callable[[str, int], None]] = None
    ):
        self.account_data = account_data
        self.video_files = [f for f in video_files if os.path.isfile(f)]
        self.reels_per_account = max(1, reels_per_account)
        self.delay_seconds = max(2.0, delay_seconds)
        self.caption_template = caption_template or "{🔥 Amazing Reel|Must Watch Video|Check this out}! Drop a follow ❤️ #reels #viral #trending #fyp"
        self.selection_mode = selection_mode

        self.log_cb = log_callback
        self.prog_cb = progress_callback
        self.counter_cb = counter_callback

        self.account_id = str(account_data.get("id", "unknown"))
        self.account_name = str(account_data.get("name", "Facebook Account"))

        self.playwright = None
        self.browser = None
        self.context = None
        self._cancelled = False
        self.uploaded_count = 0

    def log(self, level: str, message: str):
        full_msg = f"[{self.account_name}] {message}"
        if self.log_cb:
            self.log_cb(level, full_msg)
        else:
            print(f"[{level}] {full_msg}")

    def cancel(self):
        self._cancelled = True
        self.log("WARNING", "🛑 Stop command received. Terminating Reels uploader...")

    async def _init_browser(self):
        """Initializes stealth Chrome instance with account cookies and anti-fingerprinting."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed in the system environment.")

        self.playwright = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-notifications",
            "--no-first-run",
            "--disable-default-apps",
            "--disable-popup-blocking",
            "--start-maximized"
        ]

        proxy_cfg = None
        use_direct = (
            self.account_data.get("network_mode") == "direct"
            or self.account_data.get("use_direct_network", False)
        )
        raw_proxy = (self.account_data.get("proxy") or "").strip()
        is_direct_str = any(d in raw_proxy.lower() for d in ["direct", "no proxy", "none", "null", "false", "0", ""])

        if use_direct or is_direct_str or not raw_proxy:
            proxy_cfg = None
            launch_args.append("--no-proxy-server")
            self.log("INFO", "🌐 Direct internet connection enabled.")
        else:
            try:
                server_url = raw_proxy if "://" in raw_proxy else f"{self.account_data.get('proxy_type', 'http').lower()}://{raw_proxy}"
                parsed = urlparse(server_url)
                host = parsed.hostname
                port = parsed.port
                if host and port and test_proxy_connectivity(host, port, timeout=2.0):
                    proxy_cfg = {"server": f"{parsed.scheme}://{host}:{port}"}
                    u = parsed.username or self.account_data.get("proxy_user")
                    p = parsed.password or self.account_data.get("proxy_pass")
                    if u:
                        proxy_cfg["username"] = u
                    if p:
                        proxy_cfg["password"] = p
                    self.log("SUCCESS", f"🛡️ Assigned proxy ({host}:{port}) is LIVE.")
                else:
                    self.log("WARNING", "⚠️ Proxy offline. Falling back to direct connection.")
                    proxy_cfg = None
                    launch_args.append("--no-proxy-server")
            except Exception:
                proxy_cfg = None
                launch_args.append("--no-proxy-server")

        chrome_candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        chrome_exe = next((c for c in chrome_candidates if os.path.isfile(c)), None)

        launch_kwargs: Dict[str, Any] = {
            "headless": False,
            "args": launch_args
        }
        if proxy_cfg:
            launch_kwargs["proxy"] = proxy_cfg
        if chrome_exe:
            launch_kwargs["executable_path"] = chrome_exe

        try:
            self.browser = await self.playwright.chromium.launch(**launch_kwargs)
        except Exception as e:
            self.log("WARNING", f"Custom Chrome launch notice: {e}. Falling back to default Chromium...")
            launch_kwargs.pop("executable_path", None)
            self.browser = await self.playwright.chromium.launch(**launch_kwargs)

        profile_dir = self.account_data.get("profile_dir", "")
        if profile_dir and os.path.isdir(profile_dir):
            try:
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=False,
                    args=launch_args,
                    proxy=proxy_cfg,
                    viewport=None,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                    locale="en-US"
                )
            except Exception:
                self.context = await self.browser.new_context(
                    viewport=None,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                    locale="en-US"
                )
        else:
            self.context = await self.browser.new_context(
                viewport=None,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                locale="en-US"
            )

        # Inject session cookies
        raw_cookies = self.account_data.get("cookies", "")
        if raw_cookies and self.context:
            try:
                formatted = []
                if isinstance(raw_cookies, str):
                    formatted = parse_cookie_payload(raw_cookies)
                elif isinstance(raw_cookies, list):
                    for item in raw_cookies:
                        if isinstance(item, dict) and "name" in item and "value" in item:
                            formatted.append({
                                "name": str(item["name"]),
                                "value": str(item["value"]),
                                "domain": str(item.get("domain", ".facebook.com")),
                                "path": str(item.get("path", "/")),
                                "secure": bool(item.get("secure", True))
                            })
                        elif isinstance(item, str):
                            formatted.extend(parse_cookie_payload(item))
                if formatted:
                    await self.context.add_cookies(formatted)
                    self.log("SUCCESS", f"🔑 Injected {len(formatted)} Facebook cookies. Session active.")
            except Exception as e:
                self.log("DEBUG", f"Cookie injection notice: {e}")

    async def _open_reels_creator_modal(self, page: Page) -> bool:
        """
        Navigates to the Facebook Profile / Page Reels tab and triggers the 'Create reel' modal.
        Matches the exact workflow:
        1. Navigates to user profile / page (or https://www.facebook.com/me?sk=reels_tab)
        2. Clicks the 'Reels' tab if not already on it
        3. Clicks the '+ Create reel' button
        4. Verifies the 'Create reel' modal overlay is open and ready for video upload.
        """
        clean_uid = "".join(c for c in str(self.account_data.get("uid", "")) if c.isdigit())
        
        target_urls = []
        if clean_uid:
            target_urls.append(f"https://www.facebook.com/profile.php?id={clean_uid}&sk=reels_tab")
            target_urls.append(f"https://www.facebook.com/profile.php?id={clean_uid}")
        target_urls.append("https://www.facebook.com/me?sk=reels_tab")
        target_urls.append("https://www.facebook.com/me")
        target_urls.append("https://www.facebook.com/")

        modal_opened = False

        for url in target_urls:
            if self._cancelled:
                return False
            try:
                self.log("INFO", f"Navigating to Facebook profile/reels: {url} ...")
                await page.goto(url, wait_until="domcontentloaded", timeout=35000)
                await asyncio.sleep(2.5)

                # Check if redirected to login
                curr = page.url.lower()
                if "login" in curr or "checkpoint" in curr:
                    self.log("ERROR", "❌ Account session expired or requires login.")
                    return False

                # If on Profile but not Reels tab, click 'Reels' tab
                reels_tab_selectors = [
                    'a[href*="sk=reels_tab"]',
                    'a[href*="sk=reels"]',
                    'a[href*="/reels/"]',
                    'a:has-text("Reels")',
                    'div[role="tab"]:has-text("Reels")',
                    'span:has-text("Reels")'
                ]
                for r_sel in reels_tab_selectors:
                    try:
                        r_btn = page.locator(r_sel).first
                        if await r_btn.count() > 0 and await r_btn.is_visible():
                            await r_btn.click()
                            self.log("INFO", "Clicked 'Reels' tab on Facebook profile/page.")
                            await asyncio.sleep(2.0)
                            break
                    except Exception:
                        pass

                # Look for 'Create reel' button on the Reels tab or Facebook page
                create_reel_btn_selectors = [
                    'div[role="button"]:has-text("Create reel")',
                    'div[role="button"]:has-text("Create Reel")',
                    'button:has-text("Create reel")',
                    'button:has-text("Create Reel")',
                    'a:has-text("Create reel")',
                    'a:has-text("Create Reel")',
                    'div[aria-label*="Create reel" i][role="button"]',
                    'div[aria-label*="Create Reel" i][role="button"]',
                    'div[aria-label*="Create a reel" i][role="button"]',
                    'span:has-text("Create reel")',
                    'span:has-text("Create Reel")',
                    # Homepage stories/reels bar selector
                    'div[aria-label="Reel"][role="button"]',
                    'div[aria-label="Create reel"][role="button"]'
                ]

                for cr_sel in create_reel_btn_selectors:
                    try:
                        cr_btn = page.locator(cr_sel).first
                        if await cr_btn.count() > 0 and await cr_btn.is_visible():
                            self.log("INFO", "👉 Found and clicking 'Create reel' button...")
                            await cr_btn.click()
                            await asyncio.sleep(3.0)
                            modal_opened = True
                            break
                    except Exception:
                        pass

                if modal_opened:
                    break

                # Also try DOM querySelector for Create Reel button
                try:
                    clicked_dom = await page.evaluate("""() => {
                        const buttons = Array.from(document.querySelectorAll('div[role="button"], button, a, span'));
                        for (const b of buttons) {
                            const txt = (b.innerText || b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase();
                            if (txt === 'create reel' || txt.includes('create reel') || txt === 'create a reel') {
                                if (b.offsetParent !== null) {
                                    b.click();
                                    return true;
                                }
                            }
                        }
                        return false;
                    }""")
                    if clicked_dom:
                        self.log("INFO", "👉 Clicked 'Create reel' via DOM helper.")
                        await asyncio.sleep(3.0)
                        modal_opened = True
                        break
                except Exception:
                    pass

            except Exception as ex:
                self.log("WARNING", f"Navigation notice for {url}: {ex}")

        # Check if file input or Create Reel dialog is present
        file_input_count = await page.locator('input[type="file"]').count()
        if file_input_count > 0 or modal_opened:
            return True

        # Fallback: Try direct reels creator URL
        try:
            self.log("INFO", "Attempting fallback direct creator URL...")
            await page.goto("https://www.facebook.com/reels/create", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3.0)
            if "not available" not in (await page.content()).lower():
                return True
        except Exception:
            pass

        return modal_opened

    async def _upload_single_reel_tab(
        self,
        page: Page,
        video_path: str,
        caption: str,
        reel_index: int,
        total_reels: int,
        base_reels_url: str = ""
    ) -> bool:
        """
        Executes the complete Reel upload process on an isolated browser tab:
        1. Navigates to Reels tab on Facebook Profile/Page
        2. Clicks 'Create reel' button
        3. Attaches video file specifically through the Create Reel modal dialog
        4. Advances through Next -> Next steps
        5. Types Spintax caption & hashtags
        6. Clicks 'Post' / 'Publish'
        7. Confirms completion and closes tab
        """
        file_name = os.path.basename(video_path)
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        self.log("INFO", f"🎬 [Tab #{reel_index}/{total_reels}] Opening Reel Creator for: {file_name} ({file_size_mb:.1f} MB)...")

        # Determine target reels tab URL
        target_urls = []
        if base_reels_url:
            target_urls.append(base_reels_url)
        clean_uid = "".join(c for c in str(self.account_data.get("uid", "")) if c.isdigit())
        if clean_uid:
            target_urls.append(f"https://www.facebook.com/profile.php?id={clean_uid}&sk=reels_tab")
            target_urls.append(f"https://www.facebook.com/profile.php?id={clean_uid}")
        target_urls.append("https://www.facebook.com/me?sk=reels_tab")
        target_urls.append("https://www.facebook.com/me")
        target_urls.append("https://www.facebook.com/")

        modal_opened = False

        for url in target_urls:
            if self._cancelled:
                return False
            try:
                self.log("INFO", f"[Tab #{reel_index}] Navigating to: {url} ...")
                await page.goto(url, wait_until="domcontentloaded", timeout=40000)
                await asyncio.sleep(2.5)

                # Check if redirected to login
                curr = page.url.lower()
                if "login" in curr or "checkpoint" in curr:
                    self.log("ERROR", f"[Tab #{reel_index}] ❌ Account session expired.")
                    return False

                # If on profile, ensure 'Reels' tab is active
                reels_tab_selectors = [
                    'a[href*="sk=reels_tab"]',
                    'a[href*="sk=reels"]',
                    'a[href*="/reels/"]',
                    'a:has-text("Reels")',
                    'div[role="tab"]:has-text("Reels")',
                    'span:has-text("Reels")'
                ]
                for r_sel in reels_tab_selectors:
                    try:
                        r_btn = page.locator(r_sel).first
                        if await r_btn.count() > 0 and await r_btn.is_visible():
                            await r_btn.click()
                            await asyncio.sleep(1.5)
                            break
                    except Exception:
                        pass

                # Dismiss any alert dialog if open
                try:
                    close_alert = page.locator('div[role="dialog"] button:has-text("Close"), div[role="dialog"] div[role="button"]:has-text("Close")').first
                    if await close_alert.count() > 0 and await close_alert.is_visible():
                        await close_alert.click()
                        await asyncio.sleep(1.0)
                except Exception:
                    pass

                # Click 'Create reel' button
                create_reel_btn_selectors = [
                    'div[role="button"]:has-text("Create reel")',
                    'div[role="button"]:has-text("Create Reel")',
                    'button:has-text("Create reel")',
                    'button:has-text("Create Reel")',
                    'a:has-text("Create reel")',
                    'a:has-text("Create Reel")',
                    'div[aria-label*="Create reel" i][role="button"]',
                    'div[aria-label*="Create Reel" i][role="button"]',
                    'div[aria-label*="Create a reel" i][role="button"]',
                    'span:has-text("Create reel")',
                    'div[aria-label="Reel"][role="button"]',
                    'div[aria-label="Create reel"][role="button"]'
                ]

                for cr_sel in create_reel_btn_selectors:
                    try:
                        cr_btn = page.locator(cr_sel).first
                        if await cr_btn.count() > 0 and await cr_btn.is_visible():
                            self.log("INFO", f"[Tab #{reel_index}] 👉 Clicking 'Create reel' button...")
                            await cr_btn.click()
                            await asyncio.sleep(2.5)
                            modal_opened = True
                            break
                    except Exception:
                        pass

                if modal_opened:
                    break

                # Fallback DOM click
                try:
                    clicked_dom = await page.evaluate("""() => {
                        const buttons = Array.from(document.querySelectorAll('div[role="button"], button, a, span'));
                        for (const b of buttons) {
                            const txt = (b.innerText || b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase();
                            if (txt === 'create reel' || txt.includes('create reel') || txt === 'create a reel') {
                                if (b.offsetParent !== null) {
                                    b.click();
                                    return true;
                                }
                            }
                        }
                        return false;
                    }""")
                    if clicked_dom:
                        self.log("INFO", f"[Tab #{reel_index}] 👉 Clicked 'Create reel' via DOM.")
                        await asyncio.sleep(2.5)
                        modal_opened = True
                        break
                except Exception:
                    pass

            except Exception as ex:
                self.log("DEBUG", f"[Tab #{reel_index}] Navigation notice: {ex}")

        # Check if Create Reel dialog is open
        dialog_locator = page.locator('div[role="dialog"]').first
        is_dialog_present = await dialog_locator.count() > 0

        # Dismiss any "Can't Read Files" popup if present
        try:
            close_btn = page.locator('div[role="dialog"] button:has-text("Close"), div[role="dialog"] div[role="button"]:has-text("Close"), button:has-text("Close")').first
            if await close_btn.count() > 0 and await close_btn.is_visible():
                await close_btn.click()
                await asyncio.sleep(1.0)
        except Exception:
            pass

        # Attach video file specifically through the Create Reel dialog / file chooser
        self.log("INFO", f"[Tab #{reel_index}] 📤 Attaching video file: {file_name} ...")
        file_attached = False

        # Priority 1: Click the 'Upload' or 'Add video' button with native file chooser listener
        upload_btn_selectors = [
            'div[role="dialog"] div[role="button"]:has-text("Upload")',
            'div[role="dialog"] button:has-text("Upload")',
            'div[role="dialog"] div[role="button"]:has-text("Add video")',
            'div[role="dialog"] button:has-text("Add video")',
            'div[role="dialog"] div[role="button"]:has-text("Select video")',
            'div[role="dialog"] button:has-text("Select video")',
            'div[role="dialog"] div[aria-label*="video" i][role="button"]',
            'div[role="dialog"] div[aria-label*="upload" i][role="button"]',
            'div[role="button"]:has-text("Upload")',
            'button:has-text("Upload")',
            'div[role="button"]:has-text("Add video")'
        ]

        for u_sel in upload_btn_selectors:
            try:
                u_btn = page.locator(u_sel).first
                if await u_btn.count() > 0 and await u_btn.is_visible():
                    async with page.expect_file_chooser(timeout=15000) as fc_info:
                        await u_btn.click()
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(video_path)
                    file_attached = True
                    self.log("SUCCESS", f"[Tab #{reel_index}] ✅ Video file selected via FileChooser: {file_name}")
                    break
            except Exception as fc_err:
                self.log("DEBUG", f"[Tab #{reel_index}] FileChooser notice on {u_sel}: {fc_err}")

        # Priority 2: Direct set_input_files on dialog video file input
        if not file_attached:
            try:
                scoped_input = page.locator('div[role="dialog"] input[type="file"][accept*="video"], div[role="dialog"] input[type="file"]').first
                if await scoped_input.count() > 0:
                    await scoped_input.set_input_files(video_path)
                    file_attached = True
                    self.log("SUCCESS", f"[Tab #{reel_index}] ✅ Video file attached via scoped input: {file_name}")
            except Exception as si_err:
                self.log("DEBUG", f"[Tab #{reel_index}] Scoped input notice: {si_err}")

        if not file_attached:
            self.log("ERROR", f"[Tab #{reel_index}] ❌ Could not attach video file for {file_name}.")
            return False

        self.log("INFO", f"[Tab #{reel_index}] ⏳ Waiting for Facebook video processing...")
        await asyncio.sleep(4.0)

        # Dismiss any error dialogs that might have appeared
        try:
            close_btn2 = page.locator('button:has-text("Close"), div[role="button"]:has-text("Close")').first
            if await close_btn2.count() > 0 and await close_btn2.is_visible():
                await close_btn2.click()
                await asyncio.sleep(1.0)
        except Exception:
            pass

        # Step 1: Click "Next" on media upload step (Step 1 -> Step 2)
        next_selectors = [
            'div[role="dialog"] div[aria-label="Next"][role="button"]',
            'div[role="dialog"] button:has-text("Next")',
            'div[role="dialog"] div[role="button"]:has-text("Next")',
            'div[role="dialog"] span:has-text("Next")',
            'div[aria-label="Next"][role="button"]',
            'button:has-text("Next")',
            'div[role="button"]:has-text("Next")'
        ]

        next_clicked = False
        for attempt in range(30):
            if self._cancelled:
                return False
            for sel in next_selectors:
                try:
                    btn = page.locator(sel).first
                    if await btn.count() > 0 and await btn.is_visible():
                        is_disabled = await btn.get_attribute("aria-disabled")
                        if is_disabled != "true":
                            await btn.click()
                            next_clicked = True
                            self.log("INFO", f"[Tab #{reel_index}] 👉 Clicked 'Next' (Step 1 -> Step 2).")
                            break
                except Exception:
                    pass
            if next_clicked:
                break
            await asyncio.sleep(1.5)

        await asyncio.sleep(2.5)

        # Step 2: Click "Next" on Edit / Audio step (Step 2 -> Step 3 Reel Settings)
        edit_next_clicked = False
        for attempt in range(20):
            if self._cancelled:
                return False
            # Check if we already reached Reel settings (caption textbox visible)
            has_caption_box = await page.locator('div[role="dialog"] div[aria-label*="Describe your reel" i], div[role="dialog"] div[contenteditable="true"], div[role="dialog"] textarea').count() > 0
            has_post_btn = await page.locator('div[role="dialog"] div[aria-label="Post"][role="button"], div[role="dialog"] button:has-text("Post"), div[role="dialog"] div[role="button"]:has-text("Post")').count() > 0
            if has_caption_box or has_post_btn:
                self.log("INFO", f"[Tab #{reel_index}] 🎯 Reached Reel Settings step.")
                break

            for sel in next_selectors:
                try:
                    btn = page.locator(sel).first
                    if await btn.count() > 0 and await btn.is_visible():
                        is_disabled = await btn.get_attribute("aria-disabled")
                        if is_disabled != "true":
                            await btn.click()
                            edit_next_clicked = True
                            self.log("INFO", f"[Tab #{reel_index}] 👉 Clicked 'Next' (Step 2 -> Step 3).")
                            break
                except Exception:
                    pass
            if edit_next_clicked:
                break
            await asyncio.sleep(1.5)

        await asyncio.sleep(2.0)

        # Step 3: Enter Caption / Description
        self.log("INFO", f"[Tab #{reel_index}] ✍️ Entering Reel Caption: \"{caption[:40]}...\"")
        caption_selectors = [
            'div[role="dialog"] div[aria-label*="Describe your reel" i][role="textbox"]',
            'div[role="dialog"] div[aria-label*="Describe your reel" i]',
            'div[role="dialog"] div[aria-label*="Write a description" i][role="textbox"]',
            'div[role="dialog"] div[aria-label*="Description" i][role="textbox"]',
            'div[role="dialog"] div[role="textbox"][contenteditable="true"]',
            'div[role="dialog"] div[contenteditable="true"]',
            'div[role="dialog"] textarea',
            'div[aria-label*="Describe your reel" i][role="textbox"]',
            'div[role="textbox"][contenteditable="true"]',
            'textarea[placeholder*="Describe your reel" i]',
            'div[contenteditable="true"]'
        ]

        caption_entered = False
        for sel in caption_selectors:
            try:
                box = page.locator(sel).first
                if await box.count() > 0 and await box.is_visible():
                    await box.click()
                    await asyncio.sleep(0.4)
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Backspace")
                    await asyncio.sleep(0.2)
                    await page.keyboard.type(caption, delay=20)
                    caption_entered = True
                    break
            except Exception:
                pass

        if not caption_entered:
            try:
                caption_entered = await page.evaluate("""(txt) => {
                    const dialog = document.querySelector('div[role="dialog"]') || document;
                    const boxes = Array.from(dialog.querySelectorAll('div[contenteditable="true"], textarea, div[role="textbox"]'));
                    for (const b of boxes) {
                        if (b.offsetParent !== null) {
                            b.focus();
                            document.execCommand('selectAll', false, null);
                            document.execCommand('insertText', false, txt);
                            return true;
                        }
                    }
                    return false;
                }""", caption)
            except Exception:
                pass

        if caption_entered:
            self.log("SUCCESS", f"[Tab #{reel_index}] ✅ Caption & hashtags successfully inserted.")
        else:
            self.log("WARNING", f"[Tab #{reel_index}] ⚠️ Caption box note; proceeding to Post...")

        await asyncio.sleep(2.0)

        # Step 4: Click Post button specifically at the bottom left of the Reel Settings modal
        self.log("INFO", f"[Tab #{reel_index}] 🚀 Clicking 'Post' button to publish Reel #{reel_index} ({file_name})...")
        publish_selectors = [
            'div[role="dialog"] div[aria-label="Post"][role="button"]',
            'div[role="dialog"] button:has-text("Post")',
            'div[role="dialog"] div[role="button"]:has-text("Post")',
            'div[role="dialog"] span:has-text("Post")',
            'div[role="dialog"] div[aria-label="Publish"][role="button"]',
            'div[role="dialog"] button:has-text("Publish")',
            'div[role="dialog"] div[role="button"]:has-text("Publish")',
            'div[aria-label="Post"][role="button"]',
            'button:has-text("Post")',
            'div[role="button"]:has-text("Post")',
            'button:has-text("Publish")',
            'div[role="button"]:has-text("Publish")'
        ]

        published = False
        for attempt in range(30):
            if self._cancelled:
                return False
            for sel in publish_selectors:
                try:
                    btn = page.locator(sel).first
                    if await btn.count() > 0 and await btn.is_visible():
                        is_disabled = await btn.get_attribute("aria-disabled")
                        if is_disabled != "true":
                            await btn.scroll_into_view_if_needed()
                            await btn.click()
                            published = True
                            self.log("SUCCESS", f"[Tab #{reel_index}] 🎉 Clicked Post on Reel #{reel_index} ({file_name})!")
                            break
                except Exception:
                    pass
            if published:
                break

            # DOM click fallback if selector retry needed
            if attempt > 3:
                try:
                    published = await page.evaluate("""() => {
                        const dialog = document.querySelector('div[role="dialog"]') || document;
                        const btns = Array.from(dialog.querySelectorAll('button, div[role="button"], span[role="button"]'));
                        for (const b of btns) {
                            if (!b.offsetParent) continue;
                            const txt = (b.innerText || b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase();
                            if (txt === 'post' || txt === 'publish' || txt === 'share reel') {
                                const dis = b.getAttribute('aria-disabled');
                                if (dis !== 'true') {
                                    b.click();
                                    return true;
                                }
                            }
                        }
                        return false;
                    }""")
                    if published:
                        self.log("SUCCESS", f"[Tab #{reel_index}] 🎉 Clicked Post via DOM on Reel #{reel_index} ({file_name})!")
                        break
                except Exception:
                    pass

            await asyncio.sleep(1.5)

        if published:
            self.log("INFO", f"[Tab #{reel_index}] ⏳ Finalizing post processing for {file_name}...")
            # Wait for upload/post to finish and dialog to disappear
            for _ in range(15):
                if self._cancelled:
                    break
                has_dialog = await page.locator('div[role="dialog"]').count() > 0
                if not has_dialog:
                    self.log("SUCCESS", f"[Tab #{reel_index}] ✅ Reel dialog closed - successfully posted {file_name}!")
                    break
                await asyncio.sleep(2.0)
            return True
        else:
            self.log("ERROR", f"[Tab #{reel_index}] ❌ Could not click Post button for {file_name}.")
            return False

    async def run(self) -> Dict[str, Any]:
        """
        Executes bulk Reels upload for this account:
        1. Selects videos according to mode (Random / Sequential / Loop)
        2. Opens Chrome and detects the active Facebook Profile / Page Reels tab URL
        3. Spawns concurrent multi-tabs simultaneously (e.g. 2, 3, or 5 tabs at the same time)
        4. In parallel, each tab attaches video, clicks Next, Next, enters caption, and posts
        5. Cleanly closes Chrome when all tabs are completed
        """
        if not self.video_files:
            self.log("ERROR", "No video files found in the media pool.")
            return {"success": False, "count": 0, "message": "No video files found"}

        # Select videos for this account
        total_requested = self.reels_per_account
        assigned_videos: List[str] = []

        if self.selection_mode == "Sequential (Top to Bottom)":
            assigned_videos = [self.video_files[i % len(self.video_files)] for i in range(total_requested)]
        elif self.selection_mode == "Random Pool (No Dup)":
            if len(self.video_files) >= total_requested:
                assigned_videos = random.sample(self.video_files, total_requested)
            else:
                assigned_videos = list(self.video_files)
                while len(assigned_videos) < total_requested:
                    assigned_videos.append(random.choice(self.video_files))
        else: # Loop All Videos
            assigned_videos = [self.video_files[i % len(self.video_files)] for i in range(total_requested)]

        self.log(
            "INFO",
            f"🚀 Starting Multi-Tab Auto Reels Upload: {len(assigned_videos)} Reel(s) running simultaneously on {self.account_name}..."
        )

        try:
            await self._init_browser()
            if self._cancelled or not self.context:
                return {"success": False, "count": 0, "message": "Cancelled before start"}

            # Detect Profile / Page Reels Tab URL
            main_page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            try:
                await main_page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=40000)
                await asyncio.sleep(2.0)
            except Exception:
                pass

            curr_url = main_page.url.lower()
            if "login" in curr_url or "checkpoint" in curr_url:
                self.log("ERROR", "❌ Facebook account session expired. Please update cookies or login.")
                return {"success": False, "count": 0, "message": "Session expired"}

            # Auto-detect profile/page URL
            base_reels_url = ""
            try:
                detected_profile = await main_page.evaluate("""() => {
                    const links = Array.from(document.querySelectorAll('a'));
                    for (const a of links) {
                        const h = (a.href || '');
                        if (h.includes('profile.php?id=') || (h.includes('/me') && !h.includes('/messages/'))) {
                            return h;
                        }
                    }
                    return null;
                }""")
                if detected_profile:
                    clean_p = detected_profile.split('&')[0].split('#')[0]
                    if 'profile.php' in clean_p:
                        base_reels_url = f"{clean_p}&sk=reels_tab"
                    else:
                        base_reels_url = f"{clean_p.rstrip('/')}/reels"
                    self.log("INFO", f"🎯 Detected active Facebook Reels URL: {base_reels_url}")
            except Exception:
                pass

            self.uploaded_count = 0
            total_reels = len(assigned_videos)

            # Concurrent Multi-Tab Execution: Run all N tabs in parallel!
            self.log("INFO", f"⚡ Spawning {total_reels} concurrent browser tab(s) simultaneously...")

            async def _worker_tab(v_path: str, tab_idx: int):
                caption_text = resolve_spintax(self.caption_template)
                tab_page = await self.context.new_page()
                try:
                    ok = await self._upload_single_reel_tab(
                        page=tab_page,
                        video_path=v_path,
                        caption=caption_text,
                        reel_index=tab_idx,
                        total_reels=total_reels,
                        base_reels_url=base_reels_url
                    )
                    if ok:
                        self.uploaded_count += 1
                        self.log("SUCCESS", f"✨ Reel #{tab_idx} ({os.path.basename(v_path)}) successfully uploaded & posted!")
                        if self.counter_cb:
                            self.counter_cb(self.account_id, self.uploaded_count)
                    else:
                        self.log("WARNING", f"⚠️ Reel #{tab_idx} ({os.path.basename(v_path)}) upload was incomplete.")
                except Exception as ex:
                    self.log("ERROR", f"[Tab #{tab_idx}] Error: {str(ex)}")
                finally:
                    try:
                        await tab_page.close()
                    except Exception:
                        pass

            # Launch all tabs concurrently
            tab_tasks = [_worker_tab(v_path, idx + 1) for idx, v_path in enumerate(assigned_videos)]
            await asyncio.gather(*tab_tasks, return_exceptions=True)

            self.log("SUCCESS", f"🎉 Finished all reels! Total successfully uploaded: {self.uploaded_count}/{total_reels}.")
            return {
                "success": True,
                "count": self.uploaded_count,
                "message": f"Successfully uploaded {self.uploaded_count} reels"
            }

        except Exception as e:
            self.log("ERROR", f"Error during reels upload execution: {str(e)}")
            return {"success": False, "count": self.uploaded_count, "message": str(e)}

        finally:
            self.log("INFO", f"Closing Chrome browser cleanly for {self.account_name}...")
            try:
                if self.context:
                    await self.context.close()
            except Exception:
                pass
            try:
                if self.browser:
                    await self.browser.close()
            except Exception:
                pass
            try:
                if self.playwright:
                    await self.playwright.stop()
            except Exception:
                pass
            self.log("INFO", f"🔒 Chrome closed for {self.account_name}.")
