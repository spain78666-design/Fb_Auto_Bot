#!/usr/bin/env python3
"""
FB Auto Bot - Complete Automated Windows Installer & Admin KeyGen Builder
Runs PyInstaller and Inno Setup to create inside dist_installer/:
  1. FBAutoBot_Setup_v5.0.exe             (Customer Windows Setup Wizard)
  2. FBAutoBot_v5.0_Windows_Portable.zip  (Customer Portable ZIP Package)
  3. FBAutoBot_AdminKeyGen.exe            (Admin-Only Standalone License Key Generator)

Usage:
  python build_installer.py               # Build everything
  python build_installer.py --admin-only  # Build only FBAutoBot_AdminKeyGen.exe
"""

import os
import sys
import shutil
import zipfile
import argparse
import subprocess
import importlib.util

MUTABLE_OR_PRIVATE_CONFIG_FILES = {
    "accounts_db.json",
    "listings_history.json",
    "projects.json",
    "license.dat",
    "admin_keys_vault.json",
    "admin_keys_db.json",
    "custom_chrome_paths.json",
}

HIDDEN_IMPORTS = [
    # Automation engines (imported via try/except blocks in app.py)
    "automation.browser_bot",
    "automation.browser_window_manager",
    "automation.cookie_extractor_bot",
    "automation.extension_manager",
    "automation.fault_tolerance",
    "automation.friend_request_bot",
    "automation.group_bot",
    "automation.macro_recorder",
    "automation.page_creator_bot",
    "automation.profile_picture_bot",
    "automation.reels_uploader_bot",
    "automation.renew_delete_bot",
    "automation.session_manager",
    # Utilities, GUI & Config
    "utils.ai_spinner",
    "utils.image_processor",
    "utils.licensing",
    "utils.listings_tracker",
    "gui.styles",
    "gui.brand_loader",
    "config.settings",
    # Third-party & dynamic runtime dependencies
    "cv2",
    "numpy",
    "piexif",
    "requests",
    "aiohttp",
    "fake_useragent",
    "socks",
    "openai",
    "dotenv",
    "google.genai",
    "google.genai.types",
    # Standard library modules used dynamically
    "csv",
    "webbrowser",
    "ctypes",
    "urllib.parse",
    "urllib.request",
    "zipfile",
    "platform",
    "importlib.util",
    "socket",
    "uuid",
    "hmac",
    "hashlib",
    "base64",
    "asyncio",
]

COLLECT_ALL_PACKAGES = [
    "playwright",
    "playwright_stealth",
    "PIL",
    "PyQt5",
    "cv2",
    "google.genai",
    "fake_useragent",
]


def _data_spec(src: str, dst: str) -> str:
    sep = ";" if os.name == "nt" else ":"
    return f"{src}{sep}{dst}"


def _has_module(mod_name: str) -> bool:
    try:
        return importlib.util.find_spec(mod_name) is not None
    except Exception:
        return False


def find_inno_setup_compiler():
    """Locates the Inno Setup ISCC.exe compiler on Windows."""
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
        shutil.which("iscc"),
        shutil.which("ISCC.exe"),
    ]
    for path in possible_paths:
        if path and os.path.exists(path):
            return path
    return None


def fix_and_generate_valid_ico(base_dir: str) -> bool:
    """Regenerates assets/logo.ico from logo.png into a standard multi-resolution Windows ICO file."""
    png_path = os.path.join(base_dir, "assets", "logo.png")
    ico_path = os.path.join(base_dir, "assets", "logo.ico")
    try:
        from PIL import Image
        if os.path.exists(png_path):
            img = Image.open(png_path).convert("RGBA")
            img.save(
                ico_path,
                format="ICO",
                sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
            )
            print(f"✅ Re-generated valid multi-resolution Windows ICO icon: {ico_path}")
            return True
    except Exception as e:
        print(f"⚠️ Icon generation note: {e}")
    return os.path.exists(ico_path)


def _strip_mutable_config_files(dist_dir: str):
    """Removes developer/mutable config JSONs and admin files from frozen customer app output."""
    for rel_cfg in ["config", os.path.join("_internal", "config")]:
        cfg_dir = os.path.join(dist_dir, rel_cfg)
        if os.path.isdir(cfg_dir):
            for fname in MUTABLE_OR_PRIVATE_CONFIG_FILES:
                fpath = os.path.join(cfg_dir, fname)
                if os.path.isfile(fpath):
                    try:
                        os.remove(fpath)
                        print(f"🧹 Excluded private/mutable file from customer bundle: {os.path.join(rel_cfg, fname)}")
                    except Exception as e:
                        print(f"⚠️ Could not remove {fpath}: {e}")

    for root_file in ["admin_keys_db.json", "FBAutoBot_AdminKeyGen.exe"]:
        for candidate in [os.path.join(dist_dir, root_file), os.path.join(dist_dir, "_internal", root_file)]:
            if os.path.isfile(candidate):
                try:
                    os.remove(candidate)
                except Exception:
                    pass


