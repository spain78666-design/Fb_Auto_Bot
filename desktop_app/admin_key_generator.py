#!/usr/bin/env python3
"""
FB Auto Bot - Admin License Key Generator & Licensing Suite
desktop_app/admin_key_generator.py (Admin Only)

Use this tool to generate cryptographic, HWID-locked license keys for customers.
Can be run as a standalone Windows executable (FBAutoBot_AdminKeyGen.exe), via Python GUI, or via CLI.

Examples:
  GUI mode:
    python admin_key_generator.py

  CLI mode:
    python admin_key_generator.py --hwid FBAUTO-A1B2-C3D4-E5F6 --customer "John Doe" --tier "Lifetime" --days 0
"""

import os
import sys
import json
import time
import argparse
from typing import List, Dict, Any

# Ensure utils.* resolves both from desktop_app/ and inside PyInstaller bundles
_CUR_DIR = os.path.dirname(os.path.abspath(__file__))
if _CUR_DIR not in sys.path:
    sys.path.insert(0, _CUR_DIR)

from utils.licensing import LicenseManager, get_machine_hwid, get_base_dir


def _resolve_vault_file() -> str:
    """
    Returns persistent JSON database path next to the EXE when frozen,
    or inside desktop_app/config/admin_keys_vault.json in dev mode.
    """
    base_dir = get_base_dir()
    if getattr(sys, "frozen", False):
        return os.path.join(base_dir, "admin_keys_db.json")
    return os.path.join(base_dir, "config", "admin_keys_vault.json")


VAULT_FILE = _resolve_vault_file()


def _resolve_icon_path() -> str:
    """Finds assets/logo.ico across PyInstaller _MEIPASS and source directories."""
    candidates = [
        os.path.join(getattr(sys, "_MEIPASS", ""), "assets", "logo.ico"),
        os.path.join(get_base_dir(), "assets", "logo.ico"),
        os.path.join(_CUR_DIR, "assets", "logo.ico"),
        os.path.join(os.path.dirname(_CUR_DIR), "public", "assets", "logo.ico"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return ""


def load_vault() -> List[Dict[str, Any]]:
    """Loads issued license records from persistent admin vault JSON."""
    records: List[Dict[str, Any]] = []
    seen_keys = set()
    candidate_files = [VAULT_FILE]
    if not getattr(sys, "frozen", False):
        legacy_db = os.path.join(_CUR_DIR, "admin_keys_db.json")
        if legacy_db != VAULT_FILE:
            candidate_files.append(legacy_db)

    for fp in candidate_files:
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            k = item.get("key")
                            if k and k not in seen_keys:
                                seen_keys.add(k)
                                records.append(item)
            except Exception:
                pass
    return records


def save_vault(records: List[Dict[str, Any]]):
    """Saves issued license records to persistent admin vault JSON."""
    parent_dir = os.path.dirname(VAULT_FILE)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    try:
        with open(VAULT_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save to vault: {e}")


def add_record_to_vault(key: str, hwid: str, customer: str, tier: str, days: int, notes: str = "") -> Dict[str, Any]:
    """Adds or updates a license record, keeping newest issuance at top."""
    records = load_vault()
    now_ts = int(time.time())
    expiry_ts = now_ts + (days * 86400) if days > 0 else 0

    created_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_ts))
    expiry_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expiry_ts)) if expiry_ts > 0 else "LIFETIME"

    record = {
        "key": key,
        "customer": customer.strip() or "Valued Customer",
        "hwid": hwid.strip().upper(),
        "tier": tier,
        "created_date": created_date,
        "expiry_date": expiry_date,
        "notes": notes.strip(),
        "status": "ACTIVE",
        "created_ts": now_ts,
        "expiry_ts": expiry_ts,
    }

    clean_hwid = hwid.strip().upper()
    updated = [r for r in records if r.get("key") != key and r.get("hwid", "").upper() != clean_hwid]
    updated.insert(0, record)
    save_vault(updated)
    return record


def format_whatsapp_delivery_text(customer_name: str, hwid: str, key: str, tier: str, expiry_date: str) -> str:
    """Prepares copyable customer delivery message for WhatsApp."""
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


