#!/usr/bin/env python3
"""
FB Auto Bot - FewFeed Extension Manager
Provides robust discovery, configuration, validation, and browser injection
for the FewFeed Chrome Extension across all automation bots and browser sessions.
"""

import os
import sys
import json
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger("ExtensionManager")


def get_base_dir() -> str:
    """Returns application base directory handling PyInstaller bundle and script modes."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_custom_extension_path() -> Optional[str]:
    """Retrieves user-configured FewFeed extension folder from configuration if set and valid."""
    try:
        cfg_file = os.path.join(get_base_dir(), "config", "extension_config.json")
        if os.path.isfile(cfg_file):
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                custom_p = data.get("extension_path")
                if custom_p and os.path.isdir(custom_p) and os.path.exists(os.path.join(custom_p, "manifest.json")):
                    return os.path.abspath(custom_p)
    except Exception as e:
        logger.debug(f"Notice reading custom extension config: {e}")
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
            logger.info(f"Custom extension path saved: {folder_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to save custom extension path: {e}")
    return False


def verify_extension_manifest(folder_path: str) -> Tuple[bool, str]:
    """Checks whether the directory contains a valid FewFeed Chrome extension manifest."""
    if not folder_path or not os.path.isdir(folder_path):
        return False, "Directory does not exist"
    manifest_file = os.path.join(folder_path, "manifest.json")
    if not os.path.isfile(manifest_file):
        return False, "manifest.json not found in directory"
    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            name = manifest_data.get("name", "")
            version = manifest_data.get("version", "")
            mv = manifest_data.get("manifest_version", 2)
            return True, f"Found {name} v{version} (MV{mv})"
    except Exception as e:
        return False, f"Invalid manifest.json: {e}"


def _find_extension_recursive(search_root: str, max_depth: int = 3) -> Optional[str]:
    """Shallow recursive walk to find a directory containing FewFeed manifest.json."""
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
            if is_valid and ("fewfeed" in desc.lower() or "fewfeed" in root.lower()):
                return os.path.abspath(root)
    return None


def extract_extension_path_from_profile(profile_dir: str) -> Optional[str]:
    """Inspects a Chrome profile's Preferences to find the unpacked FewFeed extension path saved by Chrome."""
    if not profile_dir or not os.path.isdir(profile_dir):
        return None
    for sub in ["Default", ""]:
        pref_file = os.path.join(profile_dir, sub, "Preferences") if sub else os.path.join(profile_dir, "Preferences")
        if os.path.isfile(pref_file):
            try:
                with open(pref_file, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
                settings = prefs.get("extensions", {}).get("settings", {})
                for ext_id, ext_info in settings.items():
                    if isinstance(ext_info, dict):
                        p = ext_info.get("path")
                        if p and os.path.isdir(p) and os.path.isfile(os.path.join(p, "manifest.json")):
                            return os.path.abspath(p)
            except Exception:
                pass
    return None


def get_fewfeed_extension_path() -> Optional[str]:
    """
    Exhaustively resolves the absolute path to the unpacked FEWFEED extension folder.
    Guarantees discovery across PyInstaller --onedir, --onefile, source code, profiles, and custom paths.
    """
    # Priority 1: User-selected custom path from config
    custom = get_custom_extension_path()
    if custom:
        return custom

    base = get_base_dir()

    # Priority 1.5: Discover extension path from Master Setup profile Preferences if previously loaded
    profiles_root = os.path.join(base, "profiles")
    if os.path.isdir(profiles_root):
        for p_sub in ["master_fewfeed_profile", "fewfeed_shared", "temp_group_profile"]:
            extracted = extract_extension_path_from_profile(os.path.join(profiles_root, p_sub))
            if extracted:
                try:
                    set_custom_extension_path(extracted)
                except Exception:
                    pass
                return extracted
        try:
            for p_folder in os.listdir(profiles_root):
                extracted = extract_extension_path_from_profile(os.path.join(profiles_root, p_folder))
                if extracted:
                    try:
                        set_custom_extension_path(extracted)
                    except Exception:
                        pass
                    return extracted
        except Exception:
            pass

    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else base
    meipass = getattr(sys, '_MEIPASS', '')

    # Priority 2: Standard, PyInstaller onedir (_internal), and bundle candidate locations
    candidates = [
        # Base dir candidates
        os.path.join(base, "FewFeedV3.9.1"),
        os.path.join(base, "FEWFEED"),
        os.path.join(base, "_internal", "FewFeedV3.9.1"),
        os.path.join(base, "_internal", "FEWFEED"),
        os.path.join(base, "desktop_app", "FewFeedV3.9.1"),
        os.path.join(base, "desktop_app", "FEWFEED"),
        os.path.join(base, "extensions", "FewFeedV3.9.1"),
        os.path.join(base, "extensions", "FEWFEED"),
        os.path.join(base, "fewfeed"),
        # Exe dir candidates (critical for PyInstaller on Windows)
        os.path.join(exe_dir, "FewFeedV3.9.1"),
        os.path.join(exe_dir, "FEWFEED"),
        os.path.join(exe_dir, "_internal", "FewFeedV3.9.1"),
        os.path.join(exe_dir, "_internal", "FEWFEED"),
        os.path.join(exe_dir, "desktop_app", "FewFeedV3.9.1"),
        os.path.join(exe_dir, "desktop_app", "FEWFEED"),
        # Parent of base / exe (when running from dist or build subdirectory)
        os.path.abspath(os.path.join(base, "..", "FewFeedV3.9.1")),
        os.path.abspath(os.path.join(base, "..", "FEWFEED")),
        os.path.abspath(os.path.join(base, "..", "desktop_app", "FewFeedV3.9.1")),
        os.path.abspath(os.path.join(base, "..", "desktop_app", "FEWFEED")),
        os.path.abspath(os.path.join(exe_dir, "..", "FewFeedV3.9.1")),
        os.path.abspath(os.path.join(exe_dir, "..", "FEWFEED")),
        os.path.abspath(os.path.join(exe_dir, "..", "desktop_app", "FewFeedV3.9.1")),
        os.path.abspath(os.path.join(exe_dir, "..", "desktop_app", "FEWFEED")),
        os.path.abspath(os.path.join(exe_dir, "..", "..", "FewFeedV3.9.1")),
        os.path.abspath(os.path.join(exe_dir, "..", "..", "FEWFEED")),
        # PyInstaller temp unpack (_MEIPASS)
        os.path.join(meipass, "FewFeedV3.9.1") if meipass else "",
        os.path.join(meipass, "FEWFEED") if meipass else "",
        os.path.join(meipass, "_internal", "FewFeedV3.9.1") if meipass else "",
        os.path.join(meipass, "_internal", "FEWFEED") if meipass else "",
        os.path.join(meipass, "desktop_app", "FewFeedV3.9.1") if meipass else "",
        os.path.join(meipass, "desktop_app", "FEWFEED") if meipass else "",
        # Current working directory
        os.path.abspath("FewFeedV3.9.1"),
        os.path.abspath("FEWFEED"),
        os.path.abspath("desktop_app/FewFeedV3.9.1"),
        os.path.abspath("desktop_app/FEWFEED"),
        os.path.abspath("../FewFeedV3.9.1"),
        os.path.abspath("../FEWFEED"),
        # Standard user folders
        os.path.join(os.path.expanduser("~"), "Desktop", "FewFeedV3.9.1"),
        os.path.join(os.path.expanduser("~"), "Desktop", "FEWFEED"),
        os.path.join(os.path.expanduser("~"), "Downloads", "FewFeedV3.9.1"),
        os.path.join(os.path.expanduser("~"), "Downloads", "FEWFEED")
    ]

    for c in candidates:
        if c and os.path.isdir(c) and os.path.exists(os.path.join(c, "manifest.json")):
            resolved = os.path.abspath(c)
            try:
                set_custom_extension_path(resolved)
            except Exception:
                pass
            return resolved

    # Priority 3: Dynamic folder matching for any directory containing fewfeed in name
    search_dirs = [base, exe_dir, os.path.join(base, "desktop_app"), os.path.join(exe_dir, "desktop_app"), os.getcwd()]
    for sdir in search_dirs:
        if sdir and os.path.isdir(sdir):
            try:
                for entry in os.listdir(sdir):
                    if "fewfeed" in entry.lower():
                        full_entry = os.path.join(sdir, entry)
                        if os.path.isdir(full_entry) and os.path.exists(os.path.join(full_entry, "manifest.json")):
                            resolved = os.path.abspath(full_entry)
                            try:
                                set_custom_extension_path(resolved)
                            except Exception:
                                pass
                            return resolved
            except Exception:
                pass

    # Priority 4: Shallow recursive search from known roots
    for root in [base, exe_dir, meipass, os.getcwd()]:
        found = _find_extension_recursive(root, max_depth=3)
        if found:
            try:
                set_custom_extension_path(found)
            except Exception:
                pass
            return found

    return None


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
    Constructs the exact, standard Chrome command-line arguments needed to load the unpacked extension.
    Uses forward-slash absolute path format recognized by Chrome on Windows and Unix.
    """
    if not ext_path:
        ext_path = get_fewfeed_extension_path()

    if not ext_path or not os.path.exists(ext_path):
        return []

    fwd_p = get_clean_path_for_chrome(ext_path)

    return [
        f"--load-extension={fwd_p}",
        "--enable-extensions",
        "--enable-unsafe-extension-debugging"
    ]


def prepare_profile_for_extension(profile_dir: str, ext_path: Optional[str] = None) -> None:
    """
    Ensures Chrome user profile Default/Preferences has Developer Mode and extension toolbar settings
    while strictly preserving Secure Preferences to maintain Chrome's HMAC signatures for cloned profiles.
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

        # Enable developer mode cleanly so unpacked extensions run without restrictions
        prefs["extensions"]["developer_mode"] = True
        if "ui" not in prefs["extensions"] or not isinstance(prefs["extensions"]["ui"], dict):
            prefs["extensions"]["ui"] = {}
        prefs["extensions"]["ui"]["developer_mode"] = True

        KNOWN_FEWFEED_IDS = [
            "anmefodffnjcfkmodpaijmckfhcnccnn",
            "bjeenfnhfdgdgijpmgdekklokkisiakk",
            "ogpafcdeciolipenoiknghjhoihmkekh"
        ]
        pinned = prefs["extensions"].get("pinned_extensions", [])
        if not isinstance(pinned, list):
            pinned = []

        for fid in KNOWN_FEWFEED_IDS:
            if fid not in pinned:
                pinned.append(fid)

        # Pin FewFeed extension icon directly onto the Chrome toolbar
        prefs["extensions"]["pinned_extensions"] = pinned
        prefs["extensions"]["toolbar"] = pinned

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
            # Edge as fallback
            os.path.join(prog_files, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(prog_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(local_app_data, "Microsoft", "Edge", "Application", "msedge.exe"),
            # Brave as fallback
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
    Launches the user's real desktop Google Chrome process with the chosen profile and FewFeed extension loaded.
    Bypasses Playwright sandbox so Chrome runs 100% natively without any --no-sandbox or security warnings.
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
        ext_path = get_fewfeed_extension_path()

    # Pre-configure preferences
    try:
        prepare_profile_for_extension(profile_dir, ext_path)
    except Exception:
        pass

    # Build launch command
    norm_profile = os.path.normpath(os.path.abspath(profile_dir))
    cmd = [
        chrome_exe,
        f"--user-data-dir={norm_profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        "--lang=en-US,en",
        "--disable-blink-features=AutomationControlled",
        "--enable-extensions",
        "--enable-unsafe-extension-debugging"
    ]

    if ext_path and os.path.isdir(ext_path) and os.path.exists(os.path.join(ext_path, "manifest.json")):
        fwd_ext = os.path.abspath(ext_path).replace('\\', '/')
        cmd.append(f"--load-extension={fwd_ext}")
        cmd.append(f"--disable-extensions-except={fwd_ext}")

    target_urls = urls or ["https://www.facebook.com", "https://fewfeed.app", "chrome://extensions/"]
    cmd.extend(target_urls)

    try:
        proc = subprocess.Popen(cmd)
        return True, f"Launched Chrome ({os.path.basename(chrome_exe)}) with profile: {os.path.basename(norm_profile)}", proc
    except Exception as e:
        return False, f"Failed to launch Chrome: {str(e)}", None
