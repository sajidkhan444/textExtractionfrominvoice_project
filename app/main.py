"""Main FastAPI application entry point."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

# Create FastAPI app
app = FastAPI(
    title="Invoice Extractor API",
    description="API for extracting invoice data using EasyOCR and Qwen AI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Invoice Extractor API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "upload": "POST /api/v1/upload",
            "upload_batch": "POST /api/v1/upload/batch",
            "invoices": "GET /api/v1/invoices",
            "search": "GET /api/v1/search",
            "stats": "GET /api/v1/stats",
            "health": "GET /api/v1/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)