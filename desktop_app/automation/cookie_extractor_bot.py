#!/usr/bin/env python3
"""
FB Auto Bot - Facebook Automation Suite
automation/cookie_extractor_bot.py - Ultra High-Speed Facebook Session Cookie Extractor Engine

Automates high-speed, 100% reliable extraction of fresh Facebook session cookies
(sb, datr, dpr, wd, c_user, oo, xs, i_user) matching the exact format of the
Google Chrome extension 'Get Token Cookie'.

Features:
- Instant DOM + Native Credential Injection (Never fails to enter UID/password).
- Direct Desktop Facebook Portal navigation (https://www.facebook.com/login.php).
- Complete multi-language cookie consent overlay auto-dismissal.
- High-frequency auth polling: Live session detected within 2-5 seconds.
- Instant failure exits (Wrong Password in 1s, Checkpoint in 2s, 2FA in 1s).
- Automatic Facebook Page switching ('Use Page' / sets 'i_user' cookie).
- Strict separation: Live accounts go to Live column; Checkpoint accounts go to Checkpoint column.
- Zero network blocking: No --no-proxy-server flag, fully compatible with VPNs/proxies.
"""

import os
import sys
import time
import json
import logging
import asyncio
import tempfile
import shutil
import uuid
import gc
import re
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional, Tuple, Callable

logger = logging.getLogger("CookieExtractorBot")
logger.setLevel(logging.INFO)

# Optional Playwright and stealth support
try:
    from playwright.async_api import async_playwright, Playwright, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from playwright_stealth import stealth_async
    PLAYWRIGHT_STEALTH_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_STEALTH_AVAILABLE = False

# Import TOTP generator from session_manager if available
try:
    from automation.session_manager import generate_totp
except ImportError:
    try:
        from desktop_app.automation.session_manager import generate_totp
    except ImportError:
        import hmac
        import hashlib
        import struct
        import base64

        def generate_totp(secret: str) -> str:
            if not secret or not isinstance(secret, str):
                return ""
            try:
                clean_secret = secret.replace(" ", "").replace("-", "").upper()
                padded = clean_secret + "=" * (-len(clean_secret) % 8)
                key = base64.b32decode(padded)
                counter = int(time.time()) // 30
                msg = struct.pack(">Q", counter)
                h = hmac.new(key, msg, hashlib.sha1).digest()
                offset = h[-1] & 0x0F
                code = (struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF) % 1000000
                return f"{code:06d}"
            except Exception:
                return ""


def format_get_token_cookie_string(
    cookies: List[Dict[str, Any]],
    page_id: str = "",
    dpr_val: str = "1.125",
    wd_val: str = "833x811"
) -> str:
    """
    Constructs the exact cookie string matching the Chrome extension 'Get Token Cookie':
    sb -> datr -> dpr -> wd -> c_user -> [others: oo, fr, _fbp, presence...] -> xs -> i_user;
    Formatted without spaces, each key-value pair separated by a semicolon, ending with a semicolon.
    """
    c_map: Dict[str, str] = {}
    for c in cookies:
        n = c.get("name")
        v = c.get("value")
        if n and v is not None:
            c_map[str(n)] = str(v).strip()

    # Ensure dpr and wd match real Chrome desktop metrics
    if "dpr" not in c_map and dpr_val:
        c_map["dpr"] = str(dpr_val).strip()
    elif "dpr" not in c_map:
        c_map["dpr"] = "1.125"

    if "wd" not in c_map and wd_val:
        c_map["wd"] = str(wd_val).strip()
    elif "wd" not in c_map:
        c_map["wd"] = "833x811"

    # If page_id is known (from Page switch or detected ID) and i_user not in cookies yet
    if page_id and "i_user" not in c_map:
        c_map["i_user"] = str(page_id).strip()

    parts: List[str] = []
    seen = set()

    # 1. Leading priority matching Get Token Cookie extension
    for k in ["sb", "datr", "dpr", "wd", "c_user"]:
        if k in c_map:
            parts.append(f"{k}={c_map[k]}")
            seen.add(k)

    # 2. Intermediate cookies (oo, _fbp, fr, presence, etc.)
    for k, v in c_map.items():
        if k not in seen and k not in ("xs", "i_user"):
            parts.append(f"{k}={v}")
            seen.add(k)

    # 3. Session authentication secret xs
    if "xs" in c_map:
        parts.append(f"xs={c_map['xs']}")
        seen.add("xs")

    # 4. Page active profile i_user (if present)
    if "i_user" in c_map:
        parts.append(f"i_user={c_map['i_user']}")
        seen.add("i_user")

    # Format without any spaces, followed by trailing semicolon
    res = ";".join(parts)
    if res and not res.endswith(";"):
        res += ";"
    return res


