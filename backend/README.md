# Copilot Terminal Carousel - Backend

FastAPI-based backend for the Copilot Terminal Carousel application.

## Setup

```bash
cd backend
pip install -e ".[dev]"
```

## Running

```bash
uvicorn app.main:app --host 127.0.0.1 --port 5000
```

## Testing

```bash
pytest
```

## Linting

```bash
ruff check app tests
black --check app tests
mypy app
```
