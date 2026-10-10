FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install ca-certificates for secure WebSocket and API connections
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv frozen lockfile
RUN uv sync --frozen --no-install-project

# Put virtualenv into PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy project code
COPY . .

# Use ENTRYPOINT to enforce that ONLY the LiveKit agent server runs.
# This prevents Railway from overriding the container command with uvicorn.
ENTRYPOINT ["sh", "-c", "exec uv run python server.py start"]