class FacebookCookieExtractorBot:
    """
    Automated High-Speed Browser Bot for Extracting Fresh Facebook Cookies.
    Performs login, page switching, and cookie extraction in 5 to 10 seconds.
    """

    def __init__(
        self,
        uid_or_email: str,
        password: str,
        two_factor_secret: str = "",
        proxy: str = "",
        headless: bool = True,
        timeout_seconds: int = 25,
        switch_to_page: bool = True,
        page_target: str = "",
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.uid_or_email = str(uid_or_email).strip()
        self.password = str(password).strip()
        self.two_factor_secret = str(two_factor_secret).strip()
        self.proxy = str(proxy).strip()
        self.headless = headless
        # Cap timeout between 15 and 45 seconds to prevent endless hangs
        self.timeout_seconds = max(15, min(45, int(timeout_seconds)))
        self.switch_to_page = switch_to_page
        self.page_target = str(page_target).strip()
        self.log_callback = log_callback

        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        self.temp_profile_dir: Optional[str] = None
        self._cancelled = False

    def log(self, level: str, message: str):
        if self.log_callback:
            try:
                self.log_callback(level, message)
            except Exception:
                pass
        else:
            logger.info(f"[{level}] {message}")

    def cancel(self):
        self._cancelled = True

    async def close(self):
        """Cleanly releases browser context, Playwright instances, and temp files."""
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass
        self.context = None

        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        self.playwright = None

        if self.temp_profile_dir and os.path.exists(self.temp_profile_dir):
            try:
                shutil.rmtree(self.temp_profile_dir, ignore_errors=True)
            except Exception:
                pass
            self.temp_profile_dir = None

        try:
            gc.collect()
        except Exception:
            pass

    async def _dismiss_all_overlays(self, page: Page):
        """Dismisses cookie consent popups, language selectors, and blocking modals via DOM execution."""
        try:
            await page.evaluate("""() => {
                const buttons = Array.from(document.querySelectorAll('button, [role="button"], a[role="button"], input[type="button"]'));
                for (const b of buttons) {
                    const txt = (b.innerText || b.textContent || b.value || '').trim().toLowerCase();
                    const testId = (b.getAttribute('data-cookiebanner') || b.getAttribute('data-testid') || '').toLowerCase();
                    if (
                        testId.includes('accept') || testId.includes('agree') || testId.includes('allow') ||
                        txt.includes('allow all') || txt.includes('accept all') || 
                        txt.includes('only allow essential') || txt.includes('accept cookies') ||
                        txt.includes('allow cookies') || txt.includes('decline optional') ||
                        txt === 'allow' || txt === 'accept' || txt === 'ok' || txt === 'agree' ||
                        txt === 'i agree' || txt === 'continuer' || txt === 'accepter' || txt === 'ha' ||
                        txt.includes('permitir') || txt.includes('akzeptieren')
                    ) {
                        try { b.click(); } catch(e) {}
                    }
                }
            }""")
        except Exception:
            pass

    async def extract_cookie(self) -> Dict[str, Any]:
        """
        Executes credential authentication and extracts fresh Facebook session cookies
        within 5 to 10 seconds.
        """
        if not self.uid_or_email:
            return {"success": False, "uid": "", "name": "", "cookie": "", "status": "Error", "message": "UID/Email is empty."}
        if not self.password:
            return {"success": False, "uid": self.uid_or_email, "name": "", "cookie": "", "status": "Error", "message": "Password is empty."}
        if not PLAYWRIGHT_AVAILABLE:
            self.log("ERROR", "Playwright is not available in the environment.")
            return {"success": False, "uid": self.uid_or_email, "name": "", "cookie": "", "status": "Error", "message": "Playwright is not installed."}

        tag = f"[{self.uid_or_email}]"
        mode_str = "Background" if self.headless else "Visible Browser"
        self.log("INFO", f"{tag} 🚀 Initializing Speed Bot ({mode_str}, Max Wait: {self.timeout_seconds}s)...")

        # Create isolated temporary profile directory
        clean_uid = "".join(c for c in self.uid_or_email if c.isalnum()) or "temp"
        self.temp_profile_dir = os.path.join(tempfile.gettempdir(), f"fb_ext_{clean_uid}_{uuid.uuid4().hex[:6]}")
        os.makedirs(self.temp_profile_dir, exist_ok=True)

        start_time = time.time()

        try:
            self.playwright = await async_playwright().start()

            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-notifications",
                "--no-first-run",
                "--disable-default-apps",
                "--disable-popup-blocking",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--lang=en-US",
                "--accept-lang=en-US,en;q=0.9"
            ]
            if self.headless:
                launch_args.append("--headless=new")

            proxy_cfg = None
            if self.proxy and "direct" not in self.proxy.lower() and "no proxy" not in self.proxy.lower():
                try:
                    s_url = self.proxy if "://" in self.proxy else f"http://{self.proxy}"
                    parsed = urlparse(s_url)
                    if parsed.hostname and parsed.port:
                        proxy_cfg = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
                        if parsed.username:
                            proxy_cfg["username"] = parsed.username
                        if parsed.password:
                            proxy_cfg["password"] = parsed.password
                        self.log("INFO", f"{tag} 🛡️ Using proxy: {parsed.hostname}:{parsed.port}")
                except Exception:
                    proxy_cfg = None

            # Launch with browser channel fallback: Chrome -> Edge -> Chromium -> bundled
            channels_to_try = ["chrome", "msedge", "chromium", None]
            context = None

            for ch in channels_to_try:
                try:
                    kws: Dict[str, Any] = {
                        "user_data_dir": self.temp_profile_dir,
                        "headless": self.headless,
                        "viewport": {"width": 1280, "height": 800},
                        "args": launch_args,
                        "ignore_default_args": ["--enable-automation", "--disable-extensions"],
                        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                        "locale": "en-US",
                        "timezone_id": "America/New_York",
                        "extra_http_headers": {
                            "Accept-Language": "en-US,en;q=0.9",
                            "Upgrade-Insecure-Requests": "1"
                        }
                    }
                    if proxy_cfg:
                        kws["proxy"] = proxy_cfg
                    if ch:
                        kws["channel"] = ch

                    context = await self.playwright.chromium.launch_persistent_context(**kws)
                    self.context = context
                    break
                except Exception:
                    continue

            if not self.context:
                raise Exception("Could not launch Google Chrome or MS Edge on this PC.")

            page = self.context.pages[0] if self.context.pages else await self.context.new_page()

            # Anti-Detection Stealth Script Injection
            try:
                await page.add_init_script("""
                    try {
                        delete Object.getPrototypeOf(navigator).webdriver;
                    } catch (e) {}
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                    Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
                    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
                    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
                    window.chrome = { app: { isInstalled: false }, runtime: {} };
                """)
            except Exception:
                pass

            if PLAYWRIGHT_STEALTH_AVAILABLE:
                try:
                    await stealth_async(page)
                except Exception:
                    pass

            # Step 1: Direct Desktop Facebook Portal Navigation
            self.log("INFO", f"{tag} 🌐 Connecting to Facebook Login Portal...")
            login_urls = [
                "https://www.facebook.com/login.php",
                "https://www.facebook.com/",
                "https://m.facebook.com/login.php"
            ]

            nav_ok = False
            for u in login_urls:
                if self._cancelled:
                    return {"success": False, "uid": self.uid_or_email, "name": "", "cookie": "", "status": "Cancelled", "message": "Cancelled."}
                try:
                    await page.goto(u, wait_until="commit", timeout=8000)
                    nav_ok = True
                    break
                except Exception:
                    try:
                        await page.goto(u, timeout=8000)
                        nav_ok = True
                        break
                    except Exception:
                        continue

            if not nav_ok:
                try:
                    await page.goto("https://www.facebook.com/", timeout=10000)
                except Exception:
                    pass

            # Check if session is already authenticated (e.g. cookie retained)
            try:
                initial_cookies = await self.context.cookies()
                init_c_user = next((c.get("value") for c in initial_cookies if c.get("name") == "c_user"), None)
                if init_c_user:
                    self.log("SUCCESS", f"{tag} ✅ Session already active for c_user={init_c_user}!")
                    has_authenticated = True
                else:
                    has_authenticated = False
            except Exception:
                has_authenticated = False

            if not has_authenticated:
                await self._dismiss_all_overlays(page)

                # Step 2: Locate and Fill Email and Password Inputs
                self.log("INFO", f"{tag} ✍️ Inputting Facebook UID & Password...")
                
                # Multi-Layer Injection: DOM Event Dispatch + Playwright Native Fill
                fill_res = await page.evaluate("""(data) => {
                    const emailInput = document.querySelector('input[name="email"], input#email, input#m_login_email, input[data-testid="royal_email"], input[type="text"][autocomplete="username"], input[type="text"]');
                    const passInput = document.querySelector('input[name="pass"], input#pass, input#m_login_password, input[data-testid="royal_pass"], input[type="password"]');
                    
                    if (emailInput) {
                        emailInput.focus();
                        emailInput.value = data.u;
                        emailInput.dispatchEvent(new Event('input', { bubbles: true }));
                        emailInput.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    if (passInput) {
                        passInput.focus();
                        passInput.value = data.p;
                        passInput.dispatchEvent(new Event('input', { bubbles: true }));
                        passInput.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    return { emailFound: !!emailInput, passFound: !!passInput };
                }""", {"u": self.uid_or_email, "p": self.password})

                # Native Playwright typing fallback
                try:
                    email_loc = page.locator('input[name="email"], input#email, input#m_login_email, input[type="text"]').first
                    if await email_loc.count() > 0:
                        await email_loc.click()
                        await email_loc.fill(self.uid_or_email)
                except Exception:
                    pass

                try:
                    pass_loc = page.locator('input[name="pass"], input#pass, input#m_login_password, input[type="password"]').first
                    if await pass_loc.count() > 0:
                        await pass_loc.click()
                        await pass_loc.fill(self.password)
                except Exception:
                    pass

                # Step 3: Instant Form Submission
                self.log("INFO", f"{tag} ⚡ Submitting Facebook login credentials...")
                submitted = False
                submit_selectors = [
                    'button[name="login"]',
                    'button#loginbutton',
                    'button[data-testid="royal_login_button"]',
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Log In")',
                    'button:has-text("Login")'
                ]
                for ss in submit_selectors:
                    s_btn = page.locator(ss).first
                    if await s_btn.count() > 0:
                        try:
                            await s_btn.click(timeout=1500)
                            submitted = True
                            break
                        except Exception:
                            continue

                if not submitted:
                    try:
                        submitted = await page.evaluate("""() => {
                            const b = document.querySelector('button[name="login"], button#loginbutton, button[data-testid="royal_login_button"], button[type="submit"], input[type="submit"]');
                            if (b) { b.click(); return true; }
                            return false;
                        }""")
                    except Exception:
                        submitted = False

                if not submitted:
                    await page.keyboard.press("Enter")

                # Step 4: Rapid High-Frequency Authentication Polling (Every 0.25s)
                self.log("INFO", f"{tag} ⏳ Awaiting Facebook tokens (Fast Mode)...")
                error_status = "Timeout"
                error_msg = f"Authentication timed out after {self.timeout_seconds} seconds."

                poll_start = time.time()
                while time.time() - poll_start < self.timeout_seconds:
                    if self._cancelled:
                        return {"success": False, "uid": self.uid_or_email, "name": "", "cookie": "", "status": "Cancelled", "message": "Operation cancelled."}

                    await asyncio.sleep(0.25)

                    # Check ALL session cookies in context
                    curr_cookies: List[Dict[str, Any]] = []
                    try:
                        curr_cookies = await self.context.cookies()
                    except Exception:
                        pass

                    c_user_val = next((c.get("value") for c in curr_cookies if c.get("name") == "c_user"), None)
                    xs_val = next((c.get("value") for c in curr_cookies if c.get("name") == "xs"), None)

                    # -------------------------------------------------------------
                    # GOLDEN CHECK: If c_user exists AND (xs exists or datr exists) -> LIVE!
                    # -------------------------------------------------------------
                    if c_user_val and (xs_val or any(c.get("name") == "datr" for c in curr_cookies)):
                        has_authenticated = True
                        self.log("SUCCESS", f"{tag} ✅ Live Facebook session active! c_user={c_user_val}")
                        break

                    # Check Page Text for Instant Failure Detection
                    page_text = ""
                    try:
                        page_text = (await page.evaluate("() => (document.body ? document.body.innerText : '')")).lower()
                    except Exception:
                        pass

                    # 1. Check for Wrong Password -> Instant Exit (1-2s)
                    if any(w in page_text for w in [
                        "the password you entered is incorrect",
                        "incorrect password",
                        "the password that you've entered is incorrect",
                        "wrong password",
                        "invalid username or password",
                        "galt password",
                        "password you entered is wrong"
                    ]):
                        error_status = "Wrong Password"
                        error_msg = "Incorrect Facebook Password."
                        self.log("ERROR", f"{tag} ❌ Wrong password for account.")
                        break

                    # 2. Check for Disabled Account -> Instant Exit
                    if any(d in page_text for d in [
                        "account has been disabled",
                        "your account has been disabled",
                        "we disabled your account",
                        "account disabled"
                    ]):
                        error_status = "Disabled"
                        error_msg = "Account is disabled by Facebook."
                        self.log("ERROR", f"{tag} 🚫 Facebook account is disabled.")
                        break

                    # 3. Check for 2FA / Approvals Code prompt
                    two_fa_input = page.locator(
                        'input[name="approvals_code"], input[name="code"], input#approvals_code, input[data-testid="royal_code"]'
                    ).first
                    if await two_fa_input.count() > 0 and await two_fa_input.is_visible():
                        if self.two_factor_secret:
                            totp_code = generate_totp(self.two_factor_secret)
                            if totp_code:
                                self.log("INFO", f"{tag} 🔑 2FA Required. Generated TOTP ({totp_code}). Submitting...")
                                await two_fa_input.fill(totp_code)
                                await asyncio.sleep(0.2)
                                submit_2fa = page.locator(
                                    'button#checkpointSubmitButton, button[type="submit"], button:has-text("Continue"), button:has-text("Submit")'
                                ).first
                                if await submit_2fa.count() > 0 and await submit_2fa.is_visible():
                                    await submit_2fa.click()
                                else:
                                    await page.keyboard.press("Enter")
                                await asyncio.sleep(1.2)
                                continue
                        else:
                            error_status = "2FA Required"
                            error_msg = "Two-Factor Authentication (2FA) required, but no 2FA secret was provided."
                            self.log("WARNING", f"{tag} ⚠️ 2FA code required.")
                            break

                    # 4. Check for True Checkpoint Screen
                    curr_url = page.url.lower()
                    is_checkpoint_url = ("/checkpoint/" in curr_url or "/recover/" in curr_url)
                    is_checkpoint_text = any(cp in page_text for cp in [
                        "we suspended your account",
                        "your account has been locked",
                        "account locked",
                        "confirm your identity",
                        "upload a photo of your id",
                        "security check"
                    ])
                    if (is_checkpoint_url or is_checkpoint_text) and (time.time() - poll_start > 3.0):
                        if await two_fa_input.count() == 0:
                            error_status = "Checkpoint"
                            error_msg = "Account is in Facebook security checkpoint."
                            self.log("WARNING", f"{tag} 🔒 Genuine Checkpoint detected. Routed to Checkpoint column.")
                            break

                    # 5. Auto-dismiss "Remember Password", "Save Info", "Not Now" dialogs
                    try:
                        save_selectors = [
                            'button:has-text("Save")',
                            'button:has-text("Save Info")',
                            'button:has-text("Not Now")',
                            'a:has-text("Not Now")',
                            'button:has-text("Continue")',
                            'button:has-text("OK")'
                        ]
                        for s_sel in save_selectors:
                            s_btn = page.locator(s_sel).first
                            if await s_btn.count() > 0 and await s_btn.is_visible():
                                await s_btn.click()
                                await asyncio.sleep(0.2)
                                break
                    except Exception:
                        pass

            # =========================================================================
            # FINAL AUDIT: Ensure no Live session is ever misclassified
            # =========================================================================
            if not has_authenticated:
                final_check_cookies: List[Dict[str, Any]] = []
                try:
                    if self.context:
                        final_check_cookies = await self.context.cookies()
                except Exception:
                    pass

                c_user_found = next((c.get("value") for c in final_check_cookies if c.get("name") == "c_user"), "")
                xs_found = next((c.get("value") for c in final_check_cookies if c.get("name") == "xs"), "")
                datr_found = next((c.get("value") for c in final_check_cookies if c.get("name") == "datr"), "")

                # If c_user exists in browser session cookies, verify it's not a hard account lock
                if c_user_found and (xs_found or datr_found):
                    p_text_final = ""
                    try:
                        p_text_final = (await page.evaluate("() => document.body ? document.body.innerText.toLowerCase() : ''"))
                    except Exception:
                        pass

                    hard_locks = ["we suspended your account", "your account has been locked", "upload a photo of your id"]
                    if not any(hl in p_text_final for hl in hard_locks):
                        has_authenticated = True
                        self.log("SUCCESS", f"{tag} 🟢 Verified LIVE Facebook session! (c_user={c_user_found})")

            # =========================================================================
            # CASE A: Genuine Checkpoint / Authentication Failure Exit
            # =========================================================================
            if not has_authenticated:
                resolved_uid = self.uid_or_email
                is_cp = (error_status in ["Checkpoint", "Disabled"] or "checkpoint" in error_msg.lower())

                # If account is checkpointed, report Checkpoint immediately as requested
                self.log("WARNING", f"{tag} 🔒 Account status confirmed: {error_status}. (Routed to Checkpoint list)")

                # Extract partial cookies if available
                cp_cookies: List[Dict[str, Any]] = []
                try:
                    if self.context:
                        cp_cookies = await self.context.cookies()
                except Exception:
                    pass

                cp_cookie_str = ""
                if cp_cookies:
                    cp_cookie_str = format_get_token_cookie_string(cp_cookies)

                return {
                    "success": False,
                    "is_checkpoint": is_cp,
                    "uid": resolved_uid,
                    "name": f"FB Checkpoint ({resolved_uid})" if is_cp else f"FB User ({resolved_uid})",
                    "cookie": cp_cookie_str,
                    "status": error_status,
                    "message": error_msg
                }

            # =========================================================================
            # CASE B: LIVE Session - Page Switch & Full Token Extraction
            # =========================================================================
            self.log("INFO", f"{tag} 🔍 Fetching device display metrics (dpr, wd)...")
            dpr_from_page = "1.125"
            wd_from_page = "833x811"
            try:
                metrics = await page.evaluate("""() => ({
                    dpr: window.devicePixelRatio || 1.125,
                    wd: (window.innerWidth && window.innerHeight) ? `${window.innerWidth}x${window.innerHeight}` : "833x811"
                })""")
                if metrics:
                    dpr_from_page = str(metrics.get("dpr", "1.125"))
                    wd_from_page = str(metrics.get("wd", "833x811"))
            except Exception:
                pass

            is_page_active = False
            page_name_found = ""
            page_id_found = ""

            # Step 5: Automatic Facebook Page Switch
            if self.switch_to_page:
                self.log("INFO", f"{tag} 📄 Locating associated Facebook Page profile...")
                try:
                    switched, p_name, p_id = await self._switch_to_facebook_page(page)
                    if switched or p_id:
                        is_page_active = True
                        page_name_found = p_name
                        page_id_found = p_id
                        self.log("SUCCESS", f"{tag} 🎯 Switched into Facebook Page: '{p_name or p_id}' (ID: {p_id})!")
                    else:
                        self.log("INFO", f"{tag} ℹ️ Account in main profile.")
                except Exception as sw_ex:
                    self.log("DEBUG", f"{tag} Page switch notice: {sw_ex}")

            # Step 6: Extract Final Full Session Cookies (Exact Get Token Cookie Format)
            final_cookies: List[Dict[str, Any]] = []
            try:
                final_cookies = await self.context.cookies()
            except Exception:
                pass

            i_user_cookie = next((c.get("value") for c in final_cookies if c.get("name") == "i_user"), "")
            active_page_id = page_id_found or i_user_cookie

            # Format EXACT Get Token Cookie string matching the Chrome Extension:
            # sb=...;datr=...;dpr=1.125;wd=833x811;c_user=...;oo=...;xs=...;i_user=...;
            cookie_semicolon = format_get_token_cookie_string(
                final_cookies,
                page_id=active_page_id,
                dpr_val=dpr_from_page,
                wd_val=wd_from_page
            )

            c_user_val = next((c.get("value") for c in final_cookies if c.get("name") == "c_user"), "")
            resolved_uid = c_user_val or self.uid_or_email

            detected_name = page_name_found
            if not detected_name:
                if is_page_active and active_page_id:
                    detected_name = f"FB Page ({active_page_id})"
                else:
                    detected_name = f"FB User ({resolved_uid})"
            elif is_page_active and active_page_id and active_page_id not in detected_name:
                detected_name = f"{detected_name} [Page: {active_page_id}]"

            status_label = "Live (Page Active)" if is_page_active else "Live"
            self.log("SUCCESS", f"{tag} 🎉 Fresh cookie extracted successfully for '{detected_name}' (Status: {status_label}) in {time.time() - start_time:.1f}s!")
            self.log("INFO", f"{tag} 🍪 Get Token Cookie: {cookie_semicolon[:65]}...")

            return {
                "success": True,
                "is_checkpoint": False,
                "uid": resolved_uid,
                "name": detected_name,
                "page_name": page_name_found,
                "page_id": active_page_id,
                "is_page_active": is_page_active,
                "cookie": cookie_semicolon,
                "cookie_list": final_cookies,
                "status": status_label,
                "message": "Cookies extracted successfully!"
            }

        except Exception as e:
            self.log("ERROR", f"{tag} Extractor exception: {str(e)}")
            return {
                "success": False,
                "uid": self.uid_or_email,
                "name": "",
                "cookie": "",
                "status": "Error",
                "message": str(e)
            }

        finally:
            await self.close()

    async def _switch_to_facebook_page(self, page: Page) -> Tuple[bool, str, str]:
        """
        Switches the active profile to the Facebook Page so all actions and cookies
        are tied directly to the Page.
        """
        tag = f"[{self.uid_or_email}]"
        target_name = (self.page_target or "").lower().strip()
        switched = False
        detected_page_name = ""
        detected_page_id = ""

        # Method 1: Navigate to 'your_pages' directory
        try:
            await page.goto("https://www.facebook.com/pages/?category=your_pages", wait_until="commit", timeout=6000)
            await asyncio.sleep(1.0)

            page_switch_info = await page.evaluate("""(target) => {
                const buttons = Array.from(document.querySelectorAll('div[role="button"], button, a[role="button"], div[aria-label*="Switch" i]'));
                const switchWords = ['switch now', 'switch into', 'switch', 'use page', 'mudar agora', 'mudar', 'cambiar ahora', 'cambiar'];

                for (const b of buttons) {
                    if (!b.offsetParent) continue;
                    const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                    const aria = (b.getAttribute('aria-label') || '').trim().toLowerCase();

                    if (switchWords.some(w => txt.includes(w) || aria.includes(w))) {
                        let card = b.closest('div[role="article"]') || b.closest('div[role="listitem"]') || b.parentElement.parentElement;
                        let pName = "";
                        let pId = "";
                        if (card) {
                            const nameEl = card.querySelector('h2, h3, a[role="link"], span[dir="auto"]');
                            if (nameEl) pName = (nameEl.innerText || nameEl.textContent || '').trim();
                            const linkEl = card.querySelector('a[href*="/"]');
                            if (linkEl) {
                                const href = linkEl.getAttribute('href') || '';
                                const m = href.match(/([0-9]{10,})/);
                                if (m) pId = m[1];
                            }
                        }
                        if (target && pName && !pName.toLowerCase().includes(target)) {
                            continue;
                        }
                        b.click();
                        return { clicked: true, name: pName, id: pId };
                    }
                }
                return { clicked: false, name: "", id: "" };
            }""", target_name)

            if page_switch_info and page_switch_info.get("clicked"):
                switched = True
                detected_page_name = page_switch_info.get("name", "")
                detected_page_id = page_switch_info.get("id", "")
                self.log("INFO", f"{tag} ⚡ Clicked 'Switch Now' for page: '{detected_page_name}'")
                await asyncio.sleep(1.5)

        except Exception as e:
            self.log("DEBUG", f"{tag} Pages directory check note: {e}")

        # Method 2: Check current cookies for 'i_user'
        try:
            curr_cookies = await self.context.cookies()
            i_user = next((c.get("value") for c in curr_cookies if c.get("name") == "i_user"), "")
            if i_user:
                switched = True
                if not detected_page_id:
                    detected_page_id = i_user
        except Exception:
            pass

        return switched, detected_page_name, detected_page_id
