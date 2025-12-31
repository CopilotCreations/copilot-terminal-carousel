# Copilot Prompt

This file contains the original prompt given to GitHub Copilot to create this project.

## Prompt

## PROJECT SPECIFICATION

### 1. Project Overview
This project is a Windows-only localhost web application that provides a browser-based, fully interactive terminal UI connected to GitHub Copilot CLI (`copilot.exe`). Users can create and manage up to 10 concurrent Copilot-only terminal sessions, each running in its own dedicated workspace directory. The browser streams terminal output in realtime and sends keystrokes/resizes back to the Copilot process via WebSockets. All session metadata and terminal transcripts are persisted to local JSON/JSONL files for later inspection and reconnection.

---

### 2. Tech Stack (EXPLICIT)
- Language: **Python 3.12.7** (backend), **TypeScript 5.6.3** (frontend)
- Framework:
  - Backend: **FastAPI 0.115.6**, **Uvicorn 0.32.1**
  - Frontend: **React 18.3.1** built with **Vite 5.4.11**
- Database: **Local filesystem persistence (no RDBMS)** using:
  - `index.json` (session metadata)
  - `transcript.jsonl` (append-only event log)
- Additional tools / dependencies (exact packages and purpose):
  - Backend:
    - `pywinpty 2.0.13`: Windows ConPTY-backed pseudo-terminal to run `copilot.exe` interactively
    - `pydantic 2.10.3`: strict schema validation for WebSocket messages and config
    - `python-json-logger 2.0.7`: JSON log formatting to file
    - `aiofiles 24.1.0`: async file writes for transcript persistence
  - Frontend:
    - `xterm 5.5.0`: terminal emulator in browser
    - `@xterm/addon-fit 0.10.0`: auto-fit terminal to container size
    - `@xterm/addon-web-links 0.11.0`: clickable links in terminal output
    - `zod 3.23.8`: runtime validation of WS messages on client
  - Tooling:
    - `pytest 8.3.4`: unit/integration tests
    - `pytest-asyncio 0.24.0`: async test support
    - `coverage 7.6.9`: coverage enforcement
    - `playwright 1.49.1`: end-to-end browser tests
    - `ruff 0.8.2`: linting
    - `black 24.10.0`: formatting
    - `mypy 1.13.0`: static typing checks
- OS target: **Windows 11** (required for ConPTY + `copilot.exe`)

---

### 3. Feature List (EXHAUSTIVE)

#### 3.1. Single-Page Web UI (Terminal Dashboard)
- **Feature Name**: Terminal Dashboard UI
  - User story: "As a user, I want a single page that lists sessions and shows a terminal so that I can create and control Copilot sessions from my browser."
  - Acceptance criteria:
    1. Visiting `http://127.0.0.1:5000/` loads the UI without requiring any login.
    2. The UI displays a “New Session” button.
    3. The UI displays a session list panel showing sessionId, status (running/exited), createdAt, and lastActivityAt.
    4. Clicking a session in the list attaches the terminal view to that session within 1 second on localhost.
  - API endpoint (if applicable): None (static assets served by backend; session operations via WebSocket only).

#### 3.2. WebSocket Connection Management
- **Feature Name**: WebSocket Terminal Transport
  - User story: "As a user, I want realtime streaming over WebSockets so that terminal output and input are responsive."
  - Acceptance criteria:
    1. The client connects to `ws://127.0.0.1:5000/ws` and receives a `server.hello` message within 500ms.
    2. If the WebSocket disconnects, the UI shows “Disconnected” within 250ms and attempts reconnect every 1 second for 30 seconds.
    3. On reconnect, the client can re-attach to an existing session by sending `session.attach`.
  - API endpoint (if applicable):
    - `GET /ws` (WebSocket)
      - Server → Client initial message:
        ```json
        { "type": "server.hello", "serverTime": "2025-01-01T00:00:00.000Z", "protocolVersion": 1 }
        ```

