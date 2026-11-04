from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["Health"])
def health_check():
    """Service health probe endpoint."""
    return {"status": "healthy", "service": "Dancing with the SARs Backend", "version": "1.0.0"}
