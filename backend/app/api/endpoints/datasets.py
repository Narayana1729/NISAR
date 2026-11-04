from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path

from app.database.connection import get_db
from app.services.dataset_service import DatasetService, DatasetValidationError
from app.services.storage_service import storage_service
from app.utils.file_handler import FileHandler
from app.schemas.dataset import DatasetResponse, DatasetCreate, DatasetBase, DatasetRegister

router = APIRouter()

@router.get("", response_model=list[DatasetResponse])
def get_datasets(
    domain: Optional[str] = Query(None),
    product_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Retrieve metadata for datasets, optionally filtered by domain and product_type."""
    service = DatasetService(db)
    return service.list_datasets(domain=domain, product_type=product_type)

@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset_by_id(dataset_id: str, db: Session = Depends(get_db)):
    """Retrieve details of a specific dataset by ID."""
    service = DatasetService(db)
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset

@router.post("/register", response_model=DatasetResponse)
def register_dataset_file(payload: DatasetRegister, db: Session = Depends(get_db)):
    """Register an existing file on the filesystem under the data/ directory."""
    service = DatasetService(db)
    try:
        base_meta = DatasetBase(**payload.model_dump(exclude={"relative_path"}))
        return service.register_existing(base_meta, payload.relative_path)
    except DatasetValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset_file(
    name: str = Form(...),
    domain: str = Form(...),
    product_type: str = Form("sar_backscatter"),
    sensor: Optional[str] = Form(None),
    polarization: Optional[str] = Form(None),
    acquisition_date: Optional[str] = Form(None),
    value_scale: Optional[str] = Form(None),
    units: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    is_synthetic: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Safely upload and register a new dataset artifact."""
    handler = FileHandler(storage_service.local_adapter)
    try:
        content = await file.read()
        file.file.seek(0)
        stored_path = handler.save_upload(
            file_obj=file.file,
            original_filename=file.filename,
            file_size=len(content),
            subfolder=f"raw/{domain}"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    service = DatasetService(db)
    try:
        base_meta = DatasetBase(
            name=name,
            domain=domain,
            product_type=product_type,
            sensor=sensor,
            polarization=polarization,
            acquisition_date=acquisition_date,
            value_scale=value_scale,
            units=units,
            source=source,
            is_synthetic=is_synthetic
        )
        return service.register_existing(base_meta, stored_path)
    except DatasetValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
