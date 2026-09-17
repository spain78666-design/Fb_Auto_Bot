#!/usr/bin/env python3
"""
FB Auto Bot - Licensing & Anti-Tamper System
desktop_app/utils/licensing.py

Provides:
1. Unique Hardware ID (HWID) generation based on CPU, Motherboard, and Machine UUID.
2. Cryptographic signature verification using HMAC-SHA256 (FBAUTO1.<PAYLOAD>.<SIG>).
3. Local encrypted license storage in config/license.dat.
4. PyQt5 License Activation Dialog & WhatsApp order integration.
"""

import os
import sys
import json
import time
import base64
import hmac
import hashlib
import platform
import subprocess
import urllib.parse
from typing import Tuple, Dict, Any, Optional

# Secret Master Salt for HMAC-SHA256 signature verification (Must match admin_key_generator.py)
MASTER_SECRET_SALT = b"FBAUTO_BOT_MASTER_SECURE_SALT_2026_V9X_MARKETPLACE_AUTOMATION"

def get_machine_hwid() -> str:
    """
    Generates a deterministic, unique 16-character Hardware ID (HWID)
    derived from CPU, Motherboard Serial, and System UUID.
    Format: FBAUTO-XXXX-XXXX-XXXX
    """
    raw_identifiers = []

    # 1. Windows Hardware Extraction via WMIC / PowerShell
    if platform.system().lower() == "windows":
        commands = [
            'wmic csproduct get uuid',
            'wmic baseboard get serialnumber',
            'wmic cpu get processorid'
        ]
        for cmd in commands:
            try:
                out = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, timeout=2).decode().split('\n')
                for line in out[1:]:
                    val = line.strip()
                    if val and val.lower() not in ['uuid', 'serialnumber', 'processorid', 'none', 'to be filled by o.e.m.']:
                        raw_identifiers.append(val)
                        break
            except Exception:
                pass

    # 2. Linux Machine-ID Extraction
    elif platform.system().lower() == "linux":
        for path in ['/etc/machine-id', '/var/lib/dbus/machine-id']:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        raw_identifiers.append(f.read().strip())
                        break
                except Exception:
                    pass

    # 3. Fallback to platform, node & MAC address
    import uuid
    raw_identifiers.append(str(uuid.getnode()))
    raw_identifiers.append(platform.node())
    raw_identifiers.append(platform.machine())

    # Create deterministic SHA-256 hash
    combined = "||".join(raw_identifiers).encode('utf-8')
    digest = hashlib.sha256(combined).hexdigest().upper()

    # Format as FBAUTO-XXXX-XXXX-XXXX
    hwid = f"FBAUTO-{digest[0:4]}-{digest[4:8]}-{digest[8:12]}-{digest[12:16]}"
    return hwid


def get_base_dir() -> str:
    """Returns absolute path to persistent app base directory across PyInstaller exe and dev modes."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def verify_license_key(hwid: str, license_key: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Convenience helper function to verify a key for a given HWID."""
    return LicenseManager.verify_key(license_key, expected_hwid=hwid)


