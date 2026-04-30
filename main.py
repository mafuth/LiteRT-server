"""LiteRT-LM OpenAI-compatible inference server."""

import time
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lib.classes.llmEngine import LlmEngine
from lib.classes.logger import LoggerManager
from routes import chat

from lib.config import (
    APP_TITLE,
    APP_DESCRIPTION,
    APP_VERSION,
    CORS_ALLOW_ORIGINS,
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS,
)

logger = LoggerManager("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    logger.info(f"Starting {APP_TITLE}")

    llm = LlmEngine()
    llm.load()  # load model at startup - eliminates cold-start on first request
    app.state.llmEngine = llm

    yield

    logger.info(f"Shutting down {APP_TITLE}")
    LoggerManager.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Create FastAPI app with lifespan context manager
    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOW_ORIGINS,
        allow_credentials=CORS_ALLOW_CREDENTIALS,
        allow_methods=CORS_ALLOW_METHODS,
        allow_headers=CORS_ALLOW_HEADERS,
    )

    app.include_router(chat.router, prefix="/v1")

    return app

# Create the application instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "title": APP_TITLE,
        "version": APP_VERSION,
        "redoc": "/redoc",
        "swagger": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with async Redis operations and database health monitoring"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": APP_VERSION,
    }


if __name__ == "__main__":
    import uvicorn
    from lib.config import (
        UVICORN_HOST,
        UVICORN_PORT,
        UVICORN_RELOAD,
        UVICORN_WORKERS,
        UVICORN_LOOP,
        UVICORN_HTTP,
        UVICORN_ACCESS_LOG,
    )

    workers = UVICORN_WORKERS
    reload = UVICORN_RELOAD

    if reload and workers > 1:
        logger.warning(
            "UVICORN_RELOAD=true is incompatible with multiple workers. Forcing workers=1."
        )
        workers = 1

    if workers > 1:
        logger.warning(
            f"UVICORN_WORKERS={workers}: each worker process loads its own model copy. "
            "The asyncio lock does not serialize across processes. "
            "Set UVICORN_WORKERS=1 unless you have enough memory for multiple model copies."
        )

    uvicorn.run(
        "main:app",
        host=UVICORN_HOST,
        port=UVICORN_PORT,
        reload=reload,
        workers=workers,
        loop=UVICORN_LOOP,
        http=UVICORN_HTTP,
        access_log=UVICORN_ACCESS_LOG,
    )
    sys.exit(0)
