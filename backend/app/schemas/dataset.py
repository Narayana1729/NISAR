from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Product types the processing pipelines understand. Each domain declares which it accepts.
ProductType = Literal[
    "sar_backscatter",         # Calibrated (e.g. RTC) SAR backscatter raster
    "reference_water",         # Binary permanent/reference water mask (1 = water)
    "reference_flood",         # Independent flood reference map used ONLY for validation
    "reference_disturbance",   # Independent forest or wildfire disturbance reference mask (1 = disturbed)
    "reference_velocity",      # Independent glacier velocity reference raster (m/yr)
    "reference_displacement",  # Independent ground displacement reference raster (mm/yr or mm)
    "dem",                     # Digital elevation model (metres)
    "forest_mask",             # Binary forest/vegetation mask (1 = forest)
    "ice_velocity",            # Precomputed ice-velocity magnitude raster
    "insar_displacement",      # Precomputed unwrapped LOS displacement or velocity raster
    "insar_coherence",         # Interferometric coherence (0..1)
    "fire_detections",         # Active-fire points (GeoJSON), e.g. NASA FIRMS export
    "exposure_assets",         # Georeferenced assets GeoJSON (roads, settlements, agriculture, protected areas)
]

ValueScale = Literal["power", "amplitude", "db", "other"]


class DatasetBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    domain: str
    description: Optional[str] = None
    product_type: ProductType = "sar_backscatter"
    sensor: Optional[str] = None
    polarization: Optional[str] = None
    acquisition_date: Optional[str] = None
    value_scale: Optional[ValueScale] = None
    units: Optional[str] = None
    source: Optional[str] = None
    license: Optional[str] = None
    is_synthetic: bool = False

    @field_validator("acquisition_date")
    @classmethod
    def _validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, ""):
            return None
        try:
            datetime.strptime(v[:10], "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("acquisition_date must be formatted YYYY-MM-DD") from exc
        return v[:10]


class DatasetRegister(DatasetBase):
    """Register a file that already exists under the data root (e.g. placed in data/raw/)."""
    relative_path: str


class DatasetCreate(DatasetBase):
    relative_path: str
    format: str
    file_size_bytes: Optional[int] = None
    crs: Optional[str] = None
    bbox: Optional[list[float]] = None
    width: Optional[int] = None
    height: Optional[int] = None
    nodata: Optional[float] = None


class DatasetResponse(DatasetBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    relative_path: str
    format: str
    file_size_bytes: Optional[int] = None
    crs: Optional[str] = None
    bbox: Optional[list[float]] = None
    bbox_wgs84: Optional[list[float]] = None
    width: Optional[int] = None
    height: Optional[int] = None
    nodata: Optional[float] = None
    file_available: bool = True
    processing_readiness: str = "ready"
    is_reference_data: bool = False
    created_at: datetime


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    asset_type: str
    relative_path: str
    created_at: datetime
