from datetime import datetime
from pathlib import Path
import re
from typing import Any, Optional
import html
import json
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.schemas.dataset import DatasetBase
from app.services.dataset_service import DatasetService, DatasetValidationError
from app.services.processing_service import ProcessingService

router = APIRouter()

GAZETTEER_PLACES = [
    {
        "id": "place-lake-karla-greece",
        "name": "Lake Karla / Thessaly Basin, Greece",
        "category": "Floodplain & Reservoir (Verified Real Data)",
        "country": "Greece",
        "bbox": [22.7966, 39.4475, 22.9537, 39.5824],
        "center": [22.875, 39.515],
        "recommended_domains": ["domain1"],
        "notes": "Verified real Sentinel-1A RTC flood pair, Copernicus 30m DEM, JRC Surface Water, and Sentinel-2 NDWI flood reference staged locally.",
    },
    {
        "id": "place-novo-progresso-para-brazil",
        "name": "Novo Progresso / BR-163 Corridor, Pará, Brazil",
        "category": "Tropical Forest Frontier (Verified Real Data)",
        "country": "Brazil",
        "bbox": [-55.2311, -6.6989, -55.2044, -6.6722],
        "center": [-55.2178, -6.6855],
        "recommended_domains": ["domain2"],
        "notes": "Verified real Sentinel-1A RTC VH (2019–2020) and JAXA ALOS-2 PALSAR-2 Forest/Non-Forest reference datasets staged locally.",
    },
    {
        "id": "place-jakobshavn-greenland",
        "name": "Jakobshavn Isbræ (Sermeq Kujalleq), Greenland",
        "category": "Marine-Terminating Outlet Glacier (Verified Real Data)",
        "country": "Greenland",
        "bbox": [-49.92, 69.13, -49.62, 69.23],
        "center": [-49.77, 69.18],
        "recommended_domains": ["domain5"],
        "notes": "Verified real NASA MEaSUREs ITS_LIVE v2 ice velocity mosaics (EPSG:3413) and Sentinel-1A HH terminus pair staged locally.",
    },
    {
        "id": "place-tyrnavos-larissa-greece",
        "name": "Tyrnavos / Damasi Coseismic Basin, Thessaly, Greece",
        "category": "Active Tectonic Basin (Verified Real Data)",
        "country": "Greece",
        "bbox": [22.02, 39.62, 22.32, 39.84],
        "center": [22.17, 39.73],
        "recommended_domains": ["domain3"],
        "notes": "Verified real COMET-LiCSAR Sentinel-1 unwrapped coseismic InSAR displacement and coherence for the March 2021 Mw 6.3 earthquake staged locally.",
    },
    {
        "id": "place-dadia-evros-greece",
        "name": "Dadia-Lefkimi-Soufli National Park, Evros, Greece",
        "category": "Mediterranean Pine Forest (Verified Real Data)",
        "country": "Greece",
        "bbox": [25.82, 40.95, 25.96, 41.06],
        "center": [25.89, 41.005],
        "recommended_domains": ["domain2"],
        "notes": "Verified real Sentinel-1A RTC VH pre/post wildfire pair, NASA MODIS MCD64A1 burn reference, and MODIS active thermal detections staged locally.",
    },
    {
        "id": "place-tapajos-para-brazil",
        "name": "Tapajós Tropical Forest Benchmark, Pará, Brazil",
        "category": "Tropical Rainforest (Synthetic Benchmark)",
        "country": "Brazil",
        "bbox": [-55.025, -3.525, -55.005, -3.505],
        "center": [-55.015, -3.515],
        "recommended_domains": ["domain2"],
        "notes": "Georeferenced synthetic HV canopy disturbance & protected reserve demonstration fixtures available locally.",
    },
    {
        "id": "place-san-joaquin-california",
        "name": "San Joaquin / Corcoran Aquifer Basin, California",
        "category": "Agricultural Subsidence Bowl (Synthetic Benchmark)",
        "country": "United States",
        "bbox": [-119.560, 36.098, -119.535, 36.120],
        "center": [-119.547, 36.109],
        "recommended_domains": ["unresolved"],
        "notes": "Georeferenced synthetic InSAR LOS velocity, coherence, and canal exposure demonstration fixtures available locally.",
    },
    {
        "id": "place-butte-tehama-california",
        "name": "Cohasset / Butte & Tehama Foothills, California",
        "category": "Wildland-Urban Interface Forest (Synthetic Benchmark)",
        "country": "United States",
        "bbox": [-121.762, 39.946, -121.744, 39.960],
        "center": [-121.753, 39.953],
        "recommended_domains": ["domain2"],
        "notes": "Georeferenced synthetic wildfire HV SAR, FIRMS thermal points, and WUI exposure fixtures available locally.",
    },
    {
        "id": "place-tampa-bay-florida",
        "name": "Tampa Bay & Peace River Basin, Florida",
        "category": "Coastal Cyclone Corridor (External Discovery)",
        "country": "United States",
        "bbox": [-82.85, 27.35, -81.80, 28.15],
        "center": [-82.32, 27.75],
        "recommended_domains": ["domain1", "domain2"],
        "notes": "External discovery study area; no local SAR rasters currently staged.",
    },
    {
        "id": "place-pine-island-antarctica",
        "name": "Pine Island Glacier, West Antarctica",
        "category": "Antarctic Ice Stream (External Discovery)",
        "country": "Antarctica",
        "bbox": [-102.0, -75.3, -99.5, -74.7],
        "center": [-100.75, -75.0],
        "recommended_domains": ["domain5"],
        "notes": "External ITS_LIVE / Sentinel-1 study area; no local rasters currently staged.",
    },
]

