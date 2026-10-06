"""
Chrome Profile & Shortcut Scanner
Scans Windows / PC folders for Chrome shortcuts (*.lnk) and Chrome profile directories
where Facebook accounts are pre-logged in.
"""

import os
import re
import glob
from typing import List, Dict, Any


def extract_shortcut_target_and_args(lnk_path: str) -> Dict[str, str]:
    """
    Inspects a Windows .lnk shortcut file to extract target executable and command line arguments.
    Works natively across Windows environments without requiring external third-party dependencies.
    """
    info = {
        "shortcut_path": os.path.abspath(lnk_path),
        "name": os.path.splitext(os.path.basename(lnk_path))[0],
        "profile_name": "",
        "user_data_dir": "",
        "target": ""
    }

    # 1. Try win32com if available on Windows
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(lnk_path)
        info["target"] = shortcut.TargetPath or ""
        args = shortcut.Arguments or ""
        
        m_prof = re.search(r'--profile-directory=["\']?([^"\'\s]+)["\']?', args, re.IGNORECASE)
        if m_prof:
            info["profile_name"] = m_prof.group(1).strip()
            
        m_ud = re.search(r'--user-data-dir=["\']?([^"\']+)["\']?', args, re.IGNORECASE)
        if m_ud:
            info["user_data_dir"] = m_ud.group(1).strip()
            
        if info["profile_name"] or info["user_data_dir"]:
            return info
    except Exception:
        pass

    # 2. Binary stream regex extraction (Pure Python, highly resilient)
    try:
        with open(lnk_path, "rb") as f:
            raw = f.read()

        # Check Latin-1 / ASCII
        raw_latin = raw.decode("latin1", errors="ignore")
        m1 = re.search(r'--profile-directory=["\']?([^"\'\s\x00]+)["\']?', raw_latin, re.IGNORECASE)
        if m1:
            info["profile_name"] = m1.group(1).replace("\x00", "").strip()

        m2 = re.search(r'--user-data-dir=["\']?([^"\'\x00]+)["\']?', raw_latin, re.IGNORECASE)
        if m2:
            info["user_data_dir"] = m2.group(1).replace("\x00", "").strip()

        # Check UTF-16LE if not found
        if not info["profile_name"]:
            raw_utf16 = raw.decode("utf-16le", errors="ignore")
            m3 = re.search(r'--profile-directory=["\']?([^"\'\s\x00]+)["\']?', raw_utf16, re.IGNORECASE)
            if m3:
                info["profile_name"] = m3.group(1).replace("\x00", "").strip()

        if not info["user_data_dir"]:
            raw_utf16 = raw.decode("utf-16le", errors="ignore")
            m4 = re.search(r'--user-data-dir=["\']?([^"\'\x00]+)["\']?', raw_utf16, re.IGNORECASE)
            if m4:
                info["user_data_dir"] = m4.group(1).replace("\x00", "").strip()
    except Exception:
        pass

    return info


def scan_folder_for_chrome_profiles(folder_path: str) -> List[Dict[str, Any]]:
    """
    Scans a user-provided directory for:
    1. Chrome Windows shortcuts (*.lnk)
    2. Chrome User Data profile subfolders ('Profile 1', 'Profile 2', 'Default', etc.)
    3. Custom standalone profile directories
    
    Returns structured list of account objects ready for automation.
    """
    if not folder_path or not os.path.isdir(folder_path):
        return []

    results: List[Dict[str, Any]] = []
    seen_ids = set()

    default_chrome_user_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
    if not os.path.isdir(default_chrome_user_data):
        default_chrome_user_data = ""

    # Strategy A: Scan for Windows Shortcuts (*.lnk)
    lnk_files = sorted(glob.glob(os.path.join(folder_path, "*.lnk")))
    for idx, lnk in enumerate(lnk_files, start=1):
        info = extract_shortcut_target_and_args(lnk)
        name = info["name"]
        p_name = info["profile_name"]
        u_data = info["user_data_dir"]

        # Resolve directory
        resolved_profile_dir = ""
        if u_data and os.path.isdir(u_data):
            if p_name and os.path.isdir(os.path.join(u_data, p_name)):
                resolved_profile_dir = os.path.join(u_data, p_name)
            else:
                resolved_profile_dir = u_data
        elif default_chrome_user_data and p_name:
            cand = os.path.join(default_chrome_user_data, p_name)
            if os.path.isdir(cand):
                resolved_profile_dir = cand
            else:
                resolved_profile_dir = default_chrome_user_data
        elif default_chrome_user_data:
            # Check if name has Profile N
            m_num = re.search(r'profile\s*(\d+)', name, re.IGNORECASE)
            if m_num:
                cand = os.path.join(default_chrome_user_data, f"Profile {m_num.group(1)}")
                if os.path.isdir(cand):
                    resolved_profile_dir = cand
                    p_name = f"Profile {m_num.group(1)}"

        acc_id = f"chrome_lnk_{idx}_{re.sub(r'[^a-zA-Z0-9_]', '_', name)}"
        if acc_id not in seen_ids:
            seen_ids.add(acc_id)
            desc_tag = f"Profile: {p_name}" if p_name else "Shortcut"
            results.append({
                "id": acc_id,
                "name": name,
                "source": "local_chrome_shortcut",
                "shortcut_path": lnk,
                "profile_dir": resolved_profile_dir,
                "profile_name": p_name,
                "user_data_dir": u_data or default_chrome_user_data,
                "status": f"Ready ({desc_tag})",
                "proxy": "Direct",
                "network_mode": "direct",
                "cookies": "" # No cookies needed - session is in profile
            })

    # Strategy B: If no .lnk files found, or folder is a Chrome User Data directory / contains profile folders
    if not results or os.path.basename(folder_path.rstrip(r"\/")).lower() == "user data":
        try:
            subdirs = [d for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))]
            # Check for Profile 1, Profile 2, Default, or subdirs containing Preferences/Cookies
            profile_subdirs = []
            for d in subdirs:
                full_d = os.path.join(folder_path, d)
                is_prof = (
                    d.lower() == "default"
                    or re.match(r'^profile\s*\d+', d, re.IGNORECASE)
                    or os.path.isfile(os.path.join(full_d, "Preferences"))
                    or os.path.isfile(os.path.join(full_d, "Web Data"))
                    or os.path.isdir(os.path.join(full_d, "Network"))
                )
                if is_prof:
                    profile_subdirs.append(d)

            # If no recognized profile names, treat all subdirs as custom profile directories
            if not profile_subdirs and not results:
                profile_subdirs = [d for d in subdirs if not d.startswith(".") and d.lower() not in ("temp", "crashpad", "cache")]

            for idx, p_name in enumerate(sorted(profile_subdirs), start=len(results) + 1):
                full_p = os.path.join(folder_path, p_name)
                acc_id = f"chrome_dir_{idx}_{re.sub(r'[^a-zA-Z0-9_]', '_', p_name)}"
                if acc_id not in seen_ids:
                    seen_ids.add(acc_id)
                    results.append({
                        "id": acc_id,
                        "name": f"Chrome - {p_name}",
                        "source": "local_chrome_folder",
                        "shortcut_path": "",
                        "profile_dir": full_p,
                        "profile_name": p_name,
                        "user_data_dir": folder_path,
                        "status": "Ready (Profile Folder)",
                        "proxy": "Direct",
                        "network_mode": "direct",
                        "cookies": ""
                    })
        except Exception:
            pass

    return results
