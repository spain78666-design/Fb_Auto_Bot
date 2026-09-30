#!/usr/bin/env python3
"""
FB Auto Bot - Facebook Automation Suite
automation/cookie_extractor_bot.py - Automated Facebook Session Cookie Extractor Engine

Automates bulletproof, high-speed extraction of fresh Facebook session cookies
(c_user, xs, datr, sb, fr, etc.) from UID/Email & Password credentials.
Outputs standard semicolon string format matching the Chrome extension 'Get Token Cookie'.
"""

import os
import sys
import json
import time
import random
import uuid
import shutil
import tempfile
import asyncio
import logging
import gc
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Tuple, Callable

# Playwright async
try:
    from playwright.async_api import async_playwright, BrowserContext, Page, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from playwright_stealth import stealth_async
    PLAYWRIGHT_STEALTH_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_STEALTH_AVAILABLE = False

# Import TOTP generator and Cookie Parser from session_manager if available
try:
    from automation.session_manager import generate_totp, SessionCookieParser
except ImportError:
    try:
        from desktop_app.automation.session_manager import generate_totp, SessionCookieParser
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

        class SessionCookieParser:
            @staticmethod
            def cookies_to_semicolon_string(cookies: List[Dict[str, Any]]) -> str:
                """
                Converts normalized cookie list to string format matching
                the Chrome extension 'Get Token Cookie' (sb, datr, _fbp, c_user, i_user, xs, fr...).
                """
                priority_names = ["sb", "datr", "_fbp", "c_user", "i_user", "xs", "fr", "presence", "wd", "dpr"]
                c_map = {}
                for c in cookies:
                    n = c.get("name")
                    v = c.get("value")
                    if n and v is not None:
                        c_map[n] = v

                parts = []
                seen = set()
                for p in priority_names:
                    if p in c_map:
                        parts.append(f"{p}={c_map[p]}")
                        seen.add(p)

                for k, v in c_map.items():
                    if k not in seen:
                        parts.append(f"{k}={v}")

                return ";".join(parts) + (";" if parts else "")

logger = logging.getLogger("FBAutoBot.CookieExtractor")


