import json
import uuid
from pathlib import Path
from typing import Any, Optional

import rasterio
from rasterio.crs import CRS
from rasterio.warp import transform_bounds
from sqlalchemy.orm import Session

from app.config import settings, VALID_DOMAINS
from app.database.models import DatasetModel
from app.schemas.dataset import DatasetBase, DatasetCreate

RASTER_PRODUCTS = {
    "sar_backscatter",
    "reference_water",
    "reference_flood",
    "reference_disturbance",
    "reference_velocity",
    "reference_displacement",
    "dem",
    "forest_mask",
    "ice_velocity",
    "insar_displacement",
    "insar_coherence",
}
VECTOR_PRODUCTS = {"fire_detections", "exposure_assets"}
REFERENCE_PRODUCTS = {
    "reference_water",
    "reference_flood",
    "reference_disturbance",
    "reference_velocity",
    "reference_displacement",
    "fire_detections",
    "exposure_assets",
}


class DatasetValidationError(ValueError):
    pass


def _extract_geojson_coords(geom: dict[str, Any]) -> list[tuple[float, float]]:
    """Recursively extract (lon, lat) coordinate pairs from any GeoJSON geometry."""
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if not coords:
        return []
    if gtype == "Point":
        return [(float(coords[0]), float(coords[1]))]
    if gtype in ("MultiPoint", "LineString"):
        return [(float(c[0]), float(c[1])) for c in coords if len(c) >= 2]
    if gtype in ("MultiLineString", "Polygon"):
        out = []
        for ring in coords:
            out.extend((float(c[0]), float(c[1])) for c in ring if len(c) >= 2)
        return out
    if gtype == "MultiPolygon":
        out = []
        for poly in coords:
            for ring in poly:
                out.extend((float(c[0]), float(c[1])) for c in ring if len(c) >= 2)
        return out
    return []


def compute_wgs84_bbox(crs_str: Optional[str], bbox: Optional[list[float]]) -> Optional[list[float]]:
    """Transform a dataset's native [min_x, min_y, max_x, max_y] bbox into EPSG:4326 [min_lon, min_lat, max_lon, max_lat]."""
    if not bbox or len(bbox) != 4 or not crs_str:
        return None
    try:
        src_crs = CRS.from_user_input(crs_str)
        if src_crs.to_epsg() == 4326:
            return [round(float(x), 6) for x in bbox]
        wgs = transform_bounds(src_crs, CRS.from_epsg(4326), *bbox, densify_pts=21)
        return [round(float(x), 6) for x in wgs]
    except Exception:
        return None


def inspect_file(path: Path, product_type: str) -> dict[str, Any]:
    """Extract geospatial metadata and check that the file suits the declared product type."""
    suffix = path.suffix.lower()
    if product_type in RASTER_PRODUCTS:
        if suffix not in (".tif", ".tiff"):
            raise DatasetValidationError(f"Product type '{product_type}' must be a GeoTIFF (.tif/.tiff).")
        try:
            with rasterio.open(path) as src:
                if src.crs is None:
                    raise DatasetValidationError("GeoTIFF has no coordinate reference system.")
                if src.transform.is_identity:
                    raise DatasetValidationError("GeoTIFF has no georeferencing.")
                b = src.bounds
                return {
                    "format": "GeoTIFF",
                    "crs": src.crs.to_string(),
                    "bbox": [float(b.left), float(b.bottom), float(b.right), float(b.top)],
                    "width": src.width,
                    "height": src.height,
                    "nodata": None if src.nodata is None else float(src.nodata),
                }
        except rasterio.errors.RasterioIOError as exc:
            raise DatasetValidationError(f"File is not a readable GeoTIFF: {exc}") from exc
    if product_type in VECTOR_PRODUCTS:
        if suffix not in (".geojson", ".json"):
            raise DatasetValidationError(f"Product type '{product_type}' must be GeoJSON.")
        try:
            gj = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise DatasetValidationError(f"File is not valid JSON: {exc}") from exc
        if gj.get("type") != "FeatureCollection" or not isinstance(gj.get("features"), list):
            raise DatasetValidationError("GeoJSON must be a FeatureCollection.")
        features = [f for f in gj["features"] if f.get("geometry")]
        if not features:
            raise DatasetValidationError("GeoJSON contains no valid geometry features.")
        if product_type == "fire_detections":
            points = [f for f in features if (f.get("geometry") or {}).get("type") == "Point"]
            if not points:
                raise DatasetValidationError("GeoJSON contains no Point features.")
        all_pts: list[tuple[float, float]] = []
        for f in features:
            all_pts.extend(_extract_geojson_coords(f["geometry"]))
        if not all_pts:
            raise DatasetValidationError("GeoJSON features contain no coordinates.")
        lons = [p[0] for p in all_pts]
        lats = [p[1] for p in all_pts]
        return {
            "format": "GeoJSON",
            "crs": "EPSG:4326",
            "bbox": [min(lons), min(lats), max(lons), max(lats)],
            "width": len(features),
            "height": None,
            "nodata": None,
        }
    raise DatasetValidationError(f"Unsupported product type '{product_type}'.")


def _to_response_dict(ds: DatasetModel, db: Optional[Session] = None) -> dict[str, Any]:
    data = {c.name: getattr(ds, c.name) for c in ds.__table__.columns}
    if isinstance(data.get("bbox"), str):
        try:
            data["bbox"] = json.loads(data["bbox"])
        except Exception:
            data["bbox"] = None

    root = Path(settings.DATA_ROOT_DIR).resolve()
    file_path = (root / (data.get("relative_path") or "")).resolve()
    file_exists = file_path.is_file() and str(file_path).startswith(str(root))

    # Backfill spatial metadata if missing on disk-backed fixture rows
    if file_exists and (data.get("bbox") is None or data.get("crs") is None):
        try:
            info = inspect_file(file_path, data.get("product_type", "sar_backscatter"))
            data["bbox"] = info["bbox"]
            data["crs"] = info["crs"]
            data["width"] = info["width"]
            data["height"] = info["height"]
            data["nodata"] = info["nodata"]
            data["file_size_bytes"] = file_path.stat().st_size
            if db is not None:
                ds.bbox = json.dumps(info["bbox"])
                ds.crs = info["crs"]
                ds.width = info["width"]
                ds.height = info["height"]
                ds.nodata = info["nodata"]
                ds.file_size_bytes = data["file_size_bytes"]
                db.commit()
        except Exception:
            pass

    data["bbox_wgs84"] = compute_wgs84_bbox(data.get("crs"), data.get("bbox"))
    data["file_available"] = file_exists
    data["processing_readiness"] = (
        "ready" if (file_exists and data.get("crs") and data.get("bbox")) else ("missing_file" if not file_exists else "incomplete_metadata")
    )
    data["is_reference_data"] = data.get("product_type") in REFERENCE_PRODUCTS
    src_str = (data.get("source") or "").upper()
    if data.get("is_synthetic"):
        data["license"] = "Synthetic Test Fixture"
    elif "JAXA" in src_str or "ALOS" in src_str:
        data["license"] = "JAXA ALOS-2 PALSAR-2 Open Data Policy"
    elif "NASA" in src_str or "ITS_LIVE" in src_str or "MODIS" in src_str:
        data["license"] = "NASA EOSDIS / MEaSUREs Public Domain"
    elif "LICSAR" in src_str or "COMET" in src_str:
        data["license"] = "COMET-LiCSAR Open License (CC-BY 4.0) / Copernicus Sentinel-1"
    elif "JRC" in src_str:
        data["license"] = "EC Joint Research Centre (JRC) Open Data (CC-BY 4.0)"
    else:
        data["license"] = "Copernicus Open Access / Public Domain"
    return data


class DatasetService:
    """Metadata queries and registration for datasets."""

    def __init__(self, db: Session):
        self.db = db

    def list_datasets(self, domain: Optional[str] = None, product_type: Optional[str] = None) -> list[dict[str, Any]]:
        query = self.db.query(DatasetModel)
        if domain:
            query = query.filter(DatasetModel.domain == domain)
        if product_type:
            query = query.filter(DatasetModel.product_type == product_type)
        items = [_to_response_dict(d, self.db) for d in query.order_by(DatasetModel.created_at.desc()).all()]
        items.sort(
            key=lambda d: (
                1 if d.get("is_synthetic") else 0,
                d.get("acquisition_date") or "9999-99-99",
                d.get("name") or "",
            )
        )
        return items

    def get_dataset(self, dataset_id: str) -> Optional[dict[str, Any]]:
        ds = self.db.query(DatasetModel).filter(DatasetModel.id == dataset_id).first()
        return _to_response_dict(ds, self.db) if ds else None

    def create_dataset(self, data: DatasetCreate, custom_id: Optional[str] = None) -> dict[str, Any]:
        payload = data.model_dump(exclude={"license"})
        payload["bbox"] = json.dumps(payload["bbox"]) if payload.get("bbox") is not None else None
        dataset_id = custom_id or str(uuid.uuid4())
        existing = self.db.query(DatasetModel).filter(DatasetModel.id == dataset_id).first()
        if existing:
            for k, v in payload.items():
                setattr(existing, k, v)
            self.db.commit()
            self.db.refresh(existing)
            return _to_response_dict(existing, self.db)
        dataset = DatasetModel(id=dataset_id, **payload)
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        return _to_response_dict(dataset, self.db)

    def register_existing(self, meta: DatasetBase, relative_path: str, custom_id: Optional[str] = None) -> dict[str, Any]:
        """Register a file that already exists inside the data root."""
        validate_domain(meta.domain)
        root = Path(settings.DATA_ROOT_DIR).resolve()
        target = (root / relative_path).resolve()
        if not str(target).startswith(str(root) + "/"):
            raise DatasetValidationError("relative_path must point inside the data directory.")
        if target.parts[len(root.parts)] == "outputs":
            raise DatasetValidationError("Generated outputs cannot be registered as input datasets.")
        if not target.is_file():
            raise DatasetValidationError("No file exists at the given relative_path.")
        info = inspect_file(target, meta.product_type)
        return self.create_dataset(
            DatasetCreate(
                **meta.model_dump(),
                relative_path=target.relative_to(root).as_posix(),
                file_size_bytes=target.stat().st_size,
                **info,
            ),
            custom_id=custom_id,
        )


def validate_domain(domain: str) -> None:
    if domain not in VALID_DOMAINS:
        raise DatasetValidationError(f"Unknown domain '{domain}'. Expected one of: {', '.join(VALID_DOMAINS)}.")
