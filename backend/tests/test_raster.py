import pytest
import numpy as np
from pathlib import Path
from affine import Affine
from rasterio.crs import CRS

from app.utils.raster import (
    RasterData,
    otsu_threshold,
    pixel_area_m2,
    mask_area_m2,
    box_mean,
    remove_small_clusters,
    to_power,
    power_to_db,
    write_geotiff,
    read_band,
    align_to,
    RasterInputError
)
from rasterio.enums import Resampling

def test_otsu_bimodal_separation():
    # Construct a bimodal distribution: mode 1 around -20 dB (water), mode 2 around -10 dB (land)
    np.random.seed(42)
    water = np.random.normal(-20.0, 1.0, 500)
    land = np.random.normal(-10.0, 1.5, 500)
    data = np.concatenate([water, land])
    thr, frac = otsu_threshold(data)
    # Threshold should separate the two peaks roughly around -15 dB
    assert -18.0 <= thr <= -13.0
    assert 0.4 <= frac <= 0.6

def test_pixel_area_calculation_projected():
    # 10m x 10m pixels in UTM CRS (linear units = metres)
    transform = Affine(10.0, 0.0, 500000.0, 0.0, -10.0, 4000000.0)
    crs = CRS.from_epsg(32632) # WGS 84 / UTM zone 32N
    height = 5
    areas = pixel_area_m2(transform, crs, height)
    assert areas.shape == (5, 1)
    assert np.allclose(areas, 100.0) # 10m * 10m = 100 m²

    mask = np.ones((5, 5), dtype=bool)
    total_area = mask_area_m2(mask, areas)
    assert np.isclose(total_area, 25 * 100.0)

def test_box_mean_with_nans():
    arr = np.array([
        [1.0, 2.0, np.nan],
        [4.0, 5.0, 6.0],
        [7.0, 8.0, 9.0]
    ], dtype="float64")
    filtered = box_mean(arr, size=3)
    # Center pixel (row 1, col 1): should average finite neighbors (1+2+4+5+6+7+8+9)/8 = 42/8 = 5.25
    assert np.isclose(filtered[1, 1], 5.25)
    # The NaN pixel itself should remain NaN (do not fill nodata)
    assert np.isnan(filtered[0, 2])

def test_remove_small_clusters_sieve():
    mask = np.zeros((10, 10), dtype=bool)
    # Single isolated pixel
    mask[2, 2] = True
    # Cluster of 5 pixels
    mask[5:7, 5:7] = True # 4 pixels
    mask[7, 5] = True     # 5th pixel

    cleaned = remove_small_clusters(mask, min_pixels=4)
    assert not cleaned[2, 2]  # isolated pixel filtered
    assert np.sum(cleaned) == 5

def test_to_power_and_power_to_db():
    db_vals = np.array([-20.0, -10.0, 0.0])
    power = to_power(db_vals, scale="db")
    assert np.allclose(power, [0.01, 0.1, 1.0])

    re_db = power_to_db(power)
    assert np.allclose(re_db, db_vals)

def test_raster_io_and_alignment(tmp_path):
    # Create reference raster 4x4
    ref_file = tmp_path / "ref.tif"
    arr = np.ones((4, 4), dtype="float32") * 10.0
    arr[0, 0] = -9999.0 # nodata
    transform = Affine(10.0, 0.0, 0.0, 0.0, -10.0, 0.0)
    crs = CRS.from_epsg(32632)
    ref_data = RasterData(array=arr, transform=transform, crs=crs, width=4, height=4)
    write_geotiff(ref_file, arr, ref_data, dtype="float32", nodata=-9999.0)

    # Read back
    read_data = read_band(ref_file, max_pixels=100)
    assert read_data.width == 4
    assert read_data.height == 4
    assert np.isnan(read_data.array[0, 0]) # nodata converted to NaN
    assert read_data.array[1, 1] == 10.0

    # Alignment with identical grid
    aligned, was_resampled = align_to(read_data, read_data, Resampling.bilinear)
    assert not was_resampled
