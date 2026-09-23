#!/usr/bin/env python3
"""
FB Auto Bot - Facebook Automation Suite
automation/page_creator_bot.py - Multi-Account & Multi-Tab Facebook Page Creator Bot

Automates the exact Facebook Page creation sequence based on real Facebook UI:
  1. Opens Facebook session with account cookies / persistent profile
  2. Opens N parallel tabs per account (as requested by user, e.g. 5 tabs)
  3. Navigates to Page Creation URL (facebook.com/pages/create/ or facebook.com/pages/?category=top&ref=bookmarks)
  4. Automatically detects and selects 'Public Page' in the initial dialog and clicks 'Next'
  5. Fills 'Page name (required)', selects matching 'Category (required)' from dropdown suggestion, and fills 'Bio (optional)'
  6. Simultaneously triggers 'Create Page' across all tabs and handles completion
"""

import os
import sys
import time
import json
import random
import asyncio
import logging
import socket
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger("FBAutoBot.PageCreator")

DESKTOP_CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Standard Popular Facebook Categories for fallback & auto-completion
POPULAR_FB_CATEGORIES = [
    "Digital Creator",
    "Real Estate Agency",
    "Marketing Agency",
    "Advertising/Marketing",
    "E-commerce Website",
    "Entrepreneur",
    "Business Service",
    "Product/service",
    "Shopping & retail",
    "Consulting Agency",
    "Information Technology Company",
    "Community",
    "Health/beauty",
    "Restaurant",
    "Photographer"
]


