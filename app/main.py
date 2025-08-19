import logging
from fastapi import FastAPI
from app.routes.index import routers
from app.middleware.logging_middleware import LoggingMiddleware
from app.config.settings import settings

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A FastAPI application demonstrating CQRS pattern with task management",
    version=settings.VERSION
)

# Add middleware
app.add_middleware(LoggingMiddleware)

# Include all routers
for router in routers:
    app.include_router(router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to CQRS Task Management API"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
