"""Shared raster utilities used by all domain pipelines.

Design decisions:
- Nodata, non-finite values are represented as NaN in float64 working arrays.
- Secondary rasters are resampled onto the grid of a designated reference raster
  (never the other way round), and every alignment is reported back to the caller
  so it can be recorded in provenance.
- Areas are computed from the raster geotransform: exact planar pixel areas for
  projected CRSs, and per-row spherical areas for geographic (lat/lon) CRSs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
import rasterio
from affine import Affine
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.features import sieve as _rio_sieve
from rasterio.transform import rowcol, xy
from rasterio.warp import reproject, transform as warp_transform
from PIL import Image

EARTH_RADIUS_M = 6_371_008.8  # IUGG mean Earth radius


class RasterInputError(ValueError):
    """Raised for input problems that the user can fix (bad file, CRS, nodata, etc.)."""


@dataclass
class RasterData:
    array: np.ndarray  # float64, NaN where invalid
    transform: Affine
    crs: Optional[CRS]
    width: int
    height: int
    source_nodata: Optional[float] = None
    notes: list[str] = field(default_factory=list)

    @property
    def valid(self) -> np.ndarray:
        return np.isfinite(self.array)

    def same_grid(self, other: "RasterData") -> bool:
        return (
            self.width == other.width
            and self.height == other.height
            and self.crs == other.crs
            and self.transform.almost_equals(other.transform, precision=1e-9)
        )


def read_band(path: Path, max_pixels: int, band: int = 1) -> RasterData:
    """Read a single raster band as float64 with nodata converted to NaN."""
    try:
        with rasterio.open(path) as src:
            if src.width * src.height > max_pixels:
                raise RasterInputError(
                    f"Raster {path.name} has {src.width}x{src.height} pixels, exceeding the "
                    f"configured limit of {max_pixels}. Subset the area of interest first."
                )
            if src.crs is None:
                raise RasterInputError(f"Raster {path.name} has no coordinate reference system.")
            if src.transform.is_identity:
                raise RasterInputError(f"Raster {path.name} has no georeferencing (identity transform).")
            if band > src.count:
                raise RasterInputError(f"Raster {path.name} has no band {band}.")
            arr = src.read(band, masked=True).astype("float64")
            data = np.ma.filled(arr, np.nan)
            data[~np.isfinite(data)] = np.nan
            return RasterData(
                array=data,
                transform=src.transform,
                crs=src.crs,
                width=src.width,
                height=src.height,
                source_nodata=src.nodata,
            )
    except rasterio.errors.RasterioIOError as exc:
        raise RasterInputError(f"Could not open {path.name} as a raster: {exc}") from exc


def align_to(reference: RasterData, src: RasterData, resampling: Resampling) -> tuple[RasterData, bool]:
    """Resample `src` onto the grid of `reference`. Returns (aligned, was_resampled)."""
    if reference.same_grid(src):
        return src, False
    dst = np.full((reference.height, reference.width), np.nan, dtype="float64")
    reproject(
        source=src.array,
        destination=dst,
        src_transform=src.transform,
        src_crs=src.crs,
        src_nodata=np.nan,
        dst_transform=reference.transform,
        dst_crs=reference.crs,
        dst_nodata=np.nan,
        resampling=resampling,
    )
    if not np.isfinite(dst).any():
        raise RasterInputError("Rasters do not overlap after alignment to the reference grid.")
    aligned = RasterData(dst, reference.transform, reference.crs, reference.width, reference.height,
                         notes=[f"resampled to reference grid ({resampling.name})"])
    return aligned, True


def to_power(arr: np.ndarray, scale: str) -> np.ndarray:
    """Convert backscatter to linear power. Non-positive linear values are invalid."""
    out = arr.astype("float64", copy=True)
    if scale == "power":
        out[out <= 0] = np.nan
    elif scale == "amplitude":
        out[out <= 0] = np.nan
        out = out ** 2
    elif scale == "db":
        out = np.power(10.0, out / 10.0)
    else:
        raise RasterInputError(f"Unsupported backscatter value scale '{scale}'. Use power, amplitude, or db.")
    return out


def power_to_db(power: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        out = 10.0 * np.log10(power)
    out[~np.isfinite(out)] = np.nan
    return out


def box_mean(arr: np.ndarray, size: int) -> np.ndarray:
    """NaN-aware moving-window mean (boxcar) using integral images."""
    if size < 3 or size % 2 == 0:
        raise RasterInputError("Filter window must be an odd integer >= 3.")
    valid = np.isfinite(arr)
    vals = np.where(valid, arr, 0.0)
    pad = size // 2

    def _window_sum(a: np.ndarray) -> np.ndarray:
        p = np.pad(a, pad, mode="constant")
        c = np.cumsum(np.cumsum(p, axis=0), axis=1)
        c = np.pad(c, ((1, 0), (1, 0)), mode="constant")
        return c[size:, size:] - c[:-size, size:] - c[size:, :-size] + c[:-size, :-size]

    s = _window_sum(vals)
    n = _window_sum(valid.astype("float64"))
    with np.errstate(divide="ignore", invalid="ignore"):
        out = s / n
    out[~valid] = np.nan  # do not fill nodata pixels
    return out


def otsu_threshold(values: np.ndarray, bins: int = 256) -> tuple[float, float]:
    """Otsu's threshold on finite values. Returns (threshold, fraction_below)."""
    v = values[np.isfinite(values)]
    if v.size < 100:
        raise RasterInputError("Too few valid pixels to estimate a histogram threshold.")
    lo, hi = np.percentile(v, [0.5, 99.5])
    if not hi > lo:
        raise RasterInputError("Raster values are constant; a histogram threshold cannot be estimated.")
    hist, edges = np.histogram(np.clip(v, lo, hi), bins=bins, range=(lo, hi))
    centers = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(hist).astype("float64")
    w1 = w0[-1] - w0
    m = np.cumsum(hist * centers)
    with np.errstate(divide="ignore", invalid="ignore"):
        mu0 = m / w0
        mu1 = (m[-1] - m) / w1
        between = w0 * w1 * (mu0 - mu1) ** 2
    between[~np.isfinite(between)] = -1
    idx = int(np.argmax(between))
    thr = float(edges[idx + 1])
    return thr, float((v < thr).mean())


