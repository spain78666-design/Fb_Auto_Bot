#!/usr/bin/env python3
"""
FB Auto Bot - Global Browser Window Tiling, Human Motion, & Custom Chrome Profile Scanner

Provides:
1. Global tiled grid arrangement + dynamic zoom-out across ALL Chrome launches:
   - 1 browser  -> 1x1 full screen work area (zoom 0.85)
   - 2 browsers -> 2x1 side-by-side (zoom 0.72)
   - 3 browsers -> 3x1 Left | Center | Right (zoom 0.62)
   - 4 browsers -> 2x2 grid (zoom 0.55)
   - 5-6 browsers -> 3x2 grid (zoom 0.55)
   - 7+ browsers -> ceil(sqrt(N)) grid (zoom 0.50)
   - Plus CDP Browser.setWindowBounds enforcement so Chrome never overrides tile geometry.
2. Async BrowserSlotPool for clean concurrent slot allocation & automatic reuse as browsers close.
   Also serializes same-user_data_dir concurrent launches (e.g. multiple profiles in one User Data folder).
3. Human-like curved mouse movement, smooth incremental scrolling, and jittered typing.
4. Multi-format Custom Chrome Profile Folder Scanner (pages 5-9):
   - Format 1: Subfolders each acting as a standalone Chrome user-data-dir
   - Format 2: Single Chrome User Data folder with Default, Profile 1, Profile 2, ...
   - Format 3: Windows .lnk shortcuts with --user-data-dir / --profile-directory (pure-Python binary parser)
5. Persistence of per-page Chrome paths in config/custom_chrome_paths.json.
"""

import os
import re
import sys
import json
import math
import shlex
import struct
import random
import hashlib
import asyncio
import logging
import subprocess
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("FBAutoBot.BrowserWindowManager")

CHROME_PATH_PAGES = ("groups", "pages", "reels", "friends", "propic", "renew_delete")

_DEFAULT_WORK_AREA: Optional[Tuple[int, int, int, int]] = None


def set_screen_work_area(screen_rect: Optional[Tuple[int, int, int, int]]) -> None:
    """Optionally caches Qt primary screen logical work area (in DIPs) from main UI thread."""
    global _DEFAULT_WORK_AREA
    if screen_rect and len(screen_rect) == 4:
        sx, sy, sw, sh = (int(v) for v in screen_rect)
        if sw >= 640 and sh >= 480:
            _DEFAULT_WORK_AREA = (sx, sy, sw, sh)


