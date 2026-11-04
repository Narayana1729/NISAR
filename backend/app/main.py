from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api.routes import api_router
from app.database.connection import engine, Base, SessionLocal
from app.services.seed_service import ensure_platform_datasets

# Create tables in SQLite on startup if they don't exist
Base.metadata.create_all(bind=engine)

# Ensure real and georeferenced demonstration datasets are registered
try:
    _seed_db = SessionLocal()
    ensure_platform_datasets(_seed_db)
    _seed_db.close()
except Exception as _seed_exc:
    print(f"Dataset seeding notice: {_seed_exc}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API and processing pipeline orchestrator for Dancing with the SARs.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint
@app.get("/api/health", tags=["Health"])
def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "service": "Dancing with the SARs Backend",
        "version": "1.0.0"
    }

# Register all API routes under /api
app.include_router(api_router, prefix="/api")

# Serve generated output assets (PNG previews and GeoTIFFs) statically
outputs_dir = Path(settings.DATA_ROOT_DIR) / "outputs"
outputs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/api/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