CURATED_EVENTS = [
    {
        "id": "event-thessaly-storm-daniel-2023",
        "name": "Storm Daniel Severe Inundation (Lake Karla, Greece)",
        "date": "2023-09-13",
        "acquisition_dates": ["2023-09-01", "2023-09-13", "2023-09-15"],
        "type": "Extreme Inundation",
        "location": "Thessaly Basin, Greece",
        "bbox": [22.7966, 39.4475, 22.9537, 39.5824],
        "center": [22.875, 39.515],
        "sensor": "Copernicus Sentinel-1A IW GRDH RTC (VV) + Copernicus GLO-30 DEM + JRC GSW + Sentinel-2A MSI L2A",
        "dataset_source": "Microsoft Planetary Computer STAC / Copernicus Open Access Hub / EC JRC",
        "available_workflow": "Domain 1: Bounded Otsu & ΔVV Backscatter Drop + Slope & Permanent-Water Masking + Optical NDWI Validation",
        "reference_data_available": True,
        "reference_source": "Sentinel-2A MSI L2A Post-Flood Optical NDWI (2023-09-15, S2A_MSIL2A_20230915T092031_R093_T34SFJ) & JRC Global Surface Water v1.3",
        "validation_status": "Independent Real Reference Validation (Sentinel-2A Optical NDWI + JRC Permanent Water)",
        "description": (
            "Historic flash and riverine flood triggered by Storm Daniel, submerging agricultural plains and "
            "dramatically expanding Lake Karla. Validated with real Copernicus Sentinel-1A RTC acquisitions, "
            "Copernicus 30m DEM, JRC Global Surface Water, and independent Sentinel-2A optical flood reference."
        ),
        "domains_involved": ["domain1"],
        "status": "data_available",
        "data_readiness": "verified_real",
        "is_synthetic": False,
        "dataset_ids": {
            "domain1": {
                "baseline": "5c351e81-1dfc-4d6b-9eec-9aed124eee8a",
                "event": "15a8d70a-999e-4575-a2b7-b7b502f0dad8",
                "reference_water": "ds-real-thessaly-jrc-water",
                "dem": "ds-real-thessaly-cop-dem",
                "reference_flood": "ds-real-thessaly-s2-flood-ref",
                "exposure_assets": "ds-exp-thessaly-assets",
            }
        },
        "evidence_summary": (
            "VERIFIED REAL SATELLITE EVENT: Sentinel-1A IW GRDH RTC VV baseline (2023-09-01) and crisis pass (2023-09-13) "
            "in EPSG:32634 (10m grid), paired with real Copernicus GLO-30 DEM, JRC Global Surface Water occurrence, "
            "and independent Sentinel-2A MSI L2A optical post-flood reference (2023-09-15)."
        ),
    },
    {
        "id": "event-para-br163-real-deforestation-2020",
        "name": "Amazon BR-163 Frontier Canopy Loss (Novo Progresso, Pará, Brazil)",
        "date": "2020-08-20",
        "acquisition_dates": ["2019-08-26", "2020-08-20"],
        "type": "Canopy Structural Loss",
        "location": "Novo Progresso / BR-163, Pará, Brazil",
        "bbox": [-55.2311, -6.6989, -55.2044, -6.6722],
        "center": [-55.2178, -6.6855],
        "sensor": "Copernicus Sentinel-1A IW GRDH RTC (VH) + JAXA ALOS-2 PALSAR-2 (L-Band FNF)",
        "dataset_source": "Microsoft Planetary Computer STAC (sentinel-1-rtc & alos-fnf-mosaic)",
        "available_workflow": "Domain 2: Cross-Polarized (ΔVH) Volume Scattering Drop + ALOS-2 Baseline Forest Mask + Independent L-Band Loss Validation",
        "reference_data_available": True,
        "reference_source": "JAXA ALOS-2 PALSAR-2 Annual Forest/Non-Forest Mosaic Transition (S06W056_19_FNF → S06W056_20_FNF)",
        "validation_status": "Independent Real Reference Validation (JAXA ALOS-2 PALSAR-2 L-band Forest Loss)",
        "description": (
            "Large geometric forest clearings along the BR-163 frontier corridor near Novo Progresso (Pará, Brazil) "
            "between August 2019 and August 2020, imaged by co-orbital Sentinel-1A C-band VH passes and independently "
            "validated against JAXA ALOS-2 PALSAR-2 L-band annual Forest/Non-Forest mosaics."
        ),
        "domains_involved": ["domain2"],
        "status": "data_available",
        "data_readiness": "verified_real",
        "is_synthetic": False,
        "dataset_ids": {
            "domain2": {
                "baseline": "ds-real-d2-base",
                "event": "ds-real-d2-event",
                "forest_mask": "ds-real-d2-mask",
                "reference_disturbance": "ds-real-d2-ref",
                "exposure_assets": "ds-real-d2-exp",
            }
        },
        "evidence_summary": (
            "VERIFIED REAL SATELLITE EVENT: Real Sentinel-1A RTC VH baseline (2019-08-26, Orbit 141) and monitoring pass "
            "(2020-08-20, Orbit 141) in EPSG:32722, constrained by JAXA ALOS-2 PALSAR-2 2019 forest mask and validated "
            "against JAXA ALOS-2 2019→2020 forest-loss reference."
        ),
    },
    {
        "id": "event-jakobshavn-itslive-real-2022",
        "name": "Jakobshavn Isbræ Fast-Streaming Outlet & Terminus Dynamics (Greenland)",
        "date": "2023-09-09",
        "acquisition_dates": ["2022-07-01", "2023-08-28", "2023-09-09"],
        "type": "Glacier Velocity & Calving",
        "location": "Jakobshavn Isbræ (Sermeq Kujalleq), West Greenland",
        "bbox": [-49.92, 69.13, -49.62, 69.23],
        "center": [-49.77, 69.18],
        "sensor": "NASA MEaSUREs ITS_LIVE v2 + Copernicus Sentinel-1A IW GRDH RTC (HH)",
        "dataset_source": "NASA MEaSUREs ITS_LIVE AWS Open Data + Microsoft Planetary Computer STAC",
        "available_workflow": "Domain 5: Pre-Computed ITS_LIVE Surface Flow Velocity Analysis + Repeat-Pass Sentinel-1 HH Terminus Comparison + Climatological Anomaly Evaluation",
        "reference_data_available": True,
        "reference_source": "NASA MEaSUREs ITS_LIVE v2 Static Multi-Year Climatological Velocity Mosaic (ITS_LIVE_velocity_120m_RGI05A_0000_v02_v.tif — Same Processing Suite)",
        "validation_status": "Climatological / Multi-Year Comparative Baseline (Evaluates 2022 Velocity Anomaly vs. ITS_LIVE Climatology, Not Independent Ground Truth)",
        "description": (
            "Real surface flow velocity analysis of Greenland's fastest-flowing marine-terminating outlet glacier "
            "(Sermeq Kujalleq / Jakobshavn Isbræ) using NASA MEaSUREs ITS_LIVE v2 120m velocity mosaics (EPSG:3413) "
            "compared against the multi-year ITS_LIVE static reference mosaic, paired with co-orbital Sentinel-1A HH repeat passes over the Ilulissat Icefjord."
        ),
        "domains_involved": ["domain5"],
        "status": "data_available",
        "data_readiness": "verified_real",
        "is_synthetic": False,
        "dataset_ids": {
            "domain5": {
                "velocity": "ds-real-d3-vel",
                "baseline_sar": "ds-real-d3-sar-base",
                "event_sar": "ds-real-d3-sar-event",
                "reference_velocity": "ds-real-d3-ref",
                "exposure_assets": "ds-real-d3-exp",
            }
        },
        "evidence_summary": (
            "VERIFIED REAL SATELLITE EVENT: Real NASA MEaSUREs ITS_LIVE v2 2022 annual velocity mosaic (m/year, EPSG:3413) "
            "compared against the ITS_LIVE multi-year climatological reference mosaic, plus real Sentinel-1A HH terminus passes (2023-08-28 & 2023-09-09)."
        ),
    },
    {
        "id": "event-tyrnavos-earthquake-insar-real-2021",
        "name": "Tyrnavos Mw 6.3 Coseismic Ground Deformation (Thessaly, Greece, Mar 2021)",
        "date": "2021-03-09",
        "acquisition_dates": ["2021-02-19", "2021-02-25", "2021-03-09"],
        "type": "Coseismic InSAR Subsidence",
        "location": "Tyrnavos / Damasi Basin, Greece",
        "bbox": [22.02, 39.62, 22.32, 39.84],
        "center": [22.17, 39.73],
        "sensor": "Copernicus Sentinel-1A/1B InSAR (COMET-LiCSAR Track 102A)",
        "dataset_source": "COMET-LiCSAR Sentinel-1 InSAR Portal (Frame 102A_04971_141314, JASMIN Public Archive)",
        "available_workflow": "Domain 3: Pre-Computed Unwrapped InSAR LOS Displacement Analysis + Interferometric Coherence Filtering + Cross-Pair Interferogram Comparison",
        "reference_data_available": True,
        "reference_source": "COMET-LiCSAR 18-Day Sentinel-1B/1A Unwrapped Coseismic Interferogram (20210219_20210309.geo.unw.tif — Independent 2021-02-19 S1B Primary, Shared 2021-03-09 S1A Secondary)",
        "validation_status": "Partially Independent Cross-Interferogram Comparison (Independent 2021-02-19 S1B Pre-Event Pass, Shared 2021-03-09 S1A Post-Event Pass & LiCSAR Chain)",
        "description": (
            "Real unwrapped Sentinel-1 InSAR Line-of-Sight ground deformation across the 3 March 2021 Mw 6.3 Tyrnavos/Elassona "
            "normal-fault earthquake in Thessaly, Greece. Reveals the hanging-wall subsidence bowl reaching -368 mm LOS "
            "between 2021-02-25 and 2021-03-09, filtered by phase coherence and compared against a partially independent 18-day S1B–S1A interferogram."
        ),
        "domains_involved": ["domain3"],
        "status": "data_available",
        "data_readiness": "verified_real",
        "is_synthetic": False,
        "recommended_parameters": {
            "min_coherence": 0.35,
            "subsidence_threshold_mm": -80.0,
            "color_stretch_mm": 300.0,
        },
        "dataset_ids": {
            "domain3": {
                "displacement": "ds-real-d4-disp",
                "coherence": "ds-real-d4-coh",
                "reference_displacement": "ds-real-d4-ref",
                "exposure_assets": "ds-real-d4-exp",
            }
        },
        "evidence_summary": (
            "VERIFIED REAL SATELLITE EVENT: Real COMET-LiCSAR Frame 102A_04971_141314 unwrapped 12-day coseismic interferogram "
            "(2021-02-25 to 2021-03-09, mm LOS) and coherence raster, compared against the partially independent 18-day S1B–S1A interferogram (2021-02-19 to 2021-03-09)."
        ),
    },
    {
        "id": "event-evros-dadia-megafire-real-2023",
        "name": "Evros / Dadia Forest Megafire Burn Scar & Thermal Analysis (Greece, Aug 2023)",
        "date": "2023-09-02",
        "acquisition_dates": ["2023-08-09", "2023-08-23", "2023-09-02"],
        "type": "Wildfire Disturbance",
        "location": "Dadia-Lefkimi-Soufli National Park, Evros, Greece",
        "bbox": [25.82, 40.95, 25.96, 41.06],
        "center": [25.89, 41.005],
        "sensor": "Copernicus Sentinel-1A IW GRDH RTC (VH) + NASA Terra/Aqua MODIS (MOD14A1/MYD14A1 & MCD64A1)",
        "dataset_source": "Microsoft Planetary Computer STAC (sentinel-1-rtc, modis-14A1-061, modis-64A1-061)",
        "available_workflow": "Domain 2: Cross-Polarized (ΔVH) Canopy Burn Disturbance + MODIS Active Fire Thermal Corroboration + MODIS MCD64A1 Burn Perimeter Validation",
        "reference_data_available": True,
        "reference_source": "NASA EOSDIS MODIS MCD64A1 v061 Monthly Burned Area (MCD64A1.A2023213.h19v04.061) & MOD14A1/MYD14A1 Active Fire Detections",
        "validation_status": "Independent Real Reference Validation (NASA MODIS MCD64A1 Burned Area + 1,422 Active Thermal Detections)",
        "description": (
            "Europe's largest recorded wildfire in modern history (August 2023 Evros / Dadia Forest megafire in northeastern Greece). "
            "Combines real pre-fire (2023-08-09) and post-fire (2023-09-02) Sentinel-1A C-band VH backscatter with 1,422 real "
            "NASA Terra/Aqua MODIS active fire thermal anomaly detections and the NASA MODIS MCD64A1 burned area product."
        ),
        "domains_involved": ["domain2"],
        "status": "data_available",
        "data_readiness": "verified_real",
        "is_synthetic": False,
        "dataset_ids": {
            "domain2": {
                "baseline": "ds-real-d5-base",
                "event": "ds-real-d5-event",
                "fire_detections": "ds-real-d5-firms",
                "reference_disturbance": "ds-real-d5-ref",
                "exposure_assets": "ds-real-d5-exp",
            }
        },
        "evidence_summary": (
            "VERIFIED REAL SATELLITE EVENT: Real Sentinel-1A RTC VH pre-fire (2023-08-09, Orbit 29) and post-fire (2023-09-02, Orbit 29) "
            "in EPSG:32635, corroborated by 1,422 NASA MODIS active fire thermal points and validated against NASA MODIS MCD64A1 burned area."
        ),
    },
    {
        "id": "event-para-canopy-disturbance-demo",
        "name": "Tapajós Basin Canopy Disturbance (Pará, Brazil — Synthetic Benchmark)",
        "date": "2025-08-15",
        "acquisition_dates": ["2025-06-01", "2025-08-15"],
        "type": "Canopy Structural Loss (Demo)",
        "location": "Tapajós, Pará, Brazil",
        "bbox": [-55.022, -3.522, -55.006, -3.506],
        "center": [-55.014, -3.514],
        "sensor": "Simulated NISAR L-band / S1 HV Fixture",
        "dataset_source": "Local Synthetic Benchmark Generator (UTM Zone 21S)",
        "available_workflow": "Domain 2: Synthetic Benchmark Verification Workflow",
        "reference_data_available": True,
        "reference_source": "Synthetic Reference Disturbance Benchmark Mask (is_synthetic=True)",
        "validation_status": "Demonstration / Synthetic Benchmark Evaluation",
        "description": (
            "Georeferenced synthetic benchmark scenario illustrating cross-polarized (HV) volume scattering drop across "
            "controlled canopy clearings for automated algorithm verification."
        ),
        "domains_involved": ["domain2"],
        "status": "demo_available",
        "data_readiness": "synthetic_demo",
        "is_synthetic": True,
        "dataset_ids": {
            "domain2": {
                "baseline": "ds-demo-d2-base",
                "event": "ds-demo-d2-event",
                "forest_mask": "ds-demo-d2-mask",
                "reference_disturbance": "ds-demo-d2-ref",
                "exposure_assets": "ds-demo-d2-exp",
            }
        },
        "evidence_summary": (
            "SYNTHETIC DEMONSTRATION FIXTURE: Georeferenced in UTM Zone 21S (EPSG:32721) with baseline/monitoring HV rasters, "
            "forest mask, reference disturbance benchmark, and protected reserve polygons."
        ),
    },
    {
        "id": "event-jakobshavn-retreat-2026",
        "name": "Jakobshavn Isbræ Terminus Calving (Greenland — Synthetic Benchmark)",
        "date": "2025-07-20",
        "acquisition_dates": ["2025-07-01", "2025-07-15", "2025-07-20"],
        "type": "Glacier Calving & Flow (Demo)",
        "location": "West Greenland Ice Sheet",
        "bbox": [-49.860, 69.162, -49.782, 69.190],
        "center": [-49.821, 69.176],
        "sensor": "Simulated ITS_LIVE / SAR HH Fixture",
        "dataset_source": "Local Synthetic Benchmark Generator (UTM Zone 22N)",
        "available_workflow": "Domain 5: Synthetic Benchmark Verification Workflow",
        "reference_data_available": True,
        "reference_source": "Synthetic Reference Velocity Benchmark (is_synthetic=True)",
        "validation_status": "Demonstration / Synthetic Benchmark Evaluation",
        "description": (
            "Georeferenced synthetic outlet glacier scenario combining pre/post calving front SAR backscatter with "
            "simulated surface ice velocity fields (m/year) for automated unit test verification."
        ),
        "domains_involved": ["domain5"],
        "status": "demo_available",
        "data_readiness": "synthetic_demo",
        "is_synthetic": True,
        "dataset_ids": {
            "domain5": {
                "velocity": "ds-demo-d3-vel",
                "baseline_sar": "ds-demo-d3-sar-base",
                "event_sar": "ds-demo-d3-sar-event",
                "reference_velocity": "ds-demo-d3-ref",
                "exposure_assets": "ds-demo-d3-exp",
            }
        },
        "evidence_summary": (
            "SYNTHETIC DEMONSTRATION FIXTURE: Georeferenced in UTM Zone 22N (EPSG:32622) with simulated ITS_LIVE velocity, "
            "pre/post terminus SAR rasters, continuous validation reference, and Ilulissat fjord boundary."
        ),
    },
    {
        "id": "event-centralvalley-subsidence-2026",
        "name": "Central Valley Aquifer Compaction (California — Synthetic Benchmark)",
        "date": "2025-09-01",
        "acquisition_dates": ["2025-09-01"],
        "type": "Land Subsidence (Demo)",
        "location": "San Joaquin Valley, CA",
        "bbox": [-119.558, 36.100, -119.536, 36.118],
        "center": [-119.547, 36.109],
        "sensor": "Simulated ASF HyP3 / NISAR GUNW Fixture",
        "dataset_source": "Local Synthetic Benchmark Generator (UTM Zone 11N)",
        "available_workflow": "Unresolved Ground Subsidence: Synthetic Benchmark Verification Workflow",
        "reference_data_available": True,
        "reference_source": "Synthetic GNSS Interpolated Benchmark (is_synthetic=True)",
        "validation_status": "Demonstration / Synthetic Benchmark Evaluation",
        "description": (
            "Synthetic groundwater extraction subsidence bowl scenario for verifying coherence masking and continuous RMSE/MAE metrics."
        ),
        "domains_involved": ["unresolved"],
        "status": "demo_available",
        "data_readiness": "synthetic_demo",
        "is_synthetic": True,
        "dataset_ids": {
            "unresolved": {
                "displacement": "ds-demo-d4-disp",
                "coherence": "ds-demo-d4-coh",
                "reference_displacement": "ds-demo-d4-ref",
                "exposure_assets": "ds-demo-d4-exp",
            }
        },
        "evidence_summary": (
            "SYNTHETIC DEMONSTRATION FIXTURE: Georeferenced in UTM Zone 11N (EPSG:32611) with simulated LOS deformation rate, "
            "coherence mask, reference GNSS benchmark, and California Aqueduct corridor."
        ),
    },
    {
        "id": "event-california-parkfire-2026",
        "name": "California Park Fire Smoke Penetration (Butte/Tehama — Synthetic Benchmark)",
        "date": "2025-07-28",
        "acquisition_dates": ["2025-07-10", "2025-07-26", "2025-07-28"],
        "type": "Wildfire Disturbance (Demo)",
        "location": "Tehama & Butte Counties, CA",
        "bbox": [-121.760, 39.947, -121.745, 39.959],
        "center": [-121.752, 39.953],
        "sensor": "Simulated NISAR / S1 HV + FIRMS Fixture",
        "dataset_source": "Local Synthetic Benchmark Generator (UTM Zone 10N)",
        "available_workflow": "Domain 2: Synthetic Benchmark Verification Workflow",
        "reference_data_available": True,
        "reference_source": "Synthetic Fire Perimeter Benchmark (is_synthetic=True)",
        "validation_status": "Demonstration / Synthetic Benchmark Evaluation",
        "description": (
            "Synthetic wildfire structural canopy loss scenario for automated testing of thermal point corroboration and perimeter IoU."
        ),
        "domains_involved": ["domain2"],
        "status": "demo_available",
        "data_readiness": "synthetic_demo",
        "is_synthetic": True,
        "dataset_ids": {
            "domain2": {
                "baseline": "ds-demo-d5-base",
                "event": "ds-demo-d5-event",
                "fire_detections": "ds-demo-d5-firms",
                "reference_disturbance": "ds-demo-d5-ref",
                "exposure_assets": "ds-demo-d5-exp",
            }
        },
        "evidence_summary": (
            "SYNTHETIC DEMONSTRATION FIXTURE: Georeferenced in UTM Zone 10N (EPSG:32610) with pre/post HV rasters, "
            "simulated FIRMS thermal points, reference perimeter mask, and WUI road/settlement exposure."
        ),
    },
    {
        "id": "event-hurricane-milton-2026",
        "name": "Hurricane Milton Multi-Hazard Impact (Unstaged External Scenario)",
        "date": "2024-10-10",
        "acquisition_dates": ["2024-10-10"],
        "type": "Cyclone / Hurricane",
        "location": "Gulf Coast, Florida",
        "bbox": [-82.85, 27.35, -81.80, 28.15],
        "center": [-82.32, 27.75],
        "sensor": "External STAC Discovery / User Upload Required",
        "dataset_source": "Microsoft Planetary Computer STAC (Live Remote Query)",
        "available_workflow": "External STAC Granule Discovery & On-Demand Window Retrieval",
        "reference_data_available": False,
        "reference_source": "None staged locally",
        "validation_status": "Unvalidated (No local reference staged)",
        "description": (
            "Documented compound coastal/riverine flood and forest windthrow scenario. No local SAR granules are staged "
            "for this AOI; select this event to test honest empty/external-discovery states, retrieve remote STAC subsets, or upload custom GeoTIFFs."
        ),
        "domains_involved": ["domain1", "domain2"],
        "status": "awaiting_satellite_data",
        "data_readiness": "external_only",
        "is_synthetic": False,
        "dataset_ids": {},
        "evidence_summary": "No local SAR datasets staged. Use External STAC Discovery & Retrieval or manual GeoTIFF upload.",
    },
]


