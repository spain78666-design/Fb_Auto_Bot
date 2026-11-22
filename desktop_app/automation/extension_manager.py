#!/usr/bin/env python3
"""
FB Auto Bot - METUS Chrome Extension Manager
Provides robust discovery, configuration, validation, and browser injection
for the METUS Chrome Extension (and custom unpacked extensions) across all automation bots
and Chrome setup sessions.
"""

import os
import sys
import json
import logging
from typing import Optional, List, Tuple

try:
    from automation.browser_window_manager import build_window_chrome_args
except ImportError:
    try:
        from desktop_app.automation.browser_window_manager import build_window_chrome_args
    except ImportError:
        def build_window_chrome_args(tile_rect=None, total_slots=1, slot_index=0, profile_directory=None, apply_scale_factor=True):
            return []

logger = logging.getLogger("ExtensionManager")

# Built-in Chrome component / unrelated store extension IDs to ignore during auto-discovery
IGNORED_CHROME_EXTENSION_IDS = {
    "nmmhkkegccagdldgiimedpiccmgmieda",  # Chrome Web Store Payments
    "pkedcjkdefgpdelpbcmbmeomcjbeemfm",  # Chrome Media Router
    "ghbmnnjooekpmoecnnnilnnbdlolhkhi",  # Google Docs Offline
    "aapocclcgogkmnckokdopfmhonfmgoek",  # Google Slides
    "aohghmighlieiainnegkcijnfilokake",  # Google Docs
    "felcaaldnbdncclmgdcncolpebgiejap",  # Google Sheets
    "blpcfgokakmgnkcojhhkbfbldkacnbeo",  # YouTube
    "pjkljhegncpnkpknbcohdijeoejaedia",  # Gmail
    "apdfllckaahabafndbhieahigkjlhalf",  # Google Drive
    "mhjfbmdgcfjbbpaeojofohoefgiehjai",  # Chrome PDF Viewer
    "neajdppkdcdipfabeoofebfddakdcjhd",  # Google Network Speech
}


