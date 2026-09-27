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
        """Detects and automatically dismisses blocking dialogs and popups across languages."""
        try:
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

        try:
            specific_close_selectors = [
                'div[role="dialog"] div[aria-label="Close"][role="button"]',
                'div[role="dialog"] div[aria-label="Fechar"][role="button"]',
                'div[role="dialog"] div[aria-label="Cerrar"][role="button"]',
                'div[role="dialog"] button:has-text("Close")',
                'div[role="dialog"] button:has-text("Fechar")',
                'div[role="dialog"] button:has-text("Cerrar")',
                'div[role="dialog"] button:has-text("Not now")',
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

    async def _update_profile_picture(self, page: Page, photo_path: str) -> bool:
        """
        Uploads and saves the profile picture across ALL Facebook account languages:
        (French, Portuguese, Spanish, German, Italian, Turkish, Arabic, Urdu, Russian, English)
        1. Finds and clicks the camera/edit icon on the profile avatar
        2. Uploads the image via FileChooser or direct file input
        3. Waits for crop dialog and clicks 'Save' / 'Enregistrer' / 'Salvar' / 'Guardar' / 'Speichern'
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
                    await btn.click()
                    clicked_avatar = True
                    self.log("INFO", "👉 Clicked avatar camera icon.")
                    await asyncio.sleep(2.5)
                    break
            except Exception:
                pass

        if not clicked_avatar:
            # Universal DOM query fallback for avatar camera button
            try:
                clicked_avatar = await page.evaluate("""() => {
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
                                clickable.click();
                                return true;
                            }
                        }
                    }
                    // Structural fallback: look for the avatar container (SVG overlay on profile picture)
                    const avatarImgs = Array.from(document.querySelectorAll('image, img[alt*="profile" i], img[alt*="profil" i], img[alt*="perfil" i]'));
                    for (const img of avatarImgs) {
                        const container = img.closest('div[role="button"]') || img.parentElement?.querySelector('div[role="button"]');
                        if (container && container.offsetParent !== null) {
                            container.click();
                            return true;
                        }
                    }
                    return false;
                }""")
                if clicked_avatar:
                    self.log("INFO", "👉 Clicked avatar camera icon via universal DOM helper.")
                    await asyncio.sleep(2.5)
            except Exception:
                pass

        # Check if direct file input is available on the modal or profile
        file_attached = False
        upload_btn_selectors = [
            # English
            'div[role="dialog"] div[role="button"]:has-text("Upload Photo")',
            'div[role="dialog"] button:has-text("Upload Photo")',
            'div[role="dialog"] div[role="button"]:has-text("Upload photo")',
            'div[role="dialog"] button:has-text("Upload photo")',
            'div[role="dialog"] div[role="button"]:has-text("Upload")',
            'div[role="dialog"] button:has-text("Upload")',
            # French
            'div[role="dialog"] div[role="button"]:has-text("Importer une photo")',
            'div[role="dialog"] button:has-text("Importer une photo")',
            'div[role="dialog"] div[role="button"]:has-text("Télécharger une photo")',
            'div[role="dialog"] button:has-text("Télécharger une photo")',
            'div[role="dialog"] div[role="button"]:has-text("Ajouter une photo")',
            'div[role="dialog"] button:has-text("Ajouter une photo")',
            'div[role="dialog"] div[role="button"]:has-text("Importer")',
            'div[role="dialog"] button:has-text("Importer")',
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

        # Try expect_file_chooser on Upload Photo button
        for u_sel in upload_btn_selectors:
            try:
                u_btn = page.locator(u_sel).first
                if await u_btn.count() > 0 and await u_btn.is_visible():
                    async with page.expect_file_chooser(timeout=5000) as fc_info:
                        await u_btn.click()
                    fc = await fc_info.value
                    await fc.set_files(photo_path)
                    file_attached = True
                    self.log("SUCCESS", f"✅ Profile picture file attached via FileChooser: {file_name}")
                    break
            except Exception:
                pass

        # Fallback: direct set_input_files on any dialog file input
        if not file_attached:
            try:
                f_inputs = page.locator('div[role="dialog"] input[type="file"], input[type="file"]')
                if await f_inputs.count() > 0:
                    await f_inputs.first.set_input_files(photo_path)
                    file_attached = True
                    self.log("SUCCESS", f"✅ Profile picture file attached via direct file input: {file_name}")
            except Exception as ex:
                self.log("DEBUG", f"Direct input notice: {ex}")

        if not file_attached:
            self.log("ERROR", f"❌ Could not attach profile picture file: {file_name}")
            return False

        # Wait for crop/preview modal to appear and click 'Save' / 'Enregistrer' / 'Salvar' / 'Guardar' / 'Done'
        self.log("INFO", "⏳ Waiting for photo crop preview and clicking Save...")
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

            for s_sel in save_selectors:
                try:
                    s_btn = page.locator(s_sel).first
                    if await s_btn.count() > 0 and await s_btn.is_visible():
                        dis = await s_btn.get_attribute("aria-disabled")
                        if dis != "true":
                            await s_btn.click()
                            saved = True
                            self.log("SUCCESS", f"💾 Clicked 'Save' on Profile Picture ({file_name})!")
                            break
                except Exception:
                    pass

            if saved:
                break

            # Universal DOM query fallback for Save button
            try:
                saved = await page.evaluate("""() => {
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
                        if (saveWords.some(w => txt === w || aria === w || txt.startsWith(w) || aria.startsWith(w))) {
                            const dis = b.getAttribute('aria-disabled');
                            if (dis !== 'true' && !b.disabled) {
                                b.click();
                                return true;
                            }
                        }
                    }
                    // Structural fallback: Click the primary / last action button in the crop dialog footer
                    const footerBtns = Array.from(document.querySelectorAll('div[role="dialog"] div[role="button"]:not([aria-label*="close" i]):not([aria-label*="annuler" i]):not([aria-label*="cancelar" i]):not([aria-label*="cancel" i]), div[role="dialog"] button:not([aria-label*="close" i]):not([aria-label*="annuler" i]):not([aria-label*="cancelar" i]):not([aria-label*="cancel" i])'));
                    if (footerBtns.length > 0) {
                        const lastBtn = footerBtns[footerBtns.length - 1];
                        if (lastBtn.offsetParent !== null && !lastBtn.disabled && lastBtn.getAttribute('aria-disabled') !== 'true') {
                            lastBtn.click();
                            return true;
                        }
                    }
                    return false;
                }""")
                if saved:
                    self.log("SUCCESS", f"💾 Clicked 'Save' on Profile Picture via universal DOM helper ({file_name})!")
                    break
            except Exception:
                pass

            await asyncio.sleep(1.0)

        if saved:
            self.log("INFO", "⏳ Waiting 6 seconds for Facebook to process and finalize Profile Picture...")
            await asyncio.sleep(6.0)
            return True
        else:
            self.log("WARNING", "⚠️ Could not locate Save button for Profile Picture.")
            return False

    async def _update_cover_photo(self, page: Page, photo_path: str) -> bool:
        """
        Uploads and saves the cover photo across ALL Facebook account languages:
        (French, Portuguese, Spanish, German, Italian, Turkish, Arabic, Urdu, Russian, English)
        1. Finds and clicks 'Edit cover photo' / 'Modifier la photo de couverture' on the profile header
        2. Clicks 'Upload photo' / 'Importer une photo' in the dropdown menu via FileChooser
        3. Waits for reposition preview and clicks 'Save changes' / 'Enregistrer les modifications'
        """
        file_name = os.path.basename(photo_path)
        self.log("INFO", f"🖼️ Uploading Cover Photo: {file_name}...")

        await self._dismiss_popups_and_modals(page)

        # Look for Edit Cover Photo button (Universal Multilingual)
        cover_btn_selectors = [
            # English
            'div[aria-label*="Edit cover photo" i][role="button"]',
            'div[aria-label*="Edit Cover Photo" i]',
            'div[aria-label*="Add cover photo" i]',
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
            'button:has-text("Modifier la photo de couverture")',
            'button:has-text("Ajouter une photo de couverture")',
            # Portuguese
            'div[aria-label*="Editar foto da capa" i][role="button"]',
            'div[aria-label*="Editar foto da capa" i]',
            'div[aria-label*="Adicionar foto da capa" i]',
            'div[role="button"]:has-text("Editar foto da capa")',
            'div[role="button"]:has-text("Adicionar foto da capa")',
            'button:has-text("Editar foto da capa")',
            'button:has-text("Adicionar foto da capa")',
            # Spanish
            'div[aria-label*="Editar foto de portada" i][role="button"]',
            'div[aria-label*="Editar foto de portada" i]',
            'div[aria-label*="Agregar foto de portada" i]',
            'div[role="button"]:has-text("Editar foto de portada")',
            'div[role="button"]:has-text("Agregar foto de portada")',
            'button:has-text("Editar foto de portada")',
            'button:has-text("Agregar foto de portada")',
            # German & Italian
            'div[aria-label*="Titelbild bearbeiten" i]',
            'div[aria-label*="Modifica immagine di copertina" i]'
        ]

        clicked_cover_btn = False
        for c_sel in cover_btn_selectors:
            try:
                btn = page.locator(c_sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    clicked_cover_btn = True
                    self.log("INFO", "👉 Clicked Cover Photo edit button.")
                    await asyncio.sleep(2.0)
                    break
            except Exception:
                pass

        if not clicked_cover_btn:
            # Universal DOM query fallback for cover photo edit button
            try:
                clicked_cover_btn = await page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('div[role="button"], button'));
                    const keywords = [
                        'edit cover', 'add cover',
                        'photo de couverture', 'modifier la couverture', 'ajouter une couverture', 'couverture',
                        'foto da capa', 'editar capa', 'adicionar capa', 'capa',
                        'foto de portada', 'editar portada', 'agregar portada', 'portada',
                        'titelbild', 'copertina'
                    ];
                    for (const b of btns) {
                        const txt = (b.innerText || b.textContent || '').toLowerCase();
                        const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                        if (keywords.some(k => txt.includes(k) || aria.includes(k))) {
                            if (b.offsetParent !== null) {
                                b.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }""")
                if clicked_cover_btn:
                    self.log("INFO", "👉 Clicked Cover Photo edit button via universal DOM helper.")
                    await asyncio.sleep(2.0)
            except Exception:
                pass

        # Now click 'Upload photo' / 'Importer une photo' in the popup menu via expect_file_chooser
        file_attached = False
        upload_menu_selectors = [
            # English
            'div[role="menuitem"]:has-text("Upload photo")',
            'div[role="menuitem"]:has-text("Upload Photo")',
            'div[role="button"]:has-text("Upload photo")',
            'div[role="button"]:has-text("Upload Photo")',
            'span:has-text("Upload photo")',
            'span:has-text("Upload Photo")',
            # French
            'div[role="menuitem"]:has-text("Importer une photo")',
            'div[role="menuitem"]:has-text("Importer une Photo")',
            'div[role="menuitem"]:has-text("Télécharger une photo")',
            'div[role="menuitem"]:has-text("Téléverser une photo")',
            'div[role="button"]:has-text("Importer une photo")',
            'span:has-text("Importer une photo")',
            'span:has-text("Télécharger une photo")',
            # Portuguese
            'div[role="menuitem"]:has-text("Carregar foto")',
            'div[role="menuitem"]:has-text("Carregar Foto")',
            'div[role="button"]:has-text("Carregar foto")',
            'span:has-text("Carregar foto")',
            # Spanish
            'div[role="menuitem"]:has-text("Subir foto")',
            'div[role="menuitem"]:has-text("Subir Foto")',
            'div[role="button"]:has-text("Subir foto")',
            'span:has-text("Subir foto")',
            # German & Italian
            'div[role="menuitem"]:has-text("Foto hochladen")',
            'div[role="menuitem"]:has-text("Carica foto")'
        ]

        for u_sel in upload_menu_selectors:
            try:
                u_item = page.locator(u_sel).first
                if await u_item.count() > 0 and await u_item.is_visible():
                    try:
                        async with page.expect_file_chooser(timeout=5000) as fc_info:
                            await u_item.click()
                        fc = await fc_info.value
                        await fc.set_files(photo_path)
                        file_attached = True
                        self.log("SUCCESS", f"✅ Cover photo file attached via FileChooser: {file_name}")
                        break
                    except Exception:
                        pass
            except Exception:
                pass

        # Fallback: direct set_input_files on any file input
        if not file_attached:
            try:
                f_inputs = page.locator('input[type="file"]')
                if await f_inputs.count() > 0:
                    await f_inputs.last.set_input_files(photo_path)
                    file_attached = True
                    self.log("SUCCESS", f"✅ Cover photo attached via direct file input: {file_name}")
            except Exception:
                pass

        if not file_attached:
            self.log("ERROR", f"❌ Could not attach cover photo file: {file_name}")
            return False

        # Wait for reposition banner & 'Save changes' / 'Enregistrer les modifications' / 'Salvar alterações' / 'Guardar cambios' button
        self.log("INFO", "⏳ Waiting for reposition preview and clicking Save Changes...")
        saved_cover = False

        save_changes_selectors = [
            # English
            'div[aria-label="Save changes"][role="button"]',
            'div[role="button"]:has-text("Save changes")',
            'div[role="button"]:has-text("Save Changes")',
            'button:has-text("Save changes")',
            'button:has-text("Save Changes")',
            'span:has-text("Save changes")',
            # French
            'div[aria-label="Enregistrer les modifications"][role="button"]',
            'div[role="button"]:has-text("Enregistrer les modifications")',
            'div[role="button"]:has-text("Enregistrer les Modifications")',
            'button:has-text("Enregistrer les modifications")',
            'button:has-text("Enregistrer les Modifications")',
            'div[role="button"]:has-text("Enregistrer")',
            'button:has-text("Enregistrer")',
            # Portuguese
            'div[aria-label="Salvar alterações"][role="button"]',
            'div[role="button"]:has-text("Salvar alterações")',
            'div[role="button"]:has-text("Salvar Alterações")',
            'button:has-text("Salvar alterações")',
            'button:has-text("Salvar Alterações")',
            # Spanish
            'div[aria-label="Guardar cambios"][role="button"]',
            'div[role="button"]:has-text("Guardar cambios")',
            'div[role="button"]:has-text("Guardar Cambios")',
            'button:has-text("Guardar cambios")',
            'button:has-text("Guardar Cambios")',
            # German & Italian
            'button:has-text("Änderungen speichern")',
            'button:has-text("Salva modifiche")',
            # Fallback Save
            'div[aria-label="Save"][role="button"]',
            'button:has-text("Save")',
            'div[role="button"]:has-text("Save")'
        ]

        for loop_tick in range(30):
            if self._cancelled:
                return False

            for sc_sel in save_changes_selectors:
                try:
                    sc_btn = page.locator(sc_sel).first
                    if await sc_btn.count() > 0 and await sc_btn.is_visible():
                        dis = await sc_btn.get_attribute("aria-disabled")
                        if dis != "true":
                            await sc_btn.click()
                            saved_cover = True
                            self.log("SUCCESS", f"💾 Clicked 'Save Changes' on Cover Photo ({file_name})!")
                            break
                except Exception:
                    pass

            if saved_cover:
                break

            # Universal DOM query fallback for Save changes
            try:
                saved_cover = await page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('div[role="button"], button, span[role="button"]'));
                    const keywords = [
                        'save changes', 'save',
                        'enregistrer les modifications', 'enregistrer', 'sauvegarder',
                        'salvar alterações', 'salvar alteracoes', 'salvar',
                        'guardar cambios', 'guardar',
                        'änderungen speichern', 'salva modifiche'
                    ];
                    for (const b of btns) {
                        if (!b.offsetParent) continue;
                        const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                        const aria = (b.getAttribute('aria-label') || '').trim().toLowerCase();
                        if (keywords.some(k => txt.includes(k) || aria.includes(k))) {
                            const dis = b.getAttribute('aria-disabled');
                            if (dis !== 'true' && !b.disabled) {
                                b.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }""")
                if saved_cover:
                    self.log("SUCCESS", f"💾 Clicked 'Save Changes' on Cover Photo via universal DOM helper ({file_name})!")
                    break
            except Exception:
                pass

            await asyncio.sleep(1.0)

        if saved_cover:
            self.log("INFO", "⏳ Waiting 6 seconds for Facebook to process and finalize Cover Photo...")
            await asyncio.sleep(6.0)
            return True
        else:
            self.log("WARNING", "⚠️ Could not locate Save Changes button for Cover Photo.")
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

    async def run(self) -> Dict[str, Any]:
        """
        Executes Profile & Cover Photo Update for this account:
        1. Launches Chrome with cookies and anti-throttling flags
        2. Navigates to user profile
        3. Uploads and saves Profile Picture if configured
        4. Uploads and saves Cover Photo if configured
        5. Cleanly closes Chrome
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

            page = self.context.pages[0] if self.context.pages else await self.context.new_page()

            # Navigate to profile URL
            clean_uid = "".join(c for c in str(self.account_data.get("uid", "")) if c.isdigit())
            profile_url = f"https://www.facebook.com/profile.php?id={clean_uid}" if clean_uid else "https://www.facebook.com/me"

            self.log("INFO", f"🌐 Navigating to Facebook Profile: {profile_url} ...")
            try:
                await page.goto(profile_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(3.0)
            except Exception as ex:
                self.log("WARNING", f"Initial profile navigation notice: {ex}")

            curr_url = page.url.lower()
            if "login" in curr_url or "checkpoint" in curr_url:
                self.log("ERROR", "❌ Facebook account session expired. Please update cookies or login.")
                return {"success": False, "message": "Session expired"}

            await self._dismiss_popups_and_modals(page)

            # Step 1: Upload Profile Picture
            if self.profile_photo_path:
                profile_ok = await self._update_profile_picture(page, self.profile_photo_path)
                if profile_ok:
                    self.log("SUCCESS", "🎉 Profile Picture updated and saved successfully!")
                else:
                    self.log("WARNING", "⚠️ Profile Picture update was incomplete.")
                await asyncio.sleep(self.action_delay)

            # Step 2: Upload Cover Photo
            if self.cover_photo_path and not self._cancelled:
                cover_ok = await self._update_cover_photo(page, self.cover_photo_path)
                if cover_ok:
                    self.log("SUCCESS", "🎉 Cover Photo updated and saved changes successfully!")
                else:
                    self.log("WARNING", "⚠️ Cover Photo update was incomplete.")
                await asyncio.sleep(self.action_delay)

            overall_success = (profile_ok if self.profile_photo_path else True) and (cover_ok if self.cover_photo_path else True)

            if overall_success:
                self.log("SUCCESS", f"✨ Both Profile and Cover photos successfully completed for {self.account_name}!")
            else:
                self.log("INFO", f"Finished profile photo tasks for {self.account_name}.")

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
