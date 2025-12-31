# Architecture Documentation

This document describes the architecture of the Copilot Terminal Carousel application.

## Overview

Copilot Terminal Carousel is a Windows-only localhost web application that provides a browser-based terminal UI for GitHub Copilot CLI. The application uses a client-server architecture with WebSocket communication for real-time terminal streaming.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (React)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Session List│  │ Status Bar  │  │    Terminal Pane        │ │
│  │             │  │             │  │    (xterm.js)           │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                           │ WebSocket                           │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Python)                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    WebSocket Router                         ││
│  │  ┌───────────────┐  ┌───────────────┐  ┌─────────────────┐ ││
│  │  │   Dispatcher  │  │  Rate Limiter │  │ Connection Mgr  │ ││
│  │  └───────────────┘  └───────────────┘  └─────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   Session Manager                           ││
│  │  ┌───────────────┐  ┌───────────────┐  ┌─────────────────┐ ││
│  │  │  PTY Process  │  │  PTY Process  │  │   ... (up to 10)│ ││
│  │  │  (copilot.exe)│  │  (copilot.exe)│  │                 │ ││
│  │  └───────────────┘  └───────────────┘  └─────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   Persistence Layer                         ││
│  │  ┌───────────────┐  ┌───────────────┐  ┌─────────────────┐ ││
│  │  │  Index Store  │  │  Meta Store   │  │ Transcript Store│ ││
│  │  │  (index.json) │  │  (meta.json)  │  │ (transcript.jsonl)│||
│  │  └───────────────┘  └───────────────┘  └─────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Components

### Frontend (React + TypeScript)

The frontend is a single-page application built with React and Vite.

#### Key Components

| Component | Purpose |
|-----------|---------|
| `App.tsx` | Main layout, state management, session coordination |
| `SessionList.tsx` | Displays list of sessions with status indicators |
| `TerminalPane.tsx` | xterm.js terminal emulator integration |
| `StatusBar.tsx` | Connection status and server time display |

#### WebSocket Client

The `wsClient.ts` module manages WebSocket communication:

- Automatic reconnection with exponential backoff
- Message type validation using Zod schemas
- Subscription-based message handling
- Type-safe message sending

### Backend (FastAPI + Python)

The backend is a FastAPI application that handles WebSocket connections and manages PTY processes.

#### Module Responsibilities

| Module | Purpose |
|--------|---------|
| `app/main.py` | FastAPI app, static file serving, lifespan management |
| `app/config.py` | Environment-based configuration with Pydantic |
| `app/ws/router.py` | WebSocket endpoint and connection handling |
| `app/ws/dispatcher.py` | Message routing to handlers |
| `app/ws/protocol.py` | Message schemas with Pydantic validation |
| `app/sessions/manager.py` | Session lifecycle, PTY coordination |
| `app/sessions/pty_process.py` | Windows ConPTY wrapper using pywinpty |
| `app/persistence/index_store.py` | Session index management |
| `app/persistence/meta_store.py` | Session metadata persistence |
| `app/persistence/transcript_store.py` | JSONL event logging |

### Design Patterns

#### 1. Message Dispatcher Pattern

All WebSocket messages are routed through a central dispatcher that:
- Validates message format using Pydantic
- Routes to type-specific handlers
- Provides consistent error handling

```python
dispatcher.register("session.create", handle_session_create)
dispatcher.register("term.in", handle_term_in)
```

#### 2. Session Manager (In-Memory Registry)

The session manager maintains active sessions in memory:
- Enforces MAX_SESSIONS limit
- Maps session IDs to PTY instances
- Tracks attached clients per session

#### 3. Append-Only Event Sourcing

Transcripts use JSONL format for append-only event logging:
- Each event has a monotonically increasing sequence number
- Events are immutable once written
- Enables deterministic replay and debugging

#### 4. Atomic File Write Pattern

JSON persistence files use atomic writes:
1. Write to temporary file
2. Flush and sync to disk
3. Atomic rename to target path

This prevents partial writes and ensures file integrity.

## Data Model

### Session (meta.json)

```json
{
  "sessionId": "uuid",
  "status": "running|exited",
  "createdAt": "ISO-8601",
  "lastActivityAt": "ISO-8601",
  "workspacePath": "C:\\path\\to\\workspace",
  "pid": 12345,
  "cols": 120,
  "rows": 30,
  "exitCode": null,
  "copilotPath": "copilot.exe",
  "error": null
}
```

### Transcript Event (transcript.jsonl)

Each line is a JSON object:

```json
{"ts": "ISO-8601", "sessionId": "uuid", "seq": 1, "type": "out", "data": "..."}
{"ts": "ISO-8601", "sessionId": "uuid", "seq": 2, "type": "in", "data": "..."}
{"ts": "ISO-8601", "sessionId": "uuid", "seq": 3, "type": "resize", "cols": 80, "rows": 24}
{"ts": "ISO-8601", "sessionId": "uuid", "seq": 4, "type": "lifecycle", "event": "exited", "detail": {"exitCode": 0}}
```

### Session Index (index.json)

```json
{
  "protocolVersion": 1,
  "updatedAt": "ISO-8601",
  "sessions": [
    {
      "sessionId": "uuid",
      "status": "running",
      "createdAt": "ISO-8601",
      "lastActivityAt": "ISO-8601"
    }
  ]
}
```

## WebSocket Protocol

### Connection Flow

1. Client connects to `ws://127.0.0.1:5000/ws`
2. Server sends `server.hello` with protocol version
3. Client can send any message type

### Message Types

#### Client → Server

| Type | Purpose |
|------|---------|
| `session.create` | Create a new session |
| `session.attach` | Attach to existing session |
| `session.list` | List all sessions |
| `session.terminate` | Terminate a session |
| `term.in` | Send terminal input |
| `term.resize` | Resize terminal dimensions |

#### Server → Client

| Type | Purpose |
|------|---------|
| `server.hello` | Initial connection greeting |
| `session.created` | Session creation response |
| `session.attached` | Attach confirmation |
| `session.list.result` | List of sessions |
| `session.exited` | Session exit notification |
| `term.out` | Terminal output data |
| `error` | Error response |

## Security

### Localhost Binding

By default, the server only binds to `127.0.0.1`. Non-localhost connections are rejected with:
- HTTP 403 for HTTP requests
- WebSocket close code 1008 for WS connections

### Input Validation

All messages are validated using Pydantic with `extra="forbid"` to reject unknown fields.

### Rate Limiting

WebSocket connections are rate-limited to 200 messages per second per client.

### Copilot-Only Enforcement

The server only spawns the configured `COPILOT_PATH` executable. No arbitrary command execution is possible.

## Performance

### Targets

| Metric | Target |
|--------|--------|
| WebSocket connect | ≤ 500ms |
| Session creation | ≤ 1000ms |
| Terminal output latency | ≤ 200ms |
| Maximum sessions | 10 concurrent |

### Optimizations

- Async I/O for all file operations
- PTY read loop runs in thread pool executor
- Rate limiting prevents resource exhaustion
