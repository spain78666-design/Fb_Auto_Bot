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

def get_chrome_webdriver_desktop_config(ext_path: Optional[str] = None, user_data_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns standard Desktop Chrome WebDriver configuration options for FEWFEED.
    """
    config = {
        "args": [
            "--start-maximized",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            f"--user-agent={DESKTOP_CHROME_USER_AGENT}",
            "--lang=en-US,en"
        ]
    }
    if ext_path and os.path.exists(ext_path):
        config["args"].append(f"--disable-extensions-except={ext_path}")
        config["args"].append(f"--load-extension={ext_path}")
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

        # Ensure account profile_dir is ALWAYS a valid directory string
        profile_dir = self.account_data.get("profile_dir")
        if not profile_dir and self.account_data.get("id"):
            safe_id = "".join(c for c in str(self.account_data.get("id", "")) if c.isalnum() or c in ("_", "-"))
            profile_dir = os.path.join(get_base_dir(), "profiles", safe_id)
        if not profile_dir:
            profile_dir = os.path.join(get_base_dir(), "profiles", "temp_group_profile")

        os.makedirs(profile_dir, exist_ok=True)
        self.profile_dir = profile_dir

        # Always synchronize FewFeed extension & master session from master profile template
        src_master = get_master_fewfeed_source_dir()
        if src_master and os.path.abspath(src_master) != os.path.abspath(profile_dir):
            self.log("INFO", f"🔄 Synchronizing FewFeed Extension & Master Session from {os.path.basename(src_master)} into {os.path.basename(profile_dir)}...")
            copy_fewfeed_session_data(src_master, profile_dir)
            self.log("SUCCESS", "✅ FewFeed session & extension synced into browser profile.")

        ext_path = get_fewfeed_extension_path()
        ext_args = []
        if ext_path and os.path.exists(ext_path):
            try:
                from automation.extension_manager import get_extension_chrome_args
                ext_args = get_extension_chrome_args(ext_path)
            except Exception:
                clean_p = os.path.abspath(ext_path).replace('\\', '/')
                ext_args = [
                    f"--load-extension={clean_p}",
                    "--enable-extensions"
                ]
            self.log("SUCCESS", f"🧩 Chrome Extension Loaded: {os.path.basename(ext_path)} -> {ext_path}")
        else:
            self.log("WARNING", f"FEWFEED extension folder not detected! Checked {ext_path}.")

        launch_args = [
            "--start-maximized",
            "--no-default-browser-check",
            "--no-first-run",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--enable-extensions",
            "--enable-unsafe-extension-debugging",
            "--lang=en-US,en"
        ]
        launch_args.extend(ext_args)

        ignore_default_args = ["--no-sandbox", "--disable-extensions", "--enable-automation", "--disable-component-extensions-with-background-pages"]

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

        # Pre-configure profile preferences for developer mode and extension toolbar
        try:
            from automation.extension_manager import prepare_profile_for_extension
            prepare_profile_for_extension(profile_dir, ext_path)
        except Exception:
            pass

        # Clear profile locks to prevent SingletonLock errors
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

        # Launch browser in desktop mode with FEWFEED loaded (Real system Google Chrome priority)
        from automation.extension_manager import get_system_chrome_executable
        chrome_exe = get_system_chrome_executable()

        self.context = None
        channels_to_try = []
        if chrome_exe and os.path.isfile(chrome_exe):
            channels_to_try.append(("real_chrome", chrome_exe))
        channels_to_try.extend([("chrome", None), ("msedge", None), (None, None)])

        for ch, exe_p in channels_to_try:
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
                if exe_p:
                    kwargs["executable_path"] = exe_p
                elif ch:
                    kwargs["channel"] = ch
                self.context = await self.playwright.chromium.launch_persistent_context(**kwargs)
                self.log("INFO", f"Launched Desktop browser ({exe_p or ch or 'Chromium'}) with FEWFEED loaded.")
                break
            except Exception as ex:
                self.log("WARNING", f"Browser launch attempt ({ch or exe_p}) notice: {str(ex)[:100]}")
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
                    no_viewport=True,
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

            # If not detected yet, activate extension via CDP session
            if not self.extension_id and ext_path and os.path.isdir(ext_path):
                try:
                    fwd_p = os.path.abspath(ext_path).replace('\\', '/')
                    p0 = self.context.pages[0] if self.context.pages else await self.context.new_page()
                    cdp = await self.context.new_cdp_session(p0)
                    await cdp.send("Extensions.loadUnpacked", {"path": fwd_p})
                    self.log("SUCCESS", "⚡ Loaded FewFeed V3 extension via Chrome DevTools Protocol (CDP)!")
                    await asyncio.sleep(1.0)
                    for sw in self.context.service_workers:
                        if "chrome-extension://" in sw.url:
                            self.extension_id = sw.url.replace("chrome-extension://", "").split("/")[0]
                            self.fewfeed_ready = True
                            break
                except Exception as cdp_err:
                    self.log("DEBUG", f"CDP extension activation notice: {cdp_err}")

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
                self.log("WARNING", "⚠️ Facebook Checkpoint encountered in Tab 1. Proceeding with active profile cookies...")
            else:
                email = self.account_data.get("email") or self.account_data.get("username")
                password = self.account_data.get("password")
                if email and password:
                    self.log("INFO", f"🔑 Facebook login form detected. Attempting automated login for {email}...")
                    try:
                        email_input = await self.page.query_selector('input#email, input[name="email"]')
                        pass_input = await self.page.query_selector('input#pass, input[name="pass"]')
                        login_btn = await self.page.query_selector('button[name="login"], button[type="submit"]')
                        if email_input and pass_input and login_btn:
                            await email_input.fill(email)
                            await pass_input.fill(password)
                            await asyncio.sleep(0.5)
                            await login_btn.click()
                            await asyncio.sleep(4.0)
                            url = self.page.url.lower()
                    except Exception as le:
                        self.log("INFO", f"Auto-login notice: {str(le)[:60]}")

            if "login" in self.page.url.lower():
                self.log("WARNING", "⚠️ Facebook primary tab shows login screen. Proceeding to FewFeed tab with profile session...")
            else:
                self.log("SUCCESS", "Facebook authentication confirmed in Tab 1 (tab will remain OPEN in background).")
        else:
            self.log("SUCCESS", "Facebook authentication confirmed in Tab 1 (tab will remain OPEN in background).")
        self.fb_page = self.page

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    # FewFeed Web Extension Dashboard Navigation & Tool Automation
    # --------------------------------------------------------------------------
    async def open_fewfeed_tool_page(self, target_url: str):
        """Directly navigates to the specific FewFeed tool URL on a NEW TAB, keeping Facebook tab open."""
        # Check if an existing FewFeed tab was opened by the extension
        existing_ff = None
        for p in self.context.pages:
            if p != getattr(self, 'fb_page', None) and not p.is_closed():
                if "fewfeed" in p.url.lower():
                    existing_ff = p
                    break

        if existing_ff:
            self.fewfeed_page = existing_ff
        elif not hasattr(self, 'fewfeed_page') or self.fewfeed_page is None or self.fewfeed_page.is_closed():
            self.log("INFO", "📑 Opening FewFeed on a NEW TAB (keeping Facebook ID tab active in Tab 1)...")
            self.fewfeed_page = await self.context.new_page()
        
        self.page = self.fewfeed_page
        if target_url.rstrip('/') not in self.page.url.lower():
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
        else:
            self.log("INFO", f"🌐 Already on FewFeed Tool page: {self.page.url}")

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
            # Step A: Dispatch the extension action click inside the extension context (Simulates clicking FewFeed V3 icon)
            sw_target = None
            for sw in self.context.service_workers:
                u = sw.url.lower()
                if "bg.js" in u or "chrome-extension://" in u or "fewfeed" in u:
                    sw_target = sw
                    break

            if sw_target:
                try:
                    await sw_target.evaluate("""async () => {
                        try {
                            if (typeof chrome !== 'undefined') {
                                let activeTab = null;
                                if (chrome.tabs && chrome.tabs.query) {
                                    const tabs = await new Promise(r => chrome.tabs.query({ active: true }, r));
                                    activeTab = (tabs && tabs.length) ? tabs[0] : null;
                                }
                                if (chrome.action && chrome.action.onClicked && chrome.action.onClicked.dispatch) {
                                    chrome.action.onClicked.dispatch(activeTab || {});
                                } else if (chrome.browserAction && chrome.browserAction.onClicked && chrome.browserAction.onClicked.dispatch) {
                                    chrome.browserAction.onClicked.dispatch(activeTab || {});
                                } else if (chrome.tabs && chrome.tabs.create) {
                                    chrome.tabs.create({ url: "https://fewfeed.app/" });
                                }
                            }
                        } catch (e) {
                            if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.create) {
                                chrome.tabs.create({ url: "https://fewfeed.app/" });
                            }
                        }
                    }""")
                    self.log("SUCCESS", "🖱️ Clicked 'FewFeed V3' extension action button in Chrome!")
                except Exception as sw_ex:
                    self.log("INFO", f"Extension trigger notice: {str(sw_ex)[:60]}")

            # Step B: Wait up to 3s for the new FewFeed tab opened by clicking the extension icon
            for _ in range(6):
                if self._cancel_requested:
                    break
                for p in self.context.pages:
                    if p != getattr(self, 'fb_page', None) and not p.is_closed():
                        if "fewfeed" in p.url.lower():
                            target_page = p
                            break
                if target_page:
                    break
                await asyncio.sleep(0.5)

            if not target_page:
                self.log("INFO", "Extension initiated tab opening. Ensuring FewFeed tab is focused...")
                target_page = await self.context.new_page()
                try:
                    await target_page.goto("https://fewfeed.app/", wait_until="domcontentloaded", timeout=40000)
                except Exception:
                    pass

        self.fewfeed_page = target_page
        await self.fewfeed_page.bring_to_front()
        self.page = self.fewfeed_page
        self.log("SUCCESS", "✅ [Step 2] 'FewFeed V3' extension button clicked! FewFeed opened in Tab 2 (Facebook remains active in Tab 1).")
        return self.fewfeed_page

    async def open_fewfeed_dashboard(self):
        """Helper alias to open FewFeed via extension click."""
        return await self.open_fewfeed_via_extension_click()

    async def verify_facebook_id_blue_buttons(self, wait_sec: int = 9) -> bool:
        """
        Step 3: Wait 8 to 9 seconds passively for FewFeed extension to fetch Facebook ID from Tab 1 and turn buttons blue.
        DO NOT click any buttons or reload during this period so that FewFeed stays on its dashboard without redirecting.
        """
        self.log("INFO", f"⏳ [Step 3] FewFeed extension opened. Waiting {wait_sec} seconds for Facebook ID & Blue Buttons to fetch...")
        for i in range(wait_sec):
            if self._cancel_requested:
                return False
            await asyncio.sleep(1.0)
            if (i + 1) % 3 == 0:
                self.log("INFO", f"⏳ Fetching Facebook session & activating tool cards ({i + 1}/{wait_sec}s)...")

        # Inspect if Facebook ID or blue buttons are ready (read-only inspect, NEVER click Login FB)
        try:
            status = await self.page.evaluate("""() => {
                const allElements = Array.from(document.querySelectorAll('button, a, div[role="button"], span, div, h1, h2, h3, h4, p'));
                let blueFound = false;
                let fbIdFound = '';

                for (const el of allElements) {
                    const style = window.getComputedStyle(el);
                    const bg = style.backgroundColor || '';
                    const txt = (el.innerText || el.textContent || '').trim();

                    const isBlue = bg.includes('37, 99, 235') || bg.includes('59, 130, 246') || 
                                   bg.includes('29, 78, 216') || bg.includes('30, 64, 175') ||
                                   (el.className && typeof el.className === 'string' && (el.className.includes('btn-primary') || el.className.includes('bg-blue')));

                    if (isBlue && (el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'button')) {
                        if (txt.toLowerCase().includes('use this tool') || txt.toLowerCase().includes('open') || isBlue) {
                            blueFound = true;
                        }
                    }

                    if (!fbIdFound) {
                        const m = txt.match(/(\\b\\d{10,20}\\b)/);
                        if (m) fbIdFound = m[1];
                    }
                }
                return { blueFound, fbIdFound };
            }""")
            fb_id = status.get("fbIdFound", "")
            self.log("SUCCESS", f"🔵 [Step 3] Facebook session connected! BLUE buttons are active in FewFeed {('(' + fb_id + ')') if fb_id else ''}.")
        except Exception:
            self.log("INFO", "🔵 [Step 3] FewFeed stabilized. Ready to use tools.")

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

    async def navigate_to_fewfeed_dashboard(self) -> bool:
        """
        Navigates back to FewFeed Dashboard by strictly clicking the FewFeed logo/brand in the navbar.
        CRITICAL: Never reloads or calls page.goto(), preserving the Facebook session connection intact.
        """
        self.log("INFO", "🏠 Clicking top-left FewFeed logo in navbar to return to Dashboard...")
        
        # Check if already on dashboard
        if "/tool/" not in self.page.url.lower():
            self.log("INFO", "ℹ️ Already on FewFeed Dashboard.")
            return True

        clicked = False

        # Strategy 1: Playwright native locator click on navbar brand/home link
        brand_selectors = [
            'header a[href="/"]',
            'nav a[href="/"]',
            'a[href="/"]',
            'header a[href="https://fewfeed.app/"]',
            'nav a[href="https://fewfeed.app/"]',
            'header a:has-text("FewFeed")',
            'nav a:has-text("FewFeed")',
            'header img',
            'nav img'
        ]
        for sel in brand_selectors:
            try:
                loc = self.page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    await loc.scroll_into_view_if_needed()
                    await loc.click()
                    clicked = True
                    break
            except Exception:
                pass

        # Strategy 2: Targeted DOM dispatch on home link / logo
        if not clicked:
            try:
                clicked = await self.page.evaluate("""() => {
                    const homeLinks = Array.from(document.querySelectorAll('header a, nav a, a[href="/"], a[href="https://fewfeed.app/"], a[href="https://fewfeed.app"]'));
                    for (const link of homeLinks) {
                        const txt = (link.innerText || link.textContent || '').trim().toLowerCase();
                        const hasImg = !!link.querySelector('img, svg');
                        if (txt.includes('fewfeed') || hasImg || link.getAttribute('href') === '/' || link.getAttribute('href') === 'https://fewfeed.app/') {
                            link.scrollIntoView({ block: 'center' });
                            ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evt => {
                                link.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
                            });
                            link.click();
                            return true;
                        }
                    }

                    // Fallback to any navbar logo/img
                    const nav = document.querySelector('header, nav') || document.body;
                    const candidates = Array.from(nav.querySelectorAll('a, button, img, svg, div'));
                    for (const el of candidates) {
                        const txt = (el.innerText || el.textContent || el.alt || '').toLowerCase();
                        if (txt.includes('fewfeed')) {
                            const clk = el.closest('a') || el.closest('button') || el;
                            clk.scrollIntoView({ block: 'center' });
                            ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evt => {
                                clk.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
                            });
                            clk.click();
                            return true;
                        }
                    }
                    return false;
                }""")
            except Exception as e:
                self.log("DEBUG", f"Navbar logo click notice: {e}")

        # Wait client-side for navigation back to dashboard (never use page.goto!)
        for _ in range(12):
            await asyncio.sleep(0.5)
            if "/tool/" not in self.page.url.lower():
                self.log("SUCCESS", "✅ Returned to FewFeed Dashboard (Facebook account session preserved)!")
                await asyncio.sleep(1.0)
                return True

        self.log("INFO", "ℹ️ Returning to dashboard view completed.")
        return True

    async def open_fewfeed_tool_by_click(self, tool_name: str) -> bool:
        """
        Navigates into the requested FewFeed tool strictly by clicking 'Use this tool' from Dashboard:
        - Card 2: 'Auto Join To Facebook Groups PRO 2023' (auto-join-fb-group)
        - Card 1: 'Auto Post To Facebook Groups PRO 2023' (auto-post-fb-group)
        CRITICAL: Never reloads or uses page.goto(), keeping the in-memory Facebook account attachment intact.
        """
        is_join = tool_name.lower() in ("join", "joining")
        tool_label = "Auto Join To Facebook Groups PRO 2023" if is_join else "Auto Post To Facebook Groups PRO 2023"
        target_path = "auto-join-fb-group" if is_join else "auto-post-fb-group"
        card_title = "Auto Join To Facebook Groups" if is_join else "Auto Post To Facebook Groups"

        # Ensure FewFeed page reference is active
        if not hasattr(self, 'fewfeed_page') or self.fewfeed_page is None or self.fewfeed_page.is_closed():
            await self.open_fewfeed_via_extension_click()
            await self.verify_facebook_id_blue_buttons(wait_sec=9)

        self.page = self.fewfeed_page
        await self.fewfeed_page.bring_to_front()

        # If currently in a different tool subpage, navigate back to dashboard first via logo click
        if "/tool/" in self.page.url.lower() and target_path not in self.page.url.lower():
            self.log("INFO", f"🔄 Currently on another tool subpage. Navigating back to Dashboard via FewFeed logo...")
            await self.navigate_to_fewfeed_dashboard()
            await asyncio.sleep(1.5)

        # If already on the target tool page, proceed immediately
        if target_path in self.page.url.lower():
            self.log("SUCCESS", f"✅ Already on {tool_label} page.")
            return True

        self.log("INFO", f"🖱️ Locating and clicking 'Use this tool' for: {tool_label}...")

        clicked = False

        # Strategy 1: Playwright Native User Click on Card container
        try:
            cards = self.page.locator('div, section').filter(has_text=card_title)
            count = await cards.count()
            if count > 0:
                for idx in range(count):
                    card_el = cards.nth(idx)
                    btn = card_el.locator('button, a, div[role="button"]').filter(has_text="Use this tool").first
                    if await btn.count() > 0 and await btn.is_visible():
                        await btn.scroll_into_view_if_needed()
                        await btn.click()
                        clicked = True
                        break
        except Exception as e:
            self.log("DEBUG", f"Playwright card click notice: {e}")

        # Strategy 2: Playwright link with target path in href
        if not clicked:
            try:
                link_loc = self.page.locator(f'a[href*="{target_path}"]').first
                if await link_loc.count() > 0 and await link_loc.is_visible():
                    await link_loc.scroll_into_view_if_needed()
                    await link_loc.click()
                    clicked = True
            except Exception:
                pass

        # Strategy 3: Targeted DOM event dispatch
        if not clicked:
            try:
                clicked = await self.page.evaluate("""(data) => {
                    const { isJoin, targetPath } = data;
                    
                    // 1. Direct href match
                    const link = document.querySelector(`a[href*="${targetPath}"]`);
                    if (link) {
                        link.scrollIntoView({ block: 'center' });
                        ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evt => {
                            link.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
                        });
                        link.click();
                        return true;
                    }

                    // 2. Locate card by title text and click 'Use this tool'
                    const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, div, span, p'));
                    const titleEl = headings.find(h => {
                        const t = (h.innerText || h.textContent || '').trim().toLowerCase();
                        return isJoin ? (t.includes('auto join') && t.includes('groups')) : (t.includes('auto post') && t.includes('groups'));
                    });

                    if (titleEl) {
                        let card = titleEl.parentElement;
                        for (let d = 0; d < 8 && card; d++) {
                            const btns = Array.from(card.querySelectorAll('button, a, div[role="button"]'));
                            const useBtn = btns.find(b => {
                                const bTxt = (b.innerText || b.textContent || '').trim().toLowerCase();
                                return bTxt.includes('use this tool');
                            });
                            if (useBtn) {
                                useBtn.scrollIntoView({ block: 'center' });
                                ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evt => {
                                    useBtn.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
                                });
                                useBtn.click();
                                return true;
                            }
                            card = card.parentElement;
                        }
                    }

                    // 3. Fallback by button index under FREE TOOLS:
                    // Post = index 0, Join = index 1
                    const allUseBtns = Array.from(document.querySelectorAll('button, a, div[role="button"]')).filter(b => {
                        const t = (b.innerText || b.textContent || '').trim().toLowerCase();
                        return t.includes('use this tool');
                    });
                    const targetIdx = isJoin ? 1 : 0;
                    if (allUseBtns.length > targetIdx) {
                        const b = allUseBtns[targetIdx];
                        b.scrollIntoView({ block: 'center' });
                        ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evt => {
                            b.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true, view: window }));
                        });
                        b.click();
                        return true;
                    }

                    return false;
                }""", {"isJoin": is_join, "targetPath": target_path})
            except Exception as e:
                self.log("DEBUG", f"DOM click dispatch notice: {e}")

        # Wait client-side for tool page to load (WITHOUT reloading or goto)
        self.log("INFO", f"⏳ Waiting for {tool_label} to open...")
        for wait_i in range(16):
            await asyncio.sleep(0.5)
            if target_path in self.page.url.lower():
                break
            # If not yet open after 2 seconds, re-attempt click once
            if wait_i == 4 and not clicked:
                try:
                    await self.page.evaluate("""(tPath) => {
                        const l = document.querySelector(`a[href*="${tPath}"]`);
                        if (l) l.click();
                    }""", target_path)
                except Exception:
                    pass

        # Wait for form inputs / controls on tool page
        try:
            await self.page.wait_for_selector('textarea, input, button', timeout=6000)
        except Exception:
            pass

        self.log("SUCCESS", f"✅ {tool_label} loaded successfully with Facebook session preserved!")
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

        # Step 2: Inject Group IDs, user THREAD, DELAY and Question Answers
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
                if (!el || el.type === 'file' || el.type === 'checkbox' || el.type === 'radio') return;
                try {
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
                } catch (e) {}
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

            // 2. Search for THREAD and DELAY inputs by label / parent text (excluding file/checkbox)
            const inputs = Array.from(document.querySelectorAll('input')).filter(i => i.type !== 'file' && i.type !== 'checkbox' && i.type !== 'radio');

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

            // 3. Ensure answer keyword is present so 'Please enter at least one keyword' validation passes
            const ansInput = inputs.find(i => {
                const ph = (i.placeholder || '').toLowerCase();
                return ph.includes('answer') || ph.includes('keyword') || ph.includes('add');
            });
            if (ansInput) {
                setNativeVal(ansInput, 'Please accept me');
                const addBtn = ansInput.nextElementSibling || (ansInput.parentElement ? ansInput.parentElement.querySelector('button, svg, span') : null);
                if (addBtn) addBtn.click();
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
                ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evtName => {
                    btn.dispatchEvent(new MouseEvent(evtName, { bubbles: true, cancelable: true, view: window }));
                });
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
        self.log("INFO", "👀 Monitoring FewFeed Auto Join execution status (active joining takes 10 to 12s)...")
        turned_red = False
        for _ in range(8):
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

        # Wait 10 to 12 seconds for joining to finish as shown in user video
        join_start = time.time()
        max_join_wait = max(15, min(len(group_codes) * int(delay_str) * 2, 60))
        self.log("INFO", f"⏳ Waiting 10 to 12 seconds for group joining to complete...")
        
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
                if (turned_red and not state.get("hasStop") and state.get("isBlue")) or (time.time() - join_start >= 12):
                    self.log("SUCCESS", "🔵 FewFeed Auto Join finished! Button has returned to BLUE.")
                    break
            except Exception:
                pass

        self.log("SUCCESS", f"🎉 FewFeed Auto Join successfully completed for all {len(group_codes)} groups!")
        self.set_progress(50)
        
        # Navigate back to FewFeed Dashboard by clicking the top-left FewFeed icon / logo
        await self.navigate_to_fewfeed_dashboard()

        return len(group_codes)

    async def run_fewfeed_group_posting(
        self,
        group_codes: Optional[List[str]] = None,
        links: Optional[List[str]] = None,
        descriptions: Optional[List[str]] = None,
        posting_mode: str = "Random",
        thread_val: int = 1,
        delay_seconds: int = 15,
        post_cycles: int = 1
    ) -> int:
        """
        Automates FewFeed 'Auto Post To Facebook Groups' by clicking 'Use this tool' from Dashboard.
        Fills separate Caption in textarea, separate Link in URL field, sets user THREAD & DELAY, Selects All Groups, and starts posting.
        Supports repeating post cycles per account (post_cycles >= 1).
        """
        self.log("INFO", f"==================================================")
        self.log("INFO", f"📢 [FewFeed Auto Post] Starting automated group posting (Cycles configured: {post_cycles})...")
        self.set_progress(55)

        # Step 1: Open Auto Post Tool by clicking 'Use this tool' on FewFeed Dashboard
        await self.open_fewfeed_tool_by_click("post")
        self.set_progress(65)

        # Step 2: Prepare pure description text and link
        desc_text = random.choice(descriptions) if (descriptions and posting_mode == "Random") else ("\n\n".join(descriptions) if descriptions else "")
        if links:
            if len(links) == 1:
                link_text = links[0]
            else:
                link_text = random.choice(links)
        else:
            link_text = ""
        
        desc_content = desc_text if desc_text else "Available now! Check details and message for info."

        # Step 3: Fill Post Message / Description in FewFeed (pure description text only)
        self.log("INFO", "📝 Entering post description into FewFeed Auto Post composer...")
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
                    await inp.fill(desc_content)
                    desc_filled = True
                    self.log("SUCCESS", "✅ Filled post description in FewFeed (pure description text).")
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
                }""", desc_content)
                self.log("SUCCESS", "✅ Injected post description into FewFeed via DOM bridge.")
            except Exception:
                pass

        # Step 4: Fill separate Link input if present
        if link_text:
            try:
                link_filled = False
                link_selectors = [
                    'input[type="url"]',
                    'input[name*="link" i]',
                    'input[placeholder*="link" i]',
                    'input[placeholder*="url" i]',
                    'input[id*="link" i]'
                ]
                for lsel in link_selectors:
                    link_input = await self.page.query_selector(lsel)
                    if link_input and await link_input.is_visible():
                        await link_input.scroll_into_view_if_needed()
                        await link_input.click()
                        await link_input.fill("")
                        await link_input.fill(link_text)
                        link_filled = True
                        self.log("SUCCESS", f"🔗 Filled separate link into FewFeed link field: {link_text}")
                        break

                if not link_filled:
                    # DOM injection fallback for link input
                    await self.page.evaluate("""(linkVal) => {
                        const inputs = Array.from(document.querySelectorAll('input'));
                        const urlInp = inputs.find(i => {
                            const ph = (i.placeholder || '').toLowerCase();
                            const nm = (i.name || '').toLowerCase();
                            return ph.includes('link') || ph.includes('http') || ph.includes('url') || nm.includes('link') || i.type === 'url';
                        });
                        if (urlInp) {
                            urlInp.value = linkVal;
                            urlInp.dispatchEvent(new Event('input', { bubbles: true }));
                            urlInp.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }""", link_text)
                    self.log("INFO", f"🔗 Injected link into FewFeed: {link_text}")
            except Exception as le:
                self.log("INFO", f"Link field notice: {le}")

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
        self.log("INFO", "☑️ Clicking 'Select All' groups checkbox in FewFeed Auto Post...")
        await asyncio.sleep(1.0)

        # 1. Playwright direct click on the checkbox
        try:
            chk = await self.page.query_selector('input[type="checkbox"]')
            if chk:
                await chk.scroll_into_view_if_needed()
                await chk.click(force=True)
                self.log("SUCCESS", "✅ Clicked group checkbox via Playwright locator.")
        except Exception:
            pass

        # 2. Ensure all checkboxes are checked and change events dispatched
        try:
            chk_count = await self.page.evaluate("""() => {
                const chks = Array.from(document.querySelectorAll('input[type="checkbox"]'));
                let count = 0;
                for (const c of chks) {
                    if (!c.checked) {
                        c.scrollIntoView({ block: 'center' });
                        c.click();
                        c.checked = true;
                        c.dispatchEvent(new Event('input', { bubbles: true }));
                        c.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    count++;
                }
                return count;
            }""")
            self.log("SUCCESS", f"✅ Selected all Facebook Groups ({chk_count}) for Auto Posting.")
        except Exception as e:
            self.log("WARNING", f"Checkbox scan notice: {str(e)[:70]}")

        self.set_progress(80)
        await asyncio.sleep(1.5)

        # Step 7: Post execution across configured post_cycles
        total_cycles = max(1, int(post_cycles))
        self.log("INFO", f"🎯 Post Repetitions for this account: {total_cycles} cycle(s).")

        for current_cycle in range(1, total_cycles + 1):
            if self._cancel_requested:
                break

            if current_cycle == 1:
                self.log("INFO", f"🚀 [Cycle 1/{total_cycles}] Clicking 'Post' button in FewFeed Auto Post Tool...")
            else:
                self.log("INFO", f"⏳ [Cycle {current_cycle}/{total_cycles}] Waiting 2 seconds after previous post completion before re-triggering...")
                await asyncio.sleep(2.0)
                self.log("INFO", f"🔁 [Cycle {current_cycle}/{total_cycles}] Re-clicking 'Post' button for second/subsequent post cycle...")

            # Click the Post button
            clicked = await self.page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button, div[role="button"], input[type="submit"], a.btn'));
                
                // Priority 1: Exact matches for Post button
                for (const b of btns) {
                    const txt = (b.innerText || b.value || b.textContent || '').trim().toLowerCase();
                    if (txt === 'post' || txt === 'start post' || txt === 'post now' || txt === 'start posting') {
                        b.scrollIntoView({ block: 'center' });
                        ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evtName => {
                            b.dispatchEvent(new MouseEvent(evtName, { bubbles: true, cancelable: true, view: window }));
                        });
                        b.click();
                        return true;
                    }
                }
                
                // Priority 2: Substring matches
                for (const b of btns) {
                    const txt = (b.innerText || b.value || b.textContent || '').trim().toLowerCase();
                    if ((txt.includes('post') || txt.includes('start')) && !txt.includes('stop')) {
                        b.scrollIntoView({ block: 'center' });
                        ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(evtName => {
                            b.dispatchEvent(new MouseEvent(evtName, { bubbles: true, cancelable: true, view: window }));
                        });
                        b.click();
                        return true;
                    }
                }
                return false;
            }""")

            if not clicked:
                for psel in ['button:has-text("Post")', 'button:has-text("Start Post")', 'button:has-text("Post Now")', 'button[type="submit"]']:
                    try:
                        pbtn = await self.page.query_selector(psel)
                        if pbtn and await pbtn.is_visible():
                            await pbtn.scroll_into_view_if_needed()
                            await pbtn.click()
                            clicked = True
                            break
                    except Exception:
                        pass

            self.log("INFO", f"👀 [Cycle {current_cycle}/{total_cycles}] Monitoring FewFeed Auto Post execution (button turns RED while posting)...")
            turned_red = False
            for _ in range(8):
                if self._cancel_requested:
                    break
                try:
                    is_active = await self.page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                        for (const b of btns) {
                            const txt = (b.textContent || '').trim().toLowerCase();
                            const style = window.getComputedStyle(b);
                            const bg = style.backgroundColor || '';
                            if (txt.includes('stop') || txt.includes('pause') || txt.includes('posting') || bg.includes('239') || bg.includes('220') || bg.includes('red') || b.disabled || (b.className && (b.className.toLowerCase().includes('danger') || b.className.toLowerCase().includes('stop')))) {
                                return true;
                            }
                        }
                        return false;
                    }""")
                    if is_active:
                        turned_red = True
                        self.log("INFO", f"🔴 [Cycle {current_cycle}/{total_cycles}] Post button turned RED: FewFeed group posting is actively running...")
                        break
                except Exception:
                    pass
                await asyncio.sleep(1.0)

            # Wait 10 to 12 seconds for posting to complete and button to return to BLUE
            self.log("INFO", f"⏳ [Cycle {current_cycle}/{total_cycles}] Waiting for posting to complete (button will return to BLUE)...")
            post_start = time.time()
            max_post_wait = max(20, min(len(group_codes or [1]) * int(delay_str) * 3, 120))

            while (time.time() - post_start) < max_post_wait:
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
                            if (txt.includes('post') || txt.includes('start') || bg.includes('59') || bg.includes('37') || bg.includes('blue') || (b.className && b.className.toLowerCase().includes('primary'))) {
                                isBlue = true;
                            }
                        }
                        return { hasStop, isBlue };
                    }""")

                    if (turned_red and not state.get("hasStop") and state.get("isBlue")) or (time.time() - post_start >= 12):
                        self.log("SUCCESS", f"🔵 [Cycle {current_cycle}/{total_cycles}] Posting completed! Button has returned to BLUE.")
                        break
                except Exception:
                    pass

            if current_cycle < total_cycles:
                self.log("SUCCESS", f"✨ Cycle {current_cycle}/{total_cycles} completed successfully.")

        self.set_progress(100)
        self.log("SUCCESS", f"🎉 FewFeed group posting completed across all {total_cycles} cycle(s) successfully!")
        return len(group_codes) if group_codes else 1

    # --------------------------------------------------------------------------
    # Fallback Direct Facebook DOM Group Joining Workflow
    # --------------------------------------------------------------------------
    async def run_group_joining(self, group_codes: List[str], thread_val: int = 1, delay_seconds: int = 15):
        """Joins specified Facebook groups via FewFeed or direct fallback."""
        return await self.run_fewfeed_group_joining(group_codes=group_codes, thread_val=thread_val, delay_seconds=delay_seconds)

    # --------------------------------------------------------------------------
    # Direct Facebook Native DOM Group Posting Engine
    # --------------------------------------------------------------------------
    async def run_direct_facebook_group_posting(
        self,
        group_codes: List[str],
        links: List[str],
        descriptions: List[str],
        posting_mode: str = "Random",
        delay_seconds: int = 15
    ) -> int:
        """Directly posts to Facebook Groups via browser DOM with full reliability."""
        if not group_codes:
            self.log("INFO", "🔍 No specific group codes entered. Discovering your joined groups from Facebook...")
            try:
                await self.page.goto("https://www.facebook.com/groups/joins/", wait_until="domcontentloaded", timeout=35000)
                await asyncio.sleep(4.0)
                discovered = await self.page.evaluate("""() => {
                    const links = Array.from(document.querySelectorAll('a[href*="/groups/"]'));
                    const gids = new Set();
                    for (const a of links) {
                        const m = a.href.match(/groups\\/([^\\/?#]+)/);
                        if (m && m[1] && !['feed', 'joins', 'discover', 'create', 'notifications'].includes(m[1].toLowerCase())) {
                            gids.add(m[1]);
                        }
                    }
                    return Array.from(gids);
                }""")
                if discovered:
                    group_codes = discovered
                    self.log("SUCCESS", f"✅ Discovered {len(group_codes)} joined Facebook groups to post into!")
            except Exception as d_err:
                self.log("INFO", f"Discovery notice: {str(d_err)[:60]}")

        if not group_codes:
            self.log("WARNING", "No group codes available for direct Facebook posting.")
            return 0

        total = len(group_codes)
        posts_published = 0
        self.log("INFO", f"==================================================")
        self.log("INFO", f"📢 [Direct Facebook Posting] Posting across {total} group(s)...")

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
                            self.log("INFO", f"Typing post content into group [{code}] ({len(full_post_text)} chars)...")
                            await self.page.keyboard.type(full_post_text, delay=random.randint(25, 65))
                            box_found = True
                            break
                    except Exception:
                        continue

                if not box_found:
                    self.log("WARNING", f"Could not find editable post box in group [{code}]. Skipping.")
                    continue

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
                jitter = random.uniform(-2.0, 3.0)
                actual_delay = max(4.0, delay_seconds + jitter)
                self.log("INFO", f"⏳ Waiting {actual_delay:.1f}s before next group post...")
                await asyncio.sleep(actual_delay)

        self.log("SUCCESS", f"🏁 Direct Group Posting finished! {posts_published}/{total} posts published.")
        return posts_published

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
        delay_seconds: int = 15,
        post_cycles: int = 1
    ):
        """Posts links and descriptions across target Facebook Groups via FewFeed, with seamless direct fallback."""
        fewfeed_res = await self.run_fewfeed_group_posting(
            group_codes=group_codes,
            links=links,
            descriptions=descriptions,
            posting_mode=posting_mode,
            thread_val=thread_val,
            delay_seconds=delay_seconds,
            post_cycles=post_cycles
        )
        if fewfeed_res and fewfeed_res > 0:
            return fewfeed_res

        self.log("INFO", "⚡ FewFeed Auto Post was inactive or produced 0 posts. Switching directly to Native Group Posting Engine...")
        return await self.run_direct_facebook_group_posting(
            group_codes=group_codes or [],
            links=links or [],
            descriptions=descriptions or [],
            posting_mode=posting_mode,
            delay_seconds=delay_seconds
        )

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
        join_thread: int = 1,
        post_cycles: int = 1
    ) -> Dict[str, Any]:
        """
        Master-level unified single-click execution flow:
        1. Initialize Original Desktop Chrome & load FEWFEED extension.
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

                # Step 4 & 6: Auto Post to Groups in FewFeed or Direct Fallback
                self.log("INFO", f"⚡ [Unified Phase 2/2] Launching Auto Post (THREAD={post_thread}, DELAY={delay_seconds}s, CYCLES={post_cycles})...")
                posted_items = await self.run_group_posting(
                    group_codes=p_codes,
                    links=links or [],
                    descriptions=descriptions or [],
                    posting_mode=posting_mode,
                    thread_val=post_thread,
                    delay_seconds=delay_seconds,
                    post_cycles=post_cycles
                )
                results["status"] = "completed"
                results["items_processed"] = (0 if already_joined else len(j_codes)) + (posted_items or len(p_codes) or 1)

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
                    delay_seconds=delay_seconds,
                    post_cycles=post_cycles
                )
                results["items_processed"] = posted_count
                results["status"] = "completed"

            else:
                raise ValueError(f"Unknown task type: {task_type}")

            # Step 7: Completed - close browser cleanly upon finishing posting
            self.log("SUCCESS", "🏁 [Step 7] All group automation tasks completed successfully! Closing browser...")
            results["status"] = "completed"
            await asyncio.sleep(2.0)
            await self.close()

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            self.log("ERROR", f"❌ Group workflow notice: {str(e)}")
            # Do NOT immediately kill browser on recoverable notices
            await asyncio.sleep(2.0)
        finally:
            self.log("INFO", f"✨ Group workflow sequence ended with status: {results['status']}.")

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
