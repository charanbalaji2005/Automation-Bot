# ── Stage 1: base ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# System deps required by Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gnupg ca-certificates \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxcomposite1 libxrandr2 libxdamage1 libxfixes3 \
    libgbm1 libasound2 libpango-1.0-0 libpangocairo-1.0-0 \
    fonts-liberation fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Stage 2: dependencies ─────────────────────────────────────────────────────
FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN python -m playwright install chromium --with-deps

# ── Stage 3: runtime ──────────────────────────────────────────────────────────
FROM deps AS runtime

COPY . .

# Create required directories (they're git-ignored so not in source)
RUN mkdir -p uploads/temp_images screenshots/success screenshots/errors \
             logs data/cookies data/sessions data/cache

# Run as non-root for security
RUN useradd -m botuser && chown -R botuser /app
USER botuser

EXPOSE 8000

CMD ["python", "main.py"]