def generate_cli(hwid: str, customer: str = "Valued Customer", tier: str = "Lifetime Access", days: int = 0, notes: str = "") -> str:
    key = LicenseManager.generate_key(hwid=hwid, customer=customer, tier=tier, expiry_days=days)
    rec = add_record_to_vault(key, hwid, customer, tier, days, notes or "CLI Generation")
    exp_str = rec["expiry_date"].split(" ")[0] if rec["expiry_date"] != "LIFETIME" else "LIFETIME"

    print("\n" + "=" * 65)
    print("🔑 FB AUTO BOT - LICENSE KEY GENERATED & SAVED TO VAULT")
    print("=" * 65)
    print(f"Customer Name : {rec['customer']}")
    print(f"Target HWID   : {rec['hwid']}")
    print(f"License Tier  : {tier}")
    print(f"Duration      : {'Lifetime Access' if days == 0 else f'{days} Days'}")
    print(f"Expiry Date   : {rec['expiry_date']}")
    print(f"Vault Path    : {VAULT_FILE}")
    print("-" * 65)
    print("GENERATED ACTIVATION KEY (Send this to customer):")
    print(key)
    print("-" * 65)
    print("\n📱 WHATSAPP DELIVERY MESSAGE:\n")
    print(format_whatsapp_delivery_text(rec["customer"], rec["hwid"], key, tier, exp_str))
    print("=" * 65 + "\n")
    return key


def run_interactive_cli():
    print("=" * 65)
    print("  🔑 FB AUTO BOT - ADMIN LICENSE KEY GENERATOR (ADMIN TOOL)")
    print("=" * 65)
    name = input("Enter Customer Name [e.g. John Doe]: ").strip() or "Valued Customer"
    hwid = input("Enter Customer HWID [e.g. FBAUTO-A1B2-C3D4-E5F6]: ").strip()
    while not hwid:
        print("Hardware ID is required!")
        hwid = input("Enter Customer HWID: ").strip()

    print("\nSelect Validity Duration:")
    print(" [1] 30 Days Monthly")
    print(" [2] 365 Days (1 Year License)")
    print(" [3] Lifetime Unlimited Access")
    print(" [4] 7-Day Free Trial")
    print(" [5] Custom Days")
    choice = input("Choice (1-5) [default: 2]: ").strip() or "2"

    days = 365
    tier = "1 Year License"
    if choice == "1":
        days, tier = 30, "30-Day Monthly"
    elif choice == "3":
        days, tier = 0, "Lifetime Access"
    elif choice == "4":
        days, tier = 7, "7-Day Trial"
    elif choice == "5":
        try:
            days = int(input("Enter number of validity days (0 = Lifetime): ").strip() or "30")
            tier = "Lifetime Access" if days == 0 else f"{days}-Day Custom"
        except ValueError:
            days, tier = 365, "1 Year License"

    notes = input("Optional Order ID / WhatsApp Notes: ").strip()
    generate_cli(hwid=hwid, customer=name, tier=tier, days=days, notes=notes)


