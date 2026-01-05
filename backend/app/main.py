"""FastAPI application main module."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.logging_setup import setup_logging, get_logger
from app.sessions.manager import session_manager
from app.ws.router import router as ws_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle for startup and shutdown.

    Args:
        app: The FastAPI application instance.

    Yields:
        None: Control is yielded to the application after startup completes.
    """
    # Startup
    setup_logging()

    # Validate localhost binding
    settings.validate_localhost_binding()

    # Ensure data directories exist
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Application starting",
        extra={
            "host": settings.HOST,
            "port": settings.PORT,
            "dataDir": str(settings.DATA_DIR),
        },
    )

    yield

    # Shutdown
    logger.info("Application shutting down")
    await session_manager.shutdown()


app = FastAPI(
    title="Copilot Terminal Carousel",
    description="Browser-based terminal UI for GitHub Copilot CLI",
    version="1.0.0",
    lifespan=lifespan,
)


# Middleware to enforce localhost-only access
@app.middleware("http")
async def localhost_only_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Enforce localhost-only access for HTTP requests.

    Args:
        request: The incoming HTTP request.
        call_next: The next middleware or route handler in the chain.

    Returns:
        JSONResponse with 403 status if access is denied, otherwise the
        response from the next handler.
    """
    client_host = request.client.host if request.client else None

    if client_host != "127.0.0.1" and not settings.ALLOW_NON_LOCALHOST:
        return JSONResponse(
            status_code=403,
            content={"detail": "Access denied: localhost only"},
        )

    return await call_next(request)


# Include WebSocket router
app.include_router(ws_router)


# Serve frontend static files
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    # Mount static assets
    app.mount(
        "/assets",
        StaticFiles(directory=frontend_dist / "assets"),
        name="assets",
    )

    @app.get("/")
    async def serve_index() -> FileResponse:
        """Serve the SPA index.html file.

        Returns:
            FileResponse: The index.html file with text/html media type.
        """
        return FileResponse(frontend_dist / "index.html", media_type="text/html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        """Serve static files or fallback to index.html for client-side routing.

        Args:
            full_path: The requested URL path.

        Returns:
            FileResponse: The requested file if it exists, otherwise index.html.
        """
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html", media_type="text/html")
else:
    @app.get("/")
    async def no_frontend() -> JSONResponse:
        """Return a message indicating the frontend is not built.

        Returns:
            JSONResponse: A message with instructions to build the frontend.
        """
        return JSONResponse(
            content={
                "message": "Frontend not built. Run 'npm run build' in the frontend directory.",
                "api": "WebSocket available at /ws",
            }
        )


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return the health status of the application.

    Returns:
        dict[str, str]: A dictionary containing the health status.
    """
    return {"status": "healthy"}
