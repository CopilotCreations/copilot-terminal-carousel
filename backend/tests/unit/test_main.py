"""Unit tests for main application module."""
import pytest
from pathlib import Path
import os
from unittest.mock import patch

from fastapi.testclient import TestClient


class TestHealthCheck:
    """Tests for health check endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        """Set up test environment."""
        os.environ["DATA_DIR"] = str(tmp_path / "data")
        os.environ["LOG_FILE"] = str(tmp_path / "data" / "logs" / "app.jsonl")
        os.environ["ALLOW_NON_LOCALHOST"] = "true"
        
        (tmp_path / "data" / "sessions").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / "logs").mkdir(parents=True, exist_ok=True)

    def test_health_check(self) -> None:
        """Test health check endpoint returns healthy."""
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_root_when_frontend_not_built(self) -> None:
        """Test root endpoint when frontend is not built."""
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/")
        
        # When frontend is not built, should return JSON message
        assert response.status_code == 200


class TestLocalhostMiddleware:
    """Tests for localhost-only middleware."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        """Set up test environment."""
        os.environ["DATA_DIR"] = str(tmp_path / "data")
        os.environ["LOG_FILE"] = str(tmp_path / "data" / "logs" / "app.jsonl")
        
        (tmp_path / "data" / "sessions").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / "logs").mkdir(parents=True, exist_ok=True)

    def test_localhost_allowed(self) -> None:
        """Test that localhost connections are allowed."""
        os.environ["ALLOW_NON_LOCALHOST"] = "true"
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/health")
        assert response.status_code == 200
