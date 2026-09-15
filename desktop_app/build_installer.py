#!/usr/bin/env python3
"""
FB Auto Bot - Complete Automated Windows Installer & Package Builder
Runs PyInstaller and compiles with Inno Setup to create:
1. dist_installer/FBAutoBot_Setup_v5.0.exe (The Setup Wizard shown in your screenshot)
2. dist_installer/FBAutoBot_v5.0_Windows_Portable.zip (Portable Zip package)
"""

import os
import sys
import shutil
import subprocess
import zipfile

def find_inno_setup_compiler():
    """Locates the Inno Setup ISCC.exe compiler on Windows."""
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
        shutil.which("iscc"),
        shutil.which("ISCC.exe")
    ]
    for path in possible_paths:
        if path and os.path.exists(path):
            return path
    return None

def fix_and_generate_valid_ico(base_dir):
    """Regenerates assets/logo.ico from logo.png into a standard multi-resolution Windows ICO file."""
    png_path = os.path.join(base_dir, "assets", "logo.png")
    ico_path = os.path.join(base_dir, "assets", "logo.ico")
    try:
        from PIL import Image
        if os.path.exists(png_path):
            img = Image.open(png_path)
            img = img.convert("RGBA")
            img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            print(f"✅ Re-generated valid multi-resolution Windows ICO icon: {ico_path}")
            return True
    except Exception as e:
        print(f"⚠️ Icon generation note: {e}")
    return os.path.exists(ico_path)

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    print("=" * 70)
    print("🚀 FB Auto Bot - Windows Setup Installer Builder")
    print("=" * 70)

    # Step 0: Ensure pristine valid ICO file exists
    fix_and_generate_valid_ico(base_dir)

    # Step 1: Run PyInstaller in --onedir mode for clean Inno Setup packaging
    print("\n[1/3] Compiling Python codebase with PyInstaller...")
    
    icon_path = os.path.join(base_dir, "assets", "logo.ico")
    icon_flag = f'--icon="{icon_path}"' if os.path.exists(icon_path) else ''
    
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onedir",
        "--name", "FBAutoBot",
        "--add-data", "assets;assets" if os.name == 'nt' else "assets:assets",
        "--add-data", "FEWFEED;FEWFEED" if os.name == 'nt' else "FEWFEED:FEWFEED",
        "--add-data", "automation;automation" if os.name == 'nt' else "automation:automation",
        "--add-data", "gui;gui" if os.name == 'nt' else "gui:gui",
        "--add-data", "config;config" if os.name == 'nt' else "config:config",
        "--add-data", "utils;utils" if os.name == 'nt' else "utils:utils",
        "--add-data", "admin_keys_db.json;." if os.name == 'nt' else "admin_keys_db.json:.",
        "--collect-all", "playwright",
        "--collect-all", "playwright_stealth",
        "--collect-all", "PIL",
        "--collect-all", "PyQt5",
        "app.py"
    ]
    if os.path.exists(icon_path):
        pyinstaller_cmd.insert(4, f"--icon={icon_path}")

    print(f"Running command: {' '.join(pyinstaller_cmd)}")
    result = subprocess.run(pyinstaller_cmd)
    if result.returncode != 0:
        print("❌ PyInstaller compilation failed. Please check the logs above.")
        return

    # Step 2: Create Portable ZIP
    print("\n[2/3] Generating Portable ZIP package...")
    dist_dir = os.path.join(base_dir, "dist", "FBAutoBot")
    out_installer_dir = os.path.join(base_dir, "dist_installer")
    os.makedirs(out_installer_dir, exist_ok=True)

    zip_filename = os.path.join(out_installer_dir, "FBAutoBot_v5.0_Windows_Portable.zip")
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, dist_dir)
                zipf.write(file_path, arcname=os.path.join("FBAutoBot", rel_path))
    print(f"✅ Portable ZIP created: {zip_filename}")

    # Step 3: Compile Inno Setup Script
    print("\n[3/3] Compiling Windows Setup Wizard (.exe)...")
    iscc_path = find_inno_setup_compiler()
    iss_script = os.path.join(base_dir, "installer_setup.iss")

    if iscc_path:
        print(f"Found Inno Setup Compiler at: {iscc_path}")
        compile_cmd = [iscc_path, iss_script]
        compile_res = subprocess.run(compile_cmd)
        if compile_res.returncode == 0:
            print("\n" + "=" * 70)
            print("🎉 SUCCESS! Windows Setup Installer Created:")
            print(f"📁 {os.path.join(out_installer_dir, 'FBAutoBot_Setup_v5.0.exe')}")
            print("=" * 70)
        else:
            print("⚠️ Inno Setup icon compilation notice. Retrying compilation with default setup icon...")
            # Fallback: Comment out SetupIconFile if icon format triggers Inno Setup resource error
            with open(iss_script, "r", encoding="utf-8") as f:
                iss_content = f.read()
            iss_content_fallback = iss_content.replace("SetupIconFile=assets\\logo.ico", "; SetupIconFile=assets\\logo.ico")
            with open(iss_script, "w", encoding="utf-8") as f:
                f.write(iss_content_fallback)
            
            retry_res = subprocess.run(compile_cmd)
            if retry_res.returncode == 0:
                print("\n" + "=" * 70)
                print("🎉 SUCCESS! Windows Setup Installer Created:")
                print(f"📁 {os.path.join(out_installer_dir, 'FBAutoBot_Setup_v5.0.exe')}")
                print("=" * 70)
            else:
                print("❌ Inno Setup compilation returned an error.")
    else:
        print("⚠️ Inno Setup (ISCC.exe) was not found in default paths.")
        print("👉 Download free Inno Setup (3MB) from: https://jrsoftware.org/isdl.php")
        print(f"👉 Once installed, right-click '{iss_script}' and click 'Compile'!")
        print(f"👉 Or run: 'C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe {iss_script}'")

if __name__ == "__main__":
    main()
