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


def get_fewfeed_extension_path() -> Optional[str]:
    """
    Exhaustively resolves the absolute path to the unpacked FEWFEED extension folder.
    Guarantees discovery across PyInstaller --onedir, --onefile, source code, and custom paths.
    """
    # Priority 1: User-selected custom path from config
    custom = get_custom_extension_path()
    if custom:
        return custom

    base = get_base_dir()
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


def get_extension_chrome_args(ext_path: Optional[str] = None) -> List[str]:
    """
    Constructs the exact Chrome command-line arguments needed to load the unpacked extension.
    Crucially handles Windows path formatting (forward slashes) and modern Chrome flags.
    """
    if not ext_path:
        ext_path = get_fewfeed_extension_path()

    if not ext_path or not os.path.exists(ext_path):
        return []

    # Windows Chrome CLI requires forward slashes for extension paths
    clean_path = os.path.abspath(ext_path).replace("\\", "/")

    return [
        f"--load-extension={clean_path}",
        f"--disable-extensions-except={clean_path}",
        # Prevents modern Chrome (v128+) from disabling sideloaded extensions switch
        "--disable-features=DisableLoadExtensionCommandLineSwitch",
        # Ensures extension puzzle piece and toolbar menu are active
        "--enable-features=ExtensionsToolbarMenu",
        "--allow-legacy-extension-manifests",
        "--extensions-on-chrome-urls"
    ]


def prepare_profile_for_extension(profile_dir: str, ext_path: Optional[str] = None) -> None:
    """
    Pre-configures Chrome user profile Default/Preferences to enable Developer Mode
    and ensure unpacked extensions are allowed and visible.
    """
    if not profile_dir:
        return
    try:
        default_dir = os.path.join(profile_dir, "Default")
        os.makedirs(default_dir, exist_ok=True)
        pref_file = os.path.join(default_dir, "Preferences")

        prefs = {}
        if os.path.isfile(pref_file):
            try:
                with open(pref_file, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
            except Exception:
                prefs = {}

        if "extensions" not in prefs or not isinstance(prefs["extensions"], dict):
            prefs["extensions"] = {}

        prefs["extensions"]["developer_mode"] = True
        if "ui" not in prefs["extensions"] or not isinstance(prefs["extensions"]["ui"], dict):
            prefs["extensions"]["ui"] = {}
        prefs["extensions"]["ui"]["developer_mode"] = True

        with open(pref_file, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
    except Exception as e:
        logger.debug(f"Notice preparing profile preferences: {e}")
