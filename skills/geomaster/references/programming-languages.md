# Multi-Language Geospatial Programming

Geospatial programming across R, Julia, JavaScript, C++, Java, Go, Rust and Python.
Reviewed 2026-10-01 against upstream sources listed below. These are illustrative
language-specific fragments, not compiled/executed cross-language coverage. Python
runtime coverage is recorded separately in [review.md](review.md).

## R Geospatial

### sf (Simple Features)

```r
library(sf)
library(dplyr)
library(ggplot2)

# Read spatial data
roads <- st_read("roads.shp")
zones <- st_read("zones.geojson")

# Basic operations
st_crs(roads)  # Check CRS
roads_utm <- st_transform(roads, 32610)  # Reproject

# Geometric operations
roads_buffer <- st_buffer(roads_utm, dist = 100)  # Buffer
roads_simplify <- st_simplify(roads_utm, dTolerance = 1)  # Simplify
roads_centroid <- st_centroid(roads)  # Centroid

# Spatial joins
joined <- st_join(roads, zones, join = st_intersects)

# Overlay
intersection <- st_intersection(roads, zones)

# Plot
ggplot() +
  geom_sf(data = zones, fill = NA) +
  geom_sf(data = roads, color = "blue") +
  theme_minimal()

# Calculate area
zones$area <- st_area(zones)  # sf returns units; geographic data can use geodesic/S2 area
zones$area_km2 <- units::set_units(st_area(zones), km^2)  # Convert to km2
```

### terra (Raster Processing)

```r
library(terra)

# Load raster
r <- rast("elevation.tif")

# Basic info
r
ext(r)  # Extent
crs(r)  # CRS
res(r)  # Resolution

# Raster calculations
slope <- terrain(r, v = "slope")
aspect <- terrain(r, v = "aspect")

# Multi-raster operations
ndvi <- (nir - red) / (nir + red)  # named, aligned, masked reflectance SpatRasters

# Focal operations
focal_mean <- focal(r, w = matrix(1, 3, 3), fun = mean)
focal_sd <- focal(r, w = matrix(1, 5, 5), fun = sd)

# Zonal statistics
zones <- vect("zones.shp")
zonal_mean <- extract(r, zones, fun = mean, na.rm = TRUE)

# Extract values at points
points <- vect("points.shp")
values <- extract(r, points)

# Write output
writeRaster(slope, "slope.tif", overwrite = TRUE)
```

### R Workflows

```r
# Complete land cover classification
library(sf)
library(terra)
library(randomForest)
library(caret)

# 1. Load data
training <- st_read("training.shp")
s2 <- rast("sentinel2.tif")

# 2. Extract training data
training_points <- st_centroid(training)
training_points <- st_transform(training_points, crs(s2))
values <- extract(s2, vect(training_points), ID = FALSE)

# 3. Combine with labels
df <- data.frame(values)
df$class <- as.factor(training$class_id)

# 4. Train model
set.seed(42)
# Use independently assigned spatial folds from the training table.
train_index <- which(training$fold != "holdout")
train_data <- df[train_index, ]
test_data <- df[-train_index, ]

rf_model <- randomForest(class ~ ., data = train_data, ntree = 100)

# 5. Predict
predicted <- predict(s2, model = rf_model)

# 6. Accuracy
conf_matrix <- confusionMatrix(predict(rf_model, test_data), test_data$class)
print(conf_matrix)

# 7. Export
writeRaster(predicted, "classified.tif", overwrite = TRUE)
```

## Julia Geospatial

### ArchGDAL.jl

```julia
using ArchGDAL

# Work inside the dataset lifetime; do not return borrowed feature geometries.
ArchGDAL.read("countries.shp") do dataset
    layer = ArchGDAL.getlayer(dataset, 0)
    for feature in layer
        geometry = ArchGDAL.getgeom(feature)
        println(ArchGDAL.toWKT(geometry))
    end
end

# Synthetic planar coordinates in chosen map units:
point = ArchGDAL.createpoint(0.0, 0.0)
buffered = ArchGDAL.buffer(point, 100.0)
```

GeoInterface defines interfaces; it is not a general constructor/geometry-operation
namespace. Use an actual geometry backend. Clone borrowed geometries if they must
outlive their owning dataset/feature.

### GeoStats.jl

```julia
using GeoStats
samples = georef((; value=[1., 2., 1.5]), [(0., 0.), (10., 0.), (5., 10.)])
grid = CartesianGrid(10, 10)
result = samples |> Interpolate(grid, model=Kriging(GaussianVariogram(range=10.)))
```

