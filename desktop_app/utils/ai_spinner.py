#!/usr/bin/env python3
"""
FB Auto Bot - Facebook Marketplace Automation Suite
utils/ai_spinner.py - AI Content Spinner & Title/Description Generator
Powered by Gemini API with Offline Spintax & Synonym Replacement Engine
"""

import os
import re
import json
import random
import logging
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger("FBAutoBot.AISpinner")

# Check if google-genai or google.generativeai is installed
GEMINI_SDK_AVAILABLE = False
try:
    from google import genai
    from google.genai import types
    GEMINI_SDK_AVAILABLE = True
except ImportError:
    try:
        import google.generativeai as legacy_genai
        GEMINI_SDK_AVAILABLE = True
    except ImportError:
        GEMINI_SDK_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class SpintaxEngine:
    """
    Offline spintax parser and synonym replacement engine.
    Parses nested expressions: '{Option A|Option B|{C1|C2}}'
    and applies contextual Marketplace sales transformations.
    """

    SYNONYMS = {
        "brand new": [
            "100% brand new", "factory sealed", "unopened in box", 
            "never used", "sealed box", "mint in box", "pristine condition"
        ],
        "sealed": [
            "factory sealed", "original seal intact", "never unsealed", "box sealed"
        ],
        "like new": [
            "flawless condition", "mint condition", "barely used",
            "near perfect", "10/10 condition", "used once or twice"
        ],
        "great condition": [
            "excellent working order", "very clean condition", "well cared for",
            "super clean", "tested & 100% working"
        ],
        "fast shipping": [
            "same-day dispatch", "ships within 24h", "tracked express postage",
            "safe tracked shipping", "fast nationwide delivery"
        ],
        "local pickup": [
            "in-person pickup available", "safe public meetup", "front porch collection",
            "cash on pickup preferred", "pickup in local area"
        ],
        "authentic": [
            "100% genuine", "verified authentic", "original authentic item",
            "receipt/proof available on request"
        ],
        "message me": [
            "DM for fast response", "send a chat message", "inquire below",
            "feel free to ask any questions", "message anytime"
        ]
    }

    TITLE_PREFIXES = [
        "{🔥 Deal! |⚡ Special: |Brand New |Sealed |Authentic |Original }",
        "{[Must Go!] |[SALE] |[Verified Genuine] |[Ready for Pickup] }",
        "{New In Box: |Factory Sealed: |Best Price: }"
    ]

    TITLE_SUFFIXES = [
        " {- Fast Pickup / Shipping Available}",
        " {- Sealed Box (Never Opened)}",
        " { [Mint Condition / Warranty Ready]}",
        " {- Best Deal Around}",
        " {- Priced to Sell Quickly}",
        " {- In Hand Ready Today}"
    ]

    @classmethod
    def parse_spintax(cls, text: str) -> str:
        """
        Recursively parses and resolves spintax like '{A|B|{C|D}}'.
        """
        pattern = re.compile(r"\{([^{}]+)\}")
        while True:
            match = pattern.search(text)
            if not match:
                break
            choices = match.group(1).split("|")
            text = text[:match.start()] + random.choice(choices) + text[match.end():]
        return text

    @classmethod
    def apply_synonym_jitter(cls, text: str, probability: float = 0.6) -> str:
        """
        Subtly swaps known Marketplace sales phrases with natural synonyms.
        """
        result = text
        for key, syns in cls.SYNONYMS.items():
            if re.search(r"\b" + re.escape(key) + r"\b", result, re.IGNORECASE):
                if random.random() < probability:
                    replacement = random.choice(syns)
                    result = re.sub(r"\b" + re.escape(key) + r"\b", replacement, result, count=1, flags=re.IGNORECASE)
        return result

    @classmethod
    def spin_title(cls, seed_title: str, count: int = 5) -> List[str]:
        """
        Generates distinct, high-CTR title variants using offline heuristics.
        """
        clean_seed = seed_title.strip()
        variants = set()

        # Variant 1: Original with prefix spintax
        v1 = cls.parse_spintax(f"{random.choice(cls.TITLE_PREFIXES)}{clean_seed}")
        variants.add(re.sub(r"\s+", " ", v1).strip())

        # Variant 2: Original with suffix spintax
        v2 = cls.parse_spintax(f"{clean_seed}{random.choice(cls.TITLE_SUFFIXES)}")
        variants.add(re.sub(r"\s+", " ", v2).strip())

        # Variant 3: Prefix + clean + suffix
        v3 = cls.parse_spintax(f"{random.choice(cls.TITLE_PREFIXES)}{clean_seed}{random.choice(cls.TITLE_SUFFIXES)}")
        variants.add(re.sub(r"\s+", " ", v3).strip())

        # Variant 4: Synonym jitter on seed
        v4 = cls.apply_synonym_jitter(clean_seed, probability=1.0)
        variants.add(re.sub(r"\s+", " ", v4).strip())

        # Variant 5: Short specs highlight
        words = clean_seed.split()
        if len(words) > 3:
            v5 = f"{' '.join(words[:4])} - {random.choice(['Sealed', 'New', 'Flawless'])} ({' '.join(words[4:])})"
            variants.add(re.sub(r"\s+", " ", v5).strip())

        # Ensure we meet requested count
        while len(variants) < count:
            extra = cls.parse_spintax(f"{{Authentic |Genuine |Top Condition }}{clean_seed} - {{Available Now|Pickup Today}}")
            variants.add(re.sub(r"\s+", " ", extra).strip())

        return list(variants)[:count]

    @classmethod
    def spin_description(cls, base_desc: str, title: str = "", tone: str = "Professional", count: int = 3) -> List[str]:
        """
        Generates rich, structured description variants offline.
        """
        clean_title = title or "Product Item"
        clean_desc = base_desc.strip() or f"High quality {clean_title} in great condition."

        variants = []

        # Template A: Structured Bullet Points (Professional)
        spintax_a = f"""
{{🔥 |⭐ |✅ }} {{Up for sale is a |Available now: |Selling this authentic }} **{clean_title}**.

{{Key Details & Highlights:|Product Specifications:|Condition Overview:}}
• {{Condition:|Item State:}} {{100% Brand New & Sealed|Mint Condition, tested & fully operational|Original factory packaging}}
• {{Authenticity:|Verification:}} {{Guaranteed genuine with all original accessories|100% authentic item}}
• {{Overview:|Features:}} {clean_desc}

{{Logistics & Delivery:|Pickup & Meetup Info:}}
• {{Pickup:|Meetup:}} {{Local pickup available in public area|Front porch collection or public meetup}}
• {{Shipping:|Postage:}} {{Fast tracked shipping available upon request|Can ship safely with tracking number}}

{{Payment & Inquiries:|How to buy:}}
• {{Accepting cash, Zelle, Venmo, or Marketplace secure checkout.|Cash preferred for local pickup.}}
• {{Feel free to message with questions. Serious inquiries only!|DM anytime for immediate response.}}
"""
        variants.append(cls.parse_spintax(spintax_a).strip())

        # Template B: Urgent / Deal Style
        spintax_b = f"""
⚡ {{QUICK SALE DEAL:|MUST GO THIS WEEKEND:|PRICED TO SELL:}} {clean_title}

{clean_desc}

{{Why grab this now?:|Key highlights:}}
- {{Super clean condition, ready to use immediately.|Sealed/unused, save big compared to retail!}}
- {{Includes all original items/accessories.|Complete in original packaging.}}
- {{Tested and fully inspected.|Pristine cosmetic and functional state.}}

{{📍 Pick up locally or ask for tracked shipping.|📍 Local pickup preferred today, can deliver within reasonable radius.}}
{{💬 Send a message before it sells! First come, first served.|💬 DM if interested!}}
"""
        variants.append(cls.parse_spintax(spintax_b).strip())

        # Template C: Casual / Friendly Marketplace Tone
        spintax_c = f"""
{{Hey everyone! |Hello! |Hi there, }} {{I have this |selling my |letting go of this }} {clean_title}.

{clean_desc}

{{Everything is in top notch shape with no issues.|Works perfectly and has been taken care of really well.}}

{{Happy to meet up locally in a safe spot for pickup, or I can ship it out with tracking if you prefer.|Local pickup is welcome, or let me know if you need shipping.}}

{{Shoot me a message if you're interested or have any questions. Thanks for looking!|Message me anytime!}}
"""
        variants.append(cls.parse_spintax(spintax_c).strip())

        return variants[:count]


