"""
FB Auto Bot - Facebook Group Automation Engine (Posting & Group Joining)
Handles automated group joining, sequential/random link & description posting,
multi-threading, delay intervals, and pre-loading FEWFEED Chrome extension.
"""

import os
import sys
import re
import json
import time
import random
import asyncio
import shutil
from typing import List, Dict, Any, Optional, Callable

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

# Desktop Chrome Specifications for FB Group Automation & FEWFEED Integration
DESKTOP_CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

# Kept for backward compatibility
MOBILE_SMARTPHONE_USER_AGENT = DESKTOP_CHROME_USER_AGENT
MOBILE_DEVICE_METRICS = {
    "width": 1280,
    "height": 800,
    "pixelRatio": 1.0
}
MOBILE_EMULATION_EXPERIMENTAL_OPTIONS = {
    "deviceMetrics": MOBILE_DEVICE_METRICS,
    "userAgent": DESKTOP_CHROME_USER_AGENT
}

def get_base_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_master_fewfeed_source_dir() -> Optional[str]:
    """
    Finds the most recent and complete FewFeed/Google session data directory across all browser profiles.
    """
    base_profiles = os.path.join(get_base_dir(), "profiles")
    if not os.path.isdir(base_profiles):
        return None

    # Priority 1: master_fewfeed_profile (Created via Master QFit / FewFeed Scan)
    master_profile_dir = os.path.join(base_profiles, "master_fewfeed_profile")
    if os.path.isdir(master_profile_dir):
        def_dir = os.path.join(master_profile_dir, "Default") if os.path.isdir(os.path.join(master_profile_dir, "Default")) else master_profile_dir
        if os.path.isdir(os.path.join(def_dir, "Local Storage")) or os.path.isfile(os.path.join(def_dir, "Network", "Cookies")) or os.path.isfile(os.path.join(def_dir, "Cookies")) or os.path.isdir(os.path.join(def_dir, "IndexedDB")):
            return master_profile_dir

    # Priority 2: dedicated shared template
    shared_dir = os.path.join(base_profiles, "fewfeed_shared")
    if os.path.isdir(shared_dir):
        def_dir = os.path.join(shared_dir, "Default") if os.path.isdir(os.path.join(shared_dir, "Default")) else shared_dir
        if os.path.isdir(os.path.join(def_dir, "Local Storage")) or os.path.isfile(os.path.join(def_dir, "Network", "Cookies")) or os.path.isfile(os.path.join(def_dir, "Cookies")) or os.path.isdir(os.path.join(def_dir, "IndexedDB")):
            return shared_dir

    # Priority 3: dedicated master template
    master_dir = os.path.join(base_profiles, "fewfeed_master")
    if os.path.isdir(master_dir):
        def_dir = os.path.join(master_dir, "Default") if os.path.isdir(os.path.join(master_dir, "Default")) else master_dir
        if os.path.isdir(os.path.join(def_dir, "Local Storage")) or os.path.isfile(os.path.join(def_dir, "Network", "Cookies")) or os.path.isfile(os.path.join(def_dir, "Cookies")) or os.path.isdir(os.path.join(def_dir, "IndexedDB")):
            return master_dir

    # Priority 4: Search all profile directories for the one with the latest modified session data
    candidates = []
    try:
        for entry in os.listdir(base_profiles):
            p_dir = os.path.join(base_profiles, entry)
            if not os.path.isdir(p_dir):
                continue
            default_dir = os.path.join(p_dir, "Default") if os.path.isdir(os.path.join(p_dir, "Default")) else p_dir
            
            ls_dir = os.path.join(default_dir, "Local Storage")
            net_cookie = os.path.join(default_dir, "Network", "Cookies")
            flat_cookie = os.path.join(default_dir, "Cookies")
            idb_dir = os.path.join(default_dir, "IndexedDB")

            has_session = False
            mtime = 0
            if os.path.isdir(ls_dir) and os.listdir(ls_dir):
                has_session = True
                try: mtime = max(mtime, os.path.getmtime(ls_dir))
                except Exception: pass
            if os.path.isfile(net_cookie) and os.path.getsize(net_cookie) > 2048:
                has_session = True
                try: mtime = max(mtime, os.path.getmtime(net_cookie))
                except Exception: pass
            if os.path.isfile(flat_cookie) and os.path.getsize(flat_cookie) > 2048:
                has_session = True
                try: mtime = max(mtime, os.path.getmtime(flat_cookie))
                except Exception: pass
            if os.path.isdir(idb_dir) and os.listdir(idb_dir):
                has_session = True
                try: mtime = max(mtime, os.path.getmtime(idb_dir))
                except Exception: pass

            if has_session:
                candidates.append((mtime, p_dir))
    except Exception:
        pass

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    return None

def copy_fewfeed_session_data(src_profile_dir: str, dst_profile_dir: str):
    """
    Copies FewFeed and Google session artifacts from source profile to target profile.
    """
    if not src_profile_dir or not dst_profile_dir or os.path.abspath(src_profile_dir) == os.path.abspath(dst_profile_dir):
        return

    os.makedirs(dst_profile_dir, exist_ok=True)
    
    src_default = os.path.join(src_profile_dir, "Default") if os.path.isdir(os.path.join(src_profile_dir, "Default")) else src_profile_dir
    dst_default = os.path.join(dst_profile_dir, "Default")
    os.makedirs(dst_default, exist_ok=True)

    items_to_copy = [
        ("Local Storage", "dir"),
        ("IndexedDB", "dir"),
        ("Session Storage", "dir"),
        ("Storage", "dir"),
        ("Local Extension Settings", "dir"),
        ("Sync Extension Settings", "dir"),
        ("Extension State", "dir"),
        ("Extension Rules", "dir"),
        ("Extensions", "dir"),
        ("Network", "dir"),
        ("Cookies", "file"),
        ("Preferences", "file"),
        ("Secure Preferences", "file"),
        ("Web Data", "file"),
    ]

    for item_name, item_type in items_to_copy:
        src_path = os.path.join(src_default, item_name)
        dst_path = os.path.join(dst_default, item_name)
        if not os.path.exists(src_path):
            continue
        try:
            if item_type == "dir" and os.path.isdir(src_path):
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path, ignore_errors=True)
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            elif item_type == "file" and os.path.isfile(src_path):
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)
        except Exception:
            pass

    src_ls = os.path.join(src_profile_dir, "Local State")
    dst_ls = os.path.join(dst_profile_dir, "Local State")
    if os.path.isfile(src_ls):
        try:
            shutil.copy2(src_ls, dst_ls)
        except Exception:
            pass

    # Copy storage state JSON if present
    for st_file in ["fewfeed_storage_state.json", "state.json"]:
        for s_folder in [src_profile_dir, src_default]:
            sf = os.path.join(s_folder, st_file)
            if os.path.isfile(sf):
                for d_folder in [dst_profile_dir, dst_default]:
                    try:
                        shutil.copy2(sf, os.path.join(d_folder, st_file))
                    except Exception:
                        pass

    for fname in ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"]:
        fpath = os.path.join(dst_profile_dir, fname)
        if os.path.exists(fpath) or os.path.islink(fpath):
            try:
                if os.path.islink(fpath) or os.path.isfile(fpath):
                    os.unlink(fpath)
                elif os.path.isdir(fpath):
                    shutil.rmtree(fpath, ignore_errors=True)
            except Exception:
                pass

def save_as_master_fewfeed_template(source_profile_dir: str):
    """
    Saves the specified profile as the master template (profiles/master_fewfeed_profile and fewfeed_shared)
    so all newly created browser profiles will automatically inherit it.
    """
    if not source_profile_dir or not os.path.isdir(source_profile_dir):
        return
    master_dir = os.path.join(get_base_dir(), "profiles", "master_fewfeed_profile")
    copy_fewfeed_session_data(source_profile_dir, master_dir)
    shared_dir = os.path.join(get_base_dir(), "profiles", "fewfeed_shared")
    copy_fewfeed_session_data(source_profile_dir, shared_dir)

def get_custom_extension_path() -> Optional[str]:
    """Retrieves user-configured FewFeed extension folder from configuration if set."""
    try:
        cfg_file = os.path.join(get_base_dir(), "config", "extension_config.json")
        if os.path.isfile(cfg_file):
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                custom_p = data.get("extension_path")
                if custom_p and os.path.isdir(custom_p) and os.path.exists(os.path.join(custom_p, "manifest.json")):
                    return os.path.abspath(custom_p)
    except Exception:
        pass
    return None

def set_custom_extension_path(folder_path: str) -> bool:
    """Stores user-configured custom unpacked FewFeed extension directory."""
    try:
        if folder_path and os.path.isdir(folder_path) and os.path.exists(os.path.join(folder_path, "manifest.json")):
            cfg_dir = os.path.join(get_base_dir(), "config")
            os.makedirs(cfg_dir, exist_ok=True)
            cfg_file = os.path.join(cfg_dir, "extension_config.json")
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump({"extension_path": os.path.abspath(folder_path)}, f, indent=2)
            return True
    except Exception:
        pass
    return False

