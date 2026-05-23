# PimEyes Automation Bot 🤖🔍

A production-grade Telegram bot that accepts face images, searches [PimEyes](https://pimeyes.com) via Playwright browser automation, and returns matching result links — all asynchronously.

---

## ✨ Features

| Feature | Detail |
|---|---|
| Telegram image intake | Compressed photos **and** uncompressed document uploads |
| Browser automation | Playwright + Chromium, headless or headful |
| Retry logic | Exponential back-off, configurable attempts |
| Session persistence | Cookies saved to disk, reused between searches |
| CAPTCHA detection | Detection hooks; manual + 2captcha solver stubs |
| Step screenshots | Every automation step captured for debugging |
| Proxy rotation | Round-robin proxy support |
| REST API | FastAPI endpoint mirrors all Telegram functionality |
| HTTP Toolkit ready | Code structured for easy request reconstruction |

---

## 🗂 Project Structure

```
pimeyes-automation-bot/
├── bot/                  # Telegram handlers & application factory
├── automation/           # Playwright workflow (search, upload, extract)
├── api/                  # FastAPI server & routes
├── services/             # Orchestration, retry, proxy, screenshots
├── utils/                # Logger, config, validators, helpers, constants
├── uploads/temp_images/  # Transient image storage (auto-cleaned)
├── screenshots/          # Step-by-step browser screenshots
│   ├── success/
│   └── errors/
├── logs/                 # Rotating log files
├── data/                 # Cookies, sessions, cache
├── tests/                # pytest test suite
├── main.py               # Entry point
├── requirements.txt
├── Dockerfile
└── .env                  # Secrets (never commit)
```

---

## ⚙️ Setup

### 1. Prerequisites

- Python 3.11+
- pip

### 2. Clone & install

```bash
git clone https://github.com/yourname/pimeyes-automation-bot.git
cd pimeyes-automation-bot

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python -m playwright install chromium --with-deps
```

### 3. Configure environment

```bash
cp .env .env.local   # or just edit .env directly
```

Required variables:

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Get from [@BotFather](https://t.me/BotFather) |

Optional variables:

| Variable | Default | Description |
|---|---|---|
| `HEADLESS` | `true` | `false` = watch the browser |
| `MAX_RETRIES` | `3` | Search retry attempts |
| `PROXY_SERVER` | _(none)_ | e.g. `http://127.0.0.1:8080` for HTTP Toolkit |
| `SAVE_STEP_SCREENSHOTS` | `true` | Debug screenshots per step |
| `API_PORT` | `8000` | FastAPI port |

### 4. Create a Telegram bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram.
2. Send `/newbot` and follow prompts.
3. Copy the token into `TELEGRAM_BOT_TOKEN` in `.env`.

---

## 🚀 Running

### Bot + API together (default)

```bash
python main.py
```

### Bot only

```bash
python main.py --bot-only
```

### API only

```bash
python main.py --api-only
```

### Docker

```bash
docker build -t pimeyes-bot .
docker run --env-file .env -p 8000:8000 pimeyes-bot
```

---

## 📡 REST API

Interactive docs at: `http://localhost:8000/api/v1/docs`

### `POST /api/v1/search/image`

Upload an image file and receive search results.

```bash
curl -X POST http://localhost:8000/api/v1/search/image \
  -F "file=@photo.jpg;type=image/jpeg" \
  -F "max_results=10"
```

**Response:**

```json
{
  "success": true,
  "request_id": "a1b2c3d4e5f6",
  "results": [
    {
      "url": "https://example.com/page",
      "title": "Example Page Title",
      "thumbnail_url": "https://cdn.example.com/thumb.jpg",
      "source_domain": "example.com"
    }
  ],
  "error": null
}
```

---

## 🏗 Architecture

```
Telegram User
     │  (photo)
     ▼
[Telegram Bot]  ──────────────────────────────┐
     │                                        │ (same logic)
     ▼                                        ▼
[handlers.py]                           [FastAPI routes]
     │
     ▼
[RetryService]  ──► exponential back-off wrapper
     │
     ▼
[ImageSearchService]  ──► orchestrator
     │
     ├─► [UploadHandler]     save bytes → disk
     │
     ├─► [BrowserManager]    launch Chromium
     │         │
     │         ▼
     │   [SessionManager]    load/save cookies
     │
     ├─► [PimEyesSearch]     navigate → upload → search → wait
     │
     ├─► [CaptchaHandler]    detect + handle CAPTCHAs
     │
     └─► [result_extractor]  scrape DOM → list[dict]
               │
               ▼
         [Telegram reply / API JSON]
```

---

## 🔬 HTTP Toolkit Integration

This project is structured for easy request reconstruction via [HTTP Toolkit](https://httptoolkit.com/):

1. Set `PROXY_SERVER=http://127.0.0.1:8080` in `.env`.
2. Set `HEADLESS=false`.
3. Launch HTTP Toolkit, enable the proxy.
4. Run the bot and send a test image.
5. HTTP Toolkit will show every request the browser makes, including:
   - Multipart upload POST (with image bytes)
   - CSRF tokens / signed URLs
   - Search POST parameters
   - Cookie headers

Copy those headers/bodies into `utils/constants.py` to replicate searches via **direct HTTP** (no browser) in the future.

---

## ⚠️ Limitations

- **PimEyes UI changes** — If PimEyes updates its CSS selectors or JavaScript, the automation may break. Update `utils/constants.py` selectors and `automation/pimeyes_search.py` accordingly.
- **CAPTCHA** — Headless sessions may encounter hCaptcha or Cloudflare Turnstile. Integrate a solver API (2captcha/CapSolver) in `automation/captcha_handler.py`.
- **Rate limiting** — PimEyes may throttle or block IPs. Use proxy rotation via `PROXY_LIST`.
- **Free tier limits** — PimEyes free tier blurs results. A subscription account (set via cookies) unlocks full URLs.
- **Not affiliated with PimEyes** — This tool is for educational/research purposes.

---

## 🔮 Future Improvements

- [ ] Direct HTTP search (no browser) using HTTP Toolkit captured requests
- [ ] 2captcha / CapSolver integration in `captcha_handler.py`
- [ ] Telegram inline keyboard for result pagination
- [ ] Redis queue for concurrent search jobs
- [ ] Web dashboard for monitoring active searches
- [ ] PimEyes account cookie injection for full result access
- [ ] Webhook mode deployment (Nginx + certbot)

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 📄 License

MIT — see `LICENSE`.
