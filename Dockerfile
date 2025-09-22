FROM python:3.12-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    libsoup-3.0-0 libenchant-2-2 libsecret-1-0 libmanette-0.2-0 \
    libgles2-mesa libgles2-mesa-dev libgstgl-1.0-0 libgstcodecparsers-1.0-0 \
    libgstreamer1.0-0 libgstreamer-plugins-base1.0-0 libgstreamer-plugins-good1.0-0 \
    libgstreamer-plugins-bad1.0-0 libgstreamer-plugins-ugly1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install

COPY . .

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