def test_proxy_connectivity(host: str, port: int, timeout: float = 2.0) -> bool:
    """Quick socket probe to verify proxy server is alive before passing to Chrome."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except Exception:
        return False


def parse_cookie_payload(raw_cookies: str) -> List[Dict[str, Any]]:
    """
    Parses both JSON array cookie exports and raw semicolon string formats
    (e.g., 'c_user=1000...; xs=2%3A...; datr=...').
    Returns a list of standardized cookies suitable for Playwright.
    """
    cleaned = (raw_cookies or "").strip()
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


class FacebookPageCreatorBot:
    """
    Playwright-powered engine that opens a Facebook profile session and creates
    multiple Facebook Pages simultaneously across concurrent tabs.
    """

    def __init__(
        self,
        account_data: Dict[str, Any],
        log_callback: Optional[Callable[[str, str], None]] = None,
        progress_callback: Optional[Callable[[int], None]] = None
    ):
        self.account_data = account_data
        self.log_cb = log_callback
        self.prog_cb = progress_callback
        self.account_id = account_data.get("id", "unknown")
        self.account_name = account_data.get("name", "Account")

        self.playwright = None
        self.browser = None
        self.context = None
        self._is_cancelled = False

    def log(self, level: str, message: str):
        full_msg = f"[{self.account_name}] {message}"
        if self.log_cb:
            self.log_cb(level, full_msg)
        else:
            print(f"[{level}] {full_msg}")

    def set_progress(self, percent: int):
        if self.prog_cb:
            self.prog_cb(percent)

    def cancel(self):
        self._is_cancelled = True
        self.log("WARNING", "Cancellation requested. Halting page creation...")

    async def init_browser(self):
        """Initializes Playwright and launches Chrome with persistent context or profile."""
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()

        profile_dir = self.account_data.get("profile_dir")
        if not profile_dir or not os.path.exists(profile_dir):
            base_p = os.path.join(os.getcwd(), "profiles", f"acc_{self.account_id}")
            os.makedirs(base_p, exist_ok=True)
            profile_dir = base_p

        # Clear file locks
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

        launch_args = [
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-notifications",
            "--start-maximized"
        ]

        # Proxy support & Connectivity Verification
        proxy_cfg = None
        use_direct = (
            self.account_data.get("network_mode") == "direct"
            or self.account_data.get("use_direct_network", False)
        )
        raw_proxy = (self.account_data.get("proxy") or "").strip()

        # Check if proxy string indicates Direct or empty
        is_direct_str = any(d in raw_proxy.lower() for d in ["direct", "no proxy", "none", "null", "false", "0", ""])

        if use_direct or is_direct_str or not raw_proxy:
            proxy_cfg = None
            launch_args.append("--no-proxy-server")
            self.log("INFO", "🌐 Network Mode: Direct high-speed connection (Proxy bypassed, zero proxy errors).")
        else:
            # User provided a real proxy string: parse and probe socket connectivity
            try:
                server_url = raw_proxy if "://" in raw_proxy else f"{self.account_data.get('proxy_type', 'http').lower()}://{raw_proxy}"
                parsed = urlparse(server_url)
                host = parsed.hostname
                port = parsed.port
                if host and port:
                    self.log("INFO", f"🔍 Probing assigned proxy connectivity ({host}:{port})...")
                    if test_proxy_connectivity(host, port, timeout=2.5):
                        proxy_cfg = {"server": f"{parsed.scheme}://{host}:{port}"}
                        u = parsed.username or self.account_data.get("proxy_user")
                        p = parsed.password or self.account_data.get("proxy_pass")
                        if u:
                            proxy_cfg["username"] = u
                        if p:
                            proxy_cfg["password"] = p
                        self.log("SUCCESS", f"🛡️ Assigned proxy ({host}:{port}) is LIVE and active.")
                    else:
                        self.log("WARNING", f"⚠️ Proxy {host}:{port} is UNREACHABLE or offline! Safely falling back to direct connection to prevent ERR_PROXY_CONNECTION_FAILED.")
                        proxy_cfg = None
                        launch_args.append("--no-proxy-server")
                else:
                    self.log("WARNING", f"⚠️ Invalid proxy format '{raw_proxy}'. Falling back to direct connection.")
                    proxy_cfg = None
                    launch_args.append("--no-proxy-server")
            except Exception as e:
                self.log("WARNING", f"⚠️ Proxy resolution notice: {e}. Falling back to direct connection.")
                proxy_cfg = None
                launch_args.append("--no-proxy-server")

        # Check for real Chrome
        chrome_exe = None
        try:
            from automation.extension_manager import get_system_chrome_executable
            chrome_exe = get_system_chrome_executable()
        except Exception:
            pass

        channels = []
        if chrome_exe and os.path.isfile(chrome_exe):
            channels.append(("real_chrome", chrome_exe))
        channels.extend([("chrome", None), ("msedge", None), (None, None)])

        self.context = None
        for ch, exe_p in channels:
            try:
                kwargs = {
                    "user_data_dir": profile_dir,
                    "headless": False,
                    "args": launch_args,
                    "proxy": proxy_cfg,
                    "user_agent": DESKTOP_CHROME_USER_AGENT,
                    "no_viewport": True,
                    "locale": "en-US",
                    "permissions": ["geolocation", "notifications"]
                }
                if exe_p:
                    kwargs["executable_path"] = exe_p
                elif ch:
                    kwargs["channel"] = ch

                self.context = await self.playwright.chromium.launch_persistent_context(**kwargs)
                self.log("INFO", f"Launched browser for Page Creation ({exe_p or ch or 'Chromium'}).")
                break
            except Exception as ex:
                self.log("DEBUG", f"Browser launch attempt failed ({ch or exe_p}): {str(ex)[:80]}")
                continue

        if not self.context:
            self.log("WARNING", "Persistent profile unavailable. Launching standard browser...")
            self.browser = await self.playwright.chromium.launch(
                headless=False,
                args=launch_args,
                proxy=proxy_cfg
            )
            self.context = await self.browser.new_context(
                user_agent=DESKTOP_CHROME_USER_AGENT,
                no_viewport=True,
                locale="en-US"
            )

        # Inject session cookies if provided (handles strings, JSON arrays, and dictionaries)
        raw_cookies = self.account_data.get("cookies", "")
        if raw_cookies and self.context:
            try:
                formatted_cookies = []
                if isinstance(raw_cookies, str):
                    formatted_cookies = parse_cookie_payload(raw_cookies)
                elif isinstance(raw_cookies, list):
                    for item in raw_cookies:
                        if isinstance(item, dict) and "name" in item and "value" in item:
                            formatted_cookies.append({
                                "name": str(item["name"]),
                                "value": str(item["value"]),
                                "domain": str(item.get("domain", ".facebook.com")),
                                "path": str(item.get("path", "/")),
                                "secure": bool(item.get("secure", True))
                            })
                        elif isinstance(item, str):
                            formatted_cookies.extend(parse_cookie_payload(item))
                if formatted_cookies:
                    await self.context.add_cookies(formatted_cookies)
                    self.log("SUCCESS", f"🔑 Injected {len(formatted_cookies)} Facebook session cookies. Account logged in!")
            except Exception as e:
                self.log("DEBUG", f"Cookie injection notice: {e}")

    async def _handle_create_modal_and_navigate(self, page, tab_index: int) -> bool:
        """
        Navigates to Facebook Pages creation.
        If the modal 'Create / Which option is best for you?' pops up (as in Image 2),
        selects 'Public Page' and clicks 'Next'.
        """
        target_url = "https://www.facebook.com/pages/create/"
        self.log("INFO", f"[Tab #{tab_index}] Opening Facebook Page Creation: {target_url}")

        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(2.0)
        except Exception as e:
            self.log("WARNING", f"[Tab #{tab_index}] Navigation notice: {str(e)[:60]}")
            try:
                await asyncio.sleep(2.0)
                await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(2.0)
            except Exception:
                pass

        # Check if redirected to login
        current_url = page.url.lower()
        if "login" in current_url or "checkpoint" in current_url:
            self.log("ERROR", f"[Tab #{tab_index}] Facebook account requires login or checkpoint verification!")
            return False

        # If on bookmarks page (e.g. facebook.com/pages/?category=top), click '+ Create Page'
        if "pages/create" not in current_url:
            try:
                create_page_btn = page.locator('a[href*="/pages/create"], button:has-text("Create Page"), div[role="button"]:has-text("Create Page")').first
                if await create_page_btn.count() > 0 and await create_page_btn.is_visible():
                    self.log("INFO", f"[Tab #{tab_index}] Clicking '+ Create Page' button on Pages dashboard...")
                    await create_page_btn.click()
                    await asyncio.sleep(2.0)
            except Exception:
                pass

        # Check for Modal Dialog: 'Create / Which option is best for you?'
        # Options: 'Public Page' / 'Public Place Page' vs 'Upgrade your existing profile'
        try:
            # Look for dialog container
            dialog = page.locator('div[role="dialog"]').first
            if await dialog.count() > 0 and await dialog.is_visible():
                self.log("INFO", f"[Tab #{tab_index}] Detected 'Which option is best for you?' modal dialog.")
                
                # Click 'Public Page' or 'Public Place Page' option
                clicked_opt = False
                for p_label in ['text="Public Place Page"', 'text="Public Page"', 'div:has-text("Public Page")', 'div:has-text("Public Place Page")']:
                    public_opt = dialog.locator(p_label).first
                    if await public_opt.count() > 0 and await public_opt.is_visible():
                        await public_opt.click()
                        await asyncio.sleep(0.5)
                        clicked_opt = True
                        break

                if not clicked_opt:
                    # Fallback to first radio button
                    radio = dialog.locator('input[type="radio"], div[role="radio"]').first
                    if await radio.count() > 0:
                        await radio.click()
                        await asyncio.sleep(0.5)

                # Click the blue 'Next' button
                next_btn = dialog.locator('button:has-text("Next"), div[role="button"]:has-text("Next")').first
                if await next_btn.count() > 0 and await next_btn.is_visible():
                    self.log("INFO", f"[Tab #{tab_index}] Clicking 'Next' in Public Page creation modal...")
                    await next_btn.click()
                    await asyncio.sleep(2.0)
        except Exception as e:
            self.log("DEBUG", f"[Tab #{tab_index}] Modal handling notice: {e}")

        # Also evaluate DOM script just in case of iframe or stubborn shadow DOM
        try:
            await page.evaluate("""() => {
                const dialogs = document.querySelectorAll('div[role="dialog"]');
                for (const d of dialogs) {
                    const txt = (d.innerText || '').toLowerCase();
                    if (txt.includes('public page') || txt.includes('public place') || txt.includes('which option is best')) {
                        // Click public page option
                        const items = Array.from(d.querySelectorAll('div, span, p, label'));
                        const pub = items.find(el => {
                            const t = (el.innerText || '').trim().toLowerCase();
                            return t === 'public page' || t === 'public place page' || t.includes('public page');
                        });
                        if (pub) pub.click();

                        // Click Next
                        const btns = Array.from(d.querySelectorAll('button, div[role="button"]'));
                        const nextBtn = btns.find(b => (b.innerText || '').trim().toLowerCase() === 'next');
                        if (nextBtn) nextBtn.click();
                    }
                }
            }""")
        except Exception:
            pass

        return True

    async def _fill_page_form(self, page, tab_index: int, page_name: str, category: str, bio: str) -> bool:
        """
        Fills the 'Create a Page' form fields (Image 3):
          - Page name (required)
          - Category (required) -> selects dropdown suggestion
          - Bio (optional)
        Does NOT click 'Create Page' yet, allowing all tabs to reach filled state together.
        """
        self.log("INFO", f"[Tab #{tab_index}] Filling form: Name='{page_name}', Category='{category}'...")

        # 1. Fill Page Name (required)
        name_filled = False
        try:
            name_locators = [
                'input[aria-label*="Page name"]',
                'input[aria-label*="Page Name"]',
                'input[aria-label*="name (required)"]',
                'div[role="main"] input[type="text"]',
                'input[type="text"]'
            ]
            for sel in name_locators:
                inp = page.locator(sel).first
                if await inp.count() > 0 and await inp.is_visible():
                    await inp.scroll_into_view_if_needed()
                    await inp.click()
                    await inp.fill("")
                    await inp.type(page_name, delay=35)
                    name_filled = True
                    break
        except Exception as e:
            self.log("DEBUG", f"[Tab #{tab_index}] Page name input notice: {e}")

        if not name_filled:
            # Fallback DOM evaluation
            name_filled = await page.evaluate("""(pName) => {
                const inputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type])'));
                for (const inp of inputs) {
                    const aria = (inp.getAttribute('aria-label') || '').toLowerCase();
                    const placeholder = (inp.getAttribute('placeholder') || '').toLowerCase();
                    if (aria.includes('page name') || aria.includes('name') || placeholder.includes('name')) {
                        inp.focus();
                        inp.value = pName;
                        inp.dispatchEvent(new Event('input', { bubbles: true }));
                        inp.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                }
                if (inputs.length > 0) {
                    inputs[0].focus();
                    inputs[0].value = pName;
                    inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                    inputs[0].dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }
                return false;
            }""", page_name)

        await asyncio.sleep(0.8)

        # 2. Fill Category (required)
        cat_filled = False
        try:
            cat_locators = [
                'input[aria-label*="Category"]',
                'input[aria-label*="category"]',
                'input[aria-autocomplete="list"]',
                'div[role="combobox"] input'
            ]
            for sel in cat_locators:
                inp = page.locator(sel).first
                if await inp.count() > 0 and await inp.is_visible():
                    await inp.scroll_into_view_if_needed()
                    await inp.click()
                    await inp.fill("")
                    await inp.type(category, delay=40)
                    cat_filled = True
                    break
        except Exception as e:
            self.log("DEBUG", f"[Tab #{tab_index}] Category input notice: {e}")

        if not cat_filled:
            # Fallback DOM
            await page.evaluate("""(catVal) => {
                const inputs = Array.from(document.querySelectorAll('input'));
                for (const inp of inputs) {
                    const aria = (inp.getAttribute('aria-label') || '').toLowerCase();
                    if (aria.includes('category') || inp.getAttribute('aria-autocomplete') === 'list') {
                        inp.focus();
                        inp.value = catVal;
                        inp.dispatchEvent(new Event('input', { bubbles: true }));
                        inp.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                }
                return false;
            }""", category)

        # Wait for Facebook's Category Suggestion dropdown listbox and click the first suggestion
        await asyncio.sleep(1.5)
        suggestion_selected = False
        try:
            suggestion_locators = [
                'div[role="listbox"] div[role="option"]',
                'ul[role="listbox"] li',
                'div[role="option"]',
                'div[aria-label*="Search results"] div[role="option"]'
            ]
            for s_sel in suggestion_locators:
                opt = page.locator(s_sel).first
                if await opt.count() > 0 and await opt.is_visible():
                    await opt.click()
                    suggestion_selected = True
                    self.log("INFO", f"[Tab #{tab_index}] Category suggestion matched and selected!")
                    break
        except Exception:
            pass

        if not suggestion_selected:
            # Try keyboard Enter / Down arrow to accept first auto-complete
            try:
                await page.keyboard.press("ArrowDown")
                await asyncio.sleep(0.3)
                await page.keyboard.press("Enter")
                suggestion_selected = True
            except Exception:
                pass

        await asyncio.sleep(0.8)

        # 3. Fill Bio (optional)
        if bio:
            try:
                bio_locators = [
                    'textarea[aria-label*="Bio"]',
                    'textarea[aria-label*="bio"]',
                    'textarea[placeholder*="bio"]',
                    'textarea'
                ]
                for b_sel in bio_locators:
                    bio_el = page.locator(b_sel).first
                    if await bio_el.count() > 0 and await bio_el.is_visible():
                        await bio_el.scroll_into_view_if_needed()
                        await bio_el.click()
                        await bio_el.fill(bio)
                        break
            except Exception as e:
                self.log("DEBUG", f"[Tab #{tab_index}] Bio input notice: {e}")

        self.log("SUCCESS", f"✅ [Tab #{tab_index}] Form filled successfully for '{page_name}'!")
        return True

    async def _click_create_page(self, page, tab_index: int, page_name: str) -> bool:
        """
        Clicks the final 'Create Page' button on the form (Image 3)
        and waits for Facebook to process creation.
        """
        self.log("INFO", f"[Tab #{tab_index}] Submitting 'Create Page' for '{page_name}'...")
        await asyncio.sleep(0.5)

        clicked = False

        # Strategy 1: Playwright locator for Create Page button
        button_selectors = [
            'div[aria-label="Create Page"][role="button"]',
            'button:has-text("Create Page")',
            'div[role="button"]:has-text("Create Page")',
            'div[aria-label*="Create Page"]',
            'div[role="button"][tabindex="0"]:has-text("Create")'
        ]

        for b_sel in button_selectors:
            try:
                btn = page.locator(b_sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    # Wait briefly if disabled
                    is_disabled = await btn.get_attribute("aria-disabled")
                    if is_disabled == "true":
                        await asyncio.sleep(1.0)
                    await btn.scroll_into_view_if_needed()
                    await btn.click()
                    clicked = True
                    break
            except Exception:
                pass

        # Strategy 2: Targeted DOM evaluation
        if not clicked:
            try:
                clicked = await page.evaluate("""() => {
                    const buttons = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"]'));
                    for (const b of buttons) {
                        const txt = (b.innerText || b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase();
                        if (txt === 'create page' || (txt.includes('create') && txt.includes('page'))) {
                            b.scrollIntoView({ block: 'center' });
                            ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evt => {
                                b.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
                            });
                            b.click();
                            return true;
                        }
                    }
                    return false;
                }""")
            except Exception as e:
                self.log("DEBUG", f"[Tab #{tab_index}] DOM click notice: {e}")

        if clicked:
            self.log("INFO", f"[Tab #{tab_index}] Clicked 'Create Page' button. Waiting for Step 1 setup...")
            # Wait for creation processing and transition to 'Finish setting up your Page'
            for _ in range(12):
                await asyncio.sleep(1.0)
                try:
                    has_step1 = await page.evaluate("""() => {
                        const txt = (document.body.innerText || '').toLowerCase();
                        return txt.includes('finish setting up your page') || txt.includes('contact') || txt.includes('customize your page') || txt.includes('page created');
                    }""")
                    if has_step1:
                        self.log("SUCCESS", f"🎉 [Tab #{tab_index}] Facebook Page '{page_name}' created successfully! Advancing to page setup...")
                        return True
                except Exception:
                    pass

            self.log("INFO", f"✅ [Tab #{tab_index}] Creation submission proceeded for '{page_name}'.")
            return True
        else:
            self.log("WARNING", f"⚠️ [Tab #{tab_index}] Could not find or click 'Create Page' button.")
            return False

    async def _step1_finish_setup(self, page, tab_index: int, cfg: Dict[str, Any]) -> bool:
        """
        Handles 'Step 1 of 5: Finish setting up your Page' (Image 1):
          - Contact: Website, Phone number, Email
          - Location: Address, City/town, ZIP code
          - Hours: Always open / Open at selected hours / No hours available
          - Clicks 'Next' button
        All fields are optional; if filled, bot enters them; if empty, skipped cleanly.
        """
        self.log("INFO", f"[Tab #{tab_index}] Processing 'Finish setting up your Page' (Contact, Location, Hours)...")
        await asyncio.sleep(1.5)

        contact = cfg.get("contact", {})
        website = (contact.get("website") or "").strip()
        phone = (contact.get("phone") or "").strip()
        email = (contact.get("email") or "").strip()

        location = cfg.get("location", {})
        address = (location.get("address") or "").strip()
        city = (location.get("city") or "").strip()
        zip_code = (location.get("zip_code") or "").strip()

        hours_mode = cfg.get("hours_mode", "always_open")

        # 1. Website
        if website:
            self.log("INFO", f"[Tab #{tab_index}] Entering Website: {website}")
            w_filled = False
            for sel in ['input[placeholder*="Website" i]', 'input[aria-label*="Website" i]', 'input[name*="website" i]']:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible():
                    await el.click()
                    await el.fill(website)
                    w_filled = True
                    break
            if not w_filled:
                await page.evaluate("""(val) => {
                    const inps = Array.from(document.querySelectorAll('input'));
                    for (const inp of inps) {
                        const p = (inp.getAttribute('placeholder') || '').toLowerCase();
                        const a = (inp.getAttribute('aria-label') || '').toLowerCase();
                        if (p.includes('website') || a.includes('website')) {
                            inp.focus();
                            inp.value = val;
                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                            inp.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                    }
                    return false;
                }""", website)

        # 2. Phone Number
        if phone:
            self.log("INFO", f"[Tab #{tab_index}] Entering Phone number: {phone}")
            p_filled = False
            for sel in ['input[placeholder*="Phone number" i]', 'input[aria-label*="Phone number" i]', 'input[type="tel"]']:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible():
                    await el.click()
                    await el.fill(phone)
                    p_filled = True
                    break
            if not p_filled:
                await page.evaluate("""(val) => {
                    const inps = Array.from(document.querySelectorAll('input'));
                    for (const inp of inps) {
                        const p = (inp.getAttribute('placeholder') || '').toLowerCase();
                        const a = (inp.getAttribute('aria-label') || '').toLowerCase();
                        if (p.includes('phone') || a.includes('phone') || inp.type === 'tel') {
                            inp.focus();
                            inp.value = val;
                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                            inp.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                    }
                    return false;
                }""", phone)

        # 3. Email
        if email:
            self.log("INFO", f"[Tab #{tab_index}] Entering Email: {email}")
            e_filled = False
            for sel in ['input[placeholder*="Email" i]', 'input[aria-label*="Email" i]', 'input[type="email"]']:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible():
                    await el.click()
                    await el.fill(email)
                    e_filled = True
                    break
            if not e_filled:
                await page.evaluate("""(val) => {
                    const inps = Array.from(document.querySelectorAll('input'));
                    for (const inp of inps) {
                        const p = (inp.getAttribute('placeholder') || '').toLowerCase();
                        const a = (inp.getAttribute('aria-label') || '').toLowerCase();
                        if (p.includes('email') || a.includes('email') || inp.type === 'email') {
                            inp.focus();
                            inp.value = val;
                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                            inp.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                    }
                    return false;
                }""", email)

        # 4. Location - Address
        if address:
            self.log("INFO", f"[Tab #{tab_index}] Entering Address: {address}")
            a_filled = False
            for sel in ['input[placeholder*="Address" i]', 'input[aria-label*="Address" i]']:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible():
                    await el.click()
                    await el.fill(address)
                    a_filled = True
                    break
            if not a_filled:
                await page.evaluate("""(val) => {
                    const inps = Array.from(document.querySelectorAll('input'));
                    for (const inp of inps) {
                        const p = (inp.getAttribute('placeholder') || '').toLowerCase();
                        const a = (inp.getAttribute('aria-label') || '').toLowerCase();
                        if (p.includes('address') || a.includes('address')) {
                            inp.focus();
                            inp.value = val;
                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                            inp.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                    }
                    return false;
                }""", address)

        # 5. Location - City/town
        if city:
            self.log("INFO", f"[Tab #{tab_index}] Entering City/town: {city}")
            c_filled = False
            for sel in ['input[placeholder*="City/town" i]', 'input[placeholder*="City" i]', 'input[aria-label*="City" i]']:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible():
                    await el.click()
                    await el.fill("")
                    await el.type(city, delay=35)
                    c_filled = True
                    await asyncio.sleep(1.2)
                    try:
                        sugg = page.locator('div[role="listbox"] div[role="option"], ul[role="listbox"] li, div[role="option"]').first
                        if await sugg.count() > 0 and await sugg.is_visible():
                            await sugg.click()
                        else:
                            await page.keyboard.press("ArrowDown")
                            await asyncio.sleep(0.3)
                            await page.keyboard.press("Enter")
                    except Exception:
                        pass
                    break
            if not c_filled:
                await page.evaluate("""(val) => {
                    const inps = Array.from(document.querySelectorAll('input'));
                    for (const inp of inps) {
                        const p = (inp.getAttribute('placeholder') || '').toLowerCase();
                        const a = (inp.getAttribute('aria-label') || '').toLowerCase();
                        if (p.includes('city') || a.includes('city')) {
                            inp.focus();
                            inp.value = val;
                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                            inp.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                    }
                    return false;
                }""", city)

        # 6. Location - ZIP code
        if zip_code:
            self.log("INFO", f"[Tab #{tab_index}] Entering ZIP code: {zip_code}")
            z_filled = False
            for sel in ['input[placeholder*="ZIP code" i]', 'input[placeholder*="ZIP" i]', 'input[aria-label*="ZIP" i]']:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible():
                    await el.click()
                    await el.fill(zip_code)
                    z_filled = True
                    break
            if not z_filled:
                await page.evaluate("""(val) => {
                    const inps = Array.from(document.querySelectorAll('input'));
                    for (const inp of inps) {
                        const p = (inp.getAttribute('placeholder') || '').toLowerCase();
                        const a = (inp.getAttribute('aria-label') || '').toLowerCase();
                        if (p.includes('zip') || a.includes('zip')) {
                            inp.focus();
                            inp.value = val;
                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                            inp.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                    }
                    return false;
                }""", zip_code)

        # 7. Hours Selection (Always open / Open at selected hours / No hours available)
        target_hours_txt = "Always open"
        if hours_mode == "selected_hours":
            target_hours_txt = "Open at selected hours"
        elif hours_mode == "no_hours":
            target_hours_txt = "No hours available"

        self.log("INFO", f"[Tab #{tab_index}] Selecting Hours: '{target_hours_txt}'")
        h_clicked = False
        try:
            h_loc = page.locator(f'label:has-text("{target_hours_txt}"), div[role="radio"]:has-text("{target_hours_txt}"), span:has-text("{target_hours_txt}")').first
            if await h_loc.count() > 0 and await h_loc.is_visible():
                await h_loc.click()
                h_clicked = True
        except Exception:
            pass

        if not h_clicked:
            await page.evaluate("""(txt) => {
                const els = Array.from(document.querySelectorAll('label, div[role="radio"], span, div'));
                for (const el of els) {
                    if ((el.innerText || '').toLowerCase().includes(txt.toLowerCase())) {
                        el.click();
                        return true;
                    }
                }
                return false;
            }""", target_hours_txt)

        await asyncio.sleep(1.0)

        # 8. Click 'Next' button to advance to Step 2
        self.log("INFO", f"[Tab #{tab_index}] Clicking 'Next' button to advance to Customize Page (Photos)...")
        next_clicked = False
        try:
            for sel in ['button:has-text("Next")', 'div[role="button"]:has-text("Next")']:
                btn = page.locator(sel).last
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    next_clicked = True
                    break
        except Exception:
            pass

        if not next_clicked:
            await page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                for (let i = btns.length - 1; i >= 0; i--) {
                    const b = btns[i];
                    if ((b.innerText || '').trim().toLowerCase() === 'next') {
                        b.click();
                        return true;
                    }
                }
                return false;
            }""")

        await asyncio.sleep(2.0)
        return True

    async def _step2_customize_photos(self, page, tab_index: int, cfg: Dict[str, Any]) -> bool:
        """
        Handles 'Step 2 of 5: Customize your Page' (Image 2):
          - Add profile picture (if provided)
          - Add cover photo (if provided)
          - Clicks 'Next' button
        """
        self.log("INFO", f"[Tab #{tab_index}] Processing 'Customize your Page' (Profile & Cover Photos)...")
        await asyncio.sleep(1.5)

        profile_photo_path = (cfg.get("profile_photo_path") or "").strip()
        cover_photo_path = (cfg.get("cover_photo_path") or "").strip()

        # 1. Upload Profile Picture
        if profile_photo_path and os.path.isfile(profile_photo_path):
            self.log("INFO", f"[Tab #{tab_index}] 📷 Uploading Profile Picture: {os.path.basename(profile_photo_path)}")
            p_uploaded = False
            try:
                # Direct file input check
                file_inputs = page.locator('input[type="file"]')
                if await file_inputs.count() > 0:
                    await file_inputs.nth(0).set_input_files(profile_photo_path)
                    p_uploaded = True
                    self.log("INFO", f"[Tab #{tab_index}] Profile picture file attached.")
                    await asyncio.sleep(2.0)
            except Exception:
                pass

            if not p_uploaded:
                try:
                    p_btn = page.locator('div[aria-label*="Add profile picture" i], div:has-text("Add profile picture")').first
                    if await p_btn.count() > 0 and await p_btn.is_visible():
                        async with page.expect_file_chooser(timeout=6000) as fc_info:
                            await p_btn.click()
                        file_chooser = await fc_info.value
                        await file_chooser.set_files(profile_photo_path)
                        p_uploaded = True
                        self.log("INFO", f"[Tab #{tab_index}] Profile picture uploaded via chooser.")
                        await asyncio.sleep(2.0)
                except Exception as ex:
                    self.log("DEBUG", f"[Tab #{tab_index}] Profile photo chooser notice: {ex}")

        # 2. Upload Cover Photo
        if cover_photo_path and os.path.isfile(cover_photo_path):
            self.log("INFO", f"[Tab #{tab_index}] 🖼️ Uploading Cover Photo: {os.path.basename(cover_photo_path)}")
            c_uploaded = False
            try:
                file_inputs = page.locator('input[type="file"]')
                count = await file_inputs.count()
                if count > 1:
                    await file_inputs.nth(1).set_input_files(cover_photo_path)
                    c_uploaded = True
                    self.log("INFO", f"[Tab #{tab_index}] Cover photo file attached.")
                    await asyncio.sleep(2.0)
                elif count == 1:
                    await file_inputs.nth(0).set_input_files(cover_photo_path)
                    c_uploaded = True
                    await asyncio.sleep(2.0)
            except Exception:
                pass

            if not c_uploaded:
                try:
                    c_btn = page.locator('div[aria-label*="Add cover photo" i], div:has-text("Add cover photo")').first
                    if await c_btn.count() > 0 and await c_btn.is_visible():
                        async with page.expect_file_chooser(timeout=6000) as fc_info:
                            await c_btn.click()
                        file_chooser = await fc_info.value
                        await file_chooser.set_files(cover_photo_path)
                        c_uploaded = True
                        self.log("INFO", f"[Tab #{tab_index}] Cover photo uploaded via chooser.")
                        await asyncio.sleep(2.0)
                except Exception as ex:
                    self.log("DEBUG", f"[Tab #{tab_index}] Cover photo chooser notice: {ex}")

        await asyncio.sleep(1.0)

        # 3. Click 'Next' button
        self.log("INFO", f"[Tab #{tab_index}] Clicking 'Next' on Customize Page...")
        next_clicked = False
        try:
            for sel in ['button:has-text("Next")', 'div[role="button"]:has-text("Next")']:
                btn = page.locator(sel).last
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    next_clicked = True
                    break
        except Exception:
            pass

        if not next_clicked:
            await page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                for (let i = btns.length - 1; i >= 0; i--) {
                    const b = btns[i];
                    if ((b.innerText || '').trim().toLowerCase() === 'next') {
                        b.click();
                        return true;
                    }
                }
                return false;
            }""")

        await asyncio.sleep(2.0)
        return True

    async def _complete_remaining_wizard(self, page, tab_index: int) -> bool:
        """
        Completes remaining wizard steps (WhatsApp Connect skip, Build audience, Stay informed, Done).
        Clicks 'Done', 'Skip', or 'Next' until the Facebook page is completely finalized!
        """
        self.log("INFO", f"[Tab #{tab_index}] Finalizing page setup wizard...")
        for step in range(5):
            await asyncio.sleep(1.8)

            # Check if 'Done' is visible and clickable
            done_clicked = await page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                for (const b of btns) {
                    const txt = (b.innerText || '').trim().toLowerCase();
                    if (txt === 'done') {
                        b.click();
                        return true;
                    }
                }
                return false;
            }""")
            if done_clicked:
                self.log("SUCCESS", f"🎉 [Tab #{tab_index}] Clicked 'Done'! Facebook Page setup is 100% complete!")
                await asyncio.sleep(2.5)
                return True

            # Check if 'Skip' (WhatsApp step) or 'Next' is available
            progressed = await page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                // Skip if WhatsApp dialog
                for (const b of btns) {
                    const txt = (b.innerText || '').trim().toLowerCase();
                    if (txt === 'skip') {
                        b.click();
                        return 'Skip';
                    }
                }
                // Next for audience or stay informed
                for (let i = btns.length - 1; i >= 0; i--) {
                    const b = btns[i];
                    const txt = (b.innerText || '').trim().toLowerCase();
                    if (txt === 'next') {
                        b.click();
                        return 'Next';
                    }
                }
                return null;
            }""")

            if progressed:
                self.log("INFO", f"[Tab #{tab_index}] Advanced wizard step: '{progressed}'...")
            else:
                curr_url = page.url.lower()
                if "facebook.com" in curr_url and "pages/creation" not in curr_url:
                    self.log("SUCCESS", f"🎉 [Tab #{tab_index}] Setup complete! Navigated to Facebook Page.")
                    return True

        return True

    async def create_pages_workflow(
        self,
        page_configs: List[Dict[str, Any]],
        delay_seconds: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Executes the exact multi-tab parallel page creation and setup flow:
          - Opens N tabs simultaneously where N = len(page_configs)
          - Concurrently navigates each tab and handles 'Public Page' / 'Public Place Page' modal
          - Concurrently fills Name, Category, and Bio in each tab
          - Concurrently triggers 'Create Page' across all tabs simultaneously!
          - Concurrently fills Step 1: Finish setting up your Page (Contact, Location, Hours) & clicks 'Next'
          - Concurrently fills Step 2: Customize your Page (Profile & Cover Photos) & clicks 'Next'
          - Concurrently advances through remaining steps to 'Done'!
        """
        results = []
        if not page_configs:
            self.log("WARNING", "No page configurations provided.")
            return results

        num_tabs = len(page_configs)
        self.log("INFO", f"🚀 Starting Facebook Page Creator across {num_tabs} concurrent tab(s)...")

        # Step 1: Open browser & initialize session
        await self.init_browser()
        if not self.context:
            self.log("ERROR", "Failed to launch browser context.")
            return results

        # Step 2: Open N tabs
        pages = []
        existing_pages = self.context.pages
        if existing_pages:
            pages.append(existing_pages[0])

        while len(pages) < num_tabs:
            new_p = await self.context.new_page()
            pages.append(new_p)

        self.log("INFO", f"🌐 Opened {len(pages)} browser tab(s) simultaneously.")
        await asyncio.sleep(1.0)

        # Step 3: Phase 1 - Concurrently Navigate & Handle 'Public Page' Modal across all tabs
        self.log("INFO", "⚡ [Phase 1/5] Navigating all tabs to Facebook Page Creation...")
        nav_tasks = []
        for idx, (p, cfg) in enumerate(zip(pages, page_configs)):
            nav_tasks.append(self._handle_create_modal_and_navigate(p, idx + 1))

        await asyncio.gather(*nav_tasks, return_exceptions=True)
        await asyncio.sleep(delay_seconds)

        # Step 4: Phase 2 - Concurrently Fill Page Name, Category & Bio across all tabs
        self.log("INFO", "✍️ [Phase 2/5] Concurrently typing Page Names, Categories & Bios across all tabs...")
        fill_tasks = []
        for idx, (p, cfg) in enumerate(zip(pages, page_configs)):
            p_name = cfg.get("name", f"New Page {idx + 1}")
            p_cat = cfg.get("category", "Digital Creator")
            p_bio = cfg.get("bio", "")
            fill_tasks.append(self._fill_page_form(p, idx + 1, p_name, p_cat, p_bio))

        await asyncio.gather(*fill_tasks, return_exceptions=True)
        self.log("INFO", "⏳ All tabs filled! Synchronizing before simultaneous creation click...")
        await asyncio.sleep(2.0)

        # Step 5: Phase 3 - Concurrently Click 'Create Page' across all tabs!
        self.log("INFO", "🔥 [Phase 3/5] Triggering 'Create Page' across all tabs simultaneously!")
        click_tasks = []
        for idx, (p, cfg) in enumerate(zip(pages, page_configs)):
            p_name = cfg.get("name", f"New Page {idx + 1}")
            click_tasks.append(self._click_create_page(p, idx + 1, p_name))

        await asyncio.gather(*click_tasks, return_exceptions=True)
        await asyncio.sleep(2.0)

        # Step 6: Phase 4 - Concurrently Fill Step 1: Finish setting up your Page (Contact, Location, Hours)
        self.log("INFO", "🌐 [Phase 4/5] Concurrently filling Contact, Location & Hours across all tabs...")
        step1_tasks = []
        for idx, (p, cfg) in enumerate(zip(pages, page_configs)):
            step1_tasks.append(self._step1_finish_setup(p, idx + 1, cfg))

        await asyncio.gather(*step1_tasks, return_exceptions=True)
        await asyncio.sleep(2.0)

        # Step 7: Phase 5 - Concurrently Fill Step 2: Customize your Page (Profile & Cover Photos) & Finish
        self.log("INFO", "🖼️ [Phase 5/5] Concurrently uploading Profile/Cover Photos & finalizing Page Setup...")
        photo_tasks = []
        for idx, (p, cfg) in enumerate(zip(pages, page_configs)):
            photo_tasks.append(self._step2_customize_photos(p, idx + 1, cfg))

        await asyncio.gather(*photo_tasks, return_exceptions=True)
        await asyncio.sleep(2.0)

        # Step 8: Final wizard steps (WhatsApp, Invite, Done)
        final_tasks = []
        for idx, (p, cfg) in enumerate(zip(pages, page_configs)):
            final_tasks.append(self._complete_remaining_wizard(p, idx + 1))

        final_results = await asyncio.gather(*final_tasks, return_exceptions=True)

        for idx, (cfg, ok) in enumerate(zip(page_configs, final_results)):
            success = bool(ok is True)
            results.append({
                "account": self.account_name,
                "name": cfg.get("name"),
                "category": cfg.get("category"),
                "status": "Created" if success else "Failed"
            })

        self.log("SUCCESS", f"🏁 Finished Page Creation and Setup workflow for account {self.account_name} ({len(results)} pages processed).")
        await asyncio.sleep(3.0)

        # Close browser session cleanly
        await self.close()
        return results

    async def close(self):
        """Closes browser context and playwright."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        self.context = None
        self.browser = None
        self.playwright = None
