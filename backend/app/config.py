"""Application configuration loaded from environment variables."""
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Server binding
    HOST: str = "127.0.0.1"
    PORT: int = 5000

    # Data directory
    DATA_DIR: Path = Path("./data")

    # Copilot executable
    COPILOT_PATH: str = "copilot.exe"

    # Session limits
    MAX_SESSIONS: int = 10

    # Terminal dimensions
    INITIAL_COLS: int = 120
    INITIAL_ROWS: int = 30
    MIN_COLS: int = 20
    MAX_COLS: int = 300
    MIN_ROWS: int = 5
    MAX_ROWS: int = 120

    # Input limits
    MAX_INPUT_CHARS_PER_MESSAGE: int = 16384

    # Logging
    LOG_FILE: Path = Path("./data/logs/app.jsonl")
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # WebSocket limits
    WS_MAX_MESSAGE_BYTES: int = 1048576  # 1 MiB

    # Security
    ALLOW_NON_LOCALHOST: bool = False

    @field_validator("DATA_DIR", "LOG_FILE", mode="before")
    @classmethod
    def convert_to_path(cls, v: str | Path) -> Path:
        """Convert string paths to Path objects."""
        return Path(v) if isinstance(v, str) else v

    @property
    def sessions_dir(self) -> Path:
        """Get the sessions directory path."""
        return self.DATA_DIR / "sessions"

    @property
    def logs_dir(self) -> Path:
        """Get the logs directory path."""
        return self.DATA_DIR / "logs"

    def get_sessions_dir(self) -> Path:
        """Get sessions directory (for testing compatibility)."""
        return self.sessions_dir

    def get_logs_dir(self) -> Path:
        """Get logs directory (for testing compatibility)."""
        return self.logs_dir

    def validate_localhost_binding(self) -> None:
        """Validate that the server is bound to localhost unless explicitly allowed."""
        if self.HOST != "127.0.0.1" and not self.ALLOW_NON_LOCALHOST:
            raise ValueError(
                f"Server must bind to 127.0.0.1 unless ALLOW_NON_LOCALHOST=true. "
                f"Got HOST={self.HOST}"
            )


# Global settings instance
settings = Settings()
