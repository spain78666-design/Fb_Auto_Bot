#!/usr/bin/env python3
"""
FB Auto Bot - Facebook Automation Suite
automation/cookie_extractor_bot.py - Automated Facebook Session Cookie Extractor Engine

Automates high-speed extraction of fresh Facebook session cookies (c_user, xs, datr, sb, fr)
from UID/Email & Password credentials. Supports:
  1. Silent Background (Headless) or Visible Chrome execution
  2. Automated 2FA TOTP code generation (RFC 6238) if 2FA secret is provided
  3. Direct export to standard semicolon string format (matching 'Get Token Cookie' Chrome extension)
  4. Auto-detection of Facebook profile display name & UID validation
  5. Multi-account concurrency with strict resource cleanup & anti-detection stealth
"""

import os
import sys
import json
import time
import random
import uuid
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

# Import TOTP generator from session_manager if available
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
                the Chrome extension 'Get Token Cookie' (sb, datr, _fbp, c_user, i_user, xs...).
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
    Supports switching into Facebook Page profile ('Use Page') for direct Reels/Page actions.
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
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.uid_or_email = str(uid_or_email).strip()
        self.password = str(password).strip()
        self.two_factor_secret = str(two_factor_secret).strip()
        self.proxy = str(proxy).strip()
        self.headless = headless
        self.timeout_seconds = timeout_seconds
        self.switch_to_page = switch_to_page
        self.page_target = str(page_target).strip()
        self.log_callback = log_callback

        self.playwright: Optional[Playwright] = None
        self.browser = None
        self.context: Optional[BrowserContext] = None
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
        """Cleanly releases browser, context, and Playwright instances."""
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass
        self.context = None

        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        self.browser = None

        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        self.playwright = None

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
          - cookie: str (semicolon string format)
          - status: str ('Success', 'Wrong Password', 'Checkpoint', '2FA Required', 'Timeout', 'Error')
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
        self.log("INFO", f"{tag} 🚀 Initializing Cookie Extractor ({mode_str})...")

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
                "--disk-cache-size=16777216",
                "--media-cache-size=16777216",
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

            # Detect installed Chrome executable on Windows
            chrome_candidates = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ]
            chrome_exe = next((c for c in chrome_candidates if os.path.isfile(c)), None)

            launch_kwargs: Dict[str, Any] = {
                "headless": self.headless,
                "args": launch_args
            }
            if proxy_cfg:
                launch_kwargs["proxy"] = proxy_cfg
            if chrome_exe:
                launch_kwargs["executable_path"] = chrome_exe

            try:
                self.browser = await self.playwright.chromium.launch(**launch_kwargs)
            except Exception:
                launch_kwargs.pop("executable_path", None)
                self.browser = await self.playwright.chromium.launch(**launch_kwargs)

            context_kwargs = {
                "viewport": {"width": 1366, "height": 768},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                "locale": "en-US",
                "timezone_id": "America/New_York",
                "extra_http_headers": {
                    "Accept-Language": "en-US,en;q=0.9",
                    "Sec-Ch-Ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1"
                }
            }
            self.context = await self.browser.new_context(**context_kwargs)
            page = await self.context.new_page()

            # Military-Grade 2027 Anti-Detection Stealth Injection
            try:
                await page.add_init_script("""
                    // 1. Completely eradicate navigator.webdriver and automation traces
                    try {
                        delete Object.getPrototypeOf(navigator).webdriver;
                    } catch (e) {}
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

                    // 2. Realistic hardware & platform signatures
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                    Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
                    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
                    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
                    Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });

                    // 3. Genuine Chrome Plugins array (prevents headless detection)
                    const mockPlugins = [
                        { name: 'PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                        { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                        { name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                        { name: 'Microsoft Edge PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                        { name: 'WebKit built-in PDF', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }
                    ];
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => mockPlugins
                    });

                    // 4. Fully formed window.chrome object (matches genuine Google Chrome)
                    window.chrome = {
                        app: { isInstalled: false, InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }, RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' } },
                        runtime: {
                            OnInstalledReason: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' },
                            OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic', SHARED_MODULE_UPDATE: 'shared_module_update' },
                            PlatformArch: { ARM: 'arm', ARM64: 'arm64', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
                            PlatformNaclArch: { ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
                            PlatformOs: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' },
                            RequestUpdateCheckStatus: { NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' }
                        },
                        loadTimes: function() {
                            return {
                                requestTime: Date.now() / 1000 - 0.2,
                                startLoadTime: Date.now() / 1000 - 0.18,
                                commitLoadTime: Date.now() / 1000 - 0.05,
                                finishDocumentLoadTime: Date.now() / 1000,
                                finishLoadTime: Date.now() / 1000 + 0.05,
                                firstPaintTime: Date.now() / 1000 + 0.02,
                                firstPaintAfterLoadTime: 0,
                                navigationType: 'Other'
                            };
                        },
                        csi: function() {
                            return {
                                startE: Date.now() - 500,
                                onloadT: Date.now(),
                                pageT: 500.2,
                                tran: 15
                            };
                        }
                    };

                    // 5. Spoof WebGL Vendor and Renderer to genuine NVIDIA GPU
                    const getParameterProxy = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(parameter) {
                        if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
                            return 'Google Inc. (NVIDIA)';
                        }
                        if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
                            return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)';
                        }
                        return getParameterProxy.apply(this, arguments);
                    };

                    if (typeof WebGL2RenderingContext !== 'undefined') {
                        const getParameterProxy2 = WebGL2RenderingContext.prototype.getParameter;
                        WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                            if (parameter === 37445) {
                                return 'Google Inc. (NVIDIA)';
                            }
                            if (parameter === 37446) {
                                return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)';
                            }
                            return getParameterProxy2.apply(this, arguments);
                        };
                    }

                    // 6. Clean permissions query
                    const origQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            origQuery(parameters)
                    );

                    // 7. Remove any Playwright / ChromeDriver internal markers
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                    delete window.__playwright;
                    delete window.__pw_manualStatus;
                """)
            except Exception:
                pass

            if PLAYWRIGHT_STEALTH_AVAILABLE:
                try:
                    await stealth_async(page)
                except Exception:
                    pass

            self.log("INFO", f"{tag} 🌐 Navigating to Facebook Portal (Anti-Bot Stealth Active)...")
            try:
                # First navigate to facebook.com to establish genuine datr & sb cookies naturally
                await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=35000)
                await asyncio.sleep(random.uniform(2.0, 3.2))
            except Exception as ge:
                self.log("WARNING", f"{tag} Portal load notice: {str(ge)[:60]}")

            # Check if cookie consent banner is blocking
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
                        await asyncio.sleep(random.uniform(0.6, 1.2))
                        break
            except Exception:
                pass

            if self._cancelled:
                return {"success": False, "uid": self.uid_or_email, "name": "", "cookie": "", "status": "Cancelled", "message": "Operation cancelled."}

            # Humanized typing function with realistic cadence and jitter
            async def _human_type(loc, text_to_type: str):
                await loc.click()
                await asyncio.sleep(random.uniform(0.25, 0.55))
                await loc.fill("")
                for ch in text_to_type:
                    await loc.type(ch, delay=random.randint(35, 95))
                    if random.random() < 0.08:
                        await asyncio.sleep(random.uniform(0.08, 0.22))

            # Fill Email / UID field with human dynamics
            self.log("INFO", f"{tag} ✍️ Entering UID / Login ID (Human Cadence)...")
            email_selectors = [
                'input[name="email"]',
                'input#email',
                'input[type="text"][autocomplete="username"]',
                'input[data-testid="royal_email"]',
                'input[aria-label*="Email" i]',
                'input[placeholder*="Email" i]'
            ]
            email_field = None
            for es in email_selectors:
                el = page.locator(es).first
                if await el.count() > 0 and await el.is_visible():
                    email_field = el
                    break

            if email_field:
                await _human_type(email_field, self.uid_or_email)
            else:
                for ch in self.uid_or_email:
                    await page.keyboard.type(ch, delay=random.randint(40, 90))

            await asyncio.sleep(random.uniform(0.5, 0.9))

            # Fill Password field with human dynamics
            self.log("INFO", f"{tag} 🔑 Entering Password (Human Cadence)...")
            pass_selectors = [
                'input[name="pass"]',
                'input#pass',
                'input[type="password"]',
                'input[data-testid="royal_pass"]',
                'input[aria-label*="Password" i]',
                'input[placeholder*="Password" i]'
            ]
            pass_field = None
            for ps in pass_selectors:
                el = page.locator(ps).first
                if await el.count() > 0 and await el.is_visible():
                    pass_field = el
                    break

            if pass_field:
                await _human_type(pass_field, self.password)
            else:
                for ch in self.password:
                    await page.keyboard.type(ch, delay=random.randint(40, 90))

            # Slight hesitation before clicking submit (mimics genuine human behavior)
            await asyncio.sleep(random.uniform(0.7, 1.4))

            # Click Log In button
            self.log("INFO", f"{tag} ⚡ Submitting login credentials...")
            login_selectors = [
                'button[name="login"]',
                'button#loginbutton',
                'button[data-testid="royal_login_button"]',
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Log In")',
                'button:has-text("Login")'
            ]
            login_clicked = False
            for ls in login_selectors:
                btn = page.locator(ls).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    login_clicked = True
                    break

            if not login_clicked:
                try:
                    login_clicked = await page.evaluate("""() => {
                        const b = document.querySelector('button[name="login"], button#loginbutton, button[type="submit"], input[type="submit"]');
                        if (b) { b.click(); return true; }
                        return false;
                    }""")
                except Exception:
                    pass

            if not login_clicked:
                await page.keyboard.press("Enter")

            # Monitoring loop: look for c_user, xs, 2FA, checkpoint, or wrong password
            self.log("INFO", f"{tag} ⏳ Awaiting Facebook authentication & cookie generation...")
            has_authenticated = False
            error_status = "Timeout"
            error_msg = "Login timed out after waiting."

            start_time = time.time()
            max_wait = self.timeout_seconds

            while time.time() - start_time < max_wait:
                if self._cancelled:
                    return {"success": False, "uid": self.uid_or_email, "name": "", "cookie": "", "status": "Cancelled", "message": "Operation cancelled."}

                await asyncio.sleep(1.2)

                # Check for Checkpoint / Security Check first before declaring Live
                curr_url = page.url.lower()
                page_text = ""
                try:
                    page_text = await page.evaluate("() => (document.body ? document.body.innerText : '').toLowerCase()")
                except Exception:
                    pass

                checkpoint_phrases = [
                    "checkpoint", "confirm your identity", "verify your identity",
                    "we suspended your account", "account has been disabled",
                    "help us confirm", "sua conta foi suspensa", "su cuenta ha sido suspendida",
                    "آپ کا اکاؤنٹ معطل کر دیا گیا ہے", "سیکیورٹی چیک", "confirm that you own this account",
                    "your account has been locked", "account locked", "we noticed unusual activity",
                    "unusual activity", "help us verify it's you", "try entering your password"
                ]
                is_checkpoint_detected = any(p in curr_url for p in ["checkpoint", "suspended", "disabled", "recover", "login/device-based"]) or any(p in page_text for p in checkpoint_phrases)

                # Check cookies
                curr_cookies = await self.context.cookies()
                c_user_val = next((c.get("value") for c in curr_cookies if c.get("name") == "c_user"), None)
                xs_val = next((c.get("value") for c in curr_cookies if c.get("name") == "xs"), None)

                if c_user_val and xs_val and not is_checkpoint_detected:
                    has_authenticated = True
                    self.log("SUCCESS", f"{tag} ✅ Live session detected! c_user={c_user_val}")
                    break

                # Check for Wrong Password indicator
                if "incorrect password" in page_text or "wrong password" in page_text or "the password you entered is incorrect" in page_text:
                    error_status = "Wrong Password"
                    error_msg = "Incorrect Facebook Password."
                    self.log("ERROR", f"{tag} ❌ Wrong password for account.")
                    break

                # Check for Disabled / Suspended account
                if "account disabled" in page_text or "your account has been disabled" in page_text:
                    error_status = "Disabled"
                    error_msg = "Account is disabled by Facebook."
                    self.log("ERROR", f"{tag} 🚫 Facebook account is disabled.")
                    break

                if is_checkpoint_detected:
                    # Check if 2FA code input is present
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
                    else:
                        error_status = "Checkpoint"
                        error_msg = "Account triggered Facebook security checkpoint."
                        self.log("WARNING", f"{tag} 🔒 Account triggered Facebook security checkpoint.")
                        break

                # Handle "Save login info" or "Remember browser" prompts
                try:
                    save_info_selectors = [
                        'button:has-text("Save")',
                        'button:has-text("Save Info")',
                        'button:has-text("Not Now")',
                        'a:has-text("Not Now")',
                        'button:has-text("Continue")'
                    ]
                    for s_sel in save_info_selectors:
                        s_btn = page.locator(s_sel).first
                        if await s_btn.count() > 0 and await s_btn.is_visible():
                            await s_btn.click()
                            await asyncio.sleep(1.0)
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
                is_cp = (error_status == "Checkpoint" or "checkpoint" in error_status.lower())

                if is_cp:
                    self.log("WARNING", f"{tag} 🔒 Checkpoint ID captured ({len(cp_cookies)} cookie tokens). Kept completely separate from Live IDs.")

                return {
                    "success": False,
                    "is_checkpoint": is_cp,
                    "uid": resolved_uid,
                    "name": f"FB Checkpoint ({resolved_uid})" if is_cp else "",
                    "cookie": cp_cookie_str,
                    "cookie_list": cp_cookies,
                    "status": "Checkpoint" if is_cp else error_status,
                    "message": error_msg
                }

            # If switch_to_page is enabled, switch active profile to the Facebook Page ("Use Page")
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
                        self.log("SUCCESS", f"{tag} 🎯 Switched to Facebook Page: '{p_name}' (ID: {p_id})! Extracted cookie will open directly in Page mode.")
                except Exception as sw_ex:
                    self.log("WARNING", f"{tag} Page switch notice: {sw_ex}")

            # Session Warmup & Security Stabilizer Routine (Prevents immediate suspension / checkpoints)
            self.log("INFO", f"{tag} 🛡️ Stabilizing session security trust & warming telemetry...")
            try:
                # Gentle human-like mouse movement and natural scrolling
                await page.mouse.move(random.randint(200, 600), random.randint(200, 500))
                await asyncio.sleep(random.uniform(0.8, 1.4))
                await page.evaluate("window.scrollBy({ top: 280, behavior: 'smooth' })")
                await asyncio.sleep(random.uniform(1.2, 1.8))
                await page.evaluate("window.scrollBy({ top: -140, behavior: 'smooth' })")
                await asyncio.sleep(random.uniform(1.5, 2.2))
            except Exception:
                await asyncio.sleep(2.5)

            # Retrieve final complete cookies
            final_cookies = await self.context.cookies()
            cookie_semicolon = SessionCookieParser.cookies_to_semicolon_string(final_cookies)

            # Detect UID from c_user cookie if available
            c_user_val = next((c.get("value") for c in final_cookies if c.get("name") == "c_user"), "")
            i_user_val = next((c.get("value") for c in final_cookies if c.get("name") == "i_user"), "")
            resolved_uid = c_user_val or self.uid_or_email

            # Detect Facebook Account / Page Display Name
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
            # Final safety verification: ensure page didn't redirect to checkpoint during warmup / navigation
            final_url = page.url.lower()
            if any(p in final_url for p in ["checkpoint", "suspended", "disabled", "recover"]):
                self.log("WARNING", f"{tag} 🔒 Checkpoint verified at end of session. Kept strictly separate from Live IDs.")
                return {
                    "success": False,
                    "is_checkpoint": True,
                    "uid": resolved_uid,
                    "name": f"FB Checkpoint ({resolved_uid})",
                    "cookie": cookie_semicolon,
                    "cookie_list": final_cookies,
                    "status": "Checkpoint",
                    "message": "Account in Facebook checkpoint. Kept separate from Live."
                }

            self.log("INFO", f"{tag} 🍪 Cookie Preview: {cookie_semicolon[:65]}... ({len(final_cookies)} cookie tokens)")

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
        Switches the Facebook session from the personal user profile to an active
        Facebook Page profile ('Use Page' / New Pages Experience).
        Once switched, Facebook sets the 'i_user' cookie to the Page ID.
        """
        tag = f"[{self.uid_or_email}]"
        self.log("INFO", f"{tag} 🔍 Checking Facebook Pages manager to switch into Page profile ('Use Page')...")

        target_name = (self.page_target or "").lower().strip()
        switched = False
        detected_page_name = ""
        detected_page_id = ""

        # Method 1: Navigate to pages dashboard /pages/?category=your_pages
        try:
            await page.goto("https://www.facebook.com/pages/?category=your_pages", wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(2.5)

            # Find switch buttons on /pages/
            page_switch_info = await page.evaluate("""(target) => {
                const buttons = Array.from(document.querySelectorAll('div[role="button"], button, a[role="button"]'));
                const switchWords = ['switch now', 'switch into', 'switch', 'use page', 'mudar agora', 'mudar', 'cambiar ahora', 'cambiar', 'سوئچ کریں'];

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
                self.log("INFO", f"{tag} 👉 Clicked 'Switch now' for Page '{detected_page_name}'...")
                await asyncio.sleep(4.5)
        except Exception as e:
            self.log("DEBUG", f"{tag} Page dashboard notice: {e}")

        # Method 2: Fallback via Top-Right Profile Switcher Menu
        if not switched:
            try:
                self.log("INFO", f"{tag} Trying Top-Right Account Menu profile switcher...")
                await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(2.0)

                avatar_clicked = await page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('div[role="button"], svg'));
                    for (const b of btns) {
                        const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                        if (aria.includes('your profile') || aria.includes('account') || aria.includes('conta') || aria.includes('cuenta')) {
                            const el = b.closest('div[role="button"]') || b;
                            el.click();
                            return true;
                        }
                    }
                    return false;
                }""")

                if avatar_clicked:
                    await asyncio.sleep(1.5)
                    # Click "See all profiles" if visible
                    await page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll('div[role="button"], span'));
                        for (const b of btns) {
                            const txt = (b.innerText || b.textContent || '').toLowerCase();
                            if (txt.includes('see all profiles') || txt.includes('ver todos os perfis') || txt.includes('ver todos los perfiles')) {
                                (b.closest('div[role="button"]') || b).click();
                                return true;
                            }
                        }
                        return false;
                    }""")
                    await asyncio.sleep(1.5)

                    # Click the first Page profile item
                    switched_menu = await page.evaluate("""(target) => {
                        const items = Array.from(document.querySelectorAll('div[role="listitem"], div[role="button"]'));
                        for (const item of items) {
                            if (!item.offsetParent) continue;
                            const aria = (item.getAttribute('aria-label') || '').toLowerCase();
                            const txt = (item.innerText || item.textContent || '').toLowerCase();

                            if (aria.includes('switch to') || aria.includes('switch into') || aria.includes('mudar para') || aria.includes('cambiar a') || txt.includes('switch')) {
                                if (target && !txt.includes(target) && !aria.includes(target)) {
                                    continue;
                                }
                                item.click();
                                const namePart = aria.replace(/switch to|switch into|mudar para|cambiar a/g, '').trim() || txt.split('\\n')[0].trim();
                                return { clicked: true, name: namePart };
                            }
                        }
                        return { clicked: false, name: '' };
                    }""", target_name)

                    if switched_menu and switched_menu.get("clicked"):
                        switched = True
                        detected_page_name = switched_menu.get("name", "")
                        self.log("INFO", f"{tag} 👉 Switched to Page '{detected_page_name}' from Account Menu.")
                        await asyncio.sleep(4.5)
            except Exception as e:
                self.log("DEBUG", f"{tag} Account menu switch notice: {e}")

        # Check for i_user cookie (The Facebook Page ID)
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

        if switched and not detected_page_name:
            try:
                detected_page_name = await page.evaluate("""() => {
                    const h1 = document.querySelector('h1, h2');
                    if (h1 && h1.offsetParent) return h1.innerText.trim();
                    return '';
                }""")
            except Exception:
                pass

        if not detected_page_name and detected_page_id:
            detected_page_name = f"FB Page ({detected_page_id})"

        return switched, detected_page_name, detected_page_id