def get_base_dir() -> str:
    """Returns application base directory handling PyInstaller bundle and script modes."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _is_legacy_fewfeed_path(path_or_name: str) -> bool:
    if not path_or_name:
        return False
    low = path_or_name.lower()
    return "fewfeed" in low


def get_custom_extension_path(allow_legacy_fewfeed: bool = False) -> Optional[str]:
    """Retrieves user-configured METUS/custom extension folder from config/extension_config.json."""
    try:
        cfg_file = os.path.join(get_base_dir(), "config", "extension_config.json")
        if os.path.isfile(cfg_file):
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            custom_p = data.get("extension_path")
            user_selected = bool(data.get("user_selected", False))
            if custom_p and os.path.isdir(custom_p) and os.path.exists(os.path.join(custom_p, "manifest.json")):
                if not allow_legacy_fewfeed and not user_selected and _is_legacy_fewfeed_path(custom_p):
                    return None
                return os.path.abspath(custom_p)
    except Exception as e:
        logger.debug(f"Notice reading custom extension config: {e}")
    return None


def set_custom_extension_path(folder_path: str, user_selected: bool = True) -> bool:
    """Stores user-configured custom unpacked METUS Chrome extension directory."""
    try:
        if folder_path and os.path.isdir(folder_path) and os.path.exists(os.path.join(folder_path, "manifest.json")):
            cfg_dir = os.path.join(get_base_dir(), "config")
            os.makedirs(cfg_dir, exist_ok=True)
            cfg_file = os.path.join(cfg_dir, "extension_config.json")
            payload = {
                "extension_path": os.path.abspath(folder_path),
                "user_selected": bool(user_selected),
                "extension_brand": "METUS"
            }
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            logger.info(f"Custom METUS extension path saved: {folder_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to save custom extension path: {e}")
    return False


def verify_extension_manifest(folder_path: str) -> Tuple[bool, str]:
    """Checks whether the directory contains a valid Chrome extension manifest.json."""
    if not folder_path or not os.path.isdir(folder_path):
        return False, "Directory does not exist"
    manifest_file = os.path.join(folder_path, "manifest.json")
    if not os.path.isfile(manifest_file):
        return False, "manifest.json not found in directory"
    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        name = manifest_data.get("name", "") or os.path.basename(os.path.abspath(folder_path))
        version = manifest_data.get("version", "")
        mv = manifest_data.get("manifest_version", 3)
        return True, f"Found {name} v{version} (MV{mv})"
    except Exception as e:
        return False, f"Invalid manifest.json: {e}"


def _find_extension_recursive(search_root: str, keywords: Tuple[str, ...] = ("metus",), max_depth: int = 3) -> Optional[str]:
    """Shallow recursive walk to find a directory containing a matching extension manifest.json."""
    if not search_root or not os.path.isdir(search_root):
        return None
    root_depth = search_root.rstrip(os.path.sep).count(os.path.sep)
    for root, dirs, files in os.walk(search_root):
        cur_depth = root.rstrip(os.path.sep).count(os.path.sep) - root_depth
        if cur_depth > max_depth:
            dirs.clear()
            continue
        if "manifest.json" in files:
            is_valid, desc = verify_extension_manifest(root)
            if is_valid:
                haystack = f"{desc} {root}".lower()
                if any(kw in haystack for kw in keywords):
                    return os.path.abspath(root)
    return None


def extract_extension_path_from_profile(profile_dir: str, prefer_metus: bool = True) -> Optional[str]:
    """
    Inspects a Chrome profile's Preferences & Extensions directory to find any installed
    METUS (or custom) Chrome extension folder saved by Chrome.
    """
    if not profile_dir or not os.path.isdir(profile_dir):
        return None

    fallback_candidates: List[str] = []

    for sub in ["Default", ""]:
        sub_dir = os.path.join(profile_dir, sub) if sub else profile_dir
        pref_file = os.path.join(sub_dir, "Preferences")
        if os.path.isfile(pref_file):
            try:
                with open(pref_file, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
                settings = prefs.get("extensions", {}).get("settings", {})
                for ext_id, ext_info in settings.items():
                    if ext_id in IGNORED_CHROME_EXTENSION_IDS:
                        continue
                    if not isinstance(ext_info, dict):
                        continue
                    # Skip disabled/uninstalled or default component extensions
                    if ext_info.get("was_installed_by_default"):
                        continue
                    raw_path = ext_info.get("path")
                    if not raw_path:
                        continue

                    resolved_path = raw_path
                    if not os.path.isabs(resolved_path):
                        resolved_path = os.path.join(sub_dir, "Extensions", raw_path)

                    if os.path.isdir(resolved_path) and os.path.isfile(os.path.join(resolved_path, "manifest.json")):
                        ok, desc = verify_extension_manifest(resolved_path)
                        if not ok:
                            continue
                        ext_name_meta = (ext_info.get("manifest", {}) or {}).get("name", "")
                        hay = f"{desc} {ext_name_meta} {resolved_path}".lower()
                        if "metus" in hay:
                            return os.path.abspath(resolved_path)
                        if prefer_metus and "fewfeed" in hay:
                            continue
                        if not hay.startswith("__msg_"):
                            fallback_candidates.append(os.path.abspath(resolved_path))
            except Exception:
                pass

        # Also scan <sub_dir>/Extensions/<ext_id>/<version>/manifest.json
        ext_root = os.path.join(sub_dir, "Extensions")
        if os.path.isdir(ext_root):
            try:
                for ext_id in os.listdir(ext_root):
                    if ext_id in IGNORED_CHROME_EXTENSION_IDS:
                        continue
                    ext_id_dir = os.path.join(ext_root, ext_id)
                    if not os.path.isdir(ext_id_dir):
                        continue
                    for ver in os.listdir(ext_id_dir):
                        ver_dir = os.path.join(ext_id_dir, ver)
                        if os.path.isfile(os.path.join(ver_dir, "manifest.json")):
                            ok, desc = verify_extension_manifest(ver_dir)
                            if ok:
                                hay = f"{desc} {ver_dir}".lower()
                                if "metus" in hay:
                                    return os.path.abspath(ver_dir)
                                if not (prefer_metus and "fewfeed" in hay):
                                    fallback_candidates.append(os.path.abspath(ver_dir))
            except Exception:
                pass

    return fallback_candidates[0] if fallback_candidates else None


def get_metus_extension_path(allow_legacy_fewfeed: bool = False) -> Optional[str]:
    """
    Resolves the absolute path to the METUS Chrome extension folder if present on disk
    or previously installed inside a Setup Chrome profile.
    Does NOT auto-save or force-load legacy FewFeed unless allow_legacy_fewfeed=True.
    """
    # Priority 1: User-selected custom path from config/extension_config.json
    custom = get_custom_extension_path(allow_legacy_fewfeed=allow_legacy_fewfeed)
    if custom:
        return custom

    base = get_base_dir()

    # Priority 2: Discover METUS extension installed in Master / Account Setup Chrome profiles
    profiles_root = os.path.join(base, "profiles")
    if os.path.isdir(profiles_root):
        for p_sub in ["master_metus_profile", "master_fewfeed_profile", "metus_shared", "fewfeed_shared", "temp_group_profile"]:
            extracted = extract_extension_path_from_profile(os.path.join(profiles_root, p_sub), prefer_metus=not allow_legacy_fewfeed)
            if extracted:
                return extracted
        try:
            for p_folder in os.listdir(profiles_root):
                extracted = extract_extension_path_from_profile(os.path.join(profiles_root, p_folder), prefer_metus=not allow_legacy_fewfeed)
                if extracted:
                    return extracted
        except Exception:
            pass

    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else base
    meipass = getattr(sys, '_MEIPASS', '')

    # Priority 3: Standard METUS folder locations
    metus_names = ["METUS", "Metus", "metus", "MetusExtension", "METUS_Extension"]
    roots = [
        base,
        os.path.join(base, "_internal"),
        os.path.join(base, "desktop_app"),
        os.path.join(base, "extensions"),
        exe_dir,
        os.path.join(exe_dir, "_internal"),
        os.path.join(exe_dir, "desktop_app"),
        os.path.join(exe_dir, "extensions"),
        os.path.abspath(os.path.join(base, "..")),
        os.path.abspath(os.path.join(exe_dir, "..")),
        os.path.join(meipass) if meipass else "",
        os.path.join(meipass, "_internal") if meipass else "",
        os.getcwd(),
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "Downloads"),
    ]

    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for name in metus_names:
            cand = os.path.join(root, name)
            if os.path.isdir(cand) and os.path.isfile(os.path.join(cand, "manifest.json")):
                return os.path.abspath(cand)

    # Priority 4: Shallow recursive scan for any folder containing "metus" in name or manifest
    for root in [base, exe_dir, meipass, os.getcwd()]:
        found = _find_extension_recursive(root, keywords=("metus",), max_depth=3)
        if found:
            return found

    if allow_legacy_fewfeed:
        legacy_roots = [
            os.path.join(base, "FewFeedV3.9.1"),
            os.path.join(base, "FEWFEED"),
            os.path.join(exe_dir, "FewFeedV3.9.1"),
            os.path.join(exe_dir, "FEWFEED"),
        ]
        for lc in legacy_roots:
            if os.path.isdir(lc) and os.path.isfile(os.path.join(lc, "manifest.json")):
                return os.path.abspath(lc)

    return None


# Backward-compatible alias (defaults to METUS / user-selected extension without forcing legacy FewFeed)
def get_fewfeed_extension_path(allow_legacy_fewfeed: bool = False) -> Optional[str]:
    return get_metus_extension_path(allow_legacy_fewfeed=allow_legacy_fewfeed)


def get_clean_path_for_chrome(path: str) -> str:
    """Returns a safe path string for Chrome command-line args, using 8.3 short paths on Windows to avoid space issues."""
    if not path:
        return ""
    abs_p = os.path.abspath(path)
    if os.name == 'nt' and os.path.exists(abs_p):
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(500)
            res = ctypes.windll.kernel32.GetShortPathNameW(abs_p, buf, 500)
            if res > 0 and buf.value:
                return buf.value.replace('\\', '/')
        except Exception:
            pass
    return abs_p.replace('\\', '/')


def get_extension_chrome_args(ext_path: Optional[str] = None) -> List[str]:
    """
    Constructs the Chrome command-line arguments to load an unpacked METUS extension if specified.
    Does NOT pass --disable-extensions-except so Chrome profile extensions installed from Web Store
    or chrome://extensions also stay active.
    """
    if not ext_path:
        ext_path = get_metus_extension_path(allow_legacy_fewfeed=False)

    if not ext_path or not os.path.exists(ext_path) or not os.path.isfile(os.path.join(ext_path, "manifest.json")):
        return ["--enable-extensions"]

    fwd_p = get_clean_path_for_chrome(ext_path)

    return [
        f"--load-extension={fwd_p}",
        "--enable-extensions",
        "--enable-unsafe-extension-debugging"
    ]


def prepare_profile_for_extension(profile_dir: str, ext_path: Optional[str] = None) -> None:
    """
    Ensures Chrome user profile Default/Preferences has Developer Mode enabled so users
    can install/load METUS in Chrome Setup cleanly, while strictly preserving Secure Preferences.
    """
    if not profile_dir:
        return
    try:
        default_dir = os.path.join(profile_dir, "Default")
        os.makedirs(default_dir, exist_ok=True)

        pref_file = os.path.join(default_dir, "Preferences")
        sec_pref = os.path.join(default_dir, "Secure Preferences")

        # If Secure Preferences exists from master profile clone, keep it completely intact
        if os.path.isfile(sec_pref) and os.path.isfile(pref_file):
            return

        prefs = {}
        if os.path.isfile(pref_file):
            try:
                with open(pref_file, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
            except Exception:
                prefs = {}

        if not isinstance(prefs, dict):
            prefs = {}

        if "extensions" not in prefs or not isinstance(prefs["extensions"], dict):
            prefs["extensions"] = {}

        # Enable developer mode cleanly so unpacked extensions (METUS) can be loaded easily
        prefs["extensions"]["developer_mode"] = True
        if "ui" not in prefs["extensions"] or not isinstance(prefs["extensions"]["ui"], dict):
            prefs["extensions"]["ui"] = {}
        prefs["extensions"]["ui"]["developer_mode"] = True

        with open(pref_file, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
    except Exception as e:
        logger.debug(f"Notice preparing profile preferences: {e}")


def get_system_chrome_executable() -> Optional[str]:
    """
    Finds the real Google Chrome (or Edge/Brave) executable on the user's PC.
    Prioritizes real Google Chrome on Windows, macOS, and Linux.
    """
    import shutil
    candidates = []
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        prog_w6432 = os.environ.get("ProgramW6432", r"C:\Program Files")
        candidates = [
            os.path.join(prog_files, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(prog_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(prog_w6432, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(prog_files, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(prog_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(local_app_data, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(prog_files, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
            os.path.join(local_app_data, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
    else:
        for name in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium", "microsoft-edge"]:
            p = shutil.which(name)
            if p:
                return p

    for c in candidates:
        if c and os.path.isfile(c):
            return os.path.abspath(c)

    for name in ["chrome", "google-chrome", "msedge"]:
        p = shutil.which(name)
        if p:
            return p

    return None


def launch_native_chrome_profile(
    profile_dir: str,
    ext_path: Optional[str] = None,
    urls: Optional[List[str]] = None
) -> Tuple[bool, str, Optional[object]]:
    """
    Launches the user's real desktop Google Chrome process with the chosen profile and METUS extension support.
    """
    import subprocess
    import shutil

    chrome_exe = get_system_chrome_executable()
    if not chrome_exe:
        return False, "Google Chrome / Edge executable not found on PC.", None

    os.makedirs(profile_dir, exist_ok=True)

    # Clear stale lock files
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

    if not ext_path:
        ext_path = get_metus_extension_path(allow_legacy_fewfeed=False)

    # Pre-configure preferences (enables developer mode without wiping existing extensions)
    try:
        prepare_profile_for_extension(profile_dir, ext_path)
    except Exception:
        pass

    norm_profile = os.path.normpath(os.path.abspath(profile_dir))
    cmd = [
        chrome_exe,
        f"--user-data-dir={norm_profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--lang=en-US,en",
        "--disable-blink-features=AutomationControlled",
        "--enable-extensions",
        "--enable-unsafe-extension-debugging",
        *build_window_chrome_args(total_slots=1, slot_index=0),
    ]

    if ext_path and os.path.isdir(ext_path) and os.path.exists(os.path.join(ext_path, "manifest.json")):
        fwd_ext = get_clean_path_for_chrome(ext_path)
        cmd.append(f"--load-extension={fwd_ext}")

    target_urls = urls or ["https://www.facebook.com", "chrome://extensions/"]
    cmd.extend(target_urls)

    try:
        proc = subprocess.Popen(cmd)
        return True, f"Launched Chrome ({os.path.basename(chrome_exe)}) with profile: {os.path.basename(norm_profile)}", proc
    except Exception as e:
        return False, f"Failed to launch Chrome: {str(e)}", None
