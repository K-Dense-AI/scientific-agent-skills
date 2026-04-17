# SIMBAD Script Interface API Reference

The SIMBAD script interface (`sim-script`) accepts plain-text scripts via HTTP POST and returns formatted results. It is the simplest way to query SIMBAD for individual objects or small batches.

## Endpoint

```
POST https://simbad.cds.unistra.fr/simbad/sim-script
Content-Type: application/x-www-form-urlencoded

Body: script=<script text>
```

## Script Structure

A SIMBAD script consists of configuration lines followed by one or more query commands:

```
output console=off script=off
format object "<format string>"
query id <object name>
```

- `output console=off script=off` — Suppresses metadata/header lines
- `format object "<format string>"` — Defines the output columns using format codes
- `query ...` — The actual query command

## Query Commands

### Query by Object Name

```
query id <object_name>
```

Examples:
```
query id M31
query id Sirius
query id NGC 1068
query id HD 209458
query id Gaia DR3 4111834567779557376
```

### Query by Coordinates (Cone Search)

```
query coo <ra> <dec> radius=<value><unit>
```

Coordinate formats:
- Decimal degrees: `query coo 10.68458 +41.26917 radius=5m`
- Sexagesimal: `query coo 00:42:44.330 +41:16:07.50 radius=5m`

Radius units:
- `d` = degrees
- `m` = arcminutes
- `s` = arcseconds

### Query by Identifier Pattern

```
query id wildcard <pattern>
```

The `*` wildcard matches any sequence of characters:
```
query id wildcard NGC 10*
query id wildcard HD 20945*
query id wildcard 2MASS J*
```

### Query by Criteria

```
query sample <criteria>
```

Examples:
```
query sample otype='Star' & Vmag < 5.0
query sample region(circle, 10.68 +41.27, 10m) & otype='Galaxy'
```

## Format Codes

Format codes define which data fields appear in the output. Use them inside double quotes in the `format object` directive.

### Basic Identification

| Code | Description | Example Output |
|------|-------------|----------------|
| `%IDLIST(1)` | Primary identifier | `M  31` |
| `%IDLIST` | All identifiers | `M  31, NGC  224, UGC  454, ...` |
| `%MAIN_ID` | Main identifier | `M  31` |

### Coordinates

| Code | Description | Example Output |
|------|-------------|----------------|
| `%COO(A D;ICRS)` | RA Dec in ICRS (sexagesimal) | `00 42 44.330 +41 16 07.50` |
| `%COO(A D;ICRS;J2000)` | RA Dec with epoch | `00 42 44.330 +41 16 07.50` |
| `%COO(d d;ICRS)` | RA Dec in decimal degrees | `10.6847083 +41.2687500` |
| `%COO(A D;GAL)` | Galactic coordinates | `121.1743 -21.5733` |

### Object Properties

| Code | Description | Example Output |
|------|-------------|----------------|
| `%OTYPE` | Object type (condensed) | `Galaxy` |
| `%OTYPE(V)` | Object type (verbose) | `Galaxy` |
| `%SP` | Spectral type | `A1V` |
| `%MT` | Morphological type | `SA(s)b` |

### Photometry

| Code | Description | Example Output |
|------|-------------|----------------|
| `%FLUXLIST(V)` | V-band magnitude | `3.44` |
| `%FLUXLIST(B)` | B-band magnitude | `4.36` |
| `%FLUXLIST(U;B;V;R;I)` | Multiple bands | `... \| ... \| ...` |
| `%FLUXLIST(J;H;K)` | Near-infrared bands | `... \| ... \| ...` |

### Kinematics

| Code | Description | Example Output |
|------|-------------|----------------|
| `%PM` | Proper motion (mas/yr) | `+5.59 -1.78` |
| `%PLX` | Parallax (mas) | `130.23` |
| `%RV` | Radial velocity (km/s) | `-300` |

### Predefined Format Levels

**Basic:**
```
format object "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE"
```

**Detailed:**
```
format object "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE | %SP | %FLUXLIST(V)"
```

**Full:**
```
format object "%IDLIST(1) | %COO(A D;ICRS;J2000) | %OTYPE | %SP | %FLUXLIST(U;B;V;R;I;J;H;K) | %PM | %PLX | %RV | %MT"
```

## Parsing the Response

The response is plain text. Lines starting with `::` are metadata and should be filtered out. Data lines use the separator specified in your format string (typically `|`).

```python
import requests

def query_simbad_object(name, output_format="basic"):
    format_strings = {
        "basic": "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE",
        "detailed": "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE | %SP | %FLUXLIST(V)",
        "full": "%IDLIST(1) | %COO(A D;ICRS;J2000) | %OTYPE | %SP | %FLUXLIST(U;B;V;R;I;J;H;K) | %PM | %PLX | %RV | %MT",
    }

    fmt = format_strings.get(output_format, format_strings["basic"])

    script = '\n'.join([
        "output console=off script=off",
        f'format object "{fmt}"',
        f"query id {name}",
    ])

    response = requests.post(
        "https://simbad.cds.unistra.fr/simbad/sim-script",
        data={"script": script},
        timeout=30,
    )
    response.raise_for_status()

    lines = [
        line.strip()
        for line in response.text.strip().split("\n")
        if line.strip() and not line.startswith("::")
    ]

    results = []
    for line in lines:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            results.append({
                "main_id": parts[0],
                "coordinates": parts[1],
                "object_type": parts[2],
                **({} if len(parts) <= 3 else {"extra": parts[3:]}),
            })

    return results
```

## Error Handling

SIMBAD returns errors as plain text containing keywords like `error` or `not found`. Always check the response body for these patterns:

```python
text = response.text.strip()
data_lines = [l for l in text.split("\n") if l and not l.startswith("::")]

if any("error" in l.lower() or "not found" in l.lower() for l in data_lines):
    print("Object not found or query error")
```

## Rate Limiting

SIMBAD is a public service. While there are no strict published rate limits, best practices include:

- Add `time.sleep(0.5)` between sequential queries
- Use TAP/ADQL for batch queries instead of looping over the script interface
- Cache results for repeated lookups
- Use a `timeout=30` on requests

## Multiple Object Queries

You can query multiple objects in a single script:

```
output console=off script=off
format object "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE"
query id M31
query id M42
query id M101
```

Each query produces its own output block separated by SIMBAD metadata lines.