def run_gui():
    try:
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit, QMessageBox,
            QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QSpinBox
        )
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QCursor, QIcon
    except ImportError:
        print("PyQt5 not installed. Falling back to interactive CLI mode.")
        run_interactive_cli()
        return

    class AdminKeyGenApp(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("FB Auto Bot - Admin Key Generator & Licensing Suite")
            self.resize(900, 760)

            icon_path = _resolve_icon_path()
            if icon_path:
                self.setWindowIcon(QIcon(icon_path))

            self.setStyleSheet("""
                QMainWindow { background-color: #0b0f19; color: #f1f5f9; font-family: 'Segoe UI', sans-serif; }
                QLabel { color: #cbd5e1; font-size: 12px; font-weight: 500; }
                QLineEdit, QTextEdit, QSpinBox {
                    background-color: #111827;
                    border: 1px solid #374151;
                    border-radius: 8px;
                    padding: 8px 10px;
                    color: #ffffff;
                    font-family: Consolas, monospace;
                    font-size: 12px;
                }
                QLineEdit:focus, QTextEdit:focus, QSpinBox:focus { border: 1px solid #6366f1; }
                QComboBox {
                    background-color: #111827;
                    border: 1px solid #374151;
                    border-radius: 8px;
                    padding: 7px 10px;
                    color: #ffffff;
                    font-size: 12px;
                }
                QPushButton {
                    border-radius: 8px;
                    padding: 10px 16px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QTableWidget {
                    background-color: #111827;
                    border: 1px solid #1f2937;
                    border-radius: 8px;
                    color: #e2e8f0;
                    gridline-color: #1f2937;
                }
                QHeaderView::section {
                    background-color: #1e293b;
                    color: #94a3b8;
                    padding: 7px;
                    font-weight: bold;
                    border: none;
                }
            """)
            self.init_ui()

        def init_ui(self):
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setContentsMargins(22, 20, 22, 20)
            layout.setSpacing(12)

            hdr = QLabel("🔑 FB Auto Bot - Admin License Management Suite")
            hdr.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
            layout.addWidget(hdr)

            sub = QLabel(
                "Issue signed HWID-locked cryptographic keys for clients and generate ready-to-send WhatsApp activation messages."
            )
            sub.setStyleSheet("color: #94a3b8; font-size: 11px;")
            layout.addWidget(sub)

            # Form Group
            form_grp = QGroupBox("Generate New Customer Key")
            form_grp.setStyleSheet(
                "QGroupBox { color: #818cf8; font-weight: bold; border: 1px solid #1f2937; "
                "border-radius: 10px; margin-top: 8px; padding-top: 14px; }"
            )
            f_layout = QVBoxLayout(form_grp)
            f_layout.setSpacing(10)

            # Row 1: Name & HWID
            r1 = QHBoxLayout()
            v1 = QVBoxLayout()
            v1.addWidget(QLabel("Customer Name / Business Alias:"))
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

            # Row 2: Plan, Custom Days & Notes
            r2 = QHBoxLayout()
            v3 = QVBoxLayout()
            v3.addWidget(QLabel("License Duration / Plan:"))
            self.plan_combo = QComboBox()
            self.plan_combo.addItems([
                "1 Year License - 365 Days ($100)",
                "Monthly License - 30 Days ($10)",
                "Lifetime Unlimited Access",
                "7-Day Free Trial",
                "Custom Duration (Days)",
            ])
            self.plan_combo.currentIndexChanged.connect(self.on_plan_changed)
            v3.addWidget(self.plan_combo)
            r2.addLayout(v3, 2)

            v_days = QVBoxLayout()
            v_days.addWidget(QLabel("Validity Days (0 = Lifetime):"))
            self.days_spin = QSpinBox()
            self.days_spin.setRange(0, 36500)
            self.days_spin.setValue(365)
            self.days_spin.setEnabled(False)
            v_days.addWidget(self.days_spin)
            r2.addLayout(v_days, 1)

            v4 = QVBoxLayout()
            v4.addWidget(QLabel("Notes / WhatsApp Contact:"))
            self.notes_in = QLineEdit()
            self.notes_in.setPlaceholderText("Order #1042 / +1234567890")
            v4.addWidget(self.notes_in)
            r2.addLayout(v4, 2)
            f_layout.addLayout(r2)

            btn_row_top = QHBoxLayout()
            btn_gen = QPushButton("⚡ Generate Cryptographic License Key")
            btn_gen.setCursor(QCursor(Qt.PointingHandCursor))
            btn_gen.setStyleSheet("background-color: #4f46e5; color: #ffffff; font-size: 13px;")
            btn_gen.clicked.connect(self.on_generate)
            btn_row_top.addWidget(btn_gen, 3)

            btn_test_hwid = QPushButton("🖥️ Fill My PC HWID")
            btn_test_hwid.setCursor(QCursor(Qt.PointingHandCursor))
            btn_test_hwid.setStyleSheet("background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155;")
            btn_test_hwid.clicked.connect(lambda: self.hwid_in.setText(get_machine_hwid()))
            btn_row_top.addWidget(btn_test_hwid, 1)
            f_layout.addLayout(btn_row_top)

            layout.addWidget(form_grp)

            # Generated Key Output
            out_grp = QGroupBox("Generated License Key & Delivery Message")
            out_grp.setStyleSheet(
                "QGroupBox { color: #34d399; font-weight: bold; border: 1px solid #1f2937; "
                "border-radius: 10px; margin-top: 8px; padding-top: 14px; }"
            )
            o_layout = QVBoxLayout(out_grp)

            self.key_out = QLineEdit()
            self.key_out.setReadOnly(True)
            self.key_out.setPlaceholderText("Generated FB26-... activation key will appear here")
            self.key_out.setStyleSheet("color: #34d399; font-weight: bold; font-size: 13px; background-color: #070a12;")
            o_layout.addWidget(self.key_out)

            self.wa_out = QTextEdit()
            self.wa_out.setReadOnly(True)
            self.wa_out.setFixedHeight(105)
            o_layout.addWidget(self.wa_out)

            b_row = QHBoxLayout()
            btn_copy_key = QPushButton("📋 Copy License Key Only")
            btn_copy_key.setCursor(QCursor(Qt.PointingHandCursor))
            btn_copy_key.setStyleSheet("background-color: #374151; color: #ffffff;")
            btn_copy_key.clicked.connect(lambda: self.copy_to_clip(self.key_out.text(), "License key"))
            b_row.addWidget(btn_copy_key)

            btn_copy_wa = QPushButton("💬 Copy Full WhatsApp Delivery Message")
            btn_copy_wa.setCursor(QCursor(Qt.PointingHandCursor))
            btn_copy_wa.setStyleSheet("background-color: #059669; color: #ffffff;")
            btn_copy_wa.clicked.connect(lambda: self.copy_to_clip(self.wa_out.toPlainText(), "WhatsApp message"))
            b_row.addWidget(btn_copy_wa)

            o_layout.addLayout(b_row)
            layout.addWidget(out_grp)

            # Issued Keys Log Table
            tbl_hdr = QHBoxLayout()
            tbl_hdr.addWidget(QLabel(f"📜 Issued Licenses Log ({os.path.basename(VAULT_FILE)}):"))
            tbl_hdr.addStretch()
            btn_refresh = QPushButton("🔄 Refresh Log")
            btn_refresh.setCursor(QCursor(Qt.PointingHandCursor))
            btn_refresh.setStyleSheet("background-color: #1e293b; color: #cbd5e1; padding: 5px 12px; font-size: 11px;")
            btn_refresh.clicked.connect(self.load_database_table)
            tbl_hdr.addWidget(btn_refresh)
            layout.addLayout(tbl_hdr)

            self.table = QTableWidget()
            self.table.setColumnCount(6)
            self.table.setHorizontalHeaderLabels(["Customer", "HWID", "Plan", "Expiry Date", "Issued At", "Key"])
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.table.setMinimumHeight(150)
            layout.addWidget(self.table)
            self.load_database_table()

        def on_plan_changed(self, idx: int):
            if idx == 0:
                self.days_spin.setValue(365)
                self.days_spin.setEnabled(False)
            elif idx == 1:
                self.days_spin.setValue(30)
                self.days_spin.setEnabled(False)
            elif idx == 2:
                self.days_spin.setValue(0)
                self.days_spin.setEnabled(False)
            elif idx == 3:
                self.days_spin.setValue(7)
                self.days_spin.setEnabled(False)
            else:
                self.days_spin.setEnabled(True)

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
            elif plan_idx == 3:
                days, tier = 7, "7-Day Trial"
            else:
                days = int(self.days_spin.value())
                tier = "Lifetime Access" if days == 0 else f"{days}-Day Custom"

            notes = self.notes_in.text().strip()
            key = LicenseManager.generate_key(hwid=hwid, customer=name, tier=tier, expiry_days=days)
            rec = add_record_to_vault(key, hwid, name, tier, days, notes or "GUI Generated")
            exp_str = rec["expiry_date"].split(" ")[0] if rec["expiry_date"] != "LIFETIME" else "LIFETIME"

            self.key_out.setText(key)
            self.wa_out.setPlainText(format_whatsapp_delivery_text(name, hwid.upper(), key, tier, exp_str))
            self.load_database_table()
            QMessageBox.information(
                self,
                "Key Ready & Saved",
                f"✅ License key generated and saved!\n\n"
                f"Customer: {name}\n"
                f"HWID: {hwid.upper()}\n"
                f"Plan: {tier} ({exp_str})\n"
                f"Vault: {VAULT_FILE}",
            )

        def copy_to_clip(self, text: str, label: str):
            if not text.strip():
                QMessageBox.warning(self, "Nothing to Copy", "Generate a license key first.")
                return
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "Copied", f"{label} copied to clipboard!")

        def load_database_table(self):
            records = load_vault()
            self.table.setRowCount(len(records))
            for row, item in enumerate(records):
                self.table.setItem(row, 0, QTableWidgetItem(str(item.get("customer", ""))))
                self.table.setItem(row, 1, QTableWidgetItem(str(item.get("hwid", ""))))
                self.table.setItem(row, 2, QTableWidgetItem(str(item.get("tier", ""))))
                self.table.setItem(row, 3, QTableWidgetItem(str(item.get("expiry_date", ""))))
                self.table.setItem(row, 4, QTableWidgetItem(str(item.get("created_date", ""))))
                self.table.setItem(row, 5, QTableWidgetItem(str(item.get("key", ""))))

    app = QApplication(sys.argv)
    win = AdminKeyGenApp()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FB Auto Bot - Admin License Key Generator")
    parser.add_argument("--hwid", help="Customer Hardware ID (HWID)")
    parser.add_argument("--customer", default="Valued Customer", help="Customer Name")
    parser.add_argument("--tier", default="Lifetime Access", help="License Tier")
    parser.add_argument("--days", type=int, default=0, help="Days until expiry (0 = lifetime)")
    parser.add_argument("--notes", default="", help="Optional order/contact notes")
    parser.add_argument("--cli", action="store_true", help="Run interactive terminal mode")

    args = parser.parse_args()

    if args.hwid:
        generate_cli(hwid=args.hwid, customer=args.customer, tier=args.tier, days=args.days, notes=args.notes)
    elif args.cli:
        run_interactive_cli()
    else:
        run_gui()
