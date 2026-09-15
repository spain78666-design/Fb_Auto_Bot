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
    "width": 393,
    "height": 851,
    "pixelRatio": 3.0
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

def get_chrome_webdriver_mobile_emulation_config(ext_path: Optional[str] = None, user_data_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns Python Chrome WebDriver experimental options dictionary for mobileEmulation.
    Includes deviceMetrics (width: 393, height: 851, pixelRatio: 3.0) and genuine mobile userAgent.
    """
    config = {
        "mobileEmulation": MOBILE_EMULATION_EXPERIMENTAL_OPTIONS,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--window-size=393,851",
            "--enable-viewport",
            "--force-device-scale-factor=3.0",
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
            "--window-size=393,851",
            "--enable-viewport",
            "--force-device-scale-factor=3.0",
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
            profile_dir = os.path.join(get_base_dir(), "profiles", f"{self.account_data.get('id')}_group_mobile")

        if profile_dir:
            os.makedirs(profile_dir, exist_ok=True)

        # Launch browser with strict mobile metrics and mobile emulation
        for ch in ["chrome", "msedge", None]:
            try:
                kwargs = {
                    "user_data_dir": profile_dir,
                    "headless": False,  # Extensions require headful mode in Chromium
                    "args": launch_args,
                    "ignore_default_args": ignore_default_args,
                    "proxy": proxy_cfg,
                    "user_agent": MOBILE_SMARTPHONE_USER_AGENT,
                    "viewport": {"width": 393, "height": 851},
                    "screen": {"width": 393, "height": 851},
                    "device_scale_factor": 3.0,
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
                if "Executable doesn't exist" in str(ex) or "Channel" in str(ex):
                    continue
                self.log("WARNING", f"Browser launch notice with {ch}: {str(ex)[:100]}")

        if not self.context:
            raise RuntimeError("Failed to launch Chrome or Edge. Ensure Google Chrome is installed.")

        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

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
                raise RuntimeError("Facebook Checkpoint encountered. Manual verification required.")
            raise RuntimeError("Account cookies expired or invalid. Please update cookies.")
        self.log("SUCCESS", "Facebook authentication confirmed.")

    # --------------------------------------------------------------------------
    # Group Joining Workflow
    # --------------------------------------------------------------------------
    async def run_group_joining(self, group_codes: List[str], delay_seconds: int = 15):
        """Joins specified Facebook groups sequentially."""
        total = len(group_codes)
        self.log("INFO", f"🚀 Starting Group Joining Workflow for {total} group(s)...")
        joined_count = 0

        for idx, code in enumerate(group_codes, 1):
            if self._cancel_requested:
                self.log("WARNING", "Group joining cancelled by user.")
                break

            target_url = f"https://www.facebook.com/groups/{code}/" if not code.startswith("http") else code
            self.log("INFO", f"[{idx}/{total}] Navigating to Group: {code} ({target_url})")

            try:
                await self.page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(random.uniform(2.5, 4.0))

                # Look for 'Join group' or 'Join' button
                join_selectors = [
                    'div[aria-label="Join group"][role="button"]',
                    'div[aria-label="Join Group"][role="button"]',
                    'div[aria-label="Join"][role="button"]',
                    'div[role="button"]:has-text("Join group")',
                    'div[role="button"]:has-text("Join Group")',
                    'div[role="button"]:has-text("Join")',
                    'span:has-text("Join group")',
                    'span:has-text("Join Group")'
                ]

                # Check if already a member or pending
                already_joined = False
                for status_sel in ['div[aria-label="Joined"][role="button"]', 'div[aria-label="Pending"][role="button"]', 'div[role="button"]:has-text("Joined")', 'div[role="button"]:has-text("Pending")']:
                    try:
                        el = await self.page.query_selector(status_sel)
                        if el and await el.is_visible():
                            self.log("INFO", f"Group [{code}] is already Joined/Pending. Skipping.")
                            already_joined = True
                            joined_count += 1
                            break
                    except Exception:
                        pass

                if already_joined:
                    continue

                btn_found = False
                for sel in join_selectors:
                    try:
                        btn = await self.page.query_selector(sel)
                        if btn and await btn.is_visible():
                            await btn.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            await btn.click()
                            btn_found = True
                            joined_count += 1
                            self.log("SUCCESS", f"✅ Clicked 'Join' button on group [{code}]!")
                            await asyncio.sleep(2.0)

                            # Handle membership questions modal if it pops up
                            # Look for 'Submit' or answer field
                            submit_btn = await self.page.query_selector('div[aria-label="Submit"][role="button"], div[role="button"]:has-text("Submit")')
                            if submit_btn and await submit_btn.is_visible():
                                await submit_btn.click()
                                self.log("INFO", f"Submitted membership answer form for [{code}].")
                            break
                    except Exception as e:
                        continue

                if not btn_found:
                    self.log("WARNING", f"Could not locate 'Join' button on group [{code}]. May require approval or invite.")

            except Exception as e:
                self.log("ERROR", f"Failed to join group [{code}]: {str(e)[:100]}")

            progress_pct = int((idx / total) * 100)
            self.set_progress(progress_pct)

            if idx < total and not self._cancel_requested:
                jitter = random.uniform(-2.0, 3.0)
                actual_delay = max(2.0, delay_seconds + jitter)
                self.log("INFO", f"⏳ Delay interval: Waiting {actual_delay:.1f}s before next group...")
                await asyncio.sleep(actual_delay)

        self.log("SUCCESS", f"🎉 Group Joining Task finished! {joined_count}/{total} processed.")
        return joined_count

    # --------------------------------------------------------------------------
    # Group Posting Workflow (Links & Descriptions)
    # --------------------------------------------------------------------------
    async def run_group_posting(
        self,
        group_codes: List[str],
        links: List[str],
        descriptions: List[str],
        posting_mode: str = "Random",
        delay_seconds: int = 30
    ):
        """Posts links and descriptions across target Facebook Groups."""
        total = len(group_codes)
        self.log("INFO", f"🚀 Starting Group Posting Workflow for {total} group(s)...")
        self.log("INFO", f"🔗 Available Links: {len(links)} | 📝 Descriptions: {len(descriptions)} | Mode: {posting_mode}")
        posts_published = 0

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
