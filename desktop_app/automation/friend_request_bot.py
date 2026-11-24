"""
FB Auto Bot - Facebook Friend Request Engine (Auto Accept & Auto Reject)
Handles high-volume friend request processing across accounts with auto-scroll,
real-time counter, configurable delays, and automatic browser cleanup.
"""

import os
import sys
import json
import random
import socket
import asyncio
import logging
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Callable

try:
    from automation.browser_window_manager import (
        resolve_tile_context,
        build_window_chrome_args,
        apply_cdp_window_bounds,
        launch_bot_browser_context,
        get_bot_working_page,
        human_move_and_click,
        human_click_coords,
        human_smooth_scroll,
        human_pause,
        human_session_warmup,
        human_idle_drift,
    )
except ImportError:
    try:
        from desktop_app.automation.browser_window_manager import (
            resolve_tile_context,
            build_window_chrome_args,
            apply_cdp_window_bounds,
            launch_bot_browser_context,
            get_bot_working_page,
            human_move_and_click,
            human_click_coords,
            human_smooth_scroll,
            human_pause,
            human_session_warmup,
            human_idle_drift,
        )
    except ImportError:
        def resolve_tile_context(account_data=None, window_slot=None, total_window_slots=None, tile_rect=None):
            return 0, 1, (0, 0, 1920, 1080)
        def build_window_chrome_args(tile_rect=None, total_slots=1, slot_index=0, profile_directory=None, apply_scale_factor=True):
            return []
        async def apply_cdp_window_bounds(context, page=None, tile_rect=None, total_slots=1, slot_index=0):
            return False
        async def get_bot_working_page(context):
            return context.pages[0] if getattr(context, "pages", None) else await context.new_page()
        launch_bot_browser_context = None
        async def human_move_and_click(page, locator, hover_pause=True, force_fallback=True):
            try:
                await locator.click(timeout=4000)
                return True
            except Exception:
                return False
        async def human_click_coords(page, x, y, hover_pause=True):
            try:
                await page.mouse.click(x, y)
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

logger = logging.getLogger("FBAutoBot.FriendRequestBot")

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    Browser = None
    BrowserContext = None
    Page = None
    class PlaywrightTimeoutError(Exception):
        pass


