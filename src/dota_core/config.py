from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

STRATZ_ENDPOINT: str = "https://api.stratz.com/graphql"
STRATZ_TOKEN: str | None = os.getenv("STRATZ_TOKEN")

# How long cached player data is considered fresh before a re-fetch is recommended.
CACHE_FRESHNESS_HOURS: int = int(os.getenv("CACHE_FRESHNESS_HOURS", "6"))

# OpenAI API key — required for the long-form critique / roast feature.
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
