#!/usr/bin/env python3
"""
FB Auto Bot - Facebook Automation Suite
automation/page_creator_bot.py - Multi-Account & Multi-Tab Facebook Page Creator Bot

Human-like Playwright engine for creating and configuring Facebook Pages:
  1. Opens Facebook session with account cookies / persistent profile
  2. Opens requested tabs per account cleanly
  3. Navigates to facebook.com/pages/create/ and handles Public Page selection if shown
  4. Human-types Page Name, matches & commits Category from suggestion list, and types Bio
  5. Staggers initial 'Create Page' / 'Next' submission naturally like a real user
  6. Completes Step 1 (Website, Phone, Email, Address, City, ZIP, Hours) & reliably advances 'Next'
  7. Uploads Profile Picture & Cover Photo with section-scoped targeting + upload completion wait, then advances 'Next'
  8. Smoothly finishes WhatsApp Skip / Audience Next / Notifications Done with zero robotic jumps
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

try:
    from automation.browser_window_manager import (
        resolve_tile_context,
        build_window_chrome_args,
        apply_cdp_window_bounds,
        launch_bot_browser_context,
        get_bot_working_page,
        human_click_element,
        human_move_and_click,
        human_click_coords,
        human_type_text,
        human_smooth_scroll,
        human_pause,
        human_session_warmup,
        human_idle_drift,
    )
except ImportError:
    try:
        from desktop_app.automation.browser_window_manager import (
            resolve_tile_context,
            build_window_chrome_args,
            apply_cdp_window_bounds,
            launch_bot_browser_context,
            get_bot_working_page,
            human_click_element,
            human_move_and_click,
            human_click_coords,
            human_type_text,
            human_smooth_scroll,
            human_pause,
            human_session_warmup,
            human_idle_drift,
        )
    except ImportError:
        def resolve_tile_context(account_data=None, window_slot=None, total_window_slots=None, tile_rect=None):
            return 0, 1, (0, 0, 1920, 1080)
        def build_window_chrome_args(tile_rect=None, total_slots=1, slot_index=0, profile_directory=None, apply_scale_factor=True):
            return []
        async def apply_cdp_window_bounds(context, page=None, tile_rect=None, total_slots=1, slot_index=0):
            return False
        async def get_bot_working_page(context):
            return context.pages[0] if getattr(context, "pages", None) else await context.new_page()
        launch_bot_browser_context = None
        async def human_pause(low=0.55, high=1.45, mult=1.0):
            await asyncio.sleep(random.uniform(low, high))
        async def human_click_element(page, target, hover_pause=True, force_fallback=True):
            if target is None:
                return False
            try:
                await target.scroll_into_view_if_needed()
                await target.click()
                return True
            except Exception:
                return False
        async def human_move_and_click(page, locator, hover_pause=True, force_fallback=True):
            return await human_click_element(page, locator, hover_pause=hover_pause, force_fallback=force_fallback)
        async def human_click_coords(page, x, y, hover_pause=True):
            try:
                await page.mouse.move(x, y, steps=8)
                await page.mouse.click(x, y)
                return True
            except Exception:
                return False
        async def human_type_text(page, target, text, clear_first=True, allow_typos=False):
            if target is None:
                return False
            try:
                await target.click()
                if clear_first:
                    await target.fill("")
                await page.keyboard.type(str(text), delay=40)
                return True
            except Exception:
                return False
        async def human_smooth_scroll(page, total_delta_y=550, steps=6):
            for _ in range(max(2, steps)):
                await page.mouse.wheel(0, total_delta_y / max(2, steps))
                await asyncio.sleep(0.06)
        async def human_session_warmup(page, duration_range=(1.2, 2.3), log_cb=None):
            await asyncio.sleep(random.uniform(*duration_range))
        async def human_idle_drift(page):
            await asyncio.sleep(random.uniform(0.2, 0.45))

logger = logging.getLogger("FBAutoBot.PageCreator")

DESKTOP_CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
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

# Multilingual Category Map (English -> Portuguese/Brazil, Spanish, etc.)
CATEGORY_TRANSLATIONS: Dict[str, List[str]] = {
    "digital creator": ["Criador de conteúdo digital", "Criador digital", "Creador digital", "Digital Creator"],
    "real estate agency": ["Agência imobiliária", "Inmobiliaria", "Agencia inmobiliaria", "Real Estate Agency"],
    "marketing agency": ["Agência de marketing", "Agencia de marketing", "Marketing Agency"],
    "advertising/marketing": ["Publicidade/marketing", "Publicidad/marketing", "Advertising/Marketing"],
    "e-commerce website": ["Site de comércio eletrônico", "Sitio web de comercio electrónico", "E-commerce Website"],
    "entrepreneur": ["Empreendedor", "Emprendedor", "Entrepreneur"],
    "business service": ["Serviço empresarial", "Servicio comercial", "Business Service"],
    "product/service": ["Produto/serviço", "Producto/servicio", "Product/service"],
    "shopping & retail": ["Compras e varejo", "Compras y venta minorista", "Shopping & retail"],
    "consulting agency": ["Agência de consultoria", "Agencia de consultoría", "Consulting Agency"],
    "information technology company": ["Empresa de tecnologia da informação", "Empresa de tecnología de la información", "Information Technology Company"],
    "community": ["Comunidade", "Comunidad", "Community"],
    "health/beauty": ["Saúde/beleza", "Salud/belleza", "Health/beauty"],
    "restaurant": ["Restaurante", "Restaurant"],
    "photographer": ["Fotógrafo", "Fotógrafo(a)", "Photographer"],
    "education": ["Educação", "Educación", "Education"],
    "clothing (brand)": ["Roupas (marca)", "Ropa (marca)", "Clothing (Brand)"],
    "artist": ["Artista", "Artist"],
    "musician/band": ["Músico/banda", "Musician/band"]
}


def get_category_search_candidates(category: str) -> List[str]:
    """Returns candidate search strings for the category across English, Portuguese, and Spanish."""
    cat = (category or "").strip()
    if not cat:
        return ["Digital Creator", "Criador digital", "Criador de conteúdo digital"]
    cat_lower = cat.lower()
    results = [cat]

    if cat_lower in CATEGORY_TRANSLATIONS:
        for term in CATEGORY_TRANSLATIONS[cat_lower]:
            if term not in results:
                results.append(term)
    else:
        for k, v_list in CATEGORY_TRANSLATIONS.items():
            if k in cat_lower or cat_lower in k:
                for term in v_list:
                    if term not in results:
                        results.append(term)

    for eng_key, trans_list in CATEGORY_TRANSLATIONS.items():
        if any(t.lower() == cat_lower for t in trans_list):
            eng_title = eng_key.title()
            if eng_title not in results:
                results.append(eng_title)
            for t in trans_list:
                if t not in results:
                    results.append(t)
    return results


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
    Facebook Pages with natural human-like pacing, vertical-only panel scrolling,
    verified wizard transitions, and reliable Profile & Cover photo uploads.
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

    # --------------------------------------------------------------------------
    # Human-Like Interaction Primitives (Anti-Detection & Zero Erratic Scrolling)
    # --------------------------------------------------------------------------
    async def _human_pause(self, min_s: float = 0.45, max_s: float = 1.15):
        if self._is_cancelled:
            return
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def _smooth_scroll_vertical_to_element(self, page, locator) -> bool:
        """
        Smoothly scrolls ONLY the vertical scrollable wizard panel (never horizontal scrollLeft)
        so the target element sits comfortably in view without jerking left/right.
        """
        try:
            handle = await locator.element_handle()
            if not handle:
                return False
            await page.evaluate("""async (el) => {
                if (!el) return;
                // Walk up to find vertical scrollable container (never touch horizontal scrollLeft)
                let parent = el.parentElement;
                let scrollBox = null;
                while (parent && parent !== document.body && parent !== document.documentElement) {
                    const style = window.getComputedStyle(parent);
                    const oy = style.overflowY;
                    if ((oy === 'auto' || oy === 'scroll') && parent.scrollHeight > parent.clientHeight + 10) {
                        scrollBox = parent;
                        break;
                    }
                    parent = parent.parentElement;
                }

                const rect = el.getBoundingClientRect();
                const viewH = window.innerHeight || document.documentElement.clientHeight;
                if (rect.top >= 90 && rect.bottom <= viewH - 90) {
                    return; // Already nicely visible
                }

                if (scrollBox) {
                    const boxRect = scrollBox.getBoundingClientRect();
                    const offset = (rect.top - boxRect.top) - (boxRect.height * 0.38);
                    const start = scrollBox.scrollTop;
                    const target = Math.max(0, Math.min(scrollBox.scrollHeight - scrollBox.clientHeight, start + offset));
                    const steps = 6;
                    for (let i = 1; i <= steps; i++) {
                        scrollBox.scrollTop = start + ((target - start) * (i / steps));
                        await new Promise(r => setTimeout(r, 38));
                    }
                } else {
                    const startY = window.scrollY;
                    const deltaY = rect.top - (viewH * 0.4);
                    const targetY = Math.max(0, startY + deltaY);
                    const steps = 6;
                    for (let i = 1; i <= steps; i++) {
                        window.scrollTo({ top: startY + ((targetY - startY) * (i / steps)), left: 0 });
                        await new Promise(r => setTimeout(r, 38));
                    }
                }
            }""", handle)
            await asyncio.sleep(random.uniform(0.18, 0.35))
            return True
        except Exception:
            return False

    async def _smooth_scroll_wizard_panel(self, page, position: str = "bottom"):
        """
        Smoothly scrolls ONLY the active left-side wizard column ('top', 'middle', or 'bottom')
        without causing horizontal left/right jitter on the preview pane.
        """
        try:
            await page.evaluate("""async (pos) => {
                const vw = window.innerWidth || 1280;
                const allDivs = Array.from(document.querySelectorAll('div[role="dialog"] div, div[role="main"] div, div'));
                let targetPanel = null;
                let bestScore = -1;

                for (const d of allDivs) {
                    if (d.scrollHeight <= d.clientHeight + 25) continue;
                    const style = window.getComputedStyle(d);
                    if (style.overflowY !== 'auto' && style.overflowY !== 'scroll') continue;
                    const r = d.getBoundingClientRect();
                    // Left-side wizard pane usually has width 260..580 and starts near left side, OR inside dialog
                    if (r.width < 220 || r.height < 220) continue;
                    if (r.left > vw * 0.55) continue; // Ignore right-side preview panes!
                    const txt = (d.innerText || '').toLowerCase();
                    let score = r.height;
                    if (txt.includes('page name') || txt.includes('category') || txt.includes('finish setting up') ||
                        txt.includes('customize your page') || txt.includes('website') || txt.includes('profile picture') ||
                        txt.includes('nome da página') || txt.includes('nombre de la página') ||
                        txt.includes('next') || txt.includes('create page')) {
                        score += 2000;
                    }
                    if (score > bestScore) {
                        bestScore = score;
                        targetPanel = d;
                    }
                }

                if (!targetPanel) return;

                const maxScroll = Math.max(0, targetPanel.scrollHeight - targetPanel.clientHeight);
                let goal = maxScroll;
                if (pos === 'top') goal = 0;
                else if (pos === 'middle') goal = Math.round(maxScroll * 0.45);

                const start = targetPanel.scrollTop;
                if (Math.abs(goal - start) < 15) return;
                const steps = 6;
                for (let i = 1; i <= steps; i++) {
                    targetPanel.scrollTop = start + ((goal - start) * (i / steps));
                    await new Promise(r => setTimeout(r, 42));
                }
            }""", position)
            await asyncio.sleep(random.uniform(0.25, 0.5))
        except Exception:
            pass

    async def _human_move_and_click(self, page, locator, hover_pause: bool = True) -> bool:
        """
        Smoothly scrolls vertically to target, glides the mouse along an organic Bezier curve
        with hover pause, and performs a natural down/up click.
        """
        try:
            await self._smooth_scroll_vertical_to_element(page, locator)
            return await human_move_and_click(page, locator, hover_pause=hover_pause, force_fallback=True)
        except Exception:
            return False

    async def _human_type_into(self, page, locator, text: str, clear_first: bool = True, allow_typos: bool = False) -> bool:
        """Clicks naturally, clears existing text safely, and types with variable human keystroke rhythm."""
        if self._is_cancelled:
            return False
        try:
            await self._smooth_scroll_vertical_to_element(page, locator)
            return await human_type_text(page, locator, text, clear_first=clear_first, allow_typos=allow_typos)
        except Exception:
            return False

    # --------------------------------------------------------------------------
    # Browser Initialization & Cookies
    # --------------------------------------------------------------------------
    async def init_browser(self):
        """Initializes Playwright and launches Chrome with persistent context or profile."""
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()

        profile_dir = self.account_data.get("profile_dir")
        chrome_profile_directory = self.account_data.get("chrome_profile_directory")
        is_custom_profile = bool(self.account_data.get("is_custom_chrome_profile", False))
        if not profile_dir or not os.path.exists(profile_dir):
            base_p = os.path.join(os.getcwd(), "profiles", f"acc_{self.account_id}")
            os.makedirs(base_p, exist_ok=True)
            profile_dir = base_p

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

        slot_idx, total_slots, resolved_tile = resolve_tile_context(self.account_data)

        launch_args = [
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-notifications",
            "--lang=en-US",
            "--accept-lang=en-US,en;q=0.9",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=CalculateNativeWinOcclusion",
            "--disable-ipc-flooding-protection"
        ]
        launch_args.extend(build_window_chrome_args(
            tile_rect=resolved_tile,
            total_slots=total_slots,
            slot_index=slot_idx,
            profile_directory=chrome_profile_directory,
        ))

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
            self.log("INFO", "🌐 Network Mode: Direct high-speed connection (Proxy bypassed, zero proxy errors).")
        else:
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
                        self.log("WARNING", f"⚠️ Proxy {host}:{port} unreachable. Falling back to direct connection.")
                        proxy_cfg = None
                        launch_args.append("--no-proxy-server")
                else:
                    proxy_cfg = None
                    launch_args.append("--no-proxy-server")
            except Exception:
                proxy_cfg = None
                launch_args.append("--no-proxy-server")

        self.context = None
        if launch_bot_browser_context is not None:
            self.context, self.browser = await launch_bot_browser_context(
                playwright=self.playwright,
                account_data=self.account_data,
                profile_dir=profile_dir,
                launch_args=launch_args,
                ignore_default_args=["--enable-automation", "--disable-extensions"],
                proxy_cfg=proxy_cfg,
                context_kwargs={
                    "user_agent": DESKTOP_CHROME_USER_AGENT,
                    "no_viewport": True,
                    "locale": "en-US",
                    "extra_http_headers": {
                        "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,es;q=0.6"
                    },
                    "permissions": ["geolocation", "notifications"],
                },
                log_cb=self.log,
                allow_ephemeral_fallback=not is_custom_profile,
            )
        else:
            chrome_exe = (self.account_data.get("chrome_executable") or "").strip() or None
            if not (chrome_exe and os.path.isfile(chrome_exe)):
                try:
                    from automation.extension_manager import get_system_chrome_executable
                    chrome_exe = get_system_chrome_executable()
                except Exception:
                    chrome_exe = None

            channels = []
            if chrome_exe and os.path.isfile(chrome_exe):
                channels.append(("real_chrome", chrome_exe))
            channels.extend([("chrome", None), ("msedge", None)])
            if not is_custom_profile:
                channels.append((None, None))

            fb_ign = ["--enable-automation", "--disable-extensions"]
            if is_custom_profile:
                fb_ign.extend([
                    "--password-store=basic",
                    "--use-mock-keychain",
                    "--disable-sync",
                    "--disable-default-apps",
                    "--disable-component-extensions-with-background-pages",
                    "--disable-background-networking",
                ])

            for ch, exe_p in channels:
                try:
                    kwargs = {
                        "user_data_dir": profile_dir,
                        "headless": False,
                        "args": launch_args,
                        "ignore_default_args": fb_ign,
                        "proxy": proxy_cfg,
                        "no_viewport": True,
                        "locale": "en-US",
                        "extra_http_headers": {
                            "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,es;q=0.6"
                        },
                        "permissions": ["geolocation", "notifications"]
                    }
                    if not is_custom_profile:
                        kwargs["user_agent"] = DESKTOP_CHROME_USER_AGENT
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
                if is_custom_profile:
                    raise RuntimeError(f"Custom Chrome profile unavailable at '{profile_dir}'. Close any open Chrome window on that profile and retry.")
                self.log("WARNING", "Persistent profile unavailable. Launching standard browser...")
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=launch_args,
                    ignore_default_args=["--enable-automation"],
                    proxy=proxy_cfg
                )
                self.context = await self.browser.new_context(
                    user_agent=DESKTOP_CHROME_USER_AGENT,
                    no_viewport=True,
                    locale="en-US",
                    extra_http_headers={
                        "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,es;q=0.6"
                    }
                )

        if self.context:
            first_page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            await apply_cdp_window_bounds(
                self.context,
                first_page,
                tile_rect=resolved_tile,
                total_slots=total_slots,
                slot_index=slot_idx,
            )

        raw_cookies = self.account_data.get("cookies", "")
        if self.context and (raw_cookies or not is_custom_profile):
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

                if formatted_cookies or not is_custom_profile:
                    formatted_cookies.append({
                        "name": "locale",
                        "value": "en_US",
                        "domain": ".facebook.com",
                        "path": "/",
                        "secure": True
                    })

                if formatted_cookies:
                    await self.context.add_cookies(formatted_cookies)
                    self.log("SUCCESS", f"🔑 Injected {len(formatted_cookies)} Facebook session cookies (Language: en_US).")
            except Exception as e:
                self.log("DEBUG", f"Cookie injection notice: {e}")
        elif is_custom_profile:
            self.log("INFO", f"Using saved session cookies from custom Chrome profile '{os.path.basename(profile_dir)}'.")

    # --------------------------------------------------------------------------
    # Phase 1: Navigate & Public Page Modal
    # --------------------------------------------------------------------------
    async def _handle_create_modal_and_navigate(self, page, tab_index: int) -> bool:
        target_url = "https://www.facebook.com/pages/create/?locale=en_US"
        self.log("INFO", f"[Tab #{tab_index}] Opening Facebook Page Creation: {target_url}")

        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
            slot_idx, total_slots, tile_rect = resolve_tile_context(self.account_data)
            await apply_cdp_window_bounds(
                self.context,
                page,
                tile_rect=tile_rect,
                total_slots=total_slots,
                slot_index=slot_idx,
            )
            await self._human_pause(1.8, 3.0)
        except Exception as e:
            self.log("WARNING", f"[Tab #{tab_index}] Navigation notice: {str(e)[:60]}")
            try:
                await self._human_pause(1.5, 2.5)
                await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
                await self._human_pause(1.8, 2.8)
            except Exception:
                pass

        current_url = page.url.lower()
        if "login" in current_url or "checkpoint" in current_url:
            self.log("ERROR", f"[Tab #{tab_index}] Facebook account requires login or checkpoint verification!")
            return False

        if "pages/create" not in current_url:
            try:
                create_page_btn = page.locator(
                    'a[href*="/pages/create"], button:has-text("Create Page"), div[role="button"]:has-text("Create Page"), '
                    'button:has-text("Criar página"), div[role="button"]:has-text("Criar página"), '
                    'button:has-text("Crear página"), div[role="button"]:has-text("Crear página")'
                ).first
                if await create_page_btn.count() > 0 and await create_page_btn.is_visible():
                    self.log("INFO", f"[Tab #{tab_index}] Clicking '+ Create Page' on Pages dashboard...")
                    await self._human_move_and_click(page, create_page_btn)
                    await self._human_pause(1.6, 2.5)
            except Exception:
                pass

        # Handle 'Create / Which option is best for you?' modal if shown
        try:
            dialog = page.locator('div[role="dialog"]').first
            if await dialog.count() > 0 and await dialog.is_visible():
                dialog_txt = ((await dialog.inner_text()) or "").lower()
                if any(k in dialog_txt for k in [
                    "public page", "public place", "which option is best",
                    "página pública", "qual opção", "elige una opción", "get started"
                ]):
                    self.log("INFO", f"[Tab #{tab_index}] Detected Page Type selection dialog.")
                    clicked_opt = False
                    for p_label in [
                        'div[role="radio"]:has-text("Public")',
                        'text="Public Place Page"',
                        'text="Public Page"',
                        'text="Página pública"',
                        'text="Página de local público"',
                        'div:has-text("Public Page")',
                        'span:has-text("Public")'
                    ]:
                        public_opt = dialog.locator(p_label).first
                        if await public_opt.count() > 0 and await public_opt.is_visible():
                            await self._human_move_and_click(page, public_opt)
                            await self._human_pause(0.5, 0.9)
                            clicked_opt = True
                            break

                    if not clicked_opt:
                        radio = dialog.locator('input[type="radio"], div[role="radio"]').first
                        if await radio.count() > 0 and await radio.is_visible():
                            await self._human_move_and_click(page, radio)
                            await self._human_pause(0.5, 0.9)

                    for n_sel in [
                        'div[aria-label="Next"][role="button"]',
                        'button:has-text("Next")',
                        'div[role="button"]:has-text("Next")',
                        'button:has-text("Get Started")',
                        'div[role="button"]:has-text("Get Started")',
                        'button:has-text("Avançar")',
                        'div[role="button"]:has-text("Avançar")',
                        'button:has-text("Siguiente")',
                        'div[role="button"]:has-text("Siguiente")'
                    ]:
                        next_btn = dialog.locator(n_sel).first
                        if await next_btn.count() > 0 and await next_btn.is_visible():
                            self.log("INFO", f"[Tab #{tab_index}] Clicking dialog confirmation button...")
                            await self._human_move_and_click(page, next_btn)
                            await self._human_pause(1.8, 2.8)
                            break
        except Exception as e:
            self.log("DEBUG", f"[Tab #{tab_index}] Modal handling notice: {e}")

        if not self._is_cancelled:
            await human_session_warmup(page, duration_range=(0.9, 1.6))

        return True

    # --------------------------------------------------------------------------
    # Phase 2: Screen 1 Form Filling (Page Name, Category, Bio)
    # --------------------------------------------------------------------------
    async def _is_initial_form_screen(self, page) -> bool:
        """Returns True if page is still on Screen 1 (Page name & Category inputs visible)."""
        try:
            return await page.evaluate("""() => {
                const inputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type])'));
                for (const inp of inputs) {
                    const r = inp.getBoundingClientRect();
                    if (r.width === 0 || r.height === 0) continue;
                    const aria = (inp.getAttribute('aria-label') || '').toLowerCase();
                    if (aria.includes('page name') || aria.includes('nome da página') ||
                        aria.includes('nombre de la página') || aria.includes('category') ||
                        aria.includes('categoria')) {
                        return true;
                    }
                }
                return false;
            }""")
        except Exception:
            return False

    async def _fill_page_form(self, page, tab_index: int, page_name: str, category: str, bio: str) -> bool:
        """
        Human-fills Screen 1 ('Create a Page'):
          - Page name (required)
          - Category (required) -> types slowly, picks visible option, verifies selection & closes dropdown
          - Bio (optional)
        """
        self.log("INFO", f"[Tab #{tab_index}] Filling Screen 1: Name='{page_name}', Category='{category}'...")

        # Wait gently for form input to render
        for _ in range(10):
            if await self._is_initial_form_screen(page):
                break
            await asyncio.sleep(0.5)

        # 1. Page Name
        name_filled = False
        name_locators = [
            'input[aria-label*="Page name" i]',
            'input[aria-label*="Nome da página" i]',
            'input[aria-label*="Nombre de la página" i]',
            'input[aria-label*="name (required)" i]',
            'input[aria-label*="nome (obrigatório)" i]',
            'div[role="main"] input[type="text"]',
            'input[type="text"]'
        ]
        for sel in name_locators:
            try:
                inp = page.locator(sel).first
                if await inp.count() > 0 and await inp.is_visible():
                    await self._human_type_into(page, inp, page_name, clear_first=True, allow_typos=True)
                    val_now = (await inp.input_value()).strip()
                    if val_now == page_name.strip():
                        name_filled = True
                        break
            except Exception as e:
                self.log("DEBUG", f"[Tab #{tab_index}] Page name input notice: {e}")

        if not name_filled:
            name_filled = await page.evaluate("""(pName) => {
                function setVal(el, v) {
                    if (!el) return false;
                    el.focus();
                    const last = el.value;
                    const proto = Object.getPrototypeOf(el);
                    const desc = Object.getOwnPropertyDescriptor(proto, 'value');
                    if (desc && desc.set) desc.set.call(el, v);
                    else el.value = v;
                    if (el._valueTracker) el._valueTracker.setValue(last);
                    el.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                    return true;
                }
                const inputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type])'));
                for (const inp of inputs) {
                    const aria = (inp.getAttribute('aria-label') || '').toLowerCase();
                    if (aria.includes('page name') || aria.includes('nome') || aria.includes('nombre')) {
                        return setVal(inp, pName);
                    }
                }
                return inputs.length > 0 ? setVal(inputs[0], pName) : false;
            }""", page_name)

        await self._human_pause(0.6, 1.1)

        # 2. Category (Required autocomplete chip/selection)
        cat_filled = False
        cat_candidates = get_category_search_candidates(category)
        self.log("INFO", f"[Tab #{tab_index}] Matching Category from candidates: {', '.join(cat_candidates[:3])}")

        cat_input = None
        for sel in [
            'input[aria-label*="Category" i]',
            'input[aria-label*="Categoria" i]',
            'input[aria-label*="Categoría" i]',
            'input[aria-autocomplete="list"]',
            'div[role="combobox"] input'
        ]:
            try:
                c_loc = page.locator(sel).first
                if await c_loc.count() > 0 and await c_loc.is_visible():
                    cat_input = c_loc
                    break
            except Exception:
                pass

        for c_cand in cat_candidates:
            if cat_filled or self._is_cancelled:
                break
            try:
                if cat_input:
                    await self._human_type_into(page, cat_input, c_cand, clear_first=True)
                else:
                    await page.evaluate("""(cVal) => {
                        const inputs = Array.from(document.querySelectorAll('input'));
                        for (const inp of inputs) {
                            const aria = (inp.getAttribute('aria-label') || '').toLowerCase();
                            if (aria.includes('category') || aria.includes('categoria') ||
                                inp.getAttribute('aria-autocomplete') === 'list') {
                                inp.focus();
                                inp.value = cVal;
                                inp.dispatchEvent(new Event('input', { bubbles: true }));
                                inp.dispatchEvent(new Event('change', { bubbles: true }));
                                break;
                            }
                        }
                    }""", c_cand)

                # Wait naturally for Facebook suggestion popover items
                for _ in range(10):
                    await asyncio.sleep(0.45)
                    opt_locators = [
                        'div[role="listbox"] div[role="option"]',
                        'ul[role="listbox"] li',
                        'div[role="option"]',
                        'div[aria-label*="Search results" i] div[role="option"]',
                        'div[role="listbox"] span'
                    ]
                    clicked_option = False
                    for o_sel in opt_locators:
                        opts = page.locator(o_sel)
                        cnt = await opts.count()
                        if cnt > 0:
                            # Prefer option whose text matches candidate cleanly
                            chosen_opt = opts.first
                            for i in range(min(cnt, 6)):
                                candidate_opt = opts.nth(i)
                                if await candidate_opt.is_visible():
                                    txt = ((await candidate_opt.inner_text()) or "").strip().lower()
                                    if txt and (c_cand.lower() in txt or txt in c_cand.lower()):
                                        chosen_opt = candidate_opt
                                        break
                            if await chosen_opt.is_visible():
                                await self._human_move_and_click(page, chosen_opt)
                                clicked_option = True
                                cat_filled = True
                                self.log("SUCCESS", f"[Tab #{tab_index}] Selected Category option ('{c_cand}').")
                                break
                    if clicked_option:
                        break
            except Exception as e:
                self.log("DEBUG", f"[Tab #{tab_index}] Category attempt '{c_cand}' notice: {e}")

        if not cat_filled:
            try:
                await page.keyboard.press("ArrowDown")
                await asyncio.sleep(0.35)
                await page.keyboard.press("Enter")
                cat_filled = True
                self.log("INFO", f"[Tab #{tab_index}] Accepted Category suggestion via keyboard.")
            except Exception:
                pass

        # Gently pause & click neutral whitespace inside left panel if dropdown lingers, then ensure Bio & button are reachable
        await self._human_pause(0.6, 1.0)
        try:
            await page.keyboard.press("Tab")
        except Exception:
            pass

        # 3. Bio (Optional)
        if bio:
            await self._smooth_scroll_wizard_panel(page, "middle")
            bio_filled = False
            for b_sel in [
                'textarea[aria-label*="Bio" i]',
                'textarea[aria-label*="Biografia" i]',
                'textarea[aria-label*="Biografía" i]',
                'textarea[placeholder*="bio" i]',
                'div[role="main"] textarea',
                'textarea'
            ]:
                try:
                    bio_el = page.locator(b_sel).first
                    if await bio_el.count() > 0 and await bio_el.is_visible():
                        await self._human_type_into(page, bio_el, bio, clear_first=True, allow_typos=True)
                        bio_filled = True
                        break
                except Exception:
                    pass

            if not bio_filled:
                await page.evaluate("""(bioText) => {
                    const t = document.querySelector('textarea');
                    if (t) {
                        t.focus();
                        const proto = Object.getPrototypeOf(t);
                        const desc = Object.getOwnPropertyDescriptor(proto, 'value');
                        if (desc && desc.set) desc.set.call(t, bioText);
                        else t.value = bioText;
                        t.dispatchEvent(new Event('input', { bubbles: true }));
                        t.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }""", bio)
            await self._human_pause(0.5, 0.9)

        self.log("SUCCESS", f"✅ [Tab #{tab_index}] Screen 1 fields ready for '{page_name}'.")
        return True

    # --------------------------------------------------------------------------
    # Unified Wizard Footer Button Locator & Clicker (Scoped to Active Wizard Column)
    # --------------------------------------------------------------------------
    async def _find_and_click_wizard_footer_button(self, page, btn_type: str = "next", tab_index: int = 1) -> bool:
        """
        Reliably finds and clicks the primary visible & enabled button in the left wizard footer
        without erratic horizontal/vertical page jumping!
        Supports:
          - 'create_or_next': matches 'Create Page' OR 'Next' (and localized Portuguese/Spanish)
          - 'next': matches 'Next' / 'Avançar' / 'Seguinte' / 'Próximo' / 'Siguiente'
          - 'skip': matches 'Skip' / 'Pular' / 'Ignorar' / 'Omitir'
          - 'done': matches 'Done' / 'Save' / 'Concluir' / 'Salvar' / 'Guardar' / 'Listo'
        """
        btn_type = btn_type.lower().strip()
        await self._smooth_scroll_wizard_panel(page, "bottom")
        await self._human_pause(0.35, 0.75)

        # Wait up to ~5s if target button is momentarily aria-disabled="true" (React validation settling)
        for wait_try in range(8):
            if self._is_cancelled:
                return False

            target_meta = await page.evaluate("""(targetType) => {
                const vw = window.innerWidth || 1280;
                const vh = window.innerHeight || 720;

                const createTerms = ['create page', 'criar página', 'criar pagina', 'crear página', 'crear pagina'];
                const nextTerms = ['next', 'avançar', 'avancar', 'seguinte', 'próximo', 'proximo', 'siguiente', 'continue', 'continuar'];
                const skipTerms = ['skip', 'pular', 'ignorar', 'omitir'];
                const doneTerms = ['done', 'concluir', 'salvar', 'guardar', 'listo', 'save', 'finish'];

                let wantTerms = nextTerms;
                if (targetType === 'create_or_next') {
                    wantTerms = [...createTerms, ...nextTerms];
                } else if (targetType === 'skip') {
                    wantTerms = skipTerms;
                } else if (targetType === 'done') {
                    wantTerms = [...doneTerms, ...nextTerms.filter(t => t === 'continue')];
                }

                const candidates = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"]'));
                const scored = [];

                for (const b of candidates) {
                    // Reject invisible or aria-hidden subtrees (like background desktop/mobile preview)
                    if (b.closest('[aria-hidden="true"]')) continue;
                    const style = window.getComputedStyle(b);
                    if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity || '1') === 0) continue;

                    const rect = b.getBoundingClientRect();
                    if (rect.width < 32 || rect.height < 22) continue;

                    const rawLabel = (b.getAttribute('aria-label') || '').trim().toLowerCase();
                    const rawText = (b.innerText || b.textContent || '').trim().toLowerCase().replace(/\\s+/g, ' ');
                    const txt = rawLabel || rawText;
                    if (!txt) continue;

                    // Exact or tight match
                    let matchedPriority = 0;
                    if (targetType === 'create_or_next') {
                        if (createTerms.includes(txt)) matchedPriority = 100;
                        else if (nextTerms.includes(txt)) matchedPriority = 90;
                        else if (createTerms.some(t => txt.includes(t)) && txt.length < 30) matchedPriority = 75;
                    } else {
                        if (wantTerms.includes(txt)) matchedPriority = 100;
                        else if (wantTerms.some(t => txt === t || (txt.startsWith(t) && txt.length <= t.length + 6))) matchedPriority = 75;
                    }
                    if (!matchedPriority) continue;

                    const isDisabled = b.getAttribute('aria-disabled') === 'true' || b.hasAttribute('disabled') || style.pointerEvents === 'none';

                    // Strongly prefer buttons in left wizard sidebar (rect.left < 55% width) or inside modal dialog footer
                    let score = matchedPriority;
                    if (rect.left < vw * 0.56) score += 60;
                    if (b.closest('div[role="dialog"]')) score += 30;
                    // Prefer bottom-most action button inside panel
                    score += Math.min(40, Math.round((rect.top / Math.max(1, vh)) * 40));

                    // Prefer blue / primary highlighted button
                    const bg = (style.backgroundColor || '').toLowerCase();
                    if (bg.includes('8, 102, 255') || bg.includes('24, 119, 242') || bg.includes('0, 100, 224') || bg.includes('35, 116, 225')) {
                        score += 35;
                    }

                    scored.push({
                        el: b,
                        score,
                        isDisabled,
                        x: rect.left + rect.width * (0.4 + Math.random() * 0.2),
                        y: rect.top + rect.height * (0.4 + Math.random() * 0.2),
                        inView: rect.top >= 10 && rect.bottom <= vh - 6,
                        txt
                    });
                }

                if (scored.length === 0) return { found: false };
                scored.sort((a, b) => b.score - a.score);
                const enabledOnes = scored.filter(s => !s.isDisabled);
                const pick = enabledOnes.length > 0 ? enabledOnes[0] : scored[0];

                if (!pick.inView) {
                    pick.el.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
                }

                return {
                    found: true,
                    disabled: pick.isDisabled,
                    x: pick.x,
                    y: pick.y,
                    label: pick.txt
                };
            }""", btn_type)

            if not target_meta or not target_meta.get("found"):
                await asyncio.sleep(0.55)
                continue

            if target_meta.get("disabled"):
                self.log("DEBUG", f"[Tab #{tab_index}] Wizard button '{target_meta.get('label')}' validating... waiting ({wait_try + 1}/8)")
                await asyncio.sleep(0.65)
                continue

            # Re-measure exact coords after smooth scroll
            await asyncio.sleep(0.25)
            coords = await page.evaluate("""(targetType) => {
                const vw = window.innerWidth || 1280;
                const vh = window.innerHeight || 720;
                const createTerms = ['create page', 'criar página', 'criar pagina', 'crear página', 'crear pagina'];
                const nextTerms = ['next', 'avançar', 'avancar', 'seguinte', 'próximo', 'proximo', 'siguiente', 'continue', 'continuar'];
                const skipTerms = ['skip', 'pular', 'ignorar', 'omitir'];
                const doneTerms = ['done', 'concluir', 'salvar', 'guardar', 'listo', 'save', 'finish'];
                let wantTerms = nextTerms;
                if (targetType === 'create_or_next') wantTerms = [...createTerms, ...nextTerms];
                else if (targetType === 'skip') wantTerms = skipTerms;
                else if (targetType === 'done') wantTerms = [...doneTerms, ...nextTerms.filter(t => t === 'continue')];

                const candidates = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"]'));
                const scored = [];
                for (const b of candidates) {
                    if (b.closest('[aria-hidden="true"]')) continue;
                    const style = window.getComputedStyle(b);
                    if (style.display === 'none' || style.visibility === 'hidden') continue;
                    const rect = b.getBoundingClientRect();
                    if (rect.width < 32 || rect.height < 22) continue;
                    const dis = b.getAttribute('aria-disabled') === 'true' || b.hasAttribute('disabled');
                    if (dis) continue;
                    const txt = (b.getAttribute('aria-label') || b.innerText || b.textContent || '').trim().toLowerCase().replace(/\\s+/g, ' ');
                    if (!wantTerms.some(t => txt === t || (txt.startsWith(t) && txt.length <= t.length + 8))) continue;
                    let score = wantTerms.includes(txt) ? 100 : 75;
                    if (rect.left < vw * 0.56) score += 60;
                    if (b.closest('div[role="dialog"]')) score += 30;
                    score += Math.min(40, Math.round((rect.top / Math.max(1, vh)) * 40));
                    scored.push({ el: b, score, rect, txt });
                }
                if (!scored.length) return null;
                scored.sort((a, b) => b.score - a.score);
                const p = scored[0];
                window.__fbLastWizardBtn = p.el;
                return {
                    x: p.rect.left + p.rect.width * (0.42 + Math.random() * 0.16),
                    y: p.rect.top + p.rect.height * (0.42 + Math.random() * 0.16),
                    txt: p.txt
                };
            }""", btn_type)

            if coords and coords.get("x") and coords.get("y"):
                tx, ty = float(coords["x"]), float(coords["y"])
                await human_click_coords(page, tx, ty, hover_pause=True)
                self.log("INFO", f"🖱️ [Tab #{tab_index}] Clicked '{coords.get('txt')}' naturally.")
                return True

        return False

    async def _submit_screen1_and_verify(self, page, tab_index: int, page_name: str) -> bool:
        """
        Clicks 'Create Page' OR 'Next' on Screen 1 with human timing and verifies
        that Screen 1 actually transitions to Step 1 (Contact/Hours) or Step 2 (Photos).
        """
        for submit_try in range(2):
            if self._is_cancelled:
                return False

            clicked = await self._find_and_click_wizard_footer_button(page, "create_or_next", tab_index=tab_index)
            if not clicked:
                self.log("WARNING", f"⚠️ [Tab #{tab_index}] Could not locate active 'Next' / 'Create Page' button (attempt {submit_try + 1}).")
                await asyncio.sleep(1.0)
                continue

            # Monitor up to 12 seconds for transition away from Screen 1
            for _ in range(12):
                if self._is_cancelled:
                    return False
                await asyncio.sleep(1.0)
                status = await page.evaluate("""() => {
                    const text = (document.body.innerText || '').toLowerCase();
                    const url = (window.location.href || '').toLowerCase();

                    if (text.includes('too many pages') || text.includes('muitas páginas') ||
                        text.includes('demasiadas páginas') || text.includes('limit reached') ||
                        text.includes("you've created too many")) {
                        return 'rate_limit';
                    }

                    const movedNext = (
                        text.includes('finish setting up your page') ||
                        text.includes('conclua a configuração da sua página') ||
                        text.includes('completa la configuración') ||
                        text.includes('customize your page') ||
                        text.includes('personalize sua página') ||
                        text.includes('personaliza tu página') ||
                        text.includes('add profile picture') ||
                        text.includes('add cover photo') ||
                        text.includes('build your page audience') ||
                        text.includes('stay informed about your page') ||
                        (text.includes('website') && (text.includes('phone number') || text.includes('hours'))) ||
                        (url.includes('facebook.com/') && !url.includes('pages/create') && !url.includes('pages/creation'))
                    );
                    if (movedNext) return 'transitioned';

                    // Check if Page Name input disappeared
                    const hasNameInput = !!document.querySelector('input[aria-label*="Page name" i], input[aria-label*="Nome da página" i], input[aria-label*="Nombre de la página" i]');
                    if (!hasNameInput) return 'transitioned';

                    return 'still_screen1';
                }""")
                if status == "rate_limit":
                    self.log("WARNING", f"⚠️ [Tab #{tab_index}] Facebook Page creation rate limit notice for '{page_name}'.")
                    return False
                if status == "transitioned":
                    self.log("SUCCESS", f"🎉 [Tab #{tab_index}] Screen 1 submitted & transitioned cleanly for '{page_name}'!")
                    return True

            self.log("INFO", f"🔄 [Tab #{tab_index}] Screen 1 did not advance yet; retrying 'Next' / 'Create Page'...")

        return False

    # --------------------------------------------------------------------------
    # Phase 3: Step 1 (Contact, Location, Hours)
    # --------------------------------------------------------------------------
    async def _find_input_locator(self, page, terms: List[str]):
        """Finds visible text/url/tel input matching any term."""
        for t in terms:
            for sel in [
                f'input[aria-label*="{t}" i]',
                f'input[placeholder*="{t}" i]',
                f'input[name*="{t}" i]',
                f'label:has-text("{t}") input',
            ]:
                try:
                    loc = page.locator(sel).first
                    if await loc.count() > 0 and await loc.is_visible():
                        return loc
                except Exception:
                    pass
        return None

    async def _fill_input_smart(self, page, terms: List[str], value: str) -> bool:
        """Scrolls vertically cleanly and human-types into matching form input."""
        if not value:
            return False
        loc = await self._find_input_locator(page, terms)
        if loc:
            try:
                await self._human_type_into(page, loc, value, clear_first=True)
                val_now = (await loc.input_value()).strip()
                if val_now == value.strip():
                    return True
            except Exception:
                pass

        try:
            return await page.evaluate("""({ terms, val }) => {
                function setVal(el, v) {
                    if (!el) return false;
                    el.focus();
                    const last = el.value;
                    const proto = Object.getPrototypeOf(el);
                    const desc = Object.getOwnPropertyDescriptor(proto, 'value');
                    if (desc && desc.set) desc.set.call(el, v);
                    else el.value = v;
                    if (el._valueTracker) el._valueTracker.setValue(last);
                    el.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                    el.blur();
                    return true;
                }
                const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"])'));
                for (const inp of inputs) {
                    const r = inp.getBoundingClientRect();
                    if (r.width === 0 || r.height === 0) continue;
                    const aria = (inp.getAttribute('aria-label') || '').toLowerCase();
                    const pl = (inp.getAttribute('placeholder') || '').toLowerCase();
                    const name = (inp.getAttribute('name') || '').toLowerCase();
                    const lbl = ((inp.closest('label') || inp.parentElement || inp).innerText || '').toLowerCase();
                    if (terms.some(t => aria.includes(t) || pl.includes(t) || name.includes(t) || lbl.includes(t))) {
                        return setVal(inp, val);
                    }
                }
                return false;
            }""", {"terms": [t.lower() for t in terms], "val": value})
        except Exception:
            return False

    async def _fill_step1_fields(self, page, tab_index: int, cfg: Dict[str, Any]) -> bool:
        """Fills non-empty Step 1 fields (Website, Phone, Email, Address, City, ZIP, Hours) cleanly."""
        contact = cfg.get("contact", {})
        website = (contact.get("website") or "").strip()
        phone = (contact.get("phone") or "").strip()
        email = (contact.get("email") or "").strip()

        location = cfg.get("location", {})
        address = (location.get("address") or "").strip()
        city = (location.get("city") or "").strip()
        zip_code = (location.get("zip_code") or "").strip()
        hours_mode = cfg.get("hours_mode", "always_open")

        if website:
            self.log("INFO", f"[Tab #{tab_index}] Entering Website: {website}")
            await self._fill_input_smart(page, ['website', 'web site', 'site', 'sitio web', 'página web'], website)
            await self._human_pause(0.35, 0.7)

        if phone:
            self.log("INFO", f"[Tab #{tab_index}] Entering Phone: {phone}")
            await self._fill_input_smart(page, [
                'phone number', 'phone', 'contact number', 'mobile',
                'telefone', 'número de telefone', 'celular', 'teléfono'
            ], phone)
            await self._human_pause(0.35, 0.7)

        if email:
            self.log("INFO", f"[Tab #{tab_index}] Entering Email: {email}")
            await self._fill_input_smart(page, ['email address', 'email', 'e-mail', 'correo electrónico'], email)
            await self._human_pause(0.35, 0.7)

        if address:
            self.log("INFO", f"[Tab #{tab_index}] Entering Address: {address}")
            await self._fill_input_smart(page, ['address', 'street address', 'endereço', 'morada', 'dirección', 'calle'], address)
            await self._human_pause(0.35, 0.7)

        if city:
            self.log("INFO", f"[Tab #{tab_index}] Entering City/town: {city}")
            c_input = await self._find_input_locator(page, [
                'city/town', 'city', 'town', 'cidade/município', 'cidade', 'município', 'ciudad', 'población'
            ])
            if c_input:
                try:
                    await self._human_type_into(page, c_input, city, clear_first=True)
                    c_selected = False
                    for _ in range(10):
                        await asyncio.sleep(0.45)
                        sugg = page.locator('div[role="listbox"] div[role="option"], ul[role="listbox"] li, div[role="option"]').first
                        if await sugg.count() > 0 and await sugg.is_visible():
                            await self._human_move_and_click(page, sugg)
                            c_selected = True
                            self.log("INFO", f"[Tab #{tab_index}] Selected City suggestion for '{city}'.")
                            break
                    if not c_selected:
                        await page.keyboard.press("ArrowDown")
                        await asyncio.sleep(0.25)
                        await page.keyboard.press("Enter")
                except Exception as e:
                    self.log("DEBUG", f"[Tab #{tab_index}] City entry notice: {e}")
            await self._human_pause(0.4, 0.75)

        if zip_code:
            self.log("INFO", f"[Tab #{tab_index}] Entering ZIP code: {zip_code}")
            await self._fill_input_smart(page, ['zip code', 'zip', 'postcode', 'postal code', 'código postal', 'cep'], zip_code)
            await self._human_pause(0.35, 0.7)

        # Hours selection (scoped safely)
        if hours_mode == "selected_hours":
            hour_labels = ["Open at selected hours", "Aberto em horários selecionados", "Abierto en horario seleccionado"]
            target_radio_idx = 2
        elif hours_mode == "no_hours":
            hour_labels = ["No hours available", "Nenhum horário disponível", "No hay horario disponible"]
            target_radio_idx = 0
        else:
            hour_labels = ["Always open", "Sempre aberto", "Aberto sempre", "Siempre abierto"]
            target_radio_idx = 1

        self.log("INFO", f"[Tab #{tab_index}] Selecting Hours: '{hour_labels[0]}'")
        h_selected = False
        for lbl in hour_labels:
            try:
                h_loc = page.locator(f'div[role="radio"]:has-text("{lbl}"), label:has-text("{lbl}"), span:has-text("{lbl}")').first
                if await h_loc.count() > 0 and await h_loc.is_visible():
                    await self._human_move_and_click(page, h_loc)
                    h_selected = True
                    break
            except Exception:
                pass

        if not h_selected:
            try:
                radio_coords = await page.evaluate("""(idx) => {
                    const radios = Array.from(document.querySelectorAll('div[role="radio"], input[type="radio"]')).filter(r => {
                        const rect = r.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0 && !r.closest('[aria-hidden="true"]');
                    });
                    if (radios[idx]) {
                        radios[idx].scrollIntoView({ behavior: 'smooth', block: 'center' });
                        const r = radios[idx].getBoundingClientRect();
                        if (r.width > 2 && r.height > 2) {
                            return { found: true, x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 };
                        }
                        radios[idx].click();
                        return { found: true, x: 0, y: 0 };
                    }
                    return { found: false };
                }""", target_radio_idx)
                if radio_coords and radio_coords.get("found") and radio_coords.get("x"):
                    await asyncio.sleep(0.25)
                    await human_click_coords(page, radio_coords["x"], radio_coords["y"], hover_pause=True)
            except Exception:
                pass

        await self._human_pause(0.6, 1.0)
        return True

    # --------------------------------------------------------------------------
    # Phase 4: Step 2 Photos (Scoped DOM Context + Upload Completion Wait)
    # --------------------------------------------------------------------------
    async def _upload_single_page_photo(self, page, tab_index: int, photo_path: str, kind: str = "profile") -> bool:
        """
        Reliably uploads either 'profile' or 'cover' photo on Step 2 ('Customize your Page').
        Strictly scopes to the Profile card vs Cover card so the wrong slot is NEVER overwritten,
        then waits until Meta CDN upload finishes before continuing.
        """
        if not photo_path or not os.path.isfile(photo_path):
            return False

        is_profile = (kind == "profile")
        label_nice = "Profile Picture" if is_profile else "Cover Photo"
        emoji = "📷" if is_profile else "🖼️"
        self.log("INFO", f"[Tab #{tab_index}] {emoji} Uploading {label_nice}: {os.path.basename(photo_path)}")

        await self._smooth_scroll_wizard_panel(page, "top" if is_profile else "middle")
        await self._human_pause(0.4, 0.8)

        uploaded = False

        # Strategy A: Find dedicated <input type="file"> scoped by ancestor section text (profile vs cover)
        try:
            matched_handle = await page.evaluate_handle("""(wantKind) => {
                const wantProfile = (wantKind === 'profile');
                const profWords = ['profile picture', 'foto do perfil', 'foto de perfil', 'foto del perfil', 'add profile'];
                const covWords = ['cover photo', 'foto de capa', 'foto de portada', 'add cover'];

                const fileInputs = Array.from(document.querySelectorAll('input[type="file"]')).filter(inp => !inp.closest('[aria-hidden="true"]'));

                for (const inp of fileInputs) {
                    let cur = inp.parentElement;
                    for (let depth = 0; depth < 7 && cur; depth++) {
                        const txt = (cur.innerText || cur.getAttribute('aria-label') || '').toLowerCase();
                        const hasProf = profWords.some(w => txt.includes(w));
                        const hasCov = covWords.some(w => txt.includes(w));
                        if (wantProfile && hasProf && !hasCov) return inp;
                        if (!wantProfile && hasCov && !hasProf) return inp;
                        cur = cur.parentElement;
                    }
                }
                return null;
            }""", kind)

            inp_el = matched_handle.as_element() if matched_handle else None
            if inp_el:
                await inp_el.set_input_files(photo_path)
                uploaded = True
                self.log("SUCCESS", f"✅ [Tab #{tab_index}] {label_nice} attached directly to scoped input: {os.path.basename(photo_path)}")
        except Exception as e:
            self.log("DEBUG", f"[Tab #{tab_index}] Scoped file input notice ({kind}): {e}")

        # Strategy B: Click the explicit Profile / Cover upload button & pass file to file chooser
        if not uploaded:
            if is_profile:
                btn_selectors = [
                    'div[aria-label*="profile picture" i][role="button"]',
                    'div[aria-label*="foto do perfil" i][role="button"]',
                    'div[aria-label*="foto de perfil" i][role="button"]',
                    'div[aria-label*="foto del perfil" i][role="button"]',
                    'div[aria-label*="Add profile" i]',
                    'div[aria-label*="Adicionar foto do perfil" i]',
                    'div[role="button"]:has-text("Add profile picture")',
                    'div[role="button"]:has-text("Adicionar foto do perfil")',
                    'div[role="button"]:has-text("Agregar foto del perfil")',
                    'button:has-text("Add profile picture")',
                    'span:has-text("Add profile picture")'
                ]
            else:
                btn_selectors = [
                    'div[aria-label*="cover photo" i][role="button"]',
                    'div[aria-label*="foto de capa" i][role="button"]',
                    'div[aria-label*="foto de portada" i][role="button"]',
                    'div[aria-label*="Add cover" i]',
                    'div[aria-label*="Adicionar foto de capa" i]',
                    'div[role="button"]:has-text("Add cover photo")',
                    'div[role="button"]:has-text("Adicionar foto de capa")',
                    'div[role="button"]:has-text("Agregar foto de portada")',
                    'button:has-text("Add cover photo")',
                    'span:has-text("Add cover photo")'
                ]

            for sel in btn_selectors:
                try:
                    btn = page.locator(sel).first
                    if await btn.count() > 0 and await btn.is_visible():
                        await self._smooth_scroll_vertical_to_element(page, btn)
                        async with page.expect_file_chooser(timeout=8000) as fc_info:
                            await self._human_move_and_click(page, btn)
                        fc = await fc_info.value
                        await fc.set_files(photo_path)
                        uploaded = True
                        self.log("SUCCESS", f"✅ [Tab #{tab_index}] {label_nice} uploaded via chooser: {os.path.basename(photo_path)}")
                        break
                except Exception:
                    pass

        # Strategy C: Fallback positional match on remaining visible-context input[type="file"]
        if not uploaded:
            try:
                pos_handle = await page.evaluate_handle("""(wantKind) => {
                    const fileInputs = Array.from(document.querySelectorAll('input[type="file"]')).filter(inp => !inp.closest('[aria-hidden="true"]'));
                    if (fileInputs.length === 0) return null;
                    if (fileInputs.length === 1) return fileInputs[0];
                    // Sort vertically using closest visible parent rect
                    const withTop = fileInputs.map(inp => {
                        const p = inp.parentElement || inp;
                        return { inp, top: p.getBoundingClientRect().top };
                    }).sort((a, b) => a.top - b.top);
                    return (wantKind === 'profile') ? withTop[0].inp : withTop[withTop.length - 1].inp;
                }""", kind)
                pos_el = pos_handle.as_element() if pos_handle else None
                if pos_el:
                    await pos_el.set_input_files(photo_path)
                    uploaded = True
                    self.log("SUCCESS", f"✅ [Tab #{tab_index}] {label_nice} uploaded via positional input: {os.path.basename(photo_path)}")
            except Exception:
                pass

        if uploaded:
            # Wait cleanly up to 10s for CDN upload spinner to complete & preview to render
            self.log("INFO", f"⏳ [Tab #{tab_index}] Waiting for {label_nice} upload to finish processing...")
            await asyncio.sleep(1.8)
            for _ in range(10):
                done_state = await page.evaluate("""(wantKind) => {
                    const spin = document.querySelector('[role="progressbar"]');
                    if (spin) {
                        const r = spin.getBoundingClientRect();
                        if (r.width > 0 && r.height > 0) return 'uploading';
                    }
                    const txt = (document.body.innerText || '').toLowerCase();
                    if (wantKind === 'profile' && (txt.includes('edit profile picture') || txt.includes('remove profile') || txt.includes('editar foto do perfil'))) {
                        return 'ready';
                    }
                    if (wantKind === 'cover' && (txt.includes('edit cover photo') || txt.includes('remove cover') || txt.includes('editar foto de capa'))) {
                        return 'ready';
                    }
                    return 'settled';
                }""", kind)
                if done_state in ("ready", "settled"):
                    break
                await asyncio.sleep(0.8)
            await self._human_pause(1.2, 2.0)
        else:
            self.log("WARNING", f"⚠️ [Tab #{tab_index}] Could not locate {label_nice} upload control on Step 2.")

        return uploaded

    async def _upload_step2_photos(self, page, tab_index: int, cfg: Dict[str, Any]) -> bool:
        """Uploads assigned profile picture and cover photo sequentially with verification."""
        profile_photo_path = (cfg.get("profile_photo_path") or "").strip()
        cover_photo_path = (cfg.get("cover_photo_path") or "").strip()

        if not profile_photo_path and not cover_photo_path:
            self.log("INFO", f"[Tab #{tab_index}] No profile or cover photos assigned (skipping Step 2 uploads).")
            return True

        if profile_photo_path and os.path.isfile(profile_photo_path):
            await self._upload_single_page_photo(page, tab_index, profile_photo_path, kind="profile")

        if cover_photo_path and os.path.isfile(cover_photo_path):
            await self._upload_single_page_photo(page, tab_index, cover_photo_path, kind="cover")

        return True

    # --------------------------------------------------------------------------
    # Phase 5: Autonomous Human-Like Multi-Step Wizard Runner
    # --------------------------------------------------------------------------
    async def _execute_autonomous_wizard(self, page, tab_index: int, cfg: Dict[str, Any]) -> bool:
        """
        Guides the Facebook Page Setup wizard with human cadence & strict transition checks:
          - Step 1: Finish setting up your Page (Contact, Location, Hours) -> Next (verified)
          - Step 2: Customize your Page (Profile & Cover Photos) -> Next (verified)
          - Step 3: Connect WhatsApp -> Skip / Next
          - Step 4: Build your Page audience -> Next
          - Step 5: Stay informed about your Page -> Done
        """
        self.log("INFO", f"[Tab #{tab_index}] Running human-paced Page Setup Wizard...")

        step1_filled = False
        step2_filled = False
        max_checks = 42

        for _ in range(max_checks):
            if self._is_cancelled:
                return False
            await self._human_pause(1.2, 2.1)
            if self._is_cancelled:
                return False

            # 1. Check if already landed on active Page view
            try:
                curr_url = page.url.lower()
                if "facebook.com" in curr_url and "pages/create" not in curr_url and "pages/creation" not in curr_url and "category=top" not in curr_url:
                    self.log("SUCCESS", f"🎉 [Tab #{tab_index}] Facebook Page is active & ready ({page.url})!")
                    return True
            except Exception:
                pass

            # 2. Dismiss modal tour popups cleanly
            try:
                popup_info = await page.evaluate("""() => {
                    const dismissTerms = ['not now', 'agora não', 'agora nao', 'ahora no', 'close', 'fechar', 'cerrar'];
                    const btns = Array.from(document.querySelectorAll('div[role="dialog"] button, div[role="dialog"] div[role="button"]'));
                    for (const b of btns) {
                        const r = b.getBoundingClientRect();
                        if (r.width === 0 || r.height === 0) continue;
                        const txt = (b.innerText || b.getAttribute('aria-label') || '').trim().toLowerCase();
                        if (dismissTerms.some(t => txt === t)) {
                            return { found: true, x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 };
                        }
                    }
                    return { found: false };
                }""")
                if popup_info and popup_info.get("found"):
                    if popup_info.get("x") and popup_info.get("y"):
                        await human_click_coords(page, popup_info["x"], popup_info["y"], hover_pause=True)
                    self.log("INFO", f"[Tab #{tab_index}] Dismissed onboarding popup.")
                    await self._human_pause(0.8, 1.4)
            except Exception:
                pass

            try:
                body_text = await page.evaluate("() => (document.body.innerText || '').toLowerCase()")
            except Exception:
                body_text = ""

            # Stage: Still on Screen 1 unexpectedly? Try submitting cleanly
            if await self._is_initial_form_screen(page):
                await self._find_and_click_wizard_footer_button(page, "create_or_next", tab_index=tab_index)
                await self._human_pause(1.5, 2.5)
                continue

            # Stage: Step 1 (Finish setting up your Page - Contact, Location, Hours)
            is_step1 = any(term in body_text for term in [
                "finish setting up your page", "conclua a configuração da sua página",
                "concluir a configuração", "completa la configuración", "conclua a configuracao"
            ]) or (any(c in body_text for c in ["contact", "contato", "contacto"]) and
                   any(w in body_text for w in ["website", "site", "web site", "phone number"]))

            if is_step1:
                if not step1_filled:
                    self.log("INFO", f"[Tab #{tab_index}] 📝 Step 1: Entering Contact, Location & Hours...")
                    await self._fill_step1_fields(page, tab_index, cfg)
                    step1_filled = True
                    await self._human_pause(0.7, 1.3)

                self.log("INFO", f"[Tab #{tab_index}] Clicking 'Next' to proceed from Step 1...")
                await self._find_and_click_wizard_footer_button(page, "next", tab_index=tab_index)
                await self._human_pause(1.8, 2.8)
                continue

            # Stage: Step 2 (Customize your Page - Profile Picture & Cover Photo)
            is_step2 = any(term in body_text for term in [
                "customize your page", "personalize sua página", "personalize sua pagina",
                "personaliza tu página", "add profile picture", "adicionar foto do perfil",
                "adicionar foto de perfil", "adicionar foto de capa", "add cover photo",
                "edit profile picture", "edit cover photo"
            ])
            if is_step2:
                if not step2_filled:
                    self.log("INFO", f"[Tab #{tab_index}] 🖼️ Step 2: Uploading Profile Picture & Cover Photo...")
                    await self._upload_step2_photos(page, tab_index, cfg)
                    step2_filled = True
                    await self._human_pause(0.8, 1.4)

                self.log("INFO", f"[Tab #{tab_index}] Clicking 'Next' to proceed from Customize Page...")
                await self._find_and_click_wizard_footer_button(page, "next", tab_index=tab_index)
                await self._human_pause(1.8, 2.8)
                continue

            # Stage: WhatsApp Connect -> Skip (or Next)
            if "whatsapp" in body_text and not any(t in body_text for t in ["build your page audience", "stay informed"]):
                self.log("INFO", f"[Tab #{tab_index}] ⏩ WhatsApp step detected: Skipping cleanly...")
                skipped = await self._find_and_click_wizard_footer_button(page, "skip", tab_index=tab_index)
                if not skipped:
                    await self._find_and_click_wizard_footer_button(page, "next", tab_index=tab_index)
                await self._human_pause(1.6, 2.6)
                continue

            # Stage: Build your Page audience / Invite Friends -> Next
            if any(term in body_text for term in [
                "build your page audience", "criar o público da sua página",
                "crea la audiencia", "invite friends", "convidar amigos", "invitar amigos"
            ]):
                self.log("INFO", f"[Tab #{tab_index}] 👥 Audience step detected: Clicking 'Next'...")
                await self._find_and_click_wizard_footer_button(page, "next", tab_index=tab_index)
                await self._human_pause(1.6, 2.6)
                continue

            # Stage: Final Step ('Stay informed' / 'Done' / 'Save')
            is_final = any(term in body_text for term in [
                "stay informed", "fique por dentro", "mantente informado"
            ])
            if is_final or await self._find_and_click_wizard_footer_button(page, "done", tab_index=tab_index):
                if is_final:
                    self.log("INFO", f"[Tab #{tab_index}] 🏁 Final step detected: Clicking 'Done'...")
                    await self._find_and_click_wizard_footer_button(page, "done", tab_index=tab_index)
                self.log("SUCCESS", f"🎉 [Tab #{tab_index}] Clicked 'Done'! Waiting for new Page to load...")
                await self._human_pause(2.5, 4.0)
                return True

            # Generic next fallback
            if await self._find_and_click_wizard_footer_button(page, "next", tab_index=tab_index):
                await self._human_pause(1.5, 2.5)

        self.log("INFO", f"✅ [Tab #{tab_index}] Wizard sequence finished.")
        return True

    async def _complete_single_tab_lifecycle(self, page, tab_index: int, cfg: Dict[str, Any], delay_seconds: float) -> Dict[str, Any]:
        """Runs a realistic staggered Screen 1 submit -> Wizard flow for a single tab."""
        p_name = cfg.get("name", f"New Page {tab_index}")
        p_cat = cfg.get("category", "Digital Creator")

        # Natural human stagger before clicking Create Page/Next across tabs
        await self._human_pause(0.6 * (tab_index - 1), 1.4 * (tab_index - 1) + 0.5)
        if self._is_cancelled:
            return {"account": self.account_name, "name": p_name, "category": p_cat, "url": "", "status": "Cancelled"}

        created_ok = await self._submit_screen1_and_verify(page, tab_index, p_name)
        if not created_ok and not self._is_cancelled:
            return {"account": self.account_name, "name": p_name, "category": p_cat, "url": page.url, "status": "Failed"}

        wizard_ok = await self._execute_autonomous_wizard(page, tab_index, cfg)
        final_url = ""
        try:
            if page and not page.is_closed():
                final_url = page.url
        except Exception:
            pass

        return {
            "account": self.account_name,
            "name": p_name,
            "category": p_cat,
            "url": final_url,
            "status": "Created" if wizard_ok else ("Cancelled" if self._is_cancelled else "Failed")
        }

    # --------------------------------------------------------------------------
    # Main Orchestrator
    # --------------------------------------------------------------------------
    async def create_pages_workflow(
        self,
        page_configs: List[Dict[str, Any]],
        delay_seconds: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Executes multi-tab Page creation with human-like cadence:
          1. Opens N tabs cleanly
          2. Navigates & dismisses Public Page prompt
          3. Human-types Name, Category, Bio in each tab
          4. Staggers 'Create Page' / 'Next' submission naturally & verifies Screen 1 advance
          5. Runs Step 1 (Contact/Location/Hours -> Next), Step 2 (Profile & Cover -> Next), and Finalize (Skip/Next/Done)
        """
        results: List[Dict[str, Any]] = []
        if not page_configs:
            self.log("WARNING", "No page configurations provided.")
            return results

        num_tabs = len(page_configs)
        self.log("INFO", f"🚀 Starting Human-Like Facebook Page Creator across {num_tabs} tab(s)...")

        try:
            await self.init_browser()
            if not self.context or self._is_cancelled:
                if not self.context:
                    self.log("ERROR", "Failed to launch browser context.")
                return results

            pages = []
            first_work_p = await get_bot_working_page(self.context)
            if first_work_p:
                pages.append(first_work_p)

            while len(pages) < num_tabs and not self._is_cancelled:
                new_p = await self.context.new_page()
                pages.append(new_p)
                await self._human_pause(0.3, 0.7)

            if self._is_cancelled:
                return results

            self.log("INFO", f"🌐 Opened {len(pages)} tab(s). Navigating to Facebook Pages Create...")
            for idx, p in enumerate(pages):
                if self._is_cancelled:
                    return results
                await p.bring_to_front()
                await self._handle_create_modal_and_navigate(p, idx + 1)

            if self._is_cancelled:
                return results
            await self._human_pause(max(0.8, delay_seconds * 0.5), max(1.6, delay_seconds))

            # Fill Screen 1 naturally tab-by-tab (human brings tab to front, types Name/Category/Bio)
            self.log("INFO", "✍️ Typing Page Name, Category & Bio across tabs with human cadence...")
            for idx, (p, cfg) in enumerate(zip(pages, page_configs)):
                if self._is_cancelled:
                    return results
                await p.bring_to_front()
                await self._fill_page_form(
                    p,
                    idx + 1,
                    cfg.get("name", f"New Page {idx + 1}"),
                    cfg.get("category", "Digital Creator"),
                    cfg.get("bio", "")
                )

            if self._is_cancelled:
                return results

            # Submit Screen 1 & complete wizard cleanly tab-by-tab so mouse moves & uploads never collide across tabs!
            self.log("INFO", "🧙 Completing 'Next' → Details → Profile/Cover Photos → 'Done' seamlessly for each page...")
            for idx, (p, cfg) in enumerate(zip(pages, page_configs)):
                if self._is_cancelled:
                    break
                await p.bring_to_front()
                res = await self._complete_single_tab_lifecycle(p, idx + 1, cfg, delay_seconds)
                results.append(res)
                pct = int(((idx + 1) / max(1, len(pages))) * 100)
                self.set_progress(pct)
                if idx + 1 < len(pages) and not self._is_cancelled:
                    await human_idle_drift(p)
                    await self._human_pause(max(1.5, delay_seconds * 0.6), max(3.0, delay_seconds * 1.2))

            self.log("SUCCESS", f"🏁 Finished Page Creation for {self.account_name} ({sum(1 for r in results if r.get('status') == 'Created')}/{len(results)} created).")
            if not self._is_cancelled:
                await self._human_pause(1.8, 2.8)
            return results
        finally:
            await self.close()

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
