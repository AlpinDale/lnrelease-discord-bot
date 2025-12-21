FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY lnrelease/ ./lnrelease/
RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1
ENV BOT_DB_PATH=/app/data/bot.sqlite
ENV BOT_TIMEZONE_DEFAULT=UTC

VOLUME ["/app/data"]

CMD ["python", "-m", "lnrelease.bot"]