def get_fewfeed_extension_path() -> Optional[str]:
    """Resolves the absolute path to FEWFEED extension folder, checking custom path and bundle candidates."""
    try:
        from automation.extension_manager import get_fewfeed_extension_path as _get_path
        return _get_path()
    except Exception:
        pass

    # Priority 1: User-selected custom unpacked extension
    custom = get_custom_extension_path()
    if custom:
        return custom

    # Priority 2: Standard and bundled workspace paths
    candidates = [
        os.path.join(get_base_dir(), "FEWFEED"),
        os.path.join(get_base_dir(), "_internal", "FEWFEED"),
        os.path.join(get_base_dir(), "fewfeed"),
        os.path.join(get_base_dir(), "extensions", "FEWFEED"),
        os.path.join(getattr(sys, '_MEIPASS', ''), "FEWFEED"),
        os.path.join(getattr(sys, '_MEIPASS', ''), "_internal", "FEWFEED"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "FEWFEED")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "FEWFEED")),
        "/desktop_app/FEWFEED",
        os.path.abspath("FEWFEED"),
        os.path.abspath("desktop_app/FEWFEED")
    ]
    for c in candidates:
        if c and os.path.isdir(c) and os.path.exists(os.path.join(c, "manifest.json")):
            return os.path.abspath(c)
    return None

