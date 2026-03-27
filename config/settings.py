import os
from dotenv import load_dotenv

load_dotenv()

# ── Browser ────────────────────────────────────────────────────────────────
SESSION_DIR   = os.getenv("SESSION_DIR", "./browser/session_data")
HEADLESS      = os.getenv("HEADLESS", "false").lower() == "true"
SLOW_MO       = int(os.getenv("SLOW_MO", "80"))

# ── URLs ───────────────────────────────────────────────────────────────────
MARKETPLACE_INBOX_URL = "https://www.facebook.com/marketplace/inbox/"
FACEBOOK_URL          = "https://www.facebook.com"

# ── Timing (ms) ────────────────────────────────────────────────────────────
PAGE_LOAD_WAIT    = int(os.getenv("PAGE_LOAD_WAIT", "6000"))
CLICK_WAIT        = int(os.getenv("CLICK_WAIT",     "3000"))
TYPE_DELAY        = int(os.getenv("TYPE_DELAY",     "50"))

# ── Polling ────────────────────────────────────────────────────────────────
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_MINUTES", "3")) * 60

# ── Firebase ───────────────────────────────────────────────────────────────
FIREBASE_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# ── OpenAI ─────────────────────────────────────────────────────────────────
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL      = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_HISTORY       = int(os.getenv("MAX_HISTORY", "20"))
MAX_TOKENS        = int(os.getenv("MAX_TOKENS",  "200"))
TEMPERATURE       = float(os.getenv("TEMPERATURE", "0.7"))