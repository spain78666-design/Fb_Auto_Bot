"""
FB Auto Bot - Facebook Marketplace Renew & Delete All Listings Engine
Automates bulk listing renewal (Marketplace -> Selling -> Seller dashboard -> To renew)
and bulk listing deletion (Marketplace -> Selling -> Your listings -> ... -> Delete listing)
with full support for Accounts Manager sessions and Custom Chrome Profiles.
"""

import os
import re
import json
import math
import time
import asyncio
import random
from typing import Dict, Any, Optional, Callable, List

try:
    from playwright.async_api import async_playwright, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    Page = None
    BrowserContext = None

try:
    from playwright_stealth import stealth_async
    HAS_PLAYWRIGHT_STEALTH = True
except ImportError:
    HAS_PLAYWRIGHT_STEALTH = False

try:
    from automation.browser_window_manager import (
        resolve_tile_context,
        apply_cdp_window_bounds,
        launch_bot_browser_context,
        human_click_element,
        human_move_and_click,
        human_click_coords,
        human_type_text,
        human_smooth_scroll,
        human_pause,
        human_session_warmup,
        human_idle_drift,
    )
except ImportError:
    try:
        from desktop_app.automation.browser_window_manager import (
            resolve_tile_context,
            apply_cdp_window_bounds,
            launch_bot_browser_context,
            human_click_element,
            human_move_and_click,
            human_click_coords,
            human_type_text,
            human_smooth_scroll,
            human_pause,
            human_session_warmup,
            human_idle_drift,
        )
    except ImportError:
        def resolve_tile_context(account_data=None, window_slot=None, total_window_slots=None, tile_rect=None):
            return 0, 1, (0, 0, 1920, 1080)

        async def apply_cdp_window_bounds(context, page=None, tile_rect=None, total_slots=1, slot_index=0):
            return False

        async def launch_bot_browser_context(*args, **kwargs):
            raise RuntimeError("browser_window_manager module is required.")

        async def human_click_element(page, target, hover_pause=True, force_fallback=True):
            try:
                await target.click(timeout=4000)
                return True
            except Exception:
                return False

        async def human_move_and_click(page, locator, hover_pause=True, force_fallback=True):
            return await human_click_element(page, locator, hover_pause=hover_pause, force_fallback=force_fallback)

        async def human_click_coords(page, x, y, hover_pause=True):
            try:
                await page.mouse.click(x, y)
                return True
            except Exception:
                return False

        async def human_type_text(page, target, text, clear_first=True, allow_typos=False):
            try:
                await target.fill(text)
                return True
            except Exception:
                return False

        async def human_smooth_scroll(page, total_delta_y=550, steps=6):
            await page.evaluate("(d) => window.scrollBy(0, d)", total_delta_y)

        async def human_pause(low=0.55, high=1.45, mult=1.0):
            await asyncio.sleep(random.uniform(low, high) * mult)

        async def human_session_warmup(page, duration_range=(1.2, 2.3), log_cb=None):
            await asyncio.sleep(1.0)

        async def human_idle_drift(page):
            await asyncio.sleep(0.25)