def get_base_dir() -> str:
    """Returns application base directory handling PyInstaller bundle and script modes."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# ==============================================================================
# 1. Screen Work Area & Dynamic Grid Tiling
# ==============================================================================

def get_screen_work_area(screen_rect: Optional[Tuple[int, int, int, int]] = None) -> Tuple[int, int, int, int]:
    """
    Returns taskbar-safe desktop work area as (x, y, width, height) in Chrome DIPs.
    Handles Windows display scaling (100%/125%/150%/etc.) so Chrome --window-position,
    --window-size, and CDP Browser.setWindowBounds never overflow or stack.
    """
    if screen_rect and len(screen_rect) == 4:
        sx, sy, sw, sh = (int(v) for v in screen_rect)
        return sx, sy, max(640, sw), max(480, sh)

    if _DEFAULT_WORK_AREA is not None:
        return _DEFAULT_WORK_AREA

    if os.name == "nt":
        try:
            import ctypes
            import ctypes.wintypes as wintypes

            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", wintypes.LONG),
                    ("top", wintypes.LONG),
                    ("right", wintypes.LONG),
                    ("bottom", wintypes.LONG),
                ]

            rect = RECT()
            SPI_GETWORKAREA = 0x0030
            if ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
                left = int(rect.left)
                top = int(rect.top)
                w = max(640, int(rect.right - rect.left))
                h = max(480, int(rect.bottom - rect.top))

                # Convert physical pixels to DIPs ONLY when our process is DPI-aware
                scale = 1.0
                try:
                    if hasattr(ctypes.windll.user32, "GetDpiForSystem"):
                        sys_dpi = int(ctypes.windll.user32.GetDpiForSystem() or 96)
                        if sys_dpi > 96:
                            scale = sys_dpi / 96.0
                    else:
                        hdc = ctypes.windll.user32.GetDC(0)
                        if hdc:
                            dpi_x = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
                            ctypes.windll.user32.ReleaseDC(0, hdc)
                            if dpi_x and dpi_x > 96:
                                scale = dpi_x / 96.0
                except Exception:
                    scale = 1.0

                if scale > 1.01:
                    left = int(round(left / scale))
                    top = int(round(top / scale))
                    w = max(640, int(round(w / scale)))
                    h = max(480, int(round(h / scale)))
                return left, top, w, h
        except Exception as e:
            logger.debug(f"Work area lookup fallback: {e}")

    return 0, 0, 1920, 1080


def compute_grid_dimensions(total_slots: int) -> Tuple[int, int]:
    """
    Computes (cols, rows) matching exact user specification:
      1 -> 1x1
      2 -> 2x1
      3 -> 3x1
      4 -> 2x2
      5-6 -> 3x2
      7+ -> ceil(sqrt(N)) cols x ceil(N / cols) rows
    """
    n = max(1, int(total_slots or 1))
    if n == 1:
        return 1, 1
    if n == 2:
        return 2, 1
    if n == 3:
        return 3, 1
    if n == 4:
        return 2, 2
    if n <= 6:
        return 3, 2
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    return cols, rows


def get_zoom_factor(total_slots: int) -> float:
    """Returns calibrated Chrome UI/page zoom scale so full forms stay visible inside small tiles."""
    n = max(1, int(total_slots or 1))
    if n <= 1:
        return 0.85
    if n == 2:
        return 0.72
    if n == 3:
        return 0.62
    if n <= 6:
        return 0.55
    return 0.50


def compute_tile_rect(
    slot_index: int,
    total_slots: int,
    work_area: Optional[Tuple[int, int, int, int]] = None,
) -> Tuple[int, int, int, int]:
    """
    Computes geometry (x, y, width, height) in DIPs for slot_index within total_slots grid:
      - 1 -> 1x1 full screen
      - 2 -> 2x1 Left | Right
      - 3 -> 3x1 Left | Center | Right
      - 4 -> 2x2 Grid (2 top, 2 bottom)
      - 5-6 -> 3x2 Grid (3 top, 3 bottom)
      - 7+ -> ceil(sqrt(N)) grid
    Ensures every window remains clearly visible across the screen even on narrower laptops
    where Chrome enforces a ~500px minimum outer window width.
    """
    sx, sy, sw, sh = get_screen_work_area(work_area)
    n = max(1, int(total_slots or 1))
    cols, rows = compute_grid_dimensions(n)
    slot = max(0, int(slot_index or 0)) % n
    col = slot % cols
    row = slot // cols

    col_edges = [sx + round(sw * i / cols) for i in range(cols + 1)]
    row_edges = [sy + round(sh * j / rows) for j in range(rows + 1)]

    w = max(320, col_edges[col + 1] - col_edges[col])
    h = max(300, row_edges[row + 1] - row_edges[row])

    # Desktop Chrome on Windows enforces ~500px min outer width; if a narrow/scaled display
    # makes sw/cols < 500px, step x across [sx, sx + sw - min(500, sw)] so windows stay spread
    # Left | Center | Right instead of clipping off the right edge.
    chrome_min_w = 500
    if cols > 1 and w < chrome_min_w and sw >= chrome_min_w:
        w = chrome_min_w
        span_x = max(0, sw - w)
        x = sx + round(span_x * col / (cols - 1))
    else:
        x = col_edges[col]

    y = row_edges[row]
    return int(x), int(y), int(w), int(h)


def resolve_tile_context(
    account_data: Optional[Dict[str, Any]] = None,
    window_slot: Optional[int] = None,
    total_window_slots: Optional[int] = None,
    tile_rect: Optional[Tuple[int, int, int, int]] = None,
) -> Tuple[int, int, Tuple[int, int, int, int]]:
    """Resolves (slot_index, total_slots, tile_rect) from explicit args or account_data."""
    acc = account_data or {}
    total = int(
        total_window_slots
        if total_window_slots is not None
        else acc.get("total_window_slots", 1) or 1
    )
    total = max(1, total)
    slot = int(
        window_slot
        if window_slot is not None
        else acc.get("window_slot", 0) or 0
    )
    rect = tile_rect or acc.get("tile_rect")
    if rect and len(rect) == 4:
        resolved_rect = (int(rect[0]), int(rect[1]), max(320, int(rect[2])), max(300, int(rect[3])))
    else:
        resolved_rect = compute_tile_rect(slot, total)
    return slot, total, resolved_rect


def build_window_chrome_args(
    tile_rect: Optional[Tuple[int, int, int, int]] = None,
    total_slots: int = 1,
    slot_index: int = 0,
    profile_directory: Optional[str] = None,
    apply_scale_factor: bool = False,
) -> List[str]:
    """
    Returns Chrome launch flags for tiled window positioning, sizing,
    and optional --profile-directory. Never emits --start-maximized or
    --force-device-scale-factor (which corrupts Windows tile coordinates).
    """
    rect = tile_rect or compute_tile_rect(slot_index, total_slots)
    x, y, w, h = (int(rect[0]), int(rect[1]), max(320, int(rect[2])), max(300, int(rect[3])))
    args = [
        f"--window-position={x},{y}",
        f"--window-size={w},{h}",
    ]
    if profile_directory:
        args.append(f"--profile-directory={profile_directory}")
    return args


def strip_maximized_args(args: List[str]) -> List[str]:
    """Removes --start-maximized / --start-fullscreen so tiled geometry always takes effect."""
    return [
        a for a in args
        if a not in ("--start-maximized", "--start-fullscreen")
        and not str(a).startswith("--force-device-scale-factor")
    ]


def prepare_profile_tile_placement(
    user_data_dir: Optional[str],
    tile_rect: Optional[Tuple[int, int, int, int]],
    profile_subdir: Optional[str] = None,
    work_area: Optional[Tuple[int, int, int, int]] = None,
) -> None:
    """
    Pre-writes Chrome Preferences `browser.window_placement` to exact tile coordinates with
    `maximized: False` before launching a persistent profile so Chrome never restores an
    old maximized or stacked window placement over other slots.
    """
    if not user_data_dir or not os.path.isdir(user_data_dir) or not tile_rect:
        return
    try:
        if _is_chrome_profile_locked(user_data_dir):
            return
    except Exception:
        pass
    try:
        x, y, w, h = (int(tile_rect[0]), int(tile_rect[1]), max(320, int(tile_rect[2])), max(300, int(tile_rect[3])))
        sx, sy, sw, sh = get_screen_work_area(work_area)
        prof_name = (profile_subdir or "").strip() or "Default"
        candidates = [os.path.join(user_data_dir, prof_name, "Preferences")]
        if prof_name == "Default":
            candidates.append(os.path.join(user_data_dir, "Preferences"))

        for pref_path in candidates:
            if not os.path.isfile(pref_path):
                continue
            try:
                with open(pref_path, "r", encoding="utf-8", errors="ignore") as f:
                    prefs = json.load(f)
                if not isinstance(prefs, dict):
                    continue
                browser_cfg = prefs.setdefault("browser", {})
                if isinstance(browser_cfg, dict):
                    browser_cfg["window_placement"] = {
                        "bottom": y + h,
                        "left": x,
                        "maximized": False,
                        "right": x + w,
                        "top": y,
                        "work_area_bottom": sy + sh,
                        "work_area_left": sx,
                        "work_area_right": sx + sw,
                        "work_area_top": sy,
                    }
                profile_cfg = prefs.setdefault("profile", {})
                if isinstance(profile_cfg, dict):
                    profile_cfg["exit_type"] = "Normal"
                    profile_cfg["exited_cleanly"] = True
                with open(pref_path, "w", encoding="utf-8") as f:
                    json.dump(prefs, f, ensure_ascii=False)
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"prepare_profile_tile_placement notice: {e}")


async def apply_cdp_window_bounds(
    context: Any,
    page: Any = None,
    tile_rect: Optional[Tuple[int, int, int, int]] = None,
    total_slots: int = 1,
    slot_index: int = 0,
) -> bool:
    """
    Forces Chrome's native window frame into the exact tile geometry via CDP
    Browser.getWindowForTarget + Browser.setWindowBounds, querying Chrome's own
    window.screen available dimensions so DPI scaling never causes overlap.
    """
    if not context:
        return False
    try:
        target_page = page or (context.pages[0] if getattr(context, "pages", None) else None)
        if not target_page:
            return False

        # Read Chrome's live screen work area (exact DIP coordinates matching setWindowBounds)
        chrome_work_area: Optional[Tuple[int, int, int, int]] = None
        try:
            scr = await target_page.evaluate(
                "() => ({x: Number(screen.availLeft || 0), y: Number(screen.availTop || 0), "
                "w: Number(screen.availWidth || 0), h: Number(screen.availHeight || 0)})"
            )
            if isinstance(scr, dict) and scr.get("w", 0) >= 640 and scr.get("h", 0) >= 480:
                chrome_work_area = (int(scr["x"]), int(scr["y"]), int(scr["w"]), int(scr["h"]))
        except Exception:
            chrome_work_area = None

        n_slots = max(1, int(total_slots or 1))
        if chrome_work_area is not None:
            rect = compute_tile_rect(slot_index, n_slots, work_area=chrome_work_area)
        else:
            rect = tile_rect or compute_tile_rect(slot_index, n_slots)
        x, y, w, h = (int(rect[0]), int(rect[1]), max(320, int(rect[2])), max(300, int(rect[3])))

        cdp = await context.new_cdp_session(target_page)
        try:
            win_info = await cdp.send("Browser.getWindowForTarget")
            win_id = win_info.get("windowId")
            if win_id is not None:
                # Step 1: exit maximized/fullscreen before moving/resizing
                try:
                    await cdp.send(
                        "Browser.setWindowBounds",
                        {"windowId": win_id, "bounds": {"windowState": "normal"}},
                    )
                    await asyncio.sleep(0.06)
                except Exception:
                    pass

                # Step 2: set exact coordinates and size
                await cdp.send(
                    "Browser.setWindowBounds",
                    {
                        "windowId": win_id,
                        "bounds": {
                            "windowState": "normal",
                            "left": x,
                            "top": y,
                            "width": w,
                            "height": h,
                        },
                    },
                )
                await asyncio.sleep(0.06)

                # Step 3: verify Chrome didn't clamp min width onto neighbor slot on narrow screens
                try:
                    actual = await cdp.send("Browser.getWindowBounds", {"windowId": win_id})
                    ab = (actual or {}).get("bounds") or {}
                    aw = int(ab.get("width") or w)
                    cols, _rows = compute_grid_dimensions(n_slots)
                    if cols > 1 and aw > w + 12 and chrome_work_area is not None:
                        cx, _cy, cw, _ch = chrome_work_area
                        col = (max(0, int(slot_index or 0)) % n_slots) % cols
                        adj_x = cx + round(max(0, cw - aw) * col / (cols - 1))
                        await cdp.send(
                            "Browser.setWindowBounds",
                            {
                                "windowId": win_id,
                                "bounds": {
                                    "windowState": "normal",
                                    "left": int(adj_x),
                                    "top": y,
                                    "width": w,
                                    "height": h,
                                },
                            },
                        )
                except Exception:
                    pass
                return True
        finally:
            try:
                await cdp.detach()
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"CDP window bounds notice: {e}")
    return False


class BrowserSlotPool:
    """
    Coordinates concurrent browser grid slots and prevents Chrome user-data-dir collisions.
    When a worker acquires a slot, it receives (slot_index, tile_rect).
    When Chrome closes, releasing the slot returns that exact screen tile for immediate reuse
    by the next waiting account.
    If multiple accounts share the same physical --user-data-dir (e.g. Profile 1, Profile 2
    inside a single Chrome User Data directory), a per-directory async lock ensures they do not
    collide on Chrome's SingletonLock while accounts with separate directories stay parallel.
    """

    def __init__(self, total_slots: int, work_area: Optional[Tuple[int, int, int, int]] = None):
        self.total_slots = max(1, int(total_slots or 1))
        self.work_area = get_screen_work_area(work_area)
        self._slots: asyncio.Queue = asyncio.Queue()
        for idx in range(self.total_slots):
            self._slots.put_nowait(idx)
        self._dir_locks: Dict[str, asyncio.Lock] = {}

    def _get_dir_lock(self, user_data_dir: Optional[str]) -> Optional[asyncio.Lock]:
        if not user_data_dir:
            return None
        raw = str(user_data_dir)
        # Support optional '::ProfileName' suffix so isolated profiles in default User Data can run in parallel
        if "::" in raw:
            base_part, prof_part = raw.split("::", 1)
            key = f"{os.path.normcase(os.path.abspath(base_part))}::{prof_part.strip().lower()}"
        else:
            key = os.path.normcase(os.path.abspath(raw))
        if key not in self._dir_locks:
            self._dir_locks[key] = asyncio.Lock()
        return self._dir_locks[key]

    @asynccontextmanager
    async def acquire(self, user_data_dir: Optional[str] = None, profile_subdir: Optional[str] = None):
        lock_target = user_data_dir
        if user_data_dir and profile_subdir and _should_prebridge_profile_dir(user_data_dir):
            lock_target = f"{user_data_dir}::{profile_subdir}"
        dir_lock = self._get_dir_lock(lock_target)
        if dir_lock is not None:
            await dir_lock.acquire()
        slot_index = await self._slots.get()
        try:
            tile_rect = compute_tile_rect(slot_index, self.total_slots, self.work_area)
            yield slot_index, tile_rect
        finally:
            self._slots.put_nowait(slot_index)
            if dir_lock is not None and dir_lock.locked():
                dir_lock.release()


# ==============================================================================
# 2. Human-Like Curved Mouse, Scroll, Warm-Up & Keystroke Primitives
# ==============================================================================

async def human_pause(low: float = 0.55, high: float = 1.45, mult: float = 1.0) -> None:
    """Sleeps for a randomized human-like duration scaled cleanly by multiplier."""
    lo = max(0.02, float(low) * float(mult or 1.0))
    hi = max(lo, float(high) * float(mult or 1.0))
    await asyncio.sleep(random.uniform(lo, hi))


async def human_move_to_coords(
    page: Any,
    target_x: float,
    target_y: float,
    start_x: Optional[float] = None,
    start_y: Optional[float] = None,
) -> None:
    """Moves Playwright mouse along a smooth quadratic Bezier curve with micro-jitter."""
    try:
        if start_x is None or start_y is None:
            vp = await page.evaluate(
                "() => ({w: window.innerWidth || 1000, h: window.innerHeight || 700})"
            )
            sx = float(vp.get("w", 1000)) * random.uniform(0.25, 0.75)
            sy = float(vp.get("h", 700)) * random.uniform(0.25, 0.75)
        else:
            sx, sy = float(start_x), float(start_y)

        # Control point slightly curved off the straight line
        cx = (sx + target_x) / 2.0 + random.uniform(-65.0, 65.0)
        cy = (sy + target_y) / 2.0 + random.uniform(-45.0, 45.0)
        steps = random.randint(10, 18)

        for step in range(1, steps + 1):
            t = step / steps
            # Smoothstep ease-in-out timing
            ease_t = t * t * (3.0 - 2.0 * t)
            inv = 1.0 - ease_t
            px = (inv * inv) * sx + 2.0 * inv * ease_t * cx + (ease_t * ease_t) * target_x
            py = (inv * inv) * sy + 2.0 * inv * ease_t * cy + (ease_t * ease_t) * target_y
            await page.mouse.move(px, py)
            await asyncio.sleep(random.uniform(0.008, 0.022))
    except Exception:
        try:
            await page.mouse.move(target_x, target_y, steps=8)
        except Exception:
            pass


async def human_click_element(
    page: Any,
    target: Any,
    hover_pause: bool = True,
    force_fallback: bool = True,
) -> bool:
    """
    Universal organic click helper supporting BOTH Playwright Locator and ElementHandle.
    Scrolls into view, glides mouse along a curved Bezier path to an off-center bounding box point,
    pauses subtly like a real user, and executes human mouse.down() -> hold -> mouse.up().
    """
    if target is None:
        return False
    try:
        try:
            await target.scroll_into_view_if_needed(timeout=4000)
        except Exception:
            pass
        await asyncio.sleep(random.uniform(0.08, 0.22))

        box = None
        try:
            box = await target.bounding_box()
        except Exception:
            box = None

        if box and box.get("width", 0) > 4 and box.get("height", 0) > 4:
            tx = box["x"] + box["width"] * random.uniform(0.28, 0.72)
            ty = box["y"] + box["height"] * random.uniform(0.28, 0.72)
            await human_move_to_coords(page, tx, ty)
            if hover_pause:
                await asyncio.sleep(random.uniform(0.10, 0.28))
            await page.mouse.down()
            await asyncio.sleep(random.uniform(0.035, 0.095))
            await page.mouse.up()
            return True

        await target.click(timeout=4000)
        return True
    except Exception:
        if force_fallback:
            try:
                await target.click(force=True, timeout=4000)
                return True
            except Exception:
                return False
        return False


async def human_move_and_click(
    page: Any,
    locator: Any,
    hover_pause: bool = True,
    force_fallback: bool = True,
) -> bool:
    """
    Smoothly scrolls element into view, glides mouse along Bezier arc to an organic
    off-center point inside its bounding box, pauses naturally, and clicks.
    """
    return await human_click_element(
        page,
        locator,
        hover_pause=hover_pause,
        force_fallback=force_fallback,
    )


async def human_click_coords(page: Any, x: float, y: float, hover_pause: bool = True) -> bool:
    """Moves mouse naturally along a curve to viewport coordinates (x, y) and clicks."""
    try:
        tx = float(x) + random.uniform(-2.0, 2.0)
        ty = float(y) + random.uniform(-2.0, 2.0)
        await human_move_to_coords(page, tx, ty)
        if hover_pause:
            await asyncio.sleep(random.uniform(0.10, 0.26))
        await page.mouse.down()
        await asyncio.sleep(random.uniform(0.035, 0.095))
        await page.mouse.up()
        return True
    except Exception:
        return False


async def human_type_text(
    page: Any,
    target: Any,
    text: str,
    clear_first: bool = True,
    allow_typos: bool = False,
) -> bool:
    """
    Clicks target (Locator or ElementHandle) cleanly, clears existing input if requested,
    and types with variable human keystroke rhythm, space/punctuation cadence, and optional safe typos.
    """
    if target is None:
        return False
    val_str = str(text if text is not None else "")
    try:
        await human_click_element(page, target, hover_pause=False)
        await asyncio.sleep(random.uniform(0.12, 0.28))
        if clear_first:
            try:
                await page.keyboard.press("Control+a")
                await asyncio.sleep(random.uniform(0.05, 0.11))
                await page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.07, 0.14))
            except Exception:
                try:
                    await target.fill("")
                except Exception:
                    pass

        for idx, ch in enumerate(val_str):
            if ch == "\n":
                try:
                    await page.keyboard.press("Shift+Enter")
                except Exception:
                    await page.keyboard.type("\n", delay=random.randint(25, 55))
                await asyncio.sleep(random.uniform(0.09, 0.22))
                continue

            # Natural variable keystroke timing
            delay_ms = random.randint(26, 78)
            if ch in (" ", ".", ",", "-", "!", "?"):
                delay_ms += random.randint(35, 115)
            await asyncio.sleep(delay_ms / 1000.0)
            await page.keyboard.type(ch, delay=random.randint(12, 34))

            # Optional 1.5% realistic typo & backspace correction on safe ASCII letters in longer strings
            if (
                allow_typos
                and len(val_str) > 18
                and 3 < idx < len(val_str) - 2
                and "a" <= ch <= "y"
                and random.random() < 0.015
            ):
                wrong_ch = chr(ord(ch) + 1)
                await asyncio.sleep(random.uniform(0.04, 0.09))
                await page.keyboard.type(wrong_ch, delay=random.randint(15, 30))
                await asyncio.sleep(random.uniform(0.11, 0.24))
                await page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.07, 0.16))
            elif idx > 0 and random.random() < 0.022:
                # 2.2% micro-thinking hesitation
                await asyncio.sleep(random.uniform(0.12, 0.25))

        return True
    except Exception:
        try:
            await target.fill(val_str)
            return True
        except Exception:
            return False


async def human_smooth_scroll(page: Any, total_delta_y: int = 550, steps: int = 6) -> None:
    """Scrolls page incrementally using smooth wheel bursts + micro-pauses."""
    step_count = max(2, int(steps))
    per_step = float(total_delta_y) / step_count
    for _ in range(step_count):
        jitter = per_step * random.uniform(0.82, 1.18)
        try:
            await page.mouse.wheel(0, jitter)
        except Exception:
            try:
                await page.evaluate("(d) => window.scrollBy(0, d)", jitter)
            except Exception:
                pass
        await asyncio.sleep(random.uniform(0.04, 0.11))


async def human_session_warmup(
    page: Any,
    duration_range: Tuple[float, float] = (1.2, 2.3),
    log_cb: Optional[Callable[[str, str], None]] = None,
) -> None:
    """
    Lightweight human warm-up right after Facebook authentication/landing:
    glides cursor naturally over the feed, performs a gentle scroll & reading pause,
    and nudges back slightly so sessions never jump instantaneously to automation URLs.
    """
    if not page:
        return
    try:
        if hasattr(page, "is_closed") and page.is_closed():
            return
        if log_cb:
            log_cb("INFO", "🧠 Performing natural human session warm-up...")
        vp = await page.evaluate(
            "() => ({w: window.innerWidth || 1000, h: window.innerHeight || 700})"
        )
        w = float(vp.get("w", 1000))
        h = float(vp.get("h", 700))

        # 1. Curved cursor glide toward center/feed area
        await human_move_to_coords(
            page,
            w * random.uniform(0.35, 0.65),
            h * random.uniform(0.32, 0.58),
        )
        lo_t, hi_t = float(duration_range[0]), max(float(duration_range[0]), float(duration_range[1]))
        budget = random.uniform(lo_t, hi_t)

        # 2. Gentle downward read scroll + pause + small look-back scroll
        down_px = random.randint(150, 320)
        await human_smooth_scroll(page, total_delta_y=down_px, steps=random.randint(4, 6))
        await asyncio.sleep(budget * random.uniform(0.45, 0.65))

        up_px = -random.randint(45, 115)
        await human_smooth_scroll(page, total_delta_y=up_px, steps=random.randint(2, 4))
        await asyncio.sleep(max(0.15, budget * 0.25))
    except Exception:
        pass


async def human_idle_drift(page: Any) -> None:
    """Subtle Bezier cursor drift and brief organic hesitation between repeated bot actions."""
    if not page:
        return
    try:
        if hasattr(page, "is_closed") and page.is_closed():
            return
        vp = await page.evaluate(
            "() => ({w: window.innerWidth || 1000, h: window.innerHeight || 700})"
        )
        w = float(vp.get("w", 1000))
        h = float(vp.get("h", 700))
        await human_move_to_coords(
            page,
            w * random.uniform(0.22, 0.78),
            h * random.uniform(0.22, 0.72),
        )
        await asyncio.sleep(random.uniform(0.18, 0.48))
        if random.random() < 0.35:
            await human_smooth_scroll(page, total_delta_y=random.randint(-45, 85), steps=2)
    except Exception:
        pass


# ==============================================================================
# 3. Custom Chrome Profile Folder Scanner (.lnk + Multi-Format Discovery)
# ==============================================================================

_NON_PROFILE_USERDATA_DIRS = {
    "crashpad",
    "grshadercache",
    "shadercache",
    "swreporter",
    "widevinecdm",
    "meipreload",
    "safetytips",
    "zxcvbndata",
    "browsermetrics",
    "ondeviceheadsuggestmodel",
    "hyphen-data",
    "pnacl",
    "snapshots",
    "system profile",
    "guest profile",
    "optimization_guide_model_store",
    "first_party_sets",
    "crowd deny",
    "certificate revocation lists",
    "filetypes",
    "floc",
    "mediafoundationwidevinecdm",
    "origin trials",
    "pki metadata",
    "privacy_sandbox",
    "recovery",
    "safebrowsing",
    "sslerrorassistant",
    "subresource filter",
    "tlsdeprecationconfig",
    "tpcdmetadata",
    "trusttokenkeycommitments",
    "zxcvbn",
}

_WALK_SKIP_DIRS = _NON_PROFILE_USERDATA_DIRS | {
    "cache",
    "code cache",
    "gpucache",
    "dawn",
    "dawngraphitecache",
    "dawnwebgpucache",
    "extensions",
    "indexeddb",
    "local storage",
    "session storage",
    "service worker",
    "blob_storage",
    "network",
    "storage",
    "webstorage",
    "__pycache__",
}


def _expand_win_env_and_home(raw: str) -> str:
    """Expands Windows %ENVVAR% (case-insensitive on Windows/Linux tests) and ~ in a path or CLI string."""
    if not raw:
        return ""
    s = str(raw).strip()
    # Expand %VAR% with case-insensitive lookup against os.environ
    env_map = {k.upper(): v for k, v in os.environ.items() if v}

    def _repl(m: re.Match) -> str:
        key = m.group(1).upper()
        if key in env_map:
            return env_map[key]
        if key == "LOCALAPPDATA":
            return os.path.expanduser(os.path.join("~", "AppData", "Local"))
        if key == "APPDATA":
            return os.path.expanduser(os.path.join("~", "AppData", "Roaming"))
        if key == "USERPROFILE":
            return os.path.expanduser("~")
        return m.group(0)

    s = re.sub(r"%([A-Za-z0-9_()]+)%", _repl, s)
    if s.startswith("~"):
        s = os.path.expanduser(s)
    return s


def _extract_chrome_cli_args(raw_args: str) -> Tuple[Optional[str], Optional[str]]:
    """Extracts (--user-data-dir / --data-dir, --profile-directory) from Chrome command-line string."""
    if not raw_args:
        return None, None

    expanded_args = _expand_win_env_and_home(raw_args)
    user_data_dir: Optional[str] = None
    profile_directory: Optional[str] = None

    # 1. Quoted or strict --user-data-dir= / --data-dir=
    ud_match = re.search(
        r'--?(?:user-data-dir|data-dir)\s*=\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s]+))',
        expanded_args,
        re.IGNORECASE,
    )
    if ud_match:
        user_data_dir = next((g for g in ud_match.groups() if g), None)

    # Rescue unquoted paths containing spaces up to next flag (e.g. --user-data-dir=D:\My Chromes\Acc 1 --profile-directory=Default)
    ud_unquoted_full = re.search(
        r'--?(?:user-data-dir|data-dir)\s*=\s*([^"\'\r\n]+?)(?=\s+--|\s+https?://|\s*$)',
        expanded_args,
        re.IGNORECASE,
    )
    if ud_unquoted_full:
        cand = ud_unquoted_full.group(1).strip().strip('"').strip("'")
        if cand and (not user_data_dir or (not os.path.exists(_expand_win_env_and_home(user_data_dir)) and os.path.exists(_expand_win_env_and_home(cand)))):
            user_data_dir = cand

    # 2. Quoted or multi-word --profile-directory= (e.g. --profile-directory=Profile 1 OR --profile-directory="Profile 1")
    pd_match = re.search(
        r'--?profile-directory\s*=\s*(?:"([^"]+)"|\'([^\']+)\'|(.+?)(?=\s+--|\s+https?://|\s*$))',
        expanded_args,
        re.IGNORECASE,
    )
    if pd_match:
        profile_directory = next((g for g in pd_match.groups() if g), None)

    # 3. Space-separated flag fallback (--user-data-dir "C:\path" / --profile-directory "Profile 1")
    if not user_data_dir or not profile_directory:
        try:
            tokens = shlex.split(expanded_args, posix=False)
            for idx, tok in enumerate(tokens):
                clean_tok = tok.strip().strip('"').strip("'")
                low = clean_tok.lower()
                if not user_data_dir and low in ("--user-data-dir", "-user-data-dir", "--data-dir") and idx + 1 < len(tokens):
                    user_data_dir = tokens[idx + 1].strip().strip('"').strip("'")
                elif not profile_directory and low in ("--profile-directory", "-profile-directory") and idx + 1 < len(tokens):
                    profile_directory = tokens[idx + 1].strip().strip('"').strip("'")
        except Exception:
            pass

    if user_data_dir:
        cleaned_ud = _expand_win_env_and_home(user_data_dir.strip().strip('"').strip("'"))
        # Strip stray trailing backslash before closing quote artifact (e.g. "D:\Foo\")
        if len(cleaned_ud) > 3 and cleaned_ud.endswith(("\\", "/")):
            cleaned_ud = cleaned_ud.rstrip("\\/")
        user_data_dir = os.path.normpath(cleaned_ud) if cleaned_ud else None
    if profile_directory:
        profile_directory = profile_directory.strip().strip('"').strip("'")
    return user_data_dir or None, profile_directory or None


def _read_lnk_extradata_target(data: bytes, start_pos: int) -> str:
    """Scans ShellLink ExtraData blocks (e.g. EnvironmentVariableDataBlock 0xA0000001) for fallback target path."""
    pos = max(0, int(start_pos))
    n = len(data)
    while pos + 8 <= n:
        block_size, block_sig = struct.unpack_from("<II", data, pos)
        if block_size < 4:
            break
        if pos + block_size > n:
            break
        if block_sig == 0xA0000001 and block_size >= 788:
            # EnvironmentVariableDataBlock: offset 8..268 ANSI, offset 268..788 UTF-16LE
            uni_raw = data[pos + 268 : pos + 788]
            if len(uni_raw) >= 2:
                try:
                    decoded = uni_raw.decode("utf-16-le", errors="ignore").split("\x00", 1)[0].strip()
                    if decoded:
                        return decoded
                except Exception:
                    pass
            ansi_raw = data[pos + 8 : pos + 268]
            nul = ansi_raw.find(b"\x00")
            if nul > 0:
                decoded = ansi_raw[:nul].decode("mbcs" if os.name == "nt" else "latin-1", errors="ignore").strip()
                if decoded:
                    return decoded
        pos += block_size
    return ""


def _parse_lnk_binary_full(lnk_path: str) -> Tuple[str, str, str]:
    """
    Pure-Python Microsoft Shell Link (.lnk) binary parser.
    Reads MS-SHLLINK Header, LinkTargetIDList, LinkInfo (ANSI & Unicode), StringData
    (Name, RelativePath, WorkingDir, CommandLineArguments, IconLocation), and ExtraData blocks.
    Returns (target_hint, arguments, working_dir).
    """
    with open(lnk_path, "rb") as f:
        data = f.read()

    if len(data) < 76:
        return "", "", ""

    header_size = struct.unpack_from("<I", data, 0)[0]
    if header_size != 0x4C:
        return "", "", ""

    expected_clsid = bytes.fromhex("0114020000000000c000000000000046")
    if data[4:20] != expected_clsid:
        return "", "", ""

    flags = struct.unpack_from("<I", data, 0x14)[0]
    has_target_id_list = bool(flags & 0x01)
    has_link_info = bool(flags & 0x02)
    has_name = bool(flags & 0x04)
    has_relative_path = bool(flags & 0x08)
    has_working_dir = bool(flags & 0x10)
    has_arguments = bool(flags & 0x20)
    has_icon_location = bool(flags & 0x40)
    is_unicode = bool(flags & 0x80)

    pos = 76
    target_hint = ""

    # 1. LinkTargetIDList
    if has_target_id_list:
        if pos + 2 > len(data):
            return "", "", ""
        id_list_size = struct.unpack_from("<H", data, pos)[0]
        pos += 2 + id_list_size

    # 2. LinkInfo
    if has_link_info:
        if pos + 4 > len(data):
            return "", "", ""
        link_info_size = struct.unpack_from("<I", data, pos)[0]
        if link_info_size >= 28 and pos + link_info_size <= len(data):
            try:
                li_header_size = struct.unpack_from("<I", data, pos + 4)[0]
                li_flags = struct.unpack_from("<I", data, pos + 8)[0]
                if li_flags & 0x01:
                    # Prefer Unicode LocalBasePathOffsetUnicode if LinkInfoHeaderSize >= 0x24
                    if li_header_size >= 0x24 and pos + 36 <= pos + link_info_size:
                        uni_off = struct.unpack_from("<I", data, pos + 28)[0]
                        if 0 < uni_off < link_info_size - 1:
                            uni_tail = data[pos + uni_off : pos + link_info_size]
                            dec = uni_tail.decode("utf-16-le", errors="ignore").split("\x00", 1)[0].strip()
                            if dec:
                                target_hint = dec
                    if not target_hint:
                        local_base_off = struct.unpack_from("<I", data, pos + 16)[0]
                        if 0 < local_base_off < link_info_size:
                            raw_tail = data[pos + local_base_off : pos + link_info_size]
                            nul_idx = raw_tail.find(b"\x00")
                            if nul_idx > 0:
                                target_hint = raw_tail[:nul_idx].decode("mbcs" if os.name == "nt" else "latin-1", errors="ignore").strip()
            except Exception:
                pass
        pos += link_info_size

    def _read_string_data() -> str:
        nonlocal pos
        if pos + 2 > len(data):
            return ""
        char_count = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        if is_unicode:
            byte_len = char_count * 2
            raw = data[pos : pos + byte_len]
            pos += byte_len
            return raw.decode("utf-16-le", errors="ignore")
        else:
            raw = data[pos : pos + char_count]
            pos += char_count
            return raw.decode("mbcs" if os.name == "nt" else "latin-1", errors="ignore")

    if has_name:
        _read_string_data()
    rel_path = _read_string_data() if has_relative_path else ""
    working_dir = _read_string_data() if has_working_dir else ""
    arguments = _read_string_data() if has_arguments else ""
    icon_loc = _read_string_data() if has_icon_location else ""

    if not target_hint:
        extra_target = _read_lnk_extradata_target(data, pos)
        if extra_target:
            target_hint = extra_target
    if not target_hint and rel_path:
        target_hint = rel_path
    if not target_hint and icon_loc and icon_loc.lower().endswith(".exe"):
        target_hint = icon_loc

    return target_hint.strip(), arguments.strip(), working_dir.strip()


def _parse_lnk_binary(lnk_path: str) -> Tuple[str, str]:
    """Backward-compatible wrapper returning (target_hint, arguments)."""
    tp, args, _wd = _parse_lnk_binary_full(lnk_path)
    return tp, args


def _resolve_lnk_batch_windows(lnk_paths: List[str]) -> Dict[str, Tuple[str, str, str]]:
    """
    Resolves a batch of Windows .lnk shortcuts in ONE PowerShell WScript.Shell COM call.
    Uses Base64 UTF-16LE -EncodedCommand + UTF-8 JSON stdin/stdout + CREATE_NO_WINDOW so
    Unicode paths, quotes, MSI/Darwin shortcuts, and hundreds of files resolve cleanly with zero flicker.
    Returns {lnk_path: (target_path, arguments, working_dir)}.
    """
    results: Dict[str, Tuple[str, str, str]] = {}
    if os.name != "nt" or not lnk_paths:
        return results

    try:
        import base64

        ps_script = (
            "[Console]::InputEncoding = [System.Text.Encoding]::UTF8;"
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;"
            "$raw = [Console]::In.ReadToEnd();"
            "if (-not $raw) { exit 0 };"
            "$paths = $raw | ConvertFrom-Json;"
            "if ($paths -is [string]) { $paths = @($paths) };"
            "$sh = New-Object -ComObject WScript.Shell;"
            "$out = @();"
            "foreach ($p in $paths) {"
            "  try {"
            "    if ($p -and (Test-Path -LiteralPath $p)) {"
            "      $sc = $sh.CreateShortcut($p);"
            "      $out += [PSCustomObject]@{"
            "        lnk = [string]$p;"
            "        target = [string]$sc.TargetPath;"
            "        args = [string]$sc.Arguments;"
            "        workdir = [string]$sc.WorkingDirectory"
            "      };"
            "    }"
            "  } catch {}"
            "}"
            "$out | ConvertTo-Json -Compress -Depth 3"
        )
        encoded = base64.b64encode(ps_script.encode("utf-16-le")).decode("ascii")
        payload_json = json.dumps(list(lnk_paths), ensure_ascii=False)
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
            input=payload_json,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=18,
            creationflags=creation_flags,
        )
        if res.returncode == 0 and res.stdout and res.stdout.strip():
            raw_out = res.stdout.strip()
            # Handle occasional BOM or prefix text before JSON
            idx_obj = raw_out.find("{")
            idx_arr = raw_out.find("[")
            starts = [i for i in (idx_obj, idx_arr) if i >= 0]
            if starts:
                raw_out = raw_out[min(starts):]
            parsed = json.loads(raw_out)
            items = parsed if isinstance(parsed, list) else ([parsed] if isinstance(parsed, dict) else [])
            for item in items:
                if not isinstance(item, dict):
                    continue
                lnk_k = str(item.get("lnk") or "")
                tp = str(item.get("target") or "").strip()
                ar = str(item.get("args") or "").strip()
                wd = str(item.get("workdir") or "").strip()
                if lnk_k:
                    results[lnk_k] = (tp, ar, wd)
    except Exception as e:
        logger.debug(f"Windows batch .lnk COM resolve notice: {e}")

    return results


def parse_windows_lnk(lnk_path: str) -> Tuple[str, str]:
    """
    Parses a Windows .lnk shortcut to retrieve (target_path, command_line_arguments).
    Uses WScript.Shell COM on Windows (handling MSI/Darwin/Unicode/Env shortcuts) and
    falls back to pure-Python Shell Link binary parser cleanly.
    """
    if os.name == "nt":
        batch = _resolve_lnk_batch_windows([lnk_path])
        if lnk_path in batch:
            tp, ar, _wd = batch[lnk_path]
            if tp or ar:
                return _expand_win_env_and_home(tp), _expand_win_env_and_home(ar)

    try:
        target_path, arguments, _wd = _parse_lnk_binary_full(lnk_path)
        return _expand_win_env_and_home(target_path), _expand_win_env_and_home(arguments)
    except Exception:
        return "", ""


def _is_chrome_profile_leaf(path: str) -> bool:
    """Checks whether a directory looks like an individual Chrome profile dir (e.g. Default, Profile 1)."""
    if not path or not os.path.isdir(path):
        return False
    markers = (
        "Preferences",
        "Secure Preferences",
        "Cookies",
        os.path.join("Network", "Cookies"),
        "Login Data",
        "History",
        "Web Data",
    )
    return any(os.path.exists(os.path.join(path, m)) for m in markers)


def _is_chrome_userdata_root(path: str) -> bool:
    """Checks whether a directory looks like a Chrome --user-data-dir root."""
    if not path or not os.path.isdir(path):
        return False
    if os.path.isfile(os.path.join(path, "Local State")) or os.path.isfile(os.path.join(path, "First Run")):
        return True
    if _is_chrome_profile_leaf(os.path.join(path, "Default")) or os.path.isdir(os.path.join(path, "Default")):
        return True
    try:
        for entry in os.listdir(path):
            low = entry.lower()
            if low in _NON_PROFILE_USERDATA_DIRS:
                continue
            sub = os.path.join(path, entry)
            if os.path.isdir(sub) and (low == "default" or low.startswith("profile ") or _is_chrome_profile_leaf(sub)):
                return True
    except Exception:
        pass
    return False


def _read_chrome_profile_label(user_data_dir: str, profile_dir_name: Optional[str]) -> str:
    """Reads friendly Chrome profile display name from Preferences or Local State if available."""
    try:
        candidates: List[str] = []
        if profile_dir_name:
            candidates.append(os.path.join(user_data_dir, profile_dir_name))
        candidates.append(os.path.join(user_data_dir, "Default"))
        candidates.append(user_data_dir)
        for sub in candidates:
            if not os.path.isdir(sub):
                continue
            pref_file = os.path.join(sub, "Preferences")
            if os.path.isfile(pref_file):
                with open(pref_file, "r", encoding="utf-8", errors="ignore") as f:
                    prefs = json.load(f)
                prof_name = (prefs.get("profile") or {}).get("name") or ""
                acc_info = prefs.get("account_info") or []
                email = acc_info[0].get("email", "") if isinstance(acc_info, list) and acc_info else ""
                if prof_name and prof_name not in ("Person 1", "Your Chrome", "Default"):
                    return f"{prof_name}"
                if email:
                    return email
    except Exception:
        pass
    return ""


def _resolve_default_userdata_for_exe(target_exe: str, working_dir: str = "") -> Optional[str]:
    """Resolves the User Data root folder for Chrome/Edge/Brave/Chromium or portable browser clones."""
    exe_low = (target_exe or "").lower()
    # 1. Check WorkingDirectory if explicitly set and looks like a Chrome profile or User Data folder
    if working_dir and os.path.isdir(working_dir):
        for cand in (
            working_dir,
            os.path.join(working_dir, "User Data"),
            os.path.join(working_dir, "Data", "profile"),
            os.path.join(working_dir, "profile"),
        ):
            if _is_chrome_userdata_root(cand):
                return os.path.abspath(cand)

    # 2. Check portable Chrome / cloned folder layout relative to target_exe
    if target_exe:
        exe_dir = os.path.dirname(target_exe)
        parent_dir = os.path.dirname(exe_dir) if exe_dir else ""
        grand_dir = os.path.dirname(parent_dir) if parent_dir else ""
        portable_cands = [
            os.path.join(exe_dir, "User Data"),
            os.path.join(exe_dir, "Data", "profile"),
            os.path.join(exe_dir, "Data", "User Data"),
            os.path.join(exe_dir, "profile"),
            os.path.join(parent_dir, "User Data"),
            os.path.join(parent_dir, "Data", "profile"),
            os.path.join(grand_dir, "Data", "profile"),
        ]
        # Only treat sibling User Data as clone-specific if exe is not standard Program Files install
        is_system_prog = any(
            seg in exe_low for seg in ("\\program files\\", "\\program files (x86)\\", "\\appdata\\local\\google\\chrome\\application")
        )
        if not is_system_prog:
            for cand in portable_cands:
                if cand and _is_chrome_userdata_root(cand):
                    return os.path.abspath(cand)

    # 3. Standard OS browser User Data roots
    local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser(os.path.join("~", "AppData", "Local"))
    rel_roots: List[str] = []
    if "msedge" in exe_low or "edge" in exe_low:
        rel_roots.append(os.path.join("Microsoft", "Edge", "User Data"))
    elif "brave" in exe_low:
        rel_roots.append(os.path.join("BraveSoftware", "Brave-Browser", "User Data"))
    elif "chromium" in exe_low:
        rel_roots.append(os.path.join("Chromium", "User Data"))
    elif "chrome sxs" in exe_low or "canary" in exe_low:
        rel_roots.append(os.path.join("Google", "Chrome SxS", "User Data"))
    elif "chrome beta" in exe_low:
        rel_roots.append(os.path.join("Google", "Chrome Beta", "User Data"))
    else:
        rel_roots.append(os.path.join("Google", "Chrome", "User Data"))
        rel_roots.append(os.path.join("Chromium", "User Data"))

    for rel in rel_roots:
        cand = os.path.abspath(os.path.join(local_app, rel))
        if os.path.isdir(cand):
            return cand
    return None


def _make_custom_profile_account(
    user_data_dir: str,
    profile_directory: Optional[str],
    display_name: str,
    chrome_executable: Optional[str] = None,
    shortcut_path: Optional[str] = None,
) -> Dict[str, Any]:
    abs_dir = os.path.abspath(user_data_dir)
    prof_key = (profile_directory or "").strip()
    digest = hashlib.md5(f"{abs_dir}::{prof_key}".encode("utf-8", errors="ignore")).hexdigest()[:10]
    exe_clean = os.path.abspath(chrome_executable) if (chrome_executable and os.path.isfile(chrome_executable)) else ""
    lnk_clean = os.path.abspath(shortcut_path) if (shortcut_path and os.path.isfile(shortcut_path)) else ""
    return {
        "id": f"chrome_{digest}",
        "name": display_name,
        "status": "Chrome Profile",
        "proxy": "Direct",
        "network_mode": "direct",
        "profile_dir": abs_dir,
        "chrome_profile_directory": prof_key,
        "chrome_executable": exe_clean,
        "shortcut_path": lnk_clean,
        "is_custom_chrome_profile": True,
        "cookies": "",
    }


def _find_portable_chrome_exe_in_dir(folder: str) -> Optional[str]:
    """Looks inside a cloned/portable folder for chrome.exe/msedge.exe/brave.exe."""
    for rel in (
        "chrome.exe",
        os.path.join("Application", "chrome.exe"),
        os.path.join("App", "Chrome-bin", "chrome.exe"),
        os.path.join("Chrome-bin", "chrome.exe"),
        "msedge.exe",
        "brave.exe",
    ):
        cand = os.path.join(folder, rel)
        if os.path.isfile(cand):
            return os.path.abspath(cand)
    return None


def scan_chrome_profiles_folder(
    folder_path: str,
    diagnostics: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Discovers logged-in Chrome browser profiles inside a user-picked folder supporting all formats:
      1. Windows .lnk shortcuts (recursive up to 2 levels) with:
         - --user-data-dir / --data-dir and optional --profile-directory
         - --profile-directory only (resolves Chrome/Edge/Brave/Portable User Data automatically)
         - Bare browser shortcuts (working dir / portable Data / default Chrome User Data)
         - Shortcuts pointing directly to Chrome profile / User Data directories
      2. .bat / .cmd launcher scripts invoking Chrome with --user-data-dir / --profile-directory
      3. Single Chrome User Data root folder containing Default, Profile 1, or custom-named profile dirs
      4. Subfolders each acting as an isolated Chrome user-data-dir or portable Chrome clone
    """
    if not folder_path or not os.path.isdir(folder_path):
        if diagnostics is not None:
            diagnostics.append(f"Selected folder does not exist: {folder_path}")
        return []

    root = os.path.abspath(folder_path)
    discovered: List[Dict[str, Any]] = []
    seen_keys = set()

    def _diag(msg: str):
        if diagnostics is not None:
            diagnostics.append(msg)

    def _is_duplicate(abs_ud: str, prof_name: Optional[str]) -> bool:
        norm_ud = os.path.normcase(abs_ud)
        p_norm = (prof_name or "").strip().lower()
        if (norm_ud, p_norm) in seen_keys:
            return True
        # Treat empty prof_name and explicit "default" equivalently when checking duplicates
        if p_norm == "default" and (norm_ud, "") in seen_keys:
            return True
        if p_norm == "" and (norm_ud, "default") in seen_keys:
            return True
        return False

    def _add(
        ud_dir: str,
        prof_name: Optional[str],
        label: str,
        chrome_exe: Optional[str] = None,
        lnk_src: Optional[str] = None,
    ):
        if not ud_dir:
            return
        abs_ud = os.path.abspath(ud_dir)
        p_clean = (prof_name or "").strip() or None
        if _is_duplicate(abs_ud, p_clean):
            return
        seen_keys.add((os.path.normcase(abs_ud), (p_clean or "").lower()))
        discovered.append(
            _make_custom_profile_account(
                abs_ud,
                p_clean,
                label,
                chrome_executable=chrome_exe,
                shortcut_path=lnk_src,
            )
        )

    # Collect .lnk shortcuts & .bat/.cmd scripts up to 2 subfolder levels deep
    lnk_candidates: List[str] = []
    script_candidates: List[str] = []
    root_sep_count = root.rstrip("\\/").count(os.sep)
    try:
        for cur_root, dirnames, filenames in os.walk(root):
            depth = cur_root.rstrip("\\/").count(os.sep) - root_sep_count
            if depth >= 2:
                dirnames[:] = []
            else:
                dirnames[:] = [
                    d for d in sorted(dirnames)
                    if d.lower() not in _WALK_SKIP_DIRS
                ]
            for fn in sorted(filenames):
                low = fn.lower()
                full_f = os.path.join(cur_root, fn)
                if low.endswith(".lnk"):
                    lnk_candidates.append(full_f)
                elif low.endswith((".bat", ".cmd")):
                    script_candidates.append(full_f)
    except Exception as e:
        _diag(f"Folder walk notice: {e}")

    # Resolve all .lnk shortcuts in ONE batch COM call on Windows, with binary parser fallback
    lnk_resolved: Dict[str, Tuple[str, str, str]] = {}
    if lnk_candidates and os.name == "nt":
        lnk_resolved = _resolve_lnk_batch_windows(lnk_candidates)
        _diag(f"Inspected {len(lnk_candidates)} .lnk shortcut(s) via Windows Shell.")

    for lnk_file in lnk_candidates:
        if lnk_file in lnk_resolved:
            raw_target, raw_args, raw_workdir = lnk_resolved[lnk_file]
        else:
            try:
                raw_target, raw_args, raw_workdir = _parse_lnk_binary_full(lnk_file)
            except Exception:
                raw_target, raw_args, raw_workdir = "", "", ""

        target_exe = _expand_win_env_and_home(raw_target)
        cli_args = _expand_win_env_and_home(raw_args)
        working_dir = _expand_win_env_and_home(raw_workdir)

        # Fallback: if binary parser returned empty target/args on Windows, try single WScript call
        if os.name == "nt" and not target_exe and not cli_args:
            target_exe, cli_args = parse_windows_lnk(lnk_file)

        base_label = os.path.splitext(os.path.basename(lnk_file))[0]
        lnk_parent = os.path.dirname(lnk_file)

        # Special Case: Shortcut points directly to a directory on disk (shortcut to profile folder)
        if target_exe and os.path.isdir(target_exe) and not cli_args:
            target_dir = os.path.abspath(target_exe)
            parent_dir = os.path.dirname(target_dir)
            leaf_name = os.path.basename(target_dir)
            if _is_chrome_profile_leaf(target_dir) and (
                os.path.isfile(os.path.join(parent_dir, "Local State"))
                or leaf_name.lower() == "default"
                or leaf_name.lower().startswith("profile ")
            ):
                friendly = _read_chrome_profile_label(parent_dir, leaf_name)
                label = f"{base_label} ({friendly})" if friendly and friendly.lower() not in base_label.lower() else base_label
                _add(parent_dir, leaf_name, label, lnk_src=lnk_file)
                continue
            elif _is_chrome_userdata_root(target_dir):
                friendly = _read_chrome_profile_label(target_dir, "Default")
                label = f"{base_label} ({friendly})" if friendly and friendly.lower() not in base_label.lower() else base_label
                _add(target_dir, None, label, lnk_src=lnk_file)
                continue

        ud_dir, prof_dir = _extract_chrome_cli_args(cli_args)
        exe_base = os.path.basename(target_exe).lower() if target_exe else ""
        is_browser_shortcut = (
            any(tok in exe_base for tok in ("chrome", "chromium", "msedge", "edge", "brave", "cent", "opera", "vivaldi"))
            or "chrome" in cli_args.lower()
            or ud_dir is not None
            or prof_dir is not None
        )
        if not is_browser_shortcut:
            _diag(f"Skipped '{os.path.basename(lnk_file)}': target '{target_exe}' is not a Chrome shortcut.")
            continue

        # Normalize relative --user-data-dir against WorkingDirectory or .lnk folder
        if ud_dir and not os.path.isabs(ud_dir):
            for base_rel in (working_dir, lnk_parent):
                if base_rel and os.path.isdir(base_rel):
                    cand_rel = os.path.abspath(os.path.join(base_rel, ud_dir))
                    if os.path.isdir(cand_rel):
                        ud_dir = cand_rel
                        break

        # If --user-data-dir is set cleanly: check whether ud_dir was mistakenly pointed at ...\Default vs User Data root
        if ud_dir and not os.path.isdir(ud_dir) and os.name != "nt":
            pass
        if ud_dir and os.path.isdir(ud_dir):
            # If user passed a nonexistent sub? No, ud_dir exists. Keep exact ud_dir + prof_dir!
            pass
        elif not ud_dir:
            # Resolve Chrome/Edge/Brave/Portable User Data path when shortcut only passed --profile-directory OR bare chrome.exe
            resolved_ud = _resolve_default_userdata_for_exe(target_exe, working_dir=working_dir or lnk_parent)
            if resolved_ud:
                ud_dir = resolved_ud
                if not prof_dir:
                    prof_dir = "Default"
            else:
                # Last resort: check if .lnk is sitting alongside a matching subfolder (e.g. FB1.lnk next to FB1/)
                sibling_dir = os.path.join(lnk_parent, base_label)
                if _is_chrome_userdata_root(sibling_dir):
                    ud_dir = sibling_dir

        if ud_dir and os.path.isdir(ud_dir):
            extra_lbl = _read_chrome_profile_label(ud_dir, prof_dir)
            if extra_lbl and extra_lbl.lower() not in base_label.lower():
                label = f"{base_label} ({extra_lbl})"
            elif prof_dir and prof_dir.lower() not in base_label.lower():
                label = f"{base_label} [{prof_dir}]"
            else:
                label = base_label
            exe_valid = target_exe if (target_exe and os.path.isfile(target_exe)) else None
            _add(ud_dir, prof_dir, label, chrome_exe=exe_valid, lnk_src=lnk_file)
        else:
            _diag(
                f"Shortcut '{os.path.basename(lnk_file)}' points to missing User Data folder: '{ud_dir or '(none)'}'"
            )

    # Also inspect .bat / .cmd Chrome launcher scripts in the folder
    for bat_file in script_candidates:
        try:
            if os.path.getsize(bat_file) > 65536:
                continue
            with open(bat_file, "r", encoding="utf-8", errors="ignore") as bf:
                content = bf.read()
            if "user-data-dir" not in content.lower() and "profile-directory" not in content.lower():
                continue
            ud_dir, prof_dir = _extract_chrome_cli_args(content)
            if ud_dir and not os.path.isabs(ud_dir):
                cand_rel = os.path.abspath(os.path.join(os.path.dirname(bat_file), ud_dir))
                if os.path.isdir(cand_rel):
                    ud_dir = cand_rel
            if not ud_dir and prof_dir:
                ud_dir = _resolve_default_userdata_for_exe(content, working_dir=os.path.dirname(bat_file))
            if ud_dir and os.path.isdir(ud_dir):
                base_label = os.path.splitext(os.path.basename(bat_file))[0]
                extra_lbl = _read_chrome_profile_label(ud_dir, prof_dir)
                label = f"{base_label} ({extra_lbl})" if extra_lbl else base_label
                _add(ud_dir, prof_dir, label, lnk_src=bat_file)
        except Exception:
            pass

    # --- Format 2: Root folder itself is a Chrome User Data directory (Default, Profile 1, or custom-named) ---
    has_root_local_state = os.path.isfile(os.path.join(root, "Local State"))
    direct_profile_subdirs: List[str] = []
    try:
        for entry in sorted(os.listdir(root)):
            sub = os.path.join(root, entry)
            if not os.path.isdir(sub):
                continue
            low = entry.lower()
            if low in _NON_PROFILE_USERDATA_DIRS:
                continue
            is_named_chrome_prof = low == "default" or low.startswith("profile ")
            if _is_chrome_profile_leaf(sub) and (is_named_chrome_prof or has_root_local_state):
                direct_profile_subdirs.append(entry)
    except Exception:
        pass

    if direct_profile_subdirs and (has_root_local_state or any(d.lower() == "default" or d.lower().startswith("profile ") for d in direct_profile_subdirs)):
        root_name = os.path.basename(root)
        for prof_entry in direct_profile_subdirs:
            friendly = _read_chrome_profile_label(root, prof_entry)
            label = f"{prof_entry} ({friendly})" if friendly else f"{root_name} - {prof_entry}"
            _add(root, prof_entry, label)

    # Case 2b: User selected a single profile folder directly (e.g. picked `User Data/Default` itself)
    if not direct_profile_subdirs and _is_chrome_profile_leaf(root):
        parent_dir = os.path.dirname(root)
        leaf_name = os.path.basename(root)
        if os.path.isfile(os.path.join(parent_dir, "Local State")) or leaf_name == "Default" or leaf_name.startswith("Profile "):
            friendly = _read_chrome_profile_label(parent_dir, leaf_name)
            label = f"{leaf_name} ({friendly})" if friendly else leaf_name
            _add(parent_dir, leaf_name, label)
        else:
            friendly = _read_chrome_profile_label(root, None)
            label = f"{leaf_name} ({friendly})" if friendly else leaf_name
            _add(root, None, label)

    # --- Format 1: Subfolders each acting as an isolated Chrome user-data directory or portable clone ---
    try:
        for entry in sorted(os.listdir(root)):
            sub = os.path.join(root, entry)
            if not os.path.isdir(sub):
                continue
            if entry.lower() in _NON_PROFILE_USERDATA_DIRS or entry.lower() == "default" or entry.lower().startswith("profile "):
                continue

            portable_exe = _find_portable_chrome_exe_in_dir(sub)

            # Check portable sub-roots first (`Data/profile`, `User Data`) if `sub` itself isn't already User Data
            candidate_ud_roots = [sub]
            for extra_sub in ("User Data", os.path.join("Data", "profile"), os.path.join("Data", "User Data")):
                extra_p = os.path.join(sub, extra_sub)
                if os.path.isdir(extra_p):
                    candidate_ud_roots.append(extra_p)

            for ud_cand in candidate_ud_roots:
                sub_has_ls = os.path.isfile(os.path.join(ud_cand, "Local State"))
                sub_profiles: List[str] = []
                try:
                    for sub_item in sorted(os.listdir(ud_cand)):
                        sub_item_path = os.path.join(ud_cand, sub_item)
                        low = sub_item.lower()
                        if low in _NON_PROFILE_USERDATA_DIRS:
                            continue
                        if os.path.isdir(sub_item_path) and (low == "default" or low.startswith("profile ") or sub_has_ls) and _is_chrome_profile_leaf(sub_item_path):
                            sub_profiles.append(sub_item)
                except Exception:
                    pass

                if sub_profiles:
                    non_default = [p for p in sub_profiles if p.lower() != "default"]
                    if not non_default and "Default" in sub_profiles:
                        friendly = _read_chrome_profile_label(ud_cand, "Default")
                        label = f"{entry} ({friendly})" if friendly else entry
                        _add(ud_cand, None, label, chrome_exe=portable_exe)
                    else:
                        for p in sub_profiles:
                            friendly = _read_chrome_profile_label(ud_cand, p)
                            label = f"{entry} [{p}] ({friendly})" if friendly else f"{entry} [{p}]"
                            _add(ud_cand, p, label, chrome_exe=portable_exe)
                elif sub_has_ls or _is_chrome_profile_leaf(ud_cand) or os.path.isdir(os.path.join(ud_cand, "Default")):
                    friendly = _read_chrome_profile_label(ud_cand, None)
                    label = f"{entry} ({friendly})" if friendly else entry
                    _add(ud_cand, None, label, chrome_exe=portable_exe)
    except Exception:
        pass

    return discovered


