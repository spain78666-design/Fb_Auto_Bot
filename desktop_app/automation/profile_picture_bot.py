"""
FB Auto Bot - Facebook Profile & Cover Photo Bulk Updater Engine
Automates high-speed, stealth profile picture and cover photo updating across multiple Facebook accounts
with intelligent file pooling, Spintax/randomization, multilingual support (EN, PT, ES, UR),
robust error recovery, and automatic Chrome closure.
"""

import os
import sys
import json
import socket
import asyncio
import logging
import random
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Callable

try:
    from automation.browser_window_manager import (
        resolve_tile_context,
        build_window_chrome_args,
        apply_cdp_window_bounds,
        launch_bot_browser_context,
        get_bot_working_page,
        human_move_and_click,
        human_click_coords,
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
            human_move_and_click,
            human_click_coords,
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
        async def human_pause(low=0.55, high=1.45, mult=1.0):
            await asyncio.sleep(random.uniform(low, high) * mult)
        async def human_session_warmup(page, duration_range=(1.2, 2.3), log_cb=None):
            await asyncio.sleep(1.0)
        async def human_idle_drift(page):
            await asyncio.sleep(0.25)

logger = logging.getLogger("FBAutoBot.ProfilePictureBot")

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


class FacebookProfilePictureBot:
    """
    Automates uploading Profile Picture and Cover Photo for a target Facebook account.
    Launches Chrome with persistent stealth profile/cookies, navigates to the user's profile,
    attaches the profile photo and saves, attaches the cover photo and saves,
    and cleanly closes Chrome when finished.
    """

    def __init__(
        self,
        account_data: Dict[str, Any],
        profile_photo_path: str = "",
        cover_photo_path: str = "",
        action_delay: float = 5.0,
        log_callback: Optional[Callable[[str, str], None]] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        counter_callback: Optional[Callable[[str, int], None]] = None
    ):
        self.account_data = account_data
        self.profile_photo_path = profile_photo_path if (profile_photo_path and os.path.isfile(profile_photo_path)) else ""
        self.cover_photo_path = cover_photo_path if (cover_photo_path and os.path.isfile(cover_photo_path)) else ""
        self.action_delay = max(2.0, action_delay)

        self.log_cb = log_callback
        self.prog_cb = progress_callback
        self.counter_cb = counter_callback

        self.account_id = str(account_data.get("id", "unknown"))
        self.account_name = str(account_data.get("name", "Facebook Account"))

        self.playwright = None
        self.browser = None
        self.context = None
        self._cancelled = False

    def log(self, level: str, message: str):
        full_msg = f"[{self.account_name}] {message}"
        if self.log_cb:
            self.log_cb(level, full_msg)
        else:
            print(f"[{level}] {full_msg}")

    def cancel(self):
        self._cancelled = True
        self.log("WARNING", "🛑 Stop command received. Terminating Profile Picture Bot...")

    async def _init_browser(self):
        """Initializes stealth Chrome instance with tiled window, profile/cookies, and background throttling prevention."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed in the system environment.")

        self.playwright = await async_playwright().start()

        slot_idx, total_slots, tile_rect = resolve_tile_context(self.account_data)
        chrome_profile_directory = (self.account_data.get("chrome_profile_directory") or "").strip() or None
        is_custom_profile = bool(self.account_data.get("is_custom_chrome_profile", False))

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
            "--accept-lang=en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,es;q=0.6"
        ]
        launch_args.extend(
            build_window_chrome_args(
                tile_rect=tile_rect,
                total_slots=total_slots,
                slot_index=slot_idx,
                profile_directory=chrome_profile_directory,
            )
        )

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

        context_kwargs: Dict[str, Any] = {
            "viewport": None,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "locale": "en-US",
            "extra_http_headers": {
                "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,es;q=0.6"
            }
        }

        profile_dir = self.account_data.get("profile_dir", "")
        self.context, self.browser = await launch_bot_browser_context(
            playwright=self.playwright,
            account_data=self.account_data,
            profile_dir=profile_dir,
            launch_args=launch_args,
            ignore_default_args=["--enable-automation", "--disable-extensions"],
            proxy_cfg=proxy_cfg,
            context_kwargs=context_kwargs,
            log_cb=self.log,
            allow_ephemeral_fallback=not is_custom_profile,
        )

        if self.context:
            p0 = self.context.pages[0] if self.context.pages else await self.context.new_page()
            await apply_cdp_window_bounds(
                self.context,
                p0,
                tile_rect=tile_rect,
                total_slots=total_slots,
                slot_index=slot_idx,
            )

        # Inject session cookies (preserve existing custom Chrome profile session when cookies empty)
        raw_cookies = self.account_data.get("cookies", "")
        if self.context and (raw_cookies or not is_custom_profile):
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

                if not is_custom_profile:
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
        elif is_custom_profile:
            self.log("INFO", "📂 Using existing Chrome profile Facebook login session directly.")

    async def _dismiss_popups_and_modals(self, page: Page):
        """
        Safely dismisses blocking notification/restriction popups across languages
        WITHOUT ever closing an active Profile Picture / Cover Photo upload or crop modal,
        and protects against accidental 'Leave page / Still uploading' discard clicks.
        """
        try:
            await page.evaluate("""() => {
                const dialogs = Array.from(document.querySelectorAll('div[role="dialog"], div[aria-modal="true"], div[role="alertdialog"]'));
                for (const d of dialogs) {
                    const txt = (d.innerText || d.textContent || '').toLowerCase();

                    // 1. Protect active photo/upload/crop modals — NEVER click Close (X) on them
                    const isUploadOrCropModal = Boolean(
                        d.querySelector('input[type="file"]') ||
                        d.querySelector('[role="progressbar"]') ||
                        txt.includes('update profile picture') ||
                        txt.includes('choose profile picture') ||
                        txt.includes('edit profile picture') ||
                        txt.includes('mettre à jour la photo') ||
                        txt.includes('atualizar foto') ||
                        txt.includes('actualizar foto') ||
                        txt.includes('upload photo') ||
                        txt.includes('make temporary') ||
                        txt.includes('description') && (txt.includes('save') || txt.includes('enregistrer') || txt.includes('salvar') || txt.includes('guardar'))
                    );
                    if (isUploadOrCropModal) {
                        continue;
                    }

                    // 2. If Facebook warns 'Still uploading / Leave page / Discard changes?', click Stay/Cancel (NOT Discard/Leave)
                    const isLeaveWarning = (
                        txt.includes('still uploading') ||
                        txt.includes('leave page') ||
                        txt.includes('discard changes') ||
                        txt.includes('unsaved changes') ||
                        txt.includes('photo is still')
                    );
                    if (isLeaveWarning) {
                        const btns = Array.from(d.querySelectorAll('button, div[role="button"]'));
                        for (const b of btns) {
                            const bt = (b.innerText || b.textContent || '').trim().toLowerCase();
                            if (bt === 'stay' || bt === 'cancel' || bt === 'keep editing' || bt === 'keep' || bt === 'annuler' || bt === 'cancelar') {
                                if (b.offsetParent !== null) { b.click(); return true; }
                            }
                        }
                        continue;
                    }

                    // 3. Dismiss genuine restriction/notification banners safely
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
                                           txt.includes('alerta') ||
                                           txt.includes('not now') ||
                                           txt.includes('cookie');

                    if (isWarningPopup) {
                        const closeBtns = Array.from(d.querySelectorAll('div[aria-label="Close"], button[aria-label="Close"], div[role="button"][aria-label="Close"], [aria-label*="Fechar" i], [aria-label*="Cerrar" i], button, div[role="button"]'));
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

    async def _update_profile_picture(self, page: Page, photo_path: str) -> bool:
        """
        Uploads and saves the profile picture across ALL Facebook account languages:
        (French, Portuguese, Spanish, German, Italian, Turkish, Arabic, Urdu, Russian, English)
        1. Finds and clicks the camera/edit icon on the profile avatar
        2. Uploads the image via FileChooser or direct file input
        3. Waits for preview & enabled 'Save' button (never clicking prematurely)
        4. Waits until upload progressbar & dialog close cleanly on their own
        """
        file_name = os.path.basename(photo_path)
        self.log("INFO", f"📷 Uploading Profile Picture: {file_name}...")

        await self._dismiss_popups_and_modals(page)

        # Look for Avatar Camera / Edit Profile Picture Button (Universal Multilingual & Structural)
        avatar_btn_selectors = [
            # English
            'div[aria-label*="Update profile picture" i][role="button"]',
            'div[aria-label*="Update profile picture" i]',
            'div[aria-label*="Update your profile photo" i]',
            'div[aria-label*="Edit profile picture" i]',
            'div[aria-label*="Add profile picture" i]',
            # French
            'div[aria-label*="Mettre à jour la photo de profil" i][role="button"]',
            'div[aria-label*="Mettre à jour la photo de profil" i]',
            'div[aria-label*="Modifier la photo de profil" i]',
            'div[aria-label*="Ajouter une photo de profil" i]',
            'div[aria-label*="Changer la photo de profil" i]',
            # Portuguese (Brazilian & European)
            'div[aria-label*="Atualizar foto do perfil" i][role="button"]',
            'div[aria-label*="Atualizar foto do perfil" i]',
            'div[aria-label*="Editar foto do perfil" i]',
            'div[aria-label*="Adicionar foto do perfil" i]',
            'div[aria-label*="Carregar foto do perfil" i]',
            # Spanish
            'div[aria-label*="Actualizar foto del perfil" i][role="button"]',
            'div[aria-label*="Actualizar foto de perfil" i]',
            'div[aria-label*="Editar foto del perfil" i]',
            'div[aria-label*="Agregar foto del perfil" i]',
            'div[aria-label*="Subir foto del perfil" i]',
            # German & Italian
            'div[aria-label*="Profilbild aktualisieren" i]',
            'div[aria-label*="Profilbild bearbeiten" i]',
            'div[aria-label*="Aggiorna immagine del profilo" i]',
            'div[aria-label*="Modifica immagine del profilo" i]',
            # Generic / Class / SVG Camera icons
            'div[role="button"][data-visualcompletion*="css-img"]',
            'div[role="button"]:has(svg[aria-label*="camera" i])',
            'div[role="button"]:has(svg[aria-label*="Camera" i])',
            'div[role="button"]:has(svg[aria-label*="photo" i])',
            'div[role="button"]:has(svg[aria-label*="appareil photo" i])',
            'div[role="button"]:has(svg[aria-label*="câmera" i])',
            'div[role="button"]:has(svg[aria-label*="cámara" i])'
        ]

        clicked_avatar = False
        for a_sel in avatar_btn_selectors:
            try:
                btn = page.locator(a_sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    if await human_move_and_click(page, btn):
                        clicked_avatar = True
                        self.log("INFO", "👉 Clicked avatar camera icon smoothly.")
                        await asyncio.sleep(random.uniform(1.8, 2.6))
                        break
            except Exception:
                pass

        if not clicked_avatar:
            # Universal DOM coordinate fallback + human click for avatar camera button
            try:
                avatar_coords = await page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('div[role="button"], button, svg'));
                    const keywords = [
                        'update profile picture', 'edit profile picture', 'add profile picture',
                        'mettre à jour la photo de profil', 'modifier la photo de profil', 'ajouter une photo de profil', 'changer la photo de profil',
                        'atualizar foto do perfil', 'editar foto do perfil', 'adicionar foto do perfil',
                        'actualizar foto del perfil', 'actualizar foto de perfil', 'editar foto del perfil', 'agregar foto del perfil',
                        'profilbild aktualisieren', 'profilbild bearbeiten', 'aggiorna immagine del profilo'
                    ];
                    for (const b of btns) {
                        const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                        const title = (b.getAttribute('title') || '').toLowerCase();
                        if (keywords.some(k => aria.includes(k) || title.includes(k))) {
                            const clickable = b.closest('div[role="button"], button') || b;
                            if (clickable && clickable.offsetParent !== null) {
                                clickable.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                const r = clickable.getBoundingClientRect();
                                if (r.width > 4 && r.height > 4) {
                                    return { found: true, x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 };
                                }
                            }
                        }
                    }
                    const avatarImgs = Array.from(document.querySelectorAll('image, img[alt*="profile" i], img[alt*="profil" i], img[alt*="perfil" i]'));
                    for (const img of avatarImgs) {
                        const container = img.closest('div[role="button"]') || img.parentElement?.querySelector('div[role="button"]');
                        if (container && container.offsetParent !== null) {
                            container.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            const r = container.getBoundingClientRect();
                            if (r.width > 4 && r.height > 4) {
                                return { found: true, x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 };
                            }
                        }
                    }
                    return { found: false };
                }""")
                if avatar_coords and avatar_coords.get("found"):
                    await asyncio.sleep(0.25)
                    clicked_avatar = await human_click_coords(page, avatar_coords["x"], avatar_coords["y"])
                    if clicked_avatar:
                        self.log("INFO", "👉 Clicked avatar camera icon cleanly.")
                        await asyncio.sleep(random.uniform(1.8, 2.6))
            except Exception:
                pass

        # Attach file inside dialog via FileChooser or direct dialog input
        file_attached = False
        upload_btn_selectors = [
            # English
            'div[role="dialog"] div[role="button"]:has-text("Upload Photo")',
            'div[role="dialog"] button:has-text("Upload Photo")',
            'div[role="dialog"] div[role="button"]:has-text("Upload photo")',
            'div[role="dialog"] button:has-text("Upload photo")',
            # French
            'div[role="dialog"] div[role="button"]:has-text("Importer une photo")',
            'div[role="dialog"] button:has-text("Importer une photo")',
            'div[role="dialog"] div[role="button"]:has-text("Télécharger une photo")',
            'div[role="dialog"] button:has-text("Télécharger une photo")',
            'div[role="dialog"] div[role="button"]:has-text("Ajouter une photo")',
            'div[role="dialog"] button:has-text("Ajouter une photo")',
            # Portuguese
            'div[role="dialog"] div[role="button"]:has-text("Carregar foto")',
            'div[role="dialog"] button:has-text("Carregar foto")',
            'div[role="dialog"] div[role="button"]:has-text("Carregar Foto")',
            'div[role="dialog"] div[role="button"]:has-text("Adicionar foto")',
            # Spanish
            'div[role="dialog"] div[role="button"]:has-text("Subir foto")',
            'div[role="dialog"] button:has-text("Subir foto")',
            'div[role="dialog"] div[role="button"]:has-text("Subir Foto")',
            'div[role="dialog"] div[role="button"]:has-text("Agregar foto")',
            # German & Italian
            'div[role="dialog"] button:has-text("Foto hochladen")',
            'div[role="dialog"] button:has-text("Carica foto")'
        ]

        for u_sel in upload_btn_selectors:
            try:
                u_btn = page.locator(u_sel).first
                if await u_btn.count() > 0 and await u_btn.is_visible():
                    async with page.expect_file_chooser(timeout=5000) as fc_info:
                        await human_move_and_click(page, u_btn, hover_pause=False)
                    fc = await fc_info.value
                    await fc.set_files(photo_path)
                    file_attached = True
                    self.log("SUCCESS", f"✅ Profile picture file attached via FileChooser: {file_name}")
                    break
            except Exception:
                pass

        # Fallback: direct set_input_files ONLY on dialog file input first (avoid wrong page file inputs)
        if not file_attached:
            try:
                f_inputs = page.locator('div[role="dialog"] input[type="file"]')
                if await f_inputs.count() > 0:
                    await f_inputs.first.set_input_files(photo_path)
                    file_attached = True
                    self.log("SUCCESS", f"✅ Profile picture file attached via dialog file input: {file_name}")
            except Exception as ex:
                self.log("DEBUG", f"Direct dialog input notice: {ex}")

        if not file_attached:
            self.log("ERROR", f"❌ Could not attach profile picture file: {file_name}")
            return False

        # Allow image upload preview & crop editor to render cleanly before looking for Save
        await asyncio.sleep(random.uniform(1.8, 2.6))
        self.log("INFO", "⏳ Waiting for crop preview & enabled Save button...")
        saved = False

        save_selectors = [
            # English
            'div[role="dialog"] div[aria-label="Save"][role="button"]',
            'div[role="dialog"] button:has-text("Save")',
            'div[role="dialog"] div[role="button"]:has-text("Save")',
            'div[role="dialog"] button:has-text("Done")',
            'div[role="dialog"] div[role="button"]:has-text("Done")',
            # French
            'div[role="dialog"] div[aria-label="Enregistrer"][role="button"]',
            'div[role="dialog"] button:has-text("Enregistrer")',
            'div[role="dialog"] div[role="button"]:has-text("Enregistrer")',
            'div[role="dialog"] button:has-text("Terminé")',
            'div[role="dialog"] div[role="button"]:has-text("Terminé")',
            'div[role="dialog"] button:has-text("Appliquer")',
            # Portuguese
            'div[role="dialog"] div[aria-label="Salvar"][role="button"]',
            'div[role="dialog"] button:has-text("Salvar")',
            'div[role="dialog"] div[role="button"]:has-text("Salvar")',
            'div[role="dialog"] button:has-text("Concluir")',
            'div[role="dialog"] div[role="button"]:has-text("Concluir")',
            # Spanish
            'div[role="dialog"] div[aria-label="Guardar"][role="button"]',
            'div[role="dialog"] button:has-text("Guardar")',
            'div[role="dialog"] div[role="button"]:has-text("Guardar")',
            'div[role="dialog"] button:has-text("Listo")',
            'div[role="dialog"] div[role="button"]:has-text("Listo")',
            # German & Italian
            'div[role="dialog"] button:has-text("Speichern")',
            'div[role="dialog"] button:has-text("Salva")'
        ]

        for loop_tick in range(30):
            if self._cancelled:
                return False

            # Do not click Save while dialog still shows active upload progressbar if Save is disabled
            for s_sel in save_selectors:
                try:
                    s_btn = page.locator(s_sel).first
                    if await s_btn.count() > 0 and await s_btn.is_visible():
                        dis = await s_btn.get_attribute("aria-disabled")
                        txt = ((await s_btn.inner_text()) or "").strip().lower()
                        if dis != "true" and len(txt) <= 28 and "cancel" not in txt and "discard" not in txt and "leave" not in txt:
                            if await human_move_and_click(page, s_btn):
                                saved = True
                                self.log("SUCCESS", f"💾 Clicked 'Save' on Profile Picture ({file_name})!")
                                break
                except Exception:
                    pass

            if saved:
                break

            # Strict DOM coordinate fallback for Save/Done button ONLY (never blind footerBtn[last] click)
            try:
                save_coords = await page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('div[role="dialog"] div[role="button"], div[role="dialog"] button'));
                    const saveWords = [
                        'save', 'done', 'apply',
                        'enregistrer', 'terminé', 'appliquer',
                        'salvar', 'concluir',
                        'guardar', 'listo',
                        'speichern', 'salva',
                        'محفوظ کریں', 'حفظ'
                    ];
                    for (const b of btns) {
                        if (!b.offsetParent) continue;
                        const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                        const aria = (b.getAttribute('aria-label') || '').trim().toLowerCase();
                        if (txt.length > 28) continue;
                        if (saveWords.some(w => txt === w || aria === w)) {
                            const dis = b.getAttribute('aria-disabled');
                            if (dis !== 'true' && !b.disabled) {
                                b.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                const r = b.getBoundingClientRect();
                                if (r.width > 4 && r.height > 4) {
                                    return { found: true, x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 };
                                }
                            }
                        }
                    }
                    return { found: false };
                }""")
                if save_coords and save_coords.get("found"):
                    await asyncio.sleep(0.25)
                    if await human_click_coords(page, save_coords["x"], save_coords["y"]):
                        saved = True
                        self.log("SUCCESS", f"💾 Clicked 'Save' on Profile Picture ({file_name})!")
                        break
            except Exception:
                pass

            await asyncio.sleep(1.0)

        if not saved:
            self.log("ERROR", "❌ Could not locate enabled Save button for Profile Picture.")
            return False

        # Wait thoroughly until Facebook finishes uploading & closes the Profile Picture modal on its own
        self.log("INFO", "⏳ Waiting for Facebook upload & crop modal to finish and close...")
        upload_finished = False
        upload_error = False
        for tick in range(35):
            if self._cancelled:
                return False
            await asyncio.sleep(1.0)
            try:
                state = await page.evaluate("""() => {
                    const dlgs = Array.from(document.querySelectorAll('div[role="dialog"]'));
                    let activeModal = false;
                    let hasError = false;
                    let hasLeavePrompt = false;
                    for (const d of dlgs) {
                        const t = (d.innerText || '').toLowerCase();
                        if (t.includes('still uploading') || t.includes('leave page') || t.includes('discard changes')) {
                            hasLeavePrompt = true;
                            const stayBtn = Array.from(d.querySelectorAll('button, div[role="button"]')).find(b => {
                                const bt = (b.innerText || '').trim().toLowerCase();
                                return bt === 'stay' || bt === 'cancel' || bt === 'keep editing';
                            });
                            if (stayBtn) stayBtn.click();
                            continue;
                        }
                        if (t.includes('couldn\\'t upload') || t.includes('try again') || t.includes('something went wrong')) {
                            hasError = true;
                        }
                        if (d.querySelector('[role="progressbar"]') ||
                            t.includes('update profile picture') ||
                            t.includes('photo de profil') ||
                            t.includes('foto do perfil') ||
                            t.includes('foto del perfil') ||
                            t.includes('make temporary')) {
                            activeModal = true;
                        }
                    }
                    const globalProgress = Boolean(document.querySelector('[role="progressbar"]'));
                    return { activeModal: activeModal || globalProgress || hasLeavePrompt, hasError };
                }""")
                if state.get("hasError"):
                    upload_error = True
                    break
                if not state.get("activeModal") and tick >= 2:
                    upload_finished = True
                    break
            except Exception:
                pass

        if upload_error:
            self.log("ERROR", f"❌ Facebook reported an error while uploading Profile Picture ({file_name}).")
            return False

        if not upload_finished:
            self.log("WARNING", "⚠️ Profile Picture modal remained open after waiting; upload may not have completed.")
            return False

        await asyncio.sleep(2.5)
        return True

    async def _update_cover_photo(self, page: Page, photo_path: str) -> bool:
        """
        Uploads and saves the cover photo across ALL Facebook account languages:
        (French, Portuguese, Spanish, German, Italian, Turkish, Arabic, Urdu, Russian, English)
        1. Scrolls to profile top and opens 'Edit cover photo' / 'Add cover photo' menu
        2. Attaches cover image via 'Upload photo' FileChooser
        3. Waits for reposition banner & enabled 'Save changes' button (never matching sidebar 'Saved')
        4. Waits until 'Save changes' banner & progressbar disappear completely before returning True
        """
        file_name = os.path.basename(photo_path)
        self.log("INFO", f"🖼️ Uploading Cover Photo: {file_name}...")

        await self._dismiss_popups_and_modals(page)
        try:
            await page.evaluate("() => window.scrollTo({ top: 0, behavior: 'smooth' })")
            await asyncio.sleep(1.2)
        except Exception:
            pass

        cover_btn_selectors = [
            # English
            'div[aria-label*="Edit cover photo" i][role="button"]',
            'div[aria-label*="Edit Cover Photo" i]',
            'div[aria-label*="Add cover photo" i][role="button"]',
            'div[aria-label*="Add Cover Photo" i]',
            'div[role="button"]:has-text("Edit cover photo")',
            'div[role="button"]:has-text("Edit Cover Photo")',
            'div[role="button"]:has-text("Add cover photo")',
            'button:has-text("Edit cover photo")',
            'button:has-text("Add cover photo")',
            # French
            'div[aria-label*="Modifier la photo de couverture" i][role="button"]',
            'div[aria-label*="Modifier la photo de couverture" i]',
            'div[aria-label*="Ajouter une photo de couverture" i]',
            'div[aria-label*="Changer la photo de couverture" i]',
            'div[role="button"]:has-text("Modifier la photo de couverture")',
            'div[role="button"]:has-text("Ajouter une photo de couverture")',
            # Portuguese
            'div[aria-label*="Editar foto da capa" i][role="button"]',
            'div[aria-label*="Editar foto da capa" i]',
            'div[aria-label*="Adicionar foto da capa" i]',
            'div[role="button"]:has-text("Editar foto da capa")',
            'div[role="button"]:has-text("Adicionar foto da capa")',
            # Spanish
            'div[aria-label*="Editar foto de portada" i][role="button"]',
            'div[aria-label*="Editar foto de portada" i]',
            'div[aria-label*="Agregar foto de portada" i]',
            'div[role="button"]:has-text("Editar foto de portada")',
            'div[role="button"]:has-text("Agregar foto de portada")',
            # German & Italian
            'div[aria-label*="Titelbild bearbeiten" i]',
            'div[aria-label*="Modifica immagine di copertina" i]'
        ]

        upload_menu_selectors = [
            # English
            'div[role="menuitem"]:has-text("Upload photo")',
            'div[role="menuitem"]:has-text("Upload Photo")',
            'div[role="menuitem"] span:has-text("Upload photo")',
            'div[role="button"]:has-text("Upload photo")',
            'div[role="button"]:has-text("Upload Photo")',
            # French
            'div[role="menuitem"]:has-text("Importer une photo")',
            'div[role="menuitem"]:has-text("Télécharger une photo")',
            'div[role="menuitem"]:has-text("Téléverser une photo")',
            'div[role="button"]:has-text("Importer une photo")',
            # Portuguese
            'div[role="menuitem"]:has-text("Carregar foto")',
            'div[role="menuitem"]:has-text("Carregar Foto")',
            'div[role="button"]:has-text("Carregar foto")',
            # Spanish
            'div[role="menuitem"]:has-text("Subir foto")',
            'div[role="menuitem"]:has-text("Subir Foto")',
            'div[role="button"]:has-text("Subir foto")',
            # German & Italian
            'div[role="menuitem"]:has-text("Foto hochladen")',
            'div[role="menuitem"]:has-text("Carica foto")'
        ]

        file_attached = False
        for attempt in range(2):
            if self._cancelled:
                return False

            clicked_cover_btn = False
            for c_sel in cover_btn_selectors:
                try:
                    btn = page.locator(c_sel).first
                    if await btn.count() > 0 and await btn.is_visible():
                        if await human_move_and_click(page, btn):
                            clicked_cover_btn = True
                            self.log("INFO", "👉 Clicked Cover Photo edit button smoothly.")
                            await asyncio.sleep(random.uniform(1.4, 2.2))
                            break
                except Exception:
                    pass

            if not clicked_cover_btn:
                try:
                    cover_coords = await page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll('div[role="button"], button'));
                        const keywords = [
                            'edit cover', 'add cover',
                            'photo de couverture', 'modifier la couverture', 'ajouter une couverture',
                            'foto da capa', 'editar capa', 'adicionar capa',
                            'foto de portada', 'editar portada', 'agregar portada',
                            'titelbild', 'copertina'
                        ];
                        for (const b of btns) {
                            const txt = (b.innerText || b.textContent || '').toLowerCase();
                            const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                            if (keywords.some(k => txt.includes(k) || aria.includes(k))) {
                                if (b.offsetParent !== null) {
                                    b.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                    const r = b.getBoundingClientRect();
                                    if (r.width > 4 && r.height > 4) {
                                        return { found: true, x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 };
                                    }
                                }
                            }
                        }
                        return { found: false };
                    }""")
                    if cover_coords and cover_coords.get("found"):
                        await asyncio.sleep(0.25)
                        clicked_cover_btn = await human_click_coords(page, cover_coords["x"], cover_coords["y"])
                        if clicked_cover_btn:
                            self.log("INFO", "👉 Clicked Cover Photo edit button cleanly.")
                            await asyncio.sleep(random.uniform(1.4, 2.2))
                except Exception:
                    pass

            # Click 'Upload photo' in dropdown menu via FileChooser
            for u_sel in upload_menu_selectors:
                try:
                    u_item = page.locator(u_sel).first
                    if await u_item.count() > 0 and await u_item.is_visible():
                        async with page.expect_file_chooser(timeout=5000) as fc_info:
                            await human_move_and_click(page, u_item, hover_pause=False)
                        fc = await fc_info.value
                        await fc.set_files(photo_path)
                        file_attached = True
                        self.log("SUCCESS", f"✅ Cover photo file attached via FileChooser: {file_name}")
                        break
                except Exception:
                    pass

            if file_attached:
                break

            # Fallback: only use direct file input if menu/cover controls opened
            if clicked_cover_btn:
                try:
                    f_inputs = page.locator('div[role="menu"] input[type="file"], div[role="main"] input[type="file"], input[type="file"]')
                    cnt = await f_inputs.count()
                    if cnt > 0:
                        await f_inputs.last.set_input_files(photo_path)
                        file_attached = True
                        self.log("SUCCESS", f"✅ Cover photo attached via direct file input: {file_name}")
                        break
                except Exception:
                    pass

            if attempt == 0:
                await asyncio.sleep(1.5)

        if not file_attached:
            self.log("ERROR", f"❌ Could not attach cover photo file: {file_name}")
            return False

        # Wait for reposition preview banner & 'Save changes' button to appear cleanly
        await asyncio.sleep(random.uniform(2.0, 3.0))
        self.log("INFO", "⏳ Waiting for Cover Photo reposition preview and enabled 'Save changes' button...")
        saved_cover = False

        save_changes_selectors = [
            # English (strictly Save changes — never generic 'Save' or sidebar 'Saved')
            'div[aria-label="Save changes"][role="button"]',
            'div[aria-label="Save Changes"][role="button"]',
            'div[role="button"]:has-text("Save changes")',
            'div[role="button"]:has-text("Save Changes")',
            'button:has-text("Save changes")',
            'button:has-text("Save Changes")',
            # French
            'div[aria-label="Enregistrer les modifications"][role="button"]',
            'div[role="button"]:has-text("Enregistrer les modifications")',
            'button:has-text("Enregistrer les modifications")',
            # Portuguese
            'div[aria-label="Salvar alterações"][role="button"]',
            'div[role="button"]:has-text("Salvar alterações")',
            'div[role="button"]:has-text("Salvar Alterações")',
            'button:has-text("Salvar alterações")',
            # Spanish
            'div[aria-label="Guardar cambios"][role="button"]',
            'div[role="button"]:has-text("Guardar cambios")',
            'button:has-text("Guardar cambios")',
            # German & Italian
            'button:has-text("Änderungen speichern")',
            'div[role="button"]:has-text("Änderungen speichern")',
            'button:has-text("Salva modifiche")',
            'div[role="button"]:has-text("Salva modifiche")'
        ]

        for loop_tick in range(30):
            if self._cancelled:
                return False

            for sc_sel in save_changes_selectors:
                try:
                    sc_btn = page.locator(sc_sel).first
                    if await sc_btn.count() > 0 and await sc_btn.is_visible():
                        dis = await sc_btn.get_attribute("aria-disabled")
                        txt = ((await sc_btn.inner_text()) or "").strip().lower()
                        if dis != "true" and len(txt) <= 36 and txt != "saved":
                            if await human_move_and_click(page, sc_btn):
                                saved_cover = True
                                self.log("SUCCESS", f"💾 Clicked 'Save Changes' on Cover Photo ({file_name})!")
                                break
                except Exception:
                    pass

            if saved_cover:
                break

            # Strict DOM coordinate fallback for Cover Save button (top banner, excluding sidebar/navigation)
            try:
                sc_coords = await page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('div[role="button"], button, span[role="button"]'));
                    const exactKeywords = [
                        'save changes',
                        'enregistrer les modifications',
                        'salvar alterações', 'salvar alteracoes',
                        'guardar cambios',
                        'änderungen speichern', 'salva modifiche'
                    ];
                    for (const b of btns) {
                        if (!b.offsetParent) continue;
                        if (b.closest('[role="navigation"]')) continue;
                        const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                        const aria = (b.getAttribute('aria-label') || '').trim().toLowerCase();
                        if (txt === 'saved' || txt.length > 36) continue;
                        if (exactKeywords.some(k => txt === k || aria === k)) {
                            const dis = b.getAttribute('aria-disabled');
                            if (dis !== 'true' && !b.disabled) {
                                b.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                const r = b.getBoundingClientRect();
                                if (r.width > 4 && r.height > 4) {
                                    return { found: true, x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 };
                                }
                            }
                        }
                    }
                    return { found: false };
                }""")
                if sc_coords and sc_coords.get("found"):
                    await asyncio.sleep(0.25)
                    if await human_click_coords(page, sc_coords["x"], sc_coords["y"]):
                        saved_cover = True
                        self.log("SUCCESS", f"💾 Clicked 'Save Changes' on Cover Photo ({file_name})!")
                        break
            except Exception:
                pass

            await asyncio.sleep(1.0)

        if not saved_cover:
            self.log("ERROR", "❌ Could not locate enabled 'Save Changes' button for Cover Photo.")
            return False

        # Wait thoroughly until Cover Save Changes banner & any upload indicator completely disappear
        self.log("INFO", "⏳ Waiting for Facebook to process and finalize Cover Photo...")
        cover_finished = False
        cover_error = False
        for tick in range(35):
            if self._cancelled:
                return False
            await asyncio.sleep(1.0)
            try:
                state = await page.evaluate("""() => {
                    const saveBannerBtns = Array.from(document.querySelectorAll('div[role="button"], button'));
                    const stillHasSaveChanges = saveBannerBtns.some(b => {
                        if (!b.offsetParent) return false;
                        const t = (b.innerText || '').trim().toLowerCase();
                        return t === 'save changes' || t === 'enregistrer les modifications' || t === 'salvar alterações' || t === 'guardar cambios';
                    });
                    const hasProgress = Boolean(document.querySelector('[role="progressbar"]'));
                    let hasError = false;
                    const dlgs = Array.from(document.querySelectorAll('div[role="dialog"]'));
                    for (const d of dlgs) {
                        const dt = (d.innerText || '').toLowerCase();
                        if (dt.includes('still uploading') || dt.includes('leave page') || dt.includes('discard changes')) {
                            const stayBtn = Array.from(d.querySelectorAll('button, div[role="button"]')).find(b => {
                                const bt = (b.innerText || '').trim().toLowerCase();
                                return bt === 'stay' || bt === 'cancel' || bt === 'keep editing';
                            });
                            if (stayBtn) stayBtn.click();
                        }
                        if (dt.includes('couldn\\'t upload') || dt.includes('try again') || dt.includes('something went wrong')) {
                            hasError = true;
                        }
                    }
                    return { stillSaving: stillHasSaveChanges || hasProgress, hasError };
                }""")
                if state.get("hasError"):
                    cover_error = True
                    break
                if not state.get("stillSaving") and tick >= 2:
                    cover_finished = True
                    break
            except Exception:
                pass

        if cover_error:
            self.log("ERROR", f"❌ Facebook reported an upload error while saving Cover Photo ({file_name}).")
            return False

        if not cover_finished:
            self.log("WARNING", "⚠️ Cover Photo 'Save changes' banner stayed open; upload did not finalize.")
            return False

        await asyncio.sleep(2.5)
        return True

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

    async def run(self) -> Dict[str, Any]:
        """
        Executes Profile & Cover Photo Update for this account:
        1. Launches Chrome with cookies and anti-throttling flags
        2. Navigates to user profile & guards beforeunload/upload dialogs
        3. Uploads and saves Profile Picture if configured (waiting for upload completion)
        4. Uploads and saves Cover Photo if configured (waiting for Save Changes completion)
        5. Cleanly closes Chrome and returns true only when ALL requested photos saved
        """
        if not self.profile_photo_path and not self.cover_photo_path:
            self.log("ERROR", "No profile or cover photo selected to upload.")
            return {"success": False, "message": "No photos assigned"}

        profile_ok = False
        cover_ok = False

        try:
            await self._init_browser()
            if self._cancelled or not self.context:
                return {"success": False, "message": "Cancelled before start"}

            page = await get_bot_working_page(self.context)

            # Guard JS beforeunload dialogs so active uploads are never discarded automatically
            async def _handle_js_dialog(dialog):
                try:
                    await dialog.dismiss()
                except Exception:
                    pass
            try:
                page.on("dialog", lambda d: asyncio.create_task(_handle_js_dialog(d)))
            except Exception:
                pass

            # Navigate to profile URL
            clean_uid = "".join(c for c in str(self.account_data.get("uid", "")) if c.isdigit())
            profile_url = f"https://www.facebook.com/profile.php?id={clean_uid}" if clean_uid else "https://www.facebook.com/me"

            self.log("INFO", f"🌐 Navigating to Facebook Profile: {profile_url} ...")
            try:
                await page.goto(profile_url, wait_until="domcontentloaded", timeout=45000)
                slot_idx, total_slots, tile_rect = resolve_tile_context(self.account_data)
                await apply_cdp_window_bounds(
                    self.context,
                    page,
                    tile_rect=tile_rect,
                    total_slots=total_slots,
                    slot_index=slot_idx,
                )
                await asyncio.sleep(3.0)
            except Exception as ex:
                self.log("WARNING", f"Initial profile navigation notice: {ex}")

            curr_url = page.url.lower()
            if "login" in curr_url or "checkpoint" in curr_url:
                self.log("ERROR", "❌ Facebook account session expired. Please update cookies or login.")
                return {"success": False, "message": "Session expired"}

            await self._dismiss_popups_and_modals(page)
            await human_session_warmup(page, duration_range=(1.1, 2.0))

            # Step 1: Upload Profile Picture (if configured)
            if self.profile_photo_path:
                profile_ok = await self._update_profile_picture(page, self.profile_photo_path)
                if profile_ok:
                    self.log("SUCCESS", "🎉 Profile Picture updated and saved successfully!")
                else:
                    self.log("ERROR", "❌ Profile Picture update failed or did not finish saving.")
                await human_pause(max(1.2, self.action_delay * 0.75), max(2.2, self.action_delay * 1.25))

            # Step 2: Upload Cover Photo (if configured)
            if self.cover_photo_path and not self._cancelled:
                await human_idle_drift(page)
                cover_ok = await self._update_cover_photo(page, self.cover_photo_path)
                if cover_ok:
                    self.log("SUCCESS", "🎉 Cover Photo updated and saved changes successfully!")
                else:
                    self.log("ERROR", "❌ Cover Photo update failed or did not finish saving.")
                await human_pause(max(1.0, self.action_delay * 0.65), max(1.8, self.action_delay * 1.15))

            overall_success = (profile_ok if self.profile_photo_path else True) and (cover_ok if self.cover_photo_path else True)

            if overall_success:
                done_parts = []
                if self.profile_photo_path:
                    done_parts.append("Profile Picture")
                if self.cover_photo_path:
                    done_parts.append("Cover Photo")
                self.log("SUCCESS", f"✨ Successfully completed & saved {' and '.join(done_parts)} for {self.account_name}!")
            else:
                self.log("WARNING", f"⚠️ Profile/Cover update finished partially for {self.account_name} (Profile OK: {profile_ok}, Cover OK: {cover_ok}).")

            return {
                "success": overall_success,
                "profile_updated": profile_ok,
                "cover_updated": cover_ok,
                "message": "Completed successfully" if overall_success else "Partially completed"
            }

        except Exception as e:
            self.log("ERROR", f"Error during profile picture update: {str(e)}")
            return {"success": False, "message": str(e)}

        finally:
            self.log("INFO", f"Closing Chrome cleanly for {self.account_name}...")
            await self.close()
            self.log("INFO", f"🔒 Chrome closed for {self.account_name}.")
