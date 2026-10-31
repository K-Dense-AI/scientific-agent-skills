"""Small, in-memory geospatial recipes; caller supplies scientific provenance.

Import from the skill's scripts directory. No downloads or model fitting occur on import.
"""
from pathlib import Path
import numpy as np
import rasterio
from rasterio.features import rasterize


def as_float(values):
    """Preserve masked cells and nonfinite values as NaN before arithmetic."""
    return np.ma.asarray(values, dtype=np.float64).filled(np.nan)


def ratio(numerator, denominator):
    numerator, denominator = np.broadcast_arrays(as_float(numerator), as_float(denominator))
    result = np.full(numerator.shape, np.nan)
    valid = np.isfinite(numerator) & np.isfinite(denominator) & (denominator != 0)
    np.divide(numerator, denominator, out=result, where=valid)
    return result


def normalized_difference(a, b):
    a, b = as_float(a), as_float(b)
    if a.shape != b.shape:
        raise ValueError('Bands must have identical shapes on a verified common grid')
    return ratio(a - b, a + b)


def spectral_indices(blue, green, red, nir, swir1, swir2):
    """Input is aligned, masked physical reflectance, NOT unscaled digital numbers."""
    bands = [as_float(x) for x in (blue, green, red, nir, swir1, swir2)]
    if len({x.shape for x in bands}) != 1:
        raise ValueError('Bands must have identical shapes')
    blue, green, red, nir, swir1, swir2 = bands
    return {
        'NDVI': normalized_difference(nir, red),
        'EVI': 2.5 * ratio(nir - red, nir + 6 * red - 7.5 * blue + 1),
        'SAVI': 1.5 * ratio(nir - red, nir + red + 0.5),
        'NDWI': normalized_difference(green, nir),
        'MNDWI': normalized_difference(green, swir1),
        'NBR': normalized_difference(nir, swir2),
        'NDBI': normalized_difference(swir1, nir),
    }


def terrain_metrics(dem, transform, crs, *, azimuth=315, altitude=45):
    """Finite-difference slope/aspect/hillshade for north-up metric DEMs.

    Elevations MUST be metres. Aspect is downslope, clockwise from north; flat
    pixels have undefined (NaN) aspect. This is not a hydrological flow algorithm.
    """
    from pyproj import CRS
    crs = CRS.from_user_input(crs)
    if not crs.is_projected or any(abs(a.unit_conversion_factor - 1) > 1e-12 for a in crs.axis_info[:2]):
        raise ValueError('A projected CRS with metre horizontal units is required')
    if not np.isfinite(tuple(transform)).all() or transform.b != 0 or transform.d != 0 or transform.a <= 0 or transform.e >= 0:
        raise ValueError('A finite north-up, unrotated transform is required')
    if not np.isfinite([azimuth, altitude]).all() or not 0 <= altitude <= 90:
        raise ValueError('Finite azimuth and altitude in [0, 90] required')
    z = as_float(dem)
    if z.ndim != 2 or min(z.shape) < 2:
        raise ValueError('DEM must be a two-dimensional array with at least 2 cells per axis')
    dz_dy, dz_dx = np.gradient(z, transform.e, transform.a)
    norm = np.hypot(dz_dx, dz_dy)
    slope = np.arctan(norm)
    aspect = np.mod(np.arctan2(-dz_dx, -dz_dy), 2 * np.pi)
    az, alt = np.deg2rad([azimuth, altitude])
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    valid = np.isfinite(z) & np.isfinite(norm)
    return (np.where(valid, np.rad2deg(slope), np.nan),
            np.where(valid & (norm > 0), np.rad2deg(aspect), np.nan),
            np.where(valid, np.clip(shade, 0, 1), np.nan))