# ==============================================================================
# 4. Shared Custom-Aware Chrome Launcher Helper for Automation Bots
# ==============================================================================

def _is_chrome_profile_locked(profile_dir: str) -> bool:
    """
    Returns True only if another active Chrome/Chromium process holds an active lock
    on profile_dir. Safely removes stale non-locked Singleton*/lockfile remnants.
    """
    if not profile_dir or not os.path.isdir(profile_dir):
        return False

    # Windows Chrome locks <user-data-dir>/lockfile exclusively while running
    win_lock = os.path.join(profile_dir, "lockfile")
    if os.name == "nt" and os.path.exists(win_lock):
        try:
            # Test exclusive write/rename access without modifying content
            with open(win_lock, "r+b"):
                pass
        except PermissionError:
            return True
        except OSError as e:
            if getattr(e, "winerror", 0) in (32, 33, 5):  # ERROR_SHARING_VIOLATION / LOCK_VIOLATION
                return True

    # POSIX Chrome creates SingletonLock -> hostname-<pid> symlink
    posix_lock = os.path.join(profile_dir, "SingletonLock")
    if os.name != "nt" and os.path.islink(posix_lock):
        try:
            target = os.readlink(posix_lock)
            pid_str = target.rsplit("-", 1)[-1]
            if pid_str.isdigit():
                os.kill(int(pid_str), 0)
                return True
        except ProcessLookupError:
            pass
        except Exception:
            pass

    return False