Current GeoStats uses interpolation transforms, not the former `SimulationProblem`
and `solve(OrdinaryKriging(...))` sketches. This uses synthetic Cartesian coordinates
and a chosen variogram, not a fitted geostatistical model. Fit/check an empirical
variogram, validate spatially and define units/support before a scientific result.

## JavaScript (Node.js & Browser)

### Turf.js (Browser/Node)

```javascript
// npm install @turf/turf
const turf = require('@turf/turf');

// Create features
const pt1 = turf.point([-122.4, 37.7]);
const pt2 = turf.point([-122.3, 37.8]);

// Distance (in kilometers)
const distance = turf.distance(pt1, pt2, { units: 'kilometers' });

// Buffer
const buffered = turf.buffer(pt1, 5, { units: 'kilometers' });

// Bounding box
const bbox = turf.bbox(buffered);

// Along a line
const line = turf.lineString([[-122.4, 37.7], [-122.3, 37.8]]);
const along = turf.along(line, 2, { units: 'kilometers' });

// Within
const points = turf.points([
  [-122.4, 37.7],
  [-122.35, 37.75],
  [-122.3, 37.8]
]);
const polygon = turf.polygon([[[-122.4, 37.7], [-122.3, 37.7], [-122.3, 37.8], [-122.4, 37.8], [-122.4, 37.7]]]);
const ptsWithin = turf.pointsWithinPolygon(points, polygon);

// Nearest point
const nearest = turf.nearestPoint(pt1, points);

// Area
const area = turf.area(polygon); // square meters

```

### Leaflet (Web Mapping)

```javascript
// Initialize map
const map = L.map('map').setView([37.7, -122.4], 13);

// Add tile layer
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Add GeoJSON layer
fetch('data.geojson')
  .then(response => response.json())
  .then(data => {
    L.geoJSON(data, {
      style: function(feature) {
        return { color: feature.properties.color };
      },
      onEachFeature: function(feature, layer) {
        const label = document.createElement('span');
        label.textContent = String(feature.properties.name ?? '');
        layer.bindPopup(label);
      }
    }).addTo(map);
  });

// Add markers
const marker = L.marker([37.7, -122.4]).addTo(map);
marker.bindPopup("Hello!").openPopup();

// Draw circles
const circle = L.circle([37.7, -122.4], {
  color: 'red',
  fillColor: '#f03',
  fillOpacity: 0.5,
  radius: 500
}).addTo(map);
```

## C++ Geospatial

### GDAL C++ API

```cpp
#include "gdal_priv.h"
#include "ogr_api.h"
#include "ogr_spatialref.h"
#include "ogrsf_frmts.h"
#include <stdexcept>

// Inside an application entry point, after GDALAllRegister():
// Open raster
GDALDataset *poDataset = (GDALDataset *) GDALOpen("input.tif", GA_ReadOnly);

if (poDataset == nullptr) throw std::runtime_error("Raster open failed");
// Get band
GDALRasterBand *poBand = poDataset->GetRasterBand(1);

// Read data
int nXSize = poBand->GetXSize();
int nYSize = poBand->GetYSize();
float *pafScanline = (float *) CPLMalloc(sizeof(float) * nXSize);
CPLErr read_status = poBand->RasterIO(GF_Read, 0, 0, nXSize, 1,
                 pafScanline, nXSize, 1, GDT_Float32, 0, 0);
// Check read_status != CE_None and handle I/O errors before using values.

CPLFree(pafScanline);
GDALClose(poDataset);

// Vector data
GDALDataset *poDS = (GDALDataset *) GDALOpenEx("roads.shp",
    GDAL_OF_VECTOR, NULL, NULL, NULL);
if (poDS == nullptr) throw std::runtime_error("Vector open failed");
OGRLayer *poLayer = poDS->GetLayer(0);

OGRFeature *poFeature;
poLayer->ResetReading();
while ((poFeature = poLayer->GetNextFeature()) != NULL) {
    OGRGeometry *poGeometry = poFeature->GetGeometryRef();
    // Process geometry
    OGRFeature::DestroyFeature(poFeature);
}

GDALClose(poDS);
```

## Java Geospatial

### GeoTools