def write_ndvi(input_path, output_path, *, red_band, nir_band, scale, offset):
    """Verified stack band indices and provider-specific common scale/offset required.

    Input mask must already incorporate cloud/shadow QA. Rasterio does not infer
    Sentinel band positions. A supplied scale/offset is applied exactly once.
    """
    if Path(output_path).exists() or Path(output_path).is_symlink():
        raise ValueError('Output already exists; select a new path')
    if red_band == nir_band:
        raise ValueError('Red and NIR must be distinct bands')
    if Path(input_path).resolve() == Path(output_path).resolve():
        raise ValueError('Input and output paths must differ')
    if not np.isfinite([scale, offset]).all() or scale <= 0:
        raise ValueError('Scale must be positive and scale/offset must be finite')
    with rasterio.open(input_path) as src:
        if src.crs is None:
            raise ValueError('Input CRS is missing')
        for band in (red_band, nir_band):
            if isinstance(band, bool) or not isinstance(band, int) or not 1 <= band <= src.count:
                raise ValueError('Band positions are one-based integers within the stack')
        red = src.read(red_band, masked=True).astype('float64') * scale + offset
        nir = src.read(nir_band, masked=True).astype('float64') * scale + offset
        result = normalized_difference(nir, red).astype('float32')
        profile = src.profile.copy()
    profile.update(driver='GTiff', count=1, dtype='float32', nodata=np.nan)
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(result, 1)
        dst.set_band_description(1, 'NDVI')
    return result


def classify_imagery(raster_path, training_gdf, output_path, *, random_state=42):
    """Small in-memory RF fit/predict recipe. Accuracy must be assessed separately.

    Reject overlapping training pixel centres and require labels 1..65534; 0 is output
    nodata. Align labels to raster CRS, preserve masks, and return the fitted model.
    """
    from sklearn.ensemble import RandomForestClassifier
    if Path(output_path).exists() or Path(output_path).is_symlink():
        raise ValueError('Output already exists; select a new path')
    if Path(raster_path).resolve() == Path(output_path).resolve():
        raise ValueError('Input and output paths must differ')
    with rasterio.open(raster_path) as src:
        if src.crs is None or training_gdf.crs is None:
            raise ValueError('Both raster and training data need known CRS')
        if training_gdf.empty or training_gdf.geometry.isna().any() or training_gdf.geometry.is_empty.any() or not training_gdf.is_valid.all():
            raise ValueError('Training geometries must be nonempty and valid')
        if not training_gdf.geom_type.isin(['Polygon', 'MultiPolygon']).all():
            raise ValueError('Training geometries must be polygons')
        labels = np.asarray(training_gdf['class_id'], dtype=float)
        if not np.isfinite(labels).all() or np.any(labels != np.floor(labels)) or np.any((labels < 1) | (labels > 65534)):
            raise ValueError('class_id must be an integer from 1 to 65534')
        training = training_gdf.to_crs(src.crs)
        image = as_float(src.read(masked=True))
        valid = np.isfinite(image).all(axis=0)
        targets = np.zeros(image.shape[1:], dtype='uint16')
        occupied = np.zeros_like(targets, dtype=bool)
        for geom, label in zip(training.geometry, labels):
            cells = rasterize([(geom, 1)], out_shape=targets.shape, transform=src.transform, dtype='uint8').astype(bool)
            if not np.any(cells & valid):
                raise ValueError('A training polygon contains no valid pixel centres')
            if np.any(occupied & cells):
                raise ValueError('Training polygons overlap at raster pixel centres')
            occupied |= cells
            targets[cells] = int(label)
        train_mask = occupied & valid
        if np.unique(targets[train_mask]).size < 2:
            raise ValueError('At least two observed classes are required')
        model = RandomForestClassifier(n_estimators=100, random_state=random_state, n_jobs=1)
        model.fit(image[:, train_mask].T, targets[train_mask])
        prediction = np.zeros(targets.shape, dtype='uint16')
        prediction[valid] = model.predict(image[:, valid].T)
        profile = src.profile.copy()
    profile.update(driver='GTiff', dtype='uint16', nodata=0, count=1)
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(prediction, 1)
    return model