class FacebookCookieExtractorBot:
    """
    Automated bot that logs into Facebook using credentials and extracts fresh session cookies.
    Uses launch_persistent_context with anti-detection flags matching real Google Chrome.
    Formats cookies matching 'Get Token Cookie' Chrome extension.
    """

    def __init__(
        self,
        uid_or_email: str,
        password: str,
        two_factor_secret: str = "",
        proxy: str = "",
        headless: bool = True,
        timeout_seconds: int = 90,
        switch_to_page: bool = False,
        page_target: str = "",
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.uid_or_email = str(uid_or_email).strip()
        self.password = str(password).strip()
        self.two_factor_secret = str(two_factor_secret).strip()
        self.proxy = str(proxy).strip()
        self.headless = headless
        self.timeout_seconds = max(45, int(timeout_seconds))
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

        # Clean temp user profile directory
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

    async def extract_cookie(self) -> Dict[str, Any]:
        """
        Executes credential authentication and extracts fresh Facebook cookies.
        Returns a dict containing:
          - success: bool
          - uid: str
          - name: str
          - cookie: str (semicolon string format matching 'Get Token Cookie' extension)
          - status: str ('Live', 'Wrong Password', 'Checkpoint', '2FA Required', 'Timeout', 'Error')
          - message: str
        """
        if not self.uid_or_email:
            return {
                "success": False,
                "uid": "",
                "name": "",
                "cookie": "",
                "status": "Error",
                "message": "UID / Email is empty."
            }

        if not self.password:
            return {
                "success": False,
                "uid": self.uid_or_email,
                "name": "",
                "cookie": "",
                "status": "Error",
                "message": "Password is empty."
            }

        if not PLAYWRIGHT_AVAILABLE:
            self.log("ERROR", "Playwright is not available in the environment.")
            return {
                "success": False,
                "uid": self.uid_or_email,
                "name": "",
                "cookie": "",
                "status": "Error",
                "message": "Playwright is not installed."
            }

        tag = f"[{self.uid_or_email}]"
        mode_str = "Background (Headless)" if self.headless else "Visible Browser"
        self.log("INFO", f"{tag} 🚀 Initializing Cookie Extractor Engine ({mode_str}, Timeout: {self.timeout_seconds}s)...")

        # Create unique isolated profile directory for anti-detection
        clean_uid = "".join(c for c in self.uid_or_email if c.isalnum()) or "temp"
        self.temp_profile_dir = os.path.join(tempfile.gettempdir(), f"fb_cookie_ext_{clean_uid}_{uuid.uuid4().hex[:6]}")
        os.makedirs(self.temp_profile_dir, exist_ok=True)

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

            if not proxy_cfg:
                launch_args.append("--no-proxy-server")

            # Smart persistent context launch with browser channel fallbacks
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
                raise Exception("Could not launch Google Chrome, Chromium, or MS Edge on this PC.")

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
                    window.chrome = {
                        app: { isInstalled: false },
                        runtime: {}
                    };
                """)
            except Exception:
                pass

            if PLAYWRIGHT_STEALTH_AVAILABLE:
                try:
                    await stealth_async(page)
                except Exception:
                    pass

            # Step 1: Navigate to Facebook Login Portal
            self.log("INFO", f"{tag} 🌐 Navigating to Facebook Login Portal...")
            login_urls = [
                "https://www.facebook.com/login.php",
                "https://www.facebook.com/",
                "https://mbasic.facebook.com/login.php"
            ]

            nav_ok = False
            for u in login_urls:
                if self._cancelled:
                    return {"success": False, "uid": self.uid_or_email, "name": "", "cookie": "", "status": "Cancelled", "message": "Cancelled."}
                try:
                    await page.goto(u, wait_until="domcontentloaded", timeout=25000)
                    nav_ok = True
                    break
                except Exception as ge:
                    self.log("WARNING", f"{tag} Load notice ({u}): {str(ge)[:50]}")

            if not nav_ok:
                try:
                    await page.goto("https://www.facebook.com/", timeout=30000)
                except Exception:
                    pass

            # Step 2: Dismiss Cookie Consent Banners if present
            try:
                consent_selectors = [
                    'button[data-cookiebanner="accept_button"]',
                    'button[data-cookiebanner="accept_only_essential_button"]',
                    'button[title="Allow all cookies"]',
                    'button[title="Accept all"]',
                    'button:has-text("Allow all cookies")',
                    'button:has-text("Accept all")',
                    'button:has-text("Only allow essential cookies")',
                    'button:has-text("Decline optional cookies")',
                    'div[aria-label*="cookie" i] button'
                ]
                for c_sel in consent_selectors:
                    c_btn = page.locator(c_sel).first
                    if await c_btn.count() > 0 and await c_btn.is_visible():
                        await c_btn.click()
                        await asyncio.sleep(0.5)
                        break
            except Exception:
                pass

            # Step 3: Locate Email / UID and Password Input Fields
            email_selectors = [
                'input[name="email"]',
                'input#email',
                'input[type="text"][autocomplete="username"]',
                'input[data-testid="royal_email"]',
                'input[aria-label*="Email" i]',
                'input[placeholder*="Email" i]',
                'input[placeholder*="phone" i]',
                'input[name="m_ts"]',
                'input[type="text"]'
            ]
            pass_selectors = [
                'input[name="pass"]',
                'input#pass',
                'input[type="password"]',
                'input[data-testid="royal_pass"]',
                'input[aria-label*="Password" i]',
                'input[placeholder*="Password" i]'
            ]

            email_el = None
            pass_el = None

            # Poll for input fields up to 10 seconds
            field_find_start = time.time()
            while time.time() - field_find_start < 10.0:
                if self._cancelled:
                    return {"success": False, "uid": self.uid_or_email, "name": "", "cookie": "", "status": "Cancelled", "message": "Cancelled."}

                for es in email_selectors:
                    el = page.locator(es).first
                    if await el.count() > 0 and await el.is_visible():
                        email_el = el
                        break

                for ps in pass_selectors:
                    el = page.locator(ps).first
                    if await el.count() > 0 and await el.is_visible():
                        pass_el = el
                        break

                if email_el and pass_el:
                    break
                await asyncio.sleep(0.5)

            # Step 4: Fill Credentials & Submit Form
            if email_el and pass_el:
                self.log("INFO", f"{tag} ✍️ Inputting Facebook UID/Email & Password...")
                try:
                    await email_el.click()
                    await email_el.fill(self.uid_or_email)
                    await asyncio.sleep(0.3)
                    await pass_el.click()
                    await pass_el.fill(self.password)
                    await asyncio.sleep(0.4)
                except Exception as fe:
                    self.log("WARNING", f"{tag} Fill notice: {fe}")

                self.log("INFO", f"{tag} ⚡ Submitting login form...")
                submit_selectors = [
                    'button[name="login"]',
                    'button#loginbutton',
                    'button[data-testid="royal_login_button"]',
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'input[name="login"]',
                    'button:has-text("Log In")',
                    'button:has-text("Login")'
                ]
                submitted = False
                for ss in submit_selectors:
                    s_btn = page.locator(ss).first
                    if await s_btn.count() > 0 and await s_btn.is_visible():
                        await s_btn.click()
                        submitted = True
                        break

                if not submitted:
                    try:
                        submitted = await page.evaluate("""() => {
                            const b = document.querySelector('button[name="login"], button#loginbutton, button[type="submit"], input[type="submit"]');
                            if (b) { b.click(); return true; }
                            const f = document.querySelector('form');
                            if (f) { f.submit(); return true; }
                            return false;
                        }""")
                    except Exception:
                        pass

                if not submitted:
                    await page.keyboard.press("Enter")
            else:
                self.log("WARNING", f"{tag} Input fields not immediately matched; pressing Enter on page.")
                await page.keyboard.press("Enter")

            # Step 5: Continuous Monitoring Loop for Authentication, Captcha, 2FA, Checkpoints & Session Cookies
            self.log("INFO", f"{tag} ⏳ Awaiting Facebook authentication & cookies (Max wait: {self.timeout_seconds}s)...")
            has_authenticated = False
            error_status = "Timeout"
            error_msg = f"Login timed out after {self.timeout_seconds} seconds."

            start_time = time.time()
            max_wait = self.timeout_seconds

            while time.time() - start_time < max_wait:
                if self._cancelled:
                    return {"success": False, "uid": self.uid_or_email, "name": "", "cookie": "", "status": "Cancelled", "message": "Operation cancelled."}

                await asyncio.sleep(1.0)

                # Check cookies directly from browser context
                curr_cookies = await self.context.cookies()
                c_user_val = next((c.get("value") for c in curr_cookies if c.get("name") == "c_user"), None)
                xs_val = next((c.get("value") for c in curr_cookies if c.get("name") == "xs"), None)
                datr_val = next((c.get("value") for c in curr_cookies if c.get("name") == "datr"), None)

                curr_url = page.url.lower()

                # If c_user exists in session cookies and not stuck in a security block -> LIVE!
                if c_user_val and (xs_val or datr_val):
                    if "/checkpoint/" not in curr_url and "/recover/" not in curr_url and "suspended" not in curr_url:
                        has_authenticated = True
                        self.log("SUCCESS", f"{tag} ✅ Live Facebook session tokens detected! c_user={c_user_val}")
                        break

                page_text = ""
                try:
                    page_text = await page.evaluate("() => (document.body ? document.body.innerText : '').toLowerCase()")
                except Exception:
                    pass

                # Check for Wrong Password
                if "the password you entered is incorrect" in page_text or "incorrect password" in page_text or "the password that you've entered is incorrect" in page_text or "wrong password" in page_text:
                    error_status = "Wrong Password"
                    error_msg = "Incorrect Facebook Password."
                    self.log("ERROR", f"{tag} ❌ Wrong password for account.")
                    break

                # Check for Disabled Account
                if "account has been disabled" in page_text or "your account has been disabled" in page_text or "we disabled your account" in page_text:
                    error_status = "Disabled"
                    error_msg = "Account is disabled by Facebook."
                    self.log("ERROR", f"{tag} 🚫 Facebook account is disabled.")
                    break

                # Check for Captcha challenge
                if "security check" in page_text and ("type the characters" in page_text or "captcha" in page_text or "recaptcha" in page_text):
                    self.log("WARNING", f"{tag} 🧩 Security Captcha detected on screen. Waiting for verification...")

                # Check for 2FA / Approvals code prompt
                two_fa_input = page.locator('input[name="approvals_code"], input[name="code"], input#approvals_code').first
                if await two_fa_input.count() > 0 and await two_fa_input.is_visible():
                    if self.two_factor_secret:
                        totp_code = generate_totp(self.two_factor_secret)
                        if totp_code:
                            self.log("INFO", f"{tag} 🔑 2FA Required. Generated TOTP ({totp_code}). Submitting...")
                            await two_fa_input.fill(totp_code)
                            await asyncio.sleep(0.4)
                            submit_btn = page.locator('button#checkpointSubmitButton, button[type="submit"], button:has-text("Continue"), button:has-text("Submit")').first
                            if await submit_btn.count() > 0 and await submit_btn.is_visible():
                                await submit_btn.click()
                            else:
                                await page.keyboard.press("Enter")
                            await asyncio.sleep(2.5)
                            continue
                    else:
                        error_status = "2FA Required"
                        error_msg = "Two-Factor Authentication (2FA) required, but no 2FA secret was provided."
                        self.log("WARNING", f"{tag} ⚠️ 2FA code required.")
                        break

                # Check for genuine Checkpoint screen
                if ("/checkpoint/" in curr_url or "/recover/initiate" in curr_url) and ("confirm your identity" in page_text or "we suspended your account" in page_text or "your account has been locked" in page_text or "account locked" in page_text or "help us confirm" in page_text):
                    error_status = "Checkpoint"
                    error_msg = "Account is in Facebook security checkpoint."
                    self.log("WARNING", f"{tag} 🔒 Account triggered Facebook security checkpoint.")
                    break

                # Handle "Save login info" / "Remember password" / "Not Now" dialogs
                try:
                    save_info_selectors = [
                        'button:has-text("Save")',
                        'button:has-text("Save Info")',
                        'button:has-text("Not Now")',
                        'a:has-text("Not Now")',
                        'button:has-text("Continue")',
                        'button:has-text("OK")'
                    ]
                    for s_sel in save_info_selectors:
                        s_btn = page.locator(s_sel).first
                        if await s_btn.count() > 0 and await s_btn.is_visible():
                            await s_btn.click()
                            await asyncio.sleep(0.8)
                            break
                except Exception:
                    pass

            if not has_authenticated:
                cp_cookies = []
                cp_cookie_str = ""
                try:
                    if self.context:
                        cp_cookies = await self.context.cookies()
                        cp_cookie_str = SessionCookieParser.cookies_to_semicolon_string(cp_cookies)
                except Exception:
                    pass

                c_user_val = next((c.get("value") for c in cp_cookies if c.get("name") == "c_user"), "")
                resolved_uid = c_user_val or self.uid_or_email
                is_cp = (error_status == "Checkpoint")

                return {
                    "success": False,
                    "is_checkpoint": is_cp,
                    "uid": resolved_uid,
                    "name": f"FB Checkpoint ({resolved_uid})" if is_cp else "",
                    "cookie": cp_cookie_str,
                    "cookie_list": cp_cookies,
                    "status": error_status,
                    "message": error_msg
                }

            # Optional Facebook Page switch if requested
            is_page_active = False
            page_name_found = ""
            page_id_found = ""
            if self.switch_to_page and not self._cancelled:
                try:
                    sw_ok, p_name, p_id = await self._switch_to_facebook_page(page)
                    if sw_ok:
                        is_page_active = True
                        page_name_found = p_name
                        page_id_found = p_id
                        self.log("SUCCESS", f"{tag} 🎯 Active profile set to Page: '{p_name}' (ID: {p_id})")
                except Exception as sw_ex:
                    self.log("DEBUG", f"{tag} Page switch note: {sw_ex}")

            # Retrieve final cookies formatted identically to 'Get Token Cookie' Chrome extension
            final_cookies = await self.context.cookies()
            cookie_semicolon = SessionCookieParser.cookies_to_semicolon_string(final_cookies)

            # Detect UID from c_user cookie
            c_user_val = next((c.get("value") for c in final_cookies if c.get("name") == "c_user"), "")
            i_user_val = next((c.get("value") for c in final_cookies if c.get("name") == "i_user"), "")
            resolved_uid = c_user_val or self.uid_or_email

            # Detect Facebook Display Name
            detected_name = page_name_found
            if not detected_name:
                try:
                    detected_name = await page.evaluate("""() => {
                        const links = Array.from(document.querySelectorAll('a[href*="/me/"], a[aria-label*="Your profile"], a[href*="profile.php"]'));
                        for (const a of links) {
                            const aria = (a.getAttribute('aria-label') || '').trim();
                            if (aria && !aria.toLowerCase().includes('your profile') && aria.length > 1) {
                                return aria;
                            }
                            const txt = (a.innerText || a.textContent || '').trim();
                            if (txt && txt.length > 1 && !txt.toLowerCase().includes('profile')) {
                                return txt;
                            }
                        }
                        return null;
                    }""")
                except Exception:
                    pass

            if not detected_name or len(detected_name) < 2:
                if is_page_active and i_user_val:
                    detected_name = f"FB Page ({i_user_val})"
                else:
                    detected_name = f"FB User ({resolved_uid})"
            elif is_page_active and i_user_val and i_user_val not in detected_name:
                detected_name = f"{detected_name} [Page: {i_user_val}]"

            status_label = "Live (Page Active)" if is_page_active else "Live"
            self.log("SUCCESS", f"{tag} 🎉 Fresh cookie extracted successfully for '{detected_name}' (Status: {status_label})!")
            self.log("INFO", f"{tag} 🍪 Cookie Preview ('Get Token Cookie'): {cookie_semicolon[:60]}... ({len(final_cookies)} tokens)")

            return {
                "success": True,
                "is_checkpoint": False,
                "uid": resolved_uid,
                "name": detected_name,
                "page_name": page_name_found,
                "page_id": page_id_found or i_user_val,
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
        Attempts a quick switch to an active Facebook Page profile if available.
        """
        tag = f"[{self.uid_or_email}]"
        target_name = (self.page_target or "").lower().strip()
        switched = False
        detected_page_name = ""
        detected_page_id = ""

        try:
            await page.goto("https://www.facebook.com/pages/?category=your_pages", wait_until="domcontentloaded", timeout=12000)
            await asyncio.sleep(1.5)

            page_switch_info = await page.evaluate("""(target) => {
                const buttons = Array.from(document.querySelectorAll('div[role="button"], button, a[role="button"]'));
                const switchWords = ['switch now', 'switch into', 'switch', 'use page', 'mudar agora', 'mudar', 'cambiar ahora', 'cambiar'];

                for (const b of buttons) {
                    if (!b.offsetParent) continue;
                    const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                    const aria = (b.getAttribute('aria-label') || '').trim().toLowerCase();

                    if (switchWords.some(w => txt.includes(w) || aria.includes(w))) {
                        let card = b.closest('div[role="article"]') || b.closest('div[role="listitem"]') || b.parentElement.parentElement;
                        let pName = "";
                        if (card) {
                            const nameEl = card.querySelector('h2, h3, a[role="link"], span[dir="auto"]');
                            if (nameEl) pName = (nameEl.innerText || nameEl.textContent || '').trim();
                        }
                        if (target && pName && !pName.toLowerCase().includes(target)) {
                            continue;
                        }
                        b.click();
                        return { clicked: true, name: pName };
                    }
                }
                return { clicked: false, name: '' };
            }""", target_name)

            if page_switch_info and page_switch_info.get("clicked"):
                switched = True
                detected_page_name = page_switch_info.get("name", "")
                await asyncio.sleep(2.5)
        except Exception:
            pass

        if self.context:
            try:
                curr_cookies = await self.context.cookies()
                for c in curr_cookies:
                    if c.get("name") == "i_user":
                        detected_page_id = str(c.get("value", "")).strip()
                        switched = True
                        break
            except Exception:
                pass

        return switched, detected_page_name, detected_page_id
