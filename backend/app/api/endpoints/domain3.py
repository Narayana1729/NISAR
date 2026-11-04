from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.processing_service import ProcessingService
from app.services.pipeline import PipelineInputError
from app.domains.domain3.processor import EarthquakesPipeline, CryospherePipeline
from app.schemas.results import ProcessingRequest, StandardDomainResponse, ProcessingRunResponse

router = APIRouter()
pipeline = EarthquakesPipeline()
cryo_pipeline = CryospherePipeline()

@router.get("/info")
def get_info():
    """Metadata and parameter specs for Domain 3: Earthquakes & Ground Deformation."""
    return pipeline.describe()

@router.post("/process", response_model=StandardDomainResponse)
def run_process(payload: ProcessingRequest, db: Session = Depends(get_db)):
    """Execute domain3 processing pipeline."""
    service = ProcessingService(db)
    target_pipeline = cryo_pipeline if "velocity" in payload.inputs else pipeline
    try:
        return service.execute(target_pipeline, payload)
    except PipelineInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/runs", response_model=list[ProcessingRunResponse])
def get_runs(db: Session = Depends(get_db)):
    """List past processing runs for domain3."""
    service = ProcessingService(db)
    return service.list_runs(domain="domain3")