#### 3.3. Create Copilot-Only Session (PTY Spawn)
- **Feature Name**: Create Session (Copilot-only PTY)
  - User story: "As a user, I want to create a new Copilot session so that I can interact with copilot.exe in an isolated workspace."
  - Acceptance criteria:
    1. When the client sends `session.create`, the server creates a new UUIDv4 sessionId.
    2. The server creates a workspace directory at `DATA_DIR/sessions/{sessionId}/workspace`.
    3. The server spawns a PTY process running exactly `COPILOT_PATH` (default `copilot.exe`) with:
       - `cwd = workspace directory`
       - initial terminal size `cols=120`, `rows=30`
    4. The server returns `session.created` containing sessionId and workspacePath within 1 second.
    5. The server enforces `MAX_SESSIONS=10`: if 10 sessions are already running, `session.create` returns an error `MAX_SESSIONS_REACHED`.
  - API endpoint (WebSocket message shapes):
    - Client → Server:
      ```json
      { "type": "session.create" }
      ```
    - Server → Client (success):
      ```json
      {
        "type": "session.created",
        "session": {
          "sessionId": "uuid",
          "status": "running",
          "createdAt": "ISO-8601",
          "lastActivityAt": "ISO-8601",
          "workspacePath": "C:\\path\\to\\data\\sessions\\uuid\\workspace",
          "pid": 12345,
          "cols": 120,
          "rows": 30
        }
      }
      ```
    - Server → Client (error):
      ```json
      { "type": "error", "code": "MAX_SESSIONS_REACHED", "message": "Maximum running sessions (10) reached." }
      ```

#### 3.4. Attach to Existing Session
- **Feature Name**: Attach Session
  - User story: "As a user, I want to attach to an existing session so that I can continue where I left off after refresh or switching sessions."
  - Acceptance criteria:
    1. When the client sends `session.attach` with a valid sessionId, the server responds with `session.attached` within 500ms.
    2. If the session is running, terminal output continues streaming immediately after attach.
    3. If the session has exited, the server responds with `session.attached` and `status="exited"` and does not stream further output.
    4. If the sessionId does not exist, the server returns error `SESSION_NOT_FOUND`.
  - API endpoint (WebSocket message shapes):
    - Client → Server:
      ```json
      { "type": "session.attach", "sessionId": "uuid" }
      ```
    - Server → Client:
      ```json
      { "type": "session.attached", "sessionId": "uuid", "status": "running" }
      ```
    - Error:
      ```json
      { "type": "error", "code": "SESSION_NOT_FOUND", "message": "Session does not exist: uuid" }
      ```

#### 3.5. Realtime Terminal Output Streaming
- **Feature Name**: Stream PTY Output to Browser
  - User story: "As a user, I want to see Copilot output in realtime so that I can interact naturally."
  - Acceptance criteria:
    1. Any bytes read from the PTY are forwarded to the attached client as `term.out` messages in the same order.
    2. Output is delivered with end-to-end latency under 200ms on localhost for typical output (<4KB bursts).
    3. ANSI escape sequences are preserved (not stripped) so xterm.js renders colors/cursor movement.
  - API endpoint (WebSocket message shapes):
    - Server → Client:
      ```json
      { "type": "term.out", "sessionId": "uuid", "data": "raw string including ANSI" }
      ```

#### 3.6. Interactive Terminal Input (Keystrokes)
- **Feature Name**: Send Keystrokes to PTY
  - User story: "As a user, I want my keystrokes to control Copilot so that the browser terminal behaves like a real terminal."
  - Acceptance criteria:
    1. The client sends each input chunk as `term.in` with UTF-8 string data.
    2. The server writes the input bytes to the PTY stdin in the same order received.
    3. Special keys supported by xterm.js (Enter, Backspace, arrows, Ctrl+C) must affect the Copilot process as they do in a native terminal.
    4. The server rejects any `term.in` message where `data` length exceeds `MAX_INPUT_CHARS_PER_MESSAGE=16384` and returns error `INPUT_TOO_LARGE`.
  - API endpoint (WebSocket message shapes):
    - Client → Server:
      ```json
      { "type": "term.in", "sessionId": "uuid", "data": "string" }
      ```
    - Error:
      ```json
      { "type": "error", "code": "INPUT_TOO_LARGE", "message": "Input exceeds 16384 characters." }
      ```

