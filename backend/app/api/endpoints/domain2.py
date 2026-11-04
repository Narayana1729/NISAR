from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.processing_service import ProcessingService
from app.services.pipeline import PipelineInputError
from app.domains.domain2.processor import ForestsPipeline
from app.schemas.results import ProcessingRequest, StandardDomainResponse, ProcessingRunResponse

router = APIRouter()
pipeline = ForestsPipeline()

@router.get("/info")
def get_info():
    """Metadata and parameter specs for domain2."""
    return pipeline.describe()

@router.post("/process", response_model=StandardDomainResponse)
def run_process(payload: ProcessingRequest, db: Session = Depends(get_db)):
    """Execute domain2 processing pipeline."""
    service = ProcessingService(db)
    try:
        return service.execute(pipeline, payload)
    except PipelineInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/runs", response_model=list[ProcessingRunResponse])
def get_runs(db: Session = Depends(get_db)):
    """List past processing runs for domain2."""
    service = ProcessingService(db)
    return service.list_runs(domain="domain2")
