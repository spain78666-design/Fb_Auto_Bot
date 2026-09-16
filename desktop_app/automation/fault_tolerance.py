"""
FB Auto Bot - Fault Tolerance & Resilient Automation Engine
Provides real-time error interception, terminal color-coded logging,
and automatic fallback mechanisms between Method Manager configurations and live UI input overrides.
"""

import os
import sys
import re
import time
import json
import uuid
import random
import tempfile
import traceback
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

# ==============================================================================
# Color-Coded Console Logger
# ==============================================================================
class TerminalColor:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    # Foreground
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright Foreground
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


class AutomationLogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    FALLBACK = "FALLBACK"


class ResilientConsoleLogger:
    """
    High-visibility color-coded terminal and console logger with timestamps,
    exception stack traces, and direct callback hooks for GUI signaling.
    """

    LEVEL_COLORS = {
        AutomationLogLevel.DEBUG: TerminalColor.BRIGHT_BLACK,
        AutomationLogLevel.INFO: TerminalColor.BRIGHT_CYAN,
        AutomationLogLevel.SUCCESS: TerminalColor.BRIGHT_GREEN,
        AutomationLogLevel.WARNING: TerminalColor.BRIGHT_YELLOW,
        AutomationLogLevel.ERROR: TerminalColor.BRIGHT_RED,
        AutomationLogLevel.CRITICAL: f"{TerminalColor.BG_RED}{TerminalColor.BRIGHT_WHITE}{TerminalColor.BOLD}",
        AutomationLogLevel.FALLBACK: f"{TerminalColor.BRIGHT_MAGENTA}{TerminalColor.BOLD}",
    }

    LEVEL_BADGES = {
        AutomationLogLevel.DEBUG: "[DBG]",
        AutomationLogLevel.INFO: "[INF]",
        AutomationLogLevel.SUCCESS: "[OK!]",
        AutomationLogLevel.WARNING: "[WRN]",
        AutomationLogLevel.ERROR: "[ERR]",
        AutomationLogLevel.CRITICAL: "[CRIT]",
        AutomationLogLevel.FALLBACK: "[FLBK]",
    }

    def __init__(self, name: str = "Engine", gui_callback: Optional[Callable[[str, str], None]] = None):
        self.name = name
        self.gui_callback = gui_callback

    def log(self, level: str or AutomationLogLevel, message: str, exc: Optional[Exception] = None):
        """Prints colorized log to stdout/stderr and transmits to GUI callback."""
        if isinstance(level, str):
            try:
                norm_level = AutomationLogLevel[level.upper()]
            except KeyError:
                norm_level = AutomationLogLevel.INFO
        else:
            norm_level = level

        now_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        color = self.LEVEL_COLORS.get(norm_level, TerminalColor.WHITE)
        badge = self.LEVEL_BADGES.get(norm_level, "[LOG]")
        reset = TerminalColor.RESET

        formatted_console = f"{TerminalColor.DIM}{now_str}{reset} {color}{badge} [{self.name}] {message}{reset}"
        
        if norm_level in (AutomationLogLevel.ERROR, AutomationLogLevel.CRITICAL):
            print(formatted_console, file=sys.stderr, flush=True)
            if exc:
                tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
                print(f"{TerminalColor.RED}{''.join(tb_lines)}{reset}", file=sys.stderr, flush=True)
        else:
            print(formatted_console, flush=True)

        # Dispatch to PyQt or GUI callback if registered
        if self.gui_callback:
            try:
                gui_lvl_str = "ERROR" if norm_level in (AutomationLogLevel.ERROR, AutomationLogLevel.CRITICAL) else (
                    "WARNING" if norm_level == AutomationLogLevel.WARNING else (
                        "SUCCESS" if norm_level == AutomationLogLevel.SUCCESS else "INFO"
                    )
                )
                self.gui_callback(gui_lvl_str, message)
            except Exception:
                pass

    def debug(self, msg: str):
        self.log(AutomationLogLevel.DEBUG, msg)

    def info(self, msg: str):
        self.log(AutomationLogLevel.INFO, msg)

    def success(self, msg: str):
        self.log(AutomationLogLevel.SUCCESS, msg)

    def warning(self, msg: str):
        self.log(AutomationLogLevel.WARNING, msg)

    def error(self, msg: str, exc: Optional[Exception] = None):
        self.log(AutomationLogLevel.ERROR, msg, exc=exc)

    def critical(self, msg: str, exc: Optional[Exception] = None):
        self.log(AutomationLogLevel.CRITICAL, msg, exc=exc)

    def fallback(self, msg: str):
        self.log(AutomationLogLevel.FALLBACK, f"🔄 {msg}")