#### 3.7. Terminal Resize Support
- **Feature Name**: Resize PTY on Browser Resize
  - User story: "As a user, I want resizing the browser terminal to resize the underlying PTY so that full-screen apps and wrapping behave correctly."
  - Acceptance criteria:
    1. When the terminal container size changes, the client sends `term.resize` with integer cols/rows.
    2. The server applies the resize to the PTY within 250ms.
    3. The server rejects resize values outside bounds:
       - `MIN_COLS=20`, `MAX_COLS=300`
       - `MIN_ROWS=5`, `MAX_ROWS=120`
       and returns error `INVALID_RESIZE`.
  - API endpoint (WebSocket message shapes):
    - Client → Server:
      ```json
      { "type": "term.resize", "sessionId": "uuid", "cols": 120, "rows": 30 }
      ```
    - Error:
      ```json
      { "type": "error", "code": "INVALID_RESIZE", "message": "cols must be 20-300 and rows must be 5-120." }
      ```

#### 3.8. Session Termination
- **Feature Name**: Terminate Session
  - User story: "As a user, I want to terminate a session so that I can stop the Copilot process and free resources."
  - Acceptance criteria:
    1. When the client sends `session.terminate`, the server terminates the PTY process within 2 seconds.
    2. The server marks the session status as `exited` and records `exitCode` (or `null` if unavailable).
    3. The server sends `session.exited` to all clients attached to that session.
  - API endpoint (WebSocket message shapes):
    - Client → Server:
      ```json
      { "type": "session.terminate", "sessionId": "uuid" }
      ```
    - Server → Client:
      ```json
      { "type": "session.exited", "sessionId": "uuid", "exitCode": 0 }
      ```

#### 3.9. Session Listing (Persisted + In-Memory)
- **Feature Name**: List Sessions
  - User story: "As a user, I want to see existing sessions so that I can reattach or inspect past runs."
  - Acceptance criteria:
    1. On UI load, the client requests `session.list`.
    2. The server returns all sessions found in `DATA_DIR/sessions/index.json` sorted by `createdAt` descending.
    3. Each list item includes `sessionId`, `status`, `createdAt`, `lastActivityAt`.
  - API endpoint (WebSocket message shapes):
    - Client → Server:
      ```json
      { "type": "session.list" }
      ```
    - Server → Client:
      ```json
      { "type": "session.list.result", "sessions": [ { "sessionId":"uuid", "status":"running", "createdAt":"ISO", "lastActivityAt":"ISO" } ] }
      ```

#### 3.10. Persistence of Transcripts and Metadata
- **Feature Name**: Persist Session Metadata + Transcript
  - User story: "As a user, I want session history persisted so that I can review what happened after the session ends."
  - Acceptance criteria:
    1. On `session.create`, the server creates:
       - `DATA_DIR/sessions/{sessionId}/meta.json`
       - `DATA_DIR/sessions/{sessionId}/transcript.jsonl`
    2. Every `term.out`, `term.in`, and `term.resize` event is appended as one JSON line to `transcript.jsonl` within 250ms of occurrence.
    3. `meta.json` is updated on:
       - session creation
       - attach
       - exit
       - terminate
       and always remains valid JSON.
    4. `index.json` is updated to include the session on creation and to reflect status changes on exit.
  - API endpoint: None (internal behavior triggered by WS messages).

#### 3.11. Static Asset Serving
- **Feature Name**: Serve Frontend from Backend
  - User story: "As a user, I want to run a single command to start the app so that I can access the UI at localhost:5000."
  - Acceptance criteria:
    1. Backend serves built frontend assets from `frontend/dist`.
    2. `GET /` returns the SPA HTML.
    3. `GET /assets/*` returns JS/CSS with correct content-type.
  - API endpoint:
    - `GET /` → `text/html`
    - `GET /assets/{file}` → static

---

### 4. Data Model

