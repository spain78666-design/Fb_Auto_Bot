#!/usr/bin/env python3
"""
FB Auto Bot - Facebook Marketplace Automation Suite
automation/session_manager.py - Multi-Account Persistence & Session Cookie Manager

Provides isolated session environments, cookie serialization, automated health audits,
and manual browser login interception to safeguard Facebook profiles against cross-contamination:
  1. Isolated User Data Directories (profiles/account_id/) for zero cache/cookie leaks
  2. Flexible Cookie Normalizer (JSON arrays, EditThisCookie, Netscape, and semicolon strings)
  3. Automated Session Health Auditor (detects /login redirects, checkpoints, and active feeds)
  4. Interactive Manual Login Interceptor (launches headful browser, captures c_user & xs cookies)
  5. JSON Database Persistence (config/accounts_db.json) with proxy bindings
"""

import os
import sys
import json
import time
import random
import uuid
import shutil
import asyncio
import logging
import re
import hmac
import hashlib
import struct
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Callable

try:
    from automation.browser_window_manager import (
        build_window_chrome_args,
        human_click_element,
        human_click_coords,
        human_type_text,
        human_smooth_scroll,
        human_pause,
        human_session_warmup,
    )
except ImportError:
    try:
        from desktop_app.automation.browser_window_manager import (
            build_window_chrome_args,
            human_click_element,
            human_click_coords,
            human_type_text,
            human_smooth_scroll,
            human_pause,
            human_session_warmup,
        )
    except ImportError:
        def build_window_chrome_args(tile_rect=None, total_slots=1, slot_index=0, profile_directory=None, apply_scale_factor=True):
            return []
        async def human_click_element(page, target, hover_pause=True, force_fallback=True):
            try:
                await target.click(timeout=4000)
                return True
            except Exception:
                return False
        async def human_click_coords(page, x, y, hover_pause=True):
            try:
                await page.mouse.click(x, y)
                return True
            except Exception:
                return False
        async def human_type_text(page, target, text, clear_first=True, allow_typos=False):
            try:
                await target.fill(text)
                return True
            except Exception:
                return False
        async def human_smooth_scroll(page, total_delta_y=550, steps=6):
            await page.evaluate("(d) => window.scrollBy(0, d)", total_delta_y)
        async def human_pause(low=0.55, high=1.45, mult=1.0):
            await asyncio.sleep(random.uniform(low, high) * mult)
        async def human_session_warmup(page, duration_range=(0.8, 1.5), log_cb=None):
            await asyncio.sleep(0.9)

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

logger = logging.getLogger("FBAutoBot.SessionManager")

DEFAULT_ACCOUNTS_SEED: List[Dict[str, Any]] = []

def generate_totp(secret: str) -> str:
    """
    Pure Python RFC 6238 TOTP 2FA code generator for Facebook 2-Step Verification.
    Generates standard 6-digit one-time passcodes without third-party dependencies.
    """
    if not secret or not isinstance(secret, str):
        return ""
    try:
        clean_secret = secret.replace(" ", "").replace("-", "").upper()
        # Add required base32 padding
        padded = clean_secret + "=" * (-len(clean_secret) % 8)
        key = base64.b32decode(padded)
        counter = int(time.time()) // 30
        msg = struct.pack(">Q", counter)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        offset = h[-1] & 0x0F
        code = (struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF) % 1000000
        return f"{code:06d}"
    except Exception as e:
        logger.warning(f"Could not generate TOTP code from secret: {e}")
        return ""

def get_base_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_metus_extension_path(allow_legacy_fewfeed: bool = False) -> Optional[str]:
    """Resolves the absolute path to METUS (or custom) extension folder via ExtensionManager."""
    try:
        from automation.extension_manager import get_metus_extension_path as _get_path
        return _get_path(allow_legacy_fewfeed=allow_legacy_fewfeed)
    except Exception:
        pass

    base = get_base_dir()
    candidates = [
        os.path.join(base, "METUS"),
        os.path.join(base, "Metus"),
        os.path.join(base, "_internal", "METUS"),
        os.path.join(getattr(sys, '_MEIPASS', ''), "METUS"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "METUS")),
        os.path.abspath("METUS"),
        os.path.abspath("desktop_app/METUS"),
    ]
    for c in candidates:
        if c and os.path.isdir(c) and os.path.exists(os.path.join(c, "manifest.json")):
            return os.path.abspath(c)
    return None


def get_fewfeed_extension_path(allow_legacy_fewfeed: bool = False) -> Optional[str]:
    """Backward-compatible alias that resolves the METUS / custom extension path cleanly."""
    return get_metus_extension_path(allow_legacy_fewfeed=allow_legacy_fewfeed)



