# Materials Project API

## Base URL

```
https://api.materialsproject.org
```

## Authentication

Requires a free API key. Register at https://materialsproject.org (free account).

| Env Variable | Header |
|---|---|
| `MP_API_KEY` | `X-API-KEY: your_key_here` |

All requests must include the API key header.

## API Version

The current API is **v2** (based on the `mp-api` Python client and the new MAPI endpoints). The legacy v1 REST API at `https://www.materialsproject.org/rest/v2/` is deprecated.

## Key Endpoints

### Search materials by formula or elements

```
GET /materials/summary/?formula=Fe2O3&_fields=material_id,formula_pretty,band_gap,formation_energy_per_atom
```

```
GET /materials/summary/?elements=Si,O&_fields=material_id,formula_pretty,band_gap
```

Query parameters:
- `formula` — exact chemical formula (e.g., `Fe2O3`, `SiO2`)
- `chemsys` — chemical system, dash-separated (e.g., `Fe-O`, `Li-Fe-P-O`)
- `elements` — comma-separated elements that must be present
- `band_gap_min` / `band_gap_max` — filter by band gap (eV)
- `is_stable` — `true` to return only thermodynamically stable phases
- `_fields` — comma-separated list of fields to return
- `_limit` — max results (default 10, max 1000)
- `_skip` — offset for pagination

### Get material by ID

```
GET /materials/summary/mp-149?_fields=material_id,formula_pretty,band_gap,formation_energy_per_atom,symmetry
```

Material IDs have the format `mp-NNNNN` (e.g., `mp-149` for silicon).

### Available fields (summary)

`material_id`, `formula_pretty`, `formula_anonymous`, `chemsys`, `volume`, `density`, `density_atomic`, `symmetry`, `band_gap`, `cbm`, `vbm`, `is_gap_direct`, `is_metal`, `is_magnetic`, `ordering`, `total_magnetization`, `formation_energy_per_atom`, `energy_above_hull`, `is_stable`, `equilibrium_reaction_energy_per_atom`, `nsites`, `elements`, `nelements`, `composition`, `structure`

### Crystal structure

```
GET /materials/summary/mp-149?_fields=structure
```

Returns the structure as a pymatgen-compatible JSON dict with lattice parameters and atomic sites.

### Elastic properties

```
GET /materials/elasticity/?material_id=mp-149&_fields=material_id,bulk_modulus,shear_modulus,elastic_tensor
```

### Electronic structure (band structure / DOS)

```
GET /materials/electronic_structure/bandstructure/mp-149
GET /materials/electronic_structure/dos/mp-149
```

### Thermodynamic properties

```
GET /materials/thermo/?formula=Fe2O3&_fields=material_id,formation_energy_per_atom,energy_above_hull
```

### Example: Find stable oxides with band gap > 2 eV

```
GET /materials/summary/?elements=O&band_gap_min=2&is_stable=true&_fields=material_id,formula_pretty,band_gap,formation_energy_per_atom&_limit=10
```

## Response Format

```json
{
  "data": [
    {
      "material_id": "mp-149",
      "formula_pretty": "Si",
      "band_gap": 0.6105,
      "formation_energy_per_atom": 0.0
    }
  ],
  "meta": {
    "total_doc": 1
  }
}
```

## Rate Limits

- Authenticated: ~50 requests/minute (varies by server load)
- Batch requests preferred over many individual calls
- Use `_fields` to reduce payload size and improve performance
- The Python client `mp-api` handles pagination and retries automatically

## Error Format

```json
{
  "detail": "Not authenticated"
}
```

HTTP 401 = missing or invalid API key. HTTP 404 = material not found. HTTP 429 = rate limited.
