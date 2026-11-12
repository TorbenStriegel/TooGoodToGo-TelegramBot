FROM python:3.13-slim

LABEL org.opencontainers.image.title="Too Good To Go Telegram Bot" \
      org.opencontainers.image.description="Telegram notifications for your Too Good To Go favorites" \
      org.opencontainers.image.source="https://github.com/TorbenStriegel/TooGoodToGo-TelegramBot" \
      org.opencontainers.image.licenses="GPL-3.0"

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY tgtg_bot ./tgtg_bot
RUN chmod -R a+rX /app \
    && useradd --create-home --uid 1000 bot \
    && mkdir -p /data && chown bot:bot /data
USER bot
VOLUME ["/data"]

CMD ["python", "-m", "tgtg_bot"]
