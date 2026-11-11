FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY tgtg_bot ./tgtg_bot
COPY Telegram.py config.ini.example ./
RUN chmod -R a+rX /app

RUN useradd --create-home --uid 1000 bot && mkdir -p /data && chown bot:bot /data
USER bot
VOLUME ["/data"]

CMD ["python", "-m", "tgtg_bot"]