def _cleanup_stale_chrome_locks(profile_dir: str) -> None:
    """Removes stale Chrome lock files when no active browser process holds them."""
    if not profile_dir or not os.path.isdir(profile_dir):
        return
    for fname in ("SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"):
        fpath = os.path.join(profile_dir, fname)
        if os.path.exists(fpath) or os.path.islink(fpath):
            try:
                if os.path.islink(fpath) or os.path.isfile(fpath):
                    os.unlink(fpath)
                elif os.path.isdir(fpath):
                    import shutil
                    shutil.rmtree(fpath, ignore_errors=True)
            except Exception:
                pass


def _is_default_chrome_userdata_dir(user_data_dir: Optional[str]) -> bool:
    """
    Returns True if user_data_dir points to a system default Chrome/Edge/Brave User Data root
    where Chrome 136+ blocks --remote-debugging-port OR another Chrome instance typically shares lockfile.
    """
    if not user_data_dir:
        return False
    norm = os.path.normcase(os.path.abspath(str(user_data_dir)))
    candidates: List[str] = []
    if os.name == "nt":
        local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser(os.path.join("~", "AppData", "Local"))
        for rel in (
            os.path.join("Google", "Chrome", "User Data"),
            os.path.join("Google", "Chrome Beta", "User Data"),
            os.path.join("Google", "Chrome SxS", "User Data"),
            os.path.join("Chromium", "User Data"),
            os.path.join("Microsoft", "Edge", "User Data"),
            os.path.join("BraveSoftware", "Brave-Browser", "User Data"),
        ):
            candidates.append(os.path.normcase(os.path.abspath(os.path.join(local_app, rel))))
    else:
        for rel in (
            ".config/google-chrome",
            ".config/chromium",
            ".config/microsoft-edge",
            ".config/BraveSoftware/Brave-Browser",
            "Library/Application Support/Google/Chrome",
        ):
            candidates.append(os.path.normcase(os.path.abspath(os.path.expanduser(os.path.join("~", rel)))))
    return norm in candidates