def build_main_app(base_dir: str, icon_path: str) -> bool:
    """Compiles app.py into dist/FBAutoBot/ using PyInstaller (--onedir)."""
    print("\n[1/4] Compiling FBAutoBot Desktop App with PyInstaller...")

    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--noconsole",
        "--onedir",
        "--name", "FBAutoBot",
    ]
    if os.path.exists(icon_path):
        pyinstaller_cmd.append(f"--icon={icon_path}")

    # Customer-facing asset & package directories (NEVER bundle admin_keys_db.json)
    for folder in ["assets", "METUS", "FewFeedV3.9.1", "FEWFEED", "automation", "gui", "config", "utils"]:
        if os.path.exists(os.path.join(base_dir, folder)):
            pyinstaller_cmd.extend(["--add-data", _data_spec(folder, folder)])

    for pkg in COLLECT_ALL_PACKAGES:
        if _has_module(pkg):
            pyinstaller_cmd.extend(["--collect-all", pkg])
        else:
            print(f"⚠️ Optional package '{pkg}' not found in current Python environment (skipping --collect-all).")

    for mod in HIDDEN_IMPORTS:
        pyinstaller_cmd.extend(["--hidden-import", mod])

    pyinstaller_cmd.append("app.py")

    print(f"Running command: {' '.join(pyinstaller_cmd)}")
    result = subprocess.run(pyinstaller_cmd)
    if result.returncode != 0:
        print("❌ FBAutoBot PyInstaller compilation failed. Check logs above.")
        return False

    dist_dir = os.path.join(base_dir, "dist", "FBAutoBot")

    # Ensure METUS (or legacy) extension folders are directly present at top-level next to FBAutoBot.exe
    for ext_name in ["METUS", "FewFeedV3.9.1", "FEWFEED"]:
        dist_ext = os.path.join(dist_dir, ext_name)
        src_ext = os.path.join(base_dir, ext_name)
        if os.path.isdir(src_ext) and not os.path.isdir(dist_ext):
            try:
                shutil.copytree(src_ext, dist_ext, dirs_exist_ok=True)
                print(f"🧩 Bundled {ext_name} extension directly next to executable: {dist_ext}")
            except Exception as e:
                print(f"Notice bundling {ext_name}: {e}")

    _strip_mutable_config_files(dist_dir)
    return True


def build_admin_keygen_exe(base_dir: str, out_installer_dir: str, icon_path: str) -> bool:
    """Compiles admin_key_generator.py into standalone Admin-Only dist_installer/FBAutoBot_AdminKeyGen.exe."""
    print("\n[2/4] Compiling Standalone Admin License Key Generator EXE (FBAutoBot_AdminKeyGen.exe)...")
    os.makedirs(out_installer_dir, exist_ok=True)
    build_admin_work = os.path.join(base_dir, "build_admin")

    admin_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--noconsole",
        "--onefile",
        "--name", "FBAutoBot_AdminKeyGen",
        "--distpath", out_installer_dir,
        "--workpath", build_admin_work,
    ]
    if os.path.exists(icon_path):
        admin_cmd.append(f"--icon={icon_path}")

    for folder in ["assets", "utils"]:
        if os.path.exists(os.path.join(base_dir, folder)):
            admin_cmd.extend(["--add-data", _data_spec(folder, folder)])

    if _has_module("PyQt5"):
        admin_cmd.extend(["--collect-all", "PyQt5"])

    for mod in ["utils.licensing", "PyQt5", "PyQt5.QtWidgets", "PyQt5.QtCore", "PyQt5.QtGui"]:
        admin_cmd.extend(["--hidden-import", mod])

    admin_cmd.append("admin_key_generator.py")

    print(f"Running command: {' '.join(admin_cmd)}")
    res = subprocess.run(admin_cmd)
    shutil.rmtree(build_admin_work, ignore_errors=True)

    if res.returncode != 0:
        print("❌ FBAutoBot_AdminKeyGen PyInstaller compilation failed.")
        return False

    exe_name = "FBAutoBot_AdminKeyGen.exe" if os.name == "nt" else "FBAutoBot_AdminKeyGen"
    print(f"✅ Standalone Admin KeyGen created: {os.path.join(out_installer_dir, exe_name)}")
    return True


