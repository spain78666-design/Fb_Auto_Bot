"""
FB Auto Bot - Configuration Management Module
"""
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class StealthConfig:
    mask_webdriver: bool = True
    randomize_canvas: bool = True
    randomize_webgl: bool = True
    human_jitter_ms: tuple = (80, 240)
    scroll_steps: int = 5
    headless: bool = False
    default_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )

@dataclass
class BotConfig:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    stealth: StealthConfig = field(default_factory=StealthConfig)
    accounts_file: str = "accounts_vault.json"
    listings_history_file: str = "listings_log.json"
