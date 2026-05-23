"""
constants.py — Central registry for all magic values and config defaults.
Keeping these here avoids scattering literals across modules and makes
future HTTP-Toolkit reverse-engineering substitution straightforward:
just swap a constant and redeploy.
"""

# ── PimEyes URLs ────────────────────────────────────────────────────────────
PIMEYES_BASE_URL        = "https://pimeyes.com/en"
PIMEYES_UPLOAD_ENDPOINT = "https://pimeyes.com/en"          # Landing / upload page
PIMEYES_RESULTS_URL     = "https://pimeyes.com/en/results"  # Post-search redirect pattern

# ── Browser fingerprint constants ───────────────────────────────────────────
# These are the headers HTTP Toolkit would capture from a real Chrome session.
# Swap them out with live capture data to stay undetected.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_ACCEPT_LANGUAGE = "en-US,en;q=0.9"
DEFAULT_VIEWPORT        = {"width": 1366, "height": 768}

# ── Timeouts (milliseconds for Playwright, seconds for asyncio) ─────────────
PAGE_LOAD_TIMEOUT_MS        = 30_000   # Playwright ms
ELEMENT_WAIT_TIMEOUT_MS     = 15_000
RESULTS_WAIT_TIMEOUT_MS     = 45_000
SEARCH_TRIGGER_DELAY_SEC    = 2        # small human-like pause before clicking
INTER_ACTION_DELAY_MS       = 800      # between UI interactions

# ── Retry policy ────────────────────────────────────────────────────────────
DEFAULT_MAX_RETRIES    = 3
DEFAULT_RETRY_DELAY    = 5   # seconds between attempts
DEFAULT_RETRY_BACKOFF  = 2   # exponential back-off multiplier

# ── Image constraints ────────────────────────────────────────────────────────
ALLOWED_IMAGE_TYPES    = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_EXTENSIONS     = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_IMAGE_SIZE_MB      = 10
MAX_IMAGE_SIZE_BYTES   = MAX_IMAGE_SIZE_MB * 1024 * 1024

# ── Telegram ─────────────────────────────────────────────────────────────────
MAX_RESULTS_PER_MESSAGE = 5            # Telegram message size guard
MAX_TELEGRAM_MESSAGE_LEN = 4096

# ── Paths (relative to project root) ────────────────────────────────────────
UPLOADS_DIR       = "uploads/temp_images"
SCREENSHOTS_DIR   = "screenshots"
SUCCESS_SHOTS_DIR = "screenshots/success"
ERROR_SHOTS_DIR   = "screenshots/errors"
LOGS_DIR          = "logs"
COOKIES_DIR       = "data/cookies"
SESSIONS_DIR      = "data/sessions"
CACHE_DIR         = "data/cache"

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ── FastAPI ──────────────────────────────────────────────────────────────────
API_HOST    = "0.0.0.0"
API_PORT    = 8000
API_VERSION = "v1"
API_PREFIX  = f"/api/{API_VERSION}"

# ── Session / Cookie persistence ─────────────────────────────────────────────
COOKIE_FILE_NAME   = "pimeyes_cookies.json"
SESSION_MAX_AGE_H  = 24   # hours before cookie refresh

# ── Result extraction CSS selectors ──────────────────────────────────────────
# NOTE: If PimEyes updates its DOM, update selectors here only.
# HTTP Toolkit: capture XHR responses to /api/search for a cleaner approach.
RESULT_CONTAINER_SEL    = ".search-results, [class*='result'], [class*='Result']"
RESULT_ITEM_SEL         = "[class*='result-item'], [class*='ResultItem'], .result-card"
RESULT_LINK_SEL         = "a[href]"
RESULT_THUMBNAIL_SEL    = "img[src]"
UPLOAD_BUTTON_SEL       = "input[type='file'], [class*='upload'], [class*='Upload']"
SEARCH_BUTTON_SEL       = "button[type='submit'], [class*='search-btn'], [class*='SearchBtn']"