def parse_cookie_string(raw_cookies: str) -> List[Dict[str, Any]]:
    """Parses JSON or semicolon-separated Facebook cookie payloads for Playwright context."""
    raw = (raw_cookies or "").strip()
    if not raw:
        return []

    formatted: List[Dict[str, Any]] = []
    if raw.startswith("[") or raw.startswith("{"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                parsed = parsed.get("cookies", []) or [parsed]
            if isinstance(parsed, list):
                for item in parsed:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name", "")).strip()
                    value = str(item.get("value", "")).strip()
                    if not name:
                        continue
                    domain = str(item.get("domain") or ".facebook.com").strip()
                    path = str(item.get("path") or "/").strip()
                    c_dict: Dict[str, Any] = {
                        "name": name,
                        "value": value,
                        "domain": domain,
                        "path": path,
                        "secure": bool(item.get("secure", True)),
                        "httpOnly": bool(item.get("httpOnly", False)),
                    }
                    ss = str(item.get("sameSite", "None")).capitalize()
                    if ss in ("Strict", "Lax", "None"):
                        c_dict["sameSite"] = ss
                    formatted.append(c_dict)
                return formatted
        except Exception:
            pass

    for part in raw.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k:
            formatted.append({
                "name": k,
                "value": v,
                "domain": ".facebook.com",
                "path": "/",
                "secure": True,
            })
    return formatted


def parse_proxy_config(account_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Builds Playwright proxy config when network_mode == 'proxy' and proxy details exist."""
    if (account_data.get("network_mode") or "direct").strip().lower() != "proxy":
        return None
    raw = (account_data.get("proxy") or "").strip()
    if not raw or "direct" in raw.lower():
        return None

    proto = (account_data.get("proxy_type") or "HTTP").strip().lower()
    if proto not in ("http", "https", "socks5", "socks4"):
        proto = "http"

    p_user = (account_data.get("proxy_user") or "").strip()
    p_pass = (account_data.get("proxy_pass") or "").strip()

    if "://" in raw:
        server = raw
    else:
        parts = raw.split(":")
        if len(parts) == 4 and not p_user:
            host, port, p_user, p_pass = parts
            server = f"{proto}://{host}:{port}"
        elif len(parts) >= 2:
            server = f"{proto}://{parts[0]}:{parts[1]}"
        else:
            server = f"{proto}://{raw}"

    cfg: Dict[str, str] = {"server": server}
    if p_user:
        cfg["username"] = p_user
    if p_pass:
        cfg["password"] = p_pass
    return cfg


class FacebookRenewDeleteBot:
    """
    Enterprise Playwright controller for Facebook Marketplace listing maintenance:
      - action='renew': Opens Marketplace -> Selling -> Seller dashboard -> To renew
        -> clicks all available 'Renew' buttons inside the modal popup.
      - action='delete': Opens Marketplace -> Selling -> Your listings
        -> clicks '...' menu -> 'Delete listing' -> confirms deletion dialog
        -> repeats & re-verifies after refresh until clean.
    """

    def __init__(
        self,
        account_data: Dict[str, Any],
        action_delay: float = 1.5,
        max_limit: int = 0,
        reverify_before_close: bool = True,
        log_callback: Optional[Callable[[str, str], None]] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        counter_callback: Optional[Callable[[str, int], None]] = None,
    ):
        self.account_data = dict(account_data or {})
        self.account_name = (self.account_data.get("name") or "Account").strip()
        self.account_id = str(self.account_data.get("id") or self.account_name)
        self.is_custom_profile = bool(self.account_data.get("is_custom_chrome_profile", False))
        self.action_delay = max(0.5, float(action_delay or 1.5))
        self.max_limit = max(0, int(max_limit or 0))
        self.reverify_before_close = bool(reverify_before_close)

        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.counter_callback = counter_callback

        self.playwright = None
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._cancelled = False
        self._mouse_pos = (480.0, 320.0)
        self.processed_count = 0

    def log(self, level: str, message: str):
        prefix = f"[{self.account_name}] "
        if self.log_callback:
            try:
                self.log_callback(level, f"{prefix}{message}")
            except Exception:
                pass

    def set_progress(self, val: int):
        if self.progress_callback:
            try:
                self.progress_callback(max(0, min(100, int(val))))
            except Exception:
                pass

    def emit_counter(self, count: int):
        self.processed_count = int(count)
        if self.counter_callback:
            try:
                self.counter_callback(self.account_id, self.processed_count)
            except Exception:
                pass

    def cancel(self):
        self._cancelled = True

    async def close(self):
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        self.context = None
        self.browser = None
        self.page = None
        self.playwright = None

    async def _human_sleep(self, low: Optional[float] = None, high: Optional[float] = None):
        if self._cancelled:
            return
        lo = low if low is not None else max(0.45, self.action_delay * 0.75)
        hi = high if high is not None else max(lo + 0.25, self.action_delay * 1.25)
        await asyncio.sleep(random.uniform(lo, hi))

    async def _human_move_and_click(self, locator) -> bool:
        """Scrolls element into view and moves cursor with curved Bezier cadence before clicking."""
        if self._cancelled or not self.page:
            return False
        return await human_move_and_click(self.page, locator)

    async def _dismiss_light_overlays(self):
        """Closes common non-blocking cookie/notification prompts if visible."""
        if not self.page:
            return
        for sel in [
            'div[role="dialog"] button:has-text("Allow all cookies")',
            'div[role="dialog"] button:has-text("Decline optional cookies")',
            'div[role="dialog"] [aria-label="Close"]',
            'div[role="dialog"] button:has-text("Not Now")',
        ]:
            try:
                btn = self.page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    # Never dismiss our target Renew listings or Delete listing dialogs!
                    dlg_text = ""
                    try:
                        dlg_text = (await self.page.locator('div[role="dialog"]').first.inner_text(timeout=800)).lower()
                    except Exception:
                        pass
                    if "renew listings" in dlg_text or "delete listing" in dlg_text:
                        return
                    await human_move_and_click(self.page, btn, hover_pause=False)
                    await human_pause(0.35, 0.65)
            except Exception:
                pass

    async def _init_browser(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright library is missing. Cannot launch Chrome.")

        self.playwright = await async_playwright().start()

        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        )
        profile_dir = (self.account_data.get("profile_dir") or "").strip() or None
        if profile_dir:
            os.makedirs(profile_dir, exist_ok=True)

        proxy_cfg = parse_proxy_config(self.account_data)
        if proxy_cfg:
            self.log("INFO", f"🌐 Proxy routing enabled: {proxy_cfg['server']}")

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-default-browser-check",
            "--no-first-run",
            "--disable-dev-shm-usage",
            "--disable-notifications",
            "--password-store=basic",
            "--lang=en-US,en",
        ]
        ctx_kwargs: Dict[str, Any] = {
            "user_agent": ua,
            "no_viewport": True,
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["notifications"],
        }

        self.context, self.browser = await launch_bot_browser_context(
            self.playwright,
            account_data=self.account_data,
            profile_dir=profile_dir,
            proxy_cfg=proxy_cfg,
            launch_args=launch_args,
            ignore_default_args=["--enable-automation", "--disable-extensions"],
            context_kwargs=ctx_kwargs,
            log_cb=lambda lvl, msg: self.log(lvl, msg),
        )

        # Inject cookies when provided (Accounts Manager accounts)
        raw_cookies = (self.account_data.get("cookies") or "").strip()
        if raw_cookies and not self.is_custom_profile:
            parsed = parse_cookie_string(raw_cookies)
            parsed.append({
                "name": "locale",
                "value": "en_US",
                "domain": ".facebook.com",
                "path": "/",
                "secure": True,
            })
            if parsed:
                try:
                    await self.context.add_cookies(parsed)
                    self.log("INFO", f"🔑 Loaded {len(parsed)} session cookies into Chrome.")
                except Exception as ce:
                    self.log("WARNING", f"Cookie injection notice: {str(ce)[:80]}")
        elif self.is_custom_profile:
            self.log("INFO", f"🗂️ Using live Chrome profile session: {os.path.basename(profile_dir or '')}")

        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        if HAS_PLAYWRIGHT_STEALTH:
            try:
                await stealth_async(self.page)
            except Exception:
                pass

    async def _navigate_to_marketplace_and_verify(self) -> bool:
        """Navigates to Facebook Marketplace, applies tiled window bounds, and verifies logged-in session."""
        if not self.page:
            return False

        self.log("INFO", "🌐 Opening Facebook Marketplace...")
        try:
            await self.page.goto("https://www.facebook.com/marketplace/", wait_until="domcontentloaded", timeout=45000)
        except Exception as nav_err:
            self.log("WARNING", f"Initial navigation notice: {str(nav_err)[:80]}")
            await self.page.goto("https://www.facebook.com/marketplace/", wait_until="commit", timeout=35000)

        slot_idx, total_slots, tile_rect = resolve_tile_context(self.account_data)
        await apply_cdp_window_bounds(
            self.context,
            self.page,
            tile_rect=tile_rect,
            total_slots=total_slots,
            slot_index=slot_idx,
        )
        await self._human_sleep(1.5, 2.3)

        curr_url = (self.page.url or "").lower()
        if "checkpoint" in curr_url or "suspended" in curr_url:
            self.log("ERROR", "⚠️ Facebook Security Checkpoint or restriction detected! Skipping this account.")
            return False

        if "/login" in curr_url or "login.php" in curr_url:
            # Attempt credential login if stored
            email = (self.account_data.get("uid") or self.account_data.get("email") or "").strip()
            pwd = (self.account_data.get("password") or "").strip()
            if email and pwd:
                self.log("INFO", "🔑 Login screen detected; attempting saved credentials...")
                try:
                    e_loc = self.page.locator('input#email, input[name="email"]').first
                    p_loc = self.page.locator('input#pass, input[name="pass"]').first
                    l_loc = self.page.locator('button[name="login"], button[type="submit"]').first
                    if await e_loc.count() > 0:
                        await human_type_text(self.page, e_loc, email, clear_first=True, allow_typos=False)
                    if await p_loc.count() > 0:
                        await human_type_text(self.page, p_loc, pwd, clear_first=True, allow_typos=False)
                    if await l_loc.count() > 0:
                        await human_move_and_click(self.page, l_loc)
                    else:
                        await self.page.keyboard.press("Enter")
                    await human_pause(3.8, 5.2)
                    await self.page.goto("https://www.facebook.com/marketplace/", wait_until="domcontentloaded", timeout=35000)
                    await human_pause(1.5, 2.3)
                except Exception:
                    pass

            curr_url = (self.page.url or "").lower()
            if "/login" in curr_url or "login.php" in curr_url:
                self.log("ERROR", "❌ Facebook session is not logged in! Please refresh cookies or Chrome profile session.")
                return False

        await self._dismiss_light_overlays()
        await human_session_warmup(self.page, duration_range=(1.1, 2.0))
        return True

    async def _go_to_selling(self) -> bool:
        """Clicks 'Selling' in Marketplace sidebar or navigates directly to /marketplace/you/selling."""
        if not self.page or self._cancelled:
            return False

        self.log("INFO", "📂 Opening Marketplace -> Selling...")
        clicked = False
        for sel in [
            'a[href*="/marketplace/you/selling"]',
            'a:has-text("Selling")',
            '[role="link"]:has-text("Selling")',
            'span:text-is("Selling")',
        ]:
            try:
                loc = self.page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    if await self._human_move_and_click(loc):
                        clicked = True
                        break
            except Exception:
                continue

        if clicked:
            await self._human_sleep(1.6, 2.4)

        if "/marketplace/you" not in (self.page.url or "").lower():
            try:
                await self.page.goto(
                    "https://www.facebook.com/marketplace/you/selling",
                    wait_until="domcontentloaded",
                    timeout=40000,
                )
                await self._human_sleep(1.6, 2.3)
            except Exception as ex:
                self.log("ERROR", f"Failed to open Selling section: {ex}")
                return False

        return True

    # ==========================================================================
    # Action 1: Renew All Listings
    # ==========================================================================
    async def _open_seller_dashboard_and_renew_modal(self) -> str:
        """
        Navigates to Seller dashboard and clicks the 'To renew' card.
        Waits cleanly for the 'Renew listings' modal AND its inner listing rows/buttons to hydrate.
        Returns:
          'modal_open'    -> 'Renew listings' popup modal is open & ready
          'none_to_renew' -> 0 listings eligible to renew
          'failed'        -> Could not open dashboard/modal
        """
        if not self.page or self._cancelled:
            return "failed"

        self.log("INFO", "📊 Opening Seller dashboard...")
        clicked_dash = False
        for sel in [
            'a[href*="/marketplace/you/dashboard"]',
            '[role="link"]:has-text("Seller dashboard")',
            'a:has-text("Seller dashboard")',
            'span:text-is("Seller dashboard")',
        ]:
            try:
                loc = self.page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    if await self._human_move_and_click(loc):
                        clicked_dash = True
                        break
            except Exception:
                continue

        if clicked_dash:
            await self._human_sleep(1.5, 2.3)

        if "/marketplace/you/dashboard" not in (self.page.url or "").lower():
            try:
                await self.page.goto(
                    "https://www.facebook.com/marketplace/you/dashboard",
                    wait_until="domcontentloaded",
                    timeout=40000,
                )
                await self._human_sleep(1.8, 2.6)
            except Exception as ex:
                self.log("ERROR", f"Could not open Seller dashboard: {ex}")
                return "failed"

        self.log("INFO", "🔎 Looking for 'To renew' card in Seller dashboard...")
        # Wait briefly if Seller dashboard cards are still loading
        clicked_to_renew = False
        for _dash_wait in range(8):
            if self._cancelled:
                return "failed"
            for sel in [
                'a[href*="renew"]',
                'div[role="button"]:has-text("To renew")',
                'a:has-text("To renew")',
                '[role="link"]:has-text("To renew")',
                'span:text-is("To renew")',
            ]:
                try:
                    loc = self.page.locator(sel).first
                    if await loc.count() > 0 and await loc.is_visible():
                        if await self._human_move_and_click(loc):
                            clicked_to_renew = True
                            break
                except Exception:
                    continue
            if clicked_to_renew:
                break

            try:
                tr_coords = await self.page.evaluate("""() => {
                    const spans = Array.from(document.querySelectorAll('span, div, a'));
                    for (const el of spans) {
                        const txt = (el.innerText || '').trim();
                        if (/^to renew$/i.test(txt)) {
                            const target = el.closest('a, [role="button"], [role="link"]') || el;
                            target.scrollIntoView({block: 'center', behavior: 'smooth'});
                            const r = target.getBoundingClientRect();
                            if (r.width > 6 && r.height > 6) {
                                return { found: true, x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 };
                            }
                        }
                    }
                    return { found: false };
                }""")
                if tr_coords and tr_coords.get("found"):
                    await asyncio.sleep(random.uniform(0.25, 0.45))
                    clicked_to_renew = await human_click_coords(self.page, tr_coords["x"], tr_coords["y"])
                    if clicked_to_renew:
                        break
            except Exception:
                pass
            await asyncio.sleep(0.6)

        if not clicked_to_renew:
            # Check if '0 To renew' is explicitly shown without modal
            try:
                zero_check = await self.page.evaluate("""() => {
                    const text = (document.body.innerText || '');
                    return /0\\s*\\n*\\s*To renew/i.test(text) || /To renew\\s*\\n*\\s*0/i.test(text);
                }""")
                if zero_check:
                    return "none_to_renew"
            except Exception:
                pass
            self.log("WARNING", "Could not find 'To renew' card on Seller dashboard.")
            return "failed"

        await human_pause(1.3, 2.0)

        # Wait up to ~14s for the 'Renew listings' modal AND its Renew buttons / empty state to finish loading
        idle_open_polls = 0
        for _ in range(28):
            if self._cancelled:
                return "failed"
            probe = await self.page.evaluate("""() => {
                const dialogs = Array.from(document.querySelectorAll('div[role="dialog"]')).filter(d => {
                    const r = d.getBoundingClientRect();
                    return r.width > 200 && r.height > 110;
                });
                let dlg = null;
                for (let i = dialogs.length - 1; i >= 0; i--) {
                    const t = (dialogs[i].innerText || '').toLowerCase();
                    if (t.includes('renew') || t.includes('eligible')) {
                        dlg = dialogs[i];
                        break;
                    }
                }
                if (!dlg) return { state: 'waiting', btns: 0, loading: false };

                const txt = (dlg.innerText || '').toLowerCase();
                const loading = Boolean(dlg.querySelector('[role="progressbar"], [aria-busy="true"]'));

                const btns = Array.from(dlg.querySelectorAll('button, div[role="button"], span[role="button"], a[role="button"]'));
                let renewCount = 0;
                for (const b of btns) {
                    const label = (b.innerText || b.getAttribute('aria-label') || '').trim();
                    if (/^renew(\\s+(this\\s+)?listing)?$/i.test(label)) {
                        const ariaDis = (b.getAttribute('aria-disabled') || '').toLowerCase() === 'true';
                        if (!b.disabled && !ariaDis) {
                            const r = b.getBoundingClientRect();
                            if (r.width > 12 && r.height > 12) renewCount++;
                        }
                    }
                }

                if (renewCount > 0) return { state: 'ready', btns: renewCount, loading };
                if (!loading && (
                    txt.includes('no more listings eligible') ||
                    txt.includes('no listings to renew') ||
                    txt.includes('no eligible listings') ||
                    txt.includes('all caught up') ||
                    txt.includes('no listings available to renew')
                )) {
                    return { state: 'none', btns: 0, loading };
                }
                return { state: 'open_hydrating', btns: 0, loading };
            }""")
            st = (probe or {}).get("state", "waiting")
            if st == "ready":
                await human_pause(0.5, 0.9)
                return "modal_open"
            if st == "none":
                return "none_to_renew"
            if st == "open_hydrating":
                if not probe.get("loading"):
                    idle_open_polls += 1
                    if idle_open_polls >= 6:
                        return "modal_open"
                else:
                    idle_open_polls = 0
            await asyncio.sleep(0.5)

        try:
            zero_check = await self.page.evaluate("""() => {
                const text = (document.body.innerText || '');
                return /0\\s*\\n*\\s*To renew/i.test(text) || /To renew\\s*\\n*\\s*0/i.test(text);
            }""")
            if zero_check:
                return "none_to_renew"
        except Exception:
            pass

        return "failed"

    async def _run_renew_listings(self) -> Dict[str, Any]:
        self.log("INFO", "🔄 Starting Renew All Listings workflow...")
        self.set_progress(15)

        if not await self._go_to_selling():
            return {"success": False, "count": 0, "message": "Could not open Marketplace Selling."}

        self.set_progress(30)
        modal_state = await self._open_seller_dashboard_and_renew_modal()
        if modal_state == "none_to_renew":
            self.log("SUCCESS", "✅ 0 listings are eligible to renew on this account (already up-to-date).")
            self.emit_counter(0)
            self.set_progress(100)
            return {"success": True, "count": 0, "message": "No listings eligible to renew."}
        if modal_state != "modal_open":
            return {"success": False, "count": 0, "message": "Could not open 'Renew listings' popup modal."}

        self.log("INFO", "🖱️ Clicking eligible 'Renew' buttons inside Renew listings modal...")
        renewed = 0
        no_btn_scrolls = 0
        bottom_confirm_scrolls = 0
        loading_waits = 0

        while not self._cancelled:
            if self.max_limit > 0 and renewed >= self.max_limit:
                self.log("INFO", f"🎯 Reached configured limit ({self.max_limit} listing(s) renewed).")
                break

            target_info = await self.page.evaluate("""() => {
                const dialogs = Array.from(document.querySelectorAll('div[role="dialog"]')).filter(d => {
                    const r = d.getBoundingClientRect();
                    return r.width > 200 && r.height > 110;
                });
                let dlg = null;
                for (let i = dialogs.length - 1; i >= 0; i--) {
                    const t = (dialogs[i].innerText || '').toLowerCase();
                    if (t.includes('renew') || t.includes('eligible')) { dlg = dialogs[i]; break; }
                }
                if (!dlg) return { status: 'no_dialog' };

                const dlgText = (dlg.innerText || '').toLowerCase();
                const isLoading = Boolean(dlg.querySelector('[role="progressbar"], [aria-busy="true"]'));

                const scrollers = [dlg, ...Array.from(dlg.querySelectorAll('div'))].filter(el => {
                    const cs = window.getComputedStyle(el);
                    return el.scrollHeight > el.clientHeight + 16 && el.clientHeight > 80 &&
                           (cs.overflowY === 'auto' || cs.overflowY === 'scroll' || el === dlg);
                });
                scrollers.sort((a, b) => b.clientHeight - a.clientHeight);
                const scroller = scrollers.length > 0 ? scrollers[0] : null;

                const btns = Array.from(dlg.querySelectorAll('button, div[role="button"], span[role="button"], a[role="button"]'));
                const dRect = dlg.getBoundingClientRect();

                for (const b of btns) {
                    if (b.getAttribute('data-fbautobot-skip') === '1') continue;
                    const txt = (b.innerText || b.getAttribute('aria-label') || '').trim();
                    if (!/^renew(\\s+(this\\s+)?listing)?$/i.test(txt)) continue;
                    const ariaDis = (b.getAttribute('aria-disabled') || '').toLowerCase() === 'true';
                    const isDis = Boolean(b.disabled) || ariaDis;
                    if (isDis) continue;

                    const cs = window.getComputedStyle(b);
                    if (cs.visibility === 'hidden' || cs.display === 'none') continue;
                    const r = b.getBoundingClientRect();
                    if (r.width < 12 || r.height < 12) continue;

                    // Keep button cleanly inside visible dialog bounds (away from sticky header/footer)
                    b.scrollIntoView({ block: 'center', behavior: 'instant' });
                    const r2 = b.getBoundingClientRect();
                    if (r2.width < 12 || r2.height < 12) continue;
                    if (r2.top < dRect.top + 36 || r2.bottom > dRect.bottom - 20) {
                        if (scroller) {
                            scroller.scrollTop += (r2.top - (dRect.top + dRect.height * 0.45));
                        }
                    }
                    const r3 = b.getBoundingClientRect();
                    window.__fbLastRenewBtn = b;
                    const tries = Number(b.getAttribute('data-fbautobot-tries') || '0') + 1;
                    b.setAttribute('data-fbautobot-tries', String(tries));
                    return {
                        status: 'found',
                        x: r3.left + r3.width / 2,
                        y: r3.top + r3.height / 2,
                        tries,
                        label: txt,
                    };
                }

                if (!isLoading && (
                    dlgText.includes('no more listings eligible') ||
                    dlgText.includes('no listings to renew') ||
                    dlgText.includes('all caught up')
                )) {
                    return { status: 'empty' };
                }

                return {
                    status: isLoading ? 'loading' : 'scroll',
                    hasScroller: Boolean(scroller),
                };
            }""")

            status = (target_info or {}).get("status")
            if status in ("no_dialog", "empty"):
                self.log("SUCCESS", "🎉 All eligible listings in 'Renew listings' modal have been renewed!")
                break

            if status == "found":
                no_btn_scrolls = 0
                bottom_confirm_scrolls = 0
                loading_waits = 0
                tx = float(target_info["x"])
                ty = float(target_info["y"])
                tries = int(target_info.get("tries", 1))
                await asyncio.sleep(random.uniform(0.18, 0.34))
                try:
                    clicked = await human_click_coords(self.page, tx, ty, hover_pause=True)
                    self._mouse_pos = (tx, ty)
                    if not clicked:
                        raise RuntimeError("Mouse click failed")

                    # Deliberate 1.2 - 2.0s pause so Facebook processes the renewal & updates button state
                    wait_lo = max(1.15, self.action_delay * 0.85)
                    wait_hi = max(wait_lo + 0.55, self.action_delay * 1.35)
                    await human_pause(wait_lo, wait_hi)

                    changed = await self.page.evaluate("""() => {
                        const b = window.__fbLastRenewBtn;
                        if (!b) return true;
                        if (!b.isConnected) return true;
                        const ariaDis = (b.getAttribute('aria-disabled') || '').toLowerCase() === 'true';
                        if (b.disabled || ariaDis) return true;
                        const txt = (b.innerText || b.getAttribute('aria-label') || '').trim().toLowerCase();
                        if (!/^renew(\\s+(this\\s+)?listing)?$/i.test(txt)) return true;
                        return false;
                    }""")

                    if changed:
                        renewed += 1
                        self.emit_counter(renewed)
                        self.log("SUCCESS", f"🔄 Renewed listing #{renewed}")
                        if renewed % random.randint(6, 9) == 0:
                            await human_idle_drift(self.page)
                    elif tries >= 2:
                        await self.page.evaluate("""() => {
                            if (window.__fbLastRenewBtn) {
                                window.__fbLastRenewBtn.setAttribute('data-fbautobot-skip', '1');
                            }
                        }""")
                        self.log("WARNING", "Renew button did not confirm after retry; moving to next listing.")
                    else:
                        await human_pause(0.45, 0.85)
                except Exception as click_err:
                    self.log("WARNING", f"Renew click notice: {click_err}")
                    await asyncio.sleep(0.8)
                continue

            if status == "loading":
                loading_waits += 1
                if loading_waits <= 8:
                    await human_pause(0.9, 1.4)
                    continue

            # status == 'scroll': scroll modal container smoothly to load remaining Renew buttons
            no_btn_scrolls += 1
            scroll_res = await self.page.evaluate("""async () => {
                const dialogs = Array.from(document.querySelectorAll('div[role="dialog"]')).filter(d => {
                    const r = d.getBoundingClientRect();
                    return r.width > 200 && r.height > 110;
                });
                const dlg = dialogs.find(d => (d.innerText || '').toLowerCase().includes('renew')) || dialogs[dialogs.length - 1];
                if (!dlg) return { scrolled: false, atBottom: true };
                const scrollers = [dlg, ...Array.from(dlg.querySelectorAll('div'))].filter(el => {
                    return el.scrollHeight > el.clientHeight + 16 && el.clientHeight > 80;
                });
                scrollers.sort((a, b) => b.clientHeight - a.clientHeight);
                if (scrollers.length > 0) {
                    const sc = scrollers[0];
                    const before = sc.scrollTop;
                    const total = Math.max(260, Math.floor(sc.clientHeight * 0.68));
                    const steps = 6;
                    for (let i = 0; i < steps; i++) {
                        sc.scrollTop += total / steps;
                        await new Promise(r => setTimeout(r, 55));
                    }
                    const atBottom = Math.abs(sc.scrollTop - before) < 4 || (sc.scrollTop + sc.clientHeight >= sc.scrollHeight - 8);
                    return { scrolled: Math.abs(sc.scrollTop - before) >= 4, atBottom };
                }
                return { scrolled: false, atBottom: true };
            }""")
            await human_pause(1.0, 1.6)

            if (scroll_res or {}).get("atBottom", True):
                bottom_confirm_scrolls += 1
            else:
                bottom_confirm_scrolls = 0

            if bottom_confirm_scrolls >= 2 and no_btn_scrolls >= 4:
                self.log("INFO", "✅ No more enabled 'Renew' buttons remaining in modal.")
                break
            if no_btn_scrolls >= 10:
                self.log("INFO", "✅ Reached end of Renew listings modal.")
                break

        # Click Done / Close inside dialog
        try:
            done_btn = self.page.locator(
                'div[role="dialog"] [role="button"]:has-text("Done"), '
                'div[role="dialog"] button:has-text("Done"), '
                'div[role="dialog"] [aria-label="Close"]'
            ).first
            if await done_btn.count() > 0 and await done_btn.is_visible():
                await self._human_move_and_click(done_btn)
                await human_pause(0.8, 1.3)
        except Exception:
            pass

        self.set_progress(100)
        return {
            "success": True,
            "count": renewed,
            "message": f"Renewed {renewed} Marketplace listing(s).",
        }

    # ==========================================================================
    # Action 2: Delete All Listings
    # ==========================================================================
    async def _count_raw_listing_cards(self) -> int:
        """Counts visible Marketplace listing cards / '...' action buttons without any skip filtering."""
        if not self.page:
            return 0
        try:
            return int(await self.page.evaluate("""() => {
                const main = document.querySelector('div[role="main"]') || document.body;
                const candidates = Array.from(main.querySelectorAll('div[role="button"], button'));
                let cnt = 0;
                for (const btn of candidates) {
                    const r = btn.getBoundingClientRect();
                    if (r.width < 16 || r.height < 16 || r.width > 100 || r.height > 75) continue;
                    const aria = (btn.getAttribute('aria-label') || '').trim();
                    const hasPopup = (btn.getAttribute('aria-haspopup') || '').toLowerCase() === 'menu';
                    const text = (btn.innerText || '').trim();

                    let card = btn.parentElement;
                    let matchedCard = false;
                    for (let depth = 0; depth < 8 && card && card !== main; depth++) {
                        const ct = (card.innerText || '');
                        const low = ct.toLowerCase();
                        if (
                            low.includes('mark as sold') ||
                            low.includes('mark as pending') ||
                            low.includes('mark as available') ||
                            low.includes('mark as out of stock') ||
                            low.includes('edit listing') ||
                            low.includes('delete and relist') ||
                            low.includes('request review') ||
                            low.includes('needs attention') ||
                            low.includes('relist') ||
                            (low.includes('listed on') && (low.includes('active') || low.includes('pending') || low.includes('out of stock')))
                        ) {
                            if (card.getBoundingClientRect().height < 520) {
                                matchedCard = true;
                                break;
                            }
                        }
                        card = card.parentElement;
                    }
                    const isMoreAria = /more options|more actions|actions for|manage listing|listing options|^more$/i.test(aria);
                    const isThreeDotsButton = hasPopup && (text === '' || text === '...' || text === '⋯');
                    if ((matchedCard && (isMoreAria || isThreeDotsButton || hasPopup)) || (isMoreAria && aria.length > 6)) {
                        cnt++;
                    }
                }
                return cnt;
            }""") or 0)
        except Exception:
            return 0

    async def _find_next_listing_more_button(self, skip_signatures: set) -> Optional[Dict[str, Any]]:
        """
        Finds the '...' (three-dots) menu button on the next visible listing card inside
        Marketplace Selling -> Your listings, scrolls it cleanly into viewport center,
        and returns exact updated viewport coordinates so the click always lands inside view.
        """
        if not self.page:
            return None

        candidate = await self.page.evaluate("""(skipList) => {
            const skipSet = new Set(skipList || []);
            const main = document.querySelector('div[role="main"]') || document.body;
            const candidates = Array.from(main.querySelectorAll('div[role="button"], button'));
            const results = [];

            for (let i = 0; i < candidates.length; i++) {
                const btn = candidates[i];
                const r = btn.getBoundingClientRect();
                if (r.width < 16 || r.height < 16 || r.width > 100 || r.height > 75) continue;

                const cs = window.getComputedStyle(btn);
                if (cs.visibility === 'hidden' || cs.display === 'none') continue;

                const aria = (btn.getAttribute('aria-label') || '').trim();
                const hasPopup = (btn.getAttribute('aria-haspopup') || '').toLowerCase() === 'menu';
                const text = (btn.innerText || '').trim();

                let card = btn.parentElement;
                let cardText = '';
                let matchedCard = false;
                for (let depth = 0; depth < 8 && card && card !== main; depth++) {
                    const ct = (card.innerText || '');
                    const low = ct.toLowerCase();
                    if (
                        low.includes('mark as sold') ||
                        low.includes('mark as pending') ||
                        low.includes('mark as available') ||
                        low.includes('mark as out of stock') ||
                        low.includes('edit listing') ||
                        low.includes('delete and relist') ||
                        low.includes('request review') ||
                        low.includes('needs attention') ||
                        low.includes('relist') ||
                        (low.includes('share') && (low.includes('listed on') || low.includes('active') || low.includes('pending') || low.includes('review')))
                    ) {
                        if (card.getBoundingClientRect().height < 520) {
                            cardText = ct;
                            matchedCard = true;
                            break;
                        }
                    }
                    card = card.parentElement;
                }

                const isMoreAria = /more options|more actions|actions for|manage listing|listing options|^more$/i.test(aria);
                const isThreeDotsButton = hasPopup && (text === '' || text === '...' || text === '⋯');

                if ((matchedCard && (isMoreAria || isThreeDotsButton || hasPopup)) || (isMoreAria && aria.length > 6)) {
                    const sig = (cardText.split('\\n').slice(0, 3).join('|') || aria).trim().slice(0, 140);
                    if (sig && skipSet.has(sig)) continue;
                    results.push({
                        idx: i,
                        top: r.top,
                        sig: sig || ('pos_' + Math.round(r.top)),
                        aria,
                    });
                }
            }

            if (results.length === 0) return null;
            results.sort((a, b) => a.top - b.top);
            const chosen = results[0];
            const el = candidates[chosen.idx];
            el.scrollIntoView({ block: 'center', behavior: 'instant' });
            const r2 = el.getBoundingClientRect();
            window.__fbLastMoreBtn = el;
            return {
                x: r2.left + r2.width / 2,
                y: r2.top + r2.height / 2,
                aria: chosen.aria,
                sig: chosen.sig,
                top: r2.top,
                vh: window.innerHeight || 800,
            };
        }""", list(skip_signatures))

        if not candidate:
            return None

        # Pause briefly for sticky header / reflow, then re-read exact coordinates
        await asyncio.sleep(random.uniform(0.22, 0.38))
        recheck = await self.page.evaluate("""() => {
            const el = window.__fbLastMoreBtn;
            if (!el || !el.isConnected) return null;
            const r = el.getBoundingClientRect();
            if (r.width < 12 || r.height < 12) return null;
            return {
                x: r.left + r.width / 2,
                y: r.top + r.height / 2,
                inView: r.top >= 40 && r.bottom <= (window.innerHeight || 900) - 8,
            };
        }""")
        if recheck:
            candidate["x"] = recheck["x"]
            candidate["y"] = recheck["y"]
        return candidate

    async def _find_delete_menu_item_coords(self, anchor_x: float, anchor_y: float) -> Optional[Dict[str, Any]]:
        """
        Finds the 'Delete listing' / 'Delete' option inside the currently open '...' dropdown popover
        WITHOUT scrolling (scrolling on Facebook Web closes open popover menus!).
        """
        if not self.page:
            return None

        return await self.page.evaluate("""([ax, ay]) => {
            const vh = window.innerHeight || 900;
            const vw = window.innerWidth || 1200;

            const normalize = (s) => (s || '').replace(/\\s+/g, ' ').trim();
            const isDeleteTxt = (t) => {
                const low = t.toLowerCase();
                if (!low || low.length > 42) return 0;
                if (low.includes('relist') || low.includes('mark as') || low.includes('edit') || low.includes('view')) return 0;
                if (/^delete\\s+listing$/i.test(low)) return 3;
                if (/^delete$/i.test(low)) return 2;
                if (low.startsWith('delete listing')) return 2;
                if (/^remove\\s+listing$/i.test(low)) return 1;
                return 0;
            };

            const hits = [];
            const seen = new Set();

            // Search explicit menu items first, then floating overlay clickable rows & spans
            const selectors = [
                'div[role="menuitem"], a[role="menuitem"], div[role="menuitemradio"], div[role="menuitemcheckbox"]',
                'div[role="menu"] [role="button"], div[role="menu"] a, div[role="menu"] button',
                'body > div [role="button"], body > div a, body > div button, body > div span'
            ];

            for (const sel of selectors) {
                const els = Array.from(document.querySelectorAll(sel));
                for (const el of els) {
                    if (seen.has(el)) continue;
                    seen.add(el);

                    // Ignore listing cards inside div[role="main"] unless inside an actual menu container
                    const inMenu = Boolean(el.closest('[role="menu"], [role="menuitem"]'));
                    if (!inMenu && el.closest('div[role="main"]')) continue;

                    const cs = window.getComputedStyle(el);
                    if (cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0') continue;

                    const txt = normalize(el.innerText || el.getAttribute('aria-label') || '');
                    const prio = isDeleteTxt(txt);
                    if (!prio) continue;

                    // If we matched a bare <span>, promote to clickable parent if it's similarly compact
                    let clickEl = el.closest('[role="menuitem"], [role="menuitemradio"], [role="button"], a, button') || el;
                    const cr = clickEl.getBoundingClientRect();
                    if (cr.width < 30 || cr.height < 16 || cr.height > 85) continue;
                    if (cr.bottom < 0 || cr.top > vh || cr.right < 0 || cr.left > vw) continue;

                    const cx = cr.left + cr.width / 2;
                    const cy = cr.top + cr.height / 2;
                    const dist = Math.hypot(cx - ax, cy - ay);
                    hits.push({
                        x: cx,
                        y: cy,
                        text: txt,
                        prio: prio + (inMenu ? 10 : 0),
                        dist,
                    });
                }
            }

            if (hits.length === 0) return null;
            hits.sort((a, b) => (b.prio - a.prio) || (a.dist - b.dist));
            return hits[0];
        }""", [float(anchor_x), float(anchor_y)])

    async def _confirm_delete_dialogs(self) -> bool:
        """Handles 'Delete listing?' confirmation dialog + optional Facebook deletion survey modal."""
        if not self.page:
            return False

        confirmed = False
        # Wait up to ~6.5s for confirmation dialog to appear & render buttons
        for _ in range(18):
            if self._cancelled:
                return False
            btn_pos = await self.page.evaluate("""() => {
                const dialogs = Array.from(document.querySelectorAll('div[role="dialog"]')).filter(d => {
                    const r = d.getBoundingClientRect();
                    return r.width > 180 && r.height > 90;
                });
                const hits = [];
                for (let i = dialogs.length - 1; i >= 0; i--) {
                    const d = dialogs[i];
                    const txt = (d.innerText || '').toLowerCase();
                    if (!txt.includes('delete') && !txt.includes('remove')) continue;
                    const btns = Array.from(d.querySelectorAll('button, div[role="button"], span[role="button"]'));
                    for (const b of btns) {
                        const t = (b.innerText || b.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim();
                        if (/^(delete|delete listing|confirm|yes,?\\s*delete|remove)$/i.test(t)) {
                            const ariaDis = (b.getAttribute('aria-disabled') || '').toLowerCase() === 'true';
                            if (b.disabled || ariaDis) continue;
                            const cs = window.getComputedStyle(b);
                            if (cs.visibility === 'hidden' || cs.display === 'none') continue;
                            const r = b.getBoundingClientRect();
                            if (r.width > 12 && r.height > 12) {
                                hits.push({
                                    x: r.left + r.width / 2,
                                    y: r.top + r.height / 2,
                                    label: t,
                                    rightEdge: r.right,
                                });
                            }
                        }
                    }
                    if (hits.length > 0) {
                        // Prefer rightmost primary confirmation action button
                        hits.sort((a, b) => b.rightEdge - a.rightEdge);
                        return hits[0];
                    }
                }
                return null;
            }""")
            if btn_pos:
                await asyncio.sleep(random.uniform(0.22, 0.42))
                try:
                    if await human_click_coords(self.page, float(btn_pos["x"]), float(btn_pos["y"]), hover_pause=True):
                        confirmed = True
                        break
                except Exception:
                    pass
            await asyncio.sleep(0.36)

        if not confirmed:
            return False

        # Deliberate pause after confirming delete so Facebook completes mutation
        await human_pause(1.1, 1.8)

        # Handle optional follow-up Facebook reason survey modal ("Did you sell it?", "Skip", "No, didn't sell", "Submit")
        for _ in range(4):
            if self._cancelled:
                break
            followup_pos = await self.page.evaluate("""() => {
                const dialogs = Array.from(document.querySelectorAll('div[role="dialog"]')).filter(d => {
                    const r = d.getBoundingClientRect();
                    return r.width > 180 && r.height > 90;
                });
                for (let i = dialogs.length - 1; i >= 0; i--) {
                    const d = dialogs[i];
                    const btns = Array.from(d.querySelectorAll('button, div[role="button"], span[role="button"]'));
                    for (const b of btns) {
                        const t = (b.innerText || b.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim();
                        if (/^(skip|no,?\\s*didn\\'t\\s*sell|rather\\s+not\\s+say|next|submit|done|close)$/i.test(t)) {
                            const ariaDis = (b.getAttribute('aria-disabled') || '').toLowerCase() === 'true';
                            if (b.disabled || ariaDis) continue;
                            const r = b.getBoundingClientRect();
                            if (r.width > 12 && r.height > 12) {
                                return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
                            }
                        }
                    }
                }
                return null;
            }""")
            if not followup_pos:
                break
            try:
                await human_click_coords(self.page, float(followup_pos["x"]), float(followup_pos["y"]), hover_pause=True)
                await human_pause(0.85, 1.35)
            except Exception:
                break

        # Wait briefly for any delete confirmation dialog to finish closing
        for _ in range(6):
            try:
                still_open = await self.page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('div[role="dialog"]')).some(d => {
                        const r = d.getBoundingClientRect();
                        const t = (d.innerText || '').toLowerCase();
                        return r.width > 180 && r.height > 90 && (t.includes('delete listing') || t.includes('deleting'));
                    });
                }""")
                if not still_open:
                    break
            except Exception:
                break
            await asyncio.sleep(0.35)

        return True

    async def _run_delete_listings(self) -> Dict[str, Any]:
        self.log("INFO", "🗑️ Starting Delete All Listings workflow...")
        self.set_progress(15)

        if not await self._go_to_selling():
            return {"success": False, "count": 0, "message": "Could not open Marketplace Selling."}

        # Ensure 'Your listings' view is strictly active (/marketplace/you/selling)
        try:
            your_listings_btn = self.page.locator(
                'a[href*="/marketplace/you/selling"], span:text-is("Your listings")'
            ).first
            if await your_listings_btn.count() > 0 and await your_listings_btn.is_visible():
                await self._human_move_and_click(your_listings_btn)
                await self._human_sleep(1.3, 2.0)
        except Exception:
            pass

        if "/marketplace/you/selling" not in (self.page.url or "").lower():
            try:
                await self.page.goto(
                    "https://www.facebook.com/marketplace/you/selling",
                    wait_until="domcontentloaded",
                    timeout=35000,
                )
                await self._human_sleep(1.5, 2.2)
            except Exception:
                pass

        self.set_progress(30)
        deleted = 0
        skip_signatures = set()
        scroll_misses = 0
        refreshed_verified = False

        while not self._cancelled:
            if self.max_limit > 0 and deleted >= self.max_limit:
                self.log("INFO", f"🎯 Reached configured limit ({self.max_limit} listing(s) deleted).")
                break

            more_btn = await self._find_next_listing_more_button(skip_signatures)
            if not more_btn:
                scroll_misses += 1
                if scroll_misses <= 3:
                    try:
                        await human_smooth_scroll(self.page, total_delta_y=random.randint(420, 620), steps=5)
                    except Exception:
                        pass
                    await human_pause(1.0, 1.5)
                    continue

                if self.reverify_before_close and not refreshed_verified:
                    refreshed_verified = True
                    scroll_misses = 0
                    self.log("INFO", "🔄 Refreshing Your listings page to verify remaining listings...")
                    try:
                        await self.page.reload(wait_until="domcontentloaded", timeout=35000)
                        await self._human_sleep(1.8, 2.6)
                        skip_signatures.clear()
                        continue
                    except Exception:
                        pass

                raw_remaining = await self._count_raw_listing_cards()
                if raw_remaining == 0:
                    self.log("SUCCESS", "✅ Verified: 0 Marketplace listings remain on this account.")
                else:
                    self.log("WARNING", f"⚠️ Finished delete pass ({deleted} deleted), {raw_remaining} listing card(s) still detected.")
                break

            scroll_misses = 0
            sig = more_btn.get("sig", "")
            tx = float(more_btn["x"])
            ty = float(more_btn["y"])

            # Clear any stray open popover first
            try:
                has_stray_menu = await self.page.evaluate(
                    "() => Boolean(document.querySelector('div[role=\"menu\"], div[role=\"menuitem\"]'))"
                )
                if has_stray_menu:
                    await self.page.keyboard.press("Escape")
                    await asyncio.sleep(0.35)
            except Exception:
                pass

            # Step 1: Click '...' menu button via curved human mouse move (retry once if menu lags)
            del_item_pos = None
            for menu_attempt in range(2):
                try:
                    await human_click_coords(self.page, tx, ty, hover_pause=True)
                    self._mouse_pos = (tx, ty)
                except Exception as ex:
                    self.log("WARNING", f"Could not click '...' menu button: {ex}")
                    break

                # Wait 0.9 - 1.3s initially, then poll up to ~2.5s WITHOUT scrolling!
                await human_pause(0.85, 1.25)
                for _poll in range(10):
                    if self._cancelled:
                        break
                    del_item_pos = await self._find_delete_menu_item_coords(tx, ty)
                    if del_item_pos:
                        break
                    await asyncio.sleep(0.25)

                if del_item_pos:
                    break
                # Dismiss and try clicking '...' once more at fresh coordinates
                try:
                    await self.page.keyboard.press("Escape")
                    await asyncio.sleep(0.35)
                except Exception:
                    pass

            if not del_item_pos:
                self.log("WARNING", "Could not find 'Delete listing' inside '...' menu; skipping card.")
                try:
                    await self.page.keyboard.press("Escape")
                except Exception:
                    pass
                if sig:
                    skip_signatures.add(sig)
                await human_pause(0.5, 0.85)
                continue

            # Step 2: Click 'Delete listing' at exact popover coordinates (NEVER scroll while menu is open!)
            try:
                await asyncio.sleep(random.uniform(0.16, 0.30))
                clicked_del_item = await human_click_coords(
                    self.page,
                    float(del_item_pos["x"]),
                    float(del_item_pos["y"]),
                    hover_pause=True,
                )
                if not clicked_del_item:
                    raise RuntimeError("Menu item click failed")
            except Exception:
                if sig:
                    skip_signatures.add(sig)
                continue

            # Wait 0.9 - 1.4s cleanly for confirmation dialog to mount
            await human_pause(0.9, 1.4)

            # Step 3: Confirm deletion modal (+ optional survey)
            confirmed = await self._confirm_delete_dialogs()
            if confirmed:
                deleted += 1
                refreshed_verified = False
                self.emit_counter(deleted)
                self.log("SUCCESS", f"🗑️ Deleted Marketplace listing #{deleted}")
                if deleted % random.randint(5, 8) == 0:
                    await human_idle_drift(self.page)
                await human_pause(max(1.1, self.action_delay * 0.85), max(1.8, self.action_delay * 1.3))
            else:
                self.log("WARNING", "Delete confirmation dialog did not confirm; skipping listing.")
                try:
                    await self.page.keyboard.press("Escape")
                except Exception:
                    pass
                if sig:
                    skip_signatures.add(sig)
                await human_pause(0.6, 1.0)

        self.set_progress(100)
        return {
            "success": True,
            "count": deleted,
            "message": f"Deleted {deleted} Marketplace listing(s).",
        }

    # ==========================================================================
    # Unified Entry Point
    # ==========================================================================
    async def run(self, action: str = "renew") -> Dict[str, Any]:
        """Executes action='renew' or action='delete' and cleanly closes Chrome afterward."""
        act = (action or "renew").strip().lower()
        try:
            self.set_progress(5)
            await self._init_browser()
            if self._cancelled:
                return {"success": False, "count": 0, "message": "Cancelled by user."}

            self.set_progress(12)
            ok = await self._navigate_to_marketplace_and_verify()
            if not ok or self._cancelled:
                return {
                    "success": False,
                    "count": 0,
                    "message": "Session invalid, logged out, or stopped.",
                }

            if act == "delete":
                return await self._run_delete_listings()
            return await self._run_renew_listings()
        except Exception as ex:
            self.log("ERROR", f"❌ Error in Renew/Delete bot ({act}): {str(ex)}")
            return {"success": False, "count": self.processed_count, "message": str(ex)}
        finally:
            self.log("INFO", "🛑 Closing Chrome browser session cleanly...")
            await self.close()