def _bboxes_intersect(a: Optional[list[float]], b: Optional[list[float]]) -> bool:
    if not a or not b or len(a) != 4 or len(b) != 4:
        return False
    # [min_lon, min_lat, max_lon, max_lat]
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def _parse_bbox(bbox_str: Optional[str]) -> Optional[list[float]]:
    if not bbox_str:
        return None
    try:
        parts = [float(x.strip()) for x in bbox_str.split(",")]
        if len(parts) != 4:
            return None
        min_x, min_y, max_x, max_y = min(parts[0], parts[2]), min(parts[1], parts[3]), max(parts[0], parts[2]), max(parts[1], parts[3])
        return [min_x, min_y, max_x, max_y]
    except Exception:
        return None


class ExternalRetrieveRequest(BaseModel):
    collection: str = Field(..., description="Catalog collection (e.g. sentinel-1-rtc, cop-dem-glo-30, alos-fnf-mosaic, nasa-its-live-v2, comet-licsar)")
    granule_id: str = Field(..., min_length=2, max_length=200, description="Remote STAC item ID or granule identifier")
    domain: str = Field(..., description="Target platform domain (domain1..domain5)")
    product_type: Optional[str] = Field(None, description="Target product type (e.g. sar_backscatter, dem, forest_mask, ice_velocity, insar_displacement)")
    asset_key: Optional[str] = Field(None, description="Specific STAC asset key (e.g. vv, vh, hh, data, C)")
    bbox: list[float] = Field(..., min_length=4, max_length=4, description="WGS84 [min_lon, min_lat, max_lon, max_lat] subset window")
    name: Optional[str] = Field(None, max_length=200, description="Optional human-readable dataset name")


