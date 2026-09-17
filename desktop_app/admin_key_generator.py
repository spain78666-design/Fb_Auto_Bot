#!/usr/bin/env python3
"""
FB Auto Bot - Admin License Key Generator Tool
desktop_app/admin_key_generator.py

Use this tool to generate cryptographic, HWID-locked license keys for your customers.
Can be run via GUI or via Command Line (CLI).

Examples:
  GUI mode:
    python admin_key_generator.py

  CLI mode:
    python admin_key_generator.py --hwid FBAUTO-A1B2-C3D4-E5F6 --customer "John Doe" --tier "Lifetime"
"""

import os
import sys
import json
import time
import argparse
from utils.licensing import LicenseManager, get_machine_hwid

VAULT_FILE = os.path.join(os.path.dirname(__file__), "config", "admin_keys_vault.json")

def load_vault() -> list:
    """Loads issued license records from config/admin_keys_vault.json."""
    if os.path.exists(VAULT_FILE):
        try:
            with open(VAULT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []

def save_vault(records: list):
    """Saves issued license records to config/admin_keys_vault.json."""
    os.makedirs(os.path.dirname(VAULT_FILE), exist_ok=True)
    try:
        with open(VAULT_FILE, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save to vault: {e}")

def add_record_to_vault(key: str, hwid: str, customer: str, tier: str, days: int, notes: str = ""):
    """Adds or updates a license record, enforcing 1 key per HWID."""
    records = load_vault()
    now_ts = int(time.time())
    expiry_ts = now_ts + (days * 86400) if days > 0 else 0
    
    created_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now_ts))
    expiry_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expiry_ts)) if expiry_ts > 0 else "LIFETIME"
    
    record = {
        "key": key,
        "customer": customer,
        "hwid": hwid.strip().upper(),
        "tier": tier,
        "created_date": created_date,
        "expiry_date": expiry_date,
        "notes": notes,
        "status": "ACTIVE",
        "created_ts": now_ts,
        "expiry_ts": expiry_ts
    }
    
    # Filter existing records for this key or HWID (1 key per system)
    clean_hwid = hwid.strip().upper()
    updated = [r for r in records if r.get("key") != key and r.get("hwid", "").upper() != clean_hwid]
    updated.insert(0, record)
    save_vault(updated)
    return record

def generate_cli(hwid: str, customer: str = "Client", tier: str = "Lifetime", days: int = 0):
    key = LicenseManager.generate_key(hwid=hwid, customer=customer, tier=tier, expiry_days=days)
    add_record_to_vault(key, hwid, customer, tier, days, "CLI Generation")
    print("\n" + "=" * 60)
    print("🔑 FB AUTO BOT - LICENSE KEY GENERATED & SAVED TO VAULT")
    print("=" * 60)
    print(f"Customer Name : {customer}")
    print(f"Target HWID   : {hwid.upper()}")
    print(f"License Tier  : {tier}")
    print(f"Duration      : {'Lifetime Access' if days == 0 else f'{days} Days'}")
    print(f"Vault Path    : {VAULT_FILE}")
    print("-" * 60)
    print("GENERATED ACTIVATION KEY (Send this to customer):")
    print(key)
    print("=" * 60 + "\n")
    return key


