FROM python:3.12-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libasound2 libxshmfence1 libcairo2 \
    fonts-liberation fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages including Playwright
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright dependencies and browser
RUN python -m playwright install-deps && \
    python -m playwright install chromium

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install

COPY . .

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
