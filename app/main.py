# app/main.py (Updated with startup event)

import sys
import os
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import routers from both modules
from app.api.routes import router as invoice_router
from app.api.document_routes import router as document_router

# Import document processor for startup initialization
from app.services.document_processor import DocumentProcessor

# Serve local data directory for direct file access
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
os.makedirs(DATA_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    print("\n" + "="*70)
    print("🚀 STARTING DOCUMENT PROCESSING SYSTEM")
    print("="*70)
    
    # Initialize Document Processor at startup
    print("\n📌 Initializing Document Processing Module...")
    try:
        processor = DocumentProcessor()
        # Store in app state for later use if needed
        app.state.document_processor = processor
        print("✅ Document Processing Module initialized successfully")
    except Exception as e:
        print(f"❌ Document Processing Module initialization failed: {e}")
    
    print("\n" + "="*70)
    print("✅ SYSTEM READY")
    print("="*70)
    
    yield
    
    # Shutdown cleanup
    print("\n🛑 Shutting down...")
    from app.core.documents_model_loader import DocumentModelLoader
    DocumentModelLoader.unload_models()


# Create FastAPI app with lifespan
app = FastAPI(
    title="Document Processing System",
    description="Invoice Extraction + Document Processing (Cheques, Deposit Slips, Digital Receipts)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan  # Add lifespan here
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static file directory for direct access to /data/*
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

# Include routers with their prefixes
app.include_router(invoice_router, prefix="/api/v1")           # Existing invoice routes
app.include_router(document_router)                             # New document routes

@app.get("/")
async def root():
    """Root endpoint with all available endpoints."""
    return {
        "message": "Document Processing System API",
        "version": "2.0.0",
        "modules": {
            "invoice_extraction": {
                "status": "active",
                "endpoints": {
                    "upload": "POST /api/v1/upload",
                    "upload_batch": "POST /api/v1/upload/batch",
                    "invoices": "GET /api/v1/invoices",
                    "search": "GET /api/v1/search",
                    "stats": "GET /api/v1/stats",
                    "health": "GET /api/v1/health"
                }
            },
            "document_processing": {
                "status": "active",
                "test_endpoints": {
                    "single": "POST /api/documents/test/process",
                    "batch": "POST /api/documents/test/process/batch",
                    "info": "GET /api/documents/test/info"
                },
                "production_endpoints": {
                    "single": "POST /api/documents/process",
                    "batch": "POST /api/documents/process/batch"
                },
                "health": "GET /api/documents/health"
            }
        }
    }

@app.get("/health")
async def health():
    """Global health check."""
    return {
        "status": "healthy", 
        "modules": ["invoice_extraction", "document_processing"],
        "document_processor_ready": hasattr(app.state, 'document_processor')
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)