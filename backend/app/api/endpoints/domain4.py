from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.processing_service import ProcessingService
from app.services.pipeline import PipelineInputError
from app.domains.domain4.processor import AgriculturePipeline, LandMovementPipeline
from app.schemas.results import ProcessingRequest, StandardDomainResponse, ProcessingRunResponse

router = APIRouter()
pipeline = AgriculturePipeline()
land_pipeline = LandMovementPipeline()

@router.get("/info")
def get_info():
    """Metadata and parameter specs for Domain 4: Agriculture & Soil Conditions."""
    return pipeline.describe()

@router.post("/process", response_model=StandardDomainResponse)
def run_process(payload: ProcessingRequest, db: Session = Depends(get_db)):
    """Execute domain4 processing pipeline."""
    service = ProcessingService(db)
    target_pipeline = land_pipeline if ("displacement" in payload.inputs or "coherence" in payload.inputs) else pipeline
    try:
        return service.execute(target_pipeline, payload)
    except PipelineInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/runs", response_model=list[ProcessingRunResponse])
def get_runs(db: Session = Depends(get_db)):
    """List past processing runs for domain4."""
    service = ProcessingService(db)
    return service.list_runs(domain="domain4")