#### 4.1. Session (persisted in `meta.json` and referenced in `index.json`)
- Fields:
  - `sessionId: string` — UUIDv4, required, immutable
  - `status: "running" | "exited"` — required
  - `createdAt: string` — ISO-8601 UTC timestamp, required
  - `lastActivityAt: string` — ISO-8601 UTC timestamp, required; updated on any input/output/resize
  - `workspacePath: string` — absolute Windows path, required
  - `pid: number | null` — required; set when spawned; null if spawn failed
  - `cols: number` — required; initial 120; updated on resize
  - `rows: number` — required; initial 30; updated on resize
  - `exitCode: number | null` — required; null while running
  - `copilotPath: string` — required; resolved executable path used
  - `error: { code: string, message: string } | null` — required; set if spawn fails
- Constraints:
  - `sessionId` unique across all sessions.
  - `workspacePath` must be under `DATA_DIR/sessions/{sessionId}/workspace`.
  - `cols` in `[20, 300]`, `rows` in `[5, 120]`.

#### 4.2. Transcript Event (each line in `transcript.jsonl`)
- Common fields:
  - `ts: string` — ISO-8601 UTC timestamp, required
  - `sessionId: string` — UUIDv4, required
  - `seq: number` — monotonically increasing integer starting at 1 per session, required
  - `type: "out" | "in" | "resize" | "lifecycle"` — required
- Type-specific fields:
  - If `type="out"`:
    - `data: string` — raw output chunk (may include ANSI), required
  - If `type="in"`:
    - `data: string` — raw input chunk, required
  - If `type="resize"`:
    - `cols: number` — required
    - `rows: number` — required
  - If `type="lifecycle"`:
    - `event: "created" | "attached" | "exited" | "terminated" | "spawn_failed"` — required
    - `detail: object` — required; contains event-specific info (e.g., exitCode)
- Constraints:
  - `seq` increments by 1 for each appended event.
  - Each JSONL line must be a single JSON object with no trailing commas.

#### 4.3. Index (persisted in `DATA_DIR/sessions/index.json`)
- Structure:
  - `{ "protocolVersion": 1, "updatedAt": "ISO-8601", "sessions": SessionIndexEntry[] }`
- `SessionIndexEntry` fields:
  - `sessionId: string`
  - `status: "running" | "exited"`
  - `createdAt: string`
  - `lastActivityAt: string`

Relationships:
- `index.json.sessions[*].sessionId` references `Session.sessionId`.
- Each session has exactly one `meta.json` and one `transcript.jsonl`.

---

### 5. Architecture & Design Patterns

#### 5.1. Directory structure (explicit)
```text
repo-root/
  backend/
    pyproject.toml
    README.md
    app/
      __init__.py
      main.py                 # FastAPI app, static mount, WS route registration
      config.py               # Pydantic settings loaded from env
      logging_setup.py        # JSONL file logger configuration
      ws/
        __init__.py
        router.py             # /ws endpoint and connection loop
        protocol.py           # Pydantic models for WS messages (client/server)
        dispatcher.py         # routes messages by type to handlers
      sessions/
        __init__.py
        manager.py            # in-memory session registry + concurrency limits
        pty_process.py        # pywinpty spawn/read/write/resize/terminate
        lifecycle.py          # create/attach/terminate logic
      persistence/
        __init__.py
        index_store.py        # read/write index.json atomically
        meta_store.py         # read/write meta.json atomically
        transcript_store.py   # append JSONL with seq tracking
      util/
        __init__.py
        paths.py              # safe path joins, workspace path enforcement
        time.py               # UTC ISO timestamps
        atomic_write.py       # write temp file then replace
    tests/
      unit/
        test_protocol_validation.py
        test_resize_bounds.py
        test_index_store.py
        test_transcript_store.py
      integration/
        test_ws_create_attach_terminate.py
        test_pty_echo_fixture.py
  frontend/
    package.json
    vite.config.ts
    tsconfig.json
    index.html
    src/
      main.tsx
      App.tsx                 # layout: session list + terminal pane
      api/
        wsClient.ts           # WS connect/reconnect, send/receive typed messages
        messageSchemas.ts     # zod schemas for runtime validation
      components/
        SessionList.tsx
        TerminalPane.tsx      # xterm initialization, input/output wiring, fit addon
        StatusBar.tsx
      styles/
        terminal.css
        app.css
    tests/
      e2e/
        terminal_create_session.spec.ts
  data/                       # created at runtime
    sessions/
      index.json
    logs/
      app.jsonl
  .github/
    workflows/
      ci.yml
  Dockerfile
  docker-compose.yml
```

