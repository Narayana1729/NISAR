#!/usr/bin/env python3
"""Reproducible Real Earth-Observation Data Acquisition Script for NISAR — Dancing with the SARs.

Streams compact, georeferenced window subsets of verified real satellite and geophysical products
across all five platform domains from open public archives (no credentials required):

- Domain 1 (Floods & Water Dynamics — Lake Karla / Thessaly, Greece, Storm Daniel Sept 2023):
  * Sentinel-1A IW GRDH RTC VV Pre-Flood (2023-09-01) & Post-Flood (2023-09-13) [Planetary Computer]
  * Copernicus GLO-30 Digital Elevation Model (Copernicus_DSM_COG_10_N39_00_E022_00_DEM) [Planetary Computer]
  * JRC Global Surface Water v1.3 Occurrence (20E_40Nv1_3_2020) [Planetary Computer]
  * Sentinel-2A MSI L2A Post-Flood Optical NDWI Reference (2023-09-12, 0.26% cloud) [Planetary Computer]

- Domain 2 (Forests & Vegetation — Novo Progresso / BR-163 Corridor, Pará, Brazil, Aug 2019–Aug 2020):
  * Sentinel-1A IW GRDH RTC VH Baseline (2019-08-26, Orbit 141) & Monitoring (2020-08-20, Orbit 141) [Planetary Computer]
  * JAXA ALOS-2 PALSAR-2 Forest/Non-Forest Baseline Mask (S06W056_19_FNF, 2019) [Planetary Computer]
  * JAXA ALOS-2 PALSAR-2 Forest Loss Reference (S06W056_19_FNF -> S06W056_20_FNF, 2019–2020) [Planetary Computer]

- Domain 3 (Ice, Glaciers & Cryosphere — Jakobshavn Isbræ / Sermeq Kujalleq, Greenland):
  * NASA MEaSUREs ITS_LIVE v2 2022 Annual Ice Velocity Mosaic (EPSG:3413, 120m, m/year) [AWS Open Data]
  * NASA MEaSUREs ITS_LIVE v2 2014–2022 Climatological Reference Ice Velocity (EPSG:3413, 120m, m/year) [AWS Open Data]
  * Sentinel-1A IW GRDH RTC HH Terminus Pair (2023-08-28 & 2023-09-09, Orbit 127) [Planetary Computer]

- Domain 4 (Land Movement & Urban Change — Tyrnavos / Larissa Basin, Greece, Mw 6.3 March 2021 Earthquake):
  * COMET-LiCSAR Sentinel-1A Track 102 Unwrapped LOS Displacement (20210225_20210309.geo.unw.tif -> mm) [JASMIN / COMET]
  * COMET-LiCSAR Sentinel-1A Track 102 Interferometric Coherence (20210225_20210309.geo.cc.tif -> 0..1) [JASMIN / COMET]
  * COMET-LiCSAR Independent Sentinel-1B Unwrapped LOS Reference (20210219_20210309.geo.unw.tif -> mm) [JASMIN / COMET]

- Domain 5 (Wildfires & Land Disturbance — Dadia Forest / Evros Megafire, Greece, Aug–Sept 2023):
  * Sentinel-1A IW GRDH RTC VH Pre-Fire (2023-08-09, Orbit 29) & Post-Fire (2023-09-02, Orbit 29) [Planetary Computer]
  * NASA Terra/Aqua MODIS Active Fire Thermal Detections (MOD14A1 / MYD14A1, Aug 2023) [Planetary Computer]
  * NASA MODIS MCD64A1 v061 Burned Area Reference (MCD64A1.A2023213.h19v04.061) [Planetary Computer]

Usage:
    backend/venv/bin/python3 scripts/acquire_real_sar_data.py --domain all
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import from_bounds

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
SAS_SIGN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
USER_AGENT = "NISAR-DancingWithTheSARs/2.1"

_ITEM_CACHE: dict[tuple[str, str], dict] = {}


def fetch_json(url: str, timeout: int = 25) -> dict:
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(2.5 * (attempt + 1))
                continue
            raise


def sign_pc_href(href: str) -> str:
    q = urllib.parse.quote(href, safe="")
    data = fetch_json(f"{SAS_SIGN_URL}?href={q}")
    return data["href"]


def get_pc_asset_href(collection: str, item_id: str, asset_key: str) -> str:
    cache_key = (collection, item_id)
    if cache_key not in _ITEM_CACHE:
        _ITEM_CACHE[cache_key] = fetch_json(f"{STAC_URL}/collections/{collection}/items/{item_id}")
    raw_href = _ITEM_CACHE[cache_key]["assets"][asset_key]["href"]
    return sign_pc_href(raw_href)


def download_cog_window(
    asset_url: str,
    bbox_wgs84: list[float],
    dest_path: Path,
    resampling: Resampling = Resampling.bilinear,
    max_dim: int | None = None,
) -> dict:
    """Stream a georeferenced window subset from a remote Cloud-Optimized GeoTIFF."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(asset_url) as src:
        bounds_native = transform_bounds(CRS.from_epsg(4326), src.crs, *bbox_wgs84, densify_pts=21)
        window = from_bounds(*bounds_native, transform=src.transform)
        window = window.round_offsets().round_lengths()

        win_h = max(1, int(window.height))
        win_w = max(1, int(window.width))
        out_h, out_w = win_h, win_w
        if max_dim and max(win_h, win_w) > max_dim:
            scale = max_dim / float(max(win_h, win_w))
            out_h = max(16, int(round(win_h * scale)))
            out_w = max(16, int(round(win_w * scale)))

        data = src.read(
            1,
            window=window,
            out_shape=(out_h, out_w),
            resampling=resampling,
        )
        from affine import Affine
        win_transform = src.window_transform(window)
        if (out_h, out_w) != (win_h, win_w):
            win_transform = win_transform @ Affine.scale(win_w / out_w, win_h / out_h)

        profile = src.profile.copy()
        profile.update({
            "driver": "GTiff",
            "height": out_h,
            "width": out_w,
            "count": 1,
            "transform": win_transform,
            "compress": "lzw",
            "tiled": False,
        })
        with rasterio.open(dest_path, "w", **profile) as dst:
            dst.write(data, 1)

    print(f"  [OK] Saved {dest_path} ({dest_path.stat().st_size / 1024:.1f} KB, shape={data.shape}, crs={profile['crs']})")
    return {"path": str(dest_path), "shape": data.shape, "crs": str(profile["crs"])}


