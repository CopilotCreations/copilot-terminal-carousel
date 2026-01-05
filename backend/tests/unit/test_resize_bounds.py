"""Unit tests for terminal resize bounds validation."""
import pytest
from pathlib import Path

from app.config import Settings


class TestResizeBounds:
    """Tests for resize bounds validation."""

    def test_default_bounds(self) -> None:
        """Test default resize bounds are set correctly.

        Verifies that the Settings class initializes with the expected
        default minimum and maximum values for columns and rows.
        """
        settings = Settings()
        assert settings.MIN_COLS == 20
        assert settings.MAX_COLS == 300
        assert settings.MIN_ROWS == 5
        assert settings.MAX_ROWS == 120

    def test_initial_dimensions(self) -> None:
        """Test initial terminal dimensions.

        Verifies that the Settings class initializes with the expected
        default values for initial columns and rows.
        """
        settings = Settings()
        assert settings.INITIAL_COLS == 120
        assert settings.INITIAL_ROWS == 30

    def test_initial_within_bounds(self) -> None:
        """Test that initial dimensions are within bounds.

        Verifies that the default initial column and row values fall
        within the configured minimum and maximum bounds.
        """
        settings = Settings()
        assert settings.MIN_COLS <= settings.INITIAL_COLS <= settings.MAX_COLS
        assert settings.MIN_ROWS <= settings.INITIAL_ROWS <= settings.MAX_ROWS


class TestResizeValidation:
    """Tests for resize value validation logic."""

    @pytest.fixture
    def settings(self) -> Settings:
        """Get settings instance.

        Returns:
            Settings: A new Settings instance for testing.
        """
        return Settings()

    def test_valid_cols_range(self, settings: Settings) -> None:
        """Test valid column values.

        Args:
            settings: The Settings fixture instance.
        """
        valid_cols = [20, 80, 120, 200, 300]
        for cols in valid_cols:
            assert settings.MIN_COLS <= cols <= settings.MAX_COLS

    def test_invalid_cols_below_min(self, settings: Settings) -> None:
        """Test columns below minimum are invalid.

        Args:
            settings: The Settings fixture instance.
        """
        invalid_cols = [0, 1, 10, 19]
        for cols in invalid_cols:
            assert cols < settings.MIN_COLS

    def test_invalid_cols_above_max(self, settings: Settings) -> None:
        """Test columns above maximum are invalid.

        Args:
            settings: The Settings fixture instance.
        """
        invalid_cols = [301, 400, 1000]
        for cols in invalid_cols:
            assert cols > settings.MAX_COLS

    def test_valid_rows_range(self, settings: Settings) -> None:
        """Test valid row values.

        Args:
            settings: The Settings fixture instance.
        """
        valid_rows = [5, 24, 30, 50, 120]
        for rows in valid_rows:
            assert settings.MIN_ROWS <= rows <= settings.MAX_ROWS

    def test_invalid_rows_below_min(self, settings: Settings) -> None:
        """Test rows below minimum are invalid.

        Args:
            settings: The Settings fixture instance.
        """
        invalid_rows = [0, 1, 2, 4]
        for rows in invalid_rows:
            assert rows < settings.MIN_ROWS

    def test_invalid_rows_above_max(self, settings: Settings) -> None:
        """Test rows above maximum are invalid.

        Args:
            settings: The Settings fixture instance.
        """
        invalid_rows = [121, 200, 500]
        for rows in invalid_rows:
            assert rows > settings.MAX_ROWS

    def test_boundary_values(self, settings: Settings) -> None:
        """Test exact boundary values.

        Args:
            settings: The Settings fixture instance.
        """
        # Exact minimums
        assert settings.MIN_COLS == 20
        assert settings.MIN_ROWS == 5

        # Exact maximums
        assert settings.MAX_COLS == 300
        assert settings.MAX_ROWS == 120

    def test_max_input_chars(self, settings: Settings) -> None:
        """Test max input characters limit.

        Args:
            settings: The Settings fixture instance.
        """
        assert settings.MAX_INPUT_CHARS_PER_MESSAGE == 16384