def _linear_unit_factor(crs: CRS) -> float:
    try:
        factor = crs.linear_units_factor[1]
    except Exception as exc:  # pragma: no cover - depends on CRS definition
        raise RasterInputError(f"Cannot determine linear units of CRS {crs}.") from exc
    return float(factor)


def pixel_area_m2(transform: Affine, crs: CRS, height: int) -> np.ndarray:
    """Pixel areas in m², shape (height, 1) so it broadcasts across columns."""
    if transform.b != 0 or transform.d != 0:
        raise RasterInputError("Rotated/sheared geotransforms are not supported for area calculation.")
    if crs.is_geographic:
        dlon = math.radians(abs(transform.a))
        rows = np.arange(height + 1)
        lat_edges = np.radians(transform.f + transform.e * rows)
        lat_edges = np.clip(lat_edges, -math.pi / 2, math.pi / 2)
        areas = EARTH_RADIUS_M ** 2 * dlon * np.abs(np.sin(lat_edges[:-1]) - np.sin(lat_edges[1:]))
        return areas.reshape(-1, 1)
    f = _linear_unit_factor(crs)
    area = abs(transform.a * transform.e) * f * f
    return np.full((height, 1), area)


def pixel_size_m(transform: Affine, crs: CRS, height: int) -> tuple[np.ndarray, float]:
    """Approximate pixel spacing in metres: (dx per row, dy)."""
    if crs.is_geographic:
        lat = np.radians(transform.f + transform.e * (np.arange(height) + 0.5))
        dx = np.radians(abs(transform.a)) * EARTH_RADIUS_M * np.cos(lat)
        dy = math.radians(abs(transform.e)) * EARTH_RADIUS_M
        return dx, dy
    f = _linear_unit_factor(crs)
    return np.full(height, abs(transform.a) * f), abs(transform.e) * f


def mask_area_m2(mask: np.ndarray, areas: np.ndarray) -> float:
    return float((mask * areas).sum())


def remove_small_clusters(mask: np.ndarray, min_pixels: int) -> np.ndarray:
    """Remove 8-connected clusters smaller than `min_pixels` (does not fill holes)."""
    if min_pixels <= 1 or not mask.any():
        return mask
    sieved = _rio_sieve(mask.astype("uint8"), size=min_pixels, connectivity=8)
    return mask & (sieved == 1)


def slope_degrees(dem: RasterData) -> np.ndarray:
    dx, dy = pixel_size_m(dem.transform, dem.crs, dem.height)
    gy = np.gradient(dem.array, axis=0) / dy
    gx = np.gradient(dem.array, axis=1) / dx.reshape(-1, 1)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def write_geotiff(path: Path, array: np.ndarray, ref: RasterData, dtype: str, nodata) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = array.astype(dtype)
    with rasterio.open(
        path, "w", driver="GTiff", height=ref.height, width=ref.width, count=1, dtype=dtype,
        crs=ref.crs, transform=ref.transform, nodata=nodata, compress="deflate",
    ) as dst:
        dst.write(out, 1)


# --------------------------------------------------------------------------- previews
_MAX_PREVIEW_DIM = 2048


def _preview_stride(height: int, width: int) -> int:
    return max(1, math.ceil(max(height, width) / _MAX_PREVIEW_DIM))


