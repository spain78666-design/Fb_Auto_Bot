#!/usr/bin/env python3
"""
FB Auto Bot - Marketplace Listings History & Statistics Tracker
Tracks every marketplace listing published across all accounts with persistent JSON storage.
Supports filtering by account and time periods (e.g. Today, Last 7 Days, Last 10 Days, Last 15 Days, Last 30 Days, All Time).
"""

import os
import sys
import json
import time
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger("FBAutoBot.ListingsTracker")

def get_base_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

class ListingsTracker:
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.storage_path = storage_path
        else:
            config_dir = os.path.join(get_base_dir(), "config")
            os.makedirs(config_dir, exist_ok=True)
            self.storage_path = os.path.join(config_dir, "listings_history.json")
        self._listings: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        """Loads persisted listings from JSON file."""
        if not os.path.isfile(self.storage_path):
            self._listings = []
            self._save()
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._listings = data
                elif isinstance(data, dict):
                    self._listings = data.get("listings", [])
                else:
                    self._listings = []
        except Exception as e:
            logger.warning(f"Failed to load listings history from {self.storage_path}: {e}")
            self._listings = []

    def _save(self):
        """Atomically saves listings to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            tmp_path = self.storage_path + f".tmp.{os.getpid()}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump({"listings": self._listings}, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.storage_path)
        except Exception as e:
            logger.error(f"Error saving listings history to {self.storage_path}: {e}")

    def record_listing(
        self,
        account_name: str,
        account_id: str = "",
        title: str = "Marketplace Item",
        listing_type: str = "Item for sale",
        category: str = "General",
        price: str = "0",
        location: str = "",
        mode: str = "Standard",
        count: int = 1,
        details: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """
        Records 1 or more completed marketplace listings.
        Returns the new total count of recorded listings.
        """
        now = datetime.now()
        now_iso = now.isoformat()
        now_date = now.strftime("%Y-%m-%d")
        now_time = now.strftime("%H:%M:%S")
        now_epoch = time.time()

        clean_acc_name = (account_name or account_id or "Facebook Account").strip()
        clean_acc_id = (account_id or clean_acc_name).strip()

        records_to_add = []

        if details and isinstance(details, list) and len(details) > 0:
            for item in details:
                records_to_add.append({
                    "id": f"lst_{uuid.uuid4().hex[:10]}",
                    "timestamp": now_iso,
                    "date": now_date,
                    "time": now_time,
                    "epoch": now_epoch,
                    "account_name": clean_acc_name,
                    "account_id": clean_acc_id,
                    "title": item.get("title", title),
                    "listing_type": item.get("listing_type", listing_type),
                    "category": item.get("category", category),
                    "price": str(item.get("price", price)),
                    "location": item.get("location", location),
                    "mode": mode,
                    "status": "Published"
                })
        else:
            num = max(1, count)
            for i in range(num):
                records_to_add.append({
                    "id": f"lst_{uuid.uuid4().hex[:10]}",
                    "timestamp": now_iso,
                    "date": now_date,
                    "time": now_time,
                    "epoch": now_epoch,
                    "account_name": clean_acc_name,
                    "account_id": clean_acc_id,
                    "title": title if num == 1 else f"{title} (Post #{i+1})",
                    "listing_type": listing_type,
                    "category": category,
                    "price": str(price),
                    "location": location,
                    "mode": mode,
                    "status": "Published"
                })

        self._listings.extend(records_to_add)
        self._save()
        return len(self._listings)

    def get_all_listings(self) -> List[Dict[str, Any]]:
        self._load()
        return list(self._listings)

    def get_stats(self, account_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates listing counts filtered by account and across time periods:
        - Total All-Time
        - Today
        - Last 7 Days
        - Last 10 Days
        - Last 15 Days
        - Last 30 Days
        - Per-Account breakdown
        """
        self._load()
        now_epoch = time.time()
        
        target_acc = account_name.strip() if account_name else ""
        if target_acc in ("All Accounts", "All Profiles", "All Users", "Total", ""):
            target_acc = None

        total = 0
        today_cnt = 0
        last_7_days = 0
        last_10_days = 0
        last_15_days = 0
        last_30_days = 0
        per_account: Dict[str, int] = {}
        filtered_listings: List[Dict[str, Any]] = []

        today_str = datetime.now().strftime("%Y-%m-%d")

        for item in self._listings:
            acc = item.get("account_name") or item.get("account_id") or "Unknown"
            per_account[acc] = per_account.get(acc, 0) + 1

            if target_acc and acc != target_acc and item.get("account_id") != target_acc:
                continue

            filtered_listings.append(item)
            total += 1

            item_epoch = item.get("epoch")
            if not item_epoch:
                try:
                    dt = datetime.fromisoformat(item.get("timestamp", ""))
                    item_epoch = dt.timestamp()
                except Exception:
                    item_epoch = now_epoch

            diff_sec = max(0, now_epoch - item_epoch)
            diff_days = diff_sec / 86400.0

            if item.get("date") == today_str or diff_days <= 1.0:
                today_cnt += 1
            if diff_days <= 7.0:
                last_7_days += 1
            if diff_days <= 10.0:
                last_10_days += 1
            if diff_days <= 15.0:
                last_15_days += 1
            if diff_days <= 30.0:
                last_30_days += 1

        return {
            "account_filter": target_acc or "All Accounts",
            "total": total,
            "today": today_cnt,
            "last_7_days": last_7_days,
            "last_10_days": last_10_days,
            "last_15_days": last_15_days,
            "last_30_days": last_30_days,
            "per_account": per_account,
            "listings": filtered_listings
        }

    def clear_history(self):
        """Clears all listings history."""
        self._listings = []
        self._save()

# Global Singleton Accessor
_GLOBAL_TRACKER: Optional[ListingsTracker] = None

def get_listings_tracker() -> ListingsTracker:
    global _GLOBAL_TRACKER
    if _GLOBAL_TRACKER is None:
        _GLOBAL_TRACKER = ListingsTracker()
    return _GLOBAL_TRACKER