def run_gui():
    try:
        from PyQt5.QtWidgets import (
            QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
            QLineEdit, QPushButton, QComboBox, QMessageBox, QFrame
        )
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QFont, QCursor
    except ImportError:
        print("PyQt5 not installed. Using CLI mode instead.")
        hwid = input("Enter Customer HWID (e.g., FBAUTO-XXXX-XXXX-XXXX): ").strip()
        customer = input("Enter Customer Name: ").strip() or "Valued Client"
        days_str = input("Enter validity days (0 for lifetime): ").strip() or "0"
        generate_cli(hwid, customer, "Lifetime Pro", int(days_str))
        return

    app = QApplication(sys.argv)

    dialog = QDialog()
    dialog.setWindowTitle("FB Auto Bot - Admin Key Generator (Owner Tool)")
    dialog.setFixedSize(540, 480)
    dialog.setStyleSheet("""
        QDialog { background-color: #0b0f19; color: #f1f5f9; font-family: 'Segoe UI', sans-serif; }
        QLabel { color: #cbd5e1; }
        QLineEdit {
            background-color: #111827; border: 1px solid #374151; border-radius: 8px;
            padding: 8px 12px; color: #ffffff; font-size: 13px;
        }
        QLineEdit:focus { border: 1px solid #6366f1; }
        QPushButton { border-radius: 8px; padding: 10px 16px; font-weight: bold; font-size: 12px; }
        QComboBox { background-color: #111827; border: 1px solid #374151; border-radius: 8px; padding: 6px 10px; color: #ffffff; }
    """)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(14)

    header = QLabel("👑 Admin Cryptographic License Issuer")
    header.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
    layout.addWidget(header)

    sub = QLabel("Enter your client's Hardware ID (HWID) received via WhatsApp to issue an authentic activation key.")
    sub.setWordWrap(True)
    sub.setStyleSheet("color: #94a3b8; font-size: 12px;")
    layout.addWidget(sub)

    layout.addWidget(QLabel("Customer Name / Business Alias:"))
    name_input = QLineEdit()
    name_input.setPlaceholderText("e.g., Palwasha Doll / Spain Client")
    layout.addWidget(name_input)

    layout.addWidget(QLabel("Customer HWID (From user screen or WhatsApp message):"))
    hwid_input = QLineEdit()
    hwid_input.setPlaceholderText("FBAUTO-XXXX-XXXX-XXXX")
    layout.addWidget(hwid_input)

    tier_row = QHBoxLayout()
    col1 = QVBoxLayout()
    col1.addWidget(QLabel("Plan / Tier:"))
    tier_combo = QComboBox()
    tier_combo.addItems(["Lifetime Unlimited Pro", "Annual VIP License", "Monthly Standard", "7-Day Trial"])
    col1.addWidget(tier_combo)

    col2 = QVBoxLayout()
    col2.addWidget(QLabel("Duration Days (0 = Lifetime):"))
    days_input = QLineEdit("0")
    col2.addWidget(days_input)

    tier_row.addLayout(col1)
    tier_row.addLayout(col2)
    layout.addLayout(tier_row)

    btn_gen = QPushButton("⚡ Issue & Sign License Key")
    btn_gen.setCursor(QCursor(Qt.PointingHandCursor))
    btn_gen.setStyleSheet("background-color: #4f46e5; color: #ffffff; font-size: 13px;")
    layout.addWidget(btn_gen)

    layout.addWidget(QLabel("Generated Activation Key:"))
    key_output = QLineEdit()
    key_output.setReadOnly(True)
    key_output.setStyleSheet("background-color: #070a12; border: 1px solid #374151; color: #34d399; font-family: monospace; font-size: 11px;")
    layout.addWidget(key_output)

    btn_copy = QPushButton("📋 Copy License Key to Clipboard")
    btn_copy.setCursor(QCursor(Qt.PointingHandCursor))
    btn_copy.setStyleSheet("background-color: #059669; color: #ffffff; font-size: 12px;")
    layout.addWidget(btn_copy)

    def on_generate():
        hwid = hwid_input.text().strip()
        customer = name_input.text().strip() or "Client"
        tier = tier_combo.currentText()
        try:
            days = int(days_input.text().strip() or "0")
        except ValueError:
            days = 0

        if not hwid:
            QMessageBox.warning(dialog, "Missing HWID", "Please provide the customer's Hardware ID (HWID).")
            return

        key = LicenseManager.generate_key(hwid=hwid, customer=customer, tier=tier, expiry_days=days)
        add_record_to_vault(key, hwid, customer, tier, days, "GUI Generated")
        key_output.setText(key)
        QMessageBox.information(
            dialog,
            "Key Ready & Saved",
            f"License key generated, cryptographically signed, and saved to admin vault!\n\n"
            f"Customer: {customer}\n"
            f"Target HWID: {hwid.upper()}\n"
            f"Saved in: config/admin_keys_vault.json\n\n"
            f"Click 'Copy' and send to customer."
        )

    def on_copy():
        key = key_output.text().strip()
        if not key:
            QMessageBox.warning(dialog, "Empty Key", "Generate a license key first.")
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(key)
        QMessageBox.information(dialog, "Copied", "License key copied to clipboard! Paste it into WhatsApp to send to the buyer.")

    btn_gen.clicked.connect(on_generate)
    btn_copy.clicked.connect(on_copy)

    dialog.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FB Auto Bot - Admin License Key Generator")
    parser.add_argument("--hwid", help="Customer Hardware ID (HWID)")
    parser.add_argument("--customer", default="Valued Customer", help="Customer Name")
    parser.add_argument("--tier", default="Lifetime Pro", help="License Tier")
    parser.add_argument("--days", type=int, default=0, help="Days until expiry (0 = lifetime)")

    args = parser.parse_args()

    if args.hwid:
        generate_cli(hwid=args.hwid, customer=args.customer, tier=args.tier, days=args.days)
    else:
        run_gui()