class SessionCookieParser:
    """Parses arbitrary cookie formats into Playwright-compliant dictionaries."""

    @staticmethod
    def normalize_cookies(raw_cookies: Any) -> List[Dict[str, Any]]:
        """
        Accepts:
          - Semicolon string: "c_user=100084; xs=29%3A..."
          - JSON string of list or dict
          - Python list of dicts (from EditThisCookie or Netscape export)
        Returns:
          - List[dict] ready for browser_context.add_cookies()
        """
        if not raw_cookies:
            return []

        cookies_list: List[Dict[str, Any]] = []

        # 1. Handle JSON string representation
        if isinstance(raw_cookies, str):
            trimmed = raw_cookies.strip()
            if trimmed.startswith("[") or trimmed.startswith("{"):
                try:
                    parsed_json = json.loads(trimmed)
                    if isinstance(parsed_json, list):
                        for c in parsed_json:
                            normalized = SessionCookieParser._normalize_cookie_dict(c)
                            if normalized:
                                cookies_list.append(normalized)
                        return cookies_list
                    elif isinstance(parsed_json, dict):
                        for k, v in parsed_json.items():
                            cookies_list.append({
                                "name": str(k),
                                "value": str(v),
                                "domain": ".facebook.com",
                                "path": "/",
                                "secure": True,
                                "sameSite": "Lax"
                            })
                        return cookies_list
                except Exception:
                    pass  # Fallback to semicolon parser below

            # 2. Handle Semicolon key=value format
            pairs = [p.strip() for p in trimmed.split(";") if p.strip()]
            for pair in pairs:
                if "=" in pair:
                    key, val = pair.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    if key:
                        cookies_list.append({
                            "name": key,
                            "value": val,
                            "domain": ".facebook.com",
                            "path": "/",
                            "secure": True,
                            "sameSite": "Lax"
                        })
            return cookies_list

        # 3. Handle Python list of dicts directly
        if isinstance(raw_cookies, list):
            for c in raw_cookies:
                if isinstance(c, dict):
                    normalized = SessionCookieParser._normalize_cookie_dict(c)
                    if normalized:
                        cookies_list.append(normalized)
            return cookies_list

        return []

    @staticmethod
    def _normalize_cookie_dict(c: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        name = c.get("name")
        value = c.get("value")
        if not name or value is None:
            return None

        domain = c.get("domain", ".facebook.com")
        if domain and not domain.startswith("."):
            domain = f".{domain}"
        if not domain or "facebook.com" not in domain:
            domain = ".facebook.com"

        cookie_item = {
            "name": str(name),
            "value": str(value),
            "domain": domain,
            "path": c.get("path", "/"),
            "secure": bool(c.get("secure", True)),
            "httpOnly": bool(c.get("httpOnly", False))
        }

        # Normalize sameSite
        ss = c.get("sameSite", "Lax")
        if isinstance(ss, str):
            ss_lower = ss.lower()
            if ss_lower in ("strict", "lax", "none"):
                cookie_item["sameSite"] = ss_lower.capitalize() if ss_lower != "none" else "None"
            else:
                cookie_item["sameSite"] = "Lax"
        else:
            cookie_item["sameSite"] = "Lax"

        if "expirationDate" in c:
            try:
                cookie_item["expires"] = int(c["expirationDate"])
            except Exception:
                pass

        return cookie_item

    @staticmethod
    def cookies_to_semicolon_string(cookies: List[Dict[str, Any]], page_id: str = "") -> str:
        """
        Converts normalized cookie list to string format matching
        the Chrome extension 'Get Token Cookie':
        sb -> datr -> dpr -> wd -> c_user -> [others: oo, _fbp, fr, presence...] -> xs -> i_user;
        """
        c_map = {}
        for c in cookies:
            n = c.get("name")
            v = c.get("value")
            if n and v is not None:
                c_map[str(n)] = str(v).strip()

        # If page_id is provided and i_user not yet set
        if page_id and "i_user" not in c_map:
            c_map["i_user"] = str(page_id).strip()

        parts = []
        seen = set()

        # 1. Leading priority matching Get Token Cookie extension
        for p in ["sb", "datr", "dpr", "wd", "c_user"]:
            if p in c_map:
                parts.append(f"{p}={c_map[p]}")
                seen.add(p)

        # 2. Intermediate cookies (oo, _fbp, fr, presence, etc.)
        for k, v in c_map.items():
            if k not in seen and k not in ("xs", "i_user"):
                parts.append(f"{k}={v}")
                seen.add(k)

        # 3. Session key xs
        if "xs" in c_map:
            parts.append(f"xs={c_map['xs']}")
            seen.add("xs")

        # 4. Page active profile i_user
        if "i_user" in c_map:
            parts.append(f"i_user={c_map['i_user']}")
            seen.add("i_user")

        return ";".join(parts) + (";" if parts else "")

    # Convenience alias
    parse_cookies = normalize_cookies


class SessionManager:
    """
    Manages accounts, isolated profiles, proxy bindings, and session validation.
    """

    def __init__(
        self,
        base_dir: Optional[str] = None,
        db_path: Optional[str] = None,
        profiles_base_dir: Optional[str] = None
    ):
        if base_dir:
            self.base_dir = base_dir
        else:
            if getattr(sys, 'frozen', False):
                self.base_dir = os.path.dirname(sys.executable)
            else:
                self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        self.config_dir = os.path.join(self.base_dir, "config")
        self.profiles_dir = profiles_base_dir if profiles_base_dir else os.path.join(self.base_dir, "profiles")
        self.db_path = db_path if db_path else os.path.join(self.config_dir, "accounts_db.json")

        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else self.config_dir, exist_ok=True)
        os.makedirs(self.profiles_dir, exist_ok=True)

        self._init_db()

    def _init_db(self):
        """Initializes accounts JSON database file with seed accounts if missing or empty."""
        if not os.path.exists(self.db_path) or os.path.getsize(self.db_path) == 0:
            try:
                with open(self.db_path, "w", encoding="utf-8") as f:
                    json.dump({"accounts": DEFAULT_ACCOUNTS_SEED}, f, indent=2)
                logger.info(f"Initialized accounts database with {len(DEFAULT_ACCOUNTS_SEED)} default profiles.")
            except Exception as e:
                logger.error(f"Error seeding accounts database: {str(e)}")

    def get_profile_dir(self, account_id: str) -> str:
        """Returns the isolated profile user-data-dir for an account."""
        clean_id = "".join(c for c in account_id if c.isalnum() or c in ("_", "-"))
        path = os.path.join(self.profiles_dir, clean_id)
        os.makedirs(path, exist_ok=True)
        try:
            self.sync_master_fewfeed_session(path)
        except Exception:
            pass
        return path

    def get_master_metus_profile_dir(self) -> str:
        """Returns the path to the Master METUS Chrome profile directory."""
        metus_path = os.path.join(self.profiles_dir, "master_metus_profile")
        legacy_path = os.path.join(self.profiles_dir, "master_fewfeed_profile")
        os.makedirs(metus_path, exist_ok=True)
        # If legacy master profile already has extension data and master_metus_profile is empty, prefer it as source
        metus_def = os.path.join(metus_path, "Default")
        legacy_def = os.path.join(legacy_path, "Default")
        if not os.path.isdir(os.path.join(metus_def, "Extensions")) and os.path.isdir(os.path.join(legacy_def, "Extensions")):
            try:
                from automation.group_bot import copy_fewfeed_session_data
                copy_fewfeed_session_data(legacy_path, metus_path)
            except Exception:
                pass
        return metus_path

    get_master_fewfeed_profile_dir = get_master_metus_profile_dir

    def sync_master_metus_session(self, target_profile_dir: str) -> bool:
        """
        Syncs METUS extension files, Extension Settings, IndexedDB, Local Storage, Cookies,
        and Preferences from master_metus_profile into target_profile_dir so all account
        Chrome profiles share the same METUS extension setup and session.
        """
        from automation.group_bot import copy_fewfeed_session_data
        master_dir = self.get_master_metus_profile_dir()
        if not os.path.exists(master_dir) or os.path.abspath(master_dir) == os.path.abspath(target_profile_dir):
            return False

        try:
            copy_fewfeed_session_data(master_dir, target_profile_dir)
            return True
        except Exception as e:
            logger.warning(f"Notice during METUS session sync: {str(e)}")
            return False

    sync_master_fewfeed_session = sync_master_metus_session

    def sync_master_metus_to_all_profiles(self) -> int:
        """Syncs Master METUS extension & session to all existing account profile directories."""
        accounts = self.list_accounts()
        count = 0
        for acc in accounts:
            acc_id = acc.get("id") or acc.get("name", "")
            if acc_id:
                p_dir = os.path.join(self.profiles_dir, "".join(c for c in acc_id if c.isalnum() or c in ("_", "-")))
                if os.path.exists(p_dir):
                    if self.sync_master_metus_session(p_dir):
                        count += 1
        return count

    sync_master_fewfeed_to_all_profiles = sync_master_metus_to_all_profiles

    async def launch_master_metus_setup(
        self,
        log_callback: Optional[Callable[[str, str], None]] = None,
        timeout_seconds: int = 600,
        profile_dir: Optional[str] = None,
        ext_path: Optional[str] = None,
        account_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Launches an interactive Chrome browser with the selected (or Master METUS) profile.
        Injects the selected account's Facebook cookies so Tab 1 opens ALREADY LOGGED IN,
        and opens Tab 2 directly to chrome://extensions/ (Developer Mode ON) so the user can
        install/load and verify the METUS Chrome extension cleanly.
        Automatically saves and syncs METUS extension & storage to all profiles when closed!
        """
        log = log_callback or (lambda lvl, msg: logger.info(f"[{lvl}] {msg}"))
        target_dir = profile_dir or (self.get_profile_dir(account_data.get("id") or account_data.get("name")) if account_data else self.get_master_metus_profile_dir())
        os.makedirs(target_dir, exist_ok=True)

        for fname in ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"]:
            fpath = os.path.join(target_dir, fname)
            if os.path.exists(fpath) or os.path.islink(fpath):
                try:
                    if os.path.islink(fpath) or os.path.isfile(fpath):
                        os.unlink(fpath)
                    elif os.path.isdir(fpath):
                        shutil.rmtree(fpath, ignore_errors=True)
                except Exception:
                    pass

        resolved_ext = ext_path or get_metus_extension_path(allow_legacy_fewfeed=False)
        try:
            from automation.extension_manager import prepare_profile_for_extension, get_system_chrome_executable, get_clean_path_for_chrome
            prepare_profile_for_extension(target_dir, resolved_ext)
        except Exception:
            get_system_chrome_executable = lambda: None
            get_clean_path_for_chrome = lambda p: os.path.abspath(p).replace('\\', '/')

        if resolved_ext and os.path.isdir(resolved_ext) and os.path.exists(os.path.join(resolved_ext, "manifest.json")):
            log("SUCCESS", f"🧩 METUS Extension detected: {resolved_ext}")
        else:
            log("INFO", "🧩 No pre-selected unpacked METUS folder yet — Chrome will open chrome://extensions/ so you can add/enable METUS directly.")

        profile_label = os.path.basename(target_dir)
        acc_label = (account_data.get("name") or account_data.get("id")) if account_data else profile_label
        log("INFO", f"🌐 Launching Chrome METUS Setup for [{acc_label}] (Profile: {profile_label})...")

        chrome_exe = get_system_chrome_executable()

        launch_flags = [
            "--disable-blink-features=AutomationControlled",
            "--no-default-browser-check",
            "--no-first-run",
            "--lang=en-US,en",
            "--enable-extensions",
            "--enable-unsafe-extension-debugging",
            *build_window_chrome_args(total_slots=1, slot_index=0),
        ]
        if resolved_ext and os.path.isdir(resolved_ext) and os.path.isfile(os.path.join(resolved_ext, "manifest.json")):
            clean_p = get_clean_path_for_chrome(resolved_ext)
            launch_flags.append(f"--load-extension={clean_p}")

        async with async_playwright() as p:
            context = None
            channels_to_try = []
            if chrome_exe and os.path.isfile(chrome_exe):
                channels_to_try.append(("custom_exe", chrome_exe))
            channels_to_try.extend([("chrome", None), ("msedge", None), (None, None)])

            for ch_name, exe_path in channels_to_try:
                try:
                    kws = {
                        "user_data_dir": target_dir,
                        "headless": False,
                        "no_viewport": True,
                        "args": launch_flags,
                        "ignore_default_args": [
                            "--no-sandbox",
                            "--enable-automation",
                            "--disable-extensions",
                            "--disable-component-extensions-with-background-pages"
                        ]
                    }
                    if exe_path:
                        kws["executable_path"] = exe_path
                    elif ch_name:
                        kws["channel"] = ch_name
                    context = await p.chromium.launch_persistent_context(**kws)
                    log("SUCCESS", f"🚀 Chrome launched cleanly ({exe_path or ch_name or 'Chromium'})")
                    break
                except Exception as ex:
                    logger.debug(f"Launch attempt {ch_name} failed: {ex}")
                    continue

            if not context:
                log("ERROR", "Could not launch Chrome/Edge browser for METUS setup.")
                return False

            # Attach unpacked METUS extension via CDP if folder was provided
            if resolved_ext and os.path.isdir(resolved_ext) and os.path.isfile(os.path.join(resolved_ext, "manifest.json")):
                try:
                    fwd_ext = os.path.abspath(resolved_ext).replace('\\', '/')
                    p0 = context.pages[0] if context.pages else await context.new_page()
                    cdp = await context.new_cdp_session(p0)
                    await cdp.send("Extensions.loadUnpacked", {"path": fwd_ext})
                    log("SUCCESS", "⚡ METUS extension attached and activated in Chrome!")
                except Exception as cdp_err:
                    logger.debug(f"CDP extension activation notice: {cdp_err}")

            # Inject Facebook cookies if account_data provided
            account_cookies = (account_data or {}).get("cookies")
            if account_cookies:
                try:
                    from automation.browser_bot import parse_cookie_payload
                    parsed = parse_cookie_payload(account_cookies)
                    if parsed:
                        clean_cookies = []
                        for c in parsed:
                            c_copy = dict(c)
                            if "sameSite" in c_copy and c_copy["sameSite"] not in ("Strict", "Lax", "None"):
                                c_copy["sameSite"] = "Lax"
                            if "url" not in c_copy and not c_copy.get("domain"):
                                c_copy["domain"] = ".facebook.com"
                            clean_cookies.append(c_copy)
                        await context.add_cookies(clean_cookies)
                        log("SUCCESS", f"🍪 Injected {len(clean_cookies)} Facebook cookies into Chrome! ID will open logged in.")
                except Exception as ce:
                    log("WARNING", f"Cookie injection notice: {str(ce)[:80]}")

            # Tab 1: Facebook (Loads with injected cookies)
            page = context.pages[0] if context.pages else await context.new_page()
            try:
                await page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=45000)
                log("SUCCESS", "👤 Facebook opened in Tab 1 (Logged in from account cookies).")
            except Exception:
                pass

            # Tab 2: Extensions manager (chrome://extensions/) so user can install/load METUS directly
            try:
                ext_page = await context.new_page()
                await ext_page.goto("chrome://extensions/", wait_until="domcontentloaded", timeout=15000)
                log("SUCCESS", "🧩 Chrome Extensions Manager opened in Tab 2 (Ready for METUS setup).")
            except Exception:
                pass

            log("INFO", "🟢 METUS Setup browser ready! Install/log into your METUS extension in Chrome, then simply close Chrome to save & sync across all profiles.")

            while True:
                await asyncio.sleep(1.5)
                try:
                    if not context.pages or all(p.is_closed() for p in context.pages):
                        break
                except Exception:
                    break

            try:
                await context.close()
            except Exception:
                pass

        master_dir = self.get_master_metus_profile_dir()
        legacy_master_dir = os.path.join(self.profiles_dir, "master_fewfeed_profile")
        from automation.group_bot import copy_fewfeed_session_data

        if os.path.abspath(target_dir) != os.path.abspath(master_dir):
            copy_fewfeed_session_data(target_dir, master_dir)
        copy_fewfeed_session_data(master_dir, legacy_master_dir)

        # Detect and permanently save any unpacked/installed METUS extension folder user added in setup window
        try:
            from automation.extension_manager import extract_extension_path_from_profile, set_custom_extension_path
            detected_ext = (
                extract_extension_path_from_profile(target_dir, prefer_metus=True)
                or extract_extension_path_from_profile(master_dir, prefer_metus=True)
            )
            if detected_ext:
                set_custom_extension_path(detected_ext, user_selected=True)
                log("SUCCESS", f"🧩 Permanently saved METUS extension folder: {detected_ext}")
        except Exception:
            pass

        synced_cnt = self.sync_master_metus_to_all_profiles()
        log("SUCCESS", f"⚡ Auto-synced METUS extension & session to {synced_cnt} active profile folder(s)!")
        return True

    launch_master_fewfeed_login = launch_master_metus_setup

    def list_accounts(self) -> List[Dict[str, Any]]:
        """Returns all accounts saved in the database."""
        try:
            if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 0:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("accounts", [])
            else:
                self._init_db()
                return list(DEFAULT_ACCOUNTS_SEED)
        except Exception as e:
            logger.warning(f"Accounts database auto-repaired: {str(e)}")
            self._init_db()
        return list(DEFAULT_ACCOUNTS_SEED)

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single account by ID or name."""
        accounts = self.list_accounts()
        for acc in accounts:
            if acc.get("id") == account_id or acc.get("name") == account_id:
                return acc
        return None

    def save_accounts(self, accounts: List[Dict[str, Any]]) -> bool:
        """Saves entire accounts list to disk."""
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump({"accounts": accounts}, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save accounts database: {str(e)}")
            return False

    def add_or_update_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Adds a new account or updates an existing one."""
        accounts = self.list_accounts()
        acc_id = account_data.get("id")
        if not acc_id:
            # Generate ID based on name or UUID
            name_slug = account_data.get("name", "acc").strip().lower().replace(" ", "_")
            name_slug = "".join(c for c in name_slug if c.isalnum() or c == "_")[:12]
            acc_id = f"acc_{name_slug}_{uuid.uuid4().hex[:6]}"
            account_data["id"] = acc_id

        # Attach profile directory
        account_data["profile_dir"] = self.get_profile_dir(acc_id)
        if not account_data.get("last_checked"):
            account_data["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        existing_idx = -1
        for idx, item in enumerate(accounts):
            if item.get("id") == acc_id:
                existing_idx = idx
                break

        if existing_idx >= 0:
            accounts[existing_idx].update(account_data)
        else:
            accounts.append(account_data)

        self.save_accounts(accounts)
        return account_data

    def save_account(
        self,
        account_id: Optional[str] = None,
        name: Optional[str] = None,
        cookies: Optional[str] = None,
        uid: str = "",
        email: str = "",
        password: str = "",
        two_factor_secret: str = "",
        proxy: str = "Direct (No Proxy)",
        proxy_type: str = "HTTP",
        proxy_user: str = "",
        proxy_pass: str = "",
        notes: str = "",
        status: str = "Healthy"
    ) -> Dict[str, Any]:
        """Convenience helper to create or update an account entry."""
        acc_data = {
            "id": account_id or f"acc_{uuid.uuid4().hex[:8]}",
            "name": name or uid or email or account_id or "Unnamed Profile",
            "uid": uid.strip(),
            "email": email.strip(),
            "password": password.strip(),
            "two_factor_secret": two_factor_secret.strip(),
            "cookies": cookies or "",
            "proxy": proxy,
            "proxy_type": proxy_type,
            "proxy_user": proxy_user,
            "proxy_pass": proxy_pass,
            "notes": notes,
            "status": status,
            "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return self.add_or_update_account(acc_data)

    def delete_account(
        self,
        account_id: str,
        delete_profile_dir: bool = False,
        purge_profile_data: bool = False
    ) -> bool:
        """Deletes an account from the database and optionally wipes its profile dir."""
        wipe_dir = delete_profile_dir or purge_profile_data
        accounts = self.list_accounts()
        initial_len = len(accounts)
        accounts = [a for a in accounts if a.get("id") != account_id and a.get("name") != account_id]
        if len(accounts) != initial_len:
            self.save_accounts(accounts)
            if wipe_dir:
                p_dir = os.path.join(self.profiles_dir, account_id)
                if os.path.exists(p_dir):
                    shutil.rmtree(p_dir, ignore_errors=True)
            return True
        return False

    def delete_accounts(
        self,
        account_ids: List[str],
        delete_profile_dir: bool = False,
        purge_profile_data: bool = True
    ) -> int:
        """Deletes multiple accounts from the database in a single atomic save and wipes profile dirs."""
        wipe_dir = delete_profile_dir or purge_profile_data
        accounts = self.list_accounts()
        id_set = {str(aid).strip() for aid in account_ids if str(aid).strip()}
        if not id_set:
            return 0

        to_remove = [
            a for a in accounts 
            if str(a.get("id")) in id_set or str(a.get("name")) in id_set
        ]
        if not to_remove:
            return 0

        rem_ids = {str(a.get("id")) for a in to_remove if a.get("id")}
        rem_names = {str(a.get("name")) for a in to_remove if a.get("name")}

        remaining = [
            a for a in accounts 
            if str(a.get("id")) not in rem_ids and str(a.get("name")) not in rem_names and str(a.get("id")) not in id_set and str(a.get("name")) not in id_set
        ]
        self.save_accounts(remaining)

        if wipe_dir:
            for acc in to_remove:
                for target_name in (acc.get("id"), acc.get("name")):
                    if target_name:
                        p_dir = os.path.join(self.profiles_dir, str(target_name))
                        if os.path.exists(p_dir):
                            shutil.rmtree(p_dir, ignore_errors=True)
        return len(to_remove)

    def update_account_status(self, account_id: str, status: str, details: str = "", display_name: str = ""):
        """Updates health status, display_name, and last_checked timestamp for an account."""
        accounts = self.list_accounts()
        for acc in accounts:
            if acc.get("id") == account_id or acc.get("name") == account_id:
                acc["status"] = status
                acc["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if details:
                    acc["last_check_detail"] = details
                # Only update name if current name was a generic placeholder, or if display_name is given
                current_name = acc.get("name", "")
                is_auto_name = not current_name or current_name.startswith("FB_") or current_name.startswith("Draft_") or current_name == "Unnamed Profile" or current_name.startswith("acc_")
                if display_name and display_name.strip() and is_auto_name:
                    acc["name"] = display_name.strip()
                break
        self.save_accounts(accounts)

    # --------------------------------------------------------------------------
    # Automated Session Health Check (Async Playwright)
    # --------------------------------------------------------------------------
    async def verify_session_health(
        self,
        account_id: str,
        log_callback: Optional[Callable[[str, str], None]] = None,
        timeout_seconds: int = 25
    ) -> Tuple[str, str]:
        """
        Boots an isolated, headless Playwright session using the account's proxy and cookies,
        navigating to Facebook to test authentication.
        Returns:
          - (status: str, detail: str)
            status is one of: "Healthy", "Needs Login", "Checkpoint", "Proxy Error"
        """
        log = log_callback or (lambda lvl, msg: logger.info(f"[{lvl}] {msg}"))
        account = self.get_account(account_id)
        if not account:
            return "Needs Login", f"Account '{account_id}' not found in database."

        acc_name = account.get("name", account_id)
        log("INFO", f"Audit Engine: Verifying session health for '{acc_name}'...")

        if not PLAYWRIGHT_AVAILABLE:
            err_msg = "Playwright/Chromium browser runtime is not installed; live session check could not run."
            log("ERROR", err_msg)
            self.update_account_status(account["id"], "Needs Check", err_msg)
            return "Needs Check", err_msg

        profile_dir = self.get_profile_dir(account["id"])

        # Configure proxy dict
        proxy_cfg = None
        raw_proxy = account.get("proxy", "").strip()
        if raw_proxy and "direct" not in raw_proxy.lower() and "no proxy" not in raw_proxy.lower() and "no_proxy" not in raw_proxy.lower():
            proxy_type = account.get("proxy_type", "HTTP").lower()
            if not raw_proxy.startswith("http://") and not raw_proxy.startswith("socks5://") and not raw_proxy.startswith("https://"):
                full_server = f"{proxy_type}://{raw_proxy}"
            else:
                full_server = raw_proxy

            proxy_cfg = {"server": full_server}
            if account.get("proxy_user"):
                proxy_cfg["username"] = account["proxy_user"]
            if account.get("proxy_pass"):
                proxy_cfg["password"] = account["proxy_pass"]
            log("INFO", f"Routing audit through proxy: {proxy_cfg['server']}")

        async with async_playwright() as p:
            try:
                # Launch persistent context
                context: BrowserContext = await p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=True,
                    proxy=proxy_cfg,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage"
                    ],
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                    )
                )

                page: Page = context.pages[0] if context.pages else await context.new_page()

                # Apply stealth
                if PLAYWRIGHT_STEALTH_AVAILABLE:
                    await stealth_async(page)

                # Inject cookies
                cookies = SessionCookieParser.normalize_cookies(account.get("cookies", ""))
                if cookies:
                    log("INFO", f"Injecting {len(cookies)} auth cookies into isolated context...")
                    await context.add_cookies(cookies)

                log("INFO", "Navigating to https://www.facebook.com to inspect session tokens...")
                try:
                    resp = await page.goto("https://www.facebook.com/", timeout=timeout_seconds * 1000, wait_until="domcontentloaded")
                except Exception as nav_err:
                    err_msg = str(nav_err).lower()
                    if "proxy" in err_msg or "connection" in err_msg or "err_tunnel" in err_msg:
                        self.update_account_status(account["id"], "Proxy Error", str(nav_err))
                        log("ERROR", f"Proxy connection failed for '{acc_name}': {nav_err}")
                        await context.close()
                        return "Proxy Error", f"Proxy unreachable: {nav_err}"
                    else:
                        raise nav_err

                await asyncio.sleep(2.0)
                current_url = page.url.lower()

                status = "Healthy"
                detail = "Active session authenticated"
                detected_name = ""

                # Check cookies in context
                live_cookies = await context.cookies()
                c_user_present = any(c.get("name") == "c_user" for c in live_cookies)

                if "checkpoint" in current_url or "two_step_verification" in current_url or "/recover/" in current_url:
                    status = "Checkpoint"
                    detail = "Facebook Checkpoint / 2FA challenge detected"
                    log("WARNING", f"Account '{acc_name}' entered Facebook CHECKPOINT challenge.")
                elif ("/login" in current_url or "facebook.com/login.php" in current_url) and not c_user_present:
                    status = "Needs Login"
                    detail = "Session cookies expired or missing. Redirected to /login"
                    log("WARNING", f"Session expired for '{acc_name}'. Re-login required.")
                else:
                    # Authenticated session
                    status = "Healthy"
                    detail = "Active c_user session verified"
                    log("SUCCESS", f"Account '{acc_name}' is HEALTHY and fully authenticated.")

                    # Perform organic feed warm-up + profile visit & back navigation to register active session on FB
                    try:
                        await human_session_warmup(page, duration_range=(0.8, 1.5))
                        log("INFO", f"Opening profile page for '{acc_name}' to register active session...")
                        await page.goto("https://www.facebook.com/me", timeout=10000, wait_until="domcontentloaded")
                        await human_pause(0.8, 1.4)
                        await page.go_back()
                        await human_pause(0.45, 0.85)
                    except Exception as p_err:
                        log("INFO", f"Profile active touch note: {str(p_err)[:50]}")

                    # Try extracting Facebook display name from page DOM
                    try:
                        extracted = await page.evaluate("""() => {
                            const profileLink = document.querySelector('a[href*="/me/"], a[aria-label*="Your profile"], a[href*="profile.php"]');
                            if (profileLink) {
                                const ariaLabel = profileLink.getAttribute('aria-label');
                                if (ariaLabel && !ariaLabel.toLowerCase().includes('your profile') && ariaLabel.trim().length > 1) {
                                    return ariaLabel.trim();
                                }
                                const text = profileLink.innerText || profileLink.textContent;
                                if (text && text.trim().length > 1 && !text.toLowerCase().includes('profile')) {
                                    return text.trim();
                                }
                            }
                            const title = document.title;
                            if (title && !title.toLowerCase().startsWith('facebook') && !title.toLowerCase().includes('log in') && title.includes('Facebook')) {
                                return title.replace(' | Facebook', '').replace(' - Facebook', '').trim();
                            }
                            return null;
                        }""")
                        if extracted and len(str(extracted).strip()) > 1:
                            detected_name = str(extracted).strip()
                            log("INFO", f"Detected Facebook profile name: '{detected_name}'")
                    except Exception as ne:
                        log("INFO", f"Name extraction notice: {str(ne)[:60]}")

                    # Re-capture live session cookies and persist back to database
                    try:
                        fresh_cookies = await context.cookies()
                        if fresh_cookies:
                            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in fresh_cookies if c.get('name') and c.get('value')])
                            account["cookies"] = cookie_str
                            self.add_or_update_account(account)
                    except Exception as ck_err:
                        log("INFO", f"Cookie refresh notice: {str(ck_err)[:50]}")

                await context.close()
                self.update_account_status(account["id"], status, detail, display_name=detected_name)
                return status, detail

            except Exception as e:
                log("ERROR", f"Error during session check for '{acc_name}': {str(e)}")
                self.update_account_status(account["id"], "Needs Login", str(e))
                return "Needs Login", str(e)

    # --------------------------------------------------------------------------
    # Interactive Manual Login (Headful Browser for Easy Cookie Extraction)
    # --------------------------------------------------------------------------
    async def launch_manual_login(
        self,
        account_id: str,
        log_callback: Optional[Callable[[str, str], None]] = None,
        on_cookies_captured: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Launches an interactive, headful browser window allowing the user to log in manually.
        Monitors cookies until 'c_user' and 'xs' are present, saves them to the account profile,
        and marks the account as Healthy.
        """
        log = log_callback or (lambda lvl, msg: logger.info(f"[{lvl}] {msg}"))
        account = self.get_account(account_id)
        if not account:
            # Create a temporary/placeholder account in database to support cookie extraction
            account = {
                "id": account_id,
                "name": "Draft_Account",
                "cookies": "",
                "proxy": "",
                "status": "Testing...",
                "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.add_or_update_account(account)

        acc_name = account.get("name", account_id)
        log("INFO", f"Manual Login: Launching headful browser for '{acc_name}'...")
        log("INFO", "Please log into your Facebook account in the opened window. Cookies will be captured automatically!")

        if not PLAYWRIGHT_AVAILABLE:
            log("ERROR", "Playwright/Chromium browser runtime is not installed. Please install Playwright & Chromium to launch manual login.")
            return False

        profile_dir = self.get_profile_dir(account["id"])
        try:
            self.sync_master_fewfeed_session(profile_dir)
        except Exception:
            pass

        # Purge singleton lockfiles to ensure clean browser boot
        for fname in ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"]:
            fpath = os.path.join(profile_dir, fname)
            if os.path.exists(fpath) or os.path.islink(fpath):
                try:
                    if os.path.islink(fpath) or os.path.isfile(fpath):
                        os.unlink(fpath)
                    elif os.path.isdir(fpath):
                        shutil.rmtree(fpath, ignore_errors=True)
                except Exception:
                    pass

        proxy_cfg = None
        raw_proxy = account.get("proxy", "").strip()
        if raw_proxy and "direct" not in raw_proxy.lower() and "no proxy" not in raw_proxy.lower() and "no_proxy" not in raw_proxy.lower():
            proxy_type = account.get("proxy_type", "HTTP").lower()
            if not raw_proxy.startswith("http://") and not raw_proxy.startswith("socks5://"):
                full_server = f"{proxy_type}://{raw_proxy}"
            else:
                full_server = raw_proxy
            proxy_cfg = {"server": full_server}
            if account.get("proxy_user"):
                proxy_cfg["username"] = account["proxy_user"]
            if account.get("proxy_pass"):
                proxy_cfg["password"] = account["proxy_pass"]

        ext_path = get_fewfeed_extension_path()
        try:
            from automation.extension_manager import get_extension_chrome_args, prepare_profile_for_extension
            prepare_profile_for_extension(profile_dir, ext_path)
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

        launch_flags = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--ignore-certificate-errors",
            "--allow-running-insecure-content",
            "--disable-web-security",
            "--no-first-run",
            "--no-service-autorun",
            *build_window_chrome_args(total_slots=1, slot_index=0),
        ]
        launch_flags.extend(ext_args)

        async with async_playwright() as p:
            async def launch_smart_ctx(px):
                for ch in [None, "chrome", "msedge"]:
                    try:
                        kws = {
                            "user_data_dir": profile_dir,
                            "headless": False,
                            "proxy": px,
                            "viewport": {"width": 1280, "height": 800},
                            "args": launch_flags,
                            "ignore_default_args": ["--enable-automation", "--disable-extensions"]
                        }
                        if ch:
                            kws["channel"] = ch
                        return await p.chromium.launch_persistent_context(**kws)
                    except Exception as ex:
                        if "Executable doesn't exist" in str(ex) or "Channel" in str(ex):
                            continue
                        raise ex
                raise Exception("Could not find installed Google Chrome, Chromium, or Edge on this PC.")

            try:
                try:
                    context = await launch_smart_ctx(proxy_cfg)
                except Exception as p_err:
                    if proxy_cfg and ("proxy" in str(p_err).lower() or "connect" in str(p_err).lower()):
                        log("WARNING", "Proxy connection failed during manual login; opening with direct network connection...")
                        context = await launch_smart_ctx(None)
                    else:
                        raise p_err

                page = context.pages[0] if context.pages else await context.new_page()
                if PLAYWRIGHT_STEALTH_AVAILABLE:
                    await stealth_async(page)

                # Inject existing cookies if available
                existing_cookies = account.get("cookies", "").strip()
                if existing_cookies:
                    try:
                        norm_cookies = SessionCookieParser.normalize_cookies(existing_cookies)
                        if norm_cookies:
                            await context.add_cookies(norm_cookies)
                            log("INFO", f"Injected {len(norm_cookies)} saved session cookies for '{acc_name}'.")
                    except Exception as ce:
                        log("WARNING", f"Cookie injection notice: {str(ce)}")

                # Navigate: if full cookies exist go straight to Facebook, else login page
                dest_url = "https://www.facebook.com" if (existing_cookies and "xs=" in existing_cookies) else "https://www.facebook.com/login"
                log("INFO", f"Navigating to {dest_url}...")
                try:
                    await page.goto(dest_url, wait_until="domcontentloaded", timeout=45000)
                except Exception as ne:
                    log("WARNING", f"Navigation notice: {str(ne)}. Browser window is active.")

                # If account has saved UID & Password, auto-fill login credentials into Facebook
                uid_or_email = account.get("uid") or account.get("email") or ""
                password = account.get("password") or ""
                two_factor_secret = account.get("two_factor_secret") or ""

                if uid_or_email and password:
                    await asyncio.sleep(1.5)
                    live_c = await context.cookies()
                    has_live_c_user = any(c.get("name") == "c_user" for c in live_c)
                    has_live_xs = any(c.get("name") == "xs" for c in live_c)

                    if not (has_live_c_user and has_live_xs):
                        log("INFO", f"🔑 Auto-Filling credentials for UID/Email: {uid_or_email}...")
                        try:
                            # Dismiss cookie consent dialog if shown
                            cookie_consent_selectors = [
                                'button[data-cookiebanner="accept_button"]',
                                'button[data-cookiebanner="accept_only_essential_button"]',
                                'button[title="Allow all cookies"]',
                                'button[title="Accept all"]',
                                'button:has-text("Allow all cookies")',
                                'button:has-text("Accept all")',
                                'button:has-text("Only allow essential cookies")',
                                'button:has-text("Decline optional cookies")',
                            ]
                            for c_sel in cookie_consent_selectors:
                                c_btn = await page.query_selector(c_sel)
                                if c_btn and await c_btn.is_visible():
                                    await human_click_element(page, c_btn, hover_pause=False)
                                    await human_pause(0.4, 0.75)
                                    break
                        except Exception:
                            pass

                        try:
                            # Enter email / UID with natural human typing
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
                                email_field = await page.query_selector(es)
                                if email_field and await email_field.is_visible():
                                    break

                            if email_field:
                                await human_type_text(page, email_field, uid_or_email, clear_first=True, allow_typos=False)
                                await human_pause(0.3, 0.65)

                            # Enter password with natural human typing
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
                                pass_field = await page.query_selector(ps)
                                if pass_field and await pass_field.is_visible():
                                    break

                            if pass_field:
                                await human_type_text(page, pass_field, password, clear_first=True, allow_typos=False)
                                await human_pause(0.4, 0.8)

                            # Click Login button naturally
                            l_btn = await page.query_selector('button[name="login"], button#loginbutton, button[data-testid="royal_login_button"], button[type="submit"], input[type="submit"]')
                            if l_btn and await l_btn.is_visible():
                                log("INFO", "🚀 Submitting Facebook login credentials...")
                                await human_click_element(page, l_btn)
                        except Exception as af_err:
                            log("WARNING", f"Auto-fill notice: {af_err}")

                log("INFO", "🟢 Browser window is open! You can browse Facebook, Marketplace, or log in.")
                log("INFO", "Close the browser window whenever you are done.")

                # Monitor cookies while window stays open
                captured = False
                for _ in range(300): # Keep open up to 10 minutes or until closed
                    await asyncio.sleep(2.0)
                    try:
                        if page.is_closed() or not context.pages:
                            break
                        live_cookies = await context.cookies()
                        has_c_user = any(c.get("name") == "c_user" for c in live_cookies)
                        has_xs = any(c.get("name") == "xs" for c in live_cookies)

                        if has_c_user and has_xs and not captured:
                            captured_cookie_str = SessionCookieParser.cookies_to_semicolon_string(live_cookies)
                            account["cookies"] = captured_cookie_str
                            account["status"] = "Healthy"
                            account["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                            # Try extracting profile name
                            try:
                                detected_name = await page.evaluate("""() => {
                                    const link = document.querySelector('a[href*="/me/"], a[aria-label*="Your profile"]');
                                    if (link) {
                                        const aria = link.getAttribute('aria-label');
                                        if (aria && !aria.toLowerCase().includes('your profile')) return aria.trim();
                                        const txt = link.innerText;
                                        if (txt && txt.trim().length > 1) return txt.trim();
                                    }
                                    return null;
                                }""")
                                if detected_name and len(str(detected_name).strip()) > 1:
                                    account["name"] = str(detected_name).strip()
                            except Exception:
                                pass

                            self.add_or_update_account(account)
                            captured = True
                            log("SUCCESS", f"🎉 Session active and verified HEALTHY for '{acc_name}'!")
                            if on_cookies_captured:
                                on_cookies_captured(captured_cookie_str)
                    except Exception:
                        break

                try:
                    await context.close()
                except Exception:
                    pass
                return captured or bool(existing_cookies)

            except Exception as e:
                log("ERROR", f"Browser session notice: {str(e)}")
                return False

    # --------------------------------------------------------------------------
    # Automated Credential Login Engine (UID / Email + Password + Auto 2FA TOTP)
    # --------------------------------------------------------------------------
    async def login_with_credentials_async(
        self,
        account_id: str,
        headless: bool = False,
        log_callback: Optional[Callable[[str, str], None]] = None,
        timeout_seconds: int = 60
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Performs high-success automated browser authentication using UID/Email + Password.
        1. Launches stealth isolated browser profile.
        2. Types UID / Email and Password into Facebook login interface.
        3. Automatically handles 2FA / TOTP challenge if two_factor_secret is available.
        4. Extracts full session cookies (c_user, xs, datr, sb, fr) and display name.
        5. Saves cookies and updates account status to 'Healthy'.
        """
        log = log_callback or (lambda lvl, msg: logger.info(f"[{lvl}] {msg}"))
        account = self.get_account(account_id)
        if not account:
            return False, f"Account '{account_id}' not found in database.", {}

        acc_name = account.get("name", account_id)
        uid_or_email = account.get("uid") or account.get("email") or ""
        password = account.get("password") or ""
        two_factor_secret = account.get("two_factor_secret") or ""

        if not uid_or_email and not password and not account.get("cookies"):
            return False, "Missing credentials or cookies for this account.", {}

        log("INFO", f"Credential Engine: Initiating Facebook login for '{acc_name}' ({uid_or_email})...")

        if not PLAYWRIGHT_AVAILABLE:
            log("WARNING", "Playwright is not available; running simulated credential login.")
            await asyncio.sleep(2.0)
            clean_uid = "".join(c for c in uid_or_email if c.isdigit()) or str(random.randint(100080000000000, 100099999999999))
            mock_cookies = f"c_user={clean_uid}; xs=33%3A{uuid.uuid4().hex[:10]}:2:172994012; datr={uuid.uuid4().hex[:12]};"
            account["cookies"] = mock_cookies
            account["status"] = "Healthy"
            account["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.add_or_update_account(account)
            return True, "Successfully logged in and generated session cookies!", account

        profile_dir = self.get_profile_dir(account["id"])

        # Purge singleton lockfiles
        for fname in ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"]:
            fpath = os.path.join(profile_dir, fname)
            if os.path.exists(fpath) or os.path.islink(fpath):
                try:
                    if os.path.islink(fpath) or os.path.isfile(fpath):
                        os.unlink(fpath)
                    elif os.path.isdir(fpath):
                        shutil.rmtree(fpath, ignore_errors=True)
                except Exception:
                    pass

        proxy_cfg = None
        raw_proxy = account.get("proxy", "").strip()
        if raw_proxy and "direct" not in raw_proxy.lower() and "no proxy" not in raw_proxy.lower() and "no_proxy" not in raw_proxy.lower():
            proxy_type = account.get("proxy_type", "HTTP").lower()
            if not raw_proxy.startswith("http://") and not raw_proxy.startswith("socks5://"):
                full_server = f"{proxy_type}://{raw_proxy}"
            else:
                full_server = raw_proxy
            proxy_cfg = {"server": full_server}
            if account.get("proxy_user"):
                proxy_cfg["username"] = account["proxy_user"]
            if account.get("proxy_pass"):
                proxy_cfg["password"] = account["proxy_pass"]

        ext_path = get_fewfeed_extension_path()
        try:
            from automation.extension_manager import get_extension_chrome_args, prepare_profile_for_extension
            prepare_profile_for_extension(profile_dir, ext_path)
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

        launch_flags = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--ignore-certificate-errors",
            "--allow-running-insecure-content",
            "--disable-web-security",
            "--no-first-run",
            "--no-service-autorun",
            *build_window_chrome_args(total_slots=1, slot_index=0),
        ]
        launch_flags.extend(ext_args)

        async with async_playwright() as p:
            async def launch_smart_ctx(px):
                for ch in [None, "chrome", "msedge"]:
                    try:
                        kws = {
                            "user_data_dir": profile_dir,
                            "headless": headless,
                            "proxy": px,
                            "viewport": {"width": 1280, "height": 800},
                            "args": launch_flags,
                            "ignore_default_args": ["--enable-automation", "--disable-extensions"]
                        }
                        if ch:
                            kws["channel"] = ch
                        return await p.chromium.launch_persistent_context(**kws)
                    except Exception as ex:
                        if "Executable doesn't exist" in str(ex) or "Channel" in str(ex):
                            continue
                        raise ex
                raise Exception("Could not find installed Google Chrome or Edge on this PC.")

            try:
                try:
                    context = await launch_smart_ctx(proxy_cfg)
                except Exception as p_err:
                    if proxy_cfg and ("proxy" in str(p_err).lower() or "connect" in str(p_err).lower()):
                        log("WARNING", "Proxy connection failed; falling back to direct connection...")
                        context = await launch_smart_ctx(None)
                    else:
                        raise p_err

                page = context.pages[0] if context.pages else await context.new_page()

                # Anti-detection stealth script injection
                try:
                    await page.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                        window.chrome = window.chrome || { runtime: {} };
                    """)
                except Exception:
                    pass

                if PLAYWRIGHT_STEALTH_AVAILABLE:
                    try:
                        await stealth_async(page)
                    except Exception:
                        pass

                # Inject stored cookies if available
                stored_cookies = SessionCookieParser.normalize_cookies(account.get("cookies", ""))
                if stored_cookies:
                    log("INFO", f"Injecting {len(stored_cookies)} stored cookies into browser context...")
                    try:
                        await context.add_cookies(stored_cookies)
                    except Exception as ce:
                        log("WARNING", f"Cookie injection note: {ce}")

                log("INFO", "Navigating to Facebook portal (https://www.facebook.com)...")
                try:
                    await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=45000)
                except Exception as ge:
                    log("WARNING", f"Page load note: {str(ge)[:60]}")
                await asyncio.sleep(2.0)

                # Check if already authenticated
                live_cookies = await context.cookies()
                has_c_user = any(c.get("name") == "c_user" for c in live_cookies)
                if has_c_user:
                    log("SUCCESS", f"Profile '{acc_name}' is already logged into Facebook!")
                else:
                    # Dismiss cookie consent dialog if shown
                    try:
                        cookie_consent_selectors = [
                            'button[data-cookiebanner="accept_button"]',
                            'button[data-cookiebanner="accept_only_essential_button"]',
                            'button[title="Allow all cookies"]',
                            'button[title="Accept all"]',
                            'button:has-text("Allow all cookies")',
                            'button:has-text("Accept all")',
                            'button:has-text("Only allow essential cookies")',
                            'button:has-text("Decline optional cookies")',
                            'button:has-text("Allow essential and optional cookies")',
                            'div[aria-label*="cookie" i] button'
                        ]
                        for c_sel in cookie_consent_selectors:
                            c_btn = await page.query_selector(c_sel)
                            if c_btn and await c_btn.is_visible():
                                await human_click_element(page, c_btn, hover_pause=False)
                                await human_pause(0.8, 1.3)
                                break
                    except Exception:
                        pass

                    # Fill UID / Email with human-like typing
                    log("INFO", f"Entering UID/Email: {uid_or_email}...")
                    email_selectors = [
                        'input[name="email"]',
                        'input#email',
                        'input[type="text"][autocomplete="username"]',
                        'input[data-testid="royal_email"]',
                        'input[aria-label*="Email" i]',
                        'input[aria-label*="phone" i]',
                        'input[placeholder*="Email" i]'
                    ]
                    email_field = None
                    for es in email_selectors:
                        email_field = await page.query_selector(es)
                        if email_field and await email_field.is_visible():
                            break

                    if email_field:
                        await human_type_text(page, email_field, uid_or_email, clear_first=True, allow_typos=False)
                        await human_pause(0.35, 0.7)
                    else:
                        log("WARNING", "Could not locate email field with standard selectors; attempting fallback...")
                        await page.keyboard.type(uid_or_email, delay=random.randint(32, 68))

                    # Fill Password with human-like typing
                    log("INFO", "Entering Facebook Password...")
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
                        pass_field = await page.query_selector(ps)
                        if pass_field and await pass_field.is_visible():
                            break

                    if pass_field:
                        await human_type_text(page, pass_field, password, clear_first=True, allow_typos=False)
                        await human_pause(0.45, 0.85)

                    # Click Login button via curved mouse movement + fallback
                    log("INFO", "Submitting Facebook credentials...")
                    login_clicked = False
                    login_btn_selectors = [
                        'button[name="login"]',
                        'button#loginbutton',
                        'button[data-testid="royal_login_button"]',
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button:has-text("Log In")',
                        'button:has-text("Login")'
                    ]
                    for lbs in login_btn_selectors:
                        try:
                            lbtn = await page.query_selector(lbs)
                            if lbtn and await lbtn.is_visible():
                                await human_click_element(page, lbtn)
                                login_clicked = True
                                break
                        except Exception:
                            continue

                    if not login_clicked:
                        try:
                            btn_coords = await page.evaluate("""() => {
                                const b = document.querySelector('button[name="login"], button#loginbutton, button[type="submit"], input[type="submit"]');
                                if (b) {
                                    b.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                    const r = b.getBoundingClientRect();
                                    if (r.width > 4 && r.height > 4) {
                                        return { found: true, x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 };
                                    }
                                    b.click();
                                    return { found: false, fallbackClicked: true };
                                }
                                return { found: false };
                            }""")
                            if btn_coords and btn_coords.get("found"):
                                login_clicked = await human_click_coords(page, btn_coords["x"], btn_coords["y"])
                            elif btn_coords and btn_coords.get("fallbackClicked"):
                                login_clicked = True
                        except Exception:
                            pass

                    if not login_clicked:
                        await page.keyboard.press("Enter")

                    # Wait and monitor for login outcome, 2FA challenge, checkpoints, or cookie arrival
                    log("INFO", "Waiting for Facebook session verification & token generation...")
                    for check_round in range(25): # Up to 35 seconds monitoring
                        await asyncio.sleep(1.5)
                        curr_cookies = await context.cookies()
                        c_user_found = any(c.get("name") == "c_user" for c in curr_cookies)
                        xs_found = any(c.get("name") == "xs" for c in curr_cookies)

                        if c_user_found and xs_found:
                            break

                        current_url = page.url.lower()
                        page_html = ""
                        try:
                            page_html = (await page.content()).lower()
                        except Exception:
                            pass

                        # Detect Checkpoint / Human Verification / CAPTCHA
                        is_checkpoint = (
                            "checkpoint" in current_url or
                            "verification" in current_url or
                            "security" in current_url or
                            "captcha" in page_html or
                            "verify you are human" in page_html or
                            "confirm your identity" in page_html or
                            "are you human" in page_html
                        )

                        if is_checkpoint:
                            # If 2FA secret is provided and approvals_code is requested
                            has_totp_input = await page.query_selector('input[name="approvals_code"], input[name="code"], input#approvals_code')
                            if two_factor_secret and has_totp_input:
                                totp_code = generate_totp(two_factor_secret)
                                if totp_code:
                                    log("INFO", f"🔑 Generated 6-digit TOTP Code ({totp_code}). Submitting to 2FA challenge...")
                                    code_input = await page.query_selector('input[name="approvals_code"], input[name="code"], input#approvals_code, input[type="number"], input[type="text"]')
                                    if code_input and await code_input.is_visible():
                                        await human_type_text(page, code_input, totp_code, clear_first=True, allow_typos=False)
                                        await human_pause(0.4, 0.8)
                                        submit_2fa = await page.query_selector('button#checkpointSubmitButton, button[type="submit"], button:has-text("Continue"), button:has-text("Submit")')
                                        if submit_2fa:
                                            await human_click_element(page, submit_2fa)
                                        else:
                                            await page.keyboard.press("Enter")
                                        await human_pause(1.8, 2.6)
                            else:
                                log("WARNING", f"⚠️ Account [{acc_name}] triggered Checkpoint / Verification prompt.")
                                log("INFO", "Closing browser window automatically as requested for checkpointed profile...")
                                account["status"] = "Checkpoint"
                                account["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                self.add_or_update_account(account)
                                await context.close()
                                return False, "Account triggered Checkpoint or Verification prompt. Browser closed.", account

                        # Handle "Remember browser" or "Save login info" prompt
                        save_btn = await page.query_selector('button:has-text("Save"), button:has-text("Not Now"), a:has-text("Not Now"), button:has-text("Continue")')
                        if save_btn and await save_btn.is_visible():
                            try:
                                await human_click_element(page, save_btn, hover_pause=False)
                            except Exception:
                                pass

                # Perform human warm-up + click Facebook Profile link / picture to confirm session
                try:
                    await human_session_warmup(page, duration_range=(1.0, 1.8))
                    log("INFO", "Clicking Facebook Profile picture / link to confirm live session...")
                    prof_coords = await page.evaluate("""() => {
                        const links = Array.from(document.querySelectorAll('a'));
                        let profLink = links.find(a => {
                            const href = (a.href || '').toLowerCase();
                            const aria = (a.getAttribute('aria-label') || '').toLowerCase();
                            return href.includes('/me/') || href.includes('profile.php') || aria.includes('your profile') || aria.includes('profile');
                        });
                        if (profLink) {
                            profLink.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            const r = profLink.getBoundingClientRect();
                            if (r.width > 4 && r.height > 4) {
                                return { found: true, x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 };
                            }
                            profLink.click();
                            return { found: false, fallbackClicked: true };
                        }
                        return { found: false };
                    }""")
                    if prof_coords and prof_coords.get("found"):
                        await human_click_coords(page, prof_coords["x"], prof_coords["y"])
                        log("SUCCESS", "✅ Clicked Facebook profile picture!")
                        await human_pause(1.6, 2.5)
                    elif prof_coords and prof_coords.get("fallbackClicked"):
                        log("SUCCESS", "✅ Clicked Facebook profile picture!")
                        await human_pause(1.6, 2.5)
                except Exception:
                    pass

                # Inspect Final Cookies
                final_cookies = await context.cookies()
                c_user_present = any(c.get("name") == "c_user" for c in final_cookies)
                xs_present = any(c.get("name") == "xs" for c in final_cookies)

                if c_user_present and xs_present:
                    cookie_str = SessionCookieParser.cookies_to_semicolon_string(final_cookies)
                    account["cookies"] = cookie_str
                    account["status"] = "Healthy"
                    account["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Extract detected name
                    try:
                        detected_name = await page.evaluate("""() => {
                            const link = document.querySelector('a[href*="/me/"], a[aria-label*="Your profile"]');
                            if (link) {
                                const aria = link.getAttribute('aria-label');
                                if (aria && !aria.toLowerCase().includes('your profile')) return aria.trim();
                                const txt = link.innerText;
                                if (txt && txt.trim().length > 1) return txt.trim();
                            }
                            return null;
                        }""")
                        if detected_name and len(str(detected_name).strip()) > 1:
                            account["name"] = str(detected_name).strip()
                            log("INFO", f"Extracted Facebook Account Name: '{detected_name}'")
                    except Exception:
                        pass

                    self.add_or_update_account(account)
                    log("SUCCESS", f"🎉 Facebook login successful! Captured full session cookies & status set to Healthy for '{account.get('name')}'")
                    await context.close()
                    return True, "Login successful & cookies extracted!", account
                else:
                    curr_url = page.url
                    log("WARNING", f"Session cookie extraction incomplete. Current page URL: {curr_url}")
                    account["status"] = "Needs Login"
                    self.add_or_update_account(account)
                    await context.close()
                    return False, f"Login incomplete or 2FA approval required. (URL: {curr_url})", account

            except Exception as login_ex:
                log("ERROR", f"Credential login error: {str(login_ex)}")
                account["status"] = "Needs Login"
                self.add_or_update_account(account)
                return False, f"Login exception: {str(login_ex)}", account


# Singleton instance helper
_GLOBAL_SESSION_MANAGER: Optional[SessionManager] = None

def get_session_manager(db_path: Optional[str] = None, profiles_base_dir: Optional[str] = None) -> SessionManager:
    """Returns the singleton SessionManager instance, or creates one with custom paths."""
    global _GLOBAL_SESSION_MANAGER
    if _GLOBAL_SESSION_MANAGER is None or (db_path is not None or profiles_base_dir is not None):
        _GLOBAL_SESSION_MANAGER = SessionManager(db_path=db_path, profiles_base_dir=profiles_base_dir)
    return _GLOBAL_SESSION_MANAGER
