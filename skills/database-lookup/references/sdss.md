# SDSS SkyServer API

## Base URL

```
https://skyserver.sdss.org/dr18/SkyServerWS
```

Replace `dr18` with the desired data release (e.g., `dr17`, `dr16`).

## Authentication

No API key required. All endpoints are public.

## Key Endpoints

### 1. SQL Search (CasJobs-style free-form SQL)

```
GET /SearchTools/SqlSearch
```

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `cmd`     | string | **Required.** SQL query against SDSS CasJobs schema. |
| `format`  | string | `json`, `xml`, `csv`, `html`, `votable`. Default: `html`. |

**Example — query 10 galaxies:**
```
https://skyserver.sdss.org/dr18/SkyServerWS/SearchTools/SqlSearch?cmd=SELECT TOP 10 objid,ra,dec,u,g,r,i,z FROM PhotoObj WHERE type=3&format=json
```

Type codes: `3` = galaxy, `6` = star.

**Response (JSON):**
```json
[
  {"Rows": [
    {"objid": 1237645941825863680, "ra": 195.123, "dec": 2.456, "u": 22.1, "g": 20.8, "r": 19.5, "i": 19.1, "z": 18.9}
  ]}
]
```

### 2. Radial Search

```
GET /SearchTools/RadialSearch
```

| Parameter    | Type   | Description |
|--------------|--------|-------------|
| `ra`         | float  | **Required.** Right ascension (degrees). |
| `dec`        | float  | **Required.** Declination (degrees). |
| `radius`     | float  | Search radius in arcminutes. Default: 1. |
| `format`     | string | `json`, `xml`, `csv`. |
| `limit`      | int    | Max results. |
| `objtype`    | string | Filter: `star`, `galaxy`, or blank for all. |

**Example — objects within 2 arcmin of RA=180, Dec=+0.5:**
```
https://skyserver.sdss.org/dr18/SkyServerWS/SearchTools/RadialSearch?ra=180&dec=0.5&radius=2&format=json&limit=10
```

### 3. Rectangular Search

```
GET /SearchTools/RectangularSearch
```

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `min_ra`  | float  | Minimum RA (degrees). |
| `max_ra`  | float  | Maximum RA (degrees). |
| `min_dec` | float  | Minimum Dec (degrees). |
| `max_dec` | float  | Maximum Dec (degrees). |
| `format`  | string | `json`, `xml`, `csv`. |
| `limit`   | int    | Max results. |

### 4. Object Lookup by ObjID

```
GET /SearchTools/SqlSearch?cmd=SELECT * FROM PhotoObj WHERE objid={objid}&format=json
```

### 5. Spectra Search by Plate-MJD-Fiber

```
GET /SearchTools/SqlSearch?cmd=SELECT * FROM SpecObj WHERE plate={plate} AND mjd={mjd} AND fiberid={fiberid}&format=json
```

### 6. Image Cutout Service

```
GET /ImgCutout/getjpeg
```

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `ra`      | float  | **Required.** RA (degrees). |
| `dec`     | float  | **Required.** Dec (degrees). |
| `scale`   | float  | Arcsec/pixel. Default: 0.396127. |
| `width`   | int    | Image width in pixels. Default: 512. |
| `height`  | int    | Image height in pixels. Default: 512. |

**Example:**
```
https://skyserver.sdss.org/dr18/SkyServerWS/ImgCutout/getjpeg?ra=180.0&dec=0.5&scale=0.4&width=256&height=256
```

Returns JPEG image data.

### 7. Spectrum Plot/Data

Spectrum FITS files can be retrieved from the Science Archive Server:
```
https://data.sdss.org/sas/dr18/spectro/sdss/redux/{run2d}/spectra/{plate}/spec-{plate}-{mjd}-{fiberid}.fits
```

## Important SQL Tables

| Table       | Description |
|-------------|-------------|
| `PhotoObj`  | Photometric measurements (positions, magnitudes). |
| `SpecObj`   | Spectroscopic measurements (redshifts, classifications). |
| `Galaxy`    | View of PhotoObj filtered to galaxies. |
| `Star`      | View of PhotoObj filtered to stars. |

## Rate Limits

No formal documented rate limits. Queries returning very large result sets may time out. Use `TOP N` in SQL queries to limit results. For bulk data, use CasJobs (https://skyserver.sdss.org/CasJobs/) with a free account.