#### 5.2. Design patterns (explicit + rationale)
- **Message Dispatcher Pattern**: `dispatcher.py` maps `type` → handler function to ensure each WS message has a single, testable handler.
- **Session Manager (In-Memory Registry)**: `manager.py` maintains active sessions, enforces `MAX_SESSIONS`, and maps `sessionId` → PTY instance.
- **Append-Only Event Sourcing for Transcript**: `transcript.jsonl` stores immutable ordered events enabling deterministic replay/debugging.
- **Atomic File Write Pattern**: `atomic_write.py` writes `index.json` and `meta.json` via temp file + replace to prevent partial writes.

#### 5.3. Module responsibilities (explicit)
- `app/main.py`: create FastAPI app; mount static frontend; include WS router; startup/shutdown hooks.
- `app/config.py`: load and validate env vars; expose `Settings` singleton.
- `app/ws/router.py`: accept WS connections; run receive loop; send `server.hello`.
- `app/ws/protocol.py`: Pydantic models for all client/server WS messages; strict validation (`extra="forbid"`).
- `app/ws/dispatcher.py`: validate incoming messages; call session handlers; format errors.
- `app/sessions/pty_process.py`: spawn `copilot.exe` in PTY; async read loop; write input; resize; terminate.
- `app/sessions/manager.py`: create/lookup/terminate sessions; track attached clients per session.
- `app/persistence/*`: read/write index/meta/transcript; ensure directories exist; enforce seq increments.
- `app/logging_setup.py`: configure JSONL logs to `DATA_DIR/logs/app.jsonl`.

---

### 6. Authentication & Authorization
- Auth mechanism: **None**.
- Authorization: **None**.
- Access restriction: backend binds to **`127.0.0.1` only** and rejects any request where `client.host != "127.0.0.1"` with HTTP 403 for HTTP routes and WS close code `1008` for WebSocket.
- User types/roles: **Single implicit local user**.

---

### 7. Error Handling Strategy
- Validation:
  - All incoming WS messages are parsed by Pydantic models with `extra="forbid"`.
  - If parsing fails, server sends:
    ```json
    { "type":"error", "code":"INVALID_MESSAGE", "message":"<pydantic error summary>" }
    ```
- Runtime errors:
  - Any exception in a handler is caught; server logs it with stack trace; client receives:
    ```json
    { "type":"error", "code":"INTERNAL_ERROR", "message":"Unhandled server error. See logs." }
    ```
- PTY errors:
  - If `copilot.exe` fails to spawn, session is created with `status="exited"`, `error` populated, and client receives:
    ```json
    { "type":"error", "code":"SPAWN_FAILED", "message":"Failed to start copilot.exe: <reason>" }
    ```
- WebSocket close behavior:
  - On protocol violation (unknown `type`): send `error` with `UNKNOWN_MESSAGE_TYPE`, then close WS with code `1008`.
  - On normal disconnect: do not terminate sessions; sessions continue running until terminated or exit naturally.
- Logging:
  - Every error response sent to client is logged with fields: `event="ws_error"`, `code`, `sessionId` (if present), `clientId`.

---

### 8. Configuration & Environment
All variables are read by `backend/app/config.py` and validated at startup. Example values shown.

- `HOST` (string): bind host  
  - Example: `127.0.0.1`
- `PORT` (int): bind port  
  - Example: `5000`
- `DATA_DIR` (string): absolute or relative path for persistence and logs  
  - Example: `./data`
- `COPILOT_PATH` (string): executable name or absolute path  
  - Example: `copilot.exe`
- `MAX_SESSIONS` (int): maximum concurrently running sessions  
  - Example: `10`
- `INITIAL_COLS` (int): initial PTY columns  
  - Example: `120`
