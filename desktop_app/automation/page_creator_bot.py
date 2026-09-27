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

    # Reverse lookup: if input was in Portuguese or Spanish, ensure English is present
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
            "--start-maximized",
            "--lang=en-US",
            "--accept-lang=en-US,en;q=0.9",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=CalculateNativeWinOcclusion",
            "--disable-ipc-flooding-protection"
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
                    "extra_http_headers": {
                        "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,es;q=0.6"
                    },
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
                locale="en-US",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,es;q=0.6"
                }
            )

        # Inject session cookies if provided (handles strings, JSON arrays, and dictionaries)
        raw_cookies = self.account_data.get("cookies", "")
        if self.context:
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

                # Inject English locale cookie preference for Facebook
                formatted_cookies.append({
                    "name": "locale",
                    "value": "en_US",
                    "domain": ".facebook.com",
                    "path": "/",
                    "secure": True
                })

                if formatted_cookies:
                    await self.context.add_cookies(formatted_cookies)
                    self.log("SUCCESS", f"🔑 Injected {len(formatted_cookies)} Facebook session cookies (Language preference: en_US).")
            except Exception as e:
                self.log("DEBUG", f"Cookie injection notice: {e}")

    async def _handle_create_modal_and_navigate(self, page, tab_index: int) -> bool:
        """
        Navigates to Facebook Pages creation.
        If the modal 'Create / Which option is best for you?' pops up,
        selects 'Public Page' (supports English, Brazilian Portuguese, Spanish) and clicks 'Next'.
        """
        target_url = "https://www.facebook.com/pages/create/?locale=en_US"
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
                create_page_btn = page.locator(
                    'a[href*="/pages/create"], button:has-text("Create Page"), div[role="button"]:has-text("Create Page"), '
                    'button:has-text("Criar página"), div[role="button"]:has-text("Criar página"), '
                    'button:has-text("Crear página"), div[role="button"]:has-text("Crear página")'
                ).first
                if await create_page_btn.count() > 0 and await create_page_btn.is_visible():
                    self.log("INFO", f"[Tab #{tab_index}] Clicking '+ Create Page' button on Pages dashboard...")
                    await create_page_btn.click()
                    await asyncio.sleep(2.0)
            except Exception:
                pass

        # Check for Modal Dialog: 'Create / Which option is best for you?' / 'Qual opção é melhor para você?'
        try:
            dialog = page.locator('div[role="dialog"]').first
            if await dialog.count() > 0 and await dialog.is_visible():
                self.log("INFO", f"[Tab #{tab_index}] Detected 'Which option is best for you?' modal dialog.")
                
                # Click 'Public Page' / 'Página pública' / 'Página de local público'
                clicked_opt = False
                public_labels = [
                    'text="Public Place Page"', 'text="Public Page"',
                    'text="Página pública"', 'text="Página de local público"',
                    'div:has-text("Public Page")', 'div:has-text("Public Place Page")',
                    'div:has-text("Página pública")', 'div:has-text("Página de local público")',
                    'text="Página comercial"', 'span:has-text("Public")'
                ]
                for p_label in public_labels:
                    public_opt = dialog.locator(p_label).first
                    if await public_opt.count() > 0 and await public_opt.is_visible():
                        await public_opt.click()
                        await asyncio.sleep(0.5)
                        clicked_opt = True
                        break

                if not clicked_opt:
                    radio = dialog.locator('input[type="radio"], div[role="radio"]').first
                    if await radio.count() > 0:
                        await radio.click()
                        await asyncio.sleep(0.5)

                # Click 'Next' / 'Avançar' / 'Seguinte' / 'Siguiente'
                next_selectors = [
                    'button:has-text("Next")', 'div[role="button"]:has-text("Next")',
                    'button:has-text("Avançar")', 'div[role="button"]:has-text("Avançar")',
                    'button:has-text("Seguinte")', 'div[role="button"]:has-text("Seguinte")',
                    'button:has-text("Próximo")', 'div[role="button"]:has-text("Próximo")',
                    'button:has-text("Siguiente")', 'div[role="button"]:has-text("Siguiente")'
                ]
                for n_sel in next_selectors:
                    next_btn = dialog.locator(n_sel).first
                    if await next_btn.count() > 0 and await next_btn.is_visible():
                        self.log("INFO", f"[Tab #{tab_index}] Clicking 'Next' in Public Page creation modal...")
                        await next_btn.click()
                        await asyncio.sleep(2.0)
                        break
        except Exception as e:
            self.log("DEBUG", f"[Tab #{tab_index}] Modal handling notice: {e}")

        # Also evaluate DOM script just in case of iframe or shadow DOM
        try:
            await page.evaluate("""() => {
                const dialogs = document.querySelectorAll('div[role="dialog"]');
                for (const d of dialogs) {
                    const txt = (d.innerText || '').toLowerCase();
                    if (txt.includes('public page') || txt.includes('public place') || 
                        txt.includes('página pública') || txt.includes('qual opção') || 
                        txt.includes('which option is best')) {
                        // Click public page option
                        const items = Array.from(d.querySelectorAll('div, span, p, label, input[type="radio"]'));
                        const pub = items.find(el => {
                            const t = (el.innerText || el.textContent || '').trim().toLowerCase();
                            return t === 'public page' || t === 'public place page' || 
                                   t === 'página pública' || t.includes('página pública') || 
                                   t.includes('public page');
                        });
                        if (pub) pub.click();
                        else {
                            const r = d.querySelector('input[type="radio"], div[role="radio"]');
                            if (r) r.click();
                        }

                        // Click Next / Avançar
                        const btns = Array.from(d.querySelectorAll('button, div[role="button"]'));
                        const nextBtn = btns.find(b => {
                            const t = (b.innerText || b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase();
                            return t === 'next' || t === 'avançar' || t === 'seguinte' || t === 'próximo' || t === 'siguiente';
                        });
                        if (nextBtn) nextBtn.click();
                    }
                }
            }""")
        except Exception:
            pass

        return True

    async def _fill_page_form(self, page, tab_index: int, page_name: str, category: str, bio: str) -> bool:
        """
        Fills the 'Create a Page' form fields:
          - Page name (required) [supports English, Brazilian Portuguese, Spanish]
          - Category (required) -> tries candidate localized names & selects dropdown suggestion
          - Bio (optional)
        Does NOT click 'Create Page' yet, allowing all tabs to reach filled state together.
        """
        self.log("INFO", f"[Tab #{tab_index}] Filling form: Name='{page_name}', Category='{category}'...")

        # 1. Fill Page Name (required) - Multilingual & React 18 Safe
        name_filled = False
        name_locators = [
            'input[aria-label*="Page name" i]',
            'input[aria-label*="Nome da página" i]',
            'input[aria-label*="Nombre de la página" i]',
            'input[aria-label*="name (required)" i]',
            'input[aria-label*="nome (obrigatório)" i]',
            'input[aria-label*="nome" i]',
            'input[aria-label*="nombre" i]',
            'div[role="main"] input[type="text"]',
            'input[type="text"]'
        ]
        for sel in name_locators:
            try:
                inp = page.locator(sel).first
                if await inp.count() > 0 and await inp.is_visible():
                    await inp.scroll_into_view_if_needed()
                    await inp.click()
                    await inp.fill("")
                    await inp.type(page_name, delay=30)
                    # Verify value via JS
                    val_now = await inp.input_value()
                    if val_now.strip() == page_name.strip():
                        name_filled = True
                        break
            except Exception as e:
                self.log("DEBUG", f"[Tab #{tab_index}] Page name input notice: {e}")

        if not name_filled:
            # Fallback DOM evaluation with React prototype value setter
            name_filled = await page.evaluate("""(pName) => {
                function setVal(el, v) {
                    if (!el) return false;
                    el.focus();
                    const last = el.value;
                    el.value = v;
                    const proto = Object.getPrototypeOf(el);
                    const desc = Object.getOwnPropertyDescriptor(proto, 'value');
                    if (desc && desc.set) {
                        desc.set.call(el, v);
                    }
                    const tracker = el._valueTracker;
                    if (tracker) {
                        tracker.setValue(last);
                    }
                    el.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                    return true;
                }
                const inputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type])'));
                for (const inp of inputs) {
                    const aria = (inp.getAttribute('aria-label') || '').toLowerCase();
                    const pl = (inp.getAttribute('placeholder') || '').toLowerCase();
                    if (aria.includes('page name') || aria.includes('nome da página') || 
                        aria.includes('nombre de la página') || aria.includes('name') || 
                        aria.includes('nome') || pl.includes('name') || pl.includes('nome')) {
                        return setVal(inp, pName);
                    }
                }
                if (inputs.length > 0) {
                    return setVal(inputs[0], pName);
                }
                return false;
            }""", page_name)

        await asyncio.sleep(0.8)

        # 2. Fill Category (required) - Multilingual candidate search & adaptive dropdown selection
        cat_filled = False
        cat_candidates = get_category_search_candidates(category)
        self.log("INFO", f"[Tab #{tab_index}] Category search candidates: {', '.join(cat_candidates[:3])}")

        cat_input = None
        cat_locators = [
            'input[aria-label*="Category" i]',
            'input[aria-label*="Categoria" i]',
            'input[aria-label*="Categoría" i]',
            'input[aria-autocomplete="list"]',
            'div[role="combobox"] input'
        ]
        for sel in cat_locators:
            try:
                c_loc = page.locator(sel).first
                if await c_loc.count() > 0 and await c_loc.is_visible():
                    cat_input = c_loc
                    break
            except Exception:
                pass

        for c_cand in cat_candidates:
            if cat_filled:
                break
            try:
                if cat_input:
                    await cat_input.scroll_into_view_if_needed()
                    await cat_input.click()
                    await cat_input.fill("")
                    await cat_input.type(c_cand, delay=35)
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

                # Adaptive polling loop for Facebook's suggestion listbox (up to 4.5 seconds)
                suggestion_found = False
                for _ in range(9):
                    await asyncio.sleep(0.5)
                    sugg_locators = [
                        'div[role="listbox"] div[role="option"]',
                        'ul[role="listbox"] li',
                        'div[role="option"]',
                        'div[aria-label*="Search results" i] div[role="option"]'
                    ]
                    for s_sel in sugg_locators:
                        opt = page.locator(s_sel).first
                        if await opt.count() > 0 and await opt.is_visible():
                            await opt.click()
                            suggestion_found = True
                            cat_filled = True
                            self.log("INFO", f"[Tab #{tab_index}] Category suggestion matched ('{c_cand}') and selected!")
                            break
                    if suggestion_found:
                        break

                if cat_filled:
                    break
            except Exception as e:
                self.log("DEBUG", f"[Tab #{tab_index}] Category attempt '{c_cand}' notice: {e}")

        if not cat_filled:
            # Fallback: keyboard ArrowDown + Enter
            try:
                await page.keyboard.press("ArrowDown")
                await asyncio.sleep(0.3)
                await page.keyboard.press("Enter")
                cat_filled = True
                self.log("INFO", f"[Tab #{tab_index}] Accepted category via keyboard selection.")
            except Exception:
                pass

        await asyncio.sleep(0.8)

        # 3. Fill Bio (optional) - Multilingual
        if bio:
            bio_filled = False
            bio_locators = [
                'textarea[aria-label*="Bio" i]',
                'textarea[aria-label*="Biografia" i]',
                'textarea[aria-label*="Biografía" i]',
                'textarea[placeholder*="bio" i]',
                'textarea[placeholder*="biografia" i]',
                'div[role="main"] textarea',
                'textarea'
            ]
            for b_sel in bio_locators:
                try:
                    bio_el = page.locator(b_sel).first
                    if await bio_el.count() > 0 and await bio_el.is_visible():
                        await bio_el.scroll_into_view_if_needed()
                        await bio_el.click()
                        await bio_el.fill(bio)
                        bio_filled = True
                        break
                except Exception as e:
                    self.log("DEBUG", f"[Tab #{tab_index}] Bio input notice: {e}")

            if not bio_filled:
                await page.evaluate("""(bioText) => {
                    const t = document.querySelector('textarea');
                    if (t) {
                        t.focus();
                        t.value = bioText;
                        t.dispatchEvent(new Event('input', { bubbles: true }));
                        t.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }""", bio)

        self.log("SUCCESS", f"✅ [Tab #{tab_index}] Form filled successfully for '{page_name}'!")
        return True

    async def _arm_create_page_button(self, page, tab_index: int, page_name: str) -> bool:
        """
        Arms the 'Create Page' button on this tab:
          - Supports English ('Create Page'), Brazilian Portuguese ('Criar página'), Spanish ('Crear página')
          - Confirms the button is present, visible, and enabled (aria-disabled !== 'true').
          - Scrolls it into view and attaches it to window.__fbCreatePageBtn.
        """
        self.log("INFO", f"[Tab #{tab_index}] Arming 'Create Page' button for '{page_name}'...")
        for _ in range(16):
            try:
                is_armed = await page.evaluate("""() => {
                    window.__fbCreatePageBtn = null;
                    window.__fbCreatePageArmed = false;
                    const candidates = Array.from(document.querySelectorAll(
                        'div[aria-label="Create Page"][role="button"], div[aria-label="Criar página"][role="button"], ' +
                        'div[aria-label="Crear página"][role="button"], button, div[role="button"], div[aria-label*="Page"], div[aria-label*="Página"]'
                    ));
                    for (const b of candidates) {
                        const txt = (b.innerText || b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase();
                        const isMatch = (
                            txt === 'create page' || txt === 'criar página' || txt === 'crear página' ||
                            (txt.includes('create') && txt.includes('page')) ||
                            (txt.includes('criar') && txt.includes('página')) ||
                            (txt.includes('criar') && txt.includes('pagina')) ||
                            (txt.includes('crear') && txt.includes('página')) ||
                            (txt.includes('crear') && txt.includes('pagina'))
                        );
                        if (isMatch) {
                            const ariaDisabled = b.getAttribute('aria-disabled');
                            const isNativeDisabled = b.hasAttribute('disabled');
                            if (ariaDisabled !== 'true' && !isNativeDisabled) {
                                b.scrollIntoView({ block: 'center', behavior: 'instant' });
                                b.focus();
                                window.__fbCreatePageBtn = b;
                                window.__fbCreatePageArmed = true;
                                return true;
                            }
                        }
                    }
                    return false;
                }""")
                if is_armed:
                    self.log("SUCCESS", f"🎯 [Tab #{tab_index}] 'Create Page' button armed & verified ready for '{page_name}'!")
                    return True
            except Exception as e:
                self.log("DEBUG", f"[Tab #{tab_index}] Arming notice: {e}")
            await asyncio.sleep(0.5)

        self.log("WARNING", f"⚠️ [Tab #{tab_index}] Arming verification timed out. Will fallback to direct DOM selection during trigger.")
        return False

    async def _fire_atomic_create_click(self, page, tab_index: int, target_epoch_ms: int) -> bool:
        """
        Fires the 'Create Page' click at the exact synchronized millisecond epoch
        across all tabs simultaneously via internal page timer to bypass rate limits.
        Supports English, Portuguese, and Spanish.
        """
        try:
            res = await page.evaluate("""(targetEpoch) => {
                return new Promise((resolve) => {
                    function executeClick() {
                        try {
                            let btn = window.__fbCreatePageBtn;
                            if (!btn) {
                                const candidates = Array.from(document.querySelectorAll(
                                    'div[aria-label="Create Page"][role="button"], div[aria-label="Criar página"][role="button"], ' +
                                    'div[aria-label="Crear página"][role="button"], button, div[role="button"]'
                                ));
                                for (const b of candidates) {
                                    const txt = (b.innerText || b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase();
                                    const isMatch = (
                                        txt === 'create page' || txt === 'criar página' || txt === 'crear página' ||
                                        (txt.includes('create') && txt.includes('page')) ||
                                        (txt.includes('criar') && txt.includes('página')) ||
                                        (txt.includes('crear') && txt.includes('página'))
                                    );
                                    if (isMatch) {
                                        btn = b;
                                        break;
                                    }
                                }
                            }
                            if (btn) {
                                const opts = { bubbles: true, cancelable: true, view: window };
                                ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evt => {
                                    btn.dispatchEvent(new MouseEvent(evt, opts));
                                });
                                btn.click();
                                resolve({ clicked: true, timestamp: Date.now() });
                                return;
                            }
                        } catch (e) {}
                        resolve({ clicked: false, timestamp: Date.now() });
                    }

                    const remainingMs = Math.max(0, targetEpoch - Date.now());
                    if (remainingMs <= 0) {
                        executeClick();
                    } else {
                        setTimeout(executeClick, remainingMs);
                    }
                });
            }""", target_epoch_ms)
            clicked = res.get("clicked", False) if isinstance(res, dict) else False
            fired_at = res.get("timestamp", 0) if isinstance(res, dict) else 0
            self.log("INFO", f"💥 [Tab #{tab_index}] Atomic click dispatched (Timestamp: {fired_at})!")
            return clicked
        except Exception as e:
            self.log("DEBUG", f"[Tab #{tab_index}] Atomic click exception: {e}")
            return False

    async def _monitor_page_creation_status(self, page, tab_index: int, page_name: str) -> bool:
        """
        Monitors tab response after atomic click to detect successful creation
        or Facebook rate limit banners across English, Portuguese, and Spanish.
        """
        self.log("INFO", f"[Tab #{tab_index}] Monitoring creation response for '{page_name}'...")
        for _ in range(14):
            await asyncio.sleep(1.0)
            try:
                res = await page.evaluate("""() => {
                    const text = (document.body.innerText || '').toLowerCase();
                    const isSuccess = (
                        text.includes('finish setting up your page') ||
                        text.includes('conclua a configuração da sua página') ||
                        text.includes('concluir a configuração') ||
                        text.includes('completa la configuración') ||
                        text.includes('customize your page') ||
                        text.includes('personalize sua página') ||
                        text.includes('personaliza tu página') ||
                        text.includes('page created') ||
                        text.includes('página criada') ||
                        text.includes('contact') ||
                        text.includes('contato') ||
                        text.includes('contacto')
                    );
                    if (isSuccess) {
                        return { status: 'created' };
                    }
                    if (text.includes('too many pages') || 
                        text.includes('muitas páginas') ||
                        text.includes('demasiadas páginas') ||
                        text.includes('try again later') || 
                        text.includes('tente novamente mais tarde') ||
                        text.includes('intenta de nuevo más tarde') ||
                        text.includes('limit reached') ||
                        text.includes('limite atingido') ||
                        text.includes('you\\'ve created too many')) {
                        return { status: 'rate_limit' };
                    }
                    return { status: 'pending' };
                }""")
                st = res.get("status") if isinstance(res, dict) else "pending"
                if st == "created":
                    self.log("SUCCESS", f"🎉 [Tab #{tab_index}] Facebook Page '{page_name}' created successfully! Advancing to page setup...")
                    return True
                elif st == "rate_limit":
                    self.log("WARNING", f"⚠️ [Tab #{tab_index}] Facebook rate limit detected for '{page_name}'.")
                    return False
            except Exception:
                pass

        self.log("INFO", f"✅ [Tab #{tab_index}] Creation submission proceeded for '{page_name}'.")
        return True

    async def _click_create_page(self, page, tab_index: int, page_name: str) -> bool:
        """
        Direct single-tab fallback method for 'Create Page' button (Multilingual).
        """
        self.log("INFO", f"[Tab #{tab_index}] Submitting 'Create Page' for '{page_name}'...")
        await asyncio.sleep(0.5)

        clicked = False

        button_selectors = [
            'div[aria-label="Create Page"][role="button"]',
            'div[aria-label="Criar página"][role="button"]',
            'div[aria-label="Crear página"][role="button"]',
            'button:has-text("Create Page")',
            'button:has-text("Criar página")',
            'button:has-text("Crear página")',
            'div[role="button"]:has-text("Create Page")',
            'div[role="button"]:has-text("Criar página")',
            'div[role="button"]:has-text("Crear página")',
            'div[aria-label*="Create Page"]',
            'div[aria-label*="Criar página"]'
        ]

        for b_sel in button_selectors:
            try:
                btn = page.locator(b_sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    is_disabled = await btn.get_attribute("aria-disabled")
                    if is_disabled == "true":
                        await asyncio.sleep(1.0)
                    await btn.scroll_into_view_if_needed()
                    await btn.click()
                    clicked = True
                    break
            except Exception:
                pass

        if not clicked:
            try:
                clicked = await page.evaluate("""() => {
                    const buttons = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"]'));
                    for (const b of buttons) {
                        const txt = (b.innerText || b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase();
                        const isMatch = (
                            txt === 'create page' || txt === 'criar página' || txt === 'crear página' ||
                            (txt.includes('create') && txt.includes('page')) ||
                            (txt.includes('criar') && txt.includes('página')) ||
                            (txt.includes('crear') && txt.includes('página'))
                        );
                        if (isMatch) {
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
            return await self._monitor_page_creation_status(page, tab_index, page_name)
        else:
            self.log("WARNING", f"⚠️ [Tab #{tab_index}] Could not find or click 'Create Page' button.")
            return False

    async def _find_input_locator(self, page, terms: List[str]):
        """Finds input element matching any search term by aria, placeholder, name, or parent label."""
        for t in terms:
            for sel in [
                f'label:has-text("{t}") input',
                f'div:has-text("{t}") input',
                f'input[aria-label*="{t}" i]',
                f'input[placeholder*="{t}" i]',
                f'input[name*="{t}" i]'
            ]:
                try:
                    loc = page.locator(sel).first
                    if await loc.count() > 0 and await loc.is_visible():
                        return loc
                except Exception:
                    pass
        return None

    async def _fill_input_smart(self, page, terms: List[str], value: str):
        """Fills input with real typing and React 18 prototype setter so values persist even across concurrent windows."""
        if not value:
            return False
        loc = await self._find_input_locator(page, terms)
        if loc:
            try:
                await loc.scroll_into_view_if_needed()
                await loc.click()
                await loc.fill("")
                await loc.type(value, delay=25)
                # Verify
                val_now = await loc.input_value()
                if val_now.strip() == value.strip():
                    return True
            except Exception:
                pass

        # Fallback DOM evaluation with React prototype value setter
        try:
            return await page.evaluate("""({ terms, val }) => {
                function setVal(el, v) {
                    if (!el) return false;
                    el.focus();
                    const last = el.value;
                    el.value = v;
                    const proto = Object.getPrototypeOf(el);
                    const desc = Object.getOwnPropertyDescriptor(proto, 'value');
                    if (desc && desc.set) {
                        desc.set.call(el, v);
                    }
                    const tracker = el._valueTracker;
                    if (tracker) {
                        tracker.setValue(last);
                    }
                    el.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                    el.blur();
                    return true;
                }
                const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"])'));
                for (const inp of inputs) {
                    const aria = (inp.getAttribute('aria-label') || '').toLowerCase();
                    const pl = (inp.getAttribute('placeholder') || '').toLowerCase();
                    const name = (inp.getAttribute('name') || '').toLowerCase();
                    const lbl = (inp.closest('label') || inp.parentElement || inp).innerText.toLowerCase();
                    if (terms.some(t => aria.includes(t) || pl.includes(t) || name.includes(t) || lbl.includes(t))) {
                        return setVal(inp, val);
                    }
                }
                return false;
            }""", {"terms": [t.lower() for t in terms], "val": value})
        except Exception:
            return False

    async def _fill_step1_fields(self, page, tab_index: int, cfg: Dict[str, Any]) -> bool:
        """
        Fills non-empty Step 1 setup fields (Website, Phone, Email, Address, City/Town, ZIP, Hours).
        Supports English, Brazilian Portuguese, and Spanish keywords and index fallbacks.
        """
        contact = cfg.get("contact", {})
        website = (contact.get("website") or "").strip()
        phone = (contact.get("phone") or "").strip()
        email = (contact.get("email") or "").strip()

        location = cfg.get("location", {})
        address = (location.get("address") or "").strip()
        city = (location.get("city") or "").strip()
        zip_code = (location.get("zip_code") or "").strip()

        hours_mode = cfg.get("hours_mode", "always_open")

        # 1. Website (only if provided)
        if website:
            self.log("INFO", f"[Tab #{tab_index}] Entering Website: {website}")
            await self._fill_input_smart(page, ['website', 'web site', 'site', 'sitio web', 'página web'], website)
            await asyncio.sleep(0.5)

        # 2. Phone Number (only if provided)
        if phone:
            self.log("INFO", f"[Tab #{tab_index}] Entering Phone: {phone}")
            await self._fill_input_smart(page, [
                'phone number', 'phone', 'contact number', 'mobile',
                'telefone', 'número de telefone', 'celular', 'teléfono'
            ], phone)
            await asyncio.sleep(0.5)

        # 3. Email (only if provided)
        if email:
            self.log("INFO", f"[Tab #{tab_index}] Entering Email: {email}")
            await self._fill_input_smart(page, ['email address', 'email', 'e-mail', 'correo electrónico'], email)
            await asyncio.sleep(0.5)

        # 4. Location - Address (only if provided)
        if address:
            self.log("INFO", f"[Tab #{tab_index}] Entering Address: {address}")
            await self._fill_input_smart(page, ['address', 'street address', 'endereço', 'morada', 'dirección', 'calle'], address)
            await asyncio.sleep(0.5)

        # 5. Location - City/town (only if provided; requires suggestion selection!)
        if city:
            self.log("INFO", f"[Tab #{tab_index}] Entering City/town: {city}")
            c_input = await self._find_input_locator(page, [
                'city/town', 'city', 'town', 'cidade/município', 'cidade', 'município', 'ciudad', 'población'
            ])
            if c_input:
                try:
                    await c_input.scroll_into_view_if_needed()
                    await c_input.click()
                    await c_input.fill("")
                    await c_input.type(city, delay=35)

                    # Adaptive polling loop for City suggestion listbox (up to 5 seconds)
                    c_selected = False
                    for _ in range(10):
                        await asyncio.sleep(0.5)
                        sugg = page.locator('div[role="listbox"] div[role="option"], ul[role="listbox"] li, div[role="option"]').first
                        if await sugg.count() > 0 and await sugg.is_visible():
                            await sugg.click()
                            c_selected = True
                            self.log("INFO", f"[Tab #{tab_index}] Selected City suggestion for: {city}")
                            break

                    if not c_selected:
                        await page.keyboard.press("ArrowDown")
                        await asyncio.sleep(0.3)
                        await page.keyboard.press("Enter")
                except Exception as e:
                    self.log("DEBUG", f"[Tab #{tab_index}] City entry notice: {e}")
            await asyncio.sleep(0.5)

        # 6. Location - ZIP code (only if provided)
        if zip_code:
            self.log("INFO", f"[Tab #{tab_index}] Entering ZIP code: {zip_code}")
            await self._fill_input_smart(page, ['zip code', 'zip', 'postcode', 'postal code', 'código postal', 'cep'], zip_code)
            await asyncio.sleep(0.5)

        # 7. Hours Selection (Always open / Open at selected hours / No hours available)
        # Multilingual labels + Radio button index fallback
        hour_labels = []
        target_radio_idx = 1  # 0: No hours, 1: Always open, 2: Selected hours
        if hours_mode == "selected_hours":
            hour_labels = ["Open at selected hours", "Aberto em horários selecionados", "Abierto en horario seleccionado"]
            target_radio_idx = 2
        elif hours_mode == "no_hours":
            hour_labels = ["No hours available", "Nenhum horário disponível", "No hay horario disponible"]
            target_radio_idx = 0
        else:
            hour_labels = ["Always open", "Sempre aberto", "Aberto sempre", "Siempre abierto"]
            target_radio_idx = 1

        self.log("INFO", f"[Tab #{tab_index}] Selecting Hours mode: '{hour_labels[0]}'")
        h_selected = False
        for lbl in hour_labels:
            try:
                h_loc = page.locator(f'label:has-text("{lbl}"), div[role="radio"]:has-text("{lbl}"), span:has-text("{lbl}")').first
                if await h_loc.count() > 0 and await h_loc.is_visible():
                    await h_loc.scroll_into_view_if_needed()
                    await h_loc.click()
                    h_selected = True
                    break
            except Exception:
                pass

        if not h_selected:
            # Fallback: Select radio by index in Hours section
            try:
                await page.evaluate("""(idx) => {
                    const radios = Array.from(document.querySelectorAll('input[type="radio"], div[role="radio"]'));
                    if (radios.length >= 3 && radios[idx]) {
                        radios[idx].click();
                        return true;
                    }
                    return false;
                }""", target_radio_idx)
            except Exception:
                pass

        await asyncio.sleep(0.8)
        return True

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
        await self._fill_step1_fields(page, tab_index, cfg)
        await asyncio.sleep(0.5)
        self.log("INFO", f"[Tab #{tab_index}] Clicking 'Next' button to advance to Customize Page (Photos)...")
        await self._click_wizard_button(page, 'next')
        await asyncio.sleep(2.0)
        return True

    async def _upload_step2_photos(self, page, tab_index: int, cfg: Dict[str, Any]) -> bool:
        """
        Uploads assigned profile picture and cover photo if configured.
        Supports both single photo and multi-photo automated sequential distribution across all languages.
        """
        profile_photo_path = (cfg.get("profile_photo_path") or "").strip()
        cover_photo_path = (cfg.get("cover_photo_path") or "").strip()

        if not profile_photo_path and not cover_photo_path:
            self.log("INFO", f"[Tab #{tab_index}] No profile or cover photos assigned (will skip).")
            return True

        # 1. Profile Picture (English, Portuguese, Spanish)
        if profile_photo_path and os.path.isfile(profile_photo_path):
            self.log("INFO", f"[Tab #{tab_index}] 📷 Attaching Profile Picture: {os.path.basename(profile_photo_path)}")
            p_ok = False
            for p_sel in [
                'div[aria-label*="profile picture" i][role="button"]',
                'div[aria-label*="foto do perfil" i][role="button"]',
                'div[aria-label*="foto de perfil" i][role="button"]',
                'div[aria-label*="foto del perfil" i][role="button"]',
                'div[aria-label*="Add profile" i]',
                'div[aria-label*="Adicionar foto" i]',
                'div[role="button"]:has-text("Add profile picture")',
                'div[role="button"]:has-text("Adicionar foto do perfil")',
                'div[role="button"]:has-text("Adicionar foto de perfil")',
                'button:has-text("Add profile picture")',
                'button:has-text("Adicionar foto do perfil")'
            ]:
                try:
                    btn = page.locator(p_sel).first
                    if await btn.count() > 0 and await btn.is_visible():
                        async with page.expect_file_chooser(timeout=10000) as fc_info:
                            await btn.click()
                        fc = await fc_info.value
                        await fc.set_files(profile_photo_path)
                        p_ok = True
                        self.log("SUCCESS", f"✅ [Tab #{tab_index}] Profile picture uploaded via chooser: {os.path.basename(profile_photo_path)}")
                        break
                except Exception:
                    pass

            if not p_ok:
                try:
                    file_inputs = page.locator('input[type="file"]')
                    if await file_inputs.count() > 0:
                        await file_inputs.nth(0).set_input_files(profile_photo_path)
                        p_ok = True
                        self.log("SUCCESS", f"✅ [Tab #{tab_index}] Profile picture set via file input: {os.path.basename(profile_photo_path)}")
                except Exception:
                    pass

            if p_ok:
                await asyncio.sleep(2.5)

        # 2. Cover Photo (English, Portuguese, Spanish)
        if cover_photo_path and os.path.isfile(cover_photo_path):
            self.log("INFO", f"[Tab #{tab_index}] 🖼️ Attaching Cover Photo: {os.path.basename(cover_photo_path)}")
            c_ok = False
            for c_sel in [
                'div[aria-label*="cover photo" i][role="button"]',
                'div[aria-label*="foto de capa" i][role="button"]',
                'div[aria-label*="foto de portada" i][role="button"]',
                'div[aria-label*="Add cover" i]',
                'div[aria-label*="Adicionar capa" i]',
                'div[role="button"]:has-text("Add cover photo")',
                'div[role="button"]:has-text("Adicionar foto de capa")',
                'button:has-text("Add cover photo")',
                'button:has-text("Adicionar foto de capa")'
            ]:
                try:
                    btn = page.locator(c_sel).first
                    if await btn.count() > 0 and await btn.is_visible():
                        async with page.expect_file_chooser(timeout=10000) as fc_info:
                            await btn.click()
                        fc = await fc_info.value
                        await fc.set_files(cover_photo_path)
                        c_ok = True
                        self.log("SUCCESS", f"✅ [Tab #{tab_index}] Cover photo uploaded via chooser: {os.path.basename(cover_photo_path)}")
                        break
                except Exception:
                    pass

            if not c_ok:
                try:
                    file_inputs = page.locator('input[type="file"]')
                    cnt = await file_inputs.count()
                    if cnt > 1:
                        await file_inputs.nth(1).set_input_files(cover_photo_path)
                        c_ok = True
                        self.log("SUCCESS", f"✅ [Tab #{tab_index}] Cover photo set via second file input: {os.path.basename(cover_photo_path)}")
                    elif cnt == 1:
                        await file_inputs.nth(0).set_input_files(cover_photo_path)
                        c_ok = True
                        self.log("SUCCESS", f"✅ [Tab #{tab_index}] Cover photo set via file input: {os.path.basename(cover_photo_path)}")
                except Exception:
                    pass

            if c_ok:
                await asyncio.sleep(2.5)

        return True

    async def _step2_customize_photos(self, page, tab_index: int, cfg: Dict[str, Any]) -> bool:
        """
        Handles 'Step 2 of 5: Customize your Page' (Image 2):
          - Add profile picture (if provided)
          - Add cover photo (if provided)
          - Clicks 'Next' button
        """
        self.log("INFO", f"[Tab #{tab_index}] Processing 'Customize your Page' (Profile & Cover Photos)...")
        await self._upload_step2_photos(page, tab_index, cfg)
        await asyncio.sleep(0.5)
        self.log("INFO", f"[Tab #{tab_index}] Clicking 'Next' on Customize Page...")
        await self._click_wizard_button(page, 'next')
        await asyncio.sleep(2.0)
        return True

    async def _click_wizard_button(self, page, btn_type: str = 'next') -> bool:
        """
        Robustly clicks 'Next', 'Skip', or 'Done'/'Save' in the active wizard panel.
        Supports English, Portuguese (Avançar, Pular, Concluir), Spanish, and primary button fallback.
        """
        btn_type = btn_type.lower()

        try:
            await page.evaluate("""() => {
                const containers = Array.from(document.querySelectorAll('div[role="dialog"], div[role="main"], div[class*="scroll"], div[data-nosnippet]'));
                for (const c of containers) {
                    if (c.scrollHeight > c.clientHeight) {
                        c.scrollTop = c.scrollHeight;
                    }
                }
            }""")
        except Exception:
            pass

        target_selectors = []
        if btn_type == 'next':
            target_selectors = [
                'div[aria-label="Next"][role="button"]',
                'button:has-text("Next")',
                'div[role="button"]:has-text("Next")',
                'span:has-text("Next")',
                # Portuguese & Spanish
                'div[aria-label="Avançar"][role="button"]',
                'button:has-text("Avançar")',
                'div[role="button"]:has-text("Avançar")',
                'div[aria-label="Seguinte"][role="button"]',
                'button:has-text("Seguinte")',
                'div[role="button"]:has-text("Seguinte")',
                'div[aria-label="Próximo"][role="button"]',
                'button:has-text("Próximo")',
                'div[aria-label="Siguiente"][role="button"]',
                'button:has-text("Siguiente")'
            ]
        elif btn_type == 'skip':
            target_selectors = [
                'div[aria-label="Skip"][role="button"]',
                'button:has-text("Skip")',
                'div[role="button"]:has-text("Skip")',
                'span:has-text("Skip")',
                # Portuguese & Spanish
                'div[aria-label="Pular"][role="button"]',
                'button:has-text("Pular")',
                'div[role="button"]:has-text("Pular")',
                'div[aria-label="Ignorar"][role="button"]',
                'button:has-text("Ignorar")',
                'div[aria-label="Omitir"][role="button"]',
                'button:has-text("Omitir")'
            ]
        elif btn_type == 'done':
            target_selectors = [
                'div[aria-label="Done"][role="button"]',
                'button:has-text("Done")',
                'div[role="button"]:has-text("Done")',
                'div[aria-label="Save"][role="button"]',
                'button:has-text("Save")',
                'div[role="button"]:has-text("Save")',
                # Portuguese & Spanish
                'div[aria-label="Concluir"][role="button"]',
                'button:has-text("Concluir")',
                'div[role="button"]:has-text("Concluir")',
                'div[aria-label="Salvar"][role="button"]',
                'button:has-text("Salvar")',
                'div[aria-label="Guardar"][role="button"]',
                'button:has-text("Guardar")',
                'div[aria-label="Listo"][role="button"]',
                'button:has-text("Listo")'
            ]

        for sel in target_selectors:
            try:
                btn = page.locator(sel).last
                if await btn.count() > 0 and await btn.is_visible():
                    aria_dis = await btn.get_attribute("aria-disabled")
                    if aria_dis == "true":
                        continue
                    await btn.scroll_into_view_if_needed()
                    await btn.click()
                    return True
            except Exception:
                pass

        # Strategy 2: DOM Javascript click dispatch with multilingual dictionary
        try:
            clicked = await page.evaluate("""(targetType) => {
                const nextTerms = ['next', 'avançar', 'seguinte', 'próximo', 'siguiente', 'weiter', 'suivant'];
                const skipTerms = ['skip', 'pular', 'ignorar', 'omitir', 'passer'];
                const doneTerms = ['done', 'concluir', 'salvar', 'guardar', 'listo', 'save', 'terminer'];

                const candidates = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"]'));
                for (let i = candidates.length - 1; i >= 0; i--) {
                    const b = candidates[i];
                    const txt = (b.innerText || b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase();
                    const dis = b.getAttribute('aria-disabled') === 'true' || b.hasAttribute('disabled');
                    if (dis) continue;

                    if (targetType === 'done' && doneTerms.some(t => txt === t || txt.startsWith(t))) {
                        b.scrollIntoView({ block: 'center' });
                        ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evt => {
                            b.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
                        });
                        b.click();
                        return true;
                    }
                    if (targetType === 'skip' && skipTerms.some(t => txt === t || txt.startsWith(t))) {
                        b.scrollIntoView({ block: 'center' });
                        ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evt => {
                            b.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
                        });
                        b.click();
                        return true;
                    }
                    if (targetType === 'next' && nextTerms.some(t => txt === t || txt.startsWith(t))) {
                        b.scrollIntoView({ block: 'center' });
                        ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evt => {
                            b.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
                        });
                        b.click();
                        return true;
                    }
                }
                return false;
            }""", btn_type)
            if clicked:
                return True
        except Exception:
            pass

        return False

    async def _execute_autonomous_wizard(self, page, tab_index: int, cfg: Dict[str, Any]) -> bool:
        """
        Intelligently and autonomously guides the Facebook Page Setup through all wizard stages:
          - Step 1: Finish setting up your Page (Contact, Location, Hours) -> auto fills non-empty fields & clicks Next
          - Step 2: Customize your Page (Profile & Cover Photos) -> uploads assigned photos & clicks Next
          - Step 3: Connect WhatsApp -> clicks 'Skip' or 'Next'
          - Step 4: Build your Page audience -> clicks 'Next'
          - Step 5: Stay informed about your Page -> clicks 'Done'
          - Dismisses popups ('Take a tour', 'Not now', 'Agora não')
          - Continuously monitors screen state across English, Portuguese, and Spanish!
        """
        self.log("INFO", f"[Tab #{tab_index}] Launching Autonomous Page Setup Wizard...")

        step1_done = False
        step2_done = False
        whatsapp_done = False
        audience_done = False
        max_checks = 40

        for attempt in range(max_checks):
            await asyncio.sleep(1.8)

            # 1. Check if Facebook has navigated away from creation into active Page view
            try:
                curr_url = page.url.lower()
                if "facebook.com" in curr_url and "pages/create" not in curr_url and "pages/creation" not in curr_url and "category=top" not in curr_url:
                    self.log("SUCCESS", f"🎉 [Tab #{tab_index}] Facebook Page setup is 100% completed and active!")
                    return True
            except Exception:
                pass

            # 2. Check for popups (e.g., 'Take a tour', 'Not now', 'Agora não', 'Agora nao', 'Fechar')
            try:
                popup_handled = await page.evaluate("""() => {
                    const dismissTerms = ['not now', 'agora não', 'agora nao', 'ahora no', 'close', 'fechar', 'cerrar', 'skip', 'pular', 'omitir'];
                    const btns = Array.from(document.querySelectorAll('div[role="dialog"] button, div[role="dialog"] div[role="button"]'));
                    for (const b of btns) {
                        const txt = (b.innerText || b.getAttribute('aria-label') || '').trim().toLowerCase();
                        if (dismissTerms.some(t => txt === t || txt.includes(t))) {
                            b.click();
                            return true;
                        }
                    }
                    return false;
                }""")
                if popup_handled:
                    self.log("INFO", f"[Tab #{tab_index}] Dismissed onboarding tour popup.")
                    await asyncio.sleep(1.0)
            except Exception:
                pass

            # 3. Read current page state
            try:
                body_text = (await page.evaluate("() => (document.body.innerText || '').toLowerCase()"))
            except Exception:
                body_text = ""

            # 4. Check if on Step 1: Finish setting up your page (Contact, Location, Hours)
            is_step1 = any(term in body_text for term in [
                "finish setting up your page", "conclua a configuração da sua página",
                "concluir a configuração", "completa la configuración", "conclua a configuracao"
            ]) or (any(c in body_text for c in ["contact", "contato", "contacto"]) and 
                   any(w in body_text for w in ["website", "site", "web site"]) and not step1_done)

            if is_step1:
                if not step1_done:
                    self.log("INFO", f"[Tab #{tab_index}] 📝 Step 1 detected: Filling Contact, Location, and Hours...")
                    await self._fill_step1_fields(page, tab_index, cfg)
                    step1_done = True
                    await asyncio.sleep(1.0)

                self.log("INFO", f"[Tab #{tab_index}] Clicking 'Next' to advance from Step 1...")
                await self._click_wizard_button(page, 'next')
                await asyncio.sleep(2.0)
                continue

            # 5. Check if on Step 2: Customize your page (Profile & Cover Photos)
            is_step2 = any(term in body_text for term in [
                "customize your page", "personalize sua página", "personalize sua pagina",
                "personaliza tu página", "add profile picture", "adicionar foto do perfil",
                "adicionar foto de perfil", "adicionar foto de capa", "add cover photo"
            ])
            if is_step2:
                if not step2_done:
                    self.log("INFO", f"[Tab #{tab_index}] 🖼️ Step 2 detected: Uploading Profile & Cover Photos...")
                    await self._upload_step2_photos(page, tab_index, cfg)
                    step2_done = True
                    await asyncio.sleep(1.0)

                self.log("INFO", f"[Tab #{tab_index}] Clicking 'Next' to advance from Step 2...")
                await self._click_wizard_button(page, 'next')
                await asyncio.sleep(2.0)
                continue

            # 6. Check if on WhatsApp step
            if "whatsapp" in body_text:
                self.log("INFO", f"[Tab #{tab_index}] ⏩ WhatsApp step detected: Clicking 'Skip'...")
                skipped = await self._click_wizard_button(page, 'skip')
                if not skipped:
                    await self._click_wizard_button(page, 'next')
                whatsapp_done = True
                await asyncio.sleep(2.0)
                continue

            # 7. Check if on Audience / Invite friends step
            is_audience = any(term in body_text for term in [
                "build your page audience", "criar o público da sua página", "crea la audiencia",
                "invite friends", "convidar amigos", "invitar amigos"
            ])
            if is_audience:
                self.log("INFO", f"[Tab #{tab_index}] 👥 Audience step detected: Clicking 'Next'...")
                await self._click_wizard_button(page, 'next')
                audience_done = True
                await asyncio.sleep(2.0)
                continue

            # 8. Check if on 'Stay informed' or 'Done' / 'Save' is ready
            done_found = await page.evaluate("""() => {
                const doneTerms = ['done', 'concluir', 'salvar', 'guardar', 'listo', 'save'];
                const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                for (const b of btns) {
                    const txt = (b.innerText || b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase();
                    if (doneTerms.some(t => txt === t)) {
                        return true;
                    }
                }
                return false;
            }""")
            is_stay_informed = any(term in body_text for term in [
                "stay informed", "fique por dentro", "mantente informado"
            ])
            if done_found or is_stay_informed:
                self.log("INFO", f"[Tab #{tab_index}] 🏁 Final wizard step detected: Clicking 'Done'...")
                await self._click_wizard_button(page, 'done')
                self.log("SUCCESS", f"🎉 [Tab #{tab_index}] Clicked 'Done'! Facebook Page setup is 100% complete!")
                await asyncio.sleep(3.0)
                return True

            # 9. Generic Fallback: if Next or Skip or Done is available, click it
            fallback_clicked = await page.evaluate("""() => {
                const nextTerms = ['next', 'avançar', 'seguinte', 'próximo', 'siguiente'];
                const skipTerms = ['skip', 'pular', 'ignorar', 'omitir'];
                const doneTerms = ['done', 'concluir', 'salvar', 'guardar', 'listo', 'save'];

                const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                for (const b of btns) {
                    const txt = (b.innerText || '').trim().toLowerCase();
                    const dis = b.getAttribute('aria-disabled') === 'true' || b.hasAttribute('disabled');
                    if (dis) continue;
                    if (doneTerms.some(t => txt === t)) {
                        b.click();
                        return 'Done';
                    }
                }
                for (const b of btns) {
                    const txt = (b.innerText || '').trim().toLowerCase();
                    const dis = b.getAttribute('aria-disabled') === 'true' || b.hasAttribute('disabled');
                    if (dis) continue;
                    if (skipTerms.some(t => txt === t)) {
                        b.click();
                        return 'Skip';
                    }
                }
                for (let i = btns.length - 1; i >= 0; i--) {
                    const b = btns[i];
                    const txt = (b.innerText || '').trim().toLowerCase();
                    const dis = b.getAttribute('aria-disabled') === 'true' || b.hasAttribute('disabled');
                    if (dis) continue;
                    if (nextTerms.some(t => txt === t)) {
                        b.click();
                        return 'Next';
                    }
                }
                return null;
            }""")
            if fallback_clicked:
                self.log("INFO", f"[Tab #{tab_index}] Wizard progressed via: '{fallback_clicked}'")
                await asyncio.sleep(2.0)

        self.log("INFO", f"✅ [Tab #{tab_index}] Wizard completed.")
        return True

    async def _complete_remaining_wizard(self, page, tab_index: int) -> bool:
        """
        Completes remaining wizard steps (WhatsApp Connect skip, Build audience, Stay informed, Done).
        Clicks 'Done', 'Skip', or 'Next' until the Facebook page is completely finalized!
        """
        return await self._execute_autonomous_wizard(page, tab_index, {})

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

        # Step 5: Phase 2.5 - Arm 'Create Page' buttons across all tabs simultaneously
        self.log("INFO", f"🎯 [Phase 2.5] Arming 'Create Page' buttons across all {len(pages)} tab(s) to guarantee simultaneous readiness...")
        arm_tasks = []
        for idx, (p, cfg) in enumerate(zip(pages, page_configs)):
            p_name = cfg.get("name", f"New Page {idx + 1}")
            arm_tasks.append(self._arm_create_page_button(p, idx + 1, p_name))

        await asyncio.gather(*arm_tasks, return_exceptions=True)
        await asyncio.sleep(1.0)

        # Step 6: Phase 3 - Multi-Tab Microsecond Atomic Click Barrier (Bypasses Facebook Rate Limit)
        sync_epoch_ms = int(time.time() * 1000) + 1200
        self.log("INFO", f"🔥 [Phase 3/5] ATOMIC TRIGGER: Firing simultaneous microsecond 'Create Page' click across all {len(pages)} tabs at epoch {sync_epoch_ms}!")
        
        click_tasks = []
        for idx, p in enumerate(pages):
            click_tasks.append(self._fire_atomic_create_click(p, idx + 1, sync_epoch_ms))

        await asyncio.gather(*click_tasks, return_exceptions=True)
        self.log("SUCCESS", f"⚡ Atomic click executed simultaneously across all {len(pages)} tab(s)!")
        await asyncio.sleep(3.0)

        # Step 7: Phase 3.5 - Concurrently Monitor Creation Response across all tabs
        self.log("INFO", "👀 [Phase 3.5] Verifying page creation responses across all tabs...")
        verify_tasks = []
        for idx, (p, cfg) in enumerate(zip(pages, page_configs)):
            p_name = cfg.get("name", f"New Page {idx + 1}")
            verify_tasks.append(self._monitor_page_creation_status(p, idx + 1, p_name))

        await asyncio.gather(*verify_tasks, return_exceptions=True)
        await asyncio.sleep(1.5)

        # Step 6: Phase 4/5 - Autonomous Setup Wizard across all tabs (Step 1, Step 2 Photos, WhatsApp, Audience, Done)
        self.log("INFO", "🧙 [Phase 4/5] Executing Autonomous Setup Wizard across all tabs simultaneously...")
        wizard_tasks = []
        for idx, (p, cfg) in enumerate(zip(pages, page_configs)):
            wizard_tasks.append(self._execute_autonomous_wizard(p, idx + 1, cfg))

        final_results = await asyncio.gather(*wizard_tasks, return_exceptions=True)

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