def test_proxy_connectivity(host: str, port: int, timeout: float = 2.0) -> bool:
    """Quick socket probe to verify proxy server is alive before passing to Chrome."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except Exception:
        return False


def parse_cookie_payload(raw_cookies: str) -> List[Dict[str, Any]]:
    """
    Parses both JSON array cookie exports and raw semicolon string formats
    (e.g., 'c_user=1000...; xs=2%3A...; datr=...').
    Returns a list of standardized cookies suitable for Playwright.
    """
    cleaned = (raw_cookies or "").strip()
    if not cleaned:
        return []

    # Format 1: JSON Array
    if cleaned.startswith("[") and cleaned.endswith("]"):
        try:
            items = json.loads(cleaned)
            formatted = []
            for item in items:
                cookie = {
                    "name": str(item.get("name", "")),
                    "value": str(item.get("value", "")),
                    "domain": item.get("domain", ".facebook.com"),
                    "path": item.get("path", "/"),
                }
                if not cookie["domain"].startswith("."):
                    cookie["domain"] = "." + cookie["domain"]
                if "sameSite" in item and item["sameSite"] in ["Strict", "Lax", "None"]:
                    cookie["sameSite"] = item["sameSite"]
                if "secure" in item:
                    cookie["secure"] = bool(item["secure"])
                if cookie["name"]:
                    formatted.append(cookie)
            return formatted
        except json.JSONDecodeError:
            pass

    # Format 2: Semicolon key=value string
    formatted = []
    pairs = cleaned.split(";")
    for pair in pairs:
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        key, val = pair.split("=", 1)
        key = key.strip()
        val = val.strip()
        if key:
            formatted.append({
                "name": key,
                "value": val,
                "domain": ".facebook.com",
                "path": "/",
                "secure": True
            })
    return formatted


class FacebookFriendRequestBot:
    """
    Automates accepting or rejecting pending Facebook friend requests for an account.
    Opens Chrome, navigates to facebook.com/friends/requests, iterates through requests,
    scrolls dynamically to load 500+ items, and closes the browser cleanly when finished.
    """

    def __init__(
        self,
        account_data: Dict[str, Any],
        mode: str = "accept",  # "accept", "reject", or "send"
        max_requests: int = 0, # 0 = unlimited / all pending
        click_delay: float = 0.8,
        target_urls: Optional[List[str]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        counter_callback: Optional[Callable[[str, int], None]] = None
    ):
        self.account_data = account_data
        self.mode = mode.lower().strip() or "accept"
        self.max_requests = max_requests
        self.click_delay = max(0.2, click_delay)
        self.target_urls = list(target_urls or [])
        self.log_cb = log_callback
        self.prog_cb = progress_callback
        self.counter_cb = counter_callback

        self.account_id = account_data.get("id", "unknown")
        self.account_name = account_data.get("name", "Facebook Account")

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._cancelled = False
        self.processed_count = 0

    def log(self, level: str, message: str):
        full_msg = f"[{self.account_name}] {message}"
        if self.log_cb:
            self.log_cb(level, full_msg)
        else:
            print(f"[{level}] {full_msg}")

    def cancel(self):
        self._cancelled = True
        self.log("WARNING", "Stop signal received. Terminating automation...")

    async def _init_browser(self):
        """Initializes Chrome instance with stealth flags, window tiling, and cookie/profile session."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed in the environment.")

        self.playwright = await async_playwright().start()

        slot_idx, total_slots, tile_rect = resolve_tile_context(self.account_data)
        chrome_profile_directory = (self.account_data.get("chrome_profile_directory") or "").strip() or None
        is_custom_profile = bool(self.account_data.get("is_custom_chrome_profile", False))

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-notifications",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-default-apps",
            "--disable-popup-blocking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--lang=en-US",
        ]
        launch_args.extend(
            build_window_chrome_args(
                tile_rect=tile_rect,
                total_slots=total_slots,
                slot_index=slot_idx,
                profile_directory=chrome_profile_directory,
            )
        )

        # Proxy handling
        proxy_cfg = None
        use_direct = (
            self.account_data.get("network_mode") == "direct"
            or self.account_data.get("use_direct_network", False)
        )
        raw_proxy = (self.account_data.get("proxy") or "").strip()
        is_direct_str = any(d in raw_proxy.lower() for d in ["direct", "no proxy", "none", "null", "false", "0", ""])

        if use_direct or is_direct_str or not raw_proxy:
            proxy_cfg = None
            launch_args.append("--no-proxy-server")
            self.log("INFO", "🌐 Direct internet connection enabled (Proxy bypassed).")
        else:
            try:
                server_url = raw_proxy if "://" in raw_proxy else f"{self.account_data.get('proxy_type', 'http').lower()}://{raw_proxy}"
                parsed = urlparse(server_url)
                host = parsed.hostname
                port = parsed.port
                if host and port and test_proxy_connectivity(host, port, timeout=2.0):
                    proxy_cfg = {"server": f"{parsed.scheme}://{host}:{port}"}
                    u = parsed.username or self.account_data.get("proxy_user")
                    p = parsed.password or self.account_data.get("proxy_pass")
                    if u:
                        proxy_cfg["username"] = u
                    if p:
                        proxy_cfg["password"] = p
                    self.log("SUCCESS", f"🛡️ Assigned proxy ({host}:{port}) is LIVE.")
                else:
                    self.log("WARNING", "⚠️ Proxy offline or unassigned. Falling back to direct connection.")
                    proxy_cfg = None
                    launch_args.append("--no-proxy-server")
            except Exception:
                proxy_cfg = None
                launch_args.append("--no-proxy-server")

        profile_dir = self.account_data.get("profile_dir", "")
        context_kwargs: Dict[str, Any] = {
            "viewport": None,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "locale": "en-US"
        }

        self.context, self.browser = await launch_bot_browser_context(
            playwright=self.playwright,
            account_data=self.account_data,
            profile_dir=profile_dir,
            launch_args=launch_args,
            ignore_default_args=["--enable-automation", "--disable-extensions"],
            proxy_cfg=proxy_cfg,
            context_kwargs=context_kwargs,
            log_cb=self.log,
            allow_ephemeral_fallback=not is_custom_profile,
        )

        if self.context:
            p0 = self.context.pages[0] if self.context.pages else await self.context.new_page()
            await apply_cdp_window_bounds(
                self.context,
                p0,
                tile_rect=tile_rect,
                total_slots=total_slots,
                slot_index=slot_idx,
            )

        # Inject session cookies (preserve existing session when using custom Chrome profile)
        raw_cookies = self.account_data.get("cookies", "")
        if raw_cookies and self.context:
            try:
                formatted = []
                if isinstance(raw_cookies, str):
                    formatted = parse_cookie_payload(raw_cookies)
                elif isinstance(raw_cookies, list):
                    for item in raw_cookies:
                        if isinstance(item, dict) and "name" in item and "value" in item:
                            formatted.append({
                                "name": str(item["name"]),
                                "value": str(item["value"]),
                                "domain": str(item.get("domain", ".facebook.com")),
                                "path": str(item.get("path", "/")),
                                "secure": bool(item.get("secure", True))
                            })
                        elif isinstance(item, str):
                            formatted.extend(parse_cookie_payload(item))
                if formatted:
                    await self.context.add_cookies(formatted)
                    self.log("SUCCESS", f"🔑 Injected {len(formatted)} Facebook cookies. Session active.")
            except Exception as e:
                self.log("DEBUG", f"Cookie injection notice: {e}")
        elif is_custom_profile:
            self.log("INFO", "📂 Using existing Chrome profile login session directly.")

        # Open working tab (never overwrite restored user tabs) & enforce tiled grid bounds
        self.page = await get_bot_working_page(self.context)

        await apply_cdp_window_bounds(
            self.context,
            self.page,
            tile_rect=tile_rect,
            total_slots=total_slots,
            slot_index=slot_idx,
        )

    async def _run_send_requests(self) -> Dict[str, Any]:
        """
        Navigates to each target Facebook Profile or Page URL:
        - On Profiles: clicks 'Add Friend' (and confirms any modal)
        - On Pages (or profiles without Add Friend): automatically clicks 'Follow' (or fallback 'More -> Follow' / header 'Like')
        - Skips already-requested / already-following / already-friends targets cleanly
        """
        self.log("INFO", f"🚀 Starting Outbound Friend Request / Page Follow sender for {len(self.target_urls)} target URL(s)...")
        self.processed_count = 0
        sent_friends = 0
        followed_pages = 0

        try:
            await self._init_browser()
            if self._cancelled or not self.page:
                return {"success": False, "count": 0, "message": "Cancelled"}

            # Verify session login
            try:
                await self.page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=45000)
                slot_idx, total_slots, tile_rect = resolve_tile_context(self.account_data)
                await apply_cdp_window_bounds(
                    self.context,
                    self.page,
                    tile_rect=tile_rect,
                    total_slots=total_slots,
                    slot_index=slot_idx,
                )
                await asyncio.sleep(2.0)
            except Exception:
                pass

            curr_url = self.page.url.lower()
            if "login" in curr_url or "checkpoint" in curr_url:
                self.log("ERROR", "❌ Account requires login or updated cookies in Accounts Manager.")
                return {"success": False, "count": 0, "message": "Account not logged in"}

            await human_session_warmup(self.page, duration_range=(1.1, 2.0))

            for idx, raw_target_url in enumerate(self.target_urls, start=1):
                if self._cancelled:
                    break
                if self.max_requests > 0 and self.processed_count >= self.max_requests:
                    self.log("INFO", f"🎯 Target limit ({self.max_requests}) reached.")
                    break

                target_url = raw_target_url.strip()
                if not target_url.startswith("http"):
                    target_url = "https://" + target_url

                self.log("INFO", f"[{idx}/{len(self.target_urls)}] Navigating to target: {target_url}")
                try:
                    await self.page.goto(target_url, wait_until="domcontentloaded", timeout=40000)
                    await human_pause(1.8, 2.8)
                    await human_smooth_scroll(self.page, total_delta_y=random.randint(90, 180), steps=3)
                    await human_pause(0.45, 0.95)
                except Exception as ex:
                    self.log("WARNING", f"Could not load {target_url}: {ex}")
                    continue

                if self._cancelled:
                    break

                # Inspect visible header/profile action buttons cleanly (excluding feed posts & global nav)
                header_state = {}
                try:
                    header_state = await self.page.evaluate("""() => {
                        const pendingWords = ['cancel request', 'request sent', 'requested', 'درخواست منسوخ کریں', 'solicitud enviada', 'invitation envoyée'];
                        const followingWords = ['following', 'followed', 'فالو کر رہے ہیں', 'siguiendo', 'seguindo', 'abonné', 'suivi', 'abonniert', 'mengikuti', 'đang theo dõi'];
                        const friendsWords = ['friends', 'friend', 'دوست'];
                        const btns = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"], a[role="button"]'));
                        let hasPending = false;
                        let hasFollowing = false;
                        let hasFriends = false;
                        for (const b of btns) {
                            if (!b.offsetParent && b.offsetWidth === 0 && b.offsetHeight === 0) continue;
                            if (b.closest('[role="banner"], [role="navigation"], [role="article"]')) continue;
                            const r = b.getBoundingClientRect();
                            if (r.top < 0 || r.top > 780) continue;
                            const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                            const aria = (b.getAttribute('aria-label') || '').trim().toLowerCase();
                            if (!txt && !aria) continue;
                            if (txt.includes('follower') || aria.includes('follower')) continue;
                            if (pendingWords.some(w => txt === w || aria === w || txt.includes(w))) hasPending = true;
                            if (followingWords.some(w => txt === w || aria === w)) hasFollowing = true;
                            if (friendsWords.some(w => txt === w || aria === w)) hasFriends = true;
                        }
                        return { hasPending, hasFollowing, hasFriends };
                    }""")
                except Exception:
                    header_state = {}

                if header_state.get("hasPending"):
                    self.log("INFO", f"ℹ️ Friend request already pending for {target_url}. Skipping.")
                    continue

                # 1. Try 'Add friend' (Facebook Profile target)
                clicked_action = None  # "friend" or "follow"
                add_selectors = [
                    'div[aria-label="Add friend"][role="button"]',
                    'div[aria-label="Add Friend"][role="button"]',
                    'div[aria-label*="Add friend" i][role="button"]',
                    'button:has-text("Add friend")',
                    'div[role="button"]:has-text("Add friend")',
                    'button:has-text("Add Friend")',
                    'div[role="button"]:has-text("Add Friend")',
                    'div[aria-label="دوست بنائیں"][role="button"]',
                    'div[aria-label*="Añadir a amigos" i]',
                    'div[aria-label*="Ajouter" i]',
                    'div[aria-label*="Freund hinzufügen" i]',
                    'div[aria-label*="Adicionar" i][role="button"]'
                ]

                for sel in add_selectors:
                    try:
                        btn = self.page.locator(sel).first
                        if await btn.count() > 0 and await btn.is_visible():
                            txt = ((await btn.inner_text()) or "").strip().lower()
                            if len(txt) <= 32 and "cancel" not in txt:
                                if await human_move_and_click(self.page, btn):
                                    clicked_action = "friend"
                                    break
                    except Exception:
                        pass

                # DOM coordinate locate for 'Add friend'
                if not clicked_action:
                    try:
                        coords = await self.page.evaluate("""() => {
                            const keywords = [
                                'add friend', 'دوست بنائیں', 'añadir a amigos', 'ajouter',
                                'freund hinzufügen', 'adicionar aos amigos', 'aggiungi agli amici',
                                'tambah teman', 'thêm bạn bè'
                            ];
                            const btns = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"], a[role="button"]'));
                            for (const b of btns) {
                                if (!b.offsetParent && b.offsetWidth === 0 && b.offsetHeight === 0) continue;
                                if (b.closest('[role="banner"], [role="navigation"], [role="article"]')) continue;
                                const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                                const aria = (b.getAttribute('aria-label') || '').trim().toLowerCase();
                                if (txt.length > 35 || txt.includes('cancel')) continue;
                                if (keywords.some(k => txt === k || txt.startsWith(k) || aria === k || aria.startsWith(k))) {
                                    b.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                    const r = b.getBoundingClientRect();
                                    if (r.width > 4 && r.height > 4) {
                                        return { found: true, x: r.left + r.width * 0.5, y: r.top + r.height * 0.5 };
                                    }
                                }
                            }
                            return { found: false };
                        }""")
                        if coords and coords.get("found"):
                            await asyncio.sleep(random.uniform(0.25, 0.45))
                            if await human_click_coords(self.page, coords["x"], coords["y"]):
                                clicked_action = "friend"
                    except Exception:
                        pass

                # 2. If not a profile with 'Add friend', check if it's a Facebook Page (Auto-Follow / Like)
                if not clicked_action:
                    if header_state.get("hasFollowing"):
                        self.log("INFO", f"ℹ️ Already Following page/profile: {target_url}. Skipping.")
                        continue

                    # Look for 'Follow' button in header / action bar
                    follow_selectors = [
                        'div[aria-label="Follow"][role="button"]',
                        'div[aria-label="Follow page" i][role="button"]',
                        'div[aria-label="Follow Page" i][role="button"]',
                        'div[role="button"]:has-text("Follow")',
                        'button:has-text("Follow")',
                        'div[aria-label="Suivre"][role="button"]',
                        'div[aria-label="Seguir"][role="button"]',
                        'div[aria-label="Folgen"][role="button"]',
                        'div[aria-label="Segui"][role="button"]',
                        'div[aria-label="Ikuti"][role="button"]',
                        'div[aria-label="فالو کریں"][role="button"]',
                    ]
                    for fsel in follow_selectors:
                        try:
                            btns = self.page.locator(fsel)
                            cnt = min(await btns.count(), 8)
                            for b_i in range(cnt):
                                fbtn = btns.nth(b_i)
                                if not await fbtn.is_visible():
                                    continue
                                txt = ((await fbtn.inner_text()) or "").strip().lower()
                                aria = ((await fbtn.get_attribute("aria-label")) or "").strip().lower()
                                if any(bad in txt or bad in aria for bad in ("following", "follower", "unfollow", "stopped")):
                                    continue
                                if txt in ("follow", "follow page", "suivre", "seguir", "folgen", "segui", "ikuti", "فالو کریں", "متابعة", "theo dõi") or aria in ("follow", "follow page", "suivre", "seguir", "folgen", "segui", "ikuti"):
                                    box = await fbtn.bounding_box()
                                    if box and box.get("y", 9999) < 820:
                                        if await human_move_and_click(self.page, fbtn):
                                            clicked_action = "follow"
                                            break
                            if clicked_action:
                                break
                        except Exception:
                            pass

                    # JS DOM scan for Follow button near profile/page header
                    if not clicked_action:
                        try:
                            f_coords = await self.page.evaluate("""() => {
                                const followWords = [
                                    'follow', 'follow page', 'suivre', 'seguir', 'folgen', 'segui',
                                    'ikuti', 'فالو کریں', 'متابعة', 'theo dõi'
                                ];
                                const excludeWords = ['following', 'followers', 'follower', 'unfollow', 'suivi', 'seguindo', 'siguiendo'];
                                const btns = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"], a[role="button"]'));
                                for (const b of btns) {
                                    if (!b.offsetParent && b.offsetWidth === 0 && b.offsetHeight === 0) continue;
                                    if (b.closest('[role="banner"], [role="navigation"], [role="article"]')) continue;
                                    const r = b.getBoundingClientRect();
                                    if (r.top < 0 || r.top > 820 || r.width < 10 || r.height < 10) continue;
                                    const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                                    const aria = (b.getAttribute('aria-label') || '').trim().toLowerCase();
                                    if (excludeWords.some(ex => txt.includes(ex) || aria.includes(ex))) continue;
                                    if (followWords.some(k => txt === k || aria === k || aria.startsWith(k + ' '))) {
                                        b.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                        const nr = b.getBoundingClientRect();
                                        return { found: true, x: nr.left + nr.width * 0.5, y: nr.top + nr.height * 0.5 };
                                    }
                                }
                                return { found: false };
                            }""")
                            if f_coords and f_coords.get("found"):
                                await asyncio.sleep(random.uniform(0.22, 0.42))
                                if await human_click_coords(self.page, f_coords["x"], f_coords["y"]):
                                    clicked_action = "follow"
                        except Exception:
                            pass

                    # Try '...' (More options) menu on Facebook Pages that place Follow inside More dropdown
                    if not clicked_action:
                        try:
                            more_clicked = await self.page.evaluate("""() => {
                                const btns = Array.from(document.querySelectorAll('div[role="button"], button'));
                                for (const b of btns) {
                                    if (!b.offsetParent && b.offsetWidth === 0) continue;
                                    if (b.closest('[role="banner"], [role="navigation"], [role="article"]')) continue;
                                    const r = b.getBoundingClientRect();
                                    if (r.top < 150 || r.top > 750) continue;
                                    const aria = (b.getAttribute('aria-label') || '').trim().toLowerCase();
                                    if (aria === 'more' || aria === 'more options' || aria.includes('see options') || aria.includes('profile settings') || aria.includes('action options')) {
                                        b.click();
                                        return true;
                                    }
                                }
                                return false;
                            }""")
                            if more_clicked:
                                await asyncio.sleep(0.85)
                                menu_follow = self.page.locator(
                                    'div[role="menu"] div[role="menuitem"]:has-text("Follow"), '
                                    'div[role="menu"] span:has-text("Follow"), '
                                    'div[role="dialog"] div[role="menuitem"]:has-text("Follow")'
                                ).first
                                if await menu_follow.count() > 0 and await menu_follow.is_visible():
                                    m_txt = ((await menu_follow.inner_text()) or "").strip().lower()
                                    if "unfollow" not in m_txt and "following" not in m_txt:
                                        if await human_move_and_click(self.page, menu_follow):
                                            clicked_action = "follow"
                        except Exception:
                            pass

                    # Final Page fallback: Page header 'Like' button (on Classic Pages where Like = Follow)
                    if not clicked_action:
                        try:
                            like_coords = await self.page.evaluate("""() => {
                                const likeWords = ['like', "j'aime", 'curtir', 'me gusta', 'gefällt mir', 'mi piace', 'پسند کریں', 'أعجبني'];
                                const btns = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"]'));
                                for (const b of btns) {
                                    if (!b.offsetParent && b.offsetWidth === 0 && b.offsetHeight === 0) continue;
                                    if (b.closest('[role="banner"], [role="navigation"], [role="article"]')) continue;
                                    const r = b.getBoundingClientRect();
                                    if (r.top < 120 || r.top > 720 || r.width < 15 || r.height < 15) continue;
                                    const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                                    const aria = (b.getAttribute('aria-label') || '').trim().toLowerCase();
                                    if (likeWords.some(k => txt === k || aria === k)) {
                                        if (b.getAttribute('aria-pressed') === 'true') continue;
                                        b.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                        const nr = b.getBoundingClientRect();
                                        return { found: true, x: nr.left + nr.width * 0.5, y: nr.top + nr.height * 0.5 };
                                    }
                                }
                                return { found: false };
                            }""")
                            if like_coords and like_coords.get("found"):
                                await asyncio.sleep(random.uniform(0.22, 0.42))
                                if await human_click_coords(self.page, like_coords["x"], like_coords["y"]):
                                    clicked_action = "follow"
                        except Exception:
                            pass

                if clicked_action == "friend":
                    self.processed_count += 1
                    sent_friends += 1
                    self.log("SUCCESS", f"✅ Sent Friend Request to: {target_url} ({self.processed_count}/{len(self.target_urls)})")
                    if self.counter_cb:
                        self.counter_cb(self.account_id, self.processed_count)

                    # Handle any confirmation popup (e.g. "Do you know this person?")
                    await asyncio.sleep(random.uniform(0.85, 1.35))
                    try:
                        confirm_loc = self.page.locator(
                            'div[role="dialog"] button:has-text("Send request"), '
                            'div[role="dialog"] div[role="button"]:has-text("Send request"), '
                            'div[role="dialog"] button:has-text("Confirm"), '
                            'div[role="dialog"] div[role="button"]:has-text("Confirm")'
                        ).first
                        if await confirm_loc.count() > 0 and await confirm_loc.is_visible():
                            await human_move_and_click(self.page, confirm_loc)
                    except Exception:
                        pass
                elif clicked_action == "follow":
                    self.processed_count += 1
                    followed_pages += 1
                    self.log("SUCCESS", f"✅ Followed Facebook Page: {target_url} ({self.processed_count}/{len(self.target_urls)})")
                    if self.counter_cb:
                        self.counter_cb(self.account_id, self.processed_count)
                    await asyncio.sleep(random.uniform(0.7, 1.2))
                else:
                    if header_state.get("hasFriends"):
                        self.log("INFO", f"ℹ️ Already Friends with: {target_url}. Skipping.")
                    else:
                        self.log("WARNING", f"⚠️ Neither 'Add friend' nor 'Follow' button was available on: {target_url}")

                # Natural jittered delay & periodic idle drift between outbound requests
                if self.processed_count > 0 and self.processed_count % 5 == 0:
                    await human_idle_drift(self.page)
                await asyncio.sleep(max(0.4, self.click_delay + random.uniform(-0.1, 0.45)))

            self.log("SUCCESS", f"✨ Finished! Friend requests sent: {sent_friends} | Pages followed: {followed_pages} (Total: {self.processed_count}).")
            return {
                "success": True,
                "count": self.processed_count,
                "friend_requests": sent_friends,
                "page_follows": followed_pages,
                "message": f"Successfully processed {self.processed_count} targets ({sent_friends} friend requests, {followed_pages} page follows)"
            }

        except Exception as e:
            self.log("ERROR", f"Error in send requests: {str(e)}")
            return {"success": False, "count": self.processed_count, "message": str(e)}

        finally:
            self.log("INFO", f"Closing Chrome browser cleanly for {self.account_name}...")
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
            self.log("INFO", f"🔒 Chrome closed for {self.account_name}.")

    async def run(self) -> Dict[str, Any]:
        """
        Main execution flow:
        1. If mode == 'send', sends friend requests to profiles / follows pages in target_urls
        2. If mode == 'accept' or 'reject'/'delete', loops through incoming requests
        3. Closes browser when all requests are processed or max reached
        """
        if self.mode == "send":
            return await self._run_send_requests()

        is_accept = (self.mode == "accept")
        action_verb = "Accepting" if is_accept else "Deleting/Rejecting"
        self.log("INFO", f"🚀 Starting Auto Friend Request {action_verb} engine...")
        self.processed_count = 0

        try:
            await self._init_browser()
            if self._cancelled or not self.page:
                return {"success": False, "count": 0, "message": "Cancelled before start"}

            requests_url = "https://www.facebook.com/friends/requests"
            self.log("INFO", f"Navigating to {requests_url} ...")

            try:
                await self.page.goto(requests_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(3.0)
            except Exception as e:
                self.log("WARNING", f"Initial navigation notice: {e}. Retrying...")
                await asyncio.sleep(2.0)
                await self.page.goto(requests_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(3.0)

            # Check if redirected to login
            curr_url = self.page.url.lower()
            if "login" in curr_url or "checkpoint" in curr_url:
                self.log("ERROR", "❌ Account requires manual login or valid cookies in Account Manager.")
                return {"success": False, "count": 0, "message": "Account not logged in"}

            self.log("SUCCESS", "✅ Facebook Friend Requests page loaded. Scanning incoming requests...")
            await human_session_warmup(self.page, duration_range=(1.0, 1.9))

            consecutive_empty_scrolls = 0
            max_empty_scrolls = 6

            while not self._cancelled:
                # If a cap is specified
                if self.max_requests > 0 and self.processed_count >= self.max_requests:
                    self.log("INFO", f"🎯 Target limit of {self.max_requests} requests reached.")
                    break

                # Locate visible candidate button cleanly on REAL incoming friend request cards
                # (explicitly skips "People You May Know" suggestion cards with "Add friend" + "Remove")
                mode_name = "accept" if is_accept else "reject"
                find_and_scroll_script = """
                (mode) => {
                    const acceptKeywords = ["confirm", "accept", "تصدیق", "ایکسیپٹ", "aceptar", "confirmer", "bestätigen", "confirmar"];
                    const deleteKeywords = ["delete", "delete request", "reject", "حذف", "ریجیکٹ", "eliminar", "supprimer", "löschen", "excluir", "recusar", "rejeitar"];
                    const addFriendWords = ["add friend", "دوست بنائیں", "añadir a amigos", "ajouter", "freund hinzufügen", "adicionar"];

                    function cardContainsAddFriend(el) {
                        let p = el.parentElement;
                        for (let i = 0; i < 4 && p; i++) {
                            const btns = p.querySelectorAll('button, div[role="button"], span[role="button"]');
                            if (btns.length >= 2 && btns.length <= 6) {
                                const labels = Array.from(btns).map(b => (b.innerText || b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase());
                                if (labels.some(l => addFriendWords.some(af => l === af || l.startsWith(af)))) {
                                    return true; // People You May Know card
                                }
                                if (mode !== 'accept') {
                                    // Verify confirm/accept sibling exists if text is generic 'remove'
                                    return { isPYMK: false, hasConfirmSibling: labels.some(l => acceptKeywords.some(ak => l === ak || l.startsWith(ak))) };
                                }
                            }
                            p = p.parentElement;
                        }
                        return { isPYMK: false, hasConfirmSibling: false };
                    }

                    const elements = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"], a[role="button"]'));
                    for (const el of elements) {
                        if (!el.offsetParent && el.offsetWidth === 0 && el.offsetHeight === 0) continue;
                        if (el.getAttribute('aria-disabled') === 'true' || el.disabled) continue;
                        if (el.getAttribute('data-bot-clicked') === 'true') continue;
                        if (el.closest('[role="banner"], header')) continue;

                        const parentCard = el.closest('div[role="listitem"], div[role="article"], div[data-visualcompletion="ignore-dynamic-extra-display"], div[role="main"], div[role="navigation"]');
                        if (!parentCard) continue;

                        const text = (el.innerText || el.textContent || '').trim().toLowerCase();
                        const aria = (el.getAttribute('aria-label') || '').trim().toLowerCase();
                        if (!text && !aria) continue;
                        if (text.length > 32) continue;

                        const cardInfo = cardContainsAddFriend(el);
                        if (cardInfo === true || (cardInfo && cardInfo.isPYMK)) continue;

                        let matched = false;
                        if (mode === "accept") {
                            matched = acceptKeywords.some(k => text === k || text.startsWith(k) || aria === k);
                        } else {
                            if (deleteKeywords.some(k => text === k || text.startsWith(k) || aria === k || aria.startsWith(k + ' '))) {
                                matched = true;
                            } else if ((text === 'remove' || text === 'remover' || text === 'rimuovi') && cardInfo && cardInfo.hasConfirmSibling) {
                                matched = true;
                            }
                        }

                        if (matched) {
                            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 4 && rect.height > 4) {
                                el.setAttribute('data-bot-clicked', 'true');
                                return { found: true, text: text || aria, x: rect.left + rect.width * 0.5, y: rect.top + rect.height * 0.5 };
                            }
                        }
                    }
                    return { found: false };
                }
                """

                eval_res = await self.page.evaluate(find_and_scroll_script, mode_name)

                if eval_res and eval_res.get("found"):
                    await asyncio.sleep(random.uniform(0.18, 0.36))
                    # Re-read bounding box after smooth scroll settles
                    rect_now = await self.page.evaluate("""() => {
                        const els = Array.from(document.querySelectorAll('[data-bot-clicked="true"]'));
                        for (let i = els.length - 1; i >= 0; i--) {
                            const r = els[i].getBoundingClientRect();
                            if (r.width > 4 && r.height > 4 && r.top >= 0 && r.bottom <= window.innerHeight + 40) {
                                return {
                                    x: r.left + r.width * (0.35 + Math.random() * 0.3),
                                    y: r.top + r.height * (0.35 + Math.random() * 0.3)
                                };
                            }
                        }
                        return null;
                    }""")
                    tx = rect_now["x"] if rect_now else eval_res["x"]
                    ty = rect_now["y"] if rect_now else eval_res["y"]

                    success_click = await human_click_coords(self.page, tx, ty, hover_pause=True)
                    if success_click:
                        self.processed_count += 1
                        consecutive_empty_scrolls = 0

                        # If Facebook pops a delete confirmation modal, confirm it cleanly
                        if not is_accept:
                            await asyncio.sleep(0.3)
                            try:
                                del_confirm = self.page.locator(
                                    'div[role="dialog"] button:has-text("Delete"), '
                                    'div[role="dialog"] div[role="button"]:has-text("Delete"), '
                                    'div[role="dialog"] button:has-text("Confirm"), '
                                    'div[role="dialog"] div[role="button"]:has-text("Confirm")'
                                ).first
                                if await del_confirm.count() > 0 and await del_confirm.is_visible():
                                    await human_move_and_click(self.page, del_confirm, hover_pause=False)
                            except Exception:
                                pass

                        action_label = "✅ Accepted" if is_accept else "🗑️ Deleted/Rejected"
                        self.log("INFO", f"{action_label} request #{self.processed_count} successfully.")

                        if self.counter_cb:
                            self.counter_cb(self.account_id, self.processed_count)

                        if self.processed_count % random.randint(6, 9) == 0:
                            await human_idle_drift(self.page)

                        jittered_delay = max(0.4, self.click_delay + random.uniform(-0.1, 0.38))
                        await asyncio.sleep(jittered_delay)
                        continue

                # Smoothly scroll both sidebar request list and main viewport to reveal more requests
                await self.page.evaluate("""async () => {
                    const candidates = Array.from(document.querySelectorAll('div[role="navigation"], div[role="main"], div[tabindex="-1"], div'));
                    for (const c of candidates) {
                        if (c.scrollHeight > c.clientHeight && c.clientHeight > 250) {
                            const step = 120;
                            for (let s = 0; s < 4; s++) {
                                c.scrollTop += step;
                                await new Promise(r => setTimeout(r, 45));
                            }
                        }
                    }
                }""")
                await human_smooth_scroll(self.page, total_delta_y=520, steps=5)
                await asyncio.sleep(random.uniform(1.3, 2.0))

                # Check again without marking if any new incoming request buttons rendered after scroll
                has_more = await self.page.evaluate("""(mode) => {
                    const acceptKeywords = ["confirm", "accept", "تصدیق", "ایکسیپٹ", "aceptar", "confirmer", "bestätigen", "confirmar"];
                    const deleteKeywords = ["delete", "delete request", "reject", "حذف", "ریجیکٹ", "eliminar", "supprimer", "löschen", "excluir", "recusar", "rejeitar"];
                    const addFriendWords = ["add friend", "دوست بنائیں", "añadir a amigos", "ajouter", "freund hinzufügen", "adicionar"];
                    const elements = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"], a[role="button"]'));
                    for (const el of elements) {
                        if (!el.offsetParent && el.offsetWidth === 0 && el.offsetHeight === 0) continue;
                        if (el.getAttribute('aria-disabled') === 'true' || el.disabled) continue;
                        if (el.getAttribute('data-bot-clicked') === 'true') continue;
                        if (el.closest('[role="banner"], header')) continue;
                        const parentCard = el.closest('div[role="listitem"], div[role="article"], div[data-visualcompletion="ignore-dynamic-extra-display"], div[role="main"], div[role="navigation"]');
                        if (!parentCard) continue;
                        let isPYMK = false;
                        let hasConfirmSibling = false;
                        let p = el.parentElement;
                        for (let i = 0; i < 4 && p; i++) {
                            const btns = p.querySelectorAll('button, div[role="button"], span[role="button"]');
                            if (btns.length >= 2 && btns.length <= 6) {
                                const labels = Array.from(btns).map(b => (b.innerText || b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase());
                                if (labels.some(l => addFriendWords.some(af => l === af || l.startsWith(af)))) { isPYMK = true; break; }
                                hasConfirmSibling = labels.some(l => acceptKeywords.some(ak => l === ak || l.startsWith(ak)));
                                break;
                            }
                            p = p.parentElement;
                        }
                        if (isPYMK) continue;
                        const text = (el.innerText || el.textContent || '').trim().toLowerCase();
                        const aria = (el.getAttribute('aria-label') || '').trim().toLowerCase();
                        if (text.length > 32) continue;
                        if (mode === "accept") {
                            if (acceptKeywords.some(k => text === k || text.startsWith(k) || aria === k)) return true;
                        } else {
                            if (deleteKeywords.some(k => text === k || text.startsWith(k) || aria === k)) return true;
                            if ((text === 'remove' || text === 'remover' || text === 'rimuovi') && hasConfirmSibling) return true;
                        }
                    }
                    return false;
                }""", mode_name)

                if not has_more:
                    consecutive_empty_scrolls += 1
                    self.log("DEBUG", f"Scanning for more requests... (Scroll check {consecutive_empty_scrolls}/{max_empty_scrolls})")
                    if consecutive_empty_scrolls >= max_empty_scrolls:
                        self.log("SUCCESS", "🎉 No more pending friend requests found. All available incoming requests have been processed!")
                        break
                else:
                    consecutive_empty_scrolls = 0

            # Wrap up
            final_verb = "accepted" if is_accept else "deleted/rejected"
            self.log("SUCCESS", f"✨ Finished! Total friend requests {final_verb}: {self.processed_count}.")
            return {
                "success": True,
                "count": self.processed_count,
                "message": f"Successfully {final_verb} {self.processed_count} requests"
            }

        except Exception as e:
            self.log("ERROR", f"Error during friend request automation: {str(e)}")
            return {"success": False, "count": self.processed_count, "message": str(e)}

        finally:
            # Cleanly close Chrome browser as requested
            self.log("INFO", f"Closing Chrome browser cleanly for {self.account_name}...")
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
            self.log("INFO", f"🔒 Chrome closed for {self.account_name}.")