class GeminiAISpinner:
    """
    AI Content Generator & Rewriter leveraging the Google Gemini API.
    Falls back cleanly to the SpintaxEngine when offline or if API errors occur.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model_name

    def set_api_key(self, api_key: str):
        """Sets or updates the Gemini API key."""
        self.api_key = api_key.strip()

    def generate_titles(
        self,
        seed_keyword: str,
        tone: str = "Casual",
        count: int = 5,
        log_callback: Optional[Callable[[str, str], None]] = None
    ) -> List[str]:
        """
        Generates 3 to 5 click-worthy Facebook Marketplace titles.
        """
        log = log_callback or (lambda lvl, msg: logger.info(f"[{lvl}] {msg}"))

        if not seed_keyword or not seed_keyword.strip():
            return []

        clean_seed = seed_keyword.strip()

        # If no API key, use the local Spintax engine
        if not self.api_key:
            log("INFO", "No Gemini API key provided. Using Offline Spintax Engine for titles...")
            return SpintaxEngine.spin_title(clean_seed, count=count)

        log("INFO", f"Calling Gemini API ({self.model_name}) to generate {count} title variants for '{clean_seed}' (Tone: {tone})...")

        system_instruction = (
            "You are a top-performing Facebook Marketplace copywriter. "
            "Generate high-converting, realistic product listing titles that buyers actually click on. "
            "Avoid spammy all-caps or exaggerated claims. Keep each title between 30 and 70 characters. "
            "Return ONLY a JSON array of strings containing the title variants."
        )

        prompt = (
            f"Generate exactly {count} unique Facebook Marketplace product titles for: '{clean_seed}'.\n"
            f"Tone: {tone} (Options: Casual, Professional, Urgent).\n"
            "Include natural attributes buyers look for (e.g. condition, bundle, sealed, pickup ready) where relevant.\n"
            "Output JSON format: [\"Title 1\", \"Title 2\", ...]"
        )

        try:
            raw_text = self._call_gemini(prompt, system_instruction=system_instruction)
            parsed_titles = self._extract_json_list(raw_text)

            if parsed_titles and len(parsed_titles) >= 2:
                log("SUCCESS", f"Gemini generated {len(parsed_titles)} title variants successfully!")
                return parsed_titles[:count]
            else:
                log("WARNING", "Gemini response did not contain expected JSON list. Falling back to spintax...")
                return SpintaxEngine.spin_title(clean_seed, count=count)

        except Exception as e:
            log("WARNING", f"Gemini API call failed ({str(e)}). Engaging Offline Spintax fallback...")
            return SpintaxEngine.spin_title(clean_seed, count=count)

    # Alias for flexibility
    generate_title_variants = generate_titles

    def rewrite_description(
        self,
        base_description: str,
        title: str = "",
        tone: str = "Professional",
        count: int = 3,
        log_callback: Optional[Callable[[str, str], None]] = None
    ) -> List[str]:
        """
        Rewrites product descriptions into unique variants to evade duplicate text detection.
        """
        log = log_callback or (lambda lvl, msg: logger.info(f"[{lvl}] {msg}"))

        clean_desc = base_description.strip()
        if not clean_desc and not title:
            return []

        # If no API key, use the local Spintax engine
        if not self.api_key:
            log("INFO", "No Gemini API key provided. Using Offline Spintax Engine for descriptions...")
            return SpintaxEngine.spin_description(clean_desc, title=title, tone=tone, count=count)

        log("INFO", f"Calling Gemini API ({self.model_name}) to generate {count} unique description rewrites (Tone: {tone})...")

        system_instruction = (
            "You are an expert e-commerce copywriter crafting Facebook Marketplace descriptions. "
            "Rewrite the product details into unique, structured, and compelling listing descriptions. "
            "Format with clean bullet points for specs, condition highlights, pickup/delivery options, and a clear call-to-action. "
            "Each variant must have distinct phrasing and structure to avoid duplicate listing detection. "
            "Return ONLY a JSON array of strings containing the description variants."
        )

        prompt = (
            f"Product Title: {title}\n"
            f"Original Description:\n{clean_desc}\n\n"
            f"Tone: {tone}\n"
            f"Create {count} distinct rewritten descriptions in natural English.\n"
            "Output JSON format: [\"Description variant 1\", \"Description variant 2\", ...]"
        )

        try:
            raw_text = self._call_gemini(prompt, system_instruction=system_instruction)
            parsed_descs = self._extract_json_list(raw_text)

            if parsed_descs and len(parsed_descs) >= 1:
                log("SUCCESS", f"Gemini generated {len(parsed_descs)} description variants successfully!")
                return parsed_descs[:count]
            else:
                log("WARNING", "Gemini response format unparseable. Falling back to spintax...")
                return SpintaxEngine.spin_description(clean_desc, title=title, tone=tone, count=count)

        except Exception as e:
            log("WARNING", f"Gemini API description generation failed ({str(e)}). Using Spintax fallback...")
            return SpintaxEngine.spin_description(clean_desc, title=title, tone=tone, count=count)

    def _call_gemini(self, prompt: str, system_instruction: str = "") -> str:
        """
        Executes generation using Google GenAI SDK if available, or direct REST API fallback.
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        # 1. Try official google-genai SDK
        if GEMINI_SDK_AVAILABLE:
            try:
                # Modern SDK (google.genai)
                if 'genai' in globals() and hasattr(genai, 'Client'):
                    client = genai.Client(api_key=self.api_key)
                    config = types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7,
                        response_mime_type="application/json"
                    ) if hasattr(types, 'GenerateContentConfig') else None

                    kwargs = {"contents": prompt}
                    if config:
                        kwargs["config"] = config

                    response = client.models.generate_content(
                        model=self.model_name,
                        **kwargs
                    )
                    return response.text or ""

                # Legacy SDK (google.generativeai)
                elif 'legacy_genai' in globals():
                    legacy_genai.configure(api_key=self.api_key)
                    model = legacy_genai.GenerativeModel(
                        model_name=self.model_name,
                        system_instruction=system_instruction or None
                    )
                    resp = model.generate_content(prompt)
                    return resp.text or ""

            except Exception as sdk_err:
                logger.debug(f"SDK call failed, trying direct REST API: {sdk_err}")

        # 2. REST API direct fallback (works with standard `requests` without requiring Google SDKs)
        if REQUESTS_AVAILABLE:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [{"text": f"{system_instruction}\n\n{prompt}" if system_instruction else prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "responseMimeType": "application/json"
                }
            }
            resp = requests.post(url, json=payload, timeout=20)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini REST API error {resp.status_code}: {resp.text}")

            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            raise RuntimeError("No text candidates returned from Gemini REST API.")

        raise RuntimeError("Neither google-genai SDK nor requests module is available.")

    def _extract_json_list(self, text: str) -> List[str]:
        """Parses a JSON array from raw model text output."""
        cleaned = text.strip()
        # Remove markdown code fences if present
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
            elif isinstance(parsed, dict):
                # Look for list values inside dict
                for val in parsed.values():
                    if isinstance(val, list):
                        return [str(item).strip() for item in val if str(item).strip()]
        except Exception:
            pass

        # Fallback regex search for JSON array [...]
        match = re.search(r"\[\s*\"[^\"]+\"(?:\s*,\s*\"[^\"]+\")*\s*\]", text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed]
            except Exception:
                pass

        # Split by numbered list lines like "1. Title"
        lines = [re.sub(r"^\d+[\.\)]\s*", "", line).strip().strip('"') for line in text.split("\n") if line.strip()]
        return [line for line in lines if line and len(line) > 5]


# Global singleton
_GLOBAL_AI_SPINNER: Optional[GeminiAISpinner] = None

def get_ai_spinner(api_key: Optional[str] = None) -> GeminiAISpinner:
    """Returns the singleton GeminiAISpinner instance."""
    global _GLOBAL_AI_SPINNER
    if _GLOBAL_AI_SPINNER is None:
        _GLOBAL_AI_SPINNER = GeminiAISpinner(api_key=api_key)
    elif api_key:
        _GLOBAL_AI_SPINNER.set_api_key(api_key)
    return _GLOBAL_AI_SPINNER
