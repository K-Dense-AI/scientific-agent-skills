# NIST Data APIs

## Overview

NIST provides several scientific databases. REST API availability varies by dataset.

## 1. NIST CODATA Fundamental Physical Constants

### Base URL
```
https://physics.nist.gov/cgi-bin/cuu
```

**No formal REST API.** Data is served via CGI scripts returning HTML. The constants can be accessed programmatically via structured URLs but responses are HTML, not JSON/XML.

**Workaround — machine-readable ASCII:**
```
https://physics.nist.gov/cuu/Constants/Table/allascii.txt
```
Returns a tab-delimited text file of all fundamental constants with values, uncertainties, and units.

**Individual constant lookup:**
```
https://physics.nist.gov/cgi-bin/cuu/Value?{constant_key}
```
Example keys: `bohrrada0` (Bohr radius), `c` (speed of light), `h` (Planck constant), `e` (electron charge), `me` (electron mass), `na` (Avogadro number), `k` (Boltzmann constant).

Example:
```
https://physics.nist.gov/cgi-bin/cuu/Value?h
```
Returns HTML page. Parse the value from the page content.

**No API key required. No rate limits documented.**

## 2. NIST Atomic Spectra Database (ASD)

### Base URL
```
https://physics.nist.gov/cgi-bin/ASD
```

**No formal REST API.** Queries are CGI-based, returning HTML. However, machine-readable output is available via specific parameters.

**Spectral lines query:**
```
https://physics.nist.gov/cgi-bin/ASD/lines1.pl?spectra={element}&low_w={min_wavelength}&upp_w={max_wavelength}&unit={unit}&format={format}
```

| Parameter  | Type   | Description |
|------------|--------|-------------|
| `spectra`  | string | Element symbol or ion (e.g., `H`, `Fe`, `He+I`, `O+II`). |
| `low_w`    | float  | Lower wavelength bound. |
| `upp_w`    | float  | Upper wavelength bound. |
| `unit`     | int    | `0` = Angstroms, `1` = nm, `2` = um. |
| `format`   | int    | `0` = HTML, `1` = ASCII, `2` = CSV, `3` = tab-delimited. |
| `line_out` | int    | `0` = all, `1` = only observed, `2` = only Ritz. |
| `show_obs_wl` | int | `1` = show observed wavelengths. |
| `show_calc_wl` | int | `1` = show Ritz wavelengths. |
| `A_out`    | int    | `1` = include transition probabilities. |

**Example — Hydrogen lines 3000-7000 Angstroms as CSV:**
```
https://physics.nist.gov/cgi-bin/ASD/lines1.pl?spectra=H&low_w=3000&upp_w=7000&unit=0&format=2&line_out=0&show_obs_wl=1&A_out=1
```

**Energy levels query:**
```
https://physics.nist.gov/cgi-bin/ASD/energy1.pl?spectra={element}&units={units}&format={format}
```

**No API key required. No formal rate limits but automated bulk queries are discouraged.**

## 3. NIST Chemistry WebBook

### Base URL
```
https://webbook.nist.gov/cgi/cbook.cgi
```

**No formal REST API.** CGI-based with HTML output. Structured URLs can be used.

**Search by name:**
```
https://webbook.nist.gov/cgi/cbook.cgi?Name={compound}&Units=SI
```

**Search by CAS number:**
```
https://webbook.nist.gov/cgi/cbook.cgi?ID={cas_number}&Units=SI
```

**Search by formula:**
```
https://webbook.nist.gov/cgi/cbook.cgi?Formula={formula}&Units=SI
```

**JCAMP-DX spectra (machine-readable):**
```
https://webbook.nist.gov/cgi/cbook.cgi?ID={cas_number}&Type=IR-Spec&Index=0&JCAMP=C{cas_no_dashes}
```

## Summary

NIST databases generally do **not** offer modern REST/JSON APIs. Data access is primarily through CGI endpoints returning HTML or delimited text. For programmatic use, the ASCII/CSV output options from ASD are the most practical. No authentication is required for any NIST endpoint.
