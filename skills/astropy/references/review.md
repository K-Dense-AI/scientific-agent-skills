# Astropy review and verification

Reviewed 2026-09-30 against official stable **Astropy 8.0.1** documentation,
release notes, PyPI metadata and installed 8.0.1 source. Python 3.11+ and NumPy
2+ are required. The installed test stack used NumPy 2.5.1 and SciPy 1.18.1.

## Executed scope

`tests/astropy/test_workflows.py` exercises small synthetic data only:

- Units: spectral and Doppler round trips, magnitude conversion, no-copy aliases,
  scoped custom units.
- Coordinates: ICRS/Galactic round trip, FK5 equinox, unrefracted AltAz, proper
  motion propagation, unit-aware columns and repeated nearest-neighbor matches.
- Time: same-instant scale conversion, UTC leap second interval, two-part JD,
  masks, sidereal/rotation angles and barycentric time/RV corrections.
- Cosmology: distance duality, angular-size units, age/lookback identity,
  two inverse-distance branches, named cloning and differential-volume units.
- FITS/table: images, sections, headers, checksums, logical NULL/variable-length
  columns, ECSV/FITS masks and Time, table indices, copying, joins, HDF5, Pandas
  and a tiny Dask write.
- WCS: FITS versus zero-based pixel origin, NumPy row/column order, round trip,
  footprint and scale representation. Modeling/other modules: Gaussian fit and
  compound models, CCDData uncertainty round trip, normalization, convolution,
  robust statistics and constants.

A supplemental synthetic smoke also executed the remaining listed unit helpers,
coordinate representations, cosmology distance/density methods, Time formats and
scales, table mutations and local formats, FITS update/append/diff, model
constructors and progress API. It reproduced the unnamed-cosmology clone failure
and the unrestricted `w0wzCDM.age` failure documented in the cosmology reference.

IERS auto-download was disabled; 2023 epochs are covered by bundled data. These
checks establish API behavior on synthetic examples, not calibration accuracy,
real-observation validity or every optional backend. The standalone fragments
throughout the references are recipes, not one sequential program. File/column
placeholders need the user's corresponding inputs. Remote resolver/geocoder,
S3, large-file performance, browser display, SAMP hub and external ephemeris
examples are illustrative and were not run end to end. The broad `[all]` extras
installation was not exercised; only the local test dependencies were installed.

## Remote surfaces and provenance

This skill uses Python interfaces, not a paginated astronomy REST client. The
following network behavior was checked against the current SDK source/docs:

| Interface | Verified contract and boundary |
| --- | --- |
| `SkyCoord.from_name(name)` | Sesame resolver; returns a `SkyCoord` or raises a resolution error. SDK constructs a database selector plus URL-encoded object name; defaults to all databases and may try configured mirrors. No authentication or pagination. Record returned coordinates, frame, service and date; names are disclosed to the resolver. |
| `EarthLocation.of_site` / `get_site_names` | Reads `coordinates/sites.json` through Astropy's data server/cache. An empty cache causes a download; `refresh_cache=True` replaces it. Preserve retrieved geodetic values and registry metadata for reproducibility. |
| `EarthLocation.of_address` | Nominatim `GET /search?q=...&format=json` by default; first result is used. Google `GET /maps/api/geocode/json?address=...&key=...` with a supplied key; optional elevation uses `/maps/api/elevation/json?locations=lat,lon&key=...`. Height defaults to zero. These convenience calls are not precision survey measurements or a bulk geocoding service. |
| IERS/time transforms | Bundled `astropy-iers-data`; auto-download can fetch IERS-A from `https://datacenter.iers.org/data/9/finals2000A.all`, with USNO mirror `https://maia.usno.navy.mil/ser7/finals2000A.all`. Disabling auto-download also suppresses online leap-second refresh. Record data version/coverage and handle degraded accuracy explicitly. |
| `fits.open(..., use_fsspec=True)` | Uses the selected filesystem backend and its auth. Anonymous S3 requires public data; `.section` enables partial access subject to range/backend/compression behavior. No generic Astropy authentication or pagination contract. |
| `download_file(url, cache=True)` | Fetches the supplied URL and returns a local filename; caching is opt-in. `cache=False` uses temporary storage rather than guaranteeing no local persistence during execution. |
| `pyvo.samp.SAMPIntegratedClient` | Replacement for deprecated `astropy.samp`; requires a hub. `notify_all` discloses the supplied table URI to connected clients, so it belongs only in an explicitly requested sharing workflow. |

