"""
FB Auto Bot - Facebook Friend Request Engine (Auto Accept & Auto Reject)
Handles high-volume friend request processing across accounts with auto-scroll,
real-time counter, configurable delays, and automatic browser cleanup.
"""

import os
import sys
import json
import socket
import asyncio
import logging
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Callable

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
        mode: str = "accept",  # "accept" or "reject"
        max_requests: int = 0, # 0 = unlimited / all pending
        click_delay: float = 0.8,
        log_callback: Optional[Callable[[str, str], None]] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        counter_callback: Optional[Callable[[str, int], None]] = None
    ):
        self.account_data = account_data
        self.mode = mode.lower().strip() or "accept"
        self.max_requests = max_requests
        self.click_delay = max(0.2, click_delay)
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
        """Initializes Chrome instance with stealth flags and cookie session."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed in the environment.")

        self.playwright = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-notifications",
            "--no-first-run",
            "--disable-default-apps",
            "--disable-popup-blocking",
            "--start-maximized"
        ]

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

        # Chrome executable detection
        chrome_exe = None
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        for c in candidates:
            if os.path.isfile(c):
                chrome_exe = c
                break

        launch_kwargs: Dict[str, Any] = {
            "headless": False,
            "args": launch_args
        }
        if proxy_cfg:
            launch_kwargs["proxy"] = proxy_cfg
        if chrome_exe:
            launch_kwargs["executable_path"] = chrome_exe

        try:
            self.browser = await self.playwright.chromium.launch(**launch_kwargs)
        except Exception as e:
            self.log("WARNING", f"Custom Chrome launch failed: {e}. Trying default Chromium...")
            launch_kwargs.pop("executable_path", None)
            self.browser = await self.playwright.chromium.launch(**launch_kwargs)

        profile_dir = self.account_data.get("profile_dir", "")
        if profile_dir and os.path.isdir(profile_dir):
            try:
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    headless=False,
                    args=launch_args,
                    proxy=proxy_cfg,
                    viewport=None,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                    locale="en-US"
                )
            except Exception:
                self.context = await self.browser.new_context(
                    viewport=None,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                    locale="en-US"
                )
        else:
            self.context = await self.browser.new_context(
                viewport=None,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                locale="en-US"
            )

        # Inject session cookies
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

        # Open page
        pages = self.context.pages
        if pages:
            self.page = pages[0]
        else:
            self.page = await self.context.new_page()

    async def run(self) -> Dict[str, Any]:
        """
        Main execution flow:
        1. Opens Facebook friend requests page
        2. Loops through requests clicking Confirm (Accept) or Delete (Reject)
        3. Auto-scrolls to load all pending items
        4. Closes browser when all requests are processed or max reached
        """
        action_verb = "Accepting" if self.mode == "accept" else "Rejecting"
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

            self.log("SUCCESS", "✅ Facebook Friend Requests page loaded. Scanning for requests...")

            # Selectors based on mode
            if self.mode == "accept":
                target_button_texts = [
                    "Confirm", "Accept", "Confirm request", "ایکسیپٹ", "تصدیق",
                    "Aceptar", "Confirmer", "Bestätigen"
                ]
            else:
                target_button_texts = [
                    "Delete", "Delete request", "Reject", "Remove", "ریجیکٹ", "حذف",
                    "Eliminar", "Supprimer", "Löschen"
                ]

            consecutive_empty_scrolls = 0
            max_empty_scrolls = 5

            while not self._cancelled:
                # If a cap is specified
                if self.max_requests > 0 and self.processed_count >= self.max_requests:
                    self.log("INFO", f"🎯 Target limit of {self.max_requests} requests reached.")
                    break

                # Query all candidate buttons on the page
                clicked_in_round = False

                # We evaluate in JavaScript to locate visible buttons accurately across FB variations
                mode_name = self.mode
                js_script = """
                (mode) => {
                    const acceptKeywords = ["confirm", "accept", "تصدیق", "ایکسیپٹ", "aceptar", "confirmer", "bestätigen"];
                    const rejectKeywords = ["delete", "reject", "remove", "حذف", "ریجیکٹ", "eliminar", "supprimer", "löschen"];
                    const keywords = (mode === "accept") ? acceptKeywords : rejectKeywords;

                    // Collect all clickable elements
                    const elements = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"], a[role="button"]'));
                    
                    for (const el of elements) {
                        // Skip hidden or disabled
                        if (!el.offsetParent && el.offsetWidth === 0 && el.offsetHeight === 0) continue;
                        if (el.getAttribute('aria-disabled') === 'true' || el.disabled) continue;

                        const text = (el.innerText || el.textContent || '').trim().toLowerCase();
                        const aria = (el.getAttribute('aria-label') || '').trim().toLowerCase();
                        
                        const matched = keywords.some(k => text === k || text.startsWith(k) || aria.includes(k));
                        if (matched) {
                            // Check if this button is inside a friend request card
                            // Ensure it's not a generic navbar button
                            const parentCard = el.closest('div[role="listitem"], div[role="article"], div[data-visualcompletion="ignore-dynamic-extra-display"]') || el.parentElement;
                            if (parentCard) {
                                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                return { found: true, text: text || aria };
                            }
                        }
                    }
                    return { found: false };
                }
                """

                eval_res = await self.page.evaluate(js_script, mode_name)

                if eval_res and eval_res.get("found"):
                    # Use locator to click the button
                    btn_text = eval_res.get("text", "")
                    try:
                        # Click via JS or Locator
                        click_script = """
                        (mode) => {
                            const acceptKeywords = ["confirm", "accept", "تصدیق", "ایکسیپٹ", "aceptar", "confirmer", "bestätigen"];
                            const rejectKeywords = ["delete", "reject", "remove", "حذف", "ریجیکٹ", "eliminar", "supprimer", "löschen"];
                            const keywords = (mode === "accept") ? acceptKeywords : rejectKeywords;

                            const elements = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"], a[role="button"]'));
                            for (const el of elements) {
                                if (!el.offsetParent && el.offsetWidth === 0 && el.offsetHeight === 0) continue;
                                if (el.getAttribute('aria-disabled') === 'true' || el.disabled) continue;

                                const text = (el.innerText || el.textContent || '').trim().toLowerCase();
                                const aria = (el.getAttribute('aria-label') || '').trim().toLowerCase();
                                
                                if (keywords.some(k => text === k || text.startsWith(k) || aria.includes(k))) {
                                    el.click();
                                    // Mark element so we don't repeat
                                    el.setAttribute('data-bot-clicked', 'true');
                                    return true;
                                }
                            }
                            return false;
                        }
                        """
                        success_click = await self.page.evaluate(click_script, mode_name)
                        if success_click:
                            self.processed_count += 1
                            clicked_in_round = True
                            consecutive_empty_scrolls = 0

                            action_label = "✅ Accepted" if self.mode == "accept" else "🗑️ Rejected"
                            self.log("INFO", f"{action_label} request #{self.processed_count} successfully.")

                            if self.counter_cb:
                                self.counter_cb(self.account_id, self.processed_count)

                            # Respect user's delay interval
                            await asyncio.sleep(self.click_delay)
                            continue
                    except Exception as e:
                        self.log("DEBUG", f"Click attempt notice: {e}")

                # If no button clicked in current viewport, attempt to scroll down container
                scroll_script = """
                () => {
                    // Scroll both potential containers: left sidebar navigation list and main page
                    let scrolled = false;
                    const candidates = Array.from(document.querySelectorAll('div[role="navigation"], div[role="main"], div[tabindex="-1"], div'));
                    for (const c of candidates) {
                        if (c.scrollHeight > c.clientHeight && c.clientHeight > 250) {
                            c.scrollTop += 500;
                            scrolled = true;
                        }
                    }
                    window.scrollBy(0, 600);
                    return scrolled;
                }
                """
                await self.page.evaluate(scroll_script)
                await asyncio.sleep(1.8)

                # Check again if new buttons rendered after scroll
                eval_after = await self.page.evaluate(js_script, mode_name)
                if not eval_after.get("found"):
                    consecutive_empty_scrolls += 1
                    self.log("DEBUG", f"Scanning for more requests... (Scroll check {consecutive_empty_scrolls}/{max_empty_scrolls})")
                    if consecutive_empty_scrolls >= max_empty_scrolls:
                        self.log("SUCCESS", f"🎉 No more pending friend requests found. All available requests have been processed!")
                        break
                else:
                    consecutive_empty_scrolls = 0

            # Wrap up
            final_verb = "accepted" if self.mode == "accept" else "rejected"
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
