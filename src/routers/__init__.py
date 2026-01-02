"""
Routers package
Organizes API endpoints by domain
"""
from .sessions import router as sessions_router
from .images import router as images_router
from .processing import router as processing_router
from .reports import router as reports_router
from .jobs import router as jobs_router

__all__ = [
    "sessions_router",
    "images_router", 
    "processing_router",
    "reports_router",
    "jobs_router"
]
