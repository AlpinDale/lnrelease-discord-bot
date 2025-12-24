# Builder stage
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder

WORKDIR /app

ENV UV_NO_DEV=1
ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-install-project --no-editable

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-editable --compile-bytecode

FROM python:3.13-alpine

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

RUN find /app/.venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type d -name "test" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type f -name "*.txt" ! -path "*.dist-info/*" -delete 2>/dev/null || true && \
    find /app/.venv -type f -name "*.md" -delete 2>/dev/null || true && \
    find /app/.venv -type f -name "*.rst" -delete 2>/dev/null || true && \
    rm -rf /app/.venv/lib/python*/site-packages/pip* && \
    rm -rf /app/.venv/lib/python*/site-packages/setuptools* && \
    rm -rf /app/.venv/lib/python*/site-packages/wheel* && \
    rm -f /app/.venv/bin/pip /app/.venv/bin/pip3 /app/.venv/bin/pip3.* && \
    rm -f /app/.venv/bin/easy_install /app/.venv/bin/easy_install-3.* || true

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV BOT_DB_PATH=/app/data/bot.sqlite
ENV BOT_TIMEZONE_DEFAULT=UTC

VOLUME ["/app/data"]

CMD ["python", "-m", "lnrelease.bot"]
