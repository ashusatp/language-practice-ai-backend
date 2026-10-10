FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy dependency definition files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv frozen lockfile
RUN uv sync --frozen --no-install-project

# Copy remaining project source code
COPY . .

# Set default port
ENV PORT=8000
EXPOSE 8000

# Run database migrations and launch FastAPI uvicorn server
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
