# GIS Software Integration

Native GIS integration, reviewed 2026-10-01. All examples are illustrative: these
applications/licenses were not installed or executed. Run them in the GIS vendor's
Python environment, check the installed version and inspect tool help before use.
QGIS's `latest` cookbook currently redirects to 3.44, so use explicit 4.2 material
when targeting its Qt6 runtime.

## QGIS / PyQGIS

### Running Python Scripts in QGIS

```python
# Processing framework script
from qgis.core import (QgsProject, QgsVectorLayer, QgsRasterLayer,
                       QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer)

# Load layers
vector_layer = QgsVectorLayer("path/to/shapefile.shp", "layer_name", "ogr")
raster_layer = QgsRasterLayer("path/to/raster.tif", "raster_name", "gdal")

# Add to project
QgsProject.instance().addMapLayer(vector_layer)
QgsProject.instance().addMapLayer(raster_layer)

# Access features
for feature in vector_layer.getFeatures():
    geom = feature.geometry()
    attrs = feature.attributes()
```

### Processing algorithms

Run inside an initialized QGIS environment with Processing registered. Inspect the
provider's current parameters before assembling a workflow:

```python
import processing
processing.algorithmHelp('native:buffer')
result = processing.run('native:buffer', {
    'INPUT': metric_vector_layer, 'DISTANCE': 100, 'SEGMENTS': 8,
    'END_CAP_STYLE': 0, 'JOIN_STYLE': 0, 'MITER_LIMIT': 2,
    'DISSOLVE': False, 'OUTPUT': 'TEMPORARY_OUTPUT',
})
buffer_layer = result['OUTPUT']
```

For a custom `QgsProcessingAlgorithm`, implement parameter registration,
`processAlgorithm` and `createInstance`, and return the actual produced destination.
A placeholder `destination` variable is not an NDVI implementation. Raster calculations
must use explicit bands, scale/offset, masks and a defined output grid as in the local
raster helper; wire those through registered parameters rather than guessing Sentinel
band positions. Validate `QgsVectorLayer.isValid()`/`QgsRasterLayer.isValid()` before
adding or processing a layer.

### Plugin Development

```python
# __init__.py
def classFactory(iface):
    from .my_plugin import MyPlugin
    return MyPlugin(iface)

# my_plugin.py
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtGui import QAction  # QGIS 4 / Qt6
from qgis.core import QgsProject

class MyPlugin:
    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        self.action = QAction("My Plugin", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("My Plugin", self.action)

    def run(self):
        # Plugin logic here
        pass

    def unload(self):
        self.iface.removePluginMenu("My Plugin", self.action)
```

## ArcGIS / ArcPy

### Basic ArcPy Operations

```python
import arcpy

# Set workspace
arcpy.env.workspace = "C:/data"

# Set output overwrite
arcpy.env.overwriteOutput = True

# Set scratch workspace
arcpy.env.scratchWorkspace = "C:/data/scratch"

# List features
feature_classes = arcpy.ListFeatureClasses()
rasters = arcpy.ListRasters()
```

### Geoprocessing Workflows

```python
import arcpy
from arcpy.sa import *

# Check out Spatial Analyst extension
arcpy.CheckOutExtension("Spatial")

# Set environment
arcpy.env.workspace = "C:/data"
arcpy.env.cellSize = 10
arcpy.env.extent = "study_area"

# Slope analysis
out_slope = Slope("dem.tif")
out_slope.save("slope.tif")

# Aspect
out_aspect = Aspect("dem.tif")
out_aspect.save("aspect.tif")

# Hillshade
out_hillshade = Hillshade("dem.tif", azimuth=315, altitude=45)
out_hillshade.save("hillshade.tif")

# Viewshed analysis
out_viewshed = Viewshed("dem.tif", "observer_points.shp")  # observer fields follow tool schema
out_viewshed.save("viewshed.tif")

# Cost distance
cost_raster = DistanceAccumulation("source.shp", in_cost_raster="cost.tif")
cost_raster.save("cost_distance.tif")

# Hydrology: Flow direction
flow_dir = FlowDirection("dem.tif")
flow_dir.save("flowdir.tif")

# Flow accumulation
flow_acc = FlowAccumulation(flow_dir)
flow_acc.save("flowacc.tif")

# Stream delineation
stream = Con(flow_acc > 1000, 1)
stream_raster = StreamOrder(stream, flow_dir)
```

### Vector Analysis

```python
# Buffer analysis
arcpy.Buffer_analysis("roads.shp", "roads_buffer.shp", "100 meters")

# Spatial join
arcpy.SpatialJoin_analysis("points.shp", "zones.shp", "points_joined.shp",
                           join_operation="JOIN_ONE_TO_ONE",
                           match_option="HAVE_THEIR_CENTER_IN")

# Dissolve
arcpy.Dissolve_management("parcels.shp", "parcels_dissolved.shp",
                          dissolve_field="OWNER_ID")

# Intersect
arcpy.Intersect_analysis(["layer1.shp", "layer2.shp"], "intersection.shp")

# Clip
arcpy.Clip_analysis("input.shp", "clip_boundary.shp", "output.shp")

# Select by location
arcpy.SelectLayerByLocation_management("points_layer", "HAVE_THEIR_CENTER_IN",
                                      "polygon_layer")

# Feature to raster
arcpy.FeatureToRaster_conversion("landuse.shp", "LU_CODE", "landuse.tif", 10)
```

