.PHONY: install dev db-create db-setup migrate makemigrations rollback test lint format clean docker-build docker-run

# Install dependencies
install:
	uv sync --all-extras

# Run local development server
dev:
	uv run uvicorn app.main:app --reload --port 8000

run:
	uv run python main.py

# Create the database if it doesn't exist (like `rails db:create`)
db-create:
	uv run python -m app.db.create_db

# Full setup: create DB + apply migrations (like `rails db:setup`)
db-setup: db-create migrate

# Generate an autodetected migration (e.g. make makemigrations msg="add field")
makemigrations:
	uv run alembic revision --autogenerate -m "$${msg:-update schema}"

# Apply migrations (like `rails db:migrate`)
migrate:
	uv run alembic upgrade head

# Rollback last migration
rollback:
	uv run alembic downgrade -1

# Run tests
test:
	uv run pytest -v

# Run linter
lint:
	uv run ruff check .

# Fix and format code
format:
	uv run ruff check --fix .
	uv run ruff format .

# Docker commands
docker-build:
	docker build -t campaign-engine-api .

docker-run:
	docker run -p 8000:8000 --env-file .env campaign-engine-api