def common_stretch(*arrays: np.ndarray, pct=(2, 98)) -> tuple[float, float]:
    vals = np.concatenate([a[np.isfinite(a)].ravel() for a in arrays])
    if vals.size == 0:
        raise RasterInputError("No valid pixels available for display.")
    lo, hi = np.percentile(vals, pct)
    if hi <= lo:
        hi = lo + 1.0
    return float(lo), float(hi)


def write_grayscale_png(path: Path, arr: np.ndarray, vmin: float, vmax: float) -> None:
    s = _preview_stride(*arr.shape)
    a = arr[::s, ::s]
    norm = np.clip((a - vmin) / (vmax - vmin), 0, 1)
    gray = np.nan_to_num(norm * 255).astype("uint8")
    alpha = np.where(np.isfinite(a), 255, 0).astype("uint8")
    rgba = np.dstack([gray, gray, gray, alpha])
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(path)


def write_class_png(path: Path, classes: np.ndarray, palette: dict[int, tuple[int, int, int, int]]) -> None:
    s = _preview_stride(*classes.shape)
    c = classes[::s, ::s]
    rgba = np.zeros(c.shape + (4,), dtype="uint8")
    for value, color in palette.items():
        rgba[c == value] = color
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(path)


def _ramp(stops: list[tuple[float, tuple[int, int, int]]], t: np.ndarray) -> np.ndarray:
    xs = np.array([p for p, _ in stops])
    out = np.zeros(t.shape + (3,), dtype="float64")
    for ch in range(3):
        out[..., ch] = np.interp(t, xs, np.array([c[ch] for _, c in stops]))
    return out


DIVERGING = [(0.0, (178, 24, 43)), (0.5, (247, 247, 247)), (1.0, (33, 102, 172))]  # red-white-blue
SEQUENTIAL = [(0.0, (13, 8, 135)), (0.5, (204, 71, 120)), (1.0, (240, 249, 33))]  # plasma-like


def write_ramp_png(path: Path, arr: np.ndarray, vmin: float, vmax: float, stops) -> None:
    s = _preview_stride(*arr.shape)
    a = arr[::s, ::s]
    t = np.clip((a - vmin) / (vmax - vmin), 0, 1)
    rgb = _ramp(stops, np.nan_to_num(t))
    alpha = np.where(np.isfinite(a), 255, 0)
    rgba = np.dstack([rgb, alpha]).astype("uint8")
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(path)


# --------------------------------------------------------------------------- coordinates
def lonlat_to_pixel(ref: RasterData, lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = warp_transform(CRS.from_epsg(4326), ref.crs, list(lon), list(lat))
    rows, cols = rowcol(ref.transform, xs, ys)
    return np.asarray(rows, dtype=int), np.asarray(cols, dtype=int)


def pixel_to_lonlat(ref: RasterData, row: int, col: int) -> tuple[float, float]:
    x, y = xy(ref.transform, row, col)
    lon, lat = warp_transform(ref.crs, CRS.from_epsg(4326), [x], [y])
    return float(lon[0]), float(lat[0])


def bounds_lonlat(ref: RasterData) -> list[float]:
    from rasterio.warp import transform_bounds
    t = ref.transform
    left, top = t.c, t.f
    right = t.c + t.a * ref.width + t.b * ref.height
    bottom = t.f + t.d * ref.width + t.e * ref.height
    return list(transform_bounds(ref.crs, CRS.from_epsg(4326), min(left, right), min(top, bottom),
                                 max(left, right), max(top, bottom)))


def fmt(value: float, digits: int = 3) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}"


def build_inspector_grid(
    ref: RasterData,
    arrays: dict[str, np.ndarray],
    grid_size: int = 24,
) -> dict[str, Any]:
    """Build a lightweight downsampled spatial grid (grid_size x grid_size) for interactive pixel inspection."""
    h, w = ref.height, ref.width
    rows = np.linspace(0, max(h - 1, 0), min(grid_size, h), dtype=int)
    cols = np.linspace(0, max(w - 1, 0), min(grid_size, w), dtype=int)
    r_idx, c_idx = np.meshgrid(rows, cols, indexing="ij")
    sampled: dict[str, list[list[Optional[float]]]] = {}
    for key, arr in arrays.items():
        sub = arr[r_idx, c_idx]
        sampled[key] = [
            [round(float(val), 2) if np.isfinite(val) else None for val in row]
            for row in sub
        ]
    try:
        b_wgs84 = [round(x, 6) for x in bounds_lonlat(ref)]
    except Exception:
        b_wgs84 = None
    return {
        "grid_rows": len(rows),
        "grid_cols": len(cols),
        "raster_width": w,
        "raster_height": h,
        "crs": str(ref.crs),
        "bounds_wgs84": b_wgs84,
        "layers": sampled,
    }
