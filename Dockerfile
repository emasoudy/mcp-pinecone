# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Set the working directory
WORKDIR /app

# Copy the project files to the working directory
COPY . /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install dependencies and the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Production stage
FROM python:3.12-slim-bookworm

# Set working directory
WORKDIR /app

# Copy the virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Set environment variables for Pinecone
ENV PINECONE_API_KEY=""
ENV PINECONE_INDEX_NAME=""

# Entry point for running the MCP server
ENTRYPOINT ["python", "-m", "mcp_pinecone"]
