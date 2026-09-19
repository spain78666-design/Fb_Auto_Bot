#!/usr/bin/env python3
"""
FB Auto Bot - Admin License Key Generator Tool
admin_key_generator.py (Admin Only)

Generates cryptographically signed license keys matching client Hardware IDs (HWID),
with expiration limits (30 Days / 365 Days / Lifetime). Logs all issued licenses in admin_keys_db.json.
Supports both PyQt5 GUI and CLI generator mode.
"""

import os
import sys
import json
import time
import base64
import hmac
import hashlib
from typing import Dict, Any, Tuple, Optional

# Secret Master Salt (Must strictly match desktop_app/utils/licensing.py)
MASTER_SECRET_SALT = b"FBAUTO_BOT_MASTER_SECURE_SALT_2026_V9X_MARKETPLACE_AUTOMATION"
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin_keys_db.json")


def get_tier_code(tier: str) -> str:
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


def sanitize_slug(name: str) -> str:
    clean = "".join(c for c in name if c.isalnum()).upper()
    return clean[:10] if clean else "USER"


def normalize_hwid_hex(hwid: str) -> str:
    if not hwid:
        return ""
    clean = hwid.strip().upper()
    # Strip prefixes FBAUTO / FBAC / FBA / FB (with or without hyphens) to isolate raw machine hex
    import re
    stripped = re.sub(r'^(FBAUTO|FBAC|FBA|FB)[-\s]?', '', clean)
    hex_only = "".join(c for c in stripped if c in "0123456789ABCDEF")
    if not hex_only:
        hex_only = "".join(c for c in clean if c in "0123456789ABCDEF")
    return hex_only[:16]


def generate_license_key(
    customer_name: str,
    hwid: str,
    validity_days: int = 30,
    tier: str = "Monthly License",
    notes: str = ""
) -> Tuple[str, Dict[str, Any]]:
    """
    Creates a clean, beautiful, HWID-locked license key string for a customer's HWID.
    Format: FB26-<TIER>-<NAME>-<HWID_HEX>-<EXPIRY_HEX>-<SIG>
    """
    clean_hwid = hwid.strip().upper()
    now_ts = int(time.time())

    if validity_days > 0:
        expiry_ts = now_ts + (validity_days * 86400)
    else:
        expiry_ts = 0  # 0 indicates Lifetime

    tier_code = get_tier_code(tier)
    customer_slug = sanitize_slug(customer_name)
    hwid_hex = normalize_hwid_hex(clean_hwid)
    expiry_hex = f"{expiry_ts:08X}" if expiry_ts > 0 else "00000000"
    created_hex = f"{now_ts:08X}"

    sign_string = f"{customer_slug}:{clean_hwid}:{tier_code}:{expiry_hex}:{created_hex}"
    sig = hmac.new(MASTER_SECRET_SALT, sign_string.encode('utf-8'), hashlib.sha256).hexdigest()[:12].upper()

    license_key = f"FB26-{tier_code}-{customer_slug}-{hwid_hex}-{expiry_hex}-{sig}"

    payload = {
        "customer": customer_name.strip() or customer_slug,
        "hwid": clean_hwid,
        "tier": tier,
        "created": now_ts,
        "expiry": expiry_ts,
        "notes": notes.strip()
    }

    # Log into admin_keys_db.json
    log_issued_key(license_key, payload)

    return license_key, payload


def log_issued_key(license_key: str, payload: Dict[str, Any]):
    """Appends issued key record to admin_keys_db.json."""
    records = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            records = []

    record = {
        "key": license_key,
        "customer": payload["customer"],
        "hwid": payload["hwid"],
        "tier": payload["tier"],
        "created_date": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(payload["created"])),
        "expiry_date": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(payload["expiry"])) if payload["expiry"] > 0 else "LIFETIME",
        "notes": payload.get("notes", ""),
        "status": "ACTIVE"
    }

    # Avoid exact duplicates
    records = [r for r in records if r["key"] != license_key]
    records.insert(0, record)

    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save key database: {e}")


