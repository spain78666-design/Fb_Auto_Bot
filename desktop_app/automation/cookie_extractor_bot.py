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
import random
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional, Tuple, Callable

try:
    from automation.browser_window_manager import (
        resolve_tile_context,
        build_window_chrome_args,
        apply_cdp_window_bounds,
        human_move_and_click,
        human_click_coords,
        human_type_text,
        human_session_warmup,
        human_pause,
    )
except ImportError:
    try:
        from desktop_app.automation.browser_window_manager import (
            resolve_tile_context,
            build_window_chrome_args,
            apply_cdp_window_bounds,
            human_move_and_click,
            human_click_coords,
            human_type_text,
            human_session_warmup,
            human_pause,
        )
    except ImportError:
        def resolve_tile_context(account_data=None, window_slot=None, total_window_slots=None, tile_rect=None):
            return 0, 1, (0, 0, 1920, 1080)
        def build_window_chrome_args(tile_rect=None, total_slots=1, slot_index=0, profile_directory=None, apply_scale_factor=True):
            return []
        async def apply_cdp_window_bounds(context, page=None, tile_rect=None, total_slots=1, slot_index=0):
            return False
        async def human_move_and_click(page, locator, hover_pause=True, force_fallback=True):
            try:
                await locator.click(timeout=4000)
                return True
            except Exception:
                return False
        async def human_click_coords(page, x, y, hover_pause=True):
            try:
                await page.mouse.click(x, y)
                return True
            except Exception:
                return False
        async def human_type_text(page, locator, text, clear_first=True, allow_typos=False):
            try:
                await locator.fill(text)
                return True
            except Exception:
                return False
        async def human_session_warmup(page, duration_range=(0.7, 1.3), log_cb=None):
            await asyncio.sleep(0.8)
        async def human_pause(low=0.55, high=1.45, mult=1.0):
            await asyncio.sleep(random.uniform(low, high) * mult)

logger = logging.getLogger("CookieExtractorBot")
logger.setLevel(logging.INFO)