```java
import org.geotools.api.data.FileDataStore;
import org.geotools.api.data.FileDataStoreFinder;
import org.geotools.data.simple.SimpleFeatureCollection;
import org.geotools.data.simple.SimpleFeatureIterator;
import org.geotools.api.data.SimpleFeatureSource;
import org.geotools.geometry.jts.JTS;
import org.geotools.referencing.CRS;
import org.geotools.api.feature.simple.SimpleFeature;
import org.geotools.api.referencing.crs.CoordinateReferenceSystem;

import java.io.File;
import org.geotools.api.referencing.operation.MathTransform;
import org.locationtech.jts.geom.Geometry;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.Point;

// Load shapefile
File file = new File("roads.shp");
FileDataStore store = FileDataStoreFinder.getDataStore(file);
SimpleFeatureSource featureSource = store.getFeatureSource();

// Read features
SimpleFeatureCollection collection = featureSource.getFeatures();
try (SimpleFeatureIterator iterator = collection.features()) {
    while (iterator.hasNext()) {
        SimpleFeature feature = iterator.next();
        Geometry geom = (Geometry) feature.getDefaultGeometryProperty().getValue();
        // Process geometry
    }
}

// Create point
GeometryFactory gf = new GeometryFactory();
Point point = gf.createPoint(new Coordinate(-122.4, 37.7));

// Reproject
CoordinateReferenceSystem sourceCRS = CRS.decode("EPSG:4326", true);
CoordinateReferenceSystem targetCRS = CRS.decode("EPSG:32610", true);
MathTransform transform = CRS.findMathTransform(sourceCRS, targetCRS);
Geometry reprojected = JTS.transform(point, transform);
store.dispose(); // In production use finally to release the datastore even on error.
```

## Go Geospatial

### Orb geometry and spherical metrics

```go
package main

import (
    "fmt"
    "github.com/paulmach/orb"
    "github.com/paulmach/orb/geojson"
    "github.com/paulmach/orb/geo"
)

func main() {
    // Create point
    point := orb.Point{-122.4, 37.7}

    // Create linestring
    line := orb.LineString{
        {-122.4, 37.7},
        {-122.3, 37.8},
    }

    // Create polygon
    polygon := orb.Polygon{
        {{-122.4, 37.7}, {-122.3, 37.7}, {-122.3, 37.8}, {-122.4, 37.8}, {-122.4, 37.7}},
    }

    // GeoJSON feature
    feature := geojson.NewFeature(polygon)
    feature.Properties["name"] = "Zone 1"

    _ = line
    _ = feature
    // Spherical geographic metrics (not planar degrees)
    distance := geo.Distance(point, orb.Point{-122.3, 37.8})

    // Area
    area := geo.Area(polygon)

    fmt.Printf("Distance: %.2f meters\n", distance)
    fmt.Printf("Area: %.2f square meters\n", area)
}
```

For more code examples across all languages, see [code-examples.md](code-examples.md).

## Rust geospatial

This fragment targets the reviewed `geo` 0.33.1 API. Geometry methods are planar and
unitless; use a projected metre grid for the buffer/simplification shown.

```rust
// Cargo.toml: geo = "0.33.1"
use geo::{Point, LineString, Polygon, Buffer, Centroid, Contains, Simplify};
fn main() {
    let polygon = Polygon::new(LineString::from(vec![
        (0., 0.), (100., 0.), (100., 100.), (0., 100.), (0., 0.)
    ]), vec![]);
    let point = Point::new(50., 50.);
    let buffered = polygon.buffer(10.);
    let simplified = polygon.simplify(1.);
    println!("{} {:?}", polygon.contains(&point), buffered.centroid());
    let _ = simplified;
}
```

For CRS conversion, use a compatible `proj` crate/native PROJ version and
`Proj::new_known_crs(source, target, None)` with a verified axis-order contract.
Do not buffer longitude/latitude by 1000 and label it metres. `simplify` can change
topology; validate the result. Pin language dependencies in the actual project.

Sources: [sf unary](https://r-spatial.github.io/sf/reference/geos_unary.html),
[terra extract](https://rspatial.github.io/terra/reference/extract.html),
[ArchGDAL geometry](https://yeesian.com/ArchGDAL.jl/latest/geometries/),
[GeoStats interpolation](https://juliaearth.github.io/GeoStatsDocs/stable/interpolation/),
[GeoTools35 quickstart](https://docs.geotools.org/stable/userguide/tutorial/quickstart/maven.html),
[orb geo](https://pkg.go.dev/github.com/paulmach/orb/geo),
[GeoRust](https://docs.rs/geo/latest/geo/),
[Turf](https://turfjs.org/docs/api/interpolate),
[OSM tile policy](https://operations.osmfoundation.org/policies/tiles/).