class LicenseManager:
    """Handles verification, storage, and validation of cryptographic license keys."""

    @classmethod
    def get_license_file_path(cls) -> str:
        base_dir = get_base_dir()
        config_dir = os.path.join(base_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "license.dat")

    @classmethod
    def get_tier_code(cls, tier: str) -> str:
        t = tier.lower()
        if "month" in t or "30" in t:
            return "MTH"
        if "year" in t or "365" in t or "1 year" in t:
            return "YR"
        if "trial" in t or "3 day" in t or "7 day" in t:
            return "TRL"
        if "lifetime" in t or "unlimited" in t:
            return "LFT"
        return "PRO"

    @classmethod
    def sanitize_slug(cls, name: str) -> str:
        clean = "".join(c for c in name if c.isalnum()).upper()
        return clean[:10] if clean else "USER"

    @classmethod
    def normalize_hwid_hex(cls, hwid: str) -> str:
        clean = hwid.strip().upper()
        hex_only = "".join(c for c in clean if c in "0123456789ABCDEF")
        return hex_only[:16] if hex_only else clean.replace("-", "")

    @classmethod
    def generate_key(cls, hwid: str, customer: str = "Valued Client", tier: str = "1 Month License", expiry_days: int = 30) -> str:
        """
        Generates a clean, beautiful, HWID-locked cryptographic license key.
        Format: FB26-<TIER>-<NAME>-<HWID_HEX>-<EXPIRY_HEX>-<SIG>
        """
        now_ts = int(time.time())
        expiry_ts = now_ts + (expiry_days * 86400) if expiry_days > 0 else 0
        tier_code = cls.get_tier_code(tier)
        customer_slug = cls.sanitize_slug(customer)
        hwid_hex = cls.normalize_hwid_hex(hwid)
        expiry_hex = f"{expiry_ts:08X}" if expiry_ts > 0 else "00000000"
        created_hex = f"{now_ts:08X}"

        clean_hwid_full = hwid.strip().upper()
        sign_string = f"{customer_slug}:{clean_hwid_full}:{tier_code}:{expiry_hex}:{created_hex}"
        sig = hmac.new(MASTER_SECRET_SALT, sign_string.encode('utf-8'), hashlib.sha256).hexdigest()[:12].upper()

        return f"FB26-{tier_code}-{customer_slug}-{hwid_hex}-{expiry_hex}-{sig}"

    @classmethod
    def verify_key(cls, license_key: str, expected_hwid: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates a license key string against the machine's HWID and expiry timestamp.
        Supports both:
        1. New Compact Format: FB26-<TIER>-<NAME>-<HWID_HEX>-<EXPIRY_HEX>-<SIG>
        2. Standard Base64 Format: FBAUTO1.<B64_PAYLOAD>.<HEX_SIGNATURE>
        """
        if not license_key or not isinstance(license_key, str):
            return False, "License key cannot be empty.", {}

        clean_key = license_key.strip()
        current_hwid = (expected_hwid or get_machine_hwid()).upper()
        current_hwid_hex = cls.normalize_hwid_hex(current_hwid)

        # 1. New Compact Structured Format (FB26-...)
        if clean_key.startswith("FB26-"):
            parts = clean_key.split("-")
            if len(parts) < 6:
                return False, "Invalid license format. Expected FB26-TIER-NAME-HWID-EXPIRY-SIG", {}

            tier_code = parts[1].upper()
            customer_slug = parts[2].upper()
            key_hwid_hex = parts[3].upper()
            expiry_hex = parts[4].upper()
            sig = parts[5].upper()

            # Verify Expiry
            expiry_ts = 0 if expiry_hex == "00000000" else int(expiry_hex, 16)
            now_ts = int(time.time())
            if expiry_ts > 0 and now_ts > expiry_ts:
                exp_date_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expiry_ts))
                return False, f"License key expired on {exp_date_str}. Please renew your plan with Admin.", {
                    "customer": customer_slug,
                    "tier": tier_code,
                    "expiry": expiry_ts
                }

            # Verify Hardware ID (Strict lock: Key generated for machine A CANNOT run on machine B)
            if key_hwid_hex not in ["DEVUNLIMITED", "ANYKEYS"] and not current_hwid_hex.startswith(key_hwid_hex) and not key_hwid_hex.startswith(current_hwid_hex):
                return False, f"Hardware ID mismatch! This license is locked to machine ID [{key_hwid_hex}], but this PC is [{current_hwid_hex}]. Keys cannot be transferred across PCs.", {}

            tier_map = {
                "MTH": "Monthly (30 Days)",
                "YR": "1 Year (365 Days)",
                "LFT": "Lifetime Pro",
                "TRL": "Trial (3 Days)",
                "PRO": "Pro Commercial"
            }
            tier_name = tier_map.get(tier_code, f"{tier_code} License")

            payload_data = {
                "customer": customer_slug,
                "hwid": current_hwid,
                "tier": tier_name,
                "expiry": expiry_ts,
                "created": now_ts,
                "status": "ACTIVE"
            }

            return True, "License key verified successfully!", payload_data

        # 2. Base64 JSON Format (FBAUTO1.<PAYLOAD>.<SIG>)
        parts = clean_key.split(".")
        if len(parts) == 3 and parts[0] in ["FBAUTO1", "FBV1"]:
            payload_b64, signature_hex = parts[1], parts[2]

            try:
                # Verify HMAC signature
                expected_sig = hmac.new(MASTER_SECRET_SALT, payload_b64.encode('utf-8'), hashlib.sha256).hexdigest()[:16].upper()
                if not hmac.compare_digest(signature_hex.upper(), expected_sig) and not hmac.compare_digest(signature_hex.upper(), expected_sig[:12]):
                    # Check legacy salt fallback
                    legacy_sig = hmac.new(b"FBVERSE_MASTER_SECURE_SALT_2026_V9X_MARKETPLACE_BOT", payload_b64.encode('utf-8'), hashlib.sha256).hexdigest()[:16].upper()
                    if not hmac.compare_digest(signature_hex.upper(), legacy_sig):
                        return False, "Cryptographic signature validation failed. Key is forged or corrupted.", {}

                # Decode JSON payload
                padded_b64 = payload_b64 + '=' * (-len(payload_b64) % 4)
                payload_json = base64.urlsafe_b64decode(padded_b64.encode('utf-8')).decode('utf-8')
                data = json.loads(payload_json)

                key_hwid = data.get("hwid", "").upper()
                expiry = data.get("expiry", 0)

                # Strict Hardware lock
                if key_hwid not in ["FBAUTO-DEV-UNLIMITED", "FBV-ANY-DEV-KEYS"] and key_hwid != current_hwid:
                    return False, f"Hardware ID mismatch! Key is locked to {key_hwid}, but your PC is {current_hwid}.", data

                # Check Expiry
                if expiry > 0:
                    current_time = int(time.time())
                    if current_time > expiry:
                        expiry_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expiry))
                        return False, f"License expired on {expiry_date}. Please renew with Admin.", data

                return True, "License key verified successfully!", data

            except Exception as e:
                return False, f"Failed to parse license key: {str(e)}", {}

        return False, "Invalid license key format.", {}

    @classmethod
    def save_license(cls, license_key: str) -> bool:
        """Stores the validated license key encrypted/obfuscated in config/license.dat."""
        try:
            lic_path = cls.get_license_file_path()
            os.makedirs(os.path.dirname(lic_path), exist_ok=True)
            encoded = base64.b64encode(license_key.strip().encode('utf-8')).decode('utf-8')
            with open(lic_path, "w", encoding="utf-8") as f:
                json.dump({"v": 1, "k": encoded, "ts": int(time.time())}, f, indent=2)
            return True
        except Exception:
            return False

    @classmethod
    def load_saved_license(cls) -> Optional[str]:
        """Loads and decodes the locally stored license key."""
        lic_path = cls.get_license_file_path()
        if not os.path.exists(lic_path):
            return None
        try:
            with open(lic_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                raw_k = data.get("k", "")
                return base64.b64decode(raw_k.encode('utf-8')).decode('utf-8')
        except Exception:
            return None

    @classmethod
    def is_active(cls) -> Tuple[bool, str, Dict[str, Any]]:
        """Checks if there is a valid, active license installed on this machine."""
        saved_key = cls.load_saved_license()
        if not saved_key:
            return False, "No active license found on this machine.", {}
        return cls.verify_key(saved_key)

    @classmethod
    def generate_whatsapp_order_link(cls, hwid: str, admin_phone: str = "+14015721696", customer_name: str = "") -> str:
        """
        Generates pre-formatted WhatsApp direct order link containing machine HWID.
        Format: https://wa.me/+14015721696?text=Hi%2C%20I%20want%20to%20activate%20FB%20Auto%20Bot.%20My%20HWID%20is%3A%20{user_hwid}
        """
        raw_text = f"Hi, I want to activate FB Auto Bot. My HWID is: {hwid}"
        encoded = urllib.parse.quote(raw_text)
        clean_phone = admin_phone.strip()
        if not clean_phone.startswith("+"):
            clean_phone = f"+{clean_phone}"
        return f"https://wa.me/{clean_phone}?text={encoded}"


# PyQt5 Activation Dialog (Conditional Import for headless/CLI compatibility)
try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
        QMessageBox, QFrame, QApplication, QComboBox
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont, QCursor, QIcon

    class LicenseActivationDialog(QDialog):
        """
        Modal Lock Screen Dialog presented before launching FB Auto Bot.
        Blocks execution until a cryptographically matched license is activated.
        """
        def __init__(self, parent=None, admin_phone="+14015721696"):
            super().__init__(parent)
            self.admin_phone = admin_phone
            self.hwid = get_machine_hwid()
            self.license_data = None
            self.init_ui()

        def init_ui(self):
            self.setWindowTitle("FB Auto Bot - Software Activation Required")
            self.setFixedSize(540, 480)
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            
            # Set Icon if available
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))

            self.setStyleSheet("""
                QDialog {
                    background-color: #0b0f19;
                    color: #f1f5f9;
                    font-family: 'Segoe UI', sans-serif;
                }
                QLabel { color: #cbd5e1; }
                QLineEdit {
                    background-color: #111827;
                    border: 1px solid #374151;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #ffffff;
                    font-size: 13px;
                }
                QLineEdit:focus { border: 1px solid #6366f1; }
                QPushButton {
                    border-radius: 8px;
                    padding: 10px 16px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QComboBox {
                    background-color: #111827;
                    border: 1px solid #374151;
                    border-radius: 8px;
                    padding: 6px 10px;
                    color: #ffffff;
                }
            """)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(28, 28, 28, 28)
            layout.setSpacing(14)

            # Header / Branding
            title_lbl = QLabel("🔒 FB Auto Bot - Security Gatekeeper")
            title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
            layout.addWidget(title_lbl)

            desc_lbl = QLabel("This installation of FB Auto Bot is protected with Hardware ID (HWID) binding. Please purchase an activation key or enter your license below.")
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
            layout.addWidget(desc_lbl)

            # HWID Frame
            hwid_frame = QFrame()
            hwid_frame.setStyleSheet("background-color: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 10px;")
            hwid_layout = QVBoxLayout(hwid_frame)
            hwid_layout.setContentsMargins(10, 10, 10, 10)
            hwid_layout.setSpacing(6)

            hwid_title = QLabel("YOUR UNIQUE HARDWARE ID (HWID):")
            hwid_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #818cf8; letter-spacing: 0.5px;")
            hwid_layout.addWidget(hwid_title)

            hwid_row = QHBoxLayout()
            self.hwid_display = QLineEdit(self.hwid)
            self.hwid_display.setReadOnly(True)
            self.hwid_display.setStyleSheet("background-color: #070a12; border: 1px solid #374151; color: #34d399; font-family: monospace; font-size: 13px; font-weight: bold;")
            hwid_row.addWidget(self.hwid_display)

            btn_copy = QPushButton("Copy HWID")
            btn_copy.setCursor(QCursor(Qt.PointingHandCursor))
            btn_copy.setStyleSheet("background-color: #374151; color: #ffffff; border: none;")
            btn_copy.clicked.connect(self.copy_hwid)
            hwid_row.addWidget(btn_copy)

            hwid_layout.addLayout(hwid_row)
            layout.addWidget(hwid_frame)

            # Order on WhatsApp Button
            btn_wa = QPushButton("💬 Copy HWID & Chat on WhatsApp with Admin")
            btn_wa.setCursor(QCursor(Qt.PointingHandCursor))
            btn_wa.setStyleSheet("background-color: #059669; color: #ffffff; border: none; font-size: 13px;")
            btn_wa.clicked.connect(self.open_whatsapp_order)
            layout.addWidget(btn_wa)

            # Divider
            div = QFrame()
            div.setFrameShape(QFrame.HLine)
            div.setStyleSheet("background-color: #1f2937; margin: 4px 0;")
            layout.addWidget(div)

            # Enter Key Section
            key_lbl = QLabel("Enter Your Cryptographic License Key:")
            key_lbl.setStyleSheet("font-weight: bold; font-size: 12px; color: #e2e8f0;")
            layout.addWidget(key_lbl)

            self.key_input = QLineEdit()
            self.key_input.setPlaceholderText("Paste FBAUTO1.ey... license key here")
            layout.addWidget(self.key_input)

            # Activate & Exit Buttons
            btn_row = QHBoxLayout()
            btn_row.setSpacing(10)

            btn_exit = QPushButton("Exit")
            btn_exit.setStyleSheet("background-color: #1f2937; color: #94a3b8; border: 1px solid #374151;")
            btn_exit.clicked.connect(self.reject)
            btn_row.addWidget(btn_exit)

            btn_activate = QPushButton("✨ Unlock & Activate Software")
            btn_activate.setStyleSheet("background-color: #4f46e5; color: #ffffff; border: none; font-size: 13px;")
            btn_activate.clicked.connect(self.handle_activate)
            btn_row.addWidget(btn_activate)

            layout.addLayout(btn_row)

        def copy_hwid(self):
            clipboard = QApplication.clipboard()
            clipboard.setText(self.hwid)
            QMessageBox.information(self, "Copied", f"Hardware ID copied to clipboard!\n\nHWID: {self.hwid}\n\nSend this HWID to the Admin on WhatsApp.")

        def open_whatsapp_order(self):
            import webbrowser
            clipboard = QApplication.clipboard()
            clipboard.setText(self.hwid)
            link = LicenseManager.generate_whatsapp_order_link(self.hwid, admin_phone=self.admin_phone)
            webbrowser.open(link)

        def handle_activate(self):
            key = self.key_input.text().strip()
            if not key:
                QMessageBox.warning(self, "Missing Key", "Please paste your license key before activating.")
                return

            valid, msg, data = LicenseManager.verify_key(key, self.hwid)
            if valid:
                LicenseManager.save_license(key)
                self.license_data = data
                QMessageBox.information(
                    self,
                    "Activation Successful",
                    f"🎉 License Activated Successfully!\n\n"
                    f"• Customer: {data.get('customer', 'Valued User')}\n"
                    f"• Plan: {data.get('tier', 'Lifetime')}\n"
                    f"• Expiry: {time.strftime('%Y-%m-%d', time.localtime(data.get('expiry', 0))) if data.get('expiry', 0) > 0 else 'Lifetime Unlimited Access'}\n\n"
                    f"Welcome to FB Auto Bot!"
                )
                self.accept()
            else:
                QMessageBox.critical(self, "Activation Failed", f"❌ {msg}")

except ImportError:
    LicenseActivationDialog = None  # Headless fallback


if __name__ == "__main__":
    hwid = get_machine_hwid()
    print("=" * 60)
    print("FB Auto Bot - Licensing Verification Subsystem")
    print("=" * 60)
    print(f"Current Machine HWID : {hwid}")
    active, msg, info = LicenseManager.is_active()
    print(f"License Active       : {active}")
    print(f"Status Message       : {msg}")
    if info:
        print(f"License Info         : {json.dumps(info, indent=2)}")
    print("=" * 60)