def create_portable_zip(base_dir: str, out_installer_dir: str) -> str:
    """Packages dist/FBAutoBot into a customer-ready portable ZIP."""
    print("\n[3/4] Generating Customer Portable ZIP package...")
    dist_dir = os.path.join(base_dir, "dist", "FBAutoBot")
    os.makedirs(out_installer_dir, exist_ok=True)

    zip_filename = os.path.join(out_installer_dir, "FBAutoBot_v5.0_Windows_Portable.zip")
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, dist_dir)
                zipf.write(file_path, arcname=os.path.join("FBAutoBot", rel_path))
    print(f"✅ Portable ZIP created: {zip_filename}")
    return zip_filename


def compile_inno_setup(base_dir: str, out_installer_dir: str) -> bool:
    """Compiles installer_setup.iss with Inno Setup ISCC.exe without mutating the source script."""
    print("\n[4/4] Compiling Windows Setup Wizard (.exe) via Inno Setup...")
    iscc_path = find_inno_setup_compiler()
    iss_script = os.path.join(base_dir, "installer_setup.iss")

    if not iscc_path:
        print("⚠️ Inno Setup (ISCC.exe) was not found in default paths.")
        print("👉 Download free Inno Setup (3MB) from: https://jrsoftware.org/isdl.php")
        print(f"👉 Once installed, right-click '{iss_script}' and click 'Compile'!")
        print(f"👉 Or run: \"C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe\" \"{iss_script}\"")
        return False

    print(f"Found Inno Setup Compiler at: {iscc_path}")
    compile_res = subprocess.run([iscc_path, iss_script])
    if compile_res.returncode == 0:
        print("\n" + "=" * 70)
        print("🎉 SUCCESS! Windows Setup Installer Created:")
        print(f"📁 {os.path.join(out_installer_dir, 'FBAutoBot_Setup_v5.0.exe')}")
        print("=" * 70)
        return True

    print("⚠️ Inno Setup icon compilation notice. Retrying using temporary fallback .iss...")
    tmp_iss = os.path.join(base_dir, "installer_setup_fallback.iss")
    try:
        with open(iss_script, "r", encoding="utf-8") as f:
            iss_content = f.read()
        iss_fallback = iss_content.replace("SetupIconFile=assets\\logo.ico", "; SetupIconFile=assets\\logo.ico")
        with open(tmp_iss, "w", encoding="utf-8") as f:
            f.write(iss_fallback)
        retry_res = subprocess.run([iscc_path, tmp_iss])
        if retry_res.returncode == 0:
            print("\n" + "=" * 70)
            print("🎉 SUCCESS! Windows Setup Installer Created:")
            print(f"📁 {os.path.join(out_installer_dir, 'FBAutoBot_Setup_v5.0.exe')}")
            print("=" * 70)
            return True
        print("❌ Inno Setup compilation returned an error.")
        return False
    finally:
        if os.path.exists(tmp_iss):
            try:
                os.remove(tmp_iss)
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="FB Auto Bot - Windows Build Pipeline")
    parser.add_argument("--admin-only", action="store_true", help="Build only FBAutoBot_AdminKeyGen.exe")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    out_installer_dir = os.path.join(base_dir, "dist_installer")

    print("=" * 70)
    print("🚀 FB Auto Bot - Windows Setup, EXE & Admin KeyGen Builder")
    print("=" * 70)

    if args.admin_only:
        fix_and_generate_valid_ico(base_dir)
        icon_path = os.path.join(base_dir, "assets", "logo.ico")
        ok = build_admin_keygen_exe(base_dir, out_installer_dir, icon_path)
        if not ok:
            sys.exit(1)
        return

    # Clean previous build artifacts
    for folder in ["build", "build_admin", "dist", "dist_installer"]:
        fp = os.path.join(base_dir, folder)
        if os.path.exists(fp):
            try:
                shutil.rmtree(fp, ignore_errors=True)
                print(f"🧹 Cleaned previous cache folder: {folder}")
            except Exception:
                pass

    fix_and_generate_valid_ico(base_dir)
    icon_path = os.path.join(base_dir, "assets", "logo.ico")

    if not build_main_app(base_dir, icon_path):
        sys.exit(1)

    admin_ok = build_admin_keygen_exe(base_dir, out_installer_dir, icon_path)
    create_portable_zip(base_dir, out_installer_dir)
    setup_ok = compile_inno_setup(base_dir, out_installer_dir)

    print("\n" + "=" * 70)
    print("📦 BUILD SUMMARY (desktop_app/dist_installer/):")
    print(f"  • Customer Setup Wizard : {'✅ READY' if setup_ok else '⚠️ Pending Inno Setup'} -> FBAutoBot_Setup_v5.0.exe")
    print("  • Customer Portable ZIP : ✅ READY -> FBAutoBot_v5.0_Windows_Portable.zip")
    print(f"  • Admin KeyGen EXE      : {'✅ READY (Admin Only)' if admin_ok else '❌ Failed'} -> FBAutoBot_AdminKeyGen.exe")
    print("=" * 70)


if __name__ == "__main__":
    main()
