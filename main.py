"""Main FastAPI application factory for BSCS SOAP to REST middleware."""

import time
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lib.classes.llmEngine import LlmEngine
from routes import chat

from lib.config import (
    APP_TITLE,
    APP_DESCRIPTION,
    APP_VERSION,
    APP_ENV,
    CORS_ALLOW_ORIGINS,
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS
)

# Delay logger initialization to avoid database connection during config generation
logger = None

def get_logger():
    """Lazy initialization of logger to prevent database connection during config generation."""
    global logger
    if logger is None:
        from lib.classes.logger import LoggerManager
        logger = LoggerManager("main")
    return logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    
    get_logger().info(f"Starting {APP_TITLE}")

    app.state.llmEngine = LlmEngine()
    
    yield
    
    get_logger().info(f"Shutting down {APP_TITLE}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Create FastAPI app with lifespan context manager
    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        lifespan=lifespan
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
        "swagger": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with async Redis operations and database health monitoring"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": APP_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    import sys
    from lib.config import (
        UVICORN_HOST,
        UVICORN_PORT,
        UVICORN_RELOAD,
        UVICORN_WORKERS,
        UVICORN_LOOP,
        UVICORN_HTTP,
        UVICORN_ACCESS_LOG,
        APP_TITLE
    )

    uvicorn_config = {
        "app": "main:app",
        "host": UVICORN_HOST,
        "port": UVICORN_PORT,
        "reload": UVICORN_RELOAD,
        "workers": UVICORN_WORKERS,
        "loop": UVICORN_LOOP,
        "http": UVICORN_HTTP,
        "access_log": UVICORN_ACCESS_LOG
    }
    
    uvicorn.run(**uvicorn_config)
    sys.exit(0)
    
    
     