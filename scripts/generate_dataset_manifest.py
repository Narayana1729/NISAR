#!/usr/bin/env python3
"""
generate_dataset_manifest.py — Generate comprehensive dataset manifest
Scans the database and staged files across all domains, extracting spatial bounds,
resolution, CRS, product type, polarization, and provenance into data/manifests/datasets.json.
"""

import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

try:
    from app.database.connection import SessionLocal
    from app.database.models import DatasetModel
    import rasterio
    from rasterio.warp import transform_bounds
except ImportError as err:
    print(f"Error loading dependencies: {err}")
    sys.exit(1)


def generate_manifest():
    db = SessionLocal()
    datasets = db.query(DatasetModel).order_by(DatasetModel.domain, DatasetModel.id).all()

    manifest_entries = []
    print(f"Scanning {len(datasets)} dataset records...")

    for d in datasets:
        full_path = BASE_DIR / "data" / d.relative_path
        entry = {
            "id": d.id,
            "name": d.name,
            "domain": d.domain,
            "product_type": d.product_type,
            "relative_path": d.relative_path,
            "format": d.format,
            "sensor": d.sensor,
            "polarization": d.polarization,
            "acquisition_date": d.acquisition_date,
            "units": d.units,
            "source": d.source,
            "is_synthetic": d.is_synthetic,
            "crs": d.crs,
            "bbox_wgs84": d.bbox,
            "width": d.width,
            "height": d.height,
            "nodata": d.nodata,
            "file_size_bytes": d.file_size_bytes,
            "exists_on_disk": full_path.exists()
        }

        # If file exists on disk and is raster, extract live metadata verification
        if full_path.exists() and full_path.suffix.lower() in [".tif", ".tiff"]:
            try:
                with rasterio.open(full_path) as src:
                    entry["resolution_m"] = [round(src.res[0], 2), round(src.res[1], 2)]
                    entry["live_crs"] = src.crs.to_string() if src.crs else None
                    if src.crs:
                        b = transform_bounds(src.crs, "EPSG:4326", *src.bounds) if src.crs.to_string() != "EPSG:4326" else src.bounds
                        entry["bbox_wgs84"] = [round(x, 4) for x in b]
            except Exception as e:
                entry["read_error"] = str(e)

        manifest_entries.append(entry)

    db.close()

    out_file = BASE_DIR / "data" / "manifests" / "datasets.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"version": "1.0.0", "datasets": manifest_entries}, f, indent=2)

    print(f"Successfully generated {out_file} with {len(manifest_entries)} datasets.")
    return True


if __name__ == "__main__":
    generate_manifest()