def _query_external_stac(
    bbox: Optional[list[float]],
    domain: Optional[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict[str, Any]:
    """Query Microsoft Planetary Computer STAC and open geophysical archives if reachable, else report honestly."""
    if not bbox:
        return {
            "status": "not_queried",
            "source": "Microsoft Planetary Computer STAC / NASA ITS_LIVE / COMET-LiCSAR",
            "message": "Select or draw a geographic bounding box on the map to query external satellite catalogs.",
            "items": [],
        }

    collections = ["sentinel-1-rtc"]
    if domain == "domain1":
        collections = ["sentinel-1-rtc", "cop-dem-glo-30"]
    elif domain == "domain2":
        collections = ["sentinel-1-rtc", "alos-fnf-mosaic"]

    stac_search_url = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
    try:
        feats: list[dict[str, Any]] = []
        for idx, coll_name in enumerate(collections):
            payload: dict[str, Any] = {
                "collections": [coll_name],
                "bbox": bbox,
                "limit": 6 if idx == 0 else 2,
            }
            if (start_date or end_date) and coll_name == "sentinel-1-rtc":
                s_dt = f"{start_date[:10]}T00:00:00Z" if start_date else "2015-01-01T00:00:00Z"
                e_dt = f"{end_date[:10]}T23:59:59Z" if end_date else "2026-12-31T23:59:59Z"
                payload["datetime"] = f"{s_dt}/{e_dt}"

            req = urllib.request.Request(
                stac_search_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "NISAR-DancingWithTheSARs/2.1"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
                feats.extend(raw.get("features") or [])

        items: list[dict[str, Any]] = []
        for f in feats:
            props = f.get("properties") or {}
            coll = f.get("collection") or "sentinel-1-rtc"
            assets = f.get("assets") or {}
            pols = props.get("sar:polarizations") or []
            if coll == "sentinel-1-rtc":
                default_asset = "vh" if (domain in ("domain2", "domain5") and "vh" in assets) else ("hh" if "hh" in assets else "vv")
                rec_ptype = "sar_backscatter"
                sensor_label = f"Copernicus {str(props.get('platform', 'Sentinel-1')).upper()} RTC (C-band SAR)"
            elif coll == "cop-dem-glo-30":
                default_asset = "data"
                rec_ptype = "dem"
                sensor_label = "Copernicus GLO-30 DEM (TanDEM-X)"
            elif coll == "alos-fnf-mosaic":
                default_asset = "C"
                rec_ptype = "forest_mask"
                sensor_label = "JAXA ALOS-2 PALSAR-2 (L-band SAR)"
            else:
                default_asset = next(iter(assets.keys()), "data")
                rec_ptype = "sar_backscatter"
                sensor_label = coll

            items.append({
                "granule_id": f.get("id"),
                "collection": coll,
                "sensor": sensor_label,
                "acquisition_date": (props.get("datetime") or props.get("start_datetime") or "")[:10],
                "platform": props.get("platform", coll),
                "polarizations": pols if pols else ([default_asset.upper()] if default_asset in ("vv", "vh", "hh", "hv") else []),
                "orbit_state": props.get("sat:orbit_state"),
                "relative_orbit": props.get("sat:relative_orbit"),
                "bbox": f.get("bbox"),
                "default_asset_key": default_asset,
                "available_assets": [k for k in assets.keys() if k in ("vv", "vh", "hh", "hv", "data", "C")],
                "recommended_domain": domain or ("domain2" if coll == "alos-fnf-mosaic" else "domain1"),
                "recommended_product_type": rec_ptype,
                "retrieval_status": "discoverable_remote_cog",
                "retrievable": True,
            })

        # Supplement with open NASA ITS_LIVE v2 or COMET-LiCSAR COGs when querying Greenland/Greece
        if (domain in (None, "domain5")) and _bboxes_intersect(bbox, [-55.0, 60.0, -30.0, 82.0]):
            items.append({
                "granule_id": "ITS_LIVE_velocity_120m_RGI05A_2022_v02_v",
                "collection": "nasa-its-live-v2",
                "sensor": "NASA MEaSUREs ITS_LIVE v2 (Landsat/Sentinel-1/2)",
                "acquisition_date": "2022-07-01",
                "platform": "NASA MEaSUREs ITS_LIVE",
                "polarizations": ["Velocity Magnitude (m/year)"],
                "orbit_state": "mosaic",
                "bbox": [-55.0, 60.0, -30.0, 82.0],
                "default_asset_key": "v",
                "available_assets": ["v"],
                "recommended_domain": "domain5",
                "recommended_product_type": "ice_velocity",
                "retrieval_status": "discoverable_remote_cog",
                "retrievable": True,
            })
        if (domain in (None, "domain3")) and _bboxes_intersect(bbox, [21.5, 39.2, 23.0, 40.2]):
            items.append({
                "granule_id": "102A_04971_141314_20210225_20210309",
                "collection": "comet-licsar",
                "sensor": "COMET-LiCSAR Sentinel-1 InSAR (Track 102A)",
                "acquisition_date": "2021-03-09",
                "platform": "Sentinel-1A/1B InSAR",
                "polarizations": ["VV Interferometric Phase (LOS mm)"],
                "orbit_state": "ascending",
                "bbox": [21.5, 39.2, 23.0, 40.2],
                "default_asset_key": "unw",
                "available_assets": ["unw", "cc"],
                "recommended_domain": "domain3",
                "recommended_product_type": "insar_displacement",
                "retrieval_status": "discoverable_remote_cog",
                "retrievable": True,
            })

        return {
            "status": "connected",
            "source": "Microsoft Planetary Computer STAC + NASA ITS_LIVE + COMET-LiCSAR",
            "message": (
                f"Connected to live external satellite catalogs. Found {len(items)} remote granule(s) "
                "intersecting study area. Click 'Retrieve & Register Subset' on any granule to stage an AOI window locally."
            ),
            "items": items,
        }
    except Exception as exc:
        return {
            "status": "offline_or_blocked",
            "source": "Microsoft Planetary Computer STAC / NASA ITS_LIVE / COMET-LiCSAR",
            "message": (
                "Live external catalog query could not reach planetarycomputer.microsoft.com in this runtime environment "
                f"({type(exc).__name__}). No fabricated remote granules are shown. Use locally staged datasets below, "
                "upload a compatible GeoTIFF/GeoJSON, or run `python scripts/acquire_real_sar_data.py` when online."
            ),
            "items": [],
        }


@router.post("/retrieve")
def retrieve_external_granule(req_body: ExternalRetrieveRequest, db: Session = Depends(get_db)):
    """Stream a georeferenced AOI window subset from a discovered remote COG, validate it, and register it locally."""
    if req_body.domain not in ("domain1", "domain2", "domain3", "domain4", "domain5"):
        raise HTTPException(status_code=400, detail=f"Invalid domain '{req_body.domain}'.")

    b = req_body.bbox
    min_lon, min_lat, max_lon, max_lat = min(b[0], b[2]), min(b[1], b[3]), max(b[0], b[2]), max(b[1], b[3])
    # Clamp window span to at most 0.35 degrees around center so on-demand retrieval stays fast and compact
    if (max_lon - min_lon) > 0.35:
        cx = (min_lon + max_lon) / 2.0
        min_lon, max_lon = cx - 0.175, cx + 0.175
    if (max_lat - min_lat) > 0.35:
        cy = (min_lat + max_lat) / 2.0
        min_lat, max_lat = cy - 0.175, cy + 0.175
    subset_bbox = [round(min_lon, 5), round(min_lat, 5), round(max_lon, 5), round(max_lat, 5)]

    coll = req_body.collection.strip()
    gid = req_body.granule_id.strip()
    safe_gid = re.sub(r"[^A-Za-z0-9_-]", "_", gid)[:80]

    # Resolve remote COG URL and metadata
    try:
        if coll in ("sentinel-1-rtc", "cop-dem-glo-30", "alos-fnf-mosaic"):
            item_url = f"https://planetarycomputer.microsoft.com/api/stac/v1/collections/{coll}/items/{urllib.parse.quote(gid)}"
            with urllib.request.urlopen(
                urllib.request.Request(item_url, headers={"User-Agent": "NISAR-DancingWithTheSARs/2.1"}),
                timeout=15,
            ) as resp:
                stac_item = json.loads(resp.read().decode("utf-8"))
            props = stac_item.get("properties") or {}
            assets = stac_item.get("assets") or {}
            if coll == "sentinel-1-rtc":
                default_ak = "vh" if (req_body.domain in ("domain2", "domain5") and "vh" in assets) else ("hh" if "hh" in assets else "vv")
                ak = (req_body.asset_key or default_ak).lower()
                if ak not in assets:
                    ak = next((k for k in ("vv", "vh", "hh", "hv") if k in assets), next(iter(assets.keys())))
                ptype = req_body.product_type or "sar_backscatter"
                pol = ak.upper()
                vscale = "power"
                units = "gamma0 (linear power)"
                sensor = f"Copernicus {str(props.get('platform', 'Sentinel-1A')).upper()} IW GRDH RTC"
                acq_date = (props.get("datetime") or "")[:10] or None
                src_label = f"Copernicus Sentinel-1 RTC / Planetary Computer ({gid})"
            elif coll == "cop-dem-glo-30":
                ak = req_body.asset_key or "data"
                ptype = req_body.product_type or "dem"
                pol = None
                vscale = "other"
                units = "m"
                sensor = "Copernicus GLO-30 (TanDEM-X)"
                acq_date = "2021-01-01"
                src_label = f"Copernicus DEM GLO-30 / Planetary Computer ({gid})"
            else:
                ak = req_body.asset_key or "C"
                ptype = req_body.product_type or "forest_mask"
                pol = "HV"
                vscale = "other"
                units = "class"
                sensor = "JAXA ALOS-2 PALSAR-2"
                acq_date = (props.get("datetime") or props.get("start_datetime") or "2020-01-01")[:10]
                src_label = f"JAXA ALOS-2 PALSAR-2 FNF / Planetary Computer ({gid})"

            raw_href = assets[ak]["href"]
            sign_url = f"https://planetarycomputer.microsoft.com/api/sas/v1/sign?href={urllib.parse.quote(raw_href, safe='')}"
            with urllib.request.urlopen(
                urllib.request.Request(sign_url, headers={"User-Agent": "NISAR-DancingWithTheSARs/2.1"}),
                timeout=15,
            ) as s_resp:
                cog_url = json.loads(s_resp.read().decode("utf-8"))["href"]
        elif coll == "nasa-its-live-v2":
            ak = "v"
            ptype = req_body.product_type or "ice_velocity"
            pol = None
            vscale = "other"
            units = "m/year"
            sensor = "NASA MEaSUREs ITS_LIVE v2"
            acq_date = "2022-07-01"
            src_label = f"NASA MEaSUREs ITS_LIVE v2 AWS Open Data ({gid})"
            cog_url = "https://its-live-data.s3.amazonaws.com/velocity_mosaic/v2/annual/cog/ITS_LIVE_velocity_120m_RGI05A_2022_v02_v.tif"
        elif coll == "comet-licsar":
            ak = (req_body.asset_key or "unw").lower()
            ptype = req_body.product_type or ("insar_coherence" if ak == "cc" else "insar_displacement")
            pol = "VV"
            vscale = "other"
            units = "coherence (0-1)" if ak == "cc" else "mm"
            sensor = "COMET-LiCSAR Sentinel-1 InSAR"
            acq_date = "2021-03-09"
            src_label = f"COMET-LiCSAR Sentinel-1 InSAR Portal ({gid})"
            ext = "cc.tif" if ak == "cc" else "unw.tif"
            cog_url = f"https://gws-access.jasmin.ac.uk/public/nceo_geohazards/LiCSAR_products.public/102/102A_04971_141314/interferograms/20210225_20210309/20210225_20210309.geo.{ext}"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported external collection '{coll}'.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not resolve remote granule '{gid}' from '{coll}': {type(exc).__name__}: {exc}",
        ) from exc

    # Stream georeferenced window subset into data/raw/{domain}/
    root = Path(settings.DATA_ROOT_DIR).resolve()
    rel_path = f"raw/{req_body.domain}/retrieved_{safe_gid}_{ak}.tif"
    dest_path = (root / rel_path).resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with rasterio.open(cog_url) as src:
            bounds_native = transform_bounds(CRS.from_epsg(4326), src.crs, *subset_bbox, densify_pts=21)
            win = from_bounds(*bounds_native, transform=src.transform).round_offsets().round_lengths()
            if win.width < 2 or win.height < 2:
                raise HTTPException(status_code=400, detail="Requested bounding box does not overlap this remote granule.")
            win_h, win_w = int(win.height), int(win.width)
            max_dim = 400
            out_h, out_w = win_h, win_w
            if max(win_h, win_w) > max_dim:
                scale = max_dim / float(max(win_h, win_w))
                out_h = max(16, int(round(win_h * scale)))
                out_w = max(16, int(round(win_w * scale)))

            arr = src.read(
                1,
                window=win,
                out_shape=(out_h, out_w),
                resampling=Resampling.nearest if ptype in ("forest_mask", "reference_water", "reference_disturbance") else Resampling.bilinear,
            )
            from affine import Affine
            win_tr_base = src.window_transform(win)
            win_tr = win_tr_base @ Affine.scale(win_w / out_w, win_h / out_h) if (out_h, out_w) != (win_h, win_w) else win_tr_base

            if coll == "comet-licsar" and ak == "unw":
                arr = arr.astype("float32")
                valid = np.isfinite(arr) & (arr != 0.0)
                ref_zero = float(np.nanmedian(arr[:15, -15:])) if np.any(np.isfinite(arr[:15, -15:])) else 0.0
                arr = np.where(valid, (arr - ref_zero) * (-55.46576 / (4.0 * np.pi)), -9999.0).astype("float32")
            elif coll == "comet-licsar" and ak == "cc":
                arr = np.where(arr > 0, np.clip(arr.astype("float32") / 255.0, 0.0, 1.0), -9999.0).astype("float32")
            elif coll == "alos-fnf-mosaic":
                arr = ((arr == 1) | (arr == 2)).astype("uint8")
                units = "binary (1=forest)"

            prof = src.profile.copy()
            prof.update({
                "driver": "GTiff",
                "height": out_h,
                "width": out_w,
                "count": 1,
                "dtype": str(arr.dtype),
                "transform": win_tr,
                "compress": "lzw",
                "tiled": False,
            })
            if prof["dtype"] == "float32" and prof.get("nodata") is None:
                prof["nodata"] = -9999.0
            with rasterio.open(dest_path, "w", **prof) as dst:
                dst.write(arr, 1)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to stream remote COG window for '{gid}': {type(exc).__name__}: {exc}",
        ) from exc

    ds_service = DatasetService(db)
    ds_name = req_body.name or f"Retrieved {sensor} ({gid[:28]}, {ak.upper()})"
    try:
        registered = ds_service.register_existing(
            DatasetBase(
                name=ds_name[:200],
                domain=req_body.domain,
                description=f"Retrieved on-demand from {coll} for bbox {subset_bbox}. Granule ID: {gid}.",
                product_type=ptype,
                sensor=sensor,
                polarization=pol,
                acquisition_date=acq_date,
                value_scale=vscale,
                units=units,
                source=src_label,
                is_synthetic=False,
            ),
            rel_path,
            custom_id=f"ds-ret-{safe_gid[:40]}-{ak}",
        )
    except DatasetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "retrieved_and_registered",
        "message": f"Successfully streamed and registered '{registered['name']}' ({registered['width']}x{registered['height']} px, {registered['crs']}).",
        "dataset": registered,
    }