Do not substitute HTTP status probes for scientific payload verification. No
private targets, credentials, authenticated service requests or large remote
datasets were used in this review. Provider limits still apply; public Nominatim
requires an identifying user agent and at most one request per second, so do not
copy the older high-throughput wording from Astropy's method docstring.

## Official sources

- [8.0 changes](https://docs.astropy.org/en/stable/whatsnew/8.0.html),
  [full changelog](https://docs.astropy.org/en/stable/changelog.html),
  [release metadata](https://pypi.org/pypi/astropy/json).
- [Units](https://docs.astropy.org/en/stable/units/index.html),
  [Quantity behavior](https://docs.astropy.org/en/stable/units/quantity.html).
- [Coordinates](https://docs.astropy.org/en/stable/coordinates/index.html),
  [SkyCoord API](https://docs.astropy.org/en/stable/api/astropy.coordinates.SkyCoord.html),
  [EarthLocation API](https://docs.astropy.org/en/stable/api/astropy.coordinates.EarthLocation.html),
  [remote methods](https://docs.astropy.org/en/stable/coordinates/remote_methods.html),
  [8.0.1 resolver source](https://github.com/astropy/astropy/blob/v8.0.1/astropy/coordinates/name_resolve.py),
  [8.0.1 location source](https://github.com/astropy/astropy/blob/v8.0.1/astropy/coordinates/earth.py),
  [Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/),
  [Nominatim search](https://nominatim.org/release-docs/latest/api/Search/),
  [Google geocoding](https://developers.google.com/maps/documentation/geocoding/guides-v3/requests-geocoding),
  [Google elevation](https://developers.google.com/maps/documentation/elevation/requests-elevation).
- [Time](https://docs.astropy.org/en/stable/time/index.html),
  [IERS](https://docs.astropy.org/en/stable/utils/iers.html).
- [FITS](https://docs.astropy.org/en/stable/io/fits/index.html),
  [file API](https://docs.astropy.org/en/stable/io/fits/api/files.html),
  [remote FITS](https://docs.astropy.org/en/stable/io/fits/usage/cloud.html),
  [FITS tables](https://docs.astropy.org/en/stable/io/unified_table_fits.html).
- [Tables](https://docs.astropy.org/en/stable/table/index.html),
  [copy/view behavior](https://docs.astropy.org/en/stable/table/access_table.html),
  [unique API](https://docs.astropy.org/en/stable/api/astropy.table.unique.html).
- [Cosmology](https://docs.astropy.org/en/stable/cosmology/index.html),
  [inverse branches](https://docs.astropy.org/en/stable/api/astropy.cosmology.z_at_value.html),
  [linear dark-energy limits](https://docs.astropy.org/en/stable/api/astropy.cosmology.w0wzCDM.html).
- [WCS interface](https://docs.astropy.org/en/stable/wcs/wcsapi.html),
  [WCS API](https://docs.astropy.org/en/stable/api/astropy.wcs.WCS.html).
- [NDData](https://docs.astropy.org/en/stable/nddata/index.html),
  [fitters](https://docs.astropy.org/en/stable/modeling/fitting.html),
  [Gaussian1D](https://docs.astropy.org/en/stable/api/astropy.modeling.functional_models.Gaussian1D.html),
  [normalization](https://docs.astropy.org/en/stable/visualization/normalization.html),
  [convolution](https://docs.astropy.org/en/stable/convolution/index.html),
  [statistics](https://docs.astropy.org/en/stable/stats/index.html),
  [constants](https://docs.astropy.org/en/stable/constants/index.html),
  [download API](https://docs.astropy.org/en/stable/api/astropy.utils.data.download_file.html),
  [PyVO SAMP](https://pyvo.readthedocs.io/en/latest/samp/index.html).
