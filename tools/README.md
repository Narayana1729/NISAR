# Tools

CLI scripts for rendering and exporting CesiumJS and Map Tiles imagery.

## sat-ortho.mjs

Stitches satellite tiles from Google Map Tiles API into an orthographic satellite image centered on given coordinates.

```sh
node tools/sat-ortho.mjs --lat 30.266476 --lon -97.73719 --zoom 20 --size 2048
```

## cesium-render.mjs / cesium-render.html

Renders a CesiumJS 3D view to an image using headless Chromium with Google Photorealistic 3D Tiles and terrain sampling.

```sh
node tools/cesium-render.mjs --lookat-lat 30.266476 --lookat-lon -97.73719 --heading 180 --pitch -30 --height 250
```
