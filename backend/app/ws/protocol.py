"""WebSocket protocol message models with strict validation."""
from datetime import datetime, timezone
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# Client -> Server Messages
# ============================================================================


class SessionCreateMessage(BaseModel):
    """Client request to create a new session."""

    model_config = ConfigDict(extra="forbid")
    
    type: Literal["session.create"]


class SessionAttachMessage(BaseModel):
    """Client request to attach to an existing session."""

    model_config = ConfigDict(extra="forbid")
    
    type: Literal["session.attach"]
    sessionId: str = Field(..., min_length=36, max_length=36)


class SessionListMessage(BaseModel):
    """Client request to list all sessions."""

    model_config = ConfigDict(extra="forbid")
    
    type: Literal["session.list"]

class SessionTerminateMessage(BaseModel):
    """Client request to terminate a session."""

    model_config = ConfigDict(extra="forbid")
    
    type: Literal["session.terminate"]
    sessionId: str = Field(..., min_length=36, max_length=36)


class SessionRenameMessage(BaseModel):
    """Client request to rename a session."""

    model_config = ConfigDict(extra="forbid")
    
    type: Literal["session.rename"]
    sessionId: str = Field(..., min_length=36, max_length=36)
    name: str = Field(..., min_length=1, max_length=100)


class TerminalInputMessage(BaseModel):
    """Client terminal input data."""

    model_config = ConfigDict(extra="forbid")
    
    type: Literal["term.in"]
    sessionId: str = Field(..., min_length=36, max_length=36)
    data: str


class TerminalResizeMessage(BaseModel):
    """Client terminal resize request."""

    model_config = ConfigDict(extra="forbid")
    
    type: Literal["term.resize"]
    sessionId: str = Field(..., min_length=36, max_length=36)
    cols: int = Field(..., ge=1)
    rows: int = Field(..., ge=1)


# Union of all client messages
ClientMessage = Annotated[
    Union[
        SessionCreateMessage,
        SessionAttachMessage,
        SessionListMessage,
        SessionTerminateMessage,
        SessionRenameMessage,
        TerminalInputMessage,
        TerminalResizeMessage,
    ],
    Field(discriminator="type"),
]


# ============================================================================
# Server -> Client Messages
# ============================================================================


class SessionInfo(BaseModel):
    """Session information included in server responses."""

    sessionId: str
    status: Literal["running", "exited"]
    createdAt: str
    lastActivityAt: str
    workspacePath: str
    pid: int | None
    cols: int
    rows: int
    exitCode: int | None = None
    copilotPath: str | None = None
    error: dict[str, str] | None = None


class SessionIndexEntry(BaseModel):
    """Session entry in the session list."""

    sessionId: str
    status: Literal["running", "exited"]
    createdAt: str
    lastActivityAt: str
    name: str | None = None


class ServerHelloMessage(BaseModel):
    """Server hello message sent on connection."""

    type: Literal["server.hello"] = "server.hello"
    serverTime: str
    protocolVersion: int = 1


class SessionCreatedMessage(BaseModel):
    """Server response to session creation."""

    type: Literal["session.created"] = "session.created"
    session: SessionInfo


class SessionAttachedMessage(BaseModel):
    """Server response to session attach."""

    type: Literal["session.attached"] = "session.attached"
    sessionId: str
    status: Literal["running", "exited"]


class SessionListResultMessage(BaseModel):
    """Server response with list of sessions."""

    type: Literal["session.list.result"] = "session.list.result"
    sessions: list[SessionIndexEntry]


class SessionExitedMessage(BaseModel):
    """Server notification that a session has exited."""

    type: Literal["session.exited"] = "session.exited"
    sessionId: str
    exitCode: int | None


class SessionRenamedMessage(BaseModel):
    """Server response to session rename."""

    type: Literal["session.renamed"] = "session.renamed"
    sessionId: str
    name: str


class TerminalOutputMessage(BaseModel):
    """Server terminal output data."""

    type: Literal["term.out"] = "term.out"
    sessionId: str
    data: str


class ErrorMessage(BaseModel):
    """Server error message."""

    type: Literal["error"] = "error"
    code: str
    message: str


# Error codes
class ErrorCodes:
    """Standard error codes."""

    INVALID_MESSAGE = "INVALID_MESSAGE"
    UNKNOWN_MESSAGE_TYPE = "UNKNOWN_MESSAGE_TYPE"
    MAX_SESSIONS_REACHED = "MAX_SESSIONS_REACHED"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SPAWN_FAILED = "SPAWN_FAILED"
    INPUT_TOO_LARGE = "INPUT_TOO_LARGE"
    INVALID_RESIZE = "INVALID_RESIZE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    NOT_ATTACHED = "NOT_ATTACHED"


def parse_client_message(data: dict[str, object]) -> ClientMessage:
    """Parse and validate a client message from raw dict.

    Args:
        data: Raw message dictionary from WebSocket

    Returns:
        Validated client message

    Raises:
        ValueError: If message validation fails
    """
    msg_type = data.get("type")
    if msg_type == "session.create":
        return SessionCreateMessage(**data)  # type: ignore[arg-type]
    elif msg_type == "session.attach":
        return SessionAttachMessage(**data)  # type: ignore[arg-type]
    elif msg_type == "session.list":
        return SessionListMessage(**data)  # type: ignore[arg-type]
    elif msg_type == "session.terminate":
        return SessionTerminateMessage(**data)  # type: ignore[arg-type]
    elif msg_type == "session.rename":
        return SessionRenameMessage(**data)  # type: ignore[arg-type]
    elif msg_type == "term.in":
        return TerminalInputMessage(**data)  # type: ignore[arg-type]
    elif msg_type == "term.resize":
        return TerminalResizeMessage(**data)  # type: ignore[arg-type]
    else:
        raise ValueError(f"Unknown message type: {msg_type}")


def utc_now_iso() -> str:
    """Get current UTC time as ISO-8601 string.

    Returns:
        str: Current UTC timestamp in ISO-8601 format with millisecond
            precision (e.g., '2026-01-05T02:04:52.557Z').
    """
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
