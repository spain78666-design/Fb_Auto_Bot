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
        counter_callback: Optional[Callable[[str, int], None]] = None,
        status_callback: Optional[Callable[[str, str], None]] = None
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
        self.status_cb = status_callback

        self.account_id = str(account_data.get("id", "unknown"))
        self.account_name = str(account_data.get("name", "Facebook Account"))

        self.playwright = None
        self.browser = None
        self.context = None
        self._cancelled = False
        self.uploaded_count = 0

        self.rate_limited = False
        self.checkpoint_hit = False
        self.logged_out = False

    def log(self, level: str, message: str):
        full_msg = f"[{self.account_name}] {message}"
        if self.log_cb:
            self.log_cb(level, full_msg)
        else:
            print(f"[{level}] {full_msg}")

    def cancel(self):
        self._cancelled = True
        self.log("WARNING", "🛑 Stop command received. Terminating Reels uploader...")

    async def _check_facebook_rate_limit(self, page: Page) -> Tuple[bool, str]:
        """
        Detects Facebook temporary posting limits / action blocks:
        'We limit how often you can post, comment or do other things in a given amount of time...'
        Returns (is_limit, matched_text_snippet).
        """
        try:
            res = await page.evaluate("""() => {
                const limitPhrases = [
                    'we limit how often you can post',
                    'we limit how often',
                    'protect the community from spam',
                    'you can try again later',
                    'try again later',
                    "you can't use this feature right now",
                    "you can't post right now",
                    "you're temporarily blocked",
                    "you’re temporarily blocked",
                    'temporarily blocked from posting',
                    'action blocked',
                    'you’ve been temporarily blocked',
                    'you've been temporarily blocked',
                    'we added a restriction',
                    'account is restricted',
                    'we restricted your account',
                    'your account is restricted',
                    'limit reached',
                    'going too fast',
                    'misusing this feature',
                    "couldn't be posted",
                    "post couldn't be shared",
                    'something went wrong while posting',
                    'limitamos a frequência com que você pode',
                    'limitamos a frequência',
                    'bloqueado temporariamente',
                    'bloqueada temporariamente',
                    'ação bloqueada',
                    'você não pode publicar agora',
                    'você não pode publicar',
                    'sua conta está restrita',
                    'tente novamente mais tarde',
                    'limitamos la frecuencia con la que puedes',
                    'limitamos la frecuencia',
                    'bloqueado temporalmente',
                    'bloqueada temporalmente',
                    'acción bloqueada',
                    'no puedes publicar en este momento',
                    'no puedes publicar',
                    'tu cuenta está restringida',
                    'inténtalo de nuevo más tarde',
                    'ہم اس کی حد مقرر کرتے ہیں',
                    'عارضی طور پر بلاک',
                    'پوسٹ نہیں کر سکتے'
                ];

                // 1. Scan alert dialogs, warning banners, red error text containers
                const containers = Array.from(document.querySelectorAll('div[role="alert"], div[role="alertdialog"], div[role="dialog"], [class*="alert" i], [class*="error" i], [class*="warning" i], span, p, div'));
                for (const el of containers) {
                    const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                    if (txt.length >= 8 && txt.length <= 800) {
                        for (const ph of limitPhrases) {
                            if (txt.includes(ph)) {
                                return { found: true, snippet: (el.innerText || el.textContent || '').trim().slice(0, 140) };
                            }
                        }
                    }
                }

                // 2. Full document body fallback
                const fullText = (document.body ? document.body.innerText || document.body.textContent || '' : '').toLowerCase();
                for (const ph of limitPhrases) {
                    if (fullText.includes(ph)) {
                        return { found: true, snippet: ph };
                    }
                }
                return { found: false, snippet: '' };
            }""")
            if res and res.get("found"):
                snippet = res.get("snippet", "Facebook posting limit")
                self.rate_limited = True
                return True, snippet
            return False, ""
        except Exception:
            return False, ""

    async def _check_checkpoint_or_suspended(self, page: Page) -> Tuple[bool, str]:
        """
        Detects Facebook Checkpoint, Account Suspension, or Disabled accounts.
        Returns (is_checkpoint, matched_text_snippet).
        """
        try:
            curr_url = page.url.lower()
            checkpoint_url_keywords = [
                "checkpoint", "suspended", "confirmemail", "recover",
                "login_approval", "two_step_verification", "account_disabled",
                "help/contact/"
            ]
            for k in checkpoint_url_keywords:
                if k in curr_url:
                    self.checkpoint_hit = True
                    return True, f"URL keyword: {k}"

            res = await page.evaluate("""() => {
                const phrases = [
                    'account suspended',
                    'account has been disabled',
                    'we suspended your account',
                    'help us confirm that you own this account',
                    'confirm your identity',
                    'enter security code',
                    'login approval needed',
                    'approve your login',
                    'sua conta foi suspensa',
                    'su cuenta ha sido suspendida',
                    'آپ کا اکاؤنٹ معطل کر دیا گیا ہے',
                    'checkpoint'
                ];
                const fullText = (document.body ? document.body.innerText || document.body.textContent || '' : '').toLowerCase();
                for (const phrase of phrases) {
                    if (fullText.includes(phrase)) {
                        return { found: true, snippet: phrase };
                    }
                }
                return { found: false, snippet: '' };
            }""")
            if res and res.get("found"):
                snippet = res.get("snippet", "Account Checkpoint / Suspended")
                self.checkpoint_hit = True
                return True, snippet
            return False, ""
        except Exception:
            return False, ""

    async def _ensure_logged_in(self, page: Page) -> bool:
        """
        Verifies if Facebook session is currently authenticated.
        If logged out, attempts recovery via saved profile 'Continue as' click or credential submit (up to 2 attempts).
        If still not logged in, returns False so the uploader can immediately skip and close browser.
        """
        for attempt in range(1, 3):
            if self._cancelled:
                return False

            try:
                await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=40000)
                await asyncio.sleep(2.5)
            except Exception as e:
                self.log("DEBUG", f"Page load notice: {e}")

            # Check 1: Checkpoint
            is_cp, cp_msg = await self._check_checkpoint_or_suspended(page)
            if is_cp:
                self.checkpoint_hit = True
                clean_uid = "".join(c for c in str(self.account_data.get("uid", "")) if c.isdigit())
                uid_str = f" (UID: {clean_uid})" if clean_uid else ""
                self.log("ERROR", f"⚠️ Facebook Checkpoint or Account Suspension detected for {self.account_name}{uid_str}: {cp_msg}!")
                if self.status_cb:
                    self.status_cb(self.account_id, "checkpoint")
                return False

            # Check 2: Check if logged in via DOM elements and cookies
            is_logged_in = False
            try:
                is_logged_in = await page.evaluate("""() => {
                    const u = window.location.href.toLowerCase();
                    if (u.includes('/login') || u.includes('/checkpoint')) return false;
                    
                    // Look for logged-in UI elements
                    const hasNav = document.querySelector('div[role="navigation"], div[aria-label="Facebook"][role="navigation"], div[aria-label="Account controls and settings"], div[aria-label*="Your profile" i], svg[aria-label="Your profile"]') !== null;
                    const hasMe = document.querySelector('a[href*="/me"], a[href*="profile.php"]') !== null;
                    const hasSearch = document.querySelector('input[placeholder*="Search Facebook" i], input[aria-label*="Search Facebook" i]') !== null;
                    const hasComposer = document.querySelector('div[role="region"][aria-label*="News Feed" i], div[role="main"]') !== null;
                    
                    // If email or password input exists and is visible -> definitely logged out
                    const emailInp = document.querySelector('input[name="email"], input[id="email"]');
                    if (emailInp && emailInp.offsetParent !== null) return false;

                    return hasNav || hasMe || hasSearch || hasComposer;
                }""")
            except Exception:
                is_logged_in = False

            if is_logged_in:
                self.log("SUCCESS", f"✅ Session confirmed LIVE & authenticated for {self.account_name}.")
                return True

            self.log("WARNING", f"⚠️ Account {self.account_name} appears logged out. Attempting login verification (Attempt {attempt}/2)...")

            # Check for 'Continue as' button or saved login card
            try:
                clicked_continue = await page.evaluate("""() => {
                    const buttons = Array.from(document.querySelectorAll('div[role="button"], button, a, div[tabindex="0"]'));
                    for (const b of buttons) {
                        const txt = (b.innerText || b.textContent || b.getAttribute('aria-label') || '').toLowerCase().trim();
                        if (txt.includes('continue as') || txt.includes('continuar como') || txt.includes('iniciar sesión como') || txt.includes('جاری رکھیں')) {
                            if (b.offsetParent !== null) {
                                b.click();
                                return true;
                            }
                        }
                    }
                    // Check for profile account tile on login page
                    const tiles = Array.from(document.querySelectorAll('div[data-testid="login_account_tile"], [role="button"][aria-label*="Log in as" i]'));
                    if (tiles.length > 0 && tiles[0].offsetParent !== null) {
                        tiles[0].click();
                        return true;
                    }
                    return false;
                }""")
                if clicked_continue:
                    self.log("INFO", "👉 Clicked 'Continue as' / saved login profile. Waiting for authorization...")
                    await asyncio.sleep(4.0)
                    is_cp, _ = await self._check_checkpoint_or_suspended(page)
                    if not is_cp:
                        curr = page.url.lower()
                        if "login" not in curr and "checkpoint" not in curr:
                            self.log("SUCCESS", f"✅ Successfully logged in via saved profile for {self.account_name}!")
                            return True
            except Exception:
                pass

            # Check for saved credentials in account_data to auto-fill
            uid = str(self.account_data.get("uid") or self.account_data.get("email") or "")
            pwd = str(self.account_data.get("password") or "")
            if pwd and uid:
                try:
                    email_input = page.locator('input[name="email"], input[id="email"]').first
                    pass_input = page.locator('input[name="pass"], input[id="pass"]').first
                    if await email_input.count() > 0 and await pass_input.count() > 0:
                        self.log("INFO", f"🔑 Submitting saved credentials for {self.account_name}...")
                        await email_input.fill(uid)
                        await pass_input.fill(pwd)
                        await asyncio.sleep(0.5)
                        login_btn = page.locator('button[name="login"], button[type="submit"]').first
                        if await login_btn.count() > 0:
                            await login_btn.click()
                        else:
                            await page.keyboard.press("Enter")
                        await asyncio.sleep(5.0)
                        is_cp, _ = await self._check_checkpoint_or_suspended(page)
                        if not is_cp:
                            curr = page.url.lower()
                            if "login" not in curr and "checkpoint" not in curr:
                                self.log("SUCCESS", f"✅ Successfully logged in via credentials for {self.account_name}!")
                                return True
                except Exception as ex:
                    self.log("DEBUG", f"Credential login attempt notice: {ex}")

            # Re-inject cookies if available
            raw_cookies = self.account_data.get("cookies", "")
            if raw_cookies and self.context:
                try:
                    formatted = parse_cookie_payload(raw_cookies) if isinstance(raw_cookies, str) else raw_cookies
                    if formatted:
                        await self.context.add_cookies(formatted)
                        self.log("INFO", f"🔄 Re-injected {len(formatted)} cookies. Reloading page...")
                        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=35000)
                        await asyncio.sleep(3.0)
                except Exception:
                    pass

        # If still logged out after 2 attempts:
        self.log("ERROR", f"🔒 Facebook account {self.account_name} is NOT logged in (session cookies expired). Skipping immediately.")
        self.logged_out = True
        if self.status_cb:
            self.status_cb(self.account_id, "logged_out")
        return False

    async def _init_browser(self):
        """Initializes stealth Chrome instance with account cookies, anti-fingerprinting, and background throttling prevention."""
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
            "--start-maximized",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disk-cache-size=33554432",
            "--media-cache-size=33554432",
            "--lang=en-US",
            "--accept-lang=en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,es;q=0.6"
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

        context_kwargs = {
            "viewport": None,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "locale": "en-US",
            "extra_http_headers": {
                "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,es;q=0.6"
            }
        }

        profile_dir = self.account_data.get("profile_dir", "")
        if profile_dir and os.path.isdir(profile_dir):
            try:
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=False,
                    args=launch_args,
                    proxy=proxy_cfg,
                    **context_kwargs
                )
            except Exception:
                self.context = await self.browser.new_context(**context_kwargs)
        else:
            self.context = await self.browser.new_context(**context_kwargs)

        # Inject session cookies and force English interface cookie
        raw_cookies = self.account_data.get("cookies", "")
        if self.context:
            try:
                formatted = []
                if raw_cookies:
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

                # Inject locale cookie to request English UI on Facebook
                locale_cookie_found = any(c.get("name") == "locale" for c in formatted)
                if not locale_cookie_found:
                    formatted.append({
                        "name": "locale",
                        "value": "en_US",
                        "domain": ".facebook.com",
                        "path": "/",
                        "secure": True
                    })

                if formatted:
                    await self.context.add_cookies(formatted)
                    self.log("SUCCESS", f"🔑 Injected {len(formatted)} Facebook cookies. Session active.")
            except Exception as e:
                self.log("DEBUG", f"Cookie injection notice: {e}")

    async def _dismiss_popups_and_modals(self, page: Page):
        """
        Detects and automatically dismisses blocking dialogs and popups,
        while strictly checking for Facebook rate limits or account checkpoints.
        """
        # First check if the active dialog is a posting limit
        is_lim, lim_msg = await self._check_facebook_rate_limit(page)
        if is_lim:
            self.rate_limited = True
            self.log("ERROR", f"⛔ Facebook posting limit active on account: '{lim_msg}'!")
            if self.status_cb:
                self.status_cb(self.account_id, "LIMIT", self.uploaded_count)
            return

        is_cp, cp_msg = await self._check_checkpoint_or_suspended(page)
        if is_cp:
            self.checkpoint_hit = True
            self.log("ERROR", f"🔒 Facebook checkpoint / suspension active: '{cp_msg}'!")
            if self.status_cb:
                self.status_cb(self.account_id, "CHECKPOINT", self.uploaded_count)
            return

        try:
            # 1. Native DOM query to locate and click close (X) buttons on any warning/notice overlay
            await page.evaluate("""() => {
                const dialogs = Array.from(document.querySelectorAll('div[role="dialog"], div[aria-modal="true"], div[role="alertdialog"]'));
                for (const d of dialogs) {
                    const txt = (d.innerText || d.textContent || '').toLowerCase();
                    const isWarningPopup = txt.includes('what happened') || 
                                           txt.includes('we removed a post') || 
                                           txt.includes('restriction') || 
                                           txt.includes("can't read files") ||
                                           txt.includes('your photos') ||
                                           txt.includes('community standards') ||
                                           txt.includes('we added a restriction') ||
                                           txt.includes('notice') ||
                                           txt.includes('alert') ||
                                           txt.includes('see why') ||
                                           txt.includes('o que aconteceu') ||
                                           txt.includes('removemos') ||
                                           txt.includes('restrição') ||
                                           txt.includes('restricción') ||
                                           txt.includes('não foi possível') ||
                                           txt.includes('no se pudo') ||
                                           txt.includes('padrões da comunidade') ||
                                           txt.includes('normas comunitarias') ||
                                           txt.includes('aviso') ||
                                           txt.includes('alerta');
                    
                    if (isWarningPopup) {
                        const closeBtns = Array.from(d.querySelectorAll('div[aria-label="Close"], button[aria-label="Close"], div[role="button"][aria-label="Close"], [aria-label="Close"], [aria-label*="Fechar" i], [aria-label*="Cerrar" i], button, div[role="button"]'));
                        for (const cb of closeBtns) {
                            const aria = (cb.getAttribute('aria-label') || '').toLowerCase();
                            const cbTxt = (cb.innerText || cb.textContent || '').toLowerCase().trim();
                            if (aria === 'close' || cbTxt === 'close' || 
                                aria === 'fechar' || cbTxt === 'fechar' || 
                                aria === 'cerrar' || cbTxt === 'cerrar' || 
                                cbTxt === 'ok' || cbTxt === 'got it' || cbTxt === 'entendi' || 
                                cbTxt === 'dismiss' || cbTxt === 'descartar' || 
                                cbTxt === 'not now' || cbTxt === 'agora não' || cbTxt === 'ahora no') {
                                if (cb.offsetParent !== null) {
                                    cb.click();
                                    return true;
                                }
                            }
                        }
                    }
                }
                return false;
            }""")
        except Exception:
            pass

        # 2. Playwright locators for specific dialog close buttons
        try:
            specific_close_selectors = [
                'div[role="dialog"]:has-text("What happened") div[aria-label="Close"]',
                'div[role="dialog"]:has-text("What happened") [role="button"]',
                'div[role="dialog"]:has-text("We removed a post") div[aria-label="Close"]',
                'div[role="dialog"]:has-text("We removed a post") [role="button"]',
                'div[role="dialog"]:has-text("restriction") div[aria-label="Close"]',
                'div[role="dialog"]:has-text("restriction") button',
                "div[role='dialog']:has-text('Can\\'t Read Files') button:has-text('Close')",
                "div[role='dialog']:has-text('Can\\'t Read Files') div[role='button']:has-text('Close')",
                'div[role="dialog"] div[aria-label="Fechar"][role="button"]',
                'div[role="dialog"] div[aria-label="Cerrar"][role="button"]',
                'div[role="dialog"] button:has-text("Fechar")',
                'div[role="dialog"] button:has-text("Cerrar")',
                'div[role="dialog"] button:has-text("Agora não")',
                'div[role="dialog"] button:has-text("Ahora no")'
            ]
            for sel in specific_close_selectors:
                c_btn = page.locator(sel).first
                if await c_btn.count() > 0 and await c_btn.is_visible():
                    await c_btn.click(force=True)
                    await asyncio.sleep(0.5)
        except Exception:
            pass

    async def _open_reels_creator_modal(self, page: Page) -> bool:
        """
        Navigates to the Facebook Reels Creator interface or Profile / Page Reels tab.
        Prioritizes direct creation URL and falls back to profile reels tab.
        """
        clean_uid = "".join(c for c in str(self.account_data.get("uid", "")) if c.isdigit())
        
        # Primary candidate: Direct Reels Creator URL
        try:
            self.log("INFO", "Opening direct Facebook Reels Creator URL (https://www.facebook.com/reels/create)...")
            await page.goto("https://www.facebook.com/reels/create", wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(3.0)

            # Check if login or checkpoint
            curr = page.url.lower()
            if "login" in curr or "checkpoint" in curr:
                self.log("ERROR", "❌ Account session expired or requires login.")
                return False

            # Check if creator loaded directly
            file_inp = page.locator('input[type="file"]').first
            has_dialog = page.locator('div[role="dialog"]').first
            has_add_video = page.locator('div[role="button"]:has-text("Add video"), button:has-text("Add video"), div[role="button"]:has-text("Select video")').first
            
            if (await file_inp.count() > 0) or (await has_add_video.count() > 0 and await has_add_video.is_visible()) or (await has_dialog.count() > 0):
                self.log("SUCCESS", "✅ Direct Facebook Reels Creator interface ready.")
                return True
        except Exception as e:
            self.log("DEBUG", f"Direct creator URL notice: {e}")

        # Fallback candidate URLs
        fallback_urls = []
        if clean_uid:
            fallback_urls.append(f"https://www.facebook.com/profile.php?id={clean_uid}&sk=reels_tab")
            fallback_urls.append(f"https://www.facebook.com/profile.php?id={clean_uid}")
        fallback_urls.append("https://www.facebook.com/me?sk=reels_tab")
        fallback_urls.append("https://www.facebook.com/me")
        fallback_urls.append("https://www.facebook.com/")

        for url in fallback_urls:
            if self._cancelled:
                return False
            try:
                self.log("INFO", f"Navigating to fallback profile/reels URL: {url} ...")
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
                    'div[aria-label="Reel"][role="button"]',
                    'div[aria-label="Create reel"][role="button"]'
                ]

                modal_opened = False
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
                    return True

                # DOM querySelector fallback
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
                        self.log("INFO", "👉 Clicked 'Create reel' via DOM.")
                        await asyncio.sleep(3.0)
                        return True
                except Exception:
                    pass

            except Exception as ex:
                self.log("WARNING", f"Navigation notice for {url}: {ex}")

        # Final check if file input is available
        file_input_count = await page.locator('input[type="file"]').count()
        return file_input_count > 0

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
        Executes the Facebook Reels workflow with full multilingual resilience:
        1. Navigates to direct Reels Creator or Profile/Page Reels tab (sk=reels_tab)
        2. Clicks 'Create reel' button (multilingual: EN, PT, ES, UR)
        3. Attaches video file directly via file input or dropzone FileChooser
        4. Multilingual adaptive flow: Next -> Next -> Enter caption & hashtags -> Click Post/Publish
        5. Waits for Facebook post processing confirmation and verifies submission
        """
        file_name = os.path.basename(video_path)
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        self.log("INFO", f"🎬 [Reel #{reel_index}/{total_reels}] Opening Reels Creator for: {file_name} ({file_size_mb:.1f} MB)...")

        if self._cancelled or self.rate_limited or self.checkpoint_hit:
            return False

        # Step 0: Try direct Creator URL first
        creator_ready = False
        try:
            self.log("INFO", f"[Reel #{reel_index}] Trying direct Reels Creator (https://www.facebook.com/reels/create)...")
            await page.goto("https://www.facebook.com/reels/create", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(2.5)

            is_cp, cp_msg = await self._check_checkpoint_or_suspended(page)
            if is_cp:
                self.checkpoint_hit = True
                self.log("ERROR", f"[Reel #{reel_index}] 🔒 Account session checkpoint or expired: {cp_msg}")
                if self.status_cb:
                    self.status_cb(self.account_id, "CHECKPOINT", self.uploaded_count)
                return False

            is_lim, lim_msg = await self._check_facebook_rate_limit(page)
            if is_lim:
                self.rate_limited = True
                self.log("ERROR", f"[Reel #{reel_index}] ⛔ Facebook posting limit active: {lim_msg}")
                if self.status_cb:
                    self.status_cb(self.account_id, "LIMIT", self.uploaded_count)
                return False

            curr = page.url.lower()
            if "login" in curr or "checkpoint" in curr:
                self.checkpoint_hit = True
                self.log("ERROR", f"[Reel #{reel_index}] ❌ Account session expired.")
                return False

            await self._dismiss_popups_and_modals(page)

            # Check if file input or upload dropzone is already on screen
            has_input = await page.locator('input[type="file"]').count() > 0
            has_dropzone = await page.locator('div[role="button"]:has-text("Add video"), div[role="button"]:has-text("Adicionar"), div[role="button"]:has-text("Agregar"), div[role="button"]:has-text("drag and drop")').count() > 0
            if has_input or has_dropzone:
                creator_ready = True
                self.log("SUCCESS", f"[Reel #{reel_index}] ✅ Direct Facebook Reels Creator loaded successfully.")
        except Exception as ex:
            self.log("DEBUG", f"[Reel #{reel_index}] Direct creator notice: {ex}")

        # If direct creator not ready, navigate to profile / page reels tab
        if not creator_ready:
            clean_uid = "".join(c for c in str(self.account_data.get("uid", "")) if c.isdigit())
            target_url = base_reels_url
            if not target_url:
                if clean_uid:
                    target_url = f"https://www.facebook.com/profile.php?id={clean_uid}&sk=reels_tab"
                else:
                    target_url = "https://www.facebook.com/me?sk=reels_tab"

            self.log("INFO", f"[Reel #{reel_index}] Navigating to fallback Reels Tab: {target_url} ...")
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(2.5)
            except Exception as ex:
                self.log("WARNING", f"[Reel #{reel_index}] Navigation notice: {ex}")

            is_cp, cp_msg = await self._check_checkpoint_or_suspended(page)
            if is_cp:
                self.checkpoint_hit = True
                self.log("ERROR", f"[Reel #{reel_index}] 🔒 Account checkpoint / suspension detected: {cp_msg}")
                if self.status_cb:
                    self.status_cb(self.account_id, "CHECKPOINT", self.uploaded_count)
                return False

            is_lim, lim_msg = await self._check_facebook_rate_limit(page)
            if is_lim:
                self.rate_limited = True
                self.log("ERROR", f"[Reel #{reel_index}] ⛔ Facebook posting limit detected: {lim_msg}")
                if self.status_cb:
                    self.status_cb(self.account_id, "LIMIT", self.uploaded_count)
                return False

            curr = page.url.lower()
            if "login" in curr or "checkpoint" in curr:
                self.checkpoint_hit = True
                self.log("ERROR", f"[Reel #{reel_index}] ❌ Account session expired.")
                return False

            await self._dismiss_popups_and_modals(page)

            # Step 1: Look for 'Create reel' button (Multilingual: EN, PT, ES, UR)
            self.log("INFO", f"[Reel #{reel_index}] 👉 Looking for 'Create reel' button on Reels tab...")
            create_reel_btn_selectors = [
                # English
                'div[role="button"]:has-text("Create reel")',
                'div[role="button"]:has-text("Create Reel")',
                'button:has-text("Create reel")',
                'button:has-text("Create Reel")',
                'a:has-text("Create reel")',
                'span:has-text("Create reel")',
                'div[aria-label*="Create reel" i][role="button"]',
                'div[aria-label*="Create a reel" i][role="button"]',
                # Portuguese / Brazilian
                'div[role="button"]:has-text("Criar reel")',
                'div[role="button"]:has-text("Criar Reel")',
                'button:has-text("Criar reel")',
                'button:has-text("Criar Reel")',
                'a:has-text("Criar reel")',
                'span:has-text("Criar reel")',
                'div[aria-label*="Criar reel" i][role="button"]',
                'div[aria-label*="Criar um reel" i][role="button"]',
                # Spanish
                'div[role="button"]:has-text("Crear reel")',
                'div[role="button"]:has-text("Crear Reel")',
                'button:has-text("Crear reel")',
                'button:has-text("Crear Reel")',
                'a:has-text("Crear reel")',
                'span:has-text("Crear reel")',
                'div[aria-label*="Crear reel" i][role="button"]',
                'div[aria-label*="Crear un reel" i][role="button"]',
                # Urdu
                'div[role="button"]:has-text("ریل بنائیں")',
                'span:has-text("ریل بنائیں")',
                # Generic
                'div[aria-label="Reel"][role="button"]'
            ]

            modal_opened = False
            for cr_sel in create_reel_btn_selectors:
                try:
                    cr_btn = page.locator(cr_sel).first
                    if await cr_btn.count() > 0 and await cr_btn.is_visible():
                        self.log("INFO", f"[Reel #{reel_index}] 👉 Clicking 'Create reel' button...")
                        await cr_btn.click()
                        await asyncio.sleep(2.5)
                        modal_opened = True
                        break
                except Exception:
                    pass

            if not modal_opened:
                # Fallback DOM query for Create Reel across languages
                try:
                    clicked_dom = await page.evaluate("""() => {
                        const buttons = Array.from(document.querySelectorAll('div[role="button"], button, a, span'));
                        const phrases = ['create reel', 'create a reel', 'criar reel', 'criar um reel', 'crear reel', 'crear un reel', 'ریل بنائیں'];
                        for (const b of buttons) {
                            const txt = (b.innerText || b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase();
                            if (phrases.some(p => txt === p || txt.includes(p))) {
                                if (b.offsetParent !== null) {
                                    b.click();
                                    return true;
                                }
                            }
                        }
                        return false;
                    }""")
                    if clicked_dom:
                        self.log("INFO", f"[Reel #{reel_index}] 👉 Clicked 'Create reel' via DOM.")
                        await asyncio.sleep(2.5)
                        modal_opened = True
                except Exception:
                    pass

        await self._dismiss_popups_and_modals(page)

        # Step 2: Attach video file directly via file input or dropzone FileChooser
        self.log("INFO", f"[Reel #{reel_index}] 📤 Attaching video file: {file_name} ...")
        file_attached = False

        for attempt in range(25):
            if self._cancelled:
                return False

            await self._dismiss_popups_and_modals(page)

            # Method A: Direct file input (Fastest & most reliable across all languages)
            try:
                file_inputs = page.locator('input[type="file"]')
                f_count = await file_inputs.count()
                if f_count > 0:
                    for fi in range(f_count):
                        f_inp = file_inputs.nth(fi)
                        try:
                            await f_inp.set_input_files(video_path)
                            file_attached = True
                            self.log("SUCCESS", f"[Reel #{reel_index}] ✅ Video file attached via direct input #{fi+1}: {file_name}")
                            break
                        except Exception:
                            pass
                if file_attached:
                    break
            except Exception:
                pass

            # Method B: Click dropzone button via expect_file_chooser (Multilingual)
            if not file_attached:
                try:
                    upload_btn_selectors = [
                        # English
                        'div[role="dialog"] div[role="button"]:has-text("Add video")',
                        'div[role="dialog"] button:has-text("Add video")',
                        'div[role="dialog"] div[role="button"]:has-text("drag and drop")',
                        'div[role="dialog"] div[role="button"]:has-text("Select video")',
                        'div[role="dialog"] div[role="button"]:has-text("Upload")',
                        'div[role="dialog"] button:has-text("Upload")',
                        # Portuguese
                        'div[role="dialog"] div[role="button"]:has-text("Adicionar vídeo")',
                        'div[role="dialog"] div[role="button"]:has-text("Adicionar video")',
                        'div[role="dialog"] button:has-text("Adicionar vídeo")',
                        'div[role="dialog"] div[role="button"]:has-text("Selecionar vídeo")',
                        'div[role="dialog"] div[role="button"]:has-text("arrastar e soltar")',
                        'div[role="dialog"] div[role="button"]:has-text("Carregar")',
                        # Spanish
                        'div[role="dialog"] div[role="button"]:has-text("Agregar video")',
                        'div[role="dialog"] button:has-text("Agregar video")',
                        'div[role="dialog"] div[role="button"]:has-text("Añadir video")',
                        'div[role="dialog"] div[role="button"]:has-text("Seleccionar video")',
                        'div[role="dialog"] div[role="button"]:has-text("arrastrar y soltar")',
                        'div[role="dialog"] div[role="button"]:has-text("Subir")',
                        # Generic / Page-level
                        'div[role="button"]:has-text("Add video")',
                        'button:has-text("Add video")',
                        'div[role="button"]:has-text("Adicionar vídeo")',
                        'div[role="button"]:has-text("Agregar video")'
                    ]
                    for u_sel in upload_btn_selectors:
                        u_btn = page.locator(u_sel).first
                        if await u_btn.count() > 0 and await u_btn.is_visible():
                            try:
                                async with page.expect_file_chooser(timeout=4000) as fc_info:
                                    await u_btn.click()
                                file_chooser = await fc_info.value
                                await file_chooser.set_files(video_path)
                                file_attached = True
                                self.log("SUCCESS", f"[Reel #{reel_index}] ✅ Video file attached via FileChooser: {file_name}")
                                break
                            except Exception:
                                pass
                    if file_attached:
                        break
                except Exception:
                    pass

            await asyncio.sleep(1.5)

        if not file_attached:
            self.log("ERROR", f"[Reel #{reel_index}] ❌ Could not attach video file for {file_name}.")
            return False

        # Step 3: Adaptive Multilingual Publisher Loop (Caption -> Next -> Next -> Post)
        self.log("INFO", f"[Reel #{reel_index}] 🔄 Video attached! Processing video, caption & post submission...")

        caption_selectors = [
            # English
            'div[role="dialog"] div[aria-label*="Describe your reel" i][role="textbox"]',
            'div[role="dialog"] div[aria-label*="Describe your reel" i]',
            'div[aria-label*="Describe your reel" i][role="textbox"]',
            'div[aria-label*="Describe your reel" i]',
            'div[role="dialog"] div[aria-label*="Write a description" i][role="textbox"]',
            'div[aria-label*="Write a description" i][role="textbox"]',
            'div[role="dialog"] div[aria-label*="Description" i][role="textbox"]',
            'div[aria-label*="Description" i][role="textbox"]',
            # Portuguese
            'div[role="dialog"] div[aria-label*="Descreva seu reel" i][role="textbox"]',
            'div[aria-label*="Descreva seu reel" i]',
            'div[role="dialog"] div[aria-label*="Escreva uma descrição" i]',
            'div[aria-label*="Descrição" i][role="textbox"]',
            'div[aria-label*="Legenda" i][role="textbox"]',
            # Spanish
            'div[role="dialog"] div[aria-label*="Describe tu reel" i][role="textbox"]',
            'div[aria-label*="Describe tu reel" i]',
            'div[role="dialog"] div[aria-label*="Escribe una descripción" i]',
            'div[aria-label*="Descripción" i][role="textbox"]',
            # Generic
            'div[role="dialog"] div[role="textbox"][contenteditable="true"]',
            'div[role="textbox"][contenteditable="true"]',
            'div[role="dialog"] div[contenteditable="true"]',
            'div[contenteditable="true"]',
            'div[role="dialog"] textarea',
            'textarea[placeholder*="Describe your reel" i]',
            'textarea'
        ]

        next_selectors = [
            # English
            'div[role="dialog"] div[aria-label="Next"][role="button"]',
            'div[role="dialog"] button:has-text("Next")',
            'div[role="dialog"] div[role="button"]:has-text("Next")',
            'div[role="dialog"] span:has-text("Next")',
            'button:has-text("Next")',
            'div[role="button"]:has-text("Next")',
            # Portuguese
            'div[role="dialog"] div[aria-label="Avançar"][role="button"]',
            'div[role="dialog"] button:has-text("Avançar")',
            'div[role="dialog"] div[role="button"]:has-text("Avançar")',
            'div[role="dialog"] span:has-text("Avançar")',
            'button:has-text("Avançar")',
            'div[role="button"]:has-text("Avançar")',
            'div[role="dialog"] button:has-text("Seguinte")',
            'div[role="dialog"] div[role="button"]:has-text("Seguinte")',
            'div[role="dialog"] button:has-text("Próximo")',
            'div[role="dialog"] div[role="button"]:has-text("Próximo")',
            # Spanish
            'div[role="dialog"] div[aria-label="Siguiente"][role="button"]',
            'div[role="dialog"] button:has-text("Siguiente")',
            'div[role="dialog"] div[role="button"]:has-text("Siguiente")',
            'div[role="dialog"] span:has-text("Siguiente")',
            'button:has-text("Siguiente")',
            'div[role="button"]:has-text("Siguiente")',
            # Urdu
            'button:has-text("اگلا")',
            'div[role="button"]:has-text("اگلا")'
        ]

        strict_post_selectors = [
            # English
            'div[aria-label="Post"][role="button"]',
            'div[role="button"]:has-text("Post")',
            'button:has-text("Post")',
            'div[aria-label="Publish"][role="button"]',
            'button:has-text("Publish")',
            'div[role="dialog"] div[aria-label="Post"][role="button"]',
            'div[role="dialog"] button:has-text("Post")',
            'div[role="dialog"] div[role="button"]:has-text("Post")',
            'div[role="dialog"] div[aria-label="Publish"][role="button"]',
            'div[role="dialog"] button:has-text("Publish")',
            # Portuguese
            'div[role="dialog"] div[aria-label="Publicar"][role="button"]',
            'div[role="dialog"] button:has-text("Publicar")',
            'div[role="dialog"] div[role="button"]:has-text("Publicar")',
            'div[role="dialog"] button:has-text("Compartilhar")',
            'div[role="dialog"] button:has-text("Postar")',
            'button:has-text("Publicar")',
            'div[role="button"]:has-text("Publicar")',
            # Spanish
            'div[role="dialog"] div[aria-label="Publicar"][role="button"]',
            'div[role="dialog"] button:has-text("Publicar")',
            'div[role="dialog"] div[role="button"]:has-text("Publicar")',
            'div[role="dialog"] button:has-text("Compartir")',
            # Urdu
            'button:has-text("پوسٹ")',
            'div[role="button"]:has-text("پوسٹ")',
            'button:has-text("پوسٹ کریں")',
            'div[role="button"]:has-text("پوسٹ کریں")'
        ]

        caption_entered = False
        published = False

        for loop_tick in range(60):
            if self._cancelled:
                return False

            await self._dismiss_popups_and_modals(page)

            # 1. Check if Caption can be typed
            if not caption_entered:
                for sel in caption_selectors:
                    try:
                        box = page.locator(sel).first
                        if await box.count() > 0 and await box.is_visible():
                            await box.click()
                            await asyncio.sleep(0.3)
                            await page.keyboard.press("Control+A")
                            await page.keyboard.press("Backspace")
                            await asyncio.sleep(0.2)
                            await page.keyboard.type(caption, delay=15)
                            caption_entered = True
                            self.log("SUCCESS", f"[Reel #{reel_index}] ✅ Caption & hashtags entered: '{caption[:35]}...'")

                            # Dismiss hashtag suggestions popup
                            await page.keyboard.press("Escape")
                            await asyncio.sleep(0.2)
                            await page.keyboard.press("Escape")
                            break
                    except Exception:
                        pass

                if not caption_entered:
                    try:
                        caption_entered = await page.evaluate("""(txt) => {
                            const boxes = Array.from(document.querySelectorAll('div[aria-label*="Describe" i], div[aria-label*="Descreva" i], div[aria-label*="Describe tu" i], div[contenteditable="true"], textarea, div[role="textbox"]'));
                            for (const b of boxes) {
                                if (b.offsetParent !== null && b.getBoundingClientRect().height > 20) {
                                    b.focus();
                                    document.execCommand('selectAll', false, null);
                                    document.execCommand('insertText', false, txt);
                                    return true;
                                }
                            }
                            return false;
                        }""", caption)
                        if caption_entered:
                            self.log("SUCCESS", f"[Reel #{reel_index}] ✅ Caption entered via DOM helper.")
                            await page.keyboard.press("Escape")
                    except Exception:
                        pass

            # 2. Check if primary 'Post' / 'Publish' / 'Publicar' button is active and ready
            has_post_ready = False
            try:
                has_post_ready = await page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('div[role="button"], button, span[role="button"], [role="button"]'));
                    const postKeywords = ['post', 'publish', 'publicar', 'compartilhar', 'postar', 'compartir', 'پوسٹ', 'پوسٹ کریں', 'شائع کریں'];
                    
                    for (const b of btns) {
                        if (!b.offsetParent) continue;
                        const label = (b.getAttribute('aria-label') || '').trim().toLowerCase();
                        const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                        
                        if (txt.includes('group') || label.includes('group') ||
                            txt.includes('grupo') || label.includes('grupo') ||
                            txt.includes('share to') || label.includes('share to') ||
                            txt.includes('remix') || label.includes('remix') ||
                            txt.includes('boost') || label.includes('boost') ||
                            txt.includes('turbinar') || label.includes('turbinar') ||
                            txt.includes('schedule') || label.includes('schedule') ||
                            txt.includes('programar') || label.includes('programar') ||
                            txt.includes('star') || txt.includes('earn')) {
                            continue;
                        }
                        
                        if (postKeywords.some(w => txt === w || label === w)) {
                            const dis = b.getAttribute('aria-disabled');
                            if (dis !== 'true' && !b.disabled) {
                                return true;
                            }
                        }
                    }
                    return false;
                }""")
            except Exception:
                pass

            # 3. If Post is ready AND caption is entered -> CLICK POST!
            if has_post_ready and caption_entered:
                self.log("INFO", f"[Reel #{reel_index}] 🚀 Post button is active! Clicking Post on Reel #{reel_index} ({file_name})...")
                try:
                    published = await page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll('div[role="button"], button, span[role="button"], [role="button"]'));
                        const postKeywords = ['post', 'publish', 'publicar', 'compartilhar', 'postar', 'compartir', 'پوسٹ', 'پوسٹ کریں', 'شائع کریں'];
                        
                        for (const b of btns) {
                            if (!b.offsetParent) continue;
                            const label = (b.getAttribute('aria-label') || '').trim().toLowerCase();
                            const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                            
                            if (txt.includes('group') || label.includes('group') ||
                                txt.includes('grupo') || label.includes('grupo') ||
                                txt.includes('share to') || label.includes('share to') ||
                                txt.includes('remix') || label.includes('remix') ||
                                txt.includes('boost') || label.includes('boost') ||
                                txt.includes('turbinar') || label.includes('turbinar') ||
                                txt.includes('schedule') || label.includes('schedule') ||
                                txt.includes('programar') || label.includes('programar') ||
                                txt.includes('star') || txt.includes('earn')) {
                                continue;
                            }
                            
                            if (postKeywords.some(w => txt === w || label === w)) {
                                const dis = b.getAttribute('aria-disabled');
                                if (dis !== 'true' && !b.disabled) {
                                    b.scrollIntoView({ block: 'center', inline: 'center' });
                                    b.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
                                    b.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
                                    b.click();
                                    return true;
                                }
                            }
                        }
                        return false;
                    }""")
                    if published:
                        self.log("SUCCESS", f"[Reel #{reel_index}] 🎉 Clicked Post on Reel #{reel_index} ({file_name})!")
                        break
                except Exception:
                    pass

                # Playwright fallback click
                if not published:
                    for p_sel in strict_post_selectors:
                        try:
                            p_btn = page.locator(p_sel).last
                            if await p_btn.count() > 0 and await p_btn.is_visible():
                                p_txt = (await p_btn.inner_text() or "").strip().lower()
                                p_aria = (await p_btn.get_attribute("aria-label") or "").strip().lower()
                                if "group" not in p_txt and "grupo" not in p_txt and "share to" not in p_txt:
                                    if await p_btn.get_attribute("aria-disabled") != "true":
                                        await p_btn.scroll_into_view_if_needed()
                                        await p_btn.click(force=True)
                                        published = True
                                        self.log("SUCCESS", f"[Reel #{reel_index}] 🎉 Clicked Post via Locator on Reel #{reel_index}!")
                                        break
                        except Exception:
                            pass
                    if published:
                        break

            # 4. If Post is not ready yet, click 'Next' (Avançar / Siguiente)
            if not has_post_ready or not caption_entered:
                for sel in next_selectors:
                    try:
                        n_btn = page.locator(sel).first
                        if await n_btn.count() > 0 and await n_btn.is_visible():
                            if await n_btn.get_attribute("aria-disabled") != "true":
                                await n_btn.click()
                                self.log("INFO", f"[Reel #{reel_index}] 👉 Clicked 'Next' / 'Avançar' step.")
                                await asyncio.sleep(2.0)
                                break
                    except Exception:
                        pass

                # DOM query fallback for Next
                try:
                    clicked_next_dom = await page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll('div[role="button"], button, span[role="button"]'));
                        const nextWords = ['next', 'avançar', 'avancar', 'seguinte', 'próximo', 'proximo', 'siguiente', 'avanzar', 'اگلا'];
                        for (const b of btns) {
                            if (!b.offsetParent) continue;
                            const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                            const aria = (b.getAttribute('aria-label') || '').trim().toLowerCase();
                            if (nextWords.some(w => txt === w || aria === w)) {
                                const dis = b.getAttribute('aria-disabled');
                                if (dis !== 'true' && !b.disabled) {
                                    b.click();
                                    return true;
                                }
                            }
                        }
                        return false;
                    }""")
                    if clicked_next_dom:
                        self.log("INFO", f"[Reel #{reel_index}] 👉 Clicked 'Next' step via DOM helper.")
                        await asyncio.sleep(2.0)
                except Exception:
                    pass

            await asyncio.sleep(1.5)

        if published:
            self.log("INFO", f"[Reel #{reel_index}] ⏳ Post submitted! Checking for Facebook server response and posting status...")
            await asyncio.sleep(3.0)

            # Check immediately if Facebook showed a rate limit / action block dialog!
            is_lim, lim_msg = await self._check_facebook_rate_limit(page)
            if is_lim:
                self.rate_limited = True
                self.log("ERROR", f"⛔ [POST BLOCKED BY FACEBOOK LIMIT] Account {self.account_name} hit posting limit upon clicking Post: '{lim_msg}'. Skipping account!")
                if self.status_cb:
                    self.status_cb(self.account_id, "LIMIT", self.uploaded_count)
                return False

            # Check if Facebook redirected to checkpoint
            is_cp, cp_msg = await self._check_checkpoint_or_suspended(page)
            if is_cp:
                self.checkpoint_hit = True
                self.log("ERROR", f"🔒 [CHECKPOINT DETECTED] Account {self.account_name} triggered checkpoint upon posting: '{cp_msg}'. Skipping account!")
                if self.status_cb:
                    self.status_cb(self.account_id, "CHECKPOINT", self.uploaded_count)
                return False

            # Wait remaining seconds for upload processing
            await asyncio.sleep(4.0)

            # Secondary verification
            is_lim, lim_msg = await self._check_facebook_rate_limit(page)
            if is_lim:
                self.rate_limited = True
                self.log("ERROR", f"⛔ [POST BLOCKED BY FACEBOOK LIMIT] Facebook confirmed rate limit: '{lim_msg}'. Skipping account!")
                if self.status_cb:
                    self.status_cb(self.account_id, "LIMIT", self.uploaded_count)
                return False

            return True
        else:
            self.log("ERROR", f"[Reel #{reel_index}] ❌ Could not click Post button for {file_name}.")
            # Check if Post button was blocked by an active limit
            is_lim, lim_msg = await self._check_facebook_rate_limit(page)
            if is_lim:
                self.rate_limited = True
                self.log("ERROR", f"⛔ [POSTING LIMIT DETECTED] Reel #{reel_index} blocked by limit: '{lim_msg}'!")
                if self.status_cb:
                    self.status_cb(self.account_id, "LIMIT", self.uploaded_count)
            return False

    async def close(self):
        """Gracefully closes all open pages, browser contexts, and the Playwright engine."""
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
            import gc
            gc.collect()
        except Exception:
            pass

    async def run(self) -> Dict[str, Any]:
        """
        Executes bulk Reels upload for this account:
        1. Selects videos according to mode (Random / Sequential / Loop)
        2. Opens Chrome with anti-throttling flags and session cookies
        3. Uploads each reel sequentially with intelligent per-reel retries and delay cooldowns
        4. Cleanly closes Chrome when all reels are completed
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
            f"🚀 Starting Auto Reels Upload: {len(assigned_videos)} Reel(s) assigned for {self.account_name}..."
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

            # Check if account is in Checkpoint / Suspended
            is_cp, cp_msg = await self._check_checkpoint_or_suspended(main_page)
            if is_cp:
                self.checkpoint_hit = True
                self.log("ERROR", f"🔒 [CHECKPOINT DETECTED] Facebook checkpoint or suspension on startup: {cp_msg}. Skipping account immediately!")
                if self.status_cb:
                    self.status_cb(self.account_id, "CHECKPOINT", 0)
                return {"success": False, "status": "CHECKPOINT", "count": 0, "message": f"Checkpoint detected: {cp_msg}"}

            # Check if account has an active rate limit
            is_lim, lim_msg = await self._check_facebook_rate_limit(main_page)
            if is_lim:
                self.rate_limited = True
                self.log("WARNING", f"⛔ [POSTING LIMIT ACTIVE] Facebook posting limit active on startup: {lim_msg}. Skipping account immediately!")
                if self.status_cb:
                    self.status_cb(self.account_id, "LIMIT", 0)
                return {"success": False, "status": "LIMIT", "count": 0, "message": f"Rate limit detected: {lim_msg}"}

            curr_url = main_page.url.lower()
            if "login" in curr_url or "checkpoint" in curr_url:
                self.checkpoint_hit = True
                self.log("ERROR", "❌ Facebook account session expired. Please update cookies or login.")
                if self.status_cb:
                    self.status_cb(self.account_id, "CHECKPOINT", 0)
                return {"success": False, "status": "CHECKPOINT", "count": 0, "message": "Session expired"}

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

            # Paced Sequential Reel Execution with cooldown delay
            for idx, v_path in enumerate(assigned_videos):
                if self._cancelled:
                    self.log("WARNING", "Upload cancelled by user.")
                    break
                if self.rate_limited or self.checkpoint_hit:
                    self.log("WARNING", f"⛔ Halting reels upload on {self.account_name} due to limit/checkpoint. Skipping remaining {total_reels - idx} reel(s).")
                    break

                tab_idx = idx + 1
                caption_text = resolve_spintax(self.caption_template)
                tab_page = await self.context.new_page()
                uploaded_this_reel = False

                try:
                    for reel_attempt in range(1, 3):
                        if self._cancelled or self.rate_limited or self.checkpoint_hit:
                            break
                        if reel_attempt > 1:
                            self.log("INFO", f"[Reel #{tab_idx}] 🔄 Retrying Reel #{tab_idx} upload (Attempt {reel_attempt}/2)...")
                            await asyncio.sleep(3.0)

                        ok = await self._upload_single_reel_tab(
                            page=tab_page,
                            video_path=v_path,
                            caption=caption_text,
                            reel_index=tab_idx,
                            total_reels=total_reels,
                            base_reels_url=base_reels_url
                        )
                        if self.rate_limited or self.checkpoint_hit:
                            break

                        if ok:
                            uploaded_this_reel = True
                            self.uploaded_count += 1
                            self.log("SUCCESS", f"✨ Reel #{tab_idx} ({os.path.basename(v_path)}) successfully uploaded & posted!")
                            if self.counter_cb:
                                self.counter_cb(self.account_id, self.uploaded_count)
                            if self.status_cb:
                                self.status_cb(self.account_id, "UPLOADED", self.uploaded_count)
                            break
                        else:
                            self.log("WARNING", f"⚠️ Reel #{tab_idx} attempt {reel_attempt} was incomplete.")
                except Exception as ex:
                    self.log("ERROR", f"[Reel #{tab_idx}] Error: {str(ex)}")
                finally:
                    try:
                        await tab_page.close()
                    except Exception:
                        pass

                # If rate limited or checkpoint occurred on this reel, break out of all remaining reels immediately!
                if self.rate_limited:
                    self.log("WARNING", f"⛔ Facebook posting limit hit on Reel #{tab_idx}. Stopping remaining reels for {self.account_name} immediately!")
                    if self.status_cb:
                        self.status_cb(self.account_id, "LIMIT", self.uploaded_count)
                    break
                if self.checkpoint_hit:
                    self.log("ERROR", f"🔒 Facebook checkpoint hit on Reel #{tab_idx}. Stopping remaining reels for {self.account_name} immediately!")
                    if self.status_cb:
                        self.status_cb(self.account_id, "CHECKPOINT", self.uploaded_count)
                    break

                # Delay cooldown between consecutive reels on the same account
                if idx < total_reels - 1 and not self._cancelled:
                    cooldown = max(2.0, self.delay_seconds)
                    self.log("INFO", f"⏳ Cooldown delay of {cooldown:.1f}s before uploading next reel to {self.account_name}...")
                    await asyncio.sleep(cooldown)

            final_status = "COMPLETED"
            if self.rate_limited:
                final_status = "LIMIT"
            elif self.checkpoint_hit:
                final_status = "CHECKPOINT"
            elif self.uploaded_count == 0 and total_reels > 0:
                final_status = "FAILED"

            if final_status == "LIMIT":
                self.log("WARNING", f"⛔ Account {self.account_name} stopped due to Facebook Limit. Total uploaded: {self.uploaded_count}/{total_reels}.")
            elif final_status == "CHECKPOINT":
                self.log("ERROR", f"🔒 Account {self.account_name} stopped due to Checkpoint. Total uploaded: {self.uploaded_count}/{total_reels}.")
            else:
                self.log("SUCCESS", f"🎉 Finished all reels for {self.account_name}! Total successfully uploaded: {self.uploaded_count}/{total_reels}.")

            return {
                "success": (self.uploaded_count > 0 and not self.rate_limited and not self.checkpoint_hit),
                "status": final_status,
                "count": self.uploaded_count,
                "message": f"Finished reels for {self.account_name}. Status: {final_status} (Uploaded: {self.uploaded_count}/{total_reels})"
            }

        except Exception as e:
            self.log("ERROR", f"Error during reels upload execution: {str(e)}")
            return {"success": False, "count": self.uploaded_count, "message": str(e)}

        finally:
            self.log("INFO", f"Closing Chrome browser cleanly for {self.account_name}...")
            await self.close()
            self.log("INFO", f"🔒 Chrome closed for {self.account_name}.")