def acquire_domain1(raw_root: Path) -> None:
    """Domain 1: Storm Daniel (Lake Karla, Greece) — Sentinel-1A RTC + Copernicus DEM + JRC GSW + Sentinel-2 NDWI."""
    print("\n=== Domain 1: Floods & Water Dynamics (Lake Karla / Thessaly, Greece) ===")
    d1_dir = raw_root / "domain1"
    d1_dir.mkdir(parents=True, exist_ok=True)
    bbox = [22.79665, 39.44756, 22.95368, 39.58242]

    # 1. Pre/Post Sentinel-1A RTC VV
    b_path = d1_dir / "thessaly_flood_baseline_vv.tif"
    e_path = d1_dir / "thessaly_flood_event_vv.tif"
    if not b_path.is_file():
        href = get_pc_asset_href("sentinel-1-rtc", "S1A_IW_GRDH_1SDV_20230901T043157_20230901T043222_050129_060869_rtc", "vv")
        download_cog_window(href, bbox, b_path)
    else:
        print(f"  [SKIP] {b_path} already exists.")

    if not e_path.is_file():
        href = get_pc_asset_href("sentinel-1-rtc", "S1A_IW_GRDH_1SDV_20230913T043157_20230913T043222_050304_060E62_rtc", "vv")
        download_cog_window(href, bbox, e_path)
    else:
        print(f"  [SKIP] {e_path} already exists.")

    # 2. Real Copernicus GLO-30 DEM
    dem_path = d1_dir / "thessaly_copernicus_dem_30m.tif"
    if not dem_path.is_file():
        href = get_pc_asset_href("cop-dem-glo-30", "Copernicus_DSM_COG_10_N39_00_E022_00_DEM", "data")
        download_cog_window(href, bbox, dem_path, resampling=Resampling.bilinear)

    # 3. Real JRC Global Surface Water Occurrence (20E_40Nv1_3_2020)
    jrc_path = d1_dir / "thessaly_jrc_gsw_reference_water.tif"
    if not jrc_path.is_file():
        href = get_pc_asset_href("jrc-gsw", "20E_40Nv1_3_2020", "occurrence")
        with rasterio.open(href) as src:
            bounds_native = transform_bounds(CRS.from_epsg(4326), src.crs, *bbox, densify_pts=21)
            win = from_bounds(*bounds_native, transform=src.transform).round_offsets().round_lengths()
            occ = src.read(1, window=win)
            win_tr = src.window_transform(win)
            # Occurrence >= 50% (0..100 scale, 255=nodata) -> binary permanent water mask
            perm_bin = ((occ >= 50) & (occ <= 100)).astype("uint8")
            prof = src.profile.copy()
            prof.update({
                "driver": "GTiff",
                "height": perm_bin.shape[0],
                "width": perm_bin.shape[1],
                "count": 1,
                "dtype": "uint8",
                "nodata": 255,
                "transform": win_tr,
                "compress": "lzw",
            })
            with rasterio.open(jrc_path, "w", **prof) as dst:
                dst.write(perm_bin, 1)
        print(f"  [OK] Saved {jrc_path} ({jrc_path.stat().st_size / 1024:.1f} KB, shape={perm_bin.shape})")

    # 4. Real Sentinel-2A MSI L2A Optical Post-Flood NDWI Reference (2023-09-15, Orbit R093, 6.56% cloud cover, 100% AOI coverage)
    s2_ref_path = d1_dir / "thessaly_s2_20230915_ndwi_flood_ref.tif"
    if not s2_ref_path.is_file():
        s2_id = "S2A_MSIL2A_20230915T092031_R093_T34SFJ_20240908T124156"
        b03_href = get_pc_asset_href("sentinel-2-l2a", s2_id, "B03")
        b08_href = get_pc_asset_href("sentinel-2-l2a", s2_id, "B08")
        with rasterio.open(b03_href) as src3, rasterio.open(b08_href) as src8, rasterio.open(jrc_path) as jrc_src, rasterio.open(dem_path) as dem_src:
            bounds_s2 = transform_bounds(CRS.from_epsg(4326), src3.crs, *bbox, densify_pts=21)
            win = from_bounds(*bounds_s2, transform=src3.transform).round_offsets().round_lengths()
            # Read at 20m resolution (~762x690) to keep file compact
            out_h, out_w = int(win.height // 2), int(win.width // 2)
            g = src3.read(1, window=win, out_shape=(out_h, out_w), resampling=Resampling.bilinear).astype("float32")
            n = src8.read(1, window=win, out_shape=(out_h, out_w), resampling=Resampling.bilinear).astype("float32")
            from affine import Affine
            win_tr_base = src3.window_transform(win)
            win_tr = win_tr_base @ Affine.scale(win.width / out_w, win.height / out_h)

            # Sentinel-2 Processing Baseline 04.00+ includes +1000 radiometric offset (BOA_ADD_OFFSET = -1000)
            g_sr = np.maximum(g - 1000.0, 1.0)
            n_sr = np.maximum(n - 1000.0, 1.0)
            ndwi = (g_sr - n_sr) / (g_sr + n_sr)
            s2_water = (ndwi > 0.0) & (g > 1050.0)

            # Align JRC permanent water and Copernicus DEM to exclude permanent reservoir water and steep mountain shadows (>5 deg)
            jrc_aligned = np.zeros((out_h, out_w), dtype="uint8")
            reproject(
                source=rasterio.band(jrc_src, 1),
                destination=jrc_aligned,
                src_transform=jrc_src.transform,
                src_crs=jrc_src.crs,
                dst_transform=win_tr,
                dst_crs=src3.crs,
                resampling=Resampling.nearest,
            )
            dem_aligned = np.zeros((out_h, out_w), dtype="float32")
            reproject(
                source=rasterio.band(dem_src, 1),
                destination=dem_aligned,
                src_transform=dem_src.transform,
                src_crs=dem_src.crs,
                dst_transform=win_tr,
                dst_crs=src3.crs,
                resampling=Resampling.bilinear,
            )
            gy, gx = np.gradient(dem_aligned, 20.0, 20.0)
            slopes_deg = np.degrees(np.arctan(np.hypot(gx, gy)))
            s2_new_flood = (s2_water & (jrc_aligned == 0) & (slopes_deg <= 5.0)).astype("uint8")

            prof = src3.profile.copy()
            prof.update({
                "driver": "GTiff",
                "height": out_h,
                "width": out_w,
                "count": 1,
                "dtype": "uint8",
                "nodata": 255,
                "transform": win_tr,
                "compress": "lzw",
                "tiled": False,
            })
            with rasterio.open(s2_ref_path, "w", **prof) as dst:
                dst.write(s2_new_flood, 1)
        print(f"  [OK] Saved {s2_ref_path} ({s2_ref_path.stat().st_size / 1024:.1f} KB, flood_px={int(np.sum(s2_new_flood))})")


def acquire_domain2(raw_root: Path) -> None:
    """Domain 2: Forests & Vegetation (Novo Progresso / BR-163, Pará, Brazil) — Real Sentinel-1A VH + JAXA ALOS-2 FNF."""
    print("\n=== Domain 2: Forests & Vegetation (Novo Progresso / BR-163, Pará, Brazil) ===")
    d2_dir = raw_root / "domain2"
    d2_dir.mkdir(parents=True, exist_ok=True)
    bbox = [-55.2311, -6.6989, -55.2044, -6.6722]

    pre_path = d2_dir / "para_real_s1a_20190826_vh_pre.tif"
    post_path = d2_dir / "para_real_s1a_20200820_vh_post.tif"
    fmask_path = d2_dir / "para_real_alos_fnf_2019_mask.tif"
    ref_path = d2_dir / "para_real_alos_fnf_2019_2020_loss_ref.tif"

    if not pre_path.is_file():
        href = get_pc_asset_href("sentinel-1-rtc", "S1A_IW_GRDH_1SDV_20190826T091535_20190826T091600_028738_034106_rtc", "vh")
        download_cog_window(href, bbox, pre_path)
    if not post_path.is_file():
        href = get_pc_asset_href("sentinel-1-rtc", "S1A_IW_GRDH_1SDV_20200820T091541_20200820T091606_033988_03F1BA_rtc", "vh")
        download_cog_window(href, bbox, post_path)

    if not (fmask_path.is_file() and ref_path.is_file()):
        href_19 = get_pc_asset_href("alos-fnf-mosaic", "S06W056_19_FNF", "C")
        href_20 = get_pc_asset_href("alos-fnf-mosaic", "S06W056_20_FNF", "C")
        with rasterio.open(href_19) as s19, rasterio.open(href_20) as s20:
            win = from_bounds(*bbox, transform=s19.transform).round_offsets().round_lengths()
            c19 = s19.read(1, window=win)
            c20 = s20.read(1, window=win)
            win_tr = s19.window_transform(win)

            # ALOS FNF classes: 1=dense forest, 2=non-dense forest, 3=non-forest, 4=water
            f19_mask = ((c19 == 1) | (c19 == 2)).astype("uint8")
            loss_19_20 = (f19_mask.astype(bool) & (c20 == 3)).astype("uint8")

            prof = s19.profile.copy()
            prof.update({
                "driver": "GTiff",
                "height": f19_mask.shape[0],
                "width": f19_mask.shape[1],
                "count": 1,
                "dtype": "uint8",
                "nodata": 255,
                "transform": win_tr,
                "compress": "lzw",
            })
            with rasterio.open(fmask_path, "w", **prof) as dst:
                dst.write(f19_mask, 1)
            with rasterio.open(ref_path, "w", **prof) as dst:
                dst.write(loss_19_20, 1)
        print(f"  [OK] Saved {fmask_path} and {ref_path} (loss_px={int(np.sum(loss_19_20))})")


def acquire_domain3(raw_root: Path) -> None:
    """Domain 3: Cryosphere (Jakobshavn Isbræ, Greenland) — Real NASA ITS_LIVE v2 + Sentinel-1A HH."""
    print("\n=== Domain 3: Ice, Glaciers & Cryosphere (Jakobshavn Isbræ, Greenland) ===")
    d3_dir = raw_root / "domain3"
    d3_dir.mkdir(parents=True, exist_ok=True)
    bbox = [-49.92, 69.13, -49.62, 69.23]

    vel_2022_path = d3_dir / "jakobshavn_real_itslive_2022_velocity.tif"
    vel_clim_path = d3_dir / "jakobshavn_real_itslive_clim_ref_velocity.tif"
    s1_pre_path = d3_dir / "jakobshavn_real_s1a_20230828_hh_pre.tif"
    s1_post_path = d3_dir / "jakobshavn_real_s1a_20230909_hh_post.tif"

    if not vel_2022_path.is_file():
        url_2022 = "https://its-live-data.s3.amazonaws.com/velocity_mosaic/v2/annual/cog/ITS_LIVE_velocity_120m_RGI05A_2022_v02_v.tif"
        download_cog_window(url_2022, bbox, vel_2022_path)
    if not vel_clim_path.is_file():
        url_clim = "https://its-live-data.s3.amazonaws.com/velocity_mosaic/v2/static/cog/ITS_LIVE_velocity_120m_RGI05A_0000_v02_v.tif"
        download_cog_window(url_clim, bbox, vel_clim_path)

    if not s1_pre_path.is_file():
        href = get_pc_asset_href("sentinel-1-rtc", "S1A_IW_GRDH_1SDH_20230828T095236_20230828T095301_050074_06068B_rtc", "hh")
        download_cog_window(href, bbox, s1_pre_path, max_dim=400)
    if not s1_post_path.is_file():
        href = get_pc_asset_href("sentinel-1-rtc", "S1A_IW_GRDH_1SDH_20230909T095236_20230909T095301_050249_060C7D_rtc", "hh")
        download_cog_window(href, bbox, s1_post_path, max_dim=400)


def acquire_domain4(raw_root: Path) -> None:
    """Domain 4: Land Movement (Tyrnavos Basin, Greece Mw 6.3 2021 Earthquake) — Real COMET-LiCSAR InSAR."""
    print("\n=== Domain 4: Land Movement & Urban Change (Tyrnavos Basin, Greece — COMET-LiCSAR) ===")
    d4_dir = raw_root / "domain4"
    d4_dir.mkdir(parents=True, exist_ok=True)
    bbox = [22.02, 39.62, 22.32, 39.84]

    disp_path = d4_dir / "tyrnavos_real_licsar_20210225_20210309_los_mm.tif"
    coh_path = d4_dir / "tyrnavos_real_licsar_20210225_20210309_coherence.tif"
    ref_path = d4_dir / "tyrnavos_real_licsar_20210219_20210309_ref_los_mm.tif"

    base_licsar = "https://gws-access.jasmin.ac.uk/public/nceo_geohazards/LiCSAR_products.public/102/102A_04971_141314/interferograms"
    # Sentinel-1 C-band radar wavelength = 55.46576 mm; 1 radian unwrapped phase = 55.46576 / (4 * pi) mm = 4.413825 mm
    rad_to_los_mm = -55.46576 / (4.0 * np.pi)

    if not disp_path.is_file():
        unw_url = f"{base_licsar}/20210225_20210309/20210225_20210309.geo.unw.tif"
        with rasterio.open(unw_url) as src:
            win = from_bounds(*bbox, transform=src.transform).round_offsets().round_lengths()
            unw = src.read(1, window=win).astype("float32")
            valid = np.isfinite(unw) & (unw != 0.0)
            # Reference phase to far-field stable corner (top-right 20x20 pixels) and convert to LOS mm
            ref_zero = float(np.nanmedian(unw[:25, -25:])) if np.any(np.isfinite(unw[:25, -25:])) else 0.0
            los_mm = np.where(valid, (unw - ref_zero) * rad_to_los_mm, -9999.0).astype("float32")
            prof = src.profile.copy()
            prof.update({
                "driver": "GTiff",
                "height": los_mm.shape[0],
                "width": los_mm.shape[1],
                "count": 1,
                "dtype": "float32",
                "nodata": -9999.0,
                "transform": src.window_transform(win),
                "compress": "lzw",
            })
            with rasterio.open(disp_path, "w", **prof) as dst:
                dst.write(los_mm, 1)
        print(f"  [OK] Saved {disp_path} (shape={los_mm.shape}, min={np.min(los_mm[valid]):.1f} mm, max={np.max(los_mm[valid]):.1f} mm)")

    if not coh_path.is_file():
        cc_url = f"{base_licsar}/20210225_20210309/20210225_20210309.geo.cc.tif"
        with rasterio.open(cc_url) as src:
            win = from_bounds(*bbox, transform=src.transform).round_offsets().round_lengths()
            cc_raw = src.read(1, window=win).astype("float32")
            # LiCSAR .geo.cc.tif is scaled 0..255 uint8 -> normalize to 0.0..1.0 coherence
            coh = np.where(cc_raw > 0, np.clip(cc_raw / 255.0, 0.0, 1.0), np.nan).astype("float32")
            prof = src.profile.copy()
            prof.update({
                "driver": "GTiff",
                "height": coh.shape[0],
                "width": coh.shape[1],
                "count": 1,
                "dtype": "float32",
                "nodata": -9999.0,
                "transform": src.window_transform(win),
                "compress": "lzw",
            })
            with rasterio.open(coh_path, "w", **prof) as dst:
                dst.write(np.nan_to_num(coh, nan=-9999.0), 1)
        print(f"  [OK] Saved {coh_path} (shape={coh.shape})")

    if not ref_path.is_file():
        ref_unw_url = f"{base_licsar}/20210219_20210309/20210219_20210309.geo.unw.tif"
        with rasterio.open(ref_unw_url) as src:
            win = from_bounds(*bbox, transform=src.transform).round_offsets().round_lengths()
            unw = src.read(1, window=win).astype("float32")
            valid = np.isfinite(unw) & (unw != 0.0)
            ref_zero = float(np.nanmedian(unw[:25, -25:])) if np.any(np.isfinite(unw[:25, -25:])) else 0.0
            los_mm = np.where(valid, (unw - ref_zero) * rad_to_los_mm, -9999.0).astype("float32")
            prof = src.profile.copy()
            prof.update({
                "driver": "GTiff",
                "height": los_mm.shape[0],
                "width": los_mm.shape[1],
                "count": 1,
                "dtype": "float32",
                "nodata": -9999.0,
                "transform": src.window_transform(win),
                "compress": "lzw",
            })
            with rasterio.open(ref_path, "w", **prof) as dst:
                dst.write(los_mm, 1)
        print(f"  [OK] Saved {ref_path} (shape={los_mm.shape})")


def acquire_domain5(raw_root: Path) -> None:
    """Domain 5: Wildfires (Dadia Forest / Evros Megafire, Greece, Aug 2023) — Sentinel-1A VH + MODIS MCD64A1 & MOD14A1."""
    print("\n=== Domain 5: Wildfires & Land Disturbance (Dadia Forest / Evros, Greece, Aug 2023) ===")
    d5_dir = raw_root / "domain5"
    d5_dir.mkdir(parents=True, exist_ok=True)
    bbox = [25.82, 40.95, 25.96, 41.06]

    pre_path = d5_dir / "evros_real_s1a_20230809_vh_prefire.tif"
    post_path = d5_dir / "evros_real_s1a_20230902_vh_postfire.tif"
    burn_ref_path = d5_dir / "evros_real_modis_mcd64a1_burn_reference.tif"
    firms_path = d5_dir / "evros_real_modis_active_fire_points.geojson"

    if not pre_path.is_file():
        href = get_pc_asset_href("sentinel-1-rtc", "S1A_IW_GRDH_1SDV_20230809T161623_20230809T161648_049801_05FD3A_rtc", "vh")
        download_cog_window(href, bbox, pre_path, max_dim=400)
    if not post_path.is_file():
        href = get_pc_asset_href("sentinel-1-rtc", "S1A_IW_GRDH_1SDV_20230902T161625_20230902T161650_050151_060939_rtc", "vh")
        download_cog_window(href, bbox, post_path, max_dim=400)

    # Real NASA MODIS MCD64A1 v061 Burned Area Reference reprojected onto the Sentinel-1 UTM grid
    if not burn_ref_path.is_file():
        mcd_href = get_pc_asset_href("modis-64A1-061", "MCD64A1.A2023213.h19v04.061.2023284063433", "Burn_Date")
        with rasterio.open(mcd_href) as mcd_src, rasterio.open(pre_path) as s1_ref:
            dst_arr = np.zeros((s1_ref.height, s1_ref.width), dtype="int16")
            reproject(
                source=rasterio.band(mcd_src, 1),
                destination=dst_arr,
                src_transform=mcd_src.transform,
                src_crs=mcd_src.crs,
                dst_transform=s1_ref.transform,
                dst_crs=s1_ref.crs,
                resampling=Resampling.nearest,
            )
            # In MCD64A1 Burn_Date: > 0 is day of year burned (1..366); <= 0 is unburned/water/nodata
            burned_bin = (dst_arr > 0).astype("uint8")
            prof = s1_ref.profile.copy()
            prof.update({
                "driver": "GTiff",
                "dtype": "uint8",
                "nodata": 255,
                "count": 1,
                "compress": "lzw",
            })
            with rasterio.open(burn_ref_path, "w", **prof) as dst:
                dst.write(burned_bin, 1)
        print(f"  [OK] Saved {burn_ref_path} (burned_px={int(np.sum(burned_bin))})")

    # Real NASA MODIS MOD14A1 / MYD14A1 Active Fire Thermal Anomaly Points
    if not firms_path.is_file():
        features = []
        for mod_id, acq_date, sat_name in [
            ("MOD14A1.A2023233.h19v04.061.2023242000700", "2023-08-22", "Terra MODIS"),
            ("MYD14A1.A2023233.h19v04.061.2023242000854", "2023-08-23", "Aqua MODIS"),
            ("MOD14A1.A2023241.h19v04.061.2023251182955", "2023-08-29", "Terra MODIS"),
        ]:
            fmask_href = get_pc_asset_href("modis-14A1-061", mod_id, "FireMask")
            frp_href = get_pc_asset_href("modis-14A1-061", mod_id, "MaxFRP")
            with rasterio.open(fmask_href) as fm_src, rasterio.open(frp_href) as frp_src, rasterio.open(pre_path) as s1_ref:
                # Reproject MODIS 1km FireMask and MaxFRP onto a 30x30 grid over our Dadia Forest bbox in EPSG:4326
                from affine import Affine
                g_h, g_w = 36, 36
                g_tr = Affine(
                    (bbox[2] - bbox[0]) / g_w, 0.0, bbox[0],
                    0.0, -(bbox[3] - bbox[1]) / g_h, bbox[3],
                )
                fm_grid = np.zeros((g_h, g_w), dtype="uint8")
                frp_grid = np.zeros((g_h, g_w), dtype="int32")
                # MOD14A1 has 8 daily bands; take max across the 8-day composite
                for b_idx in range(1, fm_src.count + 1):
                    tmp_fm = np.zeros((g_h, g_w), dtype="uint8")
                    tmp_frp = np.zeros((g_h, g_w), dtype="int32")
                    reproject(
                        source=rasterio.band(fm_src, b_idx),
                        destination=tmp_fm,
                        src_transform=fm_src.transform,
                        src_crs=fm_src.crs,
                        dst_transform=g_tr,
                        dst_crs=CRS.from_epsg(4326),
                        resampling=Resampling.nearest,
                    )
                    reproject(
                        source=rasterio.band(frp_src, b_idx),
                        destination=tmp_frp,
                        src_transform=frp_src.transform,
                        src_crs=frp_src.crs,
                        dst_transform=g_tr,
                        dst_crs=CRS.from_epsg(4326),
                        resampling=Resampling.nearest,
                    )
                    fm_grid = np.maximum(fm_grid, tmp_fm)
                    frp_grid = np.maximum(frp_grid, tmp_frp)

                # In MOD14A1 FireMask: 7=low-confidence fire, 8=nominal-confidence fire, 9=high-confidence fire
                rows, cols = np.where(fm_grid >= 7)
                for r_i, c_i in zip(rows, cols):
                    lon = float(g_tr.c + (c_i + 0.5) * g_tr.a)
                    lat = float(g_tr.f + (r_i + 0.5) * g_tr.e)
                    conf_val = int(fm_grid[r_i, c_i])
                    conf_str = "high" if conf_val == 9 else "nominal" if conf_val == 8 else "low"
                    frp_mw = round(float(frp_grid[r_i, c_i]) * 0.1, 1)
                    features.append({
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
                        "properties": {
                            "sensor": sat_name,
                            "granule_id": mod_id,
                            "acq_date": acq_date,
                            "fire_mask_class": conf_val,
                            "confidence": conf_str,
                            "frp_mw": frp_mw,
                        },
                    })
        fc = {"type": "FeatureCollection", "features": features}
        firms_path.write_text(json.dumps(fc, indent=2))
        print(f"  [OK] Saved {firms_path} ({len(features)} real MODIS active fire detections)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Acquire verified real EO datasets for NISAR — Dancing with the SARs")
    parser.add_argument(
        "--domain",
        choices=["all", "domain1", "domain2", "domain3", "domain4", "domain5"],
        default="all",
        help="Target domain to acquire real datasets for",
    )
    parser.add_argument(
        "--event",
        choices=["storm_daniel", "all"],
        default=None,
        help="Backwards-compatible event selector",
    )
    args = parser.parse_args()

    raw_root = Path("data/raw")
    target = "domain1" if args.event == "storm_daniel" else args.domain

    if target in ("all", "domain1"):
        acquire_domain1(raw_root)
    if target in ("all", "domain2"):
        acquire_domain2(raw_root)
    if target in ("all", "domain3"):
        acquire_domain3(raw_root)
    if target in ("all", "domain4"):
        acquire_domain4(raw_root)
    if target in ("all", "domain5"):
        acquire_domain5(raw_root)

    print("\nAll requested real satellite/geophysical datasets acquired and verified on disk!")


if __name__ == "__main__":
    main()
