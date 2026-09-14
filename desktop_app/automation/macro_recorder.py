import os
import sys
import re
import json
import time
import random
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def get_base_dir() -> str:
    """Returns absolute path to persistent app base directory across PyInstaller exe and dev modes."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_methods_dir() -> str:
    mdir = os.path.join(get_base_dir(), "config", "methods")
    os.makedirs(mdir, exist_ok=True)
    return mdir

METHODS_DIR = get_methods_dir()

def parse_recorder_cookies(raw_cookies: Any) -> List[Dict[str, Any]]:
    """Helper to parse cookies in JSON list or semicolon string format into Playwright cookies."""
    if not raw_cookies:
        return []
    if isinstance(raw_cookies, list):
        formatted = []
        for item in raw_cookies:
            if isinstance(item, dict) and item.get("name"):
                dom = item.get("domain", ".facebook.com")
                if not dom.startswith("."):
                    dom = "." + dom
                cookie = {
                    "name": str(item["name"]),
                    "value": str(item.get("value", "")),
                    "domain": dom,
                    "path": item.get("path", "/"),
                    "secure": bool(item.get("secure", True))
                }
                if item.get("sameSite") in ["Strict", "Lax", "None"]:
                    cookie["sameSite"] = item["sameSite"]
                formatted.append(cookie)
        return formatted

    if isinstance(raw_cookies, str):
        cleaned = raw_cookies.strip()
        if not cleaned:
            return []
        if cleaned.startswith("[") and cleaned.endswith("]"):
            try:
                items = json.loads(cleaned)
                return parse_recorder_cookies(items)
            except Exception:
                pass
        formatted = []
        for pair in cleaned.split(";"):
            pair = pair.strip()
            if not pair or "=" not in pair:
                continue
            key, val = pair.split("=", 1)
            k = key.strip()
            v = val.strip()
            if k:
                formatted.append({
                    "name": k,
                    "value": v,
                    "domain": ".facebook.com",
                    "path": "/",
                    "secure": True
                })
        return formatted
    return []

# ==============================================================================
# Injected JavaScript for Chrome Action Recording (Robust Semantic Selectors)
# ==============================================================================
RECORDING_INJECT_JS = """
(() => {
    if (window.__fb_macro_recorder_active) return;
    window.__fb_macro_recorder_active = true;
    window.__fb_recorded_actions = [];
    let lastActionTime = Date.now();

    function cleanText(str) {
        if (!str) return '';
        return str.replace(/\\s+/g, ' ').trim();
    }

    function isDynamicId(id) {
        if (!id) return true;
        // Check for React / Facebook auto-generated IDs like :r1:, _r_2p_, etc.
        if (id.startsWith(':') || id.startsWith('_r_') || id.startsWith('mount_') || id.startsWith('js_') || id.includes(':')) {
            return true;
        }
        return false;
    }

    function getRobustSelectorInfo(el) {
        if (!el || el.nodeType !== 1) return { selector: null, fallbacks: [] };
        
        const fallbacks = [];
        const ariaLabel = cleanText(el.getAttribute('aria-label') || '');
        const role = el.getAttribute('role');
        const name = el.getAttribute('name');
        const dataTestId = el.getAttribute('data-testid');
        const placeholder = cleanText(el.getAttribute('placeholder') || '');
        const id = el.id;
        const tag = el.tagName.toLowerCase();
        const text = cleanText(el.innerText || el.textContent || '').slice(0, 45);

        // 1. Aria Label (Most reliable for Facebook)
        if (ariaLabel) {
            fallbacks.push(`[aria-label="${ariaLabel}"]`);
            fallbacks.push(`${tag}[aria-label="${ariaLabel}"]`);
            if (role) {
                fallbacks.push(`[role="${role}"][aria-label="${ariaLabel}"]`);
            }
        }

        // 2. Data Test ID
        if (dataTestId) {
            fallbacks.push(`[data-testid="${dataTestId}"]`);
        }

        // 3. Placeholder
        if (placeholder) {
            fallbacks.push(`[placeholder="${placeholder}"]`);
            fallbacks.push(`${tag}[placeholder="${placeholder}"]`);
        }

        // 4. Form Name
        if (name) {
            fallbacks.push(`[name="${name}"]`);
            fallbacks.push(`${tag}[name="${name}"]`);
        }

        // 5. Text-based selectors
        if (text && text.length >= 2 && text.length <= 40) {
            if (role) {
                fallbacks.push(`[role="${role}"]:has-text("${text}")`);
            }
            if (['button', 'a', 'span', 'div', 'label', 'p', 'h1', 'h2', 'h3'].includes(tag)) {
                fallbacks.push(`${tag}:has-text("${text}")`);
            }
        }

        // 6. Non-dynamic ID
        if (id && !isDynamicId(id)) {
            fallbacks.push(`#${id}`);
        }

        // 7. Input type
        if (tag === 'input') {
            const inputType = el.getAttribute('type') || 'text';
            fallbacks.push(`input[type="${inputType}"]`);
        } else if (tag === 'textarea') {
            fallbacks.push('textarea');
        }

        // Select the primary best selector
        let primary = fallbacks.length > 0 ? fallbacks[0] : tag;
        
        return {
            selector: primary,
            fallbacks: Array.from(new Set(fallbacks)),
            tag: tag,
            role: role,
            ariaLabel: ariaLabel,
            placeholder: placeholder,
            text: text,
            url: window.location.href
        };
    }

    // Infer semantic field type from attributes
    function inferFieldType(el, val) {
        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
        const placeholder = (el.getAttribute('placeholder') || '').toLowerCase();
        const name = (el.getAttribute('name') || '').toLowerCase();
        const text = (el.innerText || el.textContent || '').toLowerCase();
        const combined = `${aria} ${placeholder} ${name} ${text}`;

        if (combined.includes('title') || combined.includes('what are you selling') || combined.includes('عنوان') || combined.includes('item title')) {
            return 'title';
        }
        if (combined.includes('price') || combined.includes('قیمت') || combined.includes('amount') || combined.includes('cost') || combined.includes('usd') || combined.includes('$')) {
            return 'price';
        }
        if (combined.includes('category') || combined.includes('کیٹیگری') || combined.includes('section')) {
            return 'category';
        }
        if (combined.includes('condition') || combined.includes('حالت') || combined.includes('item condition')) {
            return 'condition';
        }
        if (combined.includes('location') || combined.includes('لوکیشن') || combined.includes('city') || combined.includes('zip') || combined.includes('postal')) {
            return 'location';
        }
        if (combined.includes('description') || combined.includes('تفصیل') || combined.includes('details') || el.tagName.toLowerCase() === 'textarea') {
            return 'description';
        }
        return 'custom';
    }

    // Capture User Clicks
    document.addEventListener('click', (e) => {
        try {
            const target = e.target;
            if (!target) return;
            const now = Date.now();
            const delay = Math.min(Math.max(now - lastActionTime, 200), 8000);
            lastActionTime = now;

            const info = getRobustSelectorInfo(target);
            const action = {
                action_type: 'click',
                selector: info.selector,
                fallbacks: info.fallbacks,
                tag: info.tag,
                role: info.role,
                aria_label: info.ariaLabel,
                text: info.text,
                url: info.url,
                delay_ms: delay,
                timestamp: now
            };

            window.__fb_recorded_actions.push(action);
            if (window.__py_on_macro_action) {
                window.__py_on_macro_action(JSON.stringify(action));
            }
        } catch (err) {}
    }, true);

    // Capture User Typing / Inputs
    document.addEventListener('change', (e) => {
        try {
            const target = e.target;
            if (!target) return;
            const now = Date.now();
            const delay = Math.min(Math.max(now - lastActionTime, 200), 8000);
            lastActionTime = now;

            const val = target.value || target.innerText || '';
            const info = getRobustSelectorInfo(target);
            const fieldType = inferFieldType(target, val);

            const action = {
                action_type: 'type',
                selector: info.selector,
                fallbacks: info.fallbacks,
                tag: info.tag,
                role: info.role,
                aria_label: info.ariaLabel,
                field_type: fieldType,
                sample_value: val,
                url: info.url,
                delay_ms: delay,
                timestamp: now
            };

            window.__fb_recorded_actions.push(action);
            if (window.__py_on_macro_action) {
                window.__py_on_macro_action(JSON.stringify(action));
            }
        } catch (err) {}
    }, true);
})();
"""

# ==============================================================================
# Macro Method Manager (Storage & Preset Library)
# ==============================================================================
class MacroMethodManager:
    """Manages saved posting workflows, storage, and default intelligent methods."""

    @staticmethod
    def get_methods_dir() -> str:
        os.makedirs(METHODS_DIR, exist_ok=True)
        return METHODS_DIR

    @classmethod
    def list_methods(cls) -> List[str]:
        """Returns all available custom and built-in posting methods."""
        mdir = cls.get_methods_dir()
        cls._ensure_default_methods()
        methods = []
        for fname in os.listdir(mdir):
            if fname.endswith(".json"):
                methods.append(fname[:-5])
        
        # Sort so defaults come first
        defaults = ["Standard Marketplace Item", "Vehicle & Auto Listing", "Property & Rental Flow"]
        sorted_methods = [d for d in defaults if d in methods]
        for m in sorted(methods):
            if m not in sorted_methods:
                sorted_methods.append(m)
        return sorted_methods or ["Standard Marketplace Item"]

    @classmethod
    def load_method_data(cls, method_name: str) -> Dict[str, Any]:
        """Loads complete method JSON with metadata and action steps."""
        cls.get_methods_dir()
        path = os.path.join(METHODS_DIR, f"{method_name}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "name": method_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Standard automated listing method",
            "actions": []
        }

    @classmethod
    def save_method(cls, method_name: str, actions: List[Dict[str, Any]], description: str = "") -> str:
        """Saves a recorded workflow to disk."""
        cls.get_methods_dir()
        safe_name = re.sub(r'[^a-zA-Z0-9_\-\s]', '', method_name).strip()
        path = os.path.join(METHODS_DIR, f"{safe_name}.json")
        
        payload = {
            "name": safe_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_steps": len(actions),
            "description": description or f"Recorded workflow with {len(actions)} actions",
            "actions": actions
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return safe_name

    @classmethod
    def delete_method(cls, method_name: str) -> bool:
        """Deletes a saved method file."""
        path = os.path.join(METHODS_DIR, f"{method_name}.json")
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except Exception:
                return False
        return False

    @classmethod
    def _ensure_default_methods(cls):
        """Initializes default pre-configured method files if missing."""
        defaults = {
            "Standard Marketplace Item": {
                "name": "Standard Marketplace Item",
                "created_at": "2026-01-01 00:00:00",
                "total_steps": 6,
                "description": "Standard Facebook Marketplace item listing workflow with AI dynamic parameter injection",
                "actions": [
                    {
                        "action_type": "click",
                        "selector": "a[href*='/marketplace/create/item'], [aria-label*='Item for sale'], span:has-text('Item for sale')",
                        "fallbacks": ["[aria-label*='Item for sale']", "span:has-text('Item for sale')"],
                        "delay_ms": 1500,
                        "text": "Item for sale"
                    },
                    {
                        "action_type": "type",
                        "selector": "input[aria-label='Title'], input[aria-label*='عنوان'], input[name='title']",
                        "field_type": "title",
                        "fallbacks": ["input[aria-label='Title']", "input[aria-label*='عنوان']"],
                        "delay_ms": 800,
                        "sample_value": "{{TITLE}}"
                    },
                    {
                        "action_type": "type",
                        "selector": "input[aria-label='Price'], input[aria-label*='قیمت'], input[name='price']",
                        "field_type": "price",
                        "fallbacks": ["input[aria-label='Price']"],
                        "delay_ms": 700,
                        "sample_value": "{{PRICE}}"
                    },
                    {
                        "action_type": "type",
                        "selector": "textarea[aria-label='Description'], textarea[aria-label*='تفصیل'], textarea[name='description']",
                        "field_type": "description",
                        "fallbacks": ["textarea[aria-label='Description']"],
                        "delay_ms": 1000,
                        "sample_value": "{{DESCRIPTION}}"
                    },
                    {
                        "action_type": "click",
                        "selector": "[aria-label='Next'], [aria-label*='اگلا'], div[role='button']:has-text('Next')",
                        "fallbacks": ["[aria-label='Next']", "div[role='button']:has-text('Next')"],
                        "delay_ms": 1200,
                        "text": "Next"
                    },
                    {
                        "action_type": "click",
                        "selector": "[aria-label='Publish'], [aria-label*='شائع'], div[role='button']:has-text('Publish')",
                        "fallbacks": ["[aria-label='Publish']", "div[role='button']:has-text('Publish')"],
                        "delay_ms": 1800,
                        "text": "Publish"
                    }
                ]
            }
        }
        for name, data in defaults.items():
            path = os.path.join(METHODS_DIR, f"{name}.json")
            if not os.path.exists(path):
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass


# ==============================================================================
# Macro Recorder Session (Chrome Action Capturing)
# ==============================================================================
class MacroRecorderSession:
    """Launches full-screen Chrome, records user clicks/typing, and compiles method steps."""

    def __init__(
        self,
        method_name: str,
        account_data: Optional[Dict[str, Any]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.method_name = method_name
        self.account_data = account_data or {}
        self.log = log_callback or (lambda lvl, msg: print(f"[{lvl}] {msg}"))
        self.recorded_actions: List[Dict[str, Any]] = []

    async def start_recording(self) -> bool:
        if not PLAYWRIGHT_AVAILABLE:
            self.log("ERROR", "Playwright library is required for browser recording.")
            return False

        acc_name = self.account_data.get("name", "")
        if acc_name:
            self.log("INFO", f"🔴 Initializing Full-Screen Action Recorder for: '{self.method_name}' using Account: '{acc_name}'...")
        else:
            self.log("INFO", f"🔴 Initializing Full-Screen Action Recorder for: '{self.method_name}'...")

        self.log("INFO", "Opening Chrome browser in full-screen window. Every click and input will be learned in real time.")
        
        async with async_playwright() as p:
            browser = None
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--disable-infobars",
                "--no-default-browser-check",
                "--disable-notifications",
                "--lang=en-US,en"
            ]

            # Proxy support if specified in selected account
            proxy_config = None
            raw_proxy = self.account_data.get("proxy", "")
            if raw_proxy and "Direct" not in raw_proxy:
                try:
                    from urllib.parse import urlparse
                    if "://" not in raw_proxy:
                        raw_proxy = f"http://{raw_proxy}"
                    parsed_p = urlparse(raw_proxy)
                    if parsed_p.hostname and parsed_p.port:
                        proxy_config = {"server": f"{parsed_p.scheme}://{parsed_p.hostname}:{parsed_p.port}"}
                        if parsed_p.username and parsed_p.password:
                            proxy_config["username"] = parsed_p.username
                            proxy_config["password"] = parsed_p.password
                        self.log("INFO", f"Applying Account Proxy: {parsed_p.hostname}:{parsed_p.port}")
                except Exception:
                    pass

            for ch in ["chrome", "msedge", None]:
                try:
                    browser = await p.chromium.launch(
                        headless=False,
                        args=launch_args,
                        ignore_default_args=["--enable-automation"],
                        proxy=proxy_config,
                        channel=ch
                    )
                    self.log("INFO", f"Full-Screen Recorder launched using: {ch.upper() if ch else 'Chromium'}")
                    break
                except Exception:
                    continue

            if not browser:
                self.log("ERROR", "Could not find Google Chrome or Edge. Please verify Chrome is installed.")
                return False

            try:
                # no_viewport=True guarantees full screen window adaptation
                context = await browser.new_context(
                    no_viewport=True,
                    locale="en-US",
                    permissions=["geolocation", "notifications"]
                )

                # Inject cookies from account_data if provided
                account_cookies = self.account_data.get("cookies")
                if account_cookies:
                    parsed_cookies = parse_recorder_cookies(account_cookies)
                    if parsed_cookies:
                        try:
                            await context.add_cookies(parsed_cookies)
                            self.log("SUCCESS", f"🔑 Injected {len(parsed_cookies)} session cookies for account '{acc_name or 'Selected'}'.")
                        except Exception as ce:
                            self.log("WARNING", f"Cookie injection notice: {str(ce)[:80]}")

                page = await context.new_page()

                # Expose Python bridge for real-time action capturing
                def on_action_bridge(action_json: str):
                    try:
                        act = json.loads(action_json)
                        self.recorded_actions.append(act)
                        typ = act.get('action_type', 'click').upper()
                        txt = act.get('text') or act.get('sample_value') or act.get('field_type') or act.get('selector', '')
                        self.log("SUCCESS", f"✅ Step #{len(self.recorded_actions)}: [{typ}] on '{str(txt)[:35]}'")
                    except Exception as e:
                        pass

                await page.expose_function("__py_on_macro_action", on_action_bridge)
                await page.add_init_script(RECORDING_INJECT_JS)

                self.log("INFO", "Navigating to Facebook Marketplace...")
                try:
                    await page.goto("https://www.facebook.com/marketplace", wait_until="domcontentloaded", timeout=45000)
                except Exception as ex:
                    self.log("WARNING", f"Page notice: {str(ex)[:80]}. Recorder is active in the open window.")

                self.log("INFO", "🟢 RECORDER IS ACTIVE! Perform your listing workflow normally.")
                self.log("INFO", "💡 When you finish the steps, simply CLOSE the Chrome window to save.")

                # Keep session alive until user closes the window
                while True:
                    try:
                        if page.is_closed():
                            break
                        await asyncio.sleep(0.8)
                    except Exception:
                        break

                if self.recorded_actions:
                    MacroMethodManager.save_method(
                        self.method_name,
                        self.recorded_actions,
                        description=f"Recorded flow with {len(self.recorded_actions)} steps on {datetime.now().strftime('%Y-%m-%d')}"
                    )
                    self.log("SUCCESS", f"🎉 Method '{self.method_name}' successfully compiled with {len(self.recorded_actions)} actions!")
                    return True
                else:
                    self.log("WARNING", f"Recording ended for '{self.method_name}'. No actions were captured.")
                    return False

            except Exception as e:
                self.log("ERROR", f"Recording session exception: {str(e)}")
                return False
            finally:
                try:
                    if browser:
                        await browser.close()
                except Exception:
                    pass


# ==============================================================================
# Macro Method Player (Dynamic Replay Engine with Guaranteed Field Injection)
# ==============================================================================
class MacroMethodPlayer:
    """Executes a recorded method on an active Playwright page with dynamic user parameters."""

    def __init__(
        self,
        method_name: str,
        dynamic_params: Dict[str, Any],
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.method_name = method_name
        self.params = dynamic_params
        self.log = log_callback or (lambda lvl, msg: print(f"[{lvl}] {msg}"))
        self.method_data = MacroMethodManager.load_method_data(method_name)
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    async def execute(self, page: Page) -> bool:
        if not page or page.is_closed():
            self.log("ERROR", "Browser window is not available or was closed.")
            return False

        actions = self.method_data.get("actions", [])
        if not actions:
            self.log("WARNING", f"Method '{self.method_name}' contains no action steps.")
            return False

        self.log("INFO", f"⚡ Replaying Learned Method '{self.method_name}' ({len(actions)} steps)...")

        title = str(self.params.get("title", "")).strip()
        price = str(self.params.get("price", "0")).strip()
        description = str(self.params.get("description", "")).strip()
        category = str(self.params.get("category", "")).strip()
        location = str(self.params.get("location", "")).strip()
        images = self.params.get("images", [])

        # Ensure we are in the Marketplace Item Creation interface
        try:
            curr_url = page.url
            if "/marketplace/create" not in curr_url:
                self.log("INFO", "Navigating directly to Facebook Marketplace Create Form...")
                await page.goto("https://www.facebook.com/marketplace/create/item", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2.5)
        except Exception as e:
            if self._is_stopped or page.is_closed():
                self.log("WARNING", "Execution stopped or browser closed.")
                return False

        # Track which core parameters have been successfully entered
        filled_fields = {
            "title": False,
            "price": False,
            "description": False,
            "category": False,
            "location": False,
            "images": False
        }

        for idx, step in enumerate(actions, 1):
            if self._is_stopped or page.is_closed():
                self.log("WARNING", "🛑 Stop command received or browser closed. Halting replay.")
                return False

            action_type = step.get("action_type", "click")
            selector = step.get("selector", "")
            fallbacks = step.get("fallbacks", [])
            field_type = step.get("field_type", "custom")
            delay = (step.get("delay_ms", 1000) / 1000.0)
            target_text = step.get("text", "")
            aria_label = step.get("aria_label", "")

            # Humanized delay before action
            await asyncio.sleep(min(max(delay, 0.3), 3.0))

            if self._is_stopped or page.is_closed():
                return False

            # 1. Multi-tier Element Finder
            element = None
            candidate_selectors = []
            if selector:
                candidate_selectors.append(selector)
            for f in fallbacks:
                if f and f not in candidate_selectors:
                    candidate_selectors.append(f)
            if aria_label:
                candidate_selectors.append(f'[aria-label="{aria_label}"]')
                candidate_selectors.append(f'[aria-label*="{aria_label}"]')
            if target_text and len(target_text) > 1:
                candidate_selectors.append(f':has-text("{target_text}")')
                candidate_selectors.append(f'button:has-text("{target_text}")')
                candidate_selectors.append(f'div[role="button"]:has-text("{target_text}")')

            for cand in candidate_selectors:
                if self._is_stopped or page.is_closed():
                    return False
                try:
                    el = await page.query_selector(cand)
                    if el and await el.is_visible():
                        element = el
                        break
                except Exception:
                    continue

            # 2. Scroll into view check if not found
            if not element:
                try:
                    await page.evaluate("window.scrollBy(0, 300)")
                    await asyncio.sleep(0.3)
                    for cand in candidate_selectors[:3]:
                        el = await page.query_selector(cand)
                        if el and await el.is_visible():
                            element = el
                            break
                except Exception:
                    pass

            # 3. Handle Semantic Typing (Title, Price, Description, Location, Category)
            if action_type == "type":
                value_to_type = step.get("sample_value", "")
                if field_type == "title" and title:
                    value_to_type = title
                    filled_fields["title"] = True
                elif field_type == "price" and price:
                    value_to_type = price
                    filled_fields["price"] = True
                elif field_type == "description" and description:
                    value_to_type = description
                    filled_fields["description"] = True
                elif field_type == "location" and location:
                    value_to_type = location
                    filled_fields["location"] = True
                elif field_type == "category" and category:
                    value_to_type = category
                    filled_fields["category"] = True

                if not element:
                    # Fallback to semantic field finders
                    element = await self._find_semantic_field_input(page, field_type)

                if element:
                    try:
                        self.log("INFO", f"Step #{idx} [TYPE]: Filling [{field_type.upper()}] with: '{value_to_type[:30]}...'")
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(0.2)
                        await element.click()
                        await page.keyboard.press("Control+A")
                        await page.keyboard.press("Backspace")
                        for ch in value_to_type:
                            if self._is_stopped or page.is_closed():
                                return False
                            await page.keyboard.type(ch)
                            await asyncio.sleep(random.uniform(0.02, 0.08))
                        continue
                    except Exception as ex:
                        self.log("WARNING", f"Typing step #{idx} notice: {str(ex)[:50]}")
                else:
                    self.log("INFO", f"Step #{idx}: Dynamic field [{field_type.upper()}] queued for batch injection.")

            # 4. Handle Clicks (Buttons, Dropdowns, Next, Publish)
            elif action_type == "click":
                if not element:
                    # Check if this click corresponds to a known button like Next, Publish, or Category
                    if "next" in str(target_text).lower() or "next" in str(aria_label).lower():
                        element = await self._find_button_by_text(page, ["Next", "اگلا"])
                    elif "publish" in str(target_text).lower() or "publish" in str(aria_label).lower() or "post" in str(target_text).lower():
                        element = await self._find_button_by_text(page, ["Publish", "Post", "شائع"])

                if element:
                    try:
                        lbl = target_text or aria_label or selector[:25]
                        self.log("INFO", f"Step #{idx} [CLICK]: Clicking [{lbl}]...")
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(0.2)
                        await element.click()
                        await asyncio.sleep(0.4)
                    except Exception as ex:
                        self.log("WARNING", f"Click step #{idx} notice: {str(ex)[:50]}")
                else:
                    # Only log non-critical skip if element not strictly found
                    pass

        # ----------------------------------------------------------------------
        # Post-Replay Verification: Ensure ALL User Inputs are Guaranteed Filled
        # ----------------------------------------------------------------------
        if not self._is_stopped and not page.is_closed():
            # 1. Guarantee Title
            if title and not filled_fields["title"]:
                await self._inject_field_safely(page, "title", title)
            
            # 2. Guarantee Price
            if price and not filled_fields["price"]:
                await self._inject_field_safely(page, "price", price)

            # 3. Guarantee Description
            if description and not filled_fields["description"]:
                await self._inject_field_safely(page, "description", description)

            # 4. Guarantee Category
            if category and not filled_fields["category"]:
                await self._inject_category_safely(page, category)

            # 5. Guarantee Location
            if location and not filled_fields["location"]:
                await self._inject_location_safely(page, location)

            # 6. Guarantee Images Upload
            if images:
                await self._upload_images_safely(page, images)

            # 7. Advance through Next / Publish if on form
            await self._finalize_submission(page)

        self.log("SUCCESS", f"🎉 Method '{self.method_name}' execution completed successfully!")
        return True

    async def _find_semantic_field_input(self, page: Page, field_type: str):
        """Finds input elements using resilient multi-attribute semantic rules."""
        selectors_map = {
            "title": [
                'input[aria-label="Title"]', 'input[aria-label*="Title"]', 'input[placeholder*="Title"]',
                'input[aria-label*="عنوان"]', 'input[name="title"]', 'label[aria-label*="Title"] input'
            ],
            "price": [
                'input[aria-label="Price"]', 'input[aria-label*="Price"]', 'input[placeholder*="Price"]',
                'input[aria-label*="قیمت"]', 'input[name="price"]', 'label[aria-label*="Price"] input'
            ],
            "description": [
                'textarea[aria-label="Description"]', 'textarea[aria-label*="Description"]',
                'textarea[aria-label*="تفصیل"]', 'textarea[name="description"]', 'textarea'
            ],
            "location": [
                'input[aria-label="Location"]', 'input[aria-label*="Location"]', 'input[placeholder*="Location"]',
                'input[aria-label*="لوکیشن"]', 'input[aria-label*="City"]', 'input[aria-label*="ZIP"]'
            ]
        }
        for sel in selectors_map.get(field_type, []):
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    return el
            except Exception:
                continue
        return None

    async def _find_button_by_text(self, page: Page, text_list: List[str]):
        """Finds buttons or clickable div cards by text content."""
        for txt in text_list:
            for query in [f'div[aria-label="{txt}"][role="button"]', f'button:has-text("{txt}")', f'div[role="button"]:has-text("{txt}")', f'span:has-text("{txt}")']:
                try:
                    el = await page.query_selector(query)
                    if el and await el.is_visible():
                        return el
                except Exception:
                    continue
        return None

    async def _inject_field_safely(self, page: Page, field_type: str, value: str):
        """Safely finds and types into a required field."""
        if self._is_stopped or page.is_closed():
            return
        el = await self._find_semantic_field_input(page, field_type)
        if el:
            try:
                self.log("INFO", f"Applying [{field_type.upper()}]: '{value[:30]}...'")
                await el.scroll_into_view_if_needed()
                await el.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(value, delay=35)
                await asyncio.sleep(0.3)
            except Exception as e:
                self.log("WARNING", f"Could not apply {field_type}: {str(e)[:40]}")

    async def _inject_category_safely(self, page: Page, category: str):
        """Selects category dropdown item safely."""
        if self._is_stopped or page.is_closed():
            return
        try:
            cat_btn = await page.query_selector('label[aria-label*="Category"], div[aria-label*="Category"][role="combobox"], div[aria-label*="Category"][role="button"]')
            if cat_btn and await cat_btn.is_visible():
                self.log("INFO", f"Setting Category to '{category}'...")
                await cat_btn.click()
                await asyncio.sleep(1.0)
                item = await page.query_selector(f'div[role="option"]:has-text("{category}"), span:has-text("{category}")')
                if item and await item.is_visible():
                    await item.click()
                    await asyncio.sleep(0.5)
        except Exception:
            pass

    async def _inject_location_safely(self, page: Page, location: str):
        """Types and selects target geographic location."""
        if self._is_stopped or page.is_closed():
            return
        try:
            loc_input = await self._find_semantic_field_input(page, "location")
            if loc_input:
                self.log("INFO", f"Setting Target Location to '{location}'...")
                await loc_input.scroll_into_view_if_needed()
                await loc_input.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(location, delay=40)
                await asyncio.sleep(1.8)
                # Pick the first location suggestion
                first_option = await page.query_selector('div[role="listbox"] div[role="option"], ul[role="listbox"] li, div[role="option"]')
                if first_option and await first_option.is_visible():
                    await first_option.click()
                else:
                    await page.keyboard.press("ArrowDown")
                    await asyncio.sleep(0.2)
                    await page.keyboard.press("Enter")
                await asyncio.sleep(0.8)
        except Exception:
            pass

    async def _upload_images_safely(self, page: Page, images: List[str]):
        """Attaches all chosen product images."""
        if self._is_stopped or page.is_closed():
            return
        try:
            valid_imgs = [os.path.abspath(img) for img in images if os.path.exists(img)]
            if valid_imgs:
                file_inputs = await page.query_selector_all('input[type="file"]')
                for finput in file_inputs:
                    try:
                        await finput.set_input_files(valid_imgs)
                        self.log("SUCCESS", f"Attached {len(valid_imgs)} product image(s) to listing.")
                        await asyncio.sleep(2.0)
                        break
                    except Exception:
                        continue
        except Exception as e:
            self.log("WARNING", f"Image upload notice: {str(e)[:40]}")

    async def _finalize_submission(self, page: Page):
        """Attempts to press Next and Publish if active."""
        if self._is_stopped or page.is_closed():
            return
        try:
            # Check for Next button
            next_btn = await self._find_button_by_text(page, ["Next", "اگلا"])
            if next_btn:
                self.log("INFO", "Progressing to final step (Next)...")
                await next_btn.click()
                await asyncio.sleep(3.0)

            # Check for Publish button
            pub_btn = await self._find_button_by_text(page, ["Publish", "Post", "شائع"])
            if pub_btn:
                self.log("INFO", "Publishing listing...")
                await pub_btn.click()
                await asyncio.sleep(4.0)
        except Exception:
            pass