def format_whatsapp_delivery_text(customer_name: str, hwid: str, key: str, tier: str, expiry_date: str) -> str:
    """Prepares copyable customer delivery message."""
    return (
        f"🎉 *FB Auto Bot Activation Key Ready!*\n\n"
        f"Hi *{customer_name}*, thank you for choosing FB Auto Bot.\n\n"
        f"📋 *License Details:*\n"
        f"• *Plan:* {tier}\n"
        f"• *Hardware ID:* `{hwid}`\n"
        f"• *Validity:* {expiry_date}\n\n"
        f"🔑 *Your Activation Key:*\n"
        f"```{key}```\n\n"
        f"🚀 *How to Activate:*\n"
        f"1. Launch `FBAutoBot.exe` on your PC.\n"
        f"2. Paste the key above into the activation box.\n"
        f"3. Click *Unlock & Activate Software* to start automating!"
    )


# ==============================================================================
# CLI / Terminal Interactive Generator
# ==============================================================================
def run_cli():
    print("=" * 65)
    print("  🔑 FB AUTO BOT - ADMIN LICENSE KEY GENERATOR (ADMIN TOOL)")
    print("=" * 65)
    print("This tool signs cryptographic activation keys locked to customer HWIDs.\n")

    name = input("Enter Customer Name [e.g. John Doe]: ").strip()
    if not name:
        name = "Valued Customer"

    hwid = input("Enter Customer HWID [e.g. FBAUTO-A1B2-C3D4-E5F6]: ").strip()
    while not hwid:
        print("Hardware ID is required!")
        hwid = input("Enter Customer HWID: ").strip()

    print("\nSelect Validity Duration:")
    print(" [1] 30 Days Trial / Monthly ($10)")
    print(" [2] 365 Days (1 Year License) ($100)")
    print(" [3] Lifetime Unlimited Access")
    print(" [4] Custom Days")
    choice = input("Choice (1-4) [default: 2]: ").strip() or "2"

    days = 365
    tier = "1 Year License"
    if choice == "1":
        days = 30
        tier = "30-Day Monthly"
    elif choice == "3":
        days = 0
        tier = "Lifetime Access"
    elif choice == "4":
        try:
            days = int(input("Enter number of validity days: "))
            tier = f"{days}-Day Custom"
        except ValueError:
            days = 365
            tier = "1 Year License"

    notes = input("Optional Order ID / Notes: ").strip()

    key, payload = generate_license_key(name, hwid, validity_days=days, tier=tier, notes=notes)
    exp_str = time.strftime('%Y-%m-%d', time.localtime(payload["expiry"])) if payload["expiry"] > 0 else "LIFETIME"

    print("\n" + "=" * 65)
    print("✅ LICENSE GENERATED AND LOGGED TO admin_keys_db.json")
    print("=" * 65)
    print(f"Customer Name : {name}")
    print(f"Target HWID   : {hwid.upper()}")
    print(f"Tier / Plan   : {tier}")
    print(f"Expiry Date   : {exp_str}")
    print("-" * 65)
    print(f"🔑 LICENSE KEY:\n{key}")
    print("-" * 65)
    print("\n📱 PREFORMATTED WHATSAPP DELIVERY MESSAGE:\n")
    print(format_whatsapp_delivery_text(name, hwid.upper(), key, tier, exp_str))
    print("=" * 65)


