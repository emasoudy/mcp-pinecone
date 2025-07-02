FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app
COPY . /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

# Install FastAPI and Uvicorn
RUN pip install fastapi uvicorn

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 3000

# Run the web wrapper
CMD ["python", "web_server.py"]