- `INITIAL_ROWS` (int): initial PTY rows  
  - Example: `30`
- `MIN_COLS` (int): minimum allowed cols on resize  
  - Example: `20`
- `MAX_COLS` (int): maximum allowed cols on resize  
  - Example: `300`
- `MIN_ROWS` (int): minimum allowed rows on resize  
  - Example: `5`
- `MAX_ROWS` (int): maximum allowed rows on resize  
  - Example: `120`
- `MAX_INPUT_CHARS_PER_MESSAGE` (int): maximum `term.in.data` length  
  - Example: `16384`
- `LOG_FILE` (string): path to JSONL log file  
  - Example: `./data/logs/app.jsonl`
- `LOG_LEVEL` (string enum): `DEBUG|INFO|WARNING|ERROR`  
  - Example: `INFO`
- `WS_MAX_MESSAGE_BYTES` (int): maximum raw WS frame size accepted  
  - Example: `1048576` (1 MiB)

---

### 9. Testing Requirements
- Unit test targets (explicit modules/functions):
  - `app/ws/protocol.py`: message parsing rejects unknown fields; required fields enforced.
  - `app/sessions/manager.py`: `create_session` enforces `MAX_SESSIONS`; `attach_session` errors on missing.
  - `app/sessions/pty_process.py`: resize bounds enforcement; terminate idempotency.
  - `app/persistence/index_store.py`: atomic write produces valid JSON; updates reflect status changes.
  - `app/persistence/transcript_store.py`: seq increments; JSONL append format correctness.
  - `app/util/paths.py`: workspace path is always under `DATA_DIR/sessions/{id}/workspace`.
- Minimum coverage: **90% line coverage** on `backend/app/**` excluding `__init__.py`.
- Integration test scenarios (explicit):
  1. WS connect → receive `server.hello`.
  2. `session.create` → `session.created` → receive at least one `term.out` within 5 seconds (using a PTY fixture binary if Copilot not available in CI).
  3. `term.in` sends `\r\n` and output changes (fixture echoes input).
  4. `term.resize` updates stored meta cols/rows and appends resize event to transcript.
  5. `session.terminate` results in `session.exited` and status persisted to `index.json`.
  6. Reconnect flow: create session, disconnect WS, reconnect, `session.attach`, continue streaming.
- Test data approach:
  - Unit tests use `tmp_path` for `DATA_DIR`.
  - Integration tests use a **fixture PTY process**:
    - On Windows CI, spawn `cmd.exe /c more` or a small Python echo script to simulate interactive output.
    - Tests must not require real GitHub authentication.
  - Playwright E2E:
    - Start backend on random port, open UI, click “New Session”, verify terminal renders and session appears in list.

---

### 10. Deployment & CI/CD

#### 10.1. Container (Dockerfile requirements)
- Provide a `Dockerfile` for **Windows containers** only (Linux containers are not supported due to ConPTY + `copilot.exe`).
- Dockerfile must:
  1. Use `mcr.microsoft.com/windows/servercore:ltsc2022` as base.
  2. Install Python 3.12.7.
  3. Copy backend and frontend build output.
  4. Install backend deps via `pip install -r requirements.txt` (generated from `pyproject.toml` lock).
  5. Expose port 5000.
  6. Entrypoint: `python -m uvicorn app.main:app --host 0.0.0.0 --port 5000`
- `docker-compose.yml` must map `5000:5000` and mount `./data` to `C:\app\data`.

#### 10.2. CI pipeline steps (GitHub Actions: `.github/workflows/ci.yml`)
- Runner: `windows-latest`
- Steps (exact):
  1. Checkout repo
  2. Setup Python 3.12
  3. Install backend deps
  4. Run `ruff check backend/app backend/tests`
  5. Run `black --check backend/app backend/tests`
  6. Run `mypy backend/app`
  7. Run `pytest -q --cov=app --cov-fail-under=90`
  8. Setup Node 20.x
  9. Install frontend deps (`npm ci`)
  10. Run `npm run build`
  11. Run Playwright install (`npx playwright install --with-deps`)
  12. Run Playwright tests (`npm run test:e2e`)

