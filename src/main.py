"""
FastAPI Web Application for Leitor de Simulados
Main application entry point - assembles routers and middleware
"""
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# Add the project root to the path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from dependencies import get_processing_service, get_session_manager
from routers import (
    sessions_router,
    images_router,
    processing_router,
    reports_router
)


# Configure logging
settings = get_settings()
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# Application Lifecycle
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events"""
    # Startup
    logger.info("🚀 Leitor de Simulados API Starting...")
    
    # Initialize services
    processing_service = get_processing_service()
    logger.info(f"✅ Loaded {len(processing_service.get_available_models())} models")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    session_manager = get_session_manager()
    session_manager.cleanup_all()
    logger.info("✅ Cleanup complete")


# =============================================================================
# Application Factory
# =============================================================================

def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    
    # Include routers
    app.include_router(sessions_router)
    app.include_router(images_router)
    app.include_router(processing_router)
    app.include_router(reports_router)
    
    # Root endpoints
    @app.get("/", tags=["root"])
    async def root():
        """API root - shows basic info"""
        return {
            "message": settings.api_title,
            "version": settings.api_version,
            "docs": "/docs",
            "redoc": "/redoc"
        }
    
    @app.get("/api/health", tags=["health"])
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy"}
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers
    )