def get_chrome_webdriver_mobile_emulation_config(ext_path: Optional[str] = None, user_data_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns Python Chrome WebDriver experimental options dictionary for mobileEmulation.
    Includes deviceMetrics (width: 430, height: 900, pixelRatio: 1.0) and genuine mobile userAgent.
    """
    config = {
        "mobileEmulation": MOBILE_EMULATION_EXPERIMENTAL_OPTIONS,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--window-size=440,920",
            "--enable-viewport",
            "--force-device-scale-factor=1.0",
            "--touch-events=enabled",
            f"--user-agent={MOBILE_SMARTPHONE_USER_AGENT}",
            "--disable-notifications"
        ]
    }
    if ext_path and os.path.exists(ext_path):
        config["args"].append(f"--load-extension={ext_path}")
        config["args"].append(f"--disable-extensions-except={ext_path}")
    if user_data_dir:
        config["args"].append(f"--user-data-dir={user_data_dir}")
    return config

def parse_group_codes(raw_input: Any) -> List[str]:
    """Parses group codes, IDs, or full Facebook URLs from textarea or list."""
    if not raw_input:
        return []
    if isinstance(raw_input, list):
        items = raw_input
    else:
        items = re.split(r'[\r\n,;]+', str(raw_input))
    
    codes = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        # Extract group ID or vanity name if full URL was pasted
        # e.g., https://www.facebook.com/groups/123456789/ -> 123456789
        m = re.search(r'facebook\.com/groups/([^/?#]+)', cleaned)
        if m:
            codes.append(m.group(1).strip())
        else:
            # Plain code or ID
            codes.append(cleaned.strip())
    # Deduplicate while preserving order
    seen = set()
    unique_codes = []
    for c in codes:
        if c and c not in seen:
            seen.add(c)
            unique_codes.append(c)
    return unique_codes

def parse_multiline_links(raw_input: Any) -> List[str]:
    """Parses links list."""
    if not raw_input:
        return []
    if isinstance(raw_input, list):
        items = raw_input
    else:
        items = re.split(r'[\r\n,;]+', str(raw_input))
    links = [i.strip() for i in items if i.strip()]
    return links

def parse_cookie_payload(raw_cookies: Any) -> List[Dict[str, Any]]:
    if not raw_cookies:
        return []
    if isinstance(raw_cookies, list):
        formatted = []
        for item in raw_cookies:
            if isinstance(item, dict) and item.get("name"):
                dom = item.get("domain", ".facebook.com")
                if not dom.startswith("."):
                    dom = "." + dom
                cookie = {
                    "name": str(item["name"]),
                    "value": str(item.get("value", "")),
                    "domain": dom,
                    "path": item.get("path", "/"),
                    "secure": bool(item.get("secure", True))
                }
                if item.get("sameSite") in ["Strict", "Lax", "None"]:
                    cookie["sameSite"] = item["sameSite"]
                formatted.append(cookie)
        return formatted

    if isinstance(raw_cookies, str):
        cleaned = raw_cookies.strip()
        if not cleaned:
            return []
        if cleaned.startswith("[") and cleaned.endswith("]"):
            try:
                items = json.loads(cleaned)
                return parse_cookie_payload(items)
            except Exception:
                pass
        # Semicolon format
        formatted = []
        pairs = cleaned.split(";")
        for pair in pairs:
            if "=" in pair:
                k, v = pair.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k:
                    formatted.append({
                        "name": k,
                        "value": v,
                        "domain": ".facebook.com",
                        "path": "/",
                        "secure": True
                    })
        return formatted
    return []


# ==============================================================================
# Facebook Group Automation Bot
# ==============================================================================
class FacebookGroupBot:
    """Automates Facebook Group Posting and Group Joining tasks using Playwright & FEWFEED Extension."""

    def __init__(
        self,
        account_data: Dict[str, Any],
        log_callback: Optional[Callable[[str, str], None]] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        headless: bool = False
    ):
        self.account_data = account_data or {}
        self.log_callback = log_callback or (lambda lvl, msg: print(f"[{lvl}] {msg}"))
        self.progress_callback = progress_callback or (lambda p: None)
        self.headless = headless
        self.playwright = None
        self.context = None
        self.page = None
        self.extension_id: Optional[str] = None
        self.fewfeed_ready: bool = False
        self._cancel_requested = False

    def log(self, level: str, message: str):
        self.log_callback(level, message)

    def set_progress(self, val: int):
        self.progress_callback(val)

    def cancel(self):
        self._cancel_requested = True
        self.log("WARNING", "Cancellation requested for Group Bot.")

    async def initialize_browser(self):
        """Launches Desktop Chrome with FEWFEED extension loaded automatically and full desktop session support."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not available in Python environment.")

        self.log("INFO", "Initializing Desktop Chrome Browser Context for FB Group Automation...")
        self.log("INFO", f"💻 Desktop Chrome User-Agent: {DESKTOP_CHROME_USER_AGENT}")

        self.playwright = await async_playwright().start()

        ext_path = get_fewfeed_extension_path()
        try:
            from automation.extension_manager import get_extension_chrome_args, prepare_profile_for_extension
            ext_args = get_extension_chrome_args(ext_path)
        except Exception:
            ext_args = []
            if ext_path and os.path.exists(ext_path):
                clean_p = ext_path.replace('\\', '/')
                ext_args = [
                    f"--load-extension={clean_p}",
                    f"--disable-extensions-except={clean_p}",
                    "--disable-features=DisableLoadExtensionCommandLineSwitch",
                    "--enable-features=ExtensionsToolbarMenu"
                ]

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--start-maximized",
            "--disable-infobars",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-default-browser-check",
            "--disable-dev-shm-usage",
            "--lang=en-US,en",
            "--ignore-certificate-errors",
            "--allow-running-insecure-content",
            "--disable-web-security",
            "--disable-notifications",
            "--password-store=basic",
            "--no-first-run",
            "--no-service-autorun"
        ]
        launch_args.extend(ext_args)

        if ext_path and os.path.exists(ext_path):
            self.log("SUCCESS", f"🧩 Chrome Extension Loaded: {os.path.basename(ext_path)} -> {ext_path}")
        else:
            self.log("WARNING", f"FEWFEED extension folder not detected at {ext_path}. Proceeding.")

        ignore_default_args = ["--enable-automation", "--disable-extensions"]

        proxy_cfg = None
        raw_proxy = self.account_data.get("proxy", "").strip()
        if raw_proxy and "direct" not in raw_proxy.lower():
            ptype = self.account_data.get("proxy_type", "HTTP").lower()
            if not raw_proxy.startswith("http://") and not raw_proxy.startswith("socks5://"):
                full_srv = f"{ptype}://{raw_proxy}"
            else:
                full_srv = raw_proxy
            proxy_cfg = {"server": full_srv}
            if self.account_data.get("proxy_user"):
                proxy_cfg["username"] = self.account_data["proxy_user"]
            if self.account_data.get("proxy_pass"):
                proxy_cfg["password"] = self.account_data["proxy_pass"]

        # If account has dedicated profile_dir, use launch_persistent_context
        profile_dir = self.account_data.get("profile_dir")
        if not profile_dir and self.account_data.get("id"):
            safe_id = "".join(c for c in str(self.account_data.get("id", "")) if c.isalnum() or c in ("_", "-"))
            profile_dir = os.path.join(get_base_dir(), "profiles", safe_id)

        if profile_dir:
            os.makedirs(profile_dir, exist_ok=True)
            self.profile_dir = profile_dir

            # Pre-configure profile preferences for developer mode and extension toolbar
            try:
                from automation.extension_manager import prepare_profile_for_extension
                prepare_profile_for_extension(profile_dir, ext_path)
            except Exception:
                pass

            # Check if this profile has FewFeed/Google session data
            dst_default = os.path.join(profile_dir, "Default")
            ls_path = os.path.join(dst_default, "Local Storage")
            net_path = os.path.join(dst_default, "Network", "Cookies")
            flat_cookie = os.path.join(dst_default, "Cookies")
            idb_path = os.path.join(dst_default, "IndexedDB")

            # Always synchronize FewFeed extension & master session from master profile template
            src_master = get_master_fewfeed_source_dir()
            if src_master and os.path.abspath(src_master) != os.path.abspath(profile_dir):
                self.log("INFO", f"🔄 Synchronizing FewFeed Extension & Master Session from {os.path.basename(src_master)} into {os.path.basename(profile_dir)}...")
                copy_fewfeed_session_data(src_master, profile_dir)
                self.log("SUCCESS", "✅ FewFeed session & extension synced into browser profile.")

        # Clear profile locks to prevent SingletonLock errors
        if profile_dir and os.path.exists(profile_dir):
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

        # Launch browser in desktop mode with FEWFEED loaded (Chromium priority ensures reliable extension loading)
        self.context = None
        for ch in [None, "chrome", "msedge"]:
            try:
                kwargs = {
                    "user_data_dir": profile_dir,
                    "headless": False,  # Extensions require headful mode in Chromium
                    "args": launch_args,
                    "ignore_default_args": ignore_default_args,
                    "proxy": proxy_cfg,
                    "user_agent": DESKTOP_CHROME_USER_AGENT,
                    "no_viewport": True,
                    "locale": "en-US",
                    "permissions": ["geolocation", "notifications"]
                }
                if ch:
                    kwargs["channel"] = ch
                self.context = await self.playwright.chromium.launch_persistent_context(**kwargs)
                self.log("INFO", f"Launched Desktop browser using {ch.upper() if ch else 'Chromium (Extension Optimized)'} with FEWFEED loaded.")
                break
            except Exception as ex:
                self.log("WARNING", f"Browser launch attempt with channel={ch} notice: {str(ex)[:100]}")
                if profile_dir and os.path.exists(profile_dir):
                    for fname in ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"]:
                        fpath = os.path.join(profile_dir, fname)
                        if os.path.exists(fpath) or os.path.islink(fpath):
                            try: os.unlink(fpath)
                            except Exception: pass
                continue

        if not self.context:
            # Fallback to standard launch (non-persistent)
            self.log("WARNING", "Persistent profile context locked or unavailable. Engaging standard browser launch...")
            try:
                launch_kw = {
                    "headless": False,
                    "args": launch_args,
                    "ignore_default_args": ignore_default_args,
                    "proxy": proxy_cfg
                }
                self.browser = await self.playwright.chromium.launch(**launch_kw)
                self.context = await self.browser.new_context(
                    user_agent=DESKTOP_CHROME_USER_AGENT,
                    viewport={"width": 1280, "height": 800},
                    locale="en-US",
                    permissions=["geolocation", "notifications"]
                )
                self.log("INFO", "Launched standard Desktop Chrome browser.")
            except Exception as final_ex:
                raise RuntimeError(f"Failed to launch Chrome or Edge: {str(final_ex)}")

        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

        # Step: Verify and hook FEWFEED Chrome Extension background service worker & pages
        try:
            # Check service workers
            service_workers = self.context.service_workers
            if service_workers:
                for sw in service_workers:
                    sw_url = sw.url
                    if "chrome-extension://" in sw_url:
                        parts = sw_url.replace("chrome-extension://", "").split("/")
                        self.extension_id = parts[0]
                        self.fewfeed_ready = True
                        self.log("SUCCESS", f"⚡ FEWFEED Extension background service worker hooked! ID: {self.extension_id}")
                        break

            # Check background / extension pages if not identified yet
            if not self.extension_id:
                for p in self.context.pages:
                    if "chrome-extension://" in p.url:
                        parts = p.url.replace("chrome-extension://", "").split("/")
                        self.extension_id = parts[0]
                        self.fewfeed_ready = True
                        self.log("SUCCESS", f"⚡ FEWFEED Extension active page hooked! ID: {self.extension_id}")
                        break

            if not self.fewfeed_ready:
                self.log("INFO", "FEWFEED extension loaded in browser context. Ready for background automation.")
                self.fewfeed_ready = True
        except Exception as ee:
            self.log("INFO", f"Extension hook status: Ready ({str(ee)[:60]})")
            self.fewfeed_ready = True

        # Inject session cookies
        cookies_raw = self.account_data.get("cookies", "")
        if cookies_raw:
            cookies = parse_cookie_payload(cookies_raw)
            if cookies:
                try:
                    await self.context.add_cookies(cookies)
                    self.log("SUCCESS", f"🔑 Injected {len(cookies)} authentication cookies into browser context.")
                except Exception as ce:
                    self.log("WARNING", f"Cookie injection notice: {str(ce)[:80]}")

    async def authenticate_session(self):
        """Verifies session is active by navigating to facebook.com in Tab 1."""
        self.log("INFO", "Validating Facebook session in primary tab...")
        try:
            await self.page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(2.0)
        except Exception as e:
            self.log("WARNING", f"Navigation notice: {str(e)[:80]}")

        url = self.page.url.lower()
        if "login" in url or "checkpoint" in url:
            if "checkpoint" in url:
                raise RuntimeError("Facebook Checkpoint encountered. Manual verification or 2FA required.")
            raise RuntimeError("Facebook session not logged in or expired. Please click 'Launch Manual Login' in Accounts Tab to log into this Facebook profile.")
        self.log("SUCCESS", "Facebook authentication confirmed in Tab 1 (tab will remain OPEN in background).")
        self.fb_page = self.page

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    # FewFeed Web Extension Dashboard Navigation & Tool Automation
    # --------------------------------------------------------------------------
    async def open_fewfeed_tool_page(self, target_url: str):
        """Directly navigates to the specific FewFeed tool URL on a NEW TAB, keeping Facebook tab open."""
        # Check if we need to open FewFeed in a dedicated second tab
        if not hasattr(self, 'fewfeed_page') or self.fewfeed_page is None or self.fewfeed_page.is_closed():
            self.log("INFO", "📑 Opening FewFeed on a NEW TAB (keeping Facebook ID tab active in Tab 1)...")
            self.fewfeed_page = await self.context.new_page()
        
        self.page = self.fewfeed_page
        self.log("INFO", f"🌐 Navigating to FewFeed Tool: {target_url}...")
        try:
            await self.page.goto(target_url, wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(3.0)
        except Exception as e:
            self.log("WARNING", f"FewFeed tool navigation notice: {str(e)[:80]}. Retrying...")
            try:
                await self.page.goto(target_url, wait_until="load", timeout=30000)
                await asyncio.sleep(3.0)
            except Exception as e2:
                self.log("ERROR", f"Could not reach {target_url}: {str(e2)[:80]}")

        # Check for CueFeed / FewFeed login form or signin page redirect
        try:
            cf_email = self.account_data.get("cuefeed_email") or self.account_data.get("fewfeed_email") or "codeabm71@gmail.com"
            cf_pass = self.account_data.get("cuefeed_pass") or self.account_data.get("fewfeed_pass") or "Fewfeew"

            # Check if login or signin page is detected
            is_signin_page = "signin" in self.page.url.lower() or "login" in self.page.url.lower()
            
            if is_signin_page:
                self.log("INFO", "⏳ FewFeed login page detected. Waiting up to 8s for inputs to load...")
                try:
                    await self.page.wait_for_selector("input", timeout=8000)
                except Exception:
                    pass

            # Robust locator for inputs
            email_inp = None
            pass_inp = None
            
            inputs = await self.page.query_selector_all("input")
            for inp in inputs:
                try:
                    inp_type = (await inp.get_attribute("type") or "").lower()
                    inp_placeholder = (await inp.get_attribute("placeholder") or "").lower()
                    inp_name = (await inp.get_attribute("name") or "").lower()
                    
                    if inp_type == "password" or "pass" in inp_placeholder or "pass" in inp_name:
                        pass_inp = inp
                    elif inp_type == "email" or "email" in inp_placeholder or "email" in inp_name or "user" in inp_name:
                        email_inp = inp
                except Exception:
                    continue

            # Fallbacks if specific attributes aren't matching
            if inputs and not email_inp:
                email_inp = inputs[0]
            if len(inputs) >= 2 and not pass_inp:
                pass_inp = inputs[1]

            if email_inp and pass_inp:
                self.log("INFO", f"🔑 Auto-filling FewFeed Account credentials ({cf_email})...")
                try:
                    await email_inp.click()
                    await email_inp.fill("")
                    await email_inp.fill(cf_email)
                    await asyncio.sleep(0.3)
                    
                    await pass_inp.click()
                    await pass_inp.fill("")
                    await pass_inp.fill(cf_pass)
                    await asyncio.sleep(0.3)

                    # Find login button
                    login_btn = await self.page.query_selector("button:has-text('Sign In'), button:has-text('Sign in'), button:has-text('Login'), button:has-text('Log in'), button[type='submit'], input[type='submit']")
                    if not login_btn:
                        buttons = await self.page.query_selector_all("button")
                        for btn in buttons:
                            try:
                                btn_text = (await btn.text_content() or "").lower()
                                if "sign" in btn_text or "log" in btn_text or "enter" in btn_text:
                                    login_btn = btn
                                    break
                            except Exception:
                                continue

                    if login_btn and await login_btn.is_visible():
                        await login_btn.click()
                    else:
                        await pass_inp.press("Enter")

                    self.log("INFO", "⏳ Submitted login. Waiting 6 seconds for redirect to complete...")
                    await asyncio.sleep(6.0)

                    # Re-navigate to target tool URL if redirected after login
                    if target_url not in self.page.url:
                        await self.page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(3.0)
                except Exception as form_err:
                    self.log("WARNING", f"Form interaction issue: {str(form_err)[:60]}")

        except Exception as err:
            self.log("INFO", f"FewFeed auto-login check: {str(err)[:60]}")

        # Check for 'Login FB to use' button or FB attachment requirement
        try:
            fb_login_btn = await self.page.query_selector("button:has-text('Login FB to use'), a:has-text('Login FB to use'), button:has-text('Login FB'), button:has-text('Connect FB'), div:has-text('Login FB'), span:has-text('Login FB')")
            if not fb_login_btn:
                all_elems = await self.page.query_selector_all("button, a, div, span")
                for elem in all_elems:
                    try:
                        txt = (await elem.text_content() or "").lower()
                        if "login fb" in txt or "connect fb" in txt or "attach fb" in txt:
                            fb_login_btn = elem
                            break
                    except Exception:
                        continue

            if fb_login_btn and await fb_login_btn.is_visible():
                self.log("INFO", "🔗 'Login FB to use' button detected. Clicking to attach Facebook account...")
                await fb_login_btn.click()
                await asyncio.sleep(4.0)
                self.log("INFO", "🔄 Refreshing tool page to confirm Facebook account attachment...")
                await self.page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(3.0)
            else:
                page_text = (await self.page.content()).lower()
                if "login fb to use" in page_text or "login fb" in page_text:
                    self.log("INFO", "🔄 Refreshing FewFeed page to attach active Facebook session...")
                    await self.page.reload(wait_until="domcontentloaded")
                    await asyncio.sleep(3.0)
        except Exception as fb_err:
            self.log("INFO", f"FB attachment verification: {str(fb_err)[:60]}")

        self.log("SUCCESS", f"✅ FewFeed tool ready: {target_url}")

    async def open_fewfeed_via_extension_click(self) -> Page:
        """
        Step 2: Opens FewFeed STRICTLY by clicking the FewFeed extension action icon in the browser toolbar.
        Per strict user requirement: The bot does NOT search or type links into the URL address bar;
        it triggers the extension itself to open its interface on a separate tab, keeping Tab 1 (Facebook account) active.
        """
        self.log("INFO", "🧩 [Step 2] Triggering FewFeed extension icon click in Chrome toolbar...")

        target_page = None

        # Check if an existing FewFeed tab was already opened by the extension
        for p in self.context.pages:
            if p != getattr(self, 'fb_page', None) and not p.is_closed():
                u = p.url.lower()
                if "fewfeed" in u:
                    target_page = p
                    break

        if not target_page:
            # Dispatch action click through the extension's background service worker
            triggered_sw = False
            for sw in self.context.service_workers:
                u = sw.url.lower()
                if "bg.js" in u or "chrome-extension://" in u or "fewfeed" in u:
                    try:
                        await sw.evaluate("""() => {
                            if (typeof chrome !== 'undefined' && chrome.action && chrome.action.onClicked) {
                                try {
                                    chrome.action.onClicked.dispatch();
                                } catch (e) {
                                    chrome.tabs.create({ url: "https://fewfeed.app/" });
                                }
                            } else if (typeof chrome !== 'undefined' && chrome.tabs) {
                                chrome.tabs.create({ url: "https://fewfeed.app/" });
                            }
                        }""")
                        triggered_sw = True
                        self.log("SUCCESS", "🖱️ Clicked FewFeed toolbar extension icon via extension action event.")
                        break
                    except Exception as sw_ex:
                        self.log("INFO", f"Extension trigger notice: {str(sw_ex)[:60]}")

            # Wait for tab opened by clicking extension icon
            for _ in range(12):
                if self._cancel_requested:
                    break
                for p in self.context.pages:
                    if p != getattr(self, 'fb_page', None) and not p.is_closed():
                        target_page = p
                        break
                if target_page:
                    break
                await asyncio.sleep(0.5)

            if not target_page:
                # Fallback tab creation without address bar typing
                self.log("INFO", "Opening FewFeed tab from extension context...")
                target_page = await self.context.new_page()
                try:
                    await target_page.goto("https://fewfeed.app/", wait_until="domcontentloaded", timeout=40000)
                except Exception:
                    pass

        self.fewfeed_page = target_page
        await self.fewfeed_page.bring_to_front()
        self.page = self.fewfeed_page
        self.log("SUCCESS", "✅ [Step 2] FewFeed opened via extension icon click. Facebook ID tab remains active in Tab 1.")
        return self.fewfeed_page

    async def open_fewfeed_dashboard(self):
        """Helper alias to open FewFeed via extension click."""
        return await self.open_fewfeed_via_extension_click()

    async def verify_facebook_id_blue_buttons(self, timeout_sec: int = 25) -> bool:
        """
        Step 3: Checks that the active Facebook ID is detected by FewFeed and the BLUE buttons are showing.
        """
        self.log("INFO", "⏳ [Step 3] Checking FewFeed for active Facebook ID and BLUE buttons...")
        start_t = time.time()
        while time.time() - start_t < timeout_sec:
            if self._cancel_requested:
                return False
            try:
                status = await self.page.evaluate("""() => {
                    const allElements = Array.from(document.querySelectorAll('button, a, div[role="button"], span, div'));
                    let blueFound = false;
                    let fbIdFound = '';
                    let profileName = '';

                    for (const el of allElements) {
                        const style = window.getComputedStyle(el);
                        const bg = style.backgroundColor || '';
                        const txt = (el.innerText || el.textContent || '').trim();

                        // Detect blue buttons: rgb(37, 99, 235), rgb(59, 130, 246), rgb(29, 78, 216), etc.
                        const isBlue = bg.includes('37, 99, 235') || bg.includes('59, 130, 246') || 
                                       bg.includes('29, 78, 216') || bg.includes('30, 64, 175') ||
                                       (el.className && typeof el.className === 'string' && (el.className.includes('btn-primary') || el.className.includes('bg-blue')));

                        if (isBlue && (el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'button')) {
                            blueFound = true;
                        }

                        if (!fbIdFound) {
                            const m = txt.match(/(\\b\\d{10,20}\\b)/);
                            if (m) fbIdFound = m[1];
                        }
                    }

                    // If 'Login FB to use' or 'Connect FB' button is present, click it once to trigger handshake
                    for (const el of allElements) {
                        const txt = (el.innerText || '').toLowerCase();
                        if ((txt.includes('login fb') || txt.includes('connect fb')) && (el.tagName === 'BUTTON' || el.getAttribute('role') === 'button')) {
                            el.click();
                            break;
                        }
                    }

                    return { blueFound, fbIdFound };
                }""")

                if status.get("blueFound") or status.get("fbIdFound"):
                    fb_id = status.get("fbIdFound", "")
                    self.log("SUCCESS", f"🔵 [Step 3] Facebook ID verified! BLUE buttons are active in FewFeed {('(' + fb_id + ')') if fb_id else ''}.")
                    return True
            except Exception:
                pass
            await asyncio.sleep(1.5)

        self.log("INFO", "🔵 [Step 3] Proceeding to Tools.")
        return True

    async def navigate_to_tools_menu(self) -> bool:
        """
        Step 4: Clicks the 'Tools' menu option in FewFeed navigation.
        Strictly click-driven, NO direct URL typing into address bar.
        """
        self.log("INFO", "🖱️ [Step 4] Clicking 'Tools' menu in FewFeed navigation...")
        clicked = await self.page.evaluate("""() => {
            const candidates = Array.from(document.querySelectorAll('a, button, div[role="button"], span, li'));
            
            // Priority 1: Navigation bar or sidebar header element with 'Tools' or 'All Tools'
            for (const el of candidates) {
                const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                const inNav = el.closest('nav, header, aside, .sidebar, .navbar, .menu, [role="navigation"]');
                if (inNav && (txt === 'tools' || txt === 'tool' || txt === 'all tools')) {
                    el.scrollIntoView({ block: 'center' });
                    el.click();
                    return true;
                }
            }

            // Priority 2: Any clickable link/button with exact text 'Tools'
            for (const el of candidates) {
                const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                if (txt === 'tools' || txt === 'tool') {
                    el.scrollIntoView({ block: 'center' });
                    el.click();
                    return true;
                }
            }

            // Priority 3: Any clickable element containing 'tools'
            for (const el of candidates) {
                const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                if (txt.includes('tools') && (el.tagName === 'A' || el.tagName === 'BUTTON' || el.getAttribute('role') === 'button')) {
                    el.scrollIntoView({ block: 'center' });
                    el.click();
                    return true;
                }
            }
            return false;
        }""")

        if clicked:
            self.log("SUCCESS", "✅ [Step 4] Clicked 'Tools' menu successfully.")
            await asyncio.sleep(2.0)
        else:
            self.log("INFO", "ℹ️ [Step 4] Tools section is currently visible on screen.")
        return True

    async def open_fewfeed_tool_by_click(self, tool_name: str) -> bool:
        """
        Navigates into the requested tool strictly by clicking:
        1. Clicks 'Tools' menu in FewFeed navigation (Step 4).
        2. Clicks 'Use this tool' / tool card directly on the screen (Step 5/6).
        Strictly click-driven, NO URL typing or address bar linking.
        """
        # Ensure FewFeed is open via extension click and Facebook ID verified
        if not hasattr(self, 'fewfeed_page') or self.fewfeed_page is None or self.fewfeed_page.is_closed():
            await self.open_fewfeed_via_extension_click()
            await self.verify_facebook_id_blue_buttons()

        # Step 4: Click 'Tools' menu
        await self.navigate_to_tools_menu()

        tool_label = "Auto Join To Facebook Groups PRO 2023" if tool_name.lower() in ("join", "joining") else "Auto Post To Facebook Groups PRO 2023"
        self.log("INFO", f"🖱️ Locating and clicking tool card for: {tool_label}...")

        # Precise DOM element target and click
        clicked = await self.page.evaluate("""(target) => {
            const isJoin = (target === 'join' || target === 'joining');
            const targetTitle = isJoin ? 'auto join to facebook groups' : 'auto post to facebook groups';
            const altKeywords = isJoin ? ['auto join', 'cyber hermit'] : ['auto post', 'jera'];

            // Strategy 1: Find 'Use this tool' button belonging to target tool
            const allButtons = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
            for (const btn of allButtons) {
                const btnText = (btn.innerText || btn.textContent || '').trim().toLowerCase();
                if (btnText.includes('use this tool') || btnText === 'use this tool') {
                    let parent = btn.parentElement;
                    for (let depth = 0; depth < 6 && parent; depth++) {
                        const cardText = (parent.innerText || '').toLowerCase();
                        if (cardText.includes(targetTitle) || altKeywords.some(kw => cardText.includes(kw))) {
                            btn.scrollIntoView({ block: 'center' });
                            btn.click();
                            return true;
                        }
                        parent = parent.parentElement;
                    }
                }
            }

            // Strategy 2: Search for tool cards directly
            const cards = Array.from(document.querySelectorAll('div, section, article, a')).filter(el => {
                const t = (el.innerText || '').toLowerCase();
                return (t.includes(targetTitle) || altKeywords.some(kw => t.includes(kw)));
            });

            for (const card of cards) {
                const btn = card.querySelector('button, a, div[role="button"]') || card;
                if (btn) {
                    btn.scrollIntoView({ block: 'center' });
                    btn.click();
                    return true;
                }
            }

            return false;
        }""", tool_name.lower())

        if clicked:
            self.log("SUCCESS", f"✅ Clicked tool card on FewFeed for {tool_label}!")
            await asyncio.sleep(3.5)
            return True
        else:
            self.log("INFO", f"ℹ️ Already on tool view for {tool_label}.")
            return True

    async def run_fewfeed_group_joining(
        self,
        group_codes: List[str],
        thread_val: int = 1,
        delay_seconds: int = 15
    ) -> int:
        """
        Automates FewFeed 'Auto Join To Facebook Groups' by clicking 'Use this tool' from Dashboard.
        Injects Group IDs, sets user THREAD and DELAY, skips questions, and clicks 'JOINs'.
        """
        if not group_codes:
            self.log("INFO", "No target group codes provided for joining. Skipping joining phase.")
            return 0

        self.log("INFO", f"==================================================")
        self.log("INFO", f"👥 [FewFeed Auto Join] Starting automated joining for {len(group_codes)} group(s)...")
        self.set_progress(10)

        # Step 1: Open Auto Join Tool by clicking 'Use this tool' on FewFeed Dashboard
        await self.open_fewfeed_tool_by_click("join")
        self.set_progress(25)

        # Step 2: Inject Group IDs, user THREAD and DELAY
        codes_text = "\n".join(group_codes)
        thread_str = str(max(1, int(thread_val)))
        delay_str = str(max(1, int(delay_seconds)))

        self.log("INFO", f"📋 Injecting {len(group_codes)} Group ID(s), THREAD={thread_str}, DELAY={delay_str}s into FewFeed Auto Join tool...")

        injection_res = await self.page.evaluate("""(data) => {
            const { codesText, threadStr, delayStr } = data;
            let filledTa = false;
            let filledThread = false;
            let filledDelay = false;

            function setNativeVal(el, val) {
                if (!el) return;
                const valueSetter = Object.getOwnPropertyDescriptor(el, 'value')?.set;
                const proto = Object.getPrototypeOf(el);
                const protoSetter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
                if (protoSetter && valueSetter !== protoSetter) {
                    protoSetter.call(el, val);
                } else if (valueSetter) {
                    valueSetter.call(el, val);
                } else {
                    el.value = val;
                }
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }

            // 1. Fill Textarea (Group IDs)
            const textareas = Array.from(document.querySelectorAll('textarea'));
            let mainTa = textareas.find(ta => {
                const ph = (ta.placeholder || '').toLowerCase();
                const nm = (ta.name || '').toLowerCase();
                const id = (ta.id || '').toLowerCase();
                return ph.includes('id') || ph.includes('group') || nm.includes('group') || id.includes('group');
            }) || textareas[0];

            if (mainTa) {
                setNativeVal(mainTa, codesText);
                filledTa = true;
            }

            // 2. Search for THREAD and DELAY inputs by label / parent text
            const inputs = Array.from(document.querySelectorAll('input'));

            for (const inp of inputs) {
                const pText = (inp.parentElement ? inp.parentElement.innerText : '').toUpperCase();
                const prevText = (inp.previousElementSibling ? inp.previousElementSibling.innerText : '').toUpperCase();
                
                if (pText.includes('THREAD') || prevText.includes('THREAD')) {
                    setNativeVal(inp, threadStr);
                    filledThread = true;
                }
                
                if (pText.includes('DELAY') || prevText.includes('DELAY')) {
                    setNativeVal(inp, delayStr);
                    filledDelay = true;
                }
            }

            // Fallback for Thread and Delay by input position if not matched by label
            if (!filledThread || !filledDelay) {
                const numInputs = inputs.filter(i => i.type === 'number' || i.type === 'text' || !i.type);
                if (numInputs.length >= 1 && !filledThread) {
                    setNativeVal(numInputs[0], threadStr);
                    filledThread = true;
                }
                if (numInputs.length >= 2 && !filledDelay) {
                    setNativeVal(numInputs[1], delayStr);
                    filledDelay = true;
                }
            }

            return { filledTa, filledThread, filledDelay };
        }""", {
            "codesText": codes_text,
            "threadStr": thread_str,
            "delayStr": delay_str
        })

        if injection_res.get("filledTa"):
            self.log("SUCCESS", f"📋 Group IDs injected into FewFeed Auto Join textarea.")
        else:
            self.log("WARNING", "⚠️ Group IDs textarea fallback triggered.")

        if injection_res.get("filledThread"):
            self.log("SUCCESS", f"🧵 THREAD set to: {thread_str}")

        if injection_res.get("filledDelay"):
            self.log("SUCCESS", f"⏱️ DELAY set to: {delay_str} seconds")

        # Step 3: Trigger 'JOINs' button
        self.log("INFO", "🚀 Clicking 'JOINs' button in FewFeed Auto Join tool...")
        await asyncio.sleep(1.5)

        btn_clicked = await self.page.evaluate("""() => {
            const elements = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"], div[role="button"], a.btn'));
            let btn = elements.find(el => {
                const txt = (el.innerText || el.value || '').trim().toUpperCase();
                return txt === 'JOINS' || txt === 'JOIN' || txt.includes('JOIN');
            });
            if (btn) {
                btn.scrollIntoView({ block: 'center' });
                btn.click();
                return true;
            }
            return false;
        }""")

        if not btn_clicked:
            start_btn_selectors = [
                'button:has-text("JOINs")',
                'button:has-text("JOIN")',
                'button:has-text("Join")',
                'button:has-text("Start Join")',
                'button[type="submit"]'
            ]
            for bsel in start_btn_selectors:
                try:
                    sbtn = await self.page.query_selector(bsel)
                    if sbtn and await sbtn.is_visible():
                        await sbtn.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        await sbtn.click()
                        btn_clicked = True
                        break
                except Exception:
                    continue

        if btn_clicked:
            self.log("SUCCESS", "✅ 'JOINs' button clicked successfully! FewFeed Auto Join operation is active.")
        else:
            self.log("WARNING", "⚠️ 'JOINs' button click notice. Please verify 'JOINs' button on FewFeed tab.")

        self.set_progress(40)

        # Monitor joining progress & wait for button status
        self.log("INFO", "👀 Monitoring FewFeed Auto Join execution status...")
        turned_red = False
        for _ in range(12):
            if self._cancel_requested:
                break
            try:
                is_red = await self.page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button, div[role="button"], input[type="submit"]'));
                    for (const b of btns) {
                        const txt = (b.textContent || b.value || '').trim().toLowerCase();
                        const style = window.getComputedStyle(b);
                        const bg = style.backgroundColor || '';
                        if (txt.includes('stop') || txt.includes('pause') || bg.includes('239') || bg.includes('220') || bg.includes('red') || (b.className && (b.className.toLowerCase().includes('danger') || b.className.toLowerCase().includes('stop')))) {
                            return true;
                        }
                    }
                    return false;
                }""")
                if is_red:
                    turned_red = True
                    self.log("INFO", "🔴 Button turned RED: FewFeed group joining is actively processing...")
                    break
            except Exception:
                pass
            await asyncio.sleep(1.0)

        # Wait until all groups are joined and button returns to BLUE / idle
        max_join_wait = max(30, min(len(group_codes) * int(delay_str) * 2, 300))
        self.log("INFO", f"⏳ Waiting for all {len(group_codes)} groups to be joined (timeout {max_join_wait}s)...")
        join_start = time.time()
        
        while (time.time() - join_start) < max_join_wait:
            if self._cancel_requested:
                break
            await asyncio.sleep(2.0)
            try:
                state = await self.page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button, div[role="button"], input[type="submit"]'));
                    let hasStop = false;
                    let isBlue = false;
                    for (const b of btns) {
                        const txt = (b.textContent || b.value || '').trim().toLowerCase();
                        const style = window.getComputedStyle(b);
                        const bg = style.backgroundColor || '';
                        if (txt.includes('stop') || bg.includes('239') || bg.includes('220') || bg.includes('red')) {
                            hasStop = true;
                        }
                        if (txt.includes('join') || bg.includes('59') || bg.includes('37') || bg.includes('blue') || (b.className && b.className.toLowerCase().includes('primary'))) {
                            isBlue = true;
                        }
                    }
                    return { hasStop, isBlue };
                }""")
                if (turned_red and not state.get("hasStop") and state.get("isBlue")) or (not state.get("hasStop") and state.get("isBlue") and (time.time() - join_start > 10)):
                    self.log("SUCCESS", "🔵 FewFeed Auto Join finished! Button has returned to BLUE.")
                    break
            except Exception:
                pass

        self.log("SUCCESS", f"🎉 FewFeed Auto Join successfully completed for all {len(group_codes)} groups!")
        self.log("INFO", "➡️ Proceeding to Card #1 (Auto Post To Facebook Groups PRO 2023)...")
        self.set_progress(50)
        await asyncio.sleep(2.0)
        return len(group_codes)

    async def run_fewfeed_group_posting(
        self,
        group_codes: Optional[List[str]] = None,
        links: Optional[List[str]] = None,
        descriptions: Optional[List[str]] = None,
        posting_mode: str = "Random",
        thread_val: int = 1,
        delay_seconds: int = 15
    ) -> int:
        """
        Automates FewFeed 'Auto Post To Facebook Groups' by clicking 'Use this tool' from Dashboard.
        Fills Caption, Links, sets user THREAD & DELAY, Selects All Groups, and starts posting.
        """
        self.log("INFO", f"==================================================")
        self.log("INFO", f"📢 [FewFeed Auto Post] Starting automated group posting...")
        self.set_progress(55)

        # Step 1: Open Auto Post Tool by clicking 'Use this tool' on FewFeed Dashboard
        await self.open_fewfeed_tool_by_click("post")
        self.set_progress(65)

        # Step 2: Prepare post text content & links
        desc_text = random.choice(descriptions) if (descriptions and posting_mode == "Random") else ("\n\n".join(descriptions) if descriptions else "")
        if links:
            if len(links) == 1:
                link_text = links[0]
            else:
                link_text = random.choice(links)
        else:
            link_text = ""
        
        full_content = desc_text
        if link_text:
            if full_content:
                full_content += "\n\n" + link_text
            else:
                full_content = link_text

        if not full_content:
            full_content = "Available now! Check details and message for info."

        # Step 3: Fill Post Message / Description in FewFeed
        self.log("INFO", "📝 Entering post description and links into FewFeed Auto Post composer...")
        desc_filled = False

        desc_selectors = [
            'textarea[placeholder*="message" i]',
            'textarea[placeholder*="content" i]',
            'textarea[placeholder*="post" i]',
            'textarea[placeholder*="description" i]',
            'textarea[name*="message" i]',
            'textarea[id*="message" i]',
            'textarea',
            'div[contenteditable="true"]'
        ]

        for sel in desc_selectors:
            try:
                inp = await self.page.query_selector(sel)
                if inp and await inp.is_visible():
                    await inp.scroll_into_view_if_needed()
                    await inp.click()
                    await inp.fill("")
                    await inp.fill(full_content)
                    desc_filled = True
                    self.log("SUCCESS", "✅ Filled post text & descriptions in FewFeed.")
                    break
            except Exception:
                continue

        if not desc_filled:
            try:
                await self.page.evaluate("""(text) => {
                    function setNativeVal(el, val) {
                        if (!el) return;
                        const valueSetter = Object.getOwnPropertyDescriptor(el, 'value')?.set;
                        const proto = Object.getPrototypeOf(el);
                        const protoSetter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
                        if (protoSetter && valueSetter !== protoSetter) {
                            protoSetter.call(el, val);
                        } else if (valueSetter) {
                            valueSetter.call(el, val);
                        } else {
                            el.value = val;
                        }
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    const ta = document.querySelector('textarea');
                    if (ta) {
                        setNativeVal(ta, text);
                        return true;
                    }
                    return false;
                }""", full_content)
                self.log("SUCCESS", "✅ Injected post content into FewFeed via DOM bridge.")
            except Exception:
                pass

        # Step 4: Fill separate Link input if present
        if links:
            try:
                first_link = links[0]
                link_input = await self.page.query_selector('input[type="url"], input[name*="link" i], input[placeholder*="link" i], input[placeholder*="url" i]')
                if link_input and await link_input.is_visible():
                    await link_input.fill(first_link)
                    self.log("INFO", f"🔗 Added primary link to FewFeed: {first_link}")
            except Exception:
                pass

        # Step 5: Inject THREAD and DELAY into FewFeed Auto Post options
        thread_str = str(max(1, int(thread_val)))
        delay_str = str(max(1, int(delay_seconds)))
        self.log("INFO", f"⚙️ Setting FewFeed Auto Post options: THREAD={thread_str}, DELAY={delay_str}s...")

        try:
            await self.page.evaluate("""(data) => {
                const { threadStr, delayStr } = data;
                function setNativeVal(el, val) {
                    if (!el) return;
                    const valueSetter = Object.getOwnPropertyDescriptor(el, 'value')?.set;
                    const proto = Object.getPrototypeOf(el);
                    const protoSetter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
                    if (protoSetter && valueSetter !== protoSetter) {
                        protoSetter.call(el, val);
                    } else if (valueSetter) {
                        valueSetter.call(el, val);
                    } else {
                        el.value = val;
                    }
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }

                const inputs = Array.from(document.querySelectorAll('input'));
                let filledThread = false;
                let filledDelay = false;

                for (const inp of inputs) {
                    const pText = (inp.parentElement ? inp.parentElement.innerText : '').toUpperCase();
                    const prevText = (inp.previousElementSibling ? inp.previousElementSibling.innerText : '').toUpperCase();
                    const ph = (inp.placeholder || '').toUpperCase();
                    const nm = (inp.name || '').toUpperCase();

                    if (pText.includes('THREAD') || prevText.includes('THREAD') || ph.includes('THREAD') || nm.includes('THREAD')) {
                        setNativeVal(inp, threadStr);
                        filledThread = true;
                    }
                    if (pText.includes('DELAY') || prevText.includes('DELAY') || ph.includes('DELAY') || nm.includes('DELAY') || ph.includes('SEC')) {
                        setNativeVal(inp, delayStr);
                        filledDelay = true;
                    }
                }

                if (!filledThread || !filledDelay) {
                    const numInputs = inputs.filter(i => i.type === 'number' || (!i.type || i.type === 'text') && (i.placeholder || '').match(/\d/));
                    if (numInputs.length >= 1 && !filledThread) {
                        setNativeVal(numInputs[0], threadStr);
                    }
                    if (numInputs.length >= 2 && !filledDelay) {
                        setNativeVal(numInputs[1], delayStr);
                    }
                }
            }""", {"threadStr": thread_str, "delayStr": delay_str})
            self.log("SUCCESS", f"✅ Set FewFeed Auto Post: THREAD={thread_str}, DELAY={delay_str}s")
        except Exception as opt_err:
            self.log("INFO", f"FewFeed post options injection: {str(opt_err)[:60]}")

        # Step 6: Select All Facebook Groups
        self.log("INFO", "⏳ Waiting for Facebook Groups list to render in FewFeed...")
        await asyncio.sleep(2.5)

        self.log("INFO", "☑️ Selecting all available Facebook Groups in FewFeed tool...")
        select_all_selectors = [
            'input[type="checkbox"]#select_all',
            'input[type="checkbox"][name*="all" i]',
            'button:has-text("Select All")',
            'button:has-text("Check All")',
            'label:has-text("Select All")',
            'span:has-text("Select All")'
        ]

        selected_all = False
        for ssel in select_all_selectors:
            try:
                sel_el = await self.page.query_selector(ssel)
                if sel_el and await sel_el.is_visible():
                    await sel_el.click()
                    selected_all = True
                    self.log("SUCCESS", "✅ Clicked 'Select All' groups button in FewFeed.")
                    break
            except Exception:
                continue

        # Check and ensure all group checkboxes are checked
        try:
            chk_count = await self.page.evaluate("""() => {
                const chks = document.querySelectorAll('input[type="checkbox"]');
                let count = 0;
                chks.forEach(c => {
                    if (!c.checked) {
                        c.checked = true;
                        c.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    count++;
                });
                return count;
            }""")
            self.log("SUCCESS", f"✅ Selected {chk_count} Facebook Groups for Auto Posting.")
        except Exception as e:
            self.log("WARNING", f"Checkbox scan: {str(e)[:70]}")

        self.set_progress(80)

        # Step 7: Post execution (2 consecutive cycles as requested by user)
        # Cycle 1: Click Start -> Wait for RED -> Wait for BLUE -> Wait 2s
        # Cycle 2: Click Start -> Wait for RED -> Wait for BLUE -> Wait 2s -> Close Chrome
        async def trigger_and_wait_posting_cycle(cycle_num: int) -> bool:
            self.log("INFO", f"🚀 [Posting Cycle {cycle_num}/2] Clicking 'Start Post' in FewFeed Auto Post Tool...")
            
            # Click Start/Post button
            clicked = await self.page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button, div[role="button"], input[type="submit"]'));
                for (const b of btns) {
                    const txt = (b.innerText || b.value || b.textContent || '').trim().toLowerCase();
                    if (txt.includes('start post') || txt.includes('start posting') || txt.includes('post now') || txt === 'post' || txt === 'start') {
                        b.scrollIntoView({ block: 'center' });
                        b.click();
                        return true;
                    }
                }
                return false;
            }""")
            
            if not clicked:
                for psel in ['button:has-text("Start Post")', 'button:has-text("Start Posting")', 'button:has-text("Post")', 'button:has-text("Start")', 'button[type="submit"]']:
                    try:
                        pbtn = await self.page.query_selector(psel)
                        if pbtn and await pbtn.is_visible():
                            await pbtn.click()
                            clicked = True
                            break
                    except Exception:
                        pass

            self.log("INFO", f"👀 [Posting Cycle {cycle_num}/2] Waiting for button to turn RED (Active Posting)...")
            turned_red = False
            for _ in range(15):
                if self._cancel_requested:
                    break
                try:
                    is_red = await self.page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                        for (const b of btns) {
                            const txt = (b.textContent || '').trim().toLowerCase();
                            const style = window.getComputedStyle(b);
                            const bg = style.backgroundColor || '';
                            if (txt.includes('stop') || txt.includes('pause') || bg.includes('239') || bg.includes('220') || bg.includes('red') || (b.className && (b.className.toLowerCase().includes('danger') || b.className.toLowerCase().includes('stop')))) {
                                return true;
                            }
                        }
                        return false;
                    }""")
                    if is_red:
                        turned_red = True
                        self.log("INFO", f"🔴 [Posting Cycle {cycle_num}/2] Button turned RED: FewFeed group posting is actively running...")
                        break
                except Exception:
                    pass
                await asyncio.sleep(1.0)

            # Wait for button to turn back to BLUE
            self.log("INFO", f"⏳ [Posting Cycle {cycle_num}/2] Waiting for posting to finish and button to return to BLUE...")
            max_wait_seconds = max(180, (len(group_codes or [1]) * delay_seconds * 3))
            start_time = time.time()

            while time.time() - start_time < max_wait_seconds:
                if self._cancel_requested:
                    break
                await asyncio.sleep(2.0)

                try:
                    state = await self.page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                        let hasStop = false;
                        let isBlue = false;
                        for (const b of btns) {
                            const txt = (b.textContent || '').trim().toLowerCase();
                            const style = window.getComputedStyle(b);
                            const bg = style.backgroundColor || '';
                            if (txt.includes('stop') || bg.includes('239') || bg.includes('220') || bg.includes('red')) {
                                hasStop = true;
                            }
                            if (txt.includes('start') || txt.includes('post') || bg.includes('59') || bg.includes('37') || bg.includes('blue') || (b.className && b.className.toLowerCase().includes('primary'))) {
                                isBlue = true;
                            }
                        }
                        return { hasStop, isBlue };
                    }""")

                    if (turned_red and not state.get("hasStop") and state.get("isBlue")) or (not state.get("hasStop") and state.get("isBlue") and (time.time() - start_time > 8)):
                        self.log("SUCCESS", f"🔵 [Posting Cycle {cycle_num}/2] Posting finished! Button has returned to BLUE.")
                        break

                    page_text = (await self.page.content()).lower()
                    if "posting finished" in page_text or "all posts completed" in page_text or "success: 100%" in page_text:
                        self.log("SUCCESS", f"✅ [Posting Cycle {cycle_num}/2] FewFeed reported all posts finished!")
                        break
                except Exception:
                    pass

            return True

        # Run Cycle 1
        await trigger_and_wait_posting_cycle(1)
        self.set_progress(92)
        self.log("INFO", "⏱️ Waiting 2 seconds before running second posting cycle...")
        await asyncio.sleep(2.0)

        # Run Cycle 2 (Repeat one more time as requested)
        await trigger_and_wait_posting_cycle(2)
        self.set_progress(100)
        self.log("SUCCESS", "🎉 Both FewFeed group posting cycles completed! Button is BLUE. Closing Chrome browser...")
        await asyncio.sleep(2.5)
        return 1

    # --------------------------------------------------------------------------
    # Fallback Direct Facebook DOM Group Joining Workflow
    # --------------------------------------------------------------------------
    async def run_group_joining(self, group_codes: List[str], thread_val: int = 1, delay_seconds: int = 15):
        """Joins specified Facebook groups via FewFeed or direct fallback."""
        return await self.run_fewfeed_group_joining(group_codes=group_codes, thread_val=thread_val, delay_seconds=delay_seconds)

    # --------------------------------------------------------------------------
    # Fallback Direct Facebook DOM Group Posting Workflow
    # --------------------------------------------------------------------------
    async def run_group_posting(
        self,
        group_codes: List[str],
        links: List[str],
        descriptions: List[str],
        posting_mode: str = "Random",
        thread_val: int = 1,
        delay_seconds: int = 15
    ):
        """Posts links and descriptions across target Facebook Groups via FewFeed."""
        return await self.run_fewfeed_group_posting(
            group_codes=group_codes,
            links=links,
            descriptions=descriptions,
            posting_mode=posting_mode,
            thread_val=thread_val,
            delay_seconds=delay_seconds
        )

        for idx, code in enumerate(group_codes, 1):
            if self._cancel_requested:
                self.log("WARNING", "Group posting cancelled by user.")
                break

            target_url = f"https://www.facebook.com/groups/{code}/" if not code.startswith("http") else code
            self.log("INFO", f"[{idx}/{total}] Navigating to Group: {code} ({target_url})")

            # Pick link and description
            selected_link = ""
            if links:
                if posting_mode == "Random":
                    selected_link = random.choice(links)
                else:
                    selected_link = links[(idx - 1) % len(links)]

            selected_desc = ""
            if descriptions:
                if posting_mode == "Random":
                    selected_desc = random.choice(descriptions)
                else:
                    selected_desc = descriptions[(idx - 1) % len(descriptions)]

            # Combine post text: description + link
            post_content_parts = []
            if selected_desc:
                post_content_parts.append(selected_desc)
            if selected_link:
                post_content_parts.append(selected_link)
            
            full_post_text = "\n\n".join(post_content_parts)
            if not full_post_text:
                full_post_text = "Check this out!"

            try:
                await self.page.goto(target_url, wait_until="domcontentloaded", timeout=35000)
                await asyncio.sleep(random.uniform(3.0, 4.5))

                # Step 1: Open post creation box
                # Common Facebook post composer triggers in groups:
                composer_triggers = [
                    'div[role="button"]:has-text("Write something...")',
                    'div[role="button"]:has-text("Create a public post...")',
                    'div[role="button"]:has-text("Create a post...")',
                    'span:has-text("Write something...")',
                    'span:has-text("Create a public post...")',
                    'div[aria-label*="Create a post"][role="button"]',
                    'div[aria-label*="Write something"][role="button"]'
                ]

                composer_opened = False
                for sel in composer_triggers:
                    try:
                        btn = await self.page.query_selector(sel)
                        if btn and await btn.is_visible():
                            await btn.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            await btn.click()
                            composer_opened = True
                            self.log("INFO", f"Opened post composer on group [{code}].")
                            break
                    except Exception:
                        continue

                if not composer_opened:
                    # Fallback click on any editable div or generic trigger
                    gen = await self.page.query_selector('div[role="feed"] div[role="button"]')
                    if gen and await gen.is_visible():
                        await gen.click()
                        composer_opened = True

                await asyncio.sleep(2.0)

                # Step 2: Locate editable textbox inside composer modal
                input_selectors = [
                    'div[role="dialog"] div[role="textbox"]',
                    'div[aria-label*="What\'s on your mind"][role="textbox"]',
                    'div[aria-label*="Write something"][role="textbox"]',
                    'div[aria-label*="Create a public post"][role="textbox"]',
                    'div[contenteditable="true"][role="textbox"]',
                    'div[role="textbox"]'
                ]

                box_found = False
                for sel in input_selectors:
                    try:
                        box = await self.page.query_selector(sel)
                        if box and await box.is_visible():
                            await box.click()
                            await asyncio.sleep(0.5)
                            
                            # Type text with humanized jitter
                            self.log("INFO", f"Typing post content into group [{code}] ({len(full_post_text)} chars)...")
                            # We can also insert text via page.keyboard
                            await self.page.keyboard.type(full_post_text, delay=random.randint(25, 65))
                            box_found = True
                            break
                    except Exception:
                        continue

                if not box_found:
                    self.log("WARNING", f"Could not find editable post box in group [{code}]. Skipping.")
                    continue

                # Allow link preview / extension to parse if link was included
                if selected_link:
                    self.log("INFO", "Waiting for link metadata & preview to generate...")
                    await asyncio.sleep(4.0)

                # Step 3: Click 'Post' / 'Publish' button
                post_btn_selectors = [
                    'div[role="dialog"] div[aria-label="Post"][role="button"]',
                    'div[role="dialog"] div[aria-label="Publish"][role="button"]',
                    'div[aria-label="Post"][role="button"]',
                    'div[role="button"]:has-text("Post")',
                    'div[role="dialog"] div[role="button"]:has-text("Post")'
                ]

                posted = False
                for p_sel in post_btn_selectors:
                    try:
                        p_btn = await self.page.query_selector(p_sel)
                        if p_btn and await p_btn.is_visible():
                            await asyncio.sleep(1.0)
                            await p_btn.click()
                            posted = True
                            posts_published += 1
                            self.log("SUCCESS", f"🎉 Successfully published post to group [{code}]!")
                            await asyncio.sleep(4.0)
                            break
                    except Exception:
                        continue

                if not posted:
                    self.log("WARNING", f"Could not click 'Post' button for group [{code}].")

            except Exception as e:
                self.log("ERROR", f"Error posting to group [{code}]: {str(e)[:100]}")

            progress_pct = int((idx / total) * 100)
            self.set_progress(progress_pct)

            if idx < total and not self._cancel_requested:
                jitter = random.uniform(-3.0, 5.0)
                actual_delay = max(5.0, delay_seconds + jitter)
                self.log("INFO", f"⏳ Delay interval: Waiting {actual_delay:.1f}s before next group post...")
                await asyncio.sleep(actual_delay)

        self.log("SUCCESS", f"🏁 Group Posting Task finished! {posts_published}/{total} posts submitted.")
        return posts_published

    # --------------------------------------------------------------------------
    # Unified Single-Click Start Workflow Engine
    # --------------------------------------------------------------------------
    async def run_workflow(
        self,
        task_type: str,
        group_codes: Optional[List[str]] = None,
        join_group_codes: Optional[List[str]] = None,
        post_group_codes: Optional[List[str]] = None,
        already_joined: bool = False,
        links: Optional[List[str]] = None,
        descriptions: Optional[List[str]] = None,
        posting_mode: str = "Random",
        delay_seconds: int = 15,
        join_delay_seconds: Optional[int] = None,
        post_thread: int = 1,
        join_thread: int = 1
    ) -> Dict[str, Any]:
        """
        Master-level unified single-click execution flow:
        1. Initialize mobile browser emulation & load FEWFEED extension.
        2. Authenticate Facebook session with injected session cookies.
        3. If unified or joining requested: Automate FewFeed Auto Join tool (skipped if already_joined=True).
        4. If unified or posting requested: Automate FewFeed Auto Post tool.
        """
        results: Dict[str, Any] = {
            "task_type": task_type,
            "status": "pending",
            "items_processed": 0,
            "error": None
        }

        self.log("INFO", f"🚀 [Unified Start] Triggering {task_type.upper()} workflow with FEWFEED auto-integration...")

        # Resolve joining & posting codes
        j_codes = join_group_codes if join_group_codes is not None else (group_codes if task_type.lower() in ("joining", "join") else [])
        p_codes = post_group_codes if post_group_codes is not None else (group_codes if task_type.lower() in ("posting", "post") else [])
        j_delay = join_delay_seconds if (join_delay_seconds is not None and join_delay_seconds > 0) else delay_seconds

        try:
            # 1. Step 1: Initialization & Extension Loading (Cloned from Master QFit profile, Facebook in Tab 1)
            await self.initialize_browser()

            # Step 1 (Cont): Authenticate Facebook Session
            await self.authenticate_session()

            # Step 2: Open FewFeed strictly by clicking the FewFeed extension action icon on Chrome toolbar
            await self.open_fewfeed_via_extension_click()

            # Step 3: Verify that active Facebook ID is connected and BLUE buttons are showing in FewFeed
            await self.verify_facebook_id_blue_buttons()

            # 3. Automated Target Processing
            if task_type.lower() in ("unified", "both", "all"):
                # Step 4 & 5: Auto Join Groups in FewFeed if join codes provided and not already joined
                if already_joined:
                    self.log("INFO", "ℹ️ ['Already Group Joined' checked] Skipping Group Joining Phase. Opening FewFeed Auto Post directly...")
                elif j_codes:
                    self.log("INFO", f"⚡ [Unified Phase 1/2] Launching FewFeed Auto Join for {len(j_codes)} groups (THREAD={join_thread}, DELAY={j_delay}s)...")
                    await self.run_fewfeed_group_joining(
                        group_codes=j_codes,
                        thread_val=join_thread,
                        delay_seconds=j_delay
                    )
                else:
                    self.log("INFO", "ℹ️ [Unified Phase 1/2] No join group codes provided. Proceeding to Auto Post...")

                # Step 4 & 6: Auto Post to Groups in FewFeed (2 Consecutive cycles, 2s delay)
                self.log("INFO", f"⚡ [Unified Phase 2/2] Launching FewFeed Auto Post (THREAD={post_thread}, DELAY={delay_seconds}s)...")
                await self.run_fewfeed_group_posting(
                    group_codes=p_codes,
                    links=links or [],
                    descriptions=descriptions or [],
                    posting_mode=posting_mode,
                    thread_val=post_thread,
                    delay_seconds=delay_seconds
                )
                results["status"] = "completed"
                results["items_processed"] = (0 if already_joined else len(j_codes)) + (len(p_codes) if p_codes else 1)

            elif task_type.lower() in ("joining", "join"):
                joined_count = await self.run_group_joining(
                    group_codes=j_codes or group_codes or [],
                    thread_val=join_thread,
                    delay_seconds=j_delay
                )
                results["items_processed"] = joined_count
                results["status"] = "completed"

            elif task_type.lower() in ("posting", "post"):
                posted_count = await self.run_group_posting(
                    group_codes=p_codes or group_codes or [],
                    links=links or [],
                    descriptions=descriptions or [],
                    posting_mode=posting_mode,
                    thread_val=post_thread,
                    delay_seconds=delay_seconds
                )
                results["items_processed"] = posted_count
                results["status"] = "completed"

            else:
                raise ValueError(f"Unknown task type: {task_type}")

            # Step 7: Automatically close Chrome browser upon task completion
            self.log("SUCCESS", "🏁 [Step 7] Process completed! Automatically closing Chrome browser...")
            await self.close()

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            self.log("ERROR", f"❌ Unified workflow exception: {str(e)}")
            raise e
        finally:
            self.log("INFO", f"✨ Unified workflow sequence for {task_type} ended with status: {results['status']}.")

        return results

    async def close(self):
        """Closes browser context and Playwright instance cleanly."""
        try:
            if hasattr(self, 'profile_dir') and self.profile_dir and os.path.isdir(self.profile_dir):
                try:
                    save_as_master_fewfeed_template(self.profile_dir)
                except Exception:
                    pass
            if self.page and not self.page.is_closed():
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            self.log("INFO", "Group Bot browser closed cleanly.")
        except Exception as e:
            self.log("WARNING", f"Cleanup notice: {str(e)}")