def _should_prebridge_profile_dir(user_data_dir: Optional[str]) -> bool:
    if not user_data_dir or not os.path.isdir(user_data_dir):
        return False
    return _is_default_chrome_userdata_dir(user_data_dir) or _is_chrome_profile_locked(user_data_dir)


_BRIDGE_SKIP_FILENAMES = {
    "lock",
    "lockfile",
    "singletonlock",
    "singletoncookie",
    "singletonsocket",
    "log",
    "log.old",
    "cookies-journal",
}
_BRIDGE_SKIP_DIRNAMES = {
    "cache",
    "code cache",
    "gpucache",
    "dawngraphitecache",
    "dawnd3dcache",
    "grshadercache",
    "shadercache",
    "crashpad",
    "browsermetrics",
    "component_crx_cache",
    "safebrowsing",
    "sessions",
    "cachestorage",
    "scriptcache",
    "blob_storage",
}

# Serialize short direct-launch checks on shared non-default User Data folders to prevent race conditions
_LAUNCH_HANDOFF_LOCKS: Dict[str, asyncio.Lock] = {}


def _get_launch_handoff_lock(profile_dir: str) -> asyncio.Lock:
    key = os.path.normcase(os.path.abspath(profile_dir))
    lock = _LAUNCH_HANDOFF_LOCKS.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _LAUNCH_HANDOFF_LOCKS[key] = lock
    return lock