# ==============================================================================
# GUI Mode (PyQt5 / Tkinter)
# ==============================================================================
def run_gui():
    try:
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit, QMessageBox,
            QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox
        )
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QFont, QCursor, QIcon

        class AdminKeyGenApp(QMainWindow):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("FB Auto Bot - Admin Key Generator & Licensing Suite")
                self.resize(880, 740)
                
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public", "assets", "logo.ico")
                if os.path.exists(icon_path):
                    self.setWindowIcon(QIcon(icon_path))

                self.setStyleSheet("""
                    QMainWindow { background-color: #0b0f19; color: #f1f5f9; }
                    QLabel { color: #cbd5e1; font-size: 12px; font-weight: 500; }
                    QLineEdit, QTextEdit {
                        background-color: #111827;
                        border: 1px solid #374151;
                        border-radius: 8px;
                        padding: 8px;
                        color: #ffffff;
                        font-family: monospace;
                    }
                    QLineEdit:focus, QTextEdit:focus { border: 1px solid #6366f1; }
                    QComboBox {
                        background-color: #111827;
                        border: 1px solid #374151;
                        border-radius: 8px;
                        padding: 6px;
                        color: #ffffff;
                    }
                    QPushButton {
                        border-radius: 8px;
                        padding: 9px 16px;
                        font-weight: bold;
                    }
                    QTableWidget {
                        background-color: #111827;
                        border: 1px solid #1f2937;
                        color: #e2e8f0;
                        gridline-color: #1f2937;
                    }
                    QHeaderView::section {
                        background-color: #1e293b;
                        color: #94a3b8;
                        padding: 6px;
                        font-weight: bold;
                        border: none;
                    }
                """)
                self.init_ui()

            def init_ui(self):
                central = QWidget()
                self.setCentralWidget(central)
                layout = QVBoxLayout(central)
                layout.setContentsMargins(20, 20, 20, 20)
                layout.setSpacing(14)

                # Header
                hdr = QLabel("🔑 FB Auto Bot - Admin License Management Suite")
                hdr.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
                layout.addWidget(hdr)

                sub = QLabel("Issue signed HWID-locked cryptographic keys and track active customers.")
                sub.setStyleSheet("color: #94a3b8; font-size: 11px;")
                layout.addWidget(sub)

                # Form Group
                form_grp = QGroupBox("Generate New Customer Key")
                form_grp.setStyleSheet("QGroupBox { color: #818cf8; font-weight: bold; border: 1px solid #1f2937; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
                f_layout = QVBoxLayout(form_grp)

                # Row 1: Name & HWID
                r1 = QHBoxLayout()
                v1 = QVBoxLayout()
                v1.addWidget(QLabel("Customer Name:"))
                self.name_in = QLineEdit()
                self.name_in.setPlaceholderText("e.g. John Doe / Seller Store")
                v1.addWidget(self.name_in)
                r1.addLayout(v1)

                v2 = QVBoxLayout()
                v2.addWidget(QLabel("Customer Hardware ID (HWID):"))
                self.hwid_in = QLineEdit()
                self.hwid_in.setPlaceholderText("e.g. FBAUTO-A1B2-C3D4-E5F6")
                v2.addWidget(self.hwid_in)
                r1.addLayout(v2)
                f_layout.addLayout(r1)

                # Row 2: Plan & Notes
                r2 = QHBoxLayout()
                v3 = QVBoxLayout()
                v3.addWidget(QLabel("License Duration / Plan:"))
                self.plan_combo = QComboBox()
                self.plan_combo.addItems([
                    "1 Year License - 365 Days ($100)",
                    "Monthly License - 30 Days ($10)",
                    "Lifetime Unlimited Access",
                    "7-Day Free Trial"
                ])
                v3.addWidget(self.plan_combo)
                r2.addLayout(v3)

                v4 = QVBoxLayout()
                v4.addWidget(QLabel("Notes / WhatsApp Contact:"))
                self.notes_in = QLineEdit()
                self.notes_in.setPlaceholderText("Order #1042 / +1234567890")
                v4.addWidget(self.notes_in)
                r2.addLayout(v4)
                f_layout.addLayout(r2)

                btn_gen = QPushButton("⚡ Generate Cryptographic License Key")
                btn_gen.setCursor(QCursor(Qt.PointingHandCursor))
                btn_gen.setStyleSheet("background-color: #4f46e5; color: #ffffff; font-size: 13px; margin-top: 8px;")
                btn_gen.clicked.connect(self.on_generate)
                f_layout.addWidget(btn_gen)

                layout.addWidget(form_grp)

                # Generated Key Output
                out_grp = QGroupBox("Generated License Key & Delivery Message")
                out_grp.setStyleSheet("QGroupBox { color: #34d399; font-weight: bold; border: 1px solid #1f2937; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
                o_layout = QVBoxLayout(out_grp)

                self.key_out = QLineEdit()
                self.key_out.setReadOnly(True)
                self.key_out.setStyleSheet("color: #34d399; font-weight: bold; font-size: 13px;")
                o_layout.addWidget(self.key_out)

                self.wa_out = QTextEdit()
                self.wa_out.setReadOnly(True)
                self.wa_out.setFixedHeight(90)
                o_layout.addWidget(self.wa_out)

                b_row = QHBoxLayout()
                btn_copy_key = QPushButton("📋 Copy License Key Only")
                btn_copy_key.setStyleSheet("background-color: #374151; color: #ffffff;")
                btn_copy_key.clicked.connect(lambda: self.copy_to_clip(self.key_out.text(), "License key"))
                b_row.addWidget(btn_copy_key)

                btn_copy_wa = QPushButton("💬 Copy Full WhatsApp Delivery Message")
                btn_copy_wa.setStyleSheet("background-color: #059669; color: #ffffff;")
                btn_copy_wa.clicked.connect(lambda: self.copy_to_clip(self.wa_out.toPlainText(), "WhatsApp message"))
                b_row.addWidget(btn_copy_wa)

                o_layout.addLayout(b_row)
                layout.addWidget(out_grp)

                # Recent Issued Keys Table
                layout.addWidget(QLabel("📜 Issued Licenses Log (admin_keys_db.json):"))
                self.table = QTableWidget()
                self.table.setColumnCount(5)
                self.table.setHorizontalHeaderLabels(["Customer", "HWID", "Plan", "Expiry Date", "Issued At"])
                self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.table.setFixedHeight(140)
                layout.addWidget(self.table)
                self.load_database_table()

            def on_generate(self):
                name = self.name_in.text().strip() or "Valued Customer"
                hwid = self.hwid_in.text().strip()
                if not hwid:
                    QMessageBox.warning(self, "Missing HWID", "Customer Hardware ID (HWID) is required!")
                    return

                plan_idx = self.plan_combo.currentIndex()
                if plan_idx == 0:
                    days, tier = 365, "1 Year License"
                elif plan_idx == 1:
                    days, tier = 30, "30-Day Monthly"
                elif plan_idx == 2:
                    days, tier = 0, "Lifetime Access"
                else:
                    days, tier = 7, "7-Day Trial"

                notes = self.notes_in.text().strip()
                key, payload = generate_license_key(name, hwid, validity_days=days, tier=tier, notes=notes)
                exp_str = time.strftime('%Y-%m-%d', time.localtime(payload["expiry"])) if payload["expiry"] > 0 else "LIFETIME"

                self.key_out.setText(key)
                self.wa_out.setPlainText(format_whatsapp_delivery_text(name, hwid.upper(), key, tier, exp_str))
                self.load_database_table()
                QMessageBox.information(self, "Key Generated", f"✅ Key successfully created for {name} ({hwid})!")

            def copy_to_clip(self, text, label):
                if not text:
                    return
                clipboard = QApplication.clipboard()
                clipboard.setText(text)
                QMessageBox.information(self, "Copied", f"{label} copied to clipboard!")

            def load_database_table(self):
                if not os.path.exists(DB_FILE):
                    return
                try:
                    with open(DB_FILE, "r", encoding="utf-8") as f:
                        records = json.load(f)
                    self.table.setRowCount(len(records))
                    for row, item in enumerate(records):
                        self.table.setItem(row, 0, QTableWidgetItem(str(item.get("customer", ""))))
                        self.table.setItem(row, 1, QTableWidgetItem(str(item.get("hwid", ""))))
                        self.table.setItem(row, 2, QTableWidgetItem(str(item.get("tier", ""))))
                        self.table.setItem(row, 3, QTableWidgetItem(str(item.get("expiry_date", ""))))
                        self.table.setItem(row, 4, QTableWidgetItem(str(item.get("created_date", ""))))
                except Exception:
                    pass

        app = QApplication(sys.argv)
        win = AdminKeyGenApp()
        win.show()
        sys.exit(app.exec_())

    except ImportError:
        run_cli()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        run_cli()
    else:
        run_gui()

