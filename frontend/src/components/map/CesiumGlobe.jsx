import React, { useEffect, useRef, useState } from 'react';
import * as Cesium from 'cesium';

/**
 * CesiumGlobe — React-wrapped photorealistic 3D Globe component
 * Derived from NASA1 (God's Eye View) mapStartup.js and main.js.
 * Supports keyless OpenStreetMap / Esri fallback and smooth camera flyTo.
 */
export default function CesiumGlobe({
  bbox = null,
  center = null,
  events = [],
  selectedEventId = null,
  onSelectEvent = null,
  rasterOverlays = [],
  height = '100%',
  showControls = true,
}) {
  const containerRef = useRef(null);
  const viewerRef = useRef(null);
  const overlaysLayersRef = useRef([]);
  const [isLoaded, setIsLoaded] = useState(false);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    if (!containerRef.current) return;

    let viewerInstance = null;
    try {
      // Create minimal chrome viewer
      viewerInstance = new Cesium.Viewer(containerRef.current, {
        timeline: false,
        animation: false,
        baseLayerPicker: false,
        geocoder: false,
        homeButton: false,
        sceneModePicker: false,
        navigationHelpButton: false,
        fullscreenButton: false,
        vrButton: false,
        selectionIndicator: false,
        infoBox: false,
        baseLayer: false,
        msaaSamples: 4,
        contextOptions: {
          webgl: {
            preserveDrawingBuffer: true,
          },
        },
      });

      // Target 60 fps cap
      viewerInstance.targetFrameRate = 60;

      // Soften atmosphere
      if (viewerInstance.scene.skyAtmosphere) {
        viewerInstance.scene.skyAtmosphere.show = true;
        viewerInstance.scene.skyAtmosphere.atmosphereLightIntensity = 18;
      }

      // Add high-resolution keyless imagery provider (Esri World Imagery or OSM)
      const imageryProvider = new Cesium.UrlTemplateImageryProvider({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        maximumLevel: 19,
        credit: 'Esri, Maxar, Earthstar Geographics, and the GIS User Community',
      });
      viewerInstance.imageryLayers.addImageryProvider(imageryProvider);
      viewerInstance.scene.globe.show = true;

      // Store ref
      viewerRef.current = viewerInstance;
      setIsLoaded(true);
    } catch (err) {
      console.error('[CesiumGlobe] Initialization error:', err);
      setLoadError(err.message || 'Cesium WebGL initialization failed');
    }

    return () => {
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        try {
          viewerRef.current.destroy();
        } catch (e) {
          console.warn('[CesiumGlobe] Cleanup warning:', e);
        }
        viewerRef.current = null;
      }
    };
  }, []);

  // Handle bounding box / center camera flights
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;

    if (bbox && bbox.length === 4) {
      // bbox: [minLon, minLat, maxLon, maxLat]
      const rectangle = Cesium.Rectangle.fromDegrees(bbox[0], bbox[1], bbox[2], bbox[3]);
      viewer.camera.flyTo({
        destination: rectangle,
        duration: 1.8,
      });
    } else if (center && center.length >= 2) {
      // center: [lon, lat, height?]
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(center[0], center[1], center[2] || 150000),
        duration: 1.8,
      });
    }
  }, [bbox, center]);

  // Render event markers on the 3D globe
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;

    viewer.entities.removeAll();

    if (Array.isArray(events) && events.length > 0) {
      events.forEach((evt) => {
        if (!evt.center || evt.center.length < 2) return;
        const [lon, lat] = evt.center;
        const isSelected = selectedEventId === evt.id;

        viewer.entities.add({
          id: evt.id,
          name: evt.name,
          position: Cesium.Cartesian3.fromDegrees(lon, lat, 100),
          point: {
            pixelSize: isSelected ? 16 : 10,
            color: isSelected
              ? Cesium.Color.fromCssColorString('#00d4ff')
              : Cesium.Color.fromCssColorString('#f59e0b'),
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
          },
          label: {
            text: evt.name,
            font: '10px JetBrains Mono, monospace',
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            pixelOffset: new Cesium.Cartesian2(0, -12),
            showBackground: true,
            backgroundColor: Cesium.Color.fromCssColorString('rgba(12, 12, 20, 0.8)'),
          },
        });
      });
    }
  }, [events, selectedEventId]);

  // Synchronize georeferenced raster overlays on the 3D terrain
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;

    // Clean up previously attached raster overlay imagery layers
    overlaysLayersRef.current.forEach((layer) => {
      try {
        if (!viewer.isDestroyed() && viewer.imageryLayers.contains(layer)) {
          viewer.imageryLayers.remove(layer, true);
        }
      } catch (err) {
        // ignore layer disposal errors
      }
    });
    overlaysLayersRef.current = [];

    if (!Array.isArray(rasterOverlays) || rasterOverlays.length === 0) return;

    // Add each active raster overlay as a georeferenced SingleTileImageryProvider
    rasterOverlays.forEach((ov) => {
      if (ov.visible === false) return;
      const b = ov.bounds || ov.bounds_wgs84;
      if (!ov.url || !b || b.length !== 4) return;
      try {
        const rectangle = Cesium.Rectangle.fromDegrees(b[0], b[1], b[2], b[3]);
        const provider = new Cesium.SingleTileImageryProvider({
          url: ov.url,
          rectangle: rectangle,
        });
        const layer = viewer.imageryLayers.addImageryProvider(provider);
        layer.alpha = ov.opacity ?? 0.85;
        overlaysLayersRef.current.push(layer);
      } catch (err) {
        console.warn('Failed to drape raster overlay onto Cesium globe:', err);
      }
    });
  }, [rasterOverlays]);

  return (
    <div className="relative w-full overflow-hidden" style={{ height }}>
      <div ref={containerRef} id="cesiumContainer" className="w-full h-full absolute inset-0" />

      {loadError && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/80 text-rose-400 p-4 font-mono text-sm z-30">
          <div>
            <strong>3D Globe Initialization Error:</strong>
            <p className="mt-1 text-xs text-gray-300">{loadError}</p>
          </div>
        </div>
      )}

      {!isLoaded && !loadError && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/60 text-cyan-400 font-mono text-xs z-20">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
            <span>INITIALIZING 3D GLOBE ENGINE...</span>
          </div>
        </div>
      )}
    </div>
  );
}
