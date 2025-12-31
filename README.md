# Copilot Terminal Carousel

A Windows-only localhost web application that provides a browser-based, fully interactive terminal UI connected to GitHub Copilot CLI (`copilot.exe`). Users can create and manage up to 10 concurrent Copilot-only terminal sessions, each running in its own dedicated workspace directory.

## Features

- 🖥️ **Browser-based Terminal**: Full terminal emulation using xterm.js with support for colors, cursor movement, and ANSI escape sequences
- 🔄 **Real-time Streaming**: WebSocket-based communication for instant terminal output
- 📋 **Multiple Sessions**: Manage up to 10 concurrent Copilot terminal sessions
- 💾 **Session Persistence**: All sessions and transcripts are persisted to local files for later inspection
- 🔒 **Localhost Only**: Secure by default - binds only to 127.0.0.1

## Prerequisites

- **Windows 11** (required for ConPTY support)
- **Python 3.12.7** or later
- **Node.js 20.x** or later
- **GitHub Copilot CLI** (`copilot.exe`) installed and in PATH

## Quick Start

### 1. Install Dependencies

```bash
# Install backend dependencies
cd backend
pip install -e ".[dev]"

# Install frontend dependencies
cd ../frontend
npm install
```

### 2. Build Frontend

```bash
cd frontend
npm run build
```

### 3. Run the Application

```bash
# From project root
python run.py
```

Open your browser to http://127.0.0.1:5000

## Development

### Running in Development Mode

**Backend** (with auto-reload):
```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 5000
```

**Frontend** (with hot-reload):
```bash
cd frontend
npm run dev
```

### Running Tests

**Backend tests**:
```bash
cd backend
pytest -v --cov=app --cov-report=term-missing
```

**Frontend E2E tests**:
```bash
cd frontend
npx playwright test
```

### Linting

```bash
cd backend
ruff check app tests
black --check app tests
mypy app
```

## Configuration

Configuration is done via environment variables. See `.env.example` for all options.

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `127.0.0.1` | Server bind address |
| `PORT` | `5000` | Server port |
| `DATA_DIR` | `./data` | Data directory for persistence |
| `COPILOT_PATH` | `copilot.exe` | Path to Copilot executable |
| `MAX_SESSIONS` | `10` | Maximum concurrent sessions |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG/INFO/WARNING/ERROR) |

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Project Structure

```
├── run.py                    # Application entry point
├── requirements.txt          # Python dependencies
├── backend/                  # FastAPI backend
│   ├── app/                  # Application source
│   │   ├── main.py          # FastAPI app
│   │   ├── config.py        # Configuration
│   │   ├── ws/              # WebSocket handling
│   │   ├── sessions/        # Session management
│   │   └── persistence/     # File storage
│   └── tests/               # Backend tests
├── frontend/                 # React frontend
│   ├── src/                 # React source
│   └── tests/               # E2E tests
├── docs/                    # Documentation
└── .github/workflows/       # CI/CD
```

## License

MIT License - see LICENSE file for details.