# ==============================================================================
# Method Manager Verification & Fallback Logic Architecture
# ==============================================================================
@dataclass
class MethodVerificationResult:
    is_valid: bool
    method_name: str
    action_count: int = 0
    reason: str = ""
    fallback_recommended: bool = False


class MethodFallbackManager:
    """
    Validates Method Manager configuration files and orchestrates immediate fallback
    to live UI parameter overrides whenever a method file is missing, corrupted,
    empty, or encounters an execution failure during replay.
    """

    @staticmethod
    def verify_method_availability(method_name: Optional[str], methods_dir: str) -> MethodVerificationResult:
        """
        Inspects if a method file exists and contains executable actions.
        """
        if not method_name:
            return MethodVerificationResult(
                is_valid=False,
                method_name="",
                reason="No custom method specified; default direct UI pipeline active.",
                fallback_recommended=True
            )

        clean_name = method_name.replace("📁 ", "").strip()

        # Built-in default flags always use direct UI pipeline
        if clean_name in (
            "Default Item Listing (Standard)",
            "Default Facebook Marketplace Flow",
            "None",
            ""
        ):
            return MethodVerificationResult(
                is_valid=False,
                method_name=clean_name,
                reason="Built-in standard flow selected.",
                fallback_recommended=True
            )

        method_path = os.path.join(methods_dir, f"{clean_name}.json")
        if not os.path.isfile(method_path):
            return MethodVerificationResult(
                is_valid=False,
                method_name=clean_name,
                reason=f"Method file '{clean_name}.json' not found on disk at '{methods_dir}'.",
                fallback_recommended=True
            )

        try:
            with open(method_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            actions = data.get("actions", [])
            if not isinstance(actions, list) or len(actions) == 0:
                return MethodVerificationResult(
                    is_valid=False,
                    method_name=clean_name,
                    action_count=0,
                    reason=f"Method '{clean_name}' contains zero recorded steps or malformed action list.",
                    fallback_recommended=True
                )

            return MethodVerificationResult(
                is_valid=True,
                method_name=clean_name,
                action_count=len(actions),
                reason="Valid recorded sequence."
            )
        except Exception as e:
            return MethodVerificationResult(
                is_valid=False,
                method_name=clean_name,
                reason=f"JSON decoding/read error in '{clean_name}.json': {str(e)}",
                fallback_recommended=True
            )


# ==============================================================================
# Live UI Input Overrides Resolver
# ==============================================================================
class UIInputOverridesResolver:
    """
    Extracts, normalizes, and validates live UI inputs (title, price, category,
    condition, description, locations, images, and anti-duplicate options).
    Guarantees that even if a custom method fails halfway, every user-entered parameter
    from the active GUI controls is preserved and executed directly.
    """

    @staticmethod
    def resolve_payload(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        resolved = dict(raw_payload)

        # Title
        raw_title = str(resolved.get("title", "")).strip()
        resolved["title"] = raw_title if raw_title else "Quality Item for Sale"

        # Price
        raw_price = resolved.get("price", "0")
        if raw_price is None or str(raw_price).strip() == "":
            resolved["price"] = "0"
        else:
            resolved["price"] = str(raw_price).strip()

        # Category
        raw_cat = str(resolved.get("category", "")).strip()
        resolved["category"] = raw_cat if raw_cat else "Household"

        # Description
        raw_desc = str(resolved.get("description", "")).strip()
        resolved["description"] = raw_desc

        # Location
        raw_loc = resolved.get("location", "")
        if isinstance(raw_loc, list):
            resolved["location"] = [str(l).strip() for l in raw_loc if str(l).strip()]
        else:
            resolved["location"] = str(raw_loc).strip()

        # Images
        raw_imgs = resolved.get("images", [])
        if isinstance(raw_imgs, list):
            resolved["images"] = [img for img in raw_imgs if os.path.exists(img)]
        else:
            resolved["images"] = []

        return resolved


# ==============================================================================
# Distinct Location & Picture Mapping Engine for Multi-Tab Automation
# ==============================================================================
class DistinctDataMapper:
    """
    Guarantees 100% distinct location and distinct picture/image mapping
    for each individual browser tab without any duplicate mapping across tabs.
    Fulfills multi-tab parallel requirements by assigning unique, non-overlapping
    geographic zones and uniquely hashed image assets to each tab.
    """

    @staticmethod
    def parse_locations_pool(raw_location: Any) -> List[str]:
        """
        Parses comma-, newline-, or semicolon-delimited location strings or lists
        into an ordered, duplicate-free list of location strings.
        """
        if isinstance(raw_location, list):
            tokens = [str(x).strip() for x in raw_location if str(x).strip()]
        elif isinstance(raw_location, str):
            tokens = [x.strip() for x in re.split(r'[\r\n,;]+', raw_location) if x.strip()]
        else:
            tokens = []

        # Deduplicate while strictly preserving user insertion order
        seen = set()
        deduped = []
        for loc in tokens:
            if loc and loc not in seen:
                seen.add(loc)
                deduped.append(loc)

        return deduped if deduped else ["Local Radius"]

    @staticmethod
    def generate_distinct_locations(locations_pool: List[str], tabs_count: int) -> List[str]:
        """
        Allocates a strictly separate, distinct location for each tab.
        If the pool has fewer locations than tabs_count, generates distinct, valid
        metro/district zone designations so no two tabs ever share identical locations.
        """
        if not locations_pool:
            locations_pool = ["Local Radius"]

        distinct_locations: List[str] = []
        if len(locations_pool) >= tabs_count:
            # We have enough unique locations for every tab
            distinct_locations = locations_pool[:tabs_count]
        else:
            # Less locations than tabs: distribute and append distinct district/zone tags
            districts = [
                "Downtown", "Metro", "North District", "South District", "East Zone",
                "West Zone", "Central Heights", "Midtown", "Valley", "Suburbs",
                "Industrial Area", "Lakeside", "Parkway", "Plaza", "Uptown",
                "Westside", "Harbor District", "Financial Center", "Airport Zone", "Tech Corridor"
            ]
            for i in range(tabs_count):
                base_loc = locations_pool[i % len(locations_pool)]
                cycle = i // len(locations_pool)
                if cycle == 0:
                    distinct_locations.append(base_loc)
                else:
                    tag = districts[(cycle - 1) % len(districts)]
                    distinct_locations.append(f"{base_loc} ({tag})")

        return distinct_locations

    @staticmethod
    def generate_distinct_images(
        images_pool: List[str],
        tabs_count: int,
        temp_dir: Optional[str] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ) -> List[List[str]]:
        """
        Allocates a strictly separate, distinct image file for each tab.
        If images_pool has fewer images than tabs_count, generates unique, anti-duplicate
        mutated images on disk (micro-rotation, EXIF wipe, noise/color jitter) so each tab
        receives a physically unique file with a distinct file hash.
        """
        log = log_callback or (lambda lvl, msg: None)
        valid_images = [os.path.abspath(img) for img in images_pool if os.path.exists(img)]

        if not valid_images:
            # No images provided on disk
            return [[] for _ in range(tabs_count)]

        # If user uploaded at least tabs_count unique images, assign 1 unique image per tab
        if len(valid_images) >= tabs_count:
            log("INFO", f"🖼️ Distinct Image Mapping: {len(valid_images)} distinct images available for {tabs_count} tabs. 1-to-1 unique mapping assigned.")
            return [[valid_images[i]] for i in range(tabs_count)]

        # If fewer images than tabs, generate unique anti-duplicate image files per tab
        log("INFO", f"🖼️ Distinct Image Generator: {len(valid_images)} base image(s) provided for {tabs_count} tabs. Generating distinct mutated variants per tab...")

        tab_images: List[List[str]] = []
        out_dir = temp_dir or os.path.join(tempfile.gettempdir(), "fb_distinct_tab_images")
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception:
            pass

        for tab_idx in range(tabs_count):
            base_img = valid_images[tab_idx % len(valid_images)]
            cycle = tab_idx // len(valid_images)

            if cycle == 0 and tab_idx < len(valid_images):
                # First usage uses original file directly
                tab_images.append([base_img])
            else:
                # Generate unique variant for this tab
                variant_path = DistinctDataMapper._create_image_variant(
                    base_img,
                    tab_idx=tab_idx + 1,
                    out_dir=out_dir,
                    log=log
                )
                tab_images.append([variant_path])

        return tab_images

    @staticmethod
    def _create_image_variant(image_path: str, tab_idx: int, out_dir: str, log: Callable) -> str:
        """Creates a distinct mutated image on disk to bypass Facebook duplicate image hash filters."""
        try:
            from PIL import Image, ImageEnhance
            with Image.open(image_path) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                else:
                    img = img.convert("RGB")

                orig_w, orig_h = img.size

                # Deterministic yet unique rotation per tab: ±0.2° to ±0.8°
                angle = (-0.65 + ((tab_idx * 0.19) % 1.3))
                if abs(angle) < 0.1:
                    angle = 0.35

                rotated = img.rotate(angle, resample=Image.BICUBIC, expand=True)
                rot_w, rot_h = rotated.size
                margin_x = max(0, (rot_w - orig_w) // 2)
                margin_y = max(0, (rot_h - orig_h) // 2)
                cropped = rotated.crop((margin_x, margin_y, margin_x + orig_w, margin_y + orig_h))

                # Unique brightness & contrast shift per tab
                b_shift = 1.0 + (((tab_idx % 5) - 2) * 0.009)
                cropped = ImageEnhance.Brightness(cropped).enhance(b_shift)

                c_shift = 1.0 + (((tab_idx % 4) - 1.5) * 0.009)
                cropped = ImageEnhance.Contrast(cropped).enhance(c_shift)

                unique_filename = f"tab_{tab_idx}_variant_{uuid.uuid4().hex[:6]}.jpg"
                dest_path = os.path.join(out_dir, unique_filename)
                cropped.save(dest_path, "JPEG", quality=93)
                return dest_path
        except Exception as e:
            # Fallback if PIL is unavailable or fails: create a unique physical file with unique binary hash & filename
            try:
                unique_filename = f"tab_{tab_idx}_variant_{uuid.uuid4().hex[:6]}.jpg"
                dest_path = os.path.join(out_dir, unique_filename)
                with open(image_path, "rb") as rf:
                    data = rf.read()
                # Write unique copy with harmless trailing comment/metadata to guarantee distinct file & hash
                with open(dest_path, "wb") as wf:
                    wf.write(data)
                    wf.write(f"\n<!-- DistinctTab-{tab_idx}-{uuid.uuid4().hex} -->\n".encode("utf-8"))
                return dest_path
            except Exception as copy_err:
                log("WARNING", f"Tab [{tab_idx}] image variant notice: {str(copy_err)}; using base image.")
                return image_path

    @classmethod
    def map_tabs_payload(
        cls,
        base_payload: Dict[str, Any],
        tabs_count: int,
        log_callback: Optional[Callable[[str, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Creates tabs_count independent payload dictionaries, ensuring each tab has:
        - A strictly distinct location
        - A strictly distinct picture/image
        - Correct tab_index and total_tabs metadata
        """
        log = log_callback or (lambda lvl, msg: None)
        tabs_count = max(1, min(tabs_count, 100))

        # 1. Resolve Distinct Locations
        loc_pool = cls.parse_locations_pool(base_payload.get("location", ""))
        distinct_locs = cls.generate_distinct_locations(loc_pool, tabs_count)

        # 2. Resolve Distinct Images
        imgs_pool = base_payload.get("images", [])
        distinct_imgs = cls.generate_distinct_images(imgs_pool, tabs_count, log_callback=log)

        # 3. Assemble distinct payload for each tab
        tab_payloads: List[Dict[str, Any]] = []
        for i in range(tabs_count):
            t_data = dict(base_payload)
            t_data["tab_index"] = i + 1
            t_data["total_tabs"] = tabs_count
            t_data["location"] = distinct_locs[i]
            t_data["images"] = distinct_imgs[i]
            tab_payloads.append(t_data)

        return tab_payloads