def _read_file_bytes_shared_win32(src: str) -> Optional[bytes]:
    """Reads a file on Windows with full FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        import ctypes.wintypes as wintypes

        GENERIC_READ = 0x80000000
        FILE_SHARE_ALL = 0x00000001 | 0x00000002 | 0x00000004
        OPEN_EXISTING = 3
        FILE_ATTRIBUTE_NORMAL = 0x00000080
        INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateFileW.restype = wintypes.HANDLE
        handle = kernel32.CreateFileW(
            str(src),
            GENERIC_READ,
            FILE_SHARE_ALL,
            None,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            None,
        )
        if not handle or handle == INVALID_HANDLE_VALUE:
            return None
        try:
            chunks: List[bytes] = []
            buf_size = 65536
            buf = ctypes.create_string_buffer(buf_size)
            bytes_read = wintypes.DWORD(0)
            while True:
                ok = kernel32.ReadFile(handle, buf, buf_size, ctypes.byref(bytes_read), None)
                if not ok:
                    break
                n = int(bytes_read.value)
                if n <= 0:
                    break
                chunks.append(buf.raw[:n])
            return b"".join(chunks)
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return None


def _copy_file_resilient(src: str, dst: str) -> Tuple[bool, bool]:
    """
    Copies src -> dst safely even if Chrome has the folder open.
    Returns (copied_ok, locked_out_bool).
    """
    import shutil

    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        return True, False
    except PermissionError:
        pass
    except OSError as e:
        if getattr(e, "winerror", 0) not in (32, 33, 5):
            return False, False

    # Try Win32 shared-read handle
    data = _read_file_bytes_shared_win32(src)
    if data is not None:
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(data)
            return True, False
        except Exception:
            pass
    return False, True


def _copy_tree_resilient(src_dir: str, dst_dir: str, status_out: Optional[Dict[str, Any]] = None) -> None:
    """Recursively copies Chrome profile storage subdirectories while skipping locks & caches."""
    if not os.path.isdir(src_dir):
        return
    os.makedirs(dst_dir, exist_ok=True)
    for cur_root, dirnames, filenames in os.walk(src_dir):
        dirnames[:] = [
            d for d in dirnames
            if d.lower() not in _BRIDGE_SKIP_DIRNAMES and not d.lower().startswith("optimization_guide")
        ]
        rel = os.path.relpath(cur_root, src_dir)
        target_root = dst_dir if rel == "." else os.path.join(dst_dir, rel)
        os.makedirs(target_root, exist_ok=True)
        for fn in filenames:
            low = fn.lower()
            if low in _BRIDGE_SKIP_FILENAMES or low.startswith("singleton") or low.endswith(".tmp"):
                continue
            sp = os.path.join(cur_root, fn)
            dp = os.path.join(target_root, fn)
            ok, locked = _copy_file_resilient(sp, dp)
            if status_out is not None and low == "cookies":
                if ok:
                    status_out["cookies_copied"] = True
                elif locked:
                    status_out["cookies_locked"] = True


def _stage_nondefault_chrome_bridge(
    src_user_data: str,
    profile_subdir: Optional[str],
    status_out: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Stages an isolated, non-default Chrome User Data directory when:
      1) Chrome 136+ blocks CDP on the system's default Chrome/Edge/Brave User Data path, OR
      2) Another Chrome window / background Chrome process already holds lockfile on src_user_data.
    Preserves Local State (DPAPI/App-Bound key material) + exact profile cookies & storage for the same chrome.exe binary.
    """
    try:
        prof_name = (profile_subdir or "").strip() or "Default"
        key = hashlib.md5(f"{os.path.abspath(src_user_data)}::{prof_name}".encode("utf-8", errors="ignore")).hexdigest()[:10]
        dst_root = os.path.join(get_base_dir(), "profiles", "_chrome_bridge", f"bridge_{key}")
        os.makedirs(dst_root, exist_ok=True)

        # Ensure Chrome skips first-run wizard in the staged root
        fr_src = os.path.join(src_user_data, "First Run")
        fr_dst = os.path.join(dst_root, "First Run")
        if os.path.isfile(fr_src):
            _copy_file_resilient(fr_src, fr_dst)
        elif not os.path.exists(fr_dst):
            try:
                with open(fr_dst, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception:
                pass

        src_ls = os.path.join(src_user_data, "Local State")
        if os.path.isfile(src_ls):
            _copy_file_resilient(src_ls, os.path.join(dst_root, "Local State"))

        src_prof = os.path.join(src_user_data, prof_name)
        if not os.path.isdir(src_prof) and prof_name == "Default" and os.path.isfile(os.path.join(src_user_data, "Preferences")):
            src_prof = src_user_data
        dst_prof = os.path.join(dst_root, prof_name)
        os.makedirs(dst_prof, exist_ok=True)

        for dname in (
            "Network",
            "Local Storage",
            "Session Storage",
            "IndexedDB",
            "Extension State",
            "Local Extension Settings",
            "Sync Extension Settings",
            "Extensions",
            "Storage",
            "WebStorage",
        ):
            sp = os.path.join(src_prof, dname)
            dp = os.path.join(dst_prof, dname)
            if os.path.isdir(sp):
                _copy_tree_resilient(sp, dp, status_out=status_out)

        for fname in ("Cookies", "Preferences", "Secure Preferences", "Web Data", "Login Data", "Login Data For Account"):
            sp = os.path.join(src_prof, fname)
            if os.path.isfile(sp):
                ok, locked = _copy_file_resilient(sp, os.path.join(dst_prof, fname))
                if status_out is not None and fname == "Cookies":
                    if ok:
                        status_out["cookies_copied"] = True
                    elif locked:
                        status_out["cookies_locked"] = True

        _cleanup_stale_chrome_locks(dst_root)
        _cleanup_stale_chrome_locks(dst_prof)
        return dst_root
    except Exception as e:
        logger.debug(f"Could not stage non-default Chrome bridge: {e}")
        return None


def resolve_chrome_executable_for_account(account_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Resolves shortcut-specific chrome_executable first, then system Google Chrome / Edge / Brave."""
    acc = account_data or {}
    custom_exe = (acc.get("chrome_executable") or "").strip()
    if custom_exe and os.path.isfile(custom_exe):
        return os.path.abspath(custom_exe)
    try:
        from automation.extension_manager import get_system_chrome_executable
        exe = get_system_chrome_executable()
        if exe and os.path.isfile(exe):
            return os.path.abspath(exe)
    except Exception:
        pass
    try:
        from desktop_app.automation.extension_manager import get_system_chrome_executable
        exe = get_system_chrome_executable()
        if exe and os.path.isfile(exe):
            return os.path.abspath(exe)
    except Exception:
        pass
    if os.name == "nt":
        local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser(os.path.join("~", "AppData", "Local"))
        for cand in (
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local_app, "Google", "Chrome", "Application", "chrome.exe"),
        ):
            if os.path.isfile(cand):
                return os.path.abspath(cand)
    return None


async def launch_bot_browser_context(
    playwright: Any,
    account_data: Optional[Dict[str, Any]],
    profile_dir: Optional[str],
    launch_args: List[str],
    ignore_default_args: Optional[List[str]] = None,
    proxy_cfg: Optional[Dict[str, Any]] = None,
    context_kwargs: Optional[Dict[str, Any]] = None,
    log_cb: Optional[Any] = None,
    allow_ephemeral_fallback: bool = True,
) -> Tuple[Any, Optional[Any]]:
    """
    Unified browser launcher across ALL automation bots:
    - Prioritizes the exact Chrome binary from the scanned shortcut (`chrome_executable`) or real system Chrome.
    - Uses exact `profile_dir` (--user-data-dir) and `--profile-directory` so Chrome decrypts & keeps logged-in FB sessions.
    - When `profile_dir` is locked by another open Chrome window/tray process OR is Chrome's default User Data
      directory (blocked by Chrome 136+ CDP), seamlessly stages an isolated Chrome session bridge preserving
      `Local State` + profile cookies/storage with the exact Chrome binary instead of aborting.
    Returns (context, browser_or_None).
    """
    acc = account_data or {}
    is_custom = bool(acc.get("is_custom_chrome_profile", False))
    acc_name = acc.get("name", "Chrome Profile")
    prof_subdir = (acc.get("chrome_profile_directory") or "").strip() or None
    chrome_exe = resolve_chrome_executable_for_account(acc)

    def _log(level: str, msg: str):
        if log_cb:
            try:
                log_cb(level, msg)
            except Exception:
                pass

    ign = list(ignore_default_args or ["--enable-automation", "--disable-extensions"])
    if "--enable-automation" not in ign:
        ign.append("--enable-automation")
    if is_custom and "--disable-extensions" not in ign:
        ign.append("--disable-extensions")

    ctx_opts = dict(context_kwargs or {})
    # Let real Chrome use its own authentic versioned User-Agent for custom profiles so Client Hints match cookies
    if is_custom and chrome_exe:
        ctx_opts.pop("user_agent", None)

    clean_args = strip_maximized_args(list(launch_args or []))
    if prof_subdir and not any(a.lower().startswith("--profile-directory") for a in clean_args):
        clean_args.append(f"--profile-directory={prof_subdir}")

    slot_idx, total_slots, resolved_tile = resolve_tile_context(acc)
    if not any(a.startswith("--window-position=") for a in clean_args):
        clean_args.extend(build_window_chrome_args(tile_rect=resolved_tile, total_slots=total_slots, slot_index=slot_idx))

    # 1. Persistent Context (Direct or Seamless Session Bridge)
    if profile_dir and os.path.isdir(profile_dir):
        handoff_lock = _get_launch_handoff_lock(profile_dir)
        async with handoff_lock:
            target_dir = profile_dir
            bridge_tried = False
            bridge_info: Dict[str, Any] = {}

            is_locked_now = _is_chrome_profile_locked(profile_dir)
            is_default_ud = _is_default_chrome_userdata_dir(profile_dir)

            if is_custom and (is_locked_now or is_default_ud):
                reason = "open in another Chrome window" if is_locked_now else "default system Chrome User Data path"
                _log("INFO", f"🔄 Profile '{acc_name}' shares a {reason}. Staging isolated real-Chrome session bridge...")
                staged = _stage_nondefault_chrome_bridge(profile_dir, prof_subdir, status_out=bridge_info)
                if staged and os.path.isdir(staged):
                    bridge_tried = True
                    target_dir = staged
                    if bridge_info.get("cookies_locked") and not bridge_info.get("cookies_copied"):
                        _log(
                            "WARNING",
                            f"⚠️ Chrome actively holds an exclusive lock on '{acc_name}' Cookies DB; "
                            f"if Facebook asks to log in, close just that Chrome profile window once."
                        )
                elif is_locked_now:
                    raise RuntimeError(
                        f"⚠️ Chrome profile '{acc_name}' is currently OPEN in another Chrome window ({profile_dir}) "
                        f"and session bridge staging failed. Please close Chrome for this profile and retry."
                    )
            else:
                _cleanup_stale_chrome_locks(target_dir)

            # Pre-write Preferences window_placement so Chrome never restores maximized/overlapping bounds
            prepare_profile_tile_placement(target_dir, resolved_tile, profile_subdir=prof_subdir)

            attempts: List[Tuple[str, Optional[str], Optional[str], List[str]]] = []
            if chrome_exe and os.path.isfile(chrome_exe):
                attempts.append(("real_chrome", chrome_exe, None, clean_args))
                minimal_args = [
                    a for a in clean_args
                    if a not in ("--no-sandbox", "--enable-unsafe-extension-debugging", "--disable-dev-shm-usage")
                ]
                if minimal_args != clean_args:
                    attempts.append(("real_chrome_clean", chrome_exe, None, minimal_args))
            else:
                attempts.append(("chrome", None, "chrome", clean_args))
                attempts.append(("msedge", None, "msedge", clean_args))

            if not is_custom:
                attempts.append(("chromium", None, None, clean_args))

            last_err: Optional[Exception] = None

            for label, exe_p, chan, args_try in attempts:
                if _is_chrome_profile_locked(target_dir):
                    if not bridge_tried and is_custom:
                        staged = _stage_nondefault_chrome_bridge(profile_dir, prof_subdir, status_out=bridge_info)
                        if staged and os.path.isdir(staged):
                            bridge_tried = True
                            target_dir = staged
                            prepare_profile_tile_placement(target_dir, resolved_tile, profile_subdir=prof_subdir)
                    if _is_chrome_profile_locked(target_dir):
                        _cleanup_stale_chrome_locks(target_dir)

                kwargs: Dict[str, Any] = {
                    "user_data_dir": target_dir,
                    "headless": False,
                    "args": args_try,
                    "ignore_default_args": ign,
                    **ctx_opts,
                }
                if proxy_cfg:
                    kwargs["proxy"] = proxy_cfg
                if exe_p:
                    kwargs["executable_path"] = exe_p
                elif chan:
                    kwargs["channel"] = chan

                try:
                    ctx = await playwright.chromium.launch_persistent_context(**kwargs)
                    mode_tag = "session bridge" if target_dir != profile_dir else f"profile '{os.path.basename(target_dir)}'"
                    _log("INFO", f"🌐 Launched Desktop Chrome ({os.path.basename(exe_p) if exe_p else (chan or 'Chromium')}) using {mode_tag}.")
                    try:
                        p0 = ctx.pages[0] if ctx.pages else await ctx.new_page()
                        await apply_cdp_window_bounds(ctx, p0, tile_rect=resolved_tile, total_slots=total_slots, slot_index=slot_idx)
                    except Exception:
                        pass
                    return ctx, None
                except Exception as ex:
                    last_err = ex
                    err_low = str(ex).lower()
                    _log("DEBUG", f"Persistent launch ({label}) notice: {str(ex)[:140]}")

                    needs_bridge = any(
                        tok in err_low
                        for tok in (
                            "non-default",
                            "default data directory",
                            "default user data",
                            "lock",
                            "already in use",
                            "profile appears to be in use",
                            "singleton",
                        )
                    )
                    if not bridge_tried and (exe_p or chan in ("chrome", "msedge")) and (needs_bridge or is_custom):
                        bridge_tried = True
                        _log("INFO", f"🔄 Staging isolated real-Chrome session bridge for '{acc_name}'...")
                        bridge_dir = _stage_nondefault_chrome_bridge(profile_dir, prof_subdir, status_out=bridge_info)
                        if bridge_dir and os.path.isdir(bridge_dir):
                            target_dir = bridge_dir
                            prepare_profile_tile_placement(bridge_dir, resolved_tile, profile_subdir=prof_subdir)
                            try:
                                b_kw = dict(kwargs)
                                b_kw["user_data_dir"] = bridge_dir
                                ctx = await playwright.chromium.launch_persistent_context(**b_kw)
                                _log("SUCCESS", f"✅ Launched real Chrome session bridge for '{acc_name}'.")
                                try:
                                    p0 = ctx.pages[0] if ctx.pages else await ctx.new_page()
                                    await apply_cdp_window_bounds(ctx, p0, tile_rect=resolved_tile, total_slots=total_slots, slot_index=slot_idx)
                                except Exception:
                                    pass
                                return ctx, None
                            except Exception as bex:
                                last_err = bex
                                _log("DEBUG", f"Bridge launch notice: {str(bex)[:120]}")

                    _cleanup_stale_chrome_locks(target_dir)

            if is_custom:
                detail = str(last_err)[:180] if last_err else "Chrome failed to open profile."
                raise RuntimeError(
                    f"Could not launch custom Chrome profile '{acc_name}' ({profile_dir}). Details: {detail}"
                )

    elif is_custom:
        raise RuntimeError(
            f"Custom Chrome profile directory missing for '{acc_name}': {profile_dir}"
        )

    # 2. Ephemeral non-custom fallback ONLY when allow_ephemeral_fallback=True and not custom profile
    if not allow_ephemeral_fallback or is_custom:
        raise RuntimeError(f"Persistent browser profile unavailable for '{acc_name}'.")

    launch_kw: Dict[str, Any] = {
        "headless": False,
        "args": clean_args,
        "ignore_default_args": ign,
    }
    if proxy_cfg:
        launch_kw["proxy"] = proxy_cfg
    if chrome_exe and os.path.isfile(chrome_exe):
        launch_kw["executable_path"] = chrome_exe
    try:
        browser = await playwright.chromium.launch(**launch_kw)
    except Exception:
        launch_kw.pop("executable_path", None)
        browser = await playwright.chromium.launch(**launch_kw)
    ctx = await browser.new_context(**ctx_opts)
    return ctx, browser


# ==============================================================================
# 5. Persistence for Per-Page Custom Chrome Paths (Pages 5-9 ONLY)
# ==============================================================================

def _get_custom_chrome_config_file() -> str:
    return os.path.join(get_base_dir(), "config", "custom_chrome_paths.json")


def load_custom_chrome_paths() -> Dict[str, str]:
    """Loads saved custom Chrome folder paths keyed by page key ('groups', 'pages', 'reels', 'friends', 'propic')."""
    cfg_file = _get_custom_chrome_config_file()
    if not os.path.isfile(cfg_file):
        return {}
    try:
        with open(cfg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items() if k in CHROME_PATH_PAGES and v}
    except Exception as e:
        logger.debug(f"Could not load custom chrome paths: {e}")
        return {}


def save_custom_chrome_path(page_key: str, folder_path: Optional[str]) -> Dict[str, str]:
    """Saves or clears custom Chrome folder path for a specific page key."""
    if page_key not in CHROME_PATH_PAGES:
        return load_custom_chrome_paths()
    data = load_custom_chrome_paths()
    if folder_path and str(folder_path).strip():
        data[page_key] = os.path.abspath(str(folder_path).strip())
    else:
        data.pop(page_key, None)

    cfg_file = _get_custom_chrome_config_file()
    os.makedirs(os.path.dirname(cfg_file), exist_ok=True)
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data