@router.get("/events")
def list_curated_events(db: Session = Depends(get_db)):
    """List curated global Earth events, verifying dataset references against the local registry."""
    ds_service = DatasetService(db)
    all_ds = {d["id"]: d for d in ds_service.list_datasets()}
    verified_events = []
    for evt in CURATED_EVENTS:
        copy_evt = dict(evt)
        valid_map: dict[str, dict[str, str]] = {}
        for dom_id, role_map in (evt.get("dataset_ids") or {}).items():
            valid_roles = {role: d_id for role, d_id in role_map.items() if d_id in all_ds and all_ds[d_id].get("file_available")}
            if valid_roles:
                valid_map[dom_id] = valid_roles
        copy_evt["dataset_ids"] = valid_map
        verified_events.append(copy_evt)
    return verified_events


@router.get("/events/{event_id}")
def get_curated_event(event_id: str, db: Session = Depends(get_db)):
    """Get details of a specific curated event."""
    events = list_curated_events(db)
    event = next((e for e in events if e["id"] == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    return event


@router.get("/places")
def search_places(q: Optional[str] = Query(None, description="Search query or coordinates")):
    """Search global EO study regions or parse direct coordinate/bbox strings."""
    if not q or not q.strip():
        return GAZETTEER_PLACES

    query = q.strip()
    # Check if user entered coordinates: "lat, lon" or "min_lon, min_lat, max_lon, max_lat"
    try:
        nums = [float(p.strip()) for p in query.split(",")]
        if len(nums) == 2:
            lat, lon = nums[0], nums[1]
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return [{
                    "id": f"custom-coord-{lat}-{lon}",
                    "name": f"Custom Coordinate ({lat:.4f}°, {lon:.4f}°)",
                    "category": "Custom Study Point",
                    "country": "Custom AOI",
                    "bbox": [round(lon - 0.1, 4), round(lat - 0.1, 4), round(lon + 0.1, 4), round(lat + 0.1, 4)],
                    "center": [lon, lat],
                    "recommended_domains": ["domain1", "domain2", "domain3", "domain4", "domain5"],
                    "notes": "User-entered geographic coordinate with +/- 0.1° bounding box.",
                }]
        elif len(nums) == 4:
            b = [min(nums[0], nums[2]), min(nums[1], nums[3]), max(nums[0], nums[2]), max(nums[1], nums[3])]
            return [{
                "id": "custom-bbox",
                "name": f"Custom Bounding Box [{b[0]:.3f}, {b[1]:.3f}, {b[2]:.3f}, {b[3]:.3f}]",
                "category": "Custom Bounding Box",
                "country": "Custom AOI",
                "bbox": b,
                "center": [round((b[0] + b[2]) / 2, 4), round((b[1] + b[3]) / 2, 4)],
                "recommended_domains": ["domain1", "domain2", "domain3", "domain4", "domain5"],
                "notes": "User-entered WGS84 bounding box.",
            }]
    except ValueError:
        pass

    ql = query.lower()
    matches = [
        p for p in GAZETTEER_PLACES
        if ql in p["name"].lower() or ql in p["country"].lower() or ql in p["category"].lower() or ql in p["notes"].lower()
    ]
    return matches


@router.get("/discover")
def discover_datasets(
    bbox: Optional[str] = Query(None, description="WGS84 min_lon,min_lat,max_lon,max_lat"),
    domain: Optional[str] = Query(None, description="Optional domain filter (domain1..domain5)"),
    start_date: Optional[str] = Query(None, description="Optional start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Optional end date YYYY-MM-DD"),
    include_external: bool = Query(False, description="Whether to query external STAC catalog"),
    db: Session = Depends(get_db),
):
    """Discover local real datasets, local synthetic fixtures, incompatible datasets, and external STAC availability."""
    parsed_bbox = _parse_bbox(bbox)
    ds_service = DatasetService(db)
    all_datasets = ds_service.list_datasets()

    local_real: list[dict[str, Any]] = []
    local_synthetic: list[dict[str, Any]] = []
    unavailable_or_incompatible: list[dict[str, Any]] = []

    for d in all_datasets:
        # Check spatial intersection if bbox filter was supplied
        d_bbox = d.get("bbox_wgs84")
        if parsed_bbox is not None:
            if not d_bbox or not _bboxes_intersect(parsed_bbox, d_bbox):
                continue

        # Optional date range filtering for primary observations
        acq = d.get("acquisition_date")
        if start_date and acq and not d.get("is_reference_data") and acq < start_date[:10]:
            continue
        if end_date and acq and not d.get("is_reference_data") and acq > end_date[:10]:
            continue

        # Check domain compatibility and file readiness
        domain_match = (domain is None) or (d.get("domain") == domain)
        file_ok = bool(d.get("file_available")) and d.get("processing_readiness") == "ready"

        if not file_ok:
            item = dict(d)
            item["availability_category"] = "unavailable_file"
            item["compatibility_note"] = "File is missing from local storage or lacks georeferencing."
            unavailable_or_incompatible.append(item)
        elif not domain_match:
            item = dict(d)
            item["availability_category"] = "incompatible_domain"
            item["compatibility_note"] = f"Registered for {d.get('domain')}, not {domain}."
            unavailable_or_incompatible.append(item)
        elif d.get("is_synthetic"):
            item = dict(d)
            item["availability_category"] = "local_synthetic_fixture"
            item["compatibility_note"] = "Synthetic demonstration/test fixture (not a real satellite observation)."
            local_synthetic.append(item)
        else:
            item = dict(d)
            item["availability_category"] = "local_verified_real"
            item["compatibility_note"] = "Verified real Earth observation / ancillary dataset ready for processing."
            local_real.append(item)

    external_info = (
        _query_external_stac(parsed_bbox, domain, start_date=start_date, end_date=end_date)
        if include_external
        else {
            "status": "not_queried",
            "source": "Microsoft Planetary Computer STAC / NASA ITS_LIVE / COMET-LiCSAR",
            "message": "Click 'Check External Satellite Catalog (STAC)' to query remote archives for this bounding box.",
            "items": [],
        }
    )

    return {
        "query": {
            "bbox_wgs84": parsed_bbox,
            "domain": domain,
            "start_date": start_date,
            "end_date": end_date,
            "include_external": include_external,
        },
        "summary": {
            "local_real_count": len(local_real),
            "local_synthetic_count": len(local_synthetic),
            "unavailable_or_incompatible_count": len(unavailable_or_incompatible),
            "external_discoverable_count": len(external_info.get("items") or []),
        },
        "local_real_datasets": local_real,
        "local_synthetic_datasets": local_synthetic,
        "unavailable_or_incompatible": unavailable_or_incompatible,
        "external_discovery": external_info,
    }


@router.get("/runs")
def list_all_runs(domain: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """List persisted analysis runs across all domains or filtered by domain."""
    service = ProcessingService(db)
    return service.list_runs(domain=domain)


@router.get("/runs/{run_id}")
def get_run_detail(run_id: str, db: Session = Depends(get_db)):
    """Reopen a previous analysis run and retrieve its complete StandardDomainResponse."""
    service = ProcessingService(db)
    result = service.get_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run result not found.")
    return result


@router.get("/runs/{run_id}/export")
def export_run_report(
    run_id: str,
    format: str = Query("json", description="Export format: 'json' or 'html'"),
    db: Session = Depends(get_db),
):
    """Export a comprehensive 15-section scientific investigation report in JSON or printable HTML."""
    service = ProcessingService(db)
    result = service.get_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run result not found.")

    prov = result.get("provenance") or {}
    inputs_prov = prov.get("inputs") or {}
    layers = result.get("layers") or []
    validation = result.get("validation") or {}
    exposure = result.get("exposure") or {}
    study_area = result.get("study_area") or prov.get("study_area") or {}

    before_layer = next((l for l in layers if l.get("key") in ("baseline_preview", "terminus_baseline")), None)
    after_layer = next(
        (l for l in layers if l.get("key") in ("event_preview", "velocity_preview", "displacement_preview", "terminus_event")),
        None,
    )
    change_layer = next(
        (l for l in layers if l.get("key") in ("flood_overlay", "disturbance_overlay", "burn_overlay", "change_overlay", "change_preview")),
        None,
    )

    report_payload = {
        # Backwards-compatible keys expected by existing tests
        "report_title": f"Scientific Investigation Report: {result.get('analysis', 'Domain Run')}",
        "run_id": run_id,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "investigation_summary": result.get("summary_metrics"),
        "four_level_explanation": result.get("explanation"),
        "caveats_and_uncertainty": result.get("caveats"),
        "warnings": result.get("warnings"),
        "deliverable_layers": layers,
        "complete_provenance": prov,
        # Complete 15-point structured specification
        "1_analysis_id": run_id,
        "2_study_area": study_area,
        "3_selected_domain": {
            "domain_id": result.get("domain"),
            "analysis_name": result.get("analysis"),
            "is_synthetic_input": result.get("is_synthetic_input", False),
        },
        "4_dataset_sources_and_identifiers": inputs_prov,
        "5_acquisition_dates": result.get("observation_dates") or [],
        "6_processing_method": {
            "algorithm": prov.get("algorithm"),
            "algorithm_version": prov.get("algorithm_version", "2.0.0"),
            "software_version": prov.get("software_version", "NISAR-DancingWithTheSARs/2.0.0"),
            "method_summary": (result.get("explanation") or {}).get("level2_method"),
        },
        "7_configuration_parameters": prov.get("parameters") or {},
        "8_before_after_visualization": {
            "before_layer": before_layer,
            "after_layer": after_layer,
        },
        "9_detected_change_map": change_layer,
        "10_quantitative_measurements": result.get("summary_metrics") or [],
        "11_validation_results": validation,
        "12_error_and_uncertainty_information": {
            "level4_uncertainty": (result.get("explanation") or {}).get("level4_uncertainty"),
            "error_explorer": validation.get("error_explorer"),
            "warnings": result.get("warnings") or [],
        },
        "13_potential_exposure_results": exposure,
        "14_known_limitations": result.get("caveats") or [],
        "15_processing_provenance": prov,
    }

    if format.lower() == "html":
        html_doc = _render_html_report(report_payload, result)
        return HTMLResponse(content=html_doc, status_code=200)

    return report_payload


def _render_html_report(rep: dict[str, Any], result: dict[str, Any]) -> str:
    """Render a self-contained, printable HTML scientific report."""
    esc = html.escape
    title = esc(str(rep.get("report_title", "NISAR Investigation Report")))
    run_id = esc(str(rep.get("run_id", "")))
    domain = esc(str(result.get("domain", "")))
    is_synth = bool(result.get("is_synthetic_input"))
    study_area = rep.get("2_study_area") or {}
    bbox_str = esc(str(study_area.get("bbox_wgs84") or "N/A"))
    crs_str = esc(str(study_area.get("native_crs") or "N/A"))
    dates_str = esc(", ".join(rep.get("5_acquisition_dates") or ["Unspecified"]))

    metrics_rows = "".join(
        f"<tr><td><strong>{esc(str(m.get('label')))}</strong></td>"
        f"<td>{esc(str(m.get('value')))} {esc(str(m.get('unit') or ''))}</td>"
        f"<td>{esc(str(m.get('description') or ''))}</td></tr>"
        for m in (rep.get("10_quantitative_measurements") or [])
    )

    inputs_rows = "".join(
        f"<tr><td><code>{esc(str(role))}</code></td>"
        f"<td>{esc(str(info.get('name')))} (<code>{esc(str(info.get('dataset_id')))}</code>)</td>"
        f"<td>{esc(str(info.get('product_type')))} | {esc(str(info.get('sensor') or 'N/A'))} | {esc(str(info.get('polarization') or 'N/A'))}</td>"
        f"<td>{esc(str(info.get('acquisition_date') or 'N/A'))}</td>"
        f"<td>{'SYNTHETIC FIXTURE' if info.get('is_synthetic') else 'REAL OBSERVATION'}</td></tr>"
        for role, info in (rep.get("4_dataset_sources_and_identifiers") or {}).items()
    )

    val = rep.get("11_validation_results") or {}
    val_metrics_rows = "".join(
        f"<tr><td>{esc(str(m.get('label')))}</td><td>{esc(str(m.get('value')))} {esc(str(m.get('unit') or ''))}</td><td>{esc(str(m.get('description') or ''))}</td></tr>"
        for m in (val.get("metrics") or [])
    )

    exp = rep.get("13_potential_exposure_results") or {}
    exp_rows = "".join(
        f"<tr><td>{esc(str(a.get('asset_name')))}</td><td>{esc(str(a.get('asset_class')))}</td>"
        f"<td>{'EXPOSED' if a.get('exposed') else 'Not Exposed'}</td>"
        f"<td>{esc(str(a.get('exposure_measurement')))} {esc(str(a.get('unit')))}</td></tr>"
        for a in (exp.get("asset_breakdown") or [])
    )

    expl = result.get("explanation") or {}
    caveats_li = "".join(f"<li>{esc(str(c))}</li>" for c in (rep.get("14_known_limitations") or []))
    params_str = esc(json.dumps(rep.get("7_configuration_parameters") or {}, indent=2))

    synth_banner = (
        '<div style="background:#7c2d12;color:#fed7aa;padding:12px 16px;border-radius:6px;margin-bottom:16px;font-weight:bold;">'
        '⚠️ SYNTHETIC DATA NOTICE: One or more input datasets in this run are synthetic demonstration fixtures. '
        'Results verify algorithm behavior and are NOT real Earth observations.</div>'
        if is_synth
        else '<div style="background:#064e3b;color:#a7f3d0;padding:12px 16px;border-radius:6px;margin-bottom:16px;font-weight:bold;">'
        '✓ VERIFIED EARTH OBSERVATION DATA: All primary inputs in this run are non-synthetic satellite/ancillary products.</div>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #0f172a; max-width: 980px; margin: 24px auto; padding: 0 20px; line-height: 1.5; }}
    h1 {{ color: #0369a1; margin-bottom: 4px; }}
    h2 {{ color: #1e293b; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin-top: 24px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; }}
    th {{ background: #f1f5f9; }}
    pre {{ background: #f8fafc; border: 1px solid #cbd5e1; padding: 10px; border-radius: 6px; overflow-x: auto; font-size: 13px; }}
    .meta-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; background: #f8fafc; padding: 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; }}
    @media print {{ .no-print {{ display: none; }} }}
  </style>
</head>
<body>
  <div class="no-print" style="text-align:right;margin-bottom:12px;">
    <button onclick="window.print()" style="padding:8px 14px;background:#0284c7;color:#fff;border:none;border-radius:4px;cursor:pointer;">🖨️ Print / Save as PDF</button>
  </div>
  <h1>{title}</h1>
  <p style="color:#475569;margin-top:0;">NISAR — Dancing with the SARs Earth Observation Platform</p>
  {synth_banner}
  <div class="meta-grid">
    <div><strong>1. Analysis Run ID:</strong> <code>{run_id}</code></div>
    <div><strong>3. Selected Domain:</strong> <code>{domain}</code></div>
    <div><strong>2. Study Area (WGS84):</strong> <code>{bbox_str}</code></div>
    <div><strong>Native CRS:</strong> <code>{crs_str}</code></div>
    <div><strong>5. Acquisition Dates:</strong> {dates_str}</div>
    <div><strong>6. Software Version:</strong> <code>{esc(str((rep.get('6_processing_method') or {{}}).get('software_version')))}</code></div>
  </div>

  <h2>4. Input Datasets & Provenance</h2>
  <table>
    <thead><tr><th>Role</th><th>Dataset Name & ID</th><th>Product / Sensor / Pol</th><th>Acquisition Date</th><th>Data Type</th></tr></thead>
    <tbody>{inputs_rows}</tbody>
  </table>

  <h2>7. Processing Method & Configuration Parameters</h2>
  <p>{esc(str(expl.get('level2_method') or ''))}</p>
  <pre>{params_str}</pre>

  <h2>10. Quantitative Measurements</h2>
  <table>
    <thead><tr><th>Metric</th><th>Measurement</th><th>Scientific Basis</th></tr></thead>
    <tbody>{metrics_rows}</tbody>
  </table>

  <h2>11 & 12. Independent Reference Validation & Error Explorer</h2>
  <p><strong>Validation Status:</strong> <code>{esc(str(val.get('status', 'not_validated')))}</code> ({esc(str(val.get('validation_category', 'not_validated')))}) — {esc(str(val.get('notes', '')))}</p>
  {f'<table><thead><tr><th>Validation Metric</th><th>Value</th><th>Description</th></tr></thead><tbody>{val_metrics_rows}</tbody></table>' if val_metrics_rows else ''}

  <h2>13. Potential Asset Exposure Analysis</h2>
  <p><strong>Exposure Status:</strong> <code>{esc(str(exp.get('status', 'not_evaluated')))}</code> — {esc(str(exp.get('notes', '')))}</p>
  {f'<table><thead><tr><th>Asset Name</th><th>Class</th><th>Intersection Status</th><th>Measured Exposure</th></tr></thead><tbody>{exp_rows}</tbody></table>' if exp_rows else ''}

  <h2>Four-Tier Scientific Explainability & Uncertainty</h2>
  <p><strong>Level 1 (Visual Observation):</strong> {esc(str(expl.get('level1_visual') or ''))}</p>
  <p><strong>Level 2 (Methodology):</strong> {esc(str(expl.get('level2_method') or ''))}</p>
  <p><strong>Level 3 (Physical Evidence):</strong> {esc(str(expl.get('level3_evidence') or ''))}</p>
  <p><strong>Level 4 (Uncertainty & Alternative Explanations):</strong> {esc(str(expl.get('level4_uncertainty') or ''))}</p>

  <h2>14. Known Scientific Limitations & Caveats</h2>
  <ul>{caveats_li}</ul>
</body>
</html>"""