# Optional Playwright and stealth support
try:
    from playwright.async_api import async_playwright, Playwright, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    Playwright = Any
    BrowserContext = Any
    Page = Any

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
        timeout_seconds: int = 45,
        switch_to_page: bool = True,
        page_target: str = "",
        log_callback: Optional[Callable[[str, str], None]] = None,
        window_slot: int = 0,
        total_window_slots: int = 1,
        tile_rect: Optional[Tuple[int, int, int, int]] = None,
        persistent_profile_dir: Optional[str] = None,
        auto_visible_fallback: bool = True,
    ):
        self.uid_or_email = str(uid_or_email).strip()
        self.password = str(password).strip()
        self.two_factor_secret = str(two_factor_secret).strip()
        self.proxy = str(proxy).strip()
        self.headless = headless
        # Respect user's timeout (between 15s and 180s)
        self.timeout_seconds = max(15, min(180, int(timeout_seconds)))
        self.switch_to_page = switch_to_page
        self.page_target = str(page_target).strip()
        self.log_callback = log_callback
        self.window_slot = int(window_slot or 0)
        self.total_window_slots = max(1, int(total_window_slots or 1))
        self.tile_rect = tile_rect
        self.persistent_profile_dir = os.path.abspath(persistent_profile_dir) if persistent_profile_dir else None
        self.auto_visible_fallback = bool(auto_visible_fallback)

        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        self.temp_profile_dir: Optional[str] = None
        self._owns_temp_dir: bool = False
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
        """Cleanly releases browser context, Playwright instances, and only ephemeral temp files."""
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

        if self._owns_temp_dir and self.temp_profile_dir and os.path.exists(self.temp_profile_dir):
            try:
                shutil.rmtree(self.temp_profile_dir, ignore_errors=True)
            except Exception:
                pass
        self.temp_profile_dir = None
        self._owns_temp_dir = False

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
                    if (!b.offsetParent && b.offsetWidth === 0) continue;
                    const txt = (b.innerText || b.textContent || b.value || '').trim().toLowerCase();
                    const aria = (b.getAttribute('aria-label') || '').trim().toLowerCase();
                    const testId = (b.getAttribute('data-cookiebanner') || b.getAttribute('data-testid') || '').toLowerCase();
                    if (
                        testId.includes('accept') || testId.includes('agree') || testId.includes('allow') ||
                        aria.includes('allow all cookies') || aria.includes('decline optional cookies') ||
                        txt.includes('allow all cookies') || txt.includes('accept all') ||
                        txt.includes('only allow essential') || txt.includes('accept cookies') ||
                        txt.includes('allow cookies') || txt.includes('decline optional') ||
                        txt === 'allow all' || txt === 'accept' || txt === 'agree' ||
                        txt === 'i agree' || txt === 'continuer' || txt === 'accepter' ||
                        txt.includes('permitir todas') || txt.includes('alle cookies gestatten')
                    ) {
                        try { b.click(); } catch(e) {}
                    }
                }
            }""")
        except Exception:
            pass

    async def extract_cookie(self) -> Dict[str, Any]:
        """
        Executes credential authentication and extracts fresh Facebook session cookies.
        If silent headless mode stalls with a Timeout and auto_visible_fallback is enabled,
        automatically retries once in a real visible Chrome window to bypass headless stalls.
        """
        if not self.uid_or_email:
            return {"success": False, "uid": "", "name": "", "cookie": "", "status": "Error", "message": "UID/Email is empty."}
        if not self.password:
            return {"success": False, "uid": self.uid_or_email, "name": "", "cookie": "", "status": "Error", "message": "Password is empty."}
        if not PLAYWRIGHT_AVAILABLE:
            self.log("ERROR", "Playwright is not available in the environment.")
            return {"success": False, "uid": self.uid_or_email, "name": "", "cookie": "", "status": "Error", "message": "Playwright is not installed."}

        result = await self._extract_cookie_attempt(use_headless=self.headless, wait_seconds=self.timeout_seconds)

        if (
            not result.get("success")
            and not result.get("is_checkpoint")
            and result.get("status") == "Timeout"
            and self.headless
            and self.auto_visible_fallback
            and not self._cancelled
        ):
            tag = f"[{self.uid_or_email}]"
            retry_wait = max(45, self.timeout_seconds)
            self.log("INFO", f"{tag} 🪟 Background mode timed out; retrying automatically in Visible Browser ({retry_wait}s max)...")
            result = await self._extract_cookie_attempt(use_headless=False, wait_seconds=retry_wait)

        return result

    async def _extract_cookie_attempt(self, use_headless: bool, wait_seconds: int) -> Dict[str, Any]:
        """Runs a single clean browser login & cookie extraction attempt."""
        tag = f"[{self.uid_or_email}]"
        mode_str = "Background" if use_headless else "Visible Browser"
        effective_wait = max(15, min(180, int(wait_seconds)))
        self.log("INFO", f"{tag} 🚀 Initializing Login Engine ({mode_str}, Max Wait: {effective_wait}s)...")

        if self.persistent_profile_dir:
            self.temp_profile_dir = self.persistent_profile_dir
            self._owns_temp_dir = False
            os.makedirs(self.temp_profile_dir, exist_ok=True)
            for lf in ("SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"):
                lp = os.path.join(self.temp_profile_dir, lf)
                if os.path.exists(lp) or os.path.islink(lp):
                    try:
                        if os.path.islink(lp) or os.path.isfile(lp):
                            os.unlink(lp)
                        else:
                            shutil.rmtree(lp, ignore_errors=True)
                    except Exception:
                        pass
        else:
            clean_uid = "".join(c for c in self.uid_or_email if c.isalnum()) or "temp"
            self.temp_profile_dir = os.path.join(tempfile.gettempdir(), f"fb_ext_{clean_uid}_{uuid.uuid4().hex[:6]}")
            self._owns_temp_dir = True
            os.makedirs(self.temp_profile_dir, exist_ok=True)

        start_time = time.time()

        try:
            self.playwright = await async_playwright().start()

            slot_idx, total_slots, resolved_tile = resolve_tile_context(
                window_slot=self.window_slot,
                total_window_slots=self.total_window_slots,
                tile_rect=self.tile_rect,
            )

            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-notifications",
                "--no-first-run",
                "--no-default-browser-check",
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
            if not use_headless:
                launch_args.extend(build_window_chrome_args(
                    tile_rect=resolved_tile,
                    total_slots=total_slots,
                    slot_index=slot_idx,
                ))

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

            # Launch with real Chrome binary + channel fallback (without spoofing mismatched UA)
            chrome_exe = None
            try:
                from automation.extension_manager import get_system_chrome_executable
                chrome_exe = get_system_chrome_executable()
            except Exception:
                chrome_exe = None

            launch_candidates: List[Tuple[Optional[str], Optional[str]]] = []
            if chrome_exe and os.path.isfile(chrome_exe):
                launch_candidates.append(("real_chrome", chrome_exe))
            launch_candidates.extend([("chrome", None), ("msedge", None), ("chromium", None), (None, None)])
            context = None

            for ch, exe_p in launch_candidates:
                try:
                    kws: Dict[str, Any] = {
                        "user_data_dir": self.temp_profile_dir,
                        "headless": use_headless,
                        "args": launch_args,
                        "ignore_default_args": ["--enable-automation", "--disable-extensions"],
                        "locale": "en-US",
                        "extra_http_headers": {
                            "Accept-Language": "en-US,en;q=0.9",
                        }
                    }
                    if use_headless:
                        kws["viewport"] = {"width": 1280, "height": 800}
                    else:
                        kws["no_viewport"] = True
                    if proxy_cfg:
                        kws["proxy"] = proxy_cfg
                    if exe_p:
                        kws["executable_path"] = exe_p
                    elif ch and ch != "real_chrome":
                        kws["channel"] = ch

                    context = await self.playwright.chromium.launch_persistent_context(**kws)
                    self.context = context
                    break
                except Exception:
                    continue

            if not self.context:
                raise Exception("Could not launch Google Chrome or MS Edge on this PC.")

            page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            if not use_headless:
                await apply_cdp_window_bounds(
                    self.context,
                    page,
                    tile_rect=resolved_tile,
                    total_slots=total_slots,
                    slot_index=slot_idx,
                )

            # Minimal clean stealth without clobbering native Chrome window.chrome or mismatching Client Hints
            try:
                await page.add_init_script("""
                    try {
                        delete Object.getPrototypeOf(navigator).webdriver;
                    } catch (e) {}
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                """)
            except Exception:
                pass

            if PLAYWRIGHT_STEALTH_AVAILABLE and use_headless:
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
                    resp = await page.goto(u, wait_until="domcontentloaded", timeout=15000)
                    if resp and resp.status >= 400:
                        self.log("WARNING", f"{tag} HTTP {resp.status} received from {u}; trying next fallback...")
                        continue
                    nav_ok = True
                    break
                except Exception:
                    try:
                        resp = await page.goto(u, timeout=12000)
                        if resp and resp.status >= 400:
                            continue
                        nav_ok = True
                        break
                    except Exception:
                        continue

            if not nav_ok:
                try:
                    await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=15000)
                except Exception:
                    pass

            if not use_headless:
                await apply_cdp_window_bounds(
                    self.context,
                    page,
                    tile_rect=resolved_tile,
                    total_slots=total_slots,
                    slot_index=slot_idx,
                )

            await asyncio.sleep(0.8)

            # Check if session is already authenticated (c_user AND xs required for active login)
            try:
                initial_cookies = await self.context.cookies()
                init_c_user = next((c.get("value") for c in initial_cookies if c.get("name") == "c_user"), None)
                init_xs = next((c.get("value") for c in initial_cookies if c.get("name") == "xs"), None)
                if init_c_user and init_xs:
                    self.log("SUCCESS", f"{tag} ✅ Session already active for c_user={init_c_user}!")
                    has_authenticated = True
                else:
                    has_authenticated = False
            except Exception:
                has_authenticated = False

            if not has_authenticated:
                await self._dismiss_all_overlays(page)
                await asyncio.sleep(0.4)

                # Step 2: Locate and Fill Email and Password Inputs (with React-safe setter fallback)
                self.log("INFO", f"{tag} ✍️ Entering Facebook UID & Password naturally...")
                email_filled = False
                pass_filled = False

                try:
                    email_loc = page.locator(
                        'input[name="email"], input#email, input#m_login_email, input[data-testid="royal_email"], input[type="text"][autocomplete="username"]'
                    ).first
                    await email_loc.wait_for(state="visible", timeout=5000)
                    email_filled = await human_type_text(page, email_loc, self.uid_or_email, clear_first=True)
                except Exception:
                    pass

                await asyncio.sleep(random.uniform(0.22, 0.48))

                try:
                    pass_loc = page.locator(
                        'input[name="pass"], input#pass, input#m_login_password, input[data-testid="royal_pass"], input[type="password"]'
                    ).first
                    await pass_loc.wait_for(state="visible", timeout=5000)
                    pass_filled = await human_type_text(page, pass_loc, self.password, clear_first=True)
                except Exception:
                    pass

                if not email_filled or not pass_filled:
                    await page.evaluate("""(data) => {
                        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        function setReactVal(el, val) {
                            if (!el) return;
                            el.focus();
                            if (nativeSetter) {
                                nativeSetter.call(el, val);
                            } else {
                                el.value = val;
                            }
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        const emailInput = document.querySelector('input[name="email"], input#email, input#m_login_email, input[data-testid="royal_email"], input[type="text"][autocomplete="username"], input[type="text"]');
                        const passInput = document.querySelector('input[name="pass"], input#pass, input#m_login_password, input[data-testid="royal_pass"], input[type="password"]');
                        if (emailInput && !emailInput.value) setReactVal(emailInput, data.u);
                        if (passInput && !passInput.value) setReactVal(passInput, data.p);
                    }""", {"u": self.uid_or_email, "p": self.password})

                await asyncio.sleep(random.uniform(0.35, 0.65))

                # Step 3: Natural Form Submission (supports both classic button & modern React div[role="button"])
                self.log("INFO", f"{tag} ⚡ Submitting Facebook login credentials...")
                submitted = False
                submit_selectors = [
                    'button[name="login"]',
                    'button#loginbutton',
                    'button[data-testid="royal_login_button"]',
                    'div[aria-label="Log in"][role="button"]',
                    'div[aria-label="Log In"][role="button"]',
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Log In")',
                    'button:has-text("Log in")',
                    'div[role="button"]:has-text("Log in")',
                    'div[role="button"]:has-text("Log In")',
                    'button:has-text("Login")'
                ]
                for ss in submit_selectors:
                    s_btn = page.locator(ss).first
                    if await s_btn.count() > 0 and await s_btn.is_visible():
                        try:
                            if await human_move_and_click(page, s_btn, hover_pause=True):
                                submitted = True
                                break
                        except Exception:
                            continue

                if not submitted:
                    try:
                        submitted = await page.evaluate("""() => {
                            const b = document.querySelector('button[name="login"], button#loginbutton, button[data-testid="royal_login_button"], div[aria-label="Log in"][role="button"], button[type="submit"], input[type="submit"]');
                            if (b) { b.click(); return true; }
                            const form = document.querySelector('form');
                            if (form) { form.submit(); return true; }
                            return false;
                        }""")
                    except Exception:
                        submitted = False

                if not submitted:
                    await page.keyboard.press("Enter")

                # Step 4: High-Frequency Authentication Polling (Every 0.35s)
                self.log("INFO", f"{tag} ⏳ Awaiting Facebook session tokens...")
                error_status = "Timeout"
                error_msg = f"Login timed out after {effective_wait}s without live session cookie."

                poll_start = time.time()
                c_user_first_seen_at: Optional[float] = None
                while time.time() - poll_start < effective_wait:
                    if self._cancelled:
                        return {"success": False, "uid": self.uid_or_email, "name": "", "cookie": "", "status": "Cancelled", "message": "Operation cancelled."}

                    await asyncio.sleep(0.35)

                    curr_cookies: List[Dict[str, Any]] = []
                    try:
                        curr_cookies = await self.context.cookies()
                    except Exception:
                        pass

                    c_user_val = next((c.get("value") for c in curr_cookies if c.get("name") == "c_user"), None)
                    xs_val = next((c.get("value") for c in curr_cookies if c.get("name") == "xs"), None)

                    if c_user_val and xs_val:
                        has_authenticated = True
                        self.log("SUCCESS", f"{tag} ✅ Live Facebook session active! c_user={c_user_val}")
                        break

                    if c_user_val and not xs_val:
                        if c_user_first_seen_at is None:
                            c_user_first_seen_at = time.time()

                    page_text = ""
                    try:
                        page_text = (await page.evaluate("() => (document.body ? document.body.innerText : '')")).lower()
                    except Exception:
                        pass

                    # 1. Check for Wrong Password -> Instant Exit
                    if any(w in page_text for w in [
                        "the password you entered is incorrect",
                        "incorrect password",
                        "the password that you've entered is incorrect",
                        "wrong password",
                        "invalid username or password",
                        "galt password",
                        "password you entered is wrong",
                        "find your account and log in"
                    ]):
                        error_status = "Wrong Password"
                        error_msg = "Incorrect Facebook Password or UID."
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

                    # 3. Check for 2FA / Approvals Code prompt (classic + modern /two_step_verification/)
                    curr_url = page.url.lower()
                    two_fa_input = page.locator(
                        'input[name="approvals_code"], input[name="code"], input#approvals_code, input[data-testid="royal_code"], input[autocomplete="one-time-code"], input[id^="_r_"]'
                    ).first
                    has_2fa_ui = (
                        "/two_step_verification/" in curr_url
                        or "enter the 6-digit code" in page_text
                        or "authentication app" in page_text
                        or "login code" in page_text
                    )
                    if (await two_fa_input.count() > 0 and await two_fa_input.is_visible()) or (has_2fa_ui and await two_fa_input.count() > 0):
                        if self.two_factor_secret:
                            totp_code = generate_totp(self.two_factor_secret)
                            if totp_code:
                                self.log("INFO", f"{tag} 🔑 2FA Required. Generated TOTP ({totp_code}). Submitting...")
                                await human_type_text(page, two_fa_input, totp_code, clear_first=True)
                                await asyncio.sleep(random.uniform(0.25, 0.5))
                                submit_2fa = page.locator(
                                    'button#checkpointSubmitButton, button[type="submit"], button:has-text("Continue"), div[role="button"]:has-text("Continue"), button:has-text("Submit")'
                                ).first
                                if await submit_2fa.count() > 0 and await submit_2fa.is_visible():
                                    await human_move_and_click(page, submit_2fa)
                                else:
                                    await page.keyboard.press("Enter")
                                await asyncio.sleep(2.0)
                                continue
                        else:
                            error_status = "2FA Required"
                            error_msg = "Two-Factor Authentication (2FA) required, but no 2FA secret was provided."
                            self.log("WARNING", f"{tag} ⚠️ 2FA code required.")
                            break

                    # 4. Check for device/notification approval prompt ("Check your notifications")
                    if any(ap in page_text for ap in [
                        "check your notifications on another device",
                        "waiting for approval",
                        "approve your login"
                    ]) and (time.time() - poll_start > 5.0):
                        error_status = "2FA / Device Approval"
                        error_msg = "Facebook requested device notification approval."
                        self.log("WARNING", f"{tag} ⚠️ Facebook requested login approval on another device.")
                        break

                    # 5. Check for Genuine Checkpoint Screen
                    is_checkpoint_url = ("/checkpoint/" in curr_url or "/recover/" in curr_url)
                    is_checkpoint_text = any(cp in page_text for cp in [
                        "we suspended your account",
                        "your account has been locked",
                        "account locked",
                        "confirm your identity",
                        "upload a photo of your id",
                        "security check",
                        "enter the characters you see"
                    ])
                    if (is_checkpoint_url or is_checkpoint_text) and (time.time() - poll_start > 4.0):
                        if await two_fa_input.count() == 0:
                            error_status = "Checkpoint"
                            error_msg = "Account is in Facebook security checkpoint."
                            self.log("WARNING", f"{tag} 🔒 Genuine Checkpoint detected. Routed to Checkpoint column.")
                            break

                    # 6. Auto-dismiss Save Info / Remember Browser / Not Now / Cookie dialogs cleanly
                    try:
                        await self._dismiss_all_overlays(page)
                        if time.time() - poll_start > 2.2:
                            save_selectors = [
                                'div[role="dialog"] button:has-text("Not Now")',
                                'div[role="dialog"] a:has-text("Not Now")',
                                'div[role="dialog"] div[role="button"]:has-text("Not Now")',
                                'div[role="dialog"] button:has-text("Save Info")',
                                'div[role="dialog"] div[role="button"]:has-text("Save Info")',
                                'button#checkpointSubmitButton:has-text("Save Browser")',
                                'button:has-text("Trust this device")',
                                'div[role="button"]:has-text("Trust this device")',
                            ]
                            for s_sel in save_selectors:
                                s_btn = page.locator(s_sel).first
                                if await s_btn.count() > 0 and await s_btn.is_visible():
                                    await human_move_and_click(page, s_btn, hover_pause=False)
                                    await asyncio.sleep(0.45)
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

                if c_user_found and xs_found:
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
            # CASE A: Authentication Failure / Checkpoint / Timeout Exit
            # =========================================================================
            if not has_authenticated:
                resolved_uid = self.uid_or_email
                is_cp = (error_status in ["Checkpoint", "Disabled"] or "checkpoint" in error_msg.lower())

                if is_cp:
                    self.log("WARNING", f"{tag} 🔒 Account status confirmed: {error_status}. (Routed to Checkpoint list)")
                else:
                    self.log("WARNING", f"{tag} ⏱️ Account login did not complete ({error_status}): {error_msg}")

                cp_cookies: List[Dict[str, Any]] = []
                try:
                    if self.context:
                        cp_cookies = await self.context.cookies()
                except Exception:
                    pass

                cp_cookie_str = ""
                if cp_cookies and is_cp:
                    cp_cookie_str = format_get_token_cookie_string(cp_cookies)

                return {
                    "success": False,
                    "is_checkpoint": is_cp,
                    "uid": resolved_uid,
                    "name": f"FB Checkpoint ({resolved_uid})" if is_cp else f"FB_{resolved_uid}",
                    "cookie": cp_cookie_str,
                    "status": error_status,
                    "message": error_msg
                }

            # =========================================================================
            # CASE B: LIVE Session - Warm-up, Page Switch & Full Token Extraction
            # =========================================================================
            await human_session_warmup(page, duration_range=(0.7, 1.3))
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

                # Handle optional confirmation modal ("Switch" / "Continue") & wait for i_user cookie update
                for _ in range(10):
                    await asyncio.sleep(0.5)
                    try:
                        modal_confirm = page.locator(
                            'div[role="dialog"] div[role="button"]:has-text("Switch"), '
                            'div[role="dialog"] button:has-text("Switch"), '
                            'div[role="dialog"] div[role="button"]:has-text("Continue"), '
                            'div[role="dialog"] button:has-text("Continue")'
                        ).last
                        if await modal_confirm.count() > 0 and await modal_confirm.is_visible():
                            await human_move_and_click(page, modal_confirm)
                            await human_pause(0.8, 1.3)
                    except Exception:
                        pass

                    try:
                        curr_cookies = await self.context.cookies()
                        i_user = next((c.get("value") for c in curr_cookies if c.get("name") == "i_user"), "")
                        if i_user:
                            detected_page_id = detected_page_id or i_user
                            break
                    except Exception:
                        pass

        except Exception as e:
            self.log("DEBUG", f"{tag} Pages directory check note: {e}")

        # Method 1b: Top-right Profile Switcher fallback (when Pages directory shows no Switch Now button)
        if not switched:
            try:
                await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=10000)
                await asyncio.sleep(1.0)
                avatar_btn = page.locator(
                    'div[aria-label="Your profile"][role="button"], '
                    'div[aria-label="Account"][role="button"], '
                    'svg[aria-label="Your profile"]'
                ).first
                if await avatar_btn.count() > 0 and await avatar_btn.is_visible():
                    await human_move_and_click(page, avatar_btn, hover_pause=False)
                    await asyncio.sleep(0.9)
                    see_all = page.locator(
                        'div[role="dialog"] span:has-text("See all profiles"), '
                        'div[role="menu"] span:has-text("See all profiles"), '
                        'div[role="button"]:has-text("See all profiles")'
                    ).first
                    if await see_all.count() > 0 and await see_all.is_visible():
                        await human_move_and_click(page, see_all, hover_pause=False)
                        await asyncio.sleep(1.0)

                    # Click secondary profile / Page entry inside the profile switcher menu
                    picked = await page.evaluate("""(target) => {
                        const menus = Array.from(document.querySelectorAll('div[role="dialog"], div[role="menu"], div[aria-label*="Account" i]'));
                        for (const m of menus) {
                            const items = Array.from(m.querySelectorAll('div[role="listitem"], div[role="radio"], div[role="button"]'));
                            for (const it of items) {
                                const txt = (it.innerText || it.textContent || '').trim();
                                if (!txt || txt.length > 90) continue;
                                const low = txt.toLowerCase();
                                if (low.includes('see all profiles') || low.includes('settings') || low.includes('log out') || low.includes('help') || low.includes('display')) continue;
                                // Skip already-selected main personal profile (first radio checked)
                                if (it.getAttribute('aria-checked') === 'true') continue;
                                if (target && !low.includes(target)) continue;
                                it.click();
                                return txt.split('\\n')[0].trim();
                            }
                        }
                        return '';
                    }""", target_name)
                    if picked:
                        detected_page_name = detected_page_name or picked
                        for _ in range(10):
                            await asyncio.sleep(0.5)
                            curr_cookies = await self.context.cookies()
                            i_user = next((c.get("value") for c in curr_cookies if c.get("name") == "i_user"), "")
                            if i_user:
                                switched = True
                                detected_page_id = detected_page_id or i_user
                                break
            except Exception as sw_menu_err:
                self.log("DEBUG", f"{tag} Top-right profile switcher fallback notice: {sw_menu_err}")

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
