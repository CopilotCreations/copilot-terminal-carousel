# User Guide

This guide covers how to install, configure, and use the Copilot Terminal Carousel application.

## Installation

### Prerequisites

Before installing, ensure you have:

1. **Windows 11** - Required for ConPTY support
2. **Python 3.12.7** or later - [Download Python](https://www.python.org/downloads/)
3. **Node.js 20.x** or later - [Download Node.js](https://nodejs.org/)
4. **GitHub Copilot CLI** - Install via `winget install GitHub.CopilotCLI`

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd copilot-terminal-carousel
```

### Step 2: Install Backend Dependencies

```bash
cd backend
pip install -e ".[dev]"
```

### Step 3: Install Frontend Dependencies

```bash
cd ../frontend
npm install
```

### Step 4: Build the Frontend

```bash
npm run build
```

### Step 5: Start the Application

```bash
cd ..
python run.py
```

The application will be available at http://127.0.0.1:5000

## Using the Application

### Creating a Session

1. Open http://127.0.0.1:5000 in your browser
2. Wait for the "Connected" status in the header
3. Click the "+ New Session" button
4. A new Copilot terminal session will open

### Interacting with Copilot

- Type in the terminal pane to send input to Copilot
- Use keyboard shortcuts (Ctrl+C, arrow keys, etc.) as you would in a normal terminal
- The terminal supports ANSI colors and formatting

### Managing Sessions

#### Switching Sessions
Click on any session in the left sidebar to attach to it.

#### Terminating Sessions
Hover over a session in the sidebar and click the "✕" button to terminate it.

#### Session Status
- 🟢 **Running** - Session is active
- 🔴 **Exited** - Session has ended

### Session Limits

You can run up to 10 concurrent sessions. If you reach the limit, you'll need to terminate an existing session before creating a new one.

## Configuration

### Environment Variables

Create a `.env` file in the project root to customize settings:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` to change settings:

```ini
# Server binding
HOST=127.0.0.1
PORT=5000

# Copilot executable path
COPILOT_PATH=copilot.exe

# Session limits
MAX_SESSIONS=10

# Terminal dimensions
INITIAL_COLS=120
INITIAL_ROWS=30

# Logging
LOG_LEVEL=INFO
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `127.0.0.1` | IP address to bind to |
| `PORT` | `5000` | Port number |
| `DATA_DIR` | `./data` | Directory for session data |
| `COPILOT_PATH` | `copilot.exe` | Path to Copilot executable |
| `MAX_SESSIONS` | `10` | Maximum concurrent sessions |
| `INITIAL_COLS` | `120` | Default terminal width |
| `INITIAL_ROWS` | `30` | Default terminal height |
| `MIN_COLS` | `20` | Minimum terminal width |
| `MAX_COLS` | `300` | Maximum terminal width |
| `MIN_ROWS` | `5` | Minimum terminal height |
| `MAX_ROWS` | `120` | Maximum terminal height |
| `MAX_INPUT_CHARS_PER_MESSAGE` | `16384` | Max input size per message |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ALLOW_NON_LOCALHOST` | `false` | Allow non-localhost connections |

## Data Storage

### Session Data Location

All session data is stored in the `DATA_DIR` directory (default: `./data`):

```
data/
├── sessions/
│   ├── index.json              # Session index
│   ├── {session-id}/
│   │   ├── meta.json           # Session metadata
│   │   ├── transcript.jsonl    # Event log
│   │   └── workspace/          # Session working directory
└── logs/
    └── app.jsonl               # Application logs
```

### Viewing Transcripts

Session transcripts are stored in JSONL format. Each line is a JSON event:

```bash
# View a session transcript
type data\sessions\{session-id}\transcript.jsonl
```

Event types include:
- `out` - Terminal output
- `in` - User input
- `resize` - Terminal resize
- `lifecycle` - Session lifecycle events (created, exited, etc.)

## Troubleshooting

### Connection Issues

**Problem**: Browser shows "Disconnected"

**Solutions**:
1. Ensure the backend is running (`python run.py`)
2. Check that port 5000 is not in use
3. Check firewall settings

### Session Creation Fails

**Problem**: Error "SPAWN_FAILED" when creating session

**Solutions**:
1. Verify `copilot.exe` is installed and in PATH
2. Check `COPILOT_PATH` configuration
3. Review logs in `data/logs/app.jsonl`

### Maximum Sessions Reached

**Problem**: Error "MAX_SESSIONS_REACHED"

**Solution**: Terminate existing sessions before creating new ones

### Terminal Not Rendering

**Problem**: Terminal pane is blank

**Solutions**:
1. Refresh the browser page
2. Check browser console for errors
3. Ensure frontend was built correctly

## Security Considerations

### Localhost Only

By default, the application only accepts connections from `127.0.0.1`. This is intentional for security. Do not expose this application to the network unless you understand the implications.

### No Authentication

This application has no authentication mechanism. It's designed for single-user local development only.

### Data Storage

Session data and transcripts are stored in plain text on the local filesystem. Do not store sensitive information in sessions.

## Development

### Running in Development Mode

**Backend with auto-reload**:
```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 5000
```

**Frontend with hot-reload**:
```bash
cd frontend
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest -v

# Frontend E2E tests
cd frontend
npx playwright test
```

### Building for Production

```bash
# Build frontend
cd frontend
npm run build

# Run production server
cd ..
python run.py
```
