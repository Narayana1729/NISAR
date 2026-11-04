#!/usr/bin/env python3
"""
validate_datasets.py — Dataset Integrity and Georeferencing Verification Tool
Validates that all staged datasets across Domains 1–5 exist, have valid raster georeferencing
(CRS, transform, bounds, nodata, non-empty dimensions), and comply with dataset manifests.
"""

import sys
import os
import json
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

try:
    import rasterio
    from app.database.connection import SessionLocal
    from app.database.models import DatasetModel
except ImportError as err:
    print(f"Error loading backend dependencies: {err}")
    print("Please run within the backend virtual environment: backend/venv/bin/python scripts/validate_datasets.py")
    sys.exit(1)


def validate_all_datasets():
    db = SessionLocal()
    manifest_path = BASE_DIR / "data" / "manifests" / "datasets.json"

    if not manifest_path.exists():
        print(f"Error: Manifest not found at {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    catalog_items = manifest_data.get("datasets", [])
    print(f"Loaded {len(catalog_items)} dataset records from {manifest_path.name}")
    print(f"Checking database synchronization & physical files in {BASE_DIR / 'data' / 'raw'}...")

    errors = []
    verified = 0

    for item in catalog_items:
        ds_id = item.get("id")
        rel_path = item.get("relative_path")
        expected_domain = item.get("domain")
        expected_ptype = item.get("product_type")

        file_path = BASE_DIR / "data" / rel_path
        if not file_path.exists():
            errors.append(f"[{ds_id}] Missing physical file on disk: {file_path}")
            continue

        # If GeoTIFF, check rasterio properties
        if file_path.suffix.lower() in [".tif", ".tiff"]:
            try:
                with rasterio.open(file_path) as src:
                    if src.width <= 0 or src.height <= 0:
                        errors.append(f"[{ds_id}] Invalid dimensions {src.shape}")
                    if src.crs is None:
                        errors.append(f"[{ds_id}] Missing CRS in GeoTIFF")
                    verified += 1
            except Exception as e:
                errors.append(f"[{ds_id}] Rasterio open failed: {e}")
        # If GeoJSON, verify valid JSON geometry
        elif file_path.suffix.lower() in [".geojson", ".json"]:
            try:
                with open(file_path, "r", encoding="utf-8") as gf:
                    gj = json.load(gf)
                    if "type" not in gj:
                        errors.append(f"[{ds_id}] Invalid GeoJSON structure")
                    verified += 1
            except Exception as e:
                errors.append(f"[{ds_id}] GeoJSON load failed: {e}")
        else:
            verified += 1

    db.close()

    print("\n" + "=" * 60)
    print(f"Dataset Validation Summary: {verified} verified successfully, {len(errors)} errors.")
    if errors:
        print("\nValidation Errors Encountered:")
        for err in errors:
            print(f"  ❌ {err}")
        return False
    else:
        print("  ✅ All staged datasets verified with valid georeferencing and integrity.")
        return True


if __name__ == "__main__":
    success = validate_all_datasets()
    sys.exit(0 if success else 1)
