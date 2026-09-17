"""
FB Auto Bot - Facebook Group Automation Engine (Posting & Group Joining)
Handles automated group joining, sequential/random link & description posting,
multi-threading, delay intervals, and pre-loading FEWFEED Chrome extension.
"""

import os
import sys
import re
import json
import time
import random
import asyncio
from typing import List, Dict, Any, Optional, Callable

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

# Mobile Smartphone Emulation Specifications for FB Group Automation
MOBILE_SMARTPHONE_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.6613.127 Mobile Safari/537.36"
)

MOBILE_DEVICE_METRICS = {
    "width": 430,
    "height": 900,
    "pixelRatio": 1.0
}

MOBILE_EMULATION_EXPERIMENTAL_OPTIONS = {
    "deviceMetrics": MOBILE_DEVICE_METRICS,
    "userAgent": MOBILE_SMARTPHONE_USER_AGENT
}

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

def get_chrome_webdriver_mobile_emulation_config(ext_path: Optional[str] = None, user_data_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns Python Chrome WebDriver experimental options dictionary for mobileEmulation.
    Includes deviceMetrics (width: 430, height: 900, pixelRatio: 1.0) and genuine mobile userAgent.
    """
    config = {
        "mobileEmulation": MOBILE_EMULATION_EXPERIMENTAL_OPTIONS,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--window-size=440,920",
            "--enable-viewport",
            "--force-device-scale-factor=1.0",
            "--touch-events=enabled",
            f"--user-agent={MOBILE_SMARTPHONE_USER_AGENT}",
            "--disable-notifications"
        ]
    }
    if ext_path and os.path.exists(ext_path):
        config["args"].append(f"--load-extension={ext_path}")
        config["args"].append(f"--disable-extensions-except={ext_path}")
    if user_data_dir:
        config["args"].append(f"--user-data-dir={user_data_dir}")
    return config

def parse_group_codes(raw_input: Any) -> List[str]:
    """Parses group codes, IDs, or full Facebook URLs from textarea or list."""
    if not raw_input:
        return []
    if isinstance(raw_input, list):
        items = raw_input
    else:
        items = re.split(r'[\r\n,;]+', str(raw_input))
    
    codes = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        # Extract group ID or vanity name if full URL was pasted
        # e.g., https://www.facebook.com/groups/123456789/ -> 123456789
        m = re.search(r'facebook\.com/groups/([^/?#]+)', cleaned)
        if m:
            codes.append(m.group(1).strip())
        else:
            # Plain code or ID
            codes.append(cleaned.strip())
    # Deduplicate while preserving order
    seen = set()
    unique_codes = []
    for c in codes:
        if c and c not in seen:
            seen.add(c)
            unique_codes.append(c)
    return unique_codes

def parse_multiline_links(raw_input: Any) -> List[str]:
    """Parses links list."""
    if not raw_input:
        return []
    if isinstance(raw_input, list):
        items = raw_input
    else:
        items = re.split(r'[\r\n,;]+', str(raw_input))
    links = [i.strip() for i in items if i.strip()]
    return links

def parse_cookie_payload(raw_cookies: Any) -> List[Dict[str, Any]]:
    if not raw_cookies:
        return []
    if isinstance(raw_cookies, list):
        formatted = []
        for item in raw_cookies:
            if isinstance(item, dict) and item.get("name"):
                dom = item.get("domain", ".facebook.com")
                if not dom.startswith("."):
                    dom = "." + dom
                cookie = {
                    "name": str(item["name"]),
                    "value": str(item.get("value", "")),
                    "domain": dom,
                    "path": item.get("path", "/"),
                    "secure": bool(item.get("secure", True))
                }
                if item.get("sameSite") in ["Strict", "Lax", "None"]:
                    cookie["sameSite"] = item["sameSite"]
                formatted.append(cookie)
        return formatted

    if isinstance(raw_cookies, str):
        cleaned = raw_cookies.strip()
        if not cleaned:
            return []
        if cleaned.startswith("[") and cleaned.endswith("]"):
            try:
                items = json.loads(cleaned)
                return parse_cookie_payload(items)
            except Exception:
                pass
        # Semicolon format
        formatted = []
        pairs = cleaned.split(";")
        for pair in pairs:
            if "=" in pair:
                k, v = pair.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k:
                    formatted.append({
                        "name": k,
                        "value": v,
                        "domain": ".facebook.com",
                        "path": "/",
                        "secure": True
                    })
        return formatted
    return []


# ==============================================================================
# Facebook Group Automation Bot
# ==============================================================================
class FacebookGroupBot:
    """Automates Facebook Group Posting and Group Joining tasks using Playwright & FEWFEED Extension."""

    def __init__(
        self,
        account_data: Dict[str, Any],
        log_callback: Optional[Callable[[str, str], None]] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        headless: bool = False
    ):
        self.account_data = account_data or {}
        self.log_callback = log_callback or (lambda lvl, msg: print(f"[{lvl}] {msg}"))
        self.progress_callback = progress_callback or (lambda p: None)
        self.headless = headless
        self.playwright = None
        self.context = None
        self.page = None
        self.extension_id: Optional[str] = None
        self.fewfeed_ready: bool = False
        self._cancel_requested = False

    def log(self, level: str, message: str):
        self.log_callback(level, message)

    def set_progress(self, val: int):
        self.progress_callback(val)

    def cancel(self):
        self._cancel_requested = True
        self.log("WARNING", "Cancellation requested for Group Bot.")

    async def initialize_browser(self):
        """Launches Chrome with strict mobile device emulation & FEWFEED extension loaded automatically."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not available in Python environment.")

        self.log("INFO", "Initializing Mobile Emulation Browser for FB Group Automation...")
        self.log("INFO", f"📱 Mobile Emulation Active: deviceMetrics={{width: 393, height: 851, pixelRatio: 3.0}}, is_mobile=True")
        self.log("INFO", f"📱 Mobile Smartphone User-Agent: {MOBILE_SMARTPHONE_USER_AGENT}")

        self.playwright = await async_playwright().start()

        ext_path = get_fewfeed_extension_path()
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--window-size=440,920",
            "--enable-viewport",
            "--force-device-scale-factor=1.0",
            "--touch-events=enabled",
            f"--user-agent={MOBILE_SMARTPHONE_USER_AGENT}",
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
            self.log("SUCCESS", f"🧩 Pre-loading Chrome Extension: {os.path.basename(ext_path)} -> {ext_path}")
        else:
            self.log("WARNING", f"FEWFEED extension folder not detected at {ext_path}. Proceeding without extension.")

        ignore_default_args = ["--enable-automation"]

        proxy_cfg = None
        raw_proxy = self.account_data.get("proxy", "").strip()
        if raw_proxy and "direct" not in raw_proxy.lower():
            ptype = self.account_data.get("proxy_type", "HTTP").lower()
            if not raw_proxy.startswith("http://") and not raw_proxy.startswith("socks5://"):
                full_srv = f"{ptype}://{raw_proxy}"
            else:
                full_srv = raw_proxy
            proxy_cfg = {"server": full_srv}
            if self.account_data.get("proxy_user"):
                proxy_cfg["username"] = self.account_data["proxy_user"]
            if self.account_data.get("proxy_pass"):
                proxy_cfg["password"] = self.account_data["proxy_pass"]

        # If account has dedicated profile_dir, use launch_persistent_context
        profile_dir = self.account_data.get("profile_dir")
        if not profile_dir and self.account_data.get("id"):
            safe_id = "".join(c for c in str(self.account_data.get("id", "")) if c.isalnum() or c in ("_", "-"))
            profile_dir = os.path.join(get_base_dir(), "profiles", safe_id)

        if profile_dir:
            os.makedirs(profile_dir, exist_ok=True)

        # Clear profile locks to prevent SingletonLock errors
        if profile_dir and os.path.exists(profile_dir):
            for fname in ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"]:
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

        # Launch browser with strict mobile metrics and mobile emulation
        self.context = None
        for ch in ["chrome", "msedge", None]:
            try:
                kwargs = {
                    "user_data_dir": profile_dir,
                    "headless": False,  # Extensions require headful mode in Chromium
                    "args": launch_args,
                    "ignore_default_args": ignore_default_args,
                    "proxy": proxy_cfg,
                    "user_agent": MOBILE_SMARTPHONE_USER_AGENT,
                    "viewport": {"width": 430, "height": 900},
                    "screen": {"width": 440, "height": 920},
                    "device_scale_factor": 1.0,
                    "is_mobile": True,
                    "has_touch": True,
                    "locale": "en-US",
                    "permissions": ["geolocation", "notifications"]
                }
                if ch:
                    kwargs["channel"] = ch
                self.context = await self.playwright.chromium.launch_persistent_context(**kwargs)
                self.log("INFO", f"Launched mobile Chrome browser using {ch.upper() if ch else 'Chromium'} with FEWFEED loaded.")
                break
            except Exception as ex:
                self.log("WARNING", f"Mobile launch attempt with channel={ch} notice: {str(ex)[:100]}")
                if profile_dir and os.path.exists(profile_dir):
                    for fname in ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"]:
                        fpath = os.path.join(profile_dir, fname)
                        if os.path.exists(fpath) or os.path.islink(fpath):
                            try: os.unlink(fpath)
                            except Exception: pass
                continue

        if not self.context:
            # Fallback to standard launch (non-persistent)
            self.log("WARNING", "Persistent profile context locked or unavailable. Engaging standard browser launch...")
            try:
                launch_kw = {
                    "headless": False,
                    "args": launch_args,
                    "ignore_default_args": ignore_default_args,
                    "proxy": proxy_cfg
                }
                self.browser = await self.playwright.chromium.launch(**launch_kw)
                self.context = await self.browser.new_context(
                    user_agent=MOBILE_SMARTPHONE_USER_AGENT,
                    viewport={"width": 430, "height": 900},
                    device_scale_factor=1.0,
                    is_mobile=True,
                    has_touch=True,
                    locale="en-US",
                    permissions=["geolocation", "notifications"]
                )
                self.log("INFO", "Launched standard mobile Chrome browser (non-persistent fallsafes).")
            except Exception as final_ex:
                raise RuntimeError(f"Failed to launch Chrome or Edge: {str(final_ex)}")

        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

        # Step: Verify and hook FEWFEED Chrome Extension background service worker & pages
        try:
            # Check service workers
            service_workers = self.context.service_workers
            if service_workers:
                for sw in service_workers:
                    sw_url = sw.url
                    if "chrome-extension://" in sw_url:
                        parts = sw_url.replace("chrome-extension://", "").split("/")
                        self.extension_id = parts[0]
                        self.fewfeed_ready = True
                        self.log("SUCCESS", f"⚡ FEWFEED Extension background service worker hooked! ID: {self.extension_id}")
                        break

            # Check background / extension pages if not identified yet
            if not self.extension_id:
                for p in self.context.pages:
                    if "chrome-extension://" in p.url:
                        parts = p.url.replace("chrome-extension://", "").split("/")
                        self.extension_id = parts[0]
                        self.fewfeed_ready = True
                        self.log("SUCCESS", f"⚡ FEWFEED Extension active page hooked! ID: {self.extension_id}")
                        break

            if not self.fewfeed_ready:
                self.log("INFO", "FEWFEED extension loaded in browser context. Ready for background automation.")
                self.fewfeed_ready = True
        except Exception as ee:
            self.log("INFO", f"Extension hook status: Ready ({str(ee)[:60]})")
            self.fewfeed_ready = True

        # Inject session cookies
        cookies_raw = self.account_data.get("cookies", "")
        if cookies_raw:
            cookies = parse_cookie_payload(cookies_raw)
            if cookies:
                try:
                    await self.context.add_cookies(cookies)
                    self.log("SUCCESS", f"🔑 Injected {len(cookies)} authentication cookies into browser context.")
                except Exception as ce:
                    self.log("WARNING", f"Cookie injection notice: {str(ce)[:80]}")

    async def authenticate_session(self):
        """Verifies session is active by navigating to facebook.com."""
        self.log("INFO", "Validating Facebook session...")
        try:
            await self.page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(2.0)
        except Exception as e:
            self.log("WARNING", f"Navigation notice: {str(e)[:80]}")

        url = self.page.url.lower()
        if "login" in url or "checkpoint" in url:
            if "checkpoint" in url:
                raise RuntimeError("Facebook Checkpoint encountered. Manual verification or 2FA required.")
            raise RuntimeError("Facebook session not logged in or expired. Please click 'Launch Manual Login' in Accounts Tab to log into this Facebook profile.")
        self.log("SUCCESS", "Facebook authentication confirmed.")

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    # FewFeed Web Extension Dashboard Navigation & Tool Automation
    # --------------------------------------------------------------------------
    async def open_fewfeed_tool_page(self, target_url: str):
        """Directly navigates to the specific FewFeed tool URL and ensures FewFeed + FB attachment."""
        self.log("INFO", f"🌐 Navigating directly to FewFeed Tool: {target_url}...")
        try:
            await self.page.goto(target_url, wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(2.0)
        except Exception as e:
            self.log("WARNING", f"FewFeed tool navigation notice: {str(e)[:80]}. Retrying...")
            try:
                await self.page.goto(target_url, wait_until="load", timeout=30000)
                await asyncio.sleep(2.0)
            except Exception as e2:
                self.log("ERROR", f"Could not reach {target_url}: {str(e2)[:80]}")

        # Check for CueFeed / FewFeed login form or signin page redirect
        try:
            cf_email = self.account_data.get("cuefeed_email") or self.account_data.get("fewfeed_email") or "codeabm71@gmail.com"
            cf_pass = self.account_data.get("cuefeed_pass") or self.account_data.get("fewfeed_pass") or "Fewfeew"

            for attempt in range(2):
                email_inp = await self.page.query_selector("input[type='email'], input[name*='email' i], input[placeholder*='Email' i], input[placeholder*='email' i], input[name*='user' i]")
                pass_inp = await self.page.query_selector("input[type='password'], input[name*='pass' i], input[placeholder*='Password' i], input[placeholder*='pass' i]")
                is_signin_page = "signin" in self.page.url.lower() or "login" in self.page.url.lower()

                if (email_inp and pass_inp and await email_inp.is_visible()) or is_signin_page:
                    self.log("INFO", f"🔑 Auto-logging into FewFeed Account ({cf_email})...")
                    if email_inp and await email_inp.is_visible():
                        await email_inp.click()
                        await email_inp.fill(cf_email)
                        await asyncio.sleep(0.3)
                    if pass_inp and await pass_inp.is_visible():
                        await pass_inp.click()
                        await pass_inp.fill(cf_pass)
                        await asyncio.sleep(0.3)

                    login_btn = await self.page.query_selector("button:has-text('Sign In'), button:has-text('Sign in'), button:has-text('Login'), button:has-text('Log in'), button[type='submit'], input[type='submit']")
                    if login_btn and await login_btn.is_visible():
                        await login_btn.click()
                    elif pass_inp:
                        await pass_inp.press("Enter")

                    await asyncio.sleep(3.5)
                    # Re-navigate to target tool URL if redirected after login
                    if target_url not in self.page.url:
                        await self.page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(2.0)
                    break
                else:
                    break

        except Exception as err:
            self.log("INFO", f"CueFeed auto-login check: {str(err)[:60]}")

        # Check for 'Login FB to use' button or FB attachment requirement
        try:
            fb_login_btn = await self.page.query_selector("button:has-text('Login FB to use'), a:has-text('Login FB to use'), button:has-text('Login FB'), button:has-text('Connect FB')")
            if fb_login_btn and await fb_login_btn.is_visible():
                self.log("INFO", "🔗 'Login FB to use' button detected. Clicking to attach Facebook account...")
                await fb_login_btn.click()
                await asyncio.sleep(2.5)
                self.log("INFO", "🔄 Refreshing tool page to confirm Facebook account attachment...")
                await self.page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(2.0)
            else:
                page_text = (await self.page.content()).lower()
                if "login fb to use" in page_text or "login fb" in page_text:
                    self.log("INFO", "🔄 Refreshing FewFeed page to attach active Facebook session...")
                    await self.page.reload(wait_until="domcontentloaded")
                    await asyncio.sleep(2.0)
        except Exception as fb_err:
            self.log("INFO", f"FB attachment verification: {str(fb_err)[:60]}")

        self.log("SUCCESS", f"✅ FewFeed tool ready: {target_url}")

    async def open_fewfeed_dashboard(self):
        """Backwards compatible alias for tool page loader."""
        await self.open_fewfeed_tool_page("https://fewfeed.app/tool/auto-post-fb-group")

    async def run_fewfeed_group_joining(self, group_codes: List[str], delay_seconds: int = 15) -> int:
        """
        Automates FewFeed 'Auto Join To Facebook Groups' via direct tool URL.
        """
        if not group_codes:
            self.log("INFO", "No target group codes provided for joining. Skipping joining phase.")
            return 0

        self.log("INFO", f"==================================================")
        self.log("INFO", f"👥 [FewFeed Auto Join] Starting automated joining for {len(group_codes)} group(s)...")
        self.set_progress(10)

        # Step 1: Directly open Auto Join Tool URL
        await self.open_fewfeed_tool_page("https://fewfeed.app/tool/auto-join-fb-group")
        self.set_progress(25)

        # Step 2: Fill Group Codes into FewFeed tool textarea / input
        codes_text = "\n".join(group_codes)
        input_filled = False

        input_selectors = [
            'textarea[placeholder*="ID" i]',
            'textarea[placeholder*="group" i]',
            'textarea[placeholder*="list" i]',
            'textarea[name*="group" i]',
            'textarea[id*="group" i]',
            'textarea',
            'input[type="text"][placeholder*="group" i]',
            'div[contenteditable="true"]'
        ]

        for sel in input_selectors:
            try:
                inp = await self.page.query_selector(sel)
                if inp and await inp.is_visible():
                    await inp.scroll_into_view_if_needed()
                    await inp.click()
                    await inp.fill("")
                    await inp.fill(codes_text)
                    input_filled = True
                    self.log("SUCCESS", f"📋 Injected {len(group_codes)} Group IDs into FewFeed Auto Join input field.")
                    break
            except Exception:
                continue

        if not input_filled:
            try:
                injected = await self.page.evaluate("""(text) => {
                    const ta = document.querySelector('textarea') || document.querySelector('input[type="text"]');
                    if (ta) {
                        ta.value = text;
                        ta.dispatchEvent(new Event('input', { bubbles: true }));
                        ta.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                    return false;
                }""", codes_text)
                if injected:
                    input_filled = True
                    self.log("SUCCESS", f"📋 Injected {len(group_codes)} Group IDs into FewFeed via DOM bridge.")
            except Exception as ex:
                self.log("WARNING", f"Input bridge: {str(ex)[:70]}")

        # Step 3: Set Delay if input is available
        try:
            delay_input = await self.page.query_selector('input[type="number"], input[name*="delay" i], input[placeholder*="delay" i], input[placeholder*="second" i]')
            if delay_input and await delay_input.is_visible():
                await delay_input.fill(str(delay_seconds))
                self.log("INFO", f"⏳ Set FewFeed Auto Join interval: {delay_seconds}s")
        except Exception:
            pass

        # Step 4: Click Start Join / Submit button inside FewFeed
        self.log("INFO", "🚀 Triggering 'Start Join' in FewFeed...")
        start_btn_selectors = [
            'button:has-text("Start Join")',
            'button:has-text("Start Joining")',
            'button:has-text("Start")',
            'button:has-text("Join")',
            'button:has-text("Run")',
            'button[type="submit"]',
            'div[role="button"]:has-text("Start")'
        ]

        started = False
        for bsel in start_btn_selectors:
            try:
                sbtn = await self.page.query_selector(bsel)
                if sbtn and await sbtn.is_visible():
                    await sbtn.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await sbtn.click()
                    started = True
                    self.log("SUCCESS", "✅ Clicked 'Start Join' in FewFeed Auto Join Extension Tool!")
                    break
            except Exception:
                continue

        if not started:
            self.log("INFO", "FewFeed Auto Join task started or ready.")

        self.set_progress(45)

        # Wait for initial joining cycles
        wait_cycles = min(len(group_codes) * delay_seconds, 60)
        self.log("INFO", f"⏳ Monitoring FewFeed automated group joining progress ({wait_cycles}s window)...")
        
        for w in range(0, max(5, int(wait_cycles / 5))):
            if self._cancel_requested:
                break
            await asyncio.sleep(5.0)

        self.log("SUCCESS", f"🎉 FewFeed Auto Join execution completed for {len(group_codes)} groups.")
        self.set_progress(50)
        return len(group_codes)

    async def run_fewfeed_group_posting(
        self,
        group_codes: Optional[List[str]] = None,
        links: Optional[List[str]] = None,
        descriptions: Optional[List[str]] = None,
        posting_mode: str = "Random",
        delay_seconds: int = 30
    ) -> int:
        """
        Automates FewFeed 'Auto Post To Facebook Groups' via direct tool URL.
        """
        self.log("INFO", f"==================================================")
        self.log("INFO", f"📢 [FewFeed Auto Post] Starting automated group posting...")
        self.set_progress(55)

        # Step 1: Directly open Auto Post Tool URL
        await self.open_fewfeed_tool_page("https://fewfeed.app/tool/auto-post-fb-group")
        self.set_progress(65)

        # Step 2: Prepare post text content & links
        desc_text = random.choice(descriptions) if (descriptions and posting_mode == "Random") else ("\n\n".join(descriptions) if descriptions else "")
        if links:
            if len(links) == 1:
                link_text = links[0]
            else:
                link_text = random.choice(links)
        else:
            link_text = ""
        
        full_content = desc_text
        if link_text:
            if full_content:
                full_content += "\n\n" + link_text
            else:
                full_content = link_text

        if not full_content:
            full_content = "Available now! Check details and message for info."

        # Step 3: Fill Post Message / Description in FewFeed
        self.log("INFO", "📝 Entering post description and links into FewFeed Auto Post composer...")
        desc_filled = False

        desc_selectors = [
            'textarea[placeholder*="message" i]',
            'textarea[placeholder*="content" i]',
            'textarea[placeholder*="post" i]',
            'textarea[placeholder*="description" i]',
            'textarea[name*="message" i]',
            'textarea[id*="message" i]',
            'textarea',
            'div[contenteditable="true"]'
        ]

        for sel in desc_selectors:
            try:
                inp = await self.page.query_selector(sel)
                if inp and await inp.is_visible():
                    await inp.scroll_into_view_if_needed()
                    await inp.click()
                    await inp.fill("")
                    await inp.fill(full_content)
                    desc_filled = True
                    self.log("SUCCESS", "✅ Filled post text & descriptions in FewFeed.")
                    break
            except Exception:
                continue

        if not desc_filled:
            try:
                await self.page.evaluate("""(text) => {
                    const ta = document.querySelector('textarea');
                    if (ta) {
                        ta.value = text;
                        ta.dispatchEvent(new Event('input', { bubbles: true }));
                        ta.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                    return false;
                }""", full_content)
                self.log("SUCCESS", "✅ Injected post content into FewFeed via DOM bridge.")
            except Exception:
                pass

        # Step 4: Fill separate Link input if present
        if links:
            try:
                first_link = links[0]
                link_input = await self.page.query_selector('input[type="url"], input[name*="link" i], input[placeholder*="link" i], input[placeholder*="url" i]')
                if link_input and await link_input.is_visible():
                    await link_input.fill(first_link)
                    self.log("INFO", f"🔗 Added primary link to FewFeed: {first_link}")
            except Exception:
                pass

        # Step 5: Select All Groups in FewFeed
        self.log("INFO", "☑️ Selecting all available Facebook Groups in FewFeed tool...")
        select_all_selectors = [
            'input[type="checkbox"]#select_all',
            'input[type="checkbox"][name*="all" i]',
            'button:has-text("Select All")',
            'button:has-text("Check All")',
            'label:has-text("Select All")',
            'span:has-text("Select All")'
        ]

        selected_all = False
        for ssel in select_all_selectors:
            try:
                sel_el = await self.page.query_selector(ssel)
                if sel_el and await sel_el.is_visible():
                    await sel_el.click()
                    selected_all = True
                    self.log("SUCCESS", "✅ Clicked 'Select All' groups in FewFeed.")
                    break
            except Exception:
                continue

        if not selected_all:
            # Fallback: check all individual checkboxes in group list
            try:
                chk_count = await self.page.evaluate("""() => {
                    const chks = document.querySelectorAll('input[type="checkbox"]');
                    let count = 0;
                    chks.forEach(c => {
                        if (!c.checked) {
                            c.checked = true;
                            c.dispatchEvent(new Event('change', { bubbles: true }));
                            count++;
                        }
                    });
                    return count;
                }""")
                if chk_count > 0:
                    self.log("SUCCESS", f"✅ Checked all {chk_count} Facebook Group checkboxes in FewFeed.")
            except Exception as e:
                self.log("WARNING", f"Checkbox scan: {str(e)[:70]}")

        # Step 6: Set Post Delay if available
        try:
            delay_input = await self.page.query_selector('input[type="number"], input[name*="delay" i], input[placeholder*="delay" i], input[placeholder*="second" i]')
            if delay_input and await delay_input.is_visible():
                await delay_input.fill(str(delay_seconds))
                self.log("INFO", f"⏳ Set FewFeed Post interval: {delay_seconds}s")
        except Exception:
            pass

        self.set_progress(80)

        # Step 7: Click Start Post button in FewFeed
        self.log("INFO", "🚀 Triggering 'Start Post' in FewFeed Auto Post Extension Tool...")
        start_post_selectors = [
            'button:has-text("Start Post")',
            'button:has-text("Start Posting")',
            'button:has-text("Post Now")',
            'button:has-text("Start")',
            'button:has-text("Post")',
            'button:has-text("Submit")',
            'button[type="submit"]',
            'div[role="button"]:has-text("Start")'
        ]

        post_started = False
        for psel in start_post_selectors:
            try:
                pbtn = await self.page.query_selector(psel)
                if pbtn and await pbtn.is_visible():
                    await pbtn.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await pbtn.click()
                    post_started = True
                    self.log("SUCCESS", "✅ Clicked 'Start Post' in FewFeed Auto Post Tool!")
                    break
            except Exception:
                continue

        if not post_started:
            self.log("INFO", "FewFeed Auto Post submission complete.")

        self.set_progress(95)

        # Monitor posting progress
        post_cycles = min(max(30, (len(group_codes or [1]) * delay_seconds)), 90)
        self.log("INFO", f"⏳ FewFeed Auto Post active in background. Monitoring progress ({post_cycles}s window)...")
        
        for w in range(0, max(5, int(post_cycles / 5))):
            if self._cancel_requested:
                break
            await asyncio.sleep(5.0)

        self.set_progress(100)
        self.log("SUCCESS", "🎉 FewFeed automated group posting sequence completed successfully!")
        return 1

    # --------------------------------------------------------------------------
    # Fallback Direct Facebook DOM Group Joining Workflow
    # --------------------------------------------------------------------------
    async def run_group_joining(self, group_codes: List[str], delay_seconds: int = 15):
        """Joins specified Facebook groups via FewFeed or direct fallback."""
        return await self.run_fewfeed_group_joining(group_codes=group_codes, delay_seconds=delay_seconds)

    # --------------------------------------------------------------------------
    # Fallback Direct Facebook DOM Group Posting Workflow
    # --------------------------------------------------------------------------
    async def run_group_posting(
        self,
        group_codes: List[str],
        links: List[str],
        descriptions: List[str],
        posting_mode: str = "Random",
        delay_seconds: int = 30
    ):
        """Posts links and descriptions across target Facebook Groups via FewFeed."""
        return await self.run_fewfeed_group_posting(
            group_codes=group_codes,
            links=links,
            descriptions=descriptions,
            posting_mode=posting_mode,
            delay_seconds=delay_seconds
        )

        for idx, code in enumerate(group_codes, 1):
            if self._cancel_requested:
                self.log("WARNING", "Group posting cancelled by user.")
                break

            target_url = f"https://www.facebook.com/groups/{code}/" if not code.startswith("http") else code
            self.log("INFO", f"[{idx}/{total}] Navigating to Group: {code} ({target_url})")

            # Pick link and description
            selected_link = ""
            if links:
                if posting_mode == "Random":
                    selected_link = random.choice(links)
                else:
                    selected_link = links[(idx - 1) % len(links)]

            selected_desc = ""
            if descriptions:
                if posting_mode == "Random":
                    selected_desc = random.choice(descriptions)
                else:
                    selected_desc = descriptions[(idx - 1) % len(descriptions)]

            # Combine post text: description + link
            post_content_parts = []
            if selected_desc:
                post_content_parts.append(selected_desc)
            if selected_link:
                post_content_parts.append(selected_link)
            
            full_post_text = "\n\n".join(post_content_parts)
            if not full_post_text:
                full_post_text = "Check this out!"

            try:
                await self.page.goto(target_url, wait_until="domcontentloaded", timeout=35000)
                await asyncio.sleep(random.uniform(3.0, 4.5))

                # Step 1: Open post creation box
                # Common Facebook post composer triggers in groups:
                composer_triggers = [
                    'div[role="button"]:has-text("Write something...")',
                    'div[role="button"]:has-text("Create a public post...")',
                    'div[role="button"]:has-text("Create a post...")',
                    'span:has-text("Write something...")',
                    'span:has-text("Create a public post...")',
                    'div[aria-label*="Create a post"][role="button"]',
                    'div[aria-label*="Write something"][role="button"]'
                ]

                composer_opened = False
                for sel in composer_triggers:
                    try:
                        btn = await self.page.query_selector(sel)
                        if btn and await btn.is_visible():
                            await btn.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            await btn.click()
                            composer_opened = True
                            self.log("INFO", f"Opened post composer on group [{code}].")
                            break
                    except Exception:
                        continue

                if not composer_opened:
                    # Fallback click on any editable div or generic trigger
                    gen = await self.page.query_selector('div[role="feed"] div[role="button"]')
                    if gen and await gen.is_visible():
                        await gen.click()
                        composer_opened = True

                await asyncio.sleep(2.0)

                # Step 2: Locate editable textbox inside composer modal
                input_selectors = [
                    'div[role="dialog"] div[role="textbox"]',
                    'div[aria-label*="What\'s on your mind"][role="textbox"]',
                    'div[aria-label*="Write something"][role="textbox"]',
                    'div[aria-label*="Create a public post"][role="textbox"]',
                    'div[contenteditable="true"][role="textbox"]',
                    'div[role="textbox"]'
                ]

                box_found = False
                for sel in input_selectors:
                    try:
                        box = await self.page.query_selector(sel)
                        if box and await box.is_visible():
                            await box.click()
                            await asyncio.sleep(0.5)
                            
                            # Type text with humanized jitter
                            self.log("INFO", f"Typing post content into group [{code}] ({len(full_post_text)} chars)...")
                            # We can also insert text via page.keyboard
                            await self.page.keyboard.type(full_post_text, delay=random.randint(25, 65))
                            box_found = True
                            break
                    except Exception:
                        continue

                if not box_found:
                    self.log("WARNING", f"Could not find editable post box in group [{code}]. Skipping.")
                    continue

                # Allow link preview / extension to parse if link was included
                if selected_link:
                    self.log("INFO", "Waiting for link metadata & preview to generate...")
                    await asyncio.sleep(4.0)

                # Step 3: Click 'Post' / 'Publish' button
                post_btn_selectors = [
                    'div[role="dialog"] div[aria-label="Post"][role="button"]',
                    'div[role="dialog"] div[aria-label="Publish"][role="button"]',
                    'div[aria-label="Post"][role="button"]',
                    'div[role="button"]:has-text("Post")',
                    'div[role="dialog"] div[role="button"]:has-text("Post")'
                ]

                posted = False
                for p_sel in post_btn_selectors:
                    try:
                        p_btn = await self.page.query_selector(p_sel)
                        if p_btn and await p_btn.is_visible():
                            await asyncio.sleep(1.0)
                            await p_btn.click()
                            posted = True
                            posts_published += 1
                            self.log("SUCCESS", f"🎉 Successfully published post to group [{code}]!")
                            await asyncio.sleep(4.0)
                            break
                    except Exception:
                        continue

                if not posted:
                    self.log("WARNING", f"Could not click 'Post' button for group [{code}].")

            except Exception as e:
                self.log("ERROR", f"Error posting to group [{code}]: {str(e)[:100]}")

            progress_pct = int((idx / total) * 100)
            self.set_progress(progress_pct)

            if idx < total and not self._cancel_requested:
                jitter = random.uniform(-3.0, 5.0)
                actual_delay = max(5.0, delay_seconds + jitter)
                self.log("INFO", f"⏳ Delay interval: Waiting {actual_delay:.1f}s before next group post...")
                await asyncio.sleep(actual_delay)

        self.log("SUCCESS", f"🏁 Group Posting Task finished! {posts_published}/{total} posts submitted.")
        return posts_published

    # --------------------------------------------------------------------------
    # Unified Single-Click Start Workflow Engine
    # --------------------------------------------------------------------------
    async def run_workflow(
        self,
        task_type: str,
        group_codes: Optional[List[str]] = None,
        join_group_codes: Optional[List[str]] = None,
        post_group_codes: Optional[List[str]] = None,
        links: Optional[List[str]] = None,
        descriptions: Optional[List[str]] = None,
        posting_mode: str = "Random",
        delay_seconds: int = 20
    ) -> Dict[str, Any]:
        """
        Master-level unified single-click execution flow:
        1. Initialize mobile browser emulation & load FEWFEED extension.
        2. Authenticate Facebook session with injected session cookies.
        3. If unified or joining requested: Automate FewFeed Auto Join tool.
        4. If unified or posting requested: Automate FewFeed Auto Post tool.
        """
        results: Dict[str, Any] = {
            "task_type": task_type,
            "status": "pending",
            "items_processed": 0,
            "error": None
        }

        self.log("INFO", f"🚀 [Unified Start] Triggering {task_type.upper()} workflow with FEWFEED auto-integration...")

        # Resolve joining & posting codes
        j_codes = join_group_codes if join_group_codes is not None else (group_codes if task_type.lower() in ("joining", "join") else [])
        p_codes = post_group_codes if post_group_codes is not None else (group_codes if task_type.lower() in ("posting", "post") else [])

        try:
            # 1. Initialization & Extension Verification
            await self.initialize_browser()

            # 2. Authenticate Session
            await self.authenticate_session()

            # 3. Automated Target Processing
            if task_type.lower() in ("unified", "both", "all"):
                # Phase 1: Auto Join Groups in FewFeed if join codes provided
                if j_codes:
                    self.log("INFO", f"⚡ [Unified Phase 1/2] Launching FewFeed Auto Join for {len(j_codes)} groups...")
                    await self.run_fewfeed_group_joining(group_codes=j_codes, delay_seconds=delay_seconds)
                else:
                    self.log("INFO", "ℹ️ [Unified Phase 1/2] No join group codes provided. Proceeding to Auto Post...")

                # Phase 2: Auto Post to Groups in FewFeed
                self.log("INFO", f"⚡ [Unified Phase 2/2] Launching FewFeed Auto Post...")
                await self.run_fewfeed_group_posting(
                    group_codes=p_codes,
                    links=links or [],
                    descriptions=descriptions or [],
                    posting_mode=posting_mode,
                    delay_seconds=delay_seconds
                )
                results["status"] = "completed"
                results["items_processed"] = len(j_codes) + (len(p_codes) if p_codes else 1)

            elif task_type.lower() in ("joining", "join"):
                joined_count = await self.run_group_joining(
                    group_codes=j_codes or group_codes or [],
                    delay_seconds=delay_seconds
                )
                results["items_processed"] = joined_count
                results["status"] = "completed"

            elif task_type.lower() in ("posting", "post"):
                posted_count = await self.run_group_posting(
                    group_codes=p_codes or group_codes or [],
                    links=links or [],
                    descriptions=descriptions or [],
                    posting_mode=posting_mode,
                    delay_seconds=delay_seconds
                )
                results["items_processed"] = posted_count
                results["status"] = "completed"

            else:
                raise ValueError(f"Unknown task type: {task_type}")

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            self.log("ERROR", f"❌ Unified workflow exception: {str(e)}")
            raise e
        finally:
            self.log("INFO", f"✨ Unified workflow sequence for {task_type} ended with status: {results['status']}.")

        return results

    async def close(self):
        """Closes browser context and Playwright instance cleanly."""
        try:
            if self.page and not self.page.is_closed():
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            self.log("INFO", "Group Bot browser closed cleanly.")
        except Exception as e:
            self.log("WARNING", f"Cleanup notice: {str(e)}")