#### 10.3. Environment configs (dev/staging/prod)
- Dev (only supported mode per requirements):
  - `HOST=127.0.0.1`
  - `PORT=5000`
  - No TLS
  - No auth
- Staging/prod: **Not supported** in this specification. The application must refuse to start if `HOST` is not `127.0.0.1` unless `ALLOW_NON_LOCALHOST=true` is explicitly set (default false).
  - Add env var:
    - `ALLOW_NON_LOCALHOST` (bool): Example `false`

---

### 11. Non-Functional Requirements

#### 11.1. Performance targets
- WebSocket connect + `server.hello`: **≤ 500ms** on localhost.
- `session.create` → `session.created`: **≤ 1000ms** when `copilot.exe` is available.
- Terminal output latency: **≤ 200ms** for output bursts ≤ 4KB.
- Concurrency: **10 running sessions** with one attached client each.

#### 11.2. Security measures
- Bind to `127.0.0.1` by default; reject non-localhost clients unless `ALLOW_NON_LOCALHOST=true`.
- Input validation:
  - WS messages validated by Pydantic with `extra="forbid"`.
  - `term.in.data` max length 16384 chars.
  - `term.resize` bounds enforced (cols 20–300, rows 5–120).
- Copilot-only enforcement:
  - Server spawns only `COPILOT_PATH` and never spawns `cmd.exe`, `powershell.exe`, or arbitrary commands.
  - No WS message exists to execute arbitrary commands.
- CORS:
  - HTTP CORS disabled; UI served from same origin only.
- Rate limiting:
  - Per WebSocket connection: max **200 messages/second**; exceeding closes WS with code `1011` and logs `RATE_LIMIT_EXCEEDED`.

#### 11.3. Logging
- Log file: `DATA_DIR/logs/app.jsonl`
- Format: one JSON object per line with fields:
  - `ts` (ISO-8601 UTC), `level`, `event`, `message`, `sessionId` (optional), `clientId`, `exception` (optional stack trace)
- Log levels:
  - `DEBUG`: WS message routing decisions, PTY read/write sizes
  - `INFO`: session created/attached/exited/terminated, client connect/disconnect
  - `WARNING`: invalid messages, rate limit exceeded, resize rejected
  - `ERROR`: spawn failures, unhandled exceptions

---

### 12. Implementation Order
1. **Backend config + logging**
   - Implement `config.py`, `logging_setup.py`, create `DATA_DIR` structure on startup.
2. **WS protocol models**
   - Implement `protocol.py` with all message schemas; enforce `protocolVersion=1`.
3. **WS router + dispatcher**
   - Implement `/ws` endpoint, `server.hello`, message receive loop, error formatting.
4. **Persistence layer**
   - Implement `index_store.py`, `meta_store.py`, `transcript_store.py`, atomic writes, JSONL append with seq.
5. **PTY process wrapper**
   - Implement `pty_process.py` using `pywinpty`: spawn `copilot.exe`, async read loop, write, resize, terminate.
6. **Session manager**
   - Implement `manager.py` to track sessions, enforce `MAX_SESSIONS=10`, map sessionId to PTY and attached clients.
7. **WS handlers for session + terminal**
   - Implement handlers for: `session.create`, `session.attach`, `session.list`, `term.in`, `term.resize`, `session.terminate`.
8. **Frontend terminal UI**
   - Implement xterm.js terminal pane, session list, create/attach flows, resize handling via fit addon.
9. **Reconnect logic**
   - Implement WS reconnect loop and attach-to-selected-session behavior.
10. **Testing**
   - Unit tests for protocol, persistence, manager.
   - Integration tests for WS flows using PTY fixture.
   - Playwright E2E tests for UI create session + terminal render.
11. **Packaging + build integration**
   - Build frontend into `frontend/dist`; backend serves static assets; single-command run documented.
12. **Docker + CI**
   - Add Windows Dockerfile + compose; add GitHub Actions workflow executing lint/type/test/build/e2e steps.

---
*Generated on 2025-12-31 14:12:53*