### ArcGIS Pro Notebooks

```python
# ArcGIS Pro Jupyter Notebook
import arcpy
import pandas as pd
import matplotlib.pyplot as plt

# Use current project's map
aprx = arcpy.mp.ArcGISProject("CURRENT")
m = aprx.listMaps()[0]

# Get layer
layer = m.listLayers("Parcels")[0]

# Read the local ArcPy feature layer through a feature-class source path.
from arcgis.features import GeoAccessor, GeoSeriesAccessor
sdf = pd.DataFrame.spatial.from_featureclass(layer.dataSource)

# Plot
sdf.plot(column='VALUE', cmap='YlOrRd', legend=True)
plt.show()

# Geocode addresses
locator = "C:/data/locators/composite.locator"
results = arcpy.geocoding.GeocodeAddresses(
    "addresses.csv", locator, "Address Address",
    "geocoded_results.gdb/addresses"
)
```

## GRASS GIS

### Python API for GRASS

```python
import grass.script as gscript
import grass.script.array as garray

# Run within an initialized GRASS mapset (for example launch through
# `grass /path/to/location/mapset --exec python workflow.py`). Merely writing
# GISDBASE/LOCATION_NAME/MAPSET with g.gisenv does not initialize a session.

# Import raster
gscript.run_command('r.in.gdal', input='elevation.tif', output='elevation')

# Import vector
gscript.run_command('v.in.ogr', input='roads.shp', output='roads')

# Get raster info
info = gscript.raster_info('elevation')
print(info)

# Match computational region/resolution to the imported DEM.
gscript.run_command('g.region', raster='elevation', align='elevation')
# Slope analysis
gscript.run_command('r.slope.aspect', elevation='elevation',
                    slope='slope', aspect='aspect')

# Buffer
gscript.run_command('v.buffer', input='roads', output='roads_buffer',
                    distance=100)

# Overlay
gscript.run_command('v.overlay', ainput='zones', binput='roads',
                    operator='and', output='zones_roads')

# Calculate statistics
stats = gscript.parse_command('r.univar', map='elevation', flags='g')
```

## SAGA GIS

### Using SAGA via command line

Tool IDs/parameters belong to a specific SAGA release. For the reviewed 9.12.1
slope/aspect/curvature tool, the library is `ta_morphometry`, ID `0`:

```python
import subprocess
subprocess.run(['saga_cmd', 'ta_morphometry', '0',
                '-ELEVATION', 'dem.sgrd', '-SLOPE', 'slope.sgrd',
                '-ASPECT', 'aspect.sgrd', '-UNIT_SLOPE', '1',
                '-UNIT_ASPECT', '1'], check=True)
```

Use `saga_cmd ta_morphometry 0 -h` and the matching version's tool documentation to
confirm inputs/output units and method. For grid calculus/channel networks, discover
the installed library/tool help instead of invented names such as `GridCalculator`
or `ChannelNetworkAndDrainageBasins`. Parameter interfaces can differ across versions.
Check exit status and output metadata; process success does not prove scientific validity.

## Cross-Platform Workflows

### Export QGIS to ArcGIS

```python
import geopandas as gpd

# Read data processed in QGIS
gdf = gpd.read_file('qgis_output.geojson')

# Ensure CRS
gdf = gdf.to_crs('EPSG:32633')

# Export for ArcGIS as GeoPackage (not File Geodatabase)
gdf.to_file('arcgis_input.gpkg', driver='GPKG')
# ArcGIS can read GPKG directly

# Or export to shapefile
gdf.to_file('arcgis_input.shp')
```

### Batch Processing

```python
import geopandas as gpd
from pathlib import Path

# Process multiple files
input_dir = Path('input')
output_dir = Path('output')
output_dir.mkdir(parents=True, exist_ok=True)

for shp in input_dir.glob('*.shp'):
    gdf = gpd.read_file(shp)

    if gdf.crs is None:
        raise ValueError('Source CRS is unknown')
    gdf = gdf.to_crs(gdf.estimate_utm_crs())
    # Process in verified metre units
    gdf['area'] = gdf.geometry.area
    gdf.geometry = gdf.geometry.buffer(100)  # one active geometry for these formats

    # Export for various platforms
    basename = shp.stem
    gdf.to_file(output_dir / f'{basename}_qgis.geojson')
    gdf.to_file(output_dir / f'{basename}_arcgis.shp')
```

For more GIS-specific examples, see [code-examples.md](code-examples.md).

Sources: [QGIS4.2](https://docs.qgis.org/4.2/en/docs/pyqgis_developer_cookbook/plugins/plugins.html), [ArcGIS viewshed](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/spatial-analyst/viewshed.html), [distance accumulation](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/spatial-analyst/distance-accumulation.html), [GRASS](https://grass.osgeo.org/grass-stable/manuals/r.watershed.html), [SAGA9.12 tool0](https://saga-gis.sourceforge.io/saga_tool_doc/9.12.1/ta_morphometry_0.html).
