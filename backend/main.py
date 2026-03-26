"""
main.py - FastAPI application entry point

This is the "front door" of our backend. It:
1. Creates the FastAPI app
2. Sets up CORS for frontend communication
3. Initializes the database on startup
4. Includes all API routes
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env file from backend folder
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)
print(f"[APP] Loaded environment from {env_path}")
print(f"[APP] ANTHROPIC_API_KEY configured: {'Yes' if os.environ.get('ANTHROPIC_API_KEY') else 'No'}")

try:
    from database import init_database
except ImportError:
    from backend.database import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.

    Why use this instead of @app.on_event("startup")?
    - on_event is deprecated in newer FastAPI versions
    - lifespan is the recommended modern approach
    """
    # Startup: Initialize database
    print("[APP] Starting up...")
    init_database()
    print("[APP] Ready to serve requests!")

    yield  # App runs here

    # Shutdown: Cleanup if needed
    print("[APP] Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Retention OS",
    description="AI Account Manager - Detects at-risk customers and takes action",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - allows frontend (port 5173) to call backend (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# Health check endpoint - useful for testing if server is running
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "retention-os"}


# Import and include routes
try:
    from routes import router
except ImportError:
    from backend.routes import router

app.include_router(router)
