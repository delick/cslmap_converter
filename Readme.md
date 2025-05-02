# CSL Map converter

This converter converts `*.cslmap` file format exported from ![csl map view](https://steamcommunity.com/sharedfiles/filedetails/?id=845665815) plugins to a GeoJSON file, so that the user can custimise the map in GIS software (QGIS, ArcGIS, etc).

The file format for cslmap is XML.

## Features

This script can convert cslmap to common GeoJSON file. Supported Layers include:

- Buildings (Polygon): Building boundary polygons.
- districts (Point): User defined administrative districts.
- nodes (Points): All nodes in Cities Skylines.
- parks: parks and park life components.
- segments (Line): Includes segments of roads, tracks, transport lines etc.
- transports (Line): Transportation lines including buses, trams, metro lines, train lines, etc.

## Usage

1. Export `.cslmap` in Cities Skylines following the instructions.
2. Find your `.cslmap` file in game folder.
3. Edit your `config.ini` file. Currently only 2 configs:
   - `xml_file`: Path to your `.cslmap` file
   - `enable_3d`: Whether to enable 3D coordinates in that xml.
4. Run the python script:
   ```bash
   python cslmap2geojson.py
   ```
   You'll see a bunch of geojson files generated.
5. Style your map in GIS software. Consider using QGIS on Linux/Mac/Windows, or
   try other GIS software that supports GeoJSON (e.g. ArcGIS).