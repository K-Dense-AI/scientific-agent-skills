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
| `cmd`     | string | **Required.** SQL query against the selected SkyServer release schema; this synchronous API is separate from asynchronous CasJobs. |
| `format`  | string | `json`, `xml`, `csv`, `html`, `votable`. Default: `html`. |

**Example — query 10 galaxies:**
```
https://skyserver.sdss.org/dr18/SkyServerWS/SearchTools/SqlSearch?cmd=SELECT TOP 10 objid,ra,dec,u,g,r,i,z FROM PhotoObj WHERE type=3&format=json
```

Type codes: `3` = galaxy, `6` = star.

**Response (JSON, illustrative):**
```json
[
  {"Rows": [
    {"objid": 1237645941825863680, "ra": 195.123, "dec": 2.456, "u": 22.1, "g": 20.8, "r": 19.5, "i": 19.1, "z": 18.9}
  ]}
]
```

The response may contain a separate `SqlQuery` table alongside the result table. Select the result by `TableName` and validate its columns, rather than concatenating every `Rows` array.

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
| `whichquery` | string | `imaging` or `spectro`, as supported by this search. |
| `whichway` | string | Coordinate mode, e.g. `equatorial`. |

**Example — objects within 2 arcmin of RA=180, Dec=+0.5:**
```
https://skyserver.sdss.org/dr18/SkyServerWS/SearchTools/RadialSearch?ra=180&dec=0.5&radius=2&whichway=equatorial&whichquery=imaging&format=json&limit=10
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

Spectrum FITS files are on the [Science Archive Server](https://data.sdss.org/sas/dr18/). Paths depend on instrument, data release, reduction pipeline and plate/fiber formatting. Obtain the actual file URL from the selected release's object page or data model; do not construct one universal `spectro/sdss/redux` path for every survey.

## Important SQL Tables

| Table       | Description |
|-------------|-------------|
| `PhotoObj`  | Photometric measurements (positions, magnitudes). |
| `SpecObj`   | Spectroscopic measurements (redshifts, classifications). |
| `Galaxy`    | View of PhotoObj filtered to galaxies. |
| `Star`      | View of PhotoObj filtered to stars. |

URL-encode `cmd` (for example `curl --get --data-urlencode "cmd=SELECT TOP 10 ..."`). Preserve 64-bit object IDs as integers or strings, not floating-point numbers.

## Rate Limits

No formal documented rate limits. Queries returning very large result sets may time out. Use `TOP N` in SQL queries to limit results. For bulk data, use CasJobs (https://skyserver.sdss.org/CasJobs/) with a free account.
