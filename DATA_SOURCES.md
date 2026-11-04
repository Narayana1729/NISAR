# Data Sources & Attribution

The platform code is [MIT](LICENSE)-licensed. **The MIT grant covers source code only — it does NOT extend to third-party data or visual assets.** Every third-party source maintains its own license and terms.

Attribution is displayed in-app on the bottom-left credit line (`#cesium-credits`) and within the **Data Attribution** dialog (`src/data/dataCredits.js`). Keep all attributions intact.

---

## Active Data Sources

| Source | Used for | License / Terms | Attribution |
|---|---|---|---|
| **Google Map Tiles API** | Photorealistic 3D Tiles basemap and place search | Google Maps Platform ToS (proprietary, BYOK) | "Google" / "Google Maps" logo — displayed on globe |
| **Esri World Imagery** | Keyless satellite imagery basemap | Esri Master Agreement (public tile service) | "Powered by Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community" |
| **USGS** | Global earthquake event catalog | U.S. Public Domain | "Data courtesy of the U.S. Geological Survey" |
| **NASA FIRMS** | Near-real-time active fire hotspots (VIIRS/MODIS) | NASA Open Data Policy (LANCE/FIRMS) | "NASA FIRMS / LANCE" |
| **Forest Intelligence (Sentinel-2 / Landsat)** | Multi-spectral surface reflectance and canopy analysis | Copernicus Open Access / USGS Landsat / INPE PRODES | "Copernicus Sentinel-2, Landsat (USGS/NASA), INPE PRODES, NASA FIRMS" |
| **Re:Earth Terrain** (Mapterhorn) | Quantized-mesh digital elevation model and heights | CC BY 4.0; Geoid: EGM96 / EGM2008 (NGA, Public Domain) | "Terrain: Re:Earth Terrain / Mapterhorn (CC BY 4.0) / EGM96 (NGA)" |
| **OpenStreetMap (Overpass / Nominatim)** | Vector geometry search and annotation outlines | ODbL 1.0 | "© OpenStreetMap contributors" |
| **TeleGeography** | Submarine telecommunication cable network | CC BY-NC-SA 4.0 (NonCommercial) | "TeleGeography Submarine Cable Map" |
| **Global Dam Watch** | Worldwide dam infrastructure locations | Open Database License / Research use | "Global Dam Watch / GOODD / GRanD" |
| **Natural Earth** | Marine labels, region boundaries, bathymetry | Public Domain | "Made with Natural Earth" |

---

## NonCommercial License Carve-Out

* **TeleGeography Submarine Cables**: Licensed under **CC BY-NC-SA 4.0 (NonCommercial)**. Commercial deployments must omit or replace `src/data/local_data/telegeography_submarine_cables/` or obtain a commercial license from TeleGeography.
