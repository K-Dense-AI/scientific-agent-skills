# ZINC Database API

## Base URL

```
https://zinc.docking.org
```

## Auth

No API key required. Fully open public API.

## URL Pattern

Resources follow a uniform pattern with format specified by file extension:

```
/{resource}.{format}
/{resource}/{id}.{format}
/{resource}/subsets/{subset}.{format}
```

Supported formats: `.json`, `.csv`, `.txt`, `.smi`, `.sdf`, `.mol2`, `.xml`, `.png`

Field selection (return only specific fields):
```
/{resource}.json:field1+field2+field3
```

## Key Endpoints

### Substance lookup by ZINC ID
```
GET /substances/ZINC000000000053.json
```

### Search by name
```
GET /substances.json?preferred_name=aspirin
```

### Search by InChIKey
```
GET /substances.json?inchikey=BSYNRYMUTXBXSQ-UHFFFAOYSA-N
```

### Search by molecular formula
```
GET /substances.json?mol_formula=C9H8O4
```

### Substructure search (SMILES)
```
GET /substances.json?sub_id-matches=c1ccccc1&count=10
```

### Substructure search (SMARTS)
```
GET /substances.json?sub_id-matches-sma=[ND1]&count=10
```

### Similarity search (Tanimoto, ECFP4 fingerprints)

The threshold (e.g., 40 = 40%) is part of the parameter name. Value can be SMILES or a ZINC ID number.
```
GET /substances/?ecfp4_fp-tanimoto-40=c1ccccc1O
GET /substances/?ecfp4_fp-tanimoto-70=ZINC000000000053
```

### Browse subsets

Filter by purchasability, drug status, reactivity, or origin:
```
GET /substances/subsets/fda.json              # FDA-approved drugs
GET /substances/subsets/in-stock.json         # In-stock compounds
GET /substances/subsets/metabolites.json      # Metabolites
GET /substances/subsets/fda+in-stock.json     # Combine subsets with +
```

Key subsets:
- **Purchasability**: `in-stock`, `on-demand`, `for-sale`, `bb` (building blocks)
- **Drug status**: `fda`, `world`, `in-trials`, `in-man`, `in-vivo`, `in-vitro`
- **Origin**: `biogenic`, `metabolites`, `natural-products`, `endogenous`
- **Reactivity**: `anodyne`, `clean`, `standard`, `reactive`

### Substances for a gene target
```
GET /genes/ACHE/substances.json?count=10
```

### Catalogs
```
GET /catalogs.json                            # List all vendor catalogs
GET /catalogs/cmcd/substances.json            # Substances in a catalog
```

### 2D structure image (300x300 PNG)
```
GET /substances/ZINC000000000053.png
```

### Molecule format conversion
```
GET /apps/mol/convert?from=CC(=O)Oc1ccccc1C(=O)O&to=inchikey
```
Returns the InChIKey as plain text. Supports conversions between SMILES, InChI, and InChIKey.

### Batch resolution (POST)

Resolve multiple names, ZINC IDs, or SMILES at once:
```
POST /substances/resolved/
Content-Type: application/x-www-form-urlencoded

paste=aspirin%0Aibuprofen%0AZINC000000000053&identifiers=y&structures=y&names=y&output_format=json
```

## Query Parameters

### Pagination
- `count=N` — results per page (use `count=all` cautiously on large sets)
- `page=N` — page number (1-indexed)

### Sorting
- `sort=mwt` — ascending by field
- `sort=-mwt` — descending (prefix with `-`)
- `sort=no` — disable sorting for faster bulk queries

### Property filters (comparison operators)
- `mwt-le=500` — molecular weight <= 500
- `logp-ge=2` — LogP >= 2
- `hbd-le=5` — H-bond donors <= 5
- Operators: `-le` (<=), `-ge` (>=), `-lt` (<), `-gt` (>), `-eq` (=)

### Searchable substance attributes

Molecular properties: `mwt`, `logp`, `hba`, `hbd`, `tpsa`, `rb` (rotatable bonds), `num_rings`, `num_aromatic_rings`, `num_heavy_atoms`, `num_chiral_centers`, `fractioncsp3`

Identifiers: `zinc_id`, `smiles`, `inchikey`, `mol_formula`, `preferred_name`, `cas_numbers`

Status: `purchasable`, `reactive`, `bb` (building block)

## Example Calls

### Get properties for a compound
```
GET /substances/ZINC000000000053.json:zinc_id+smiles+mwt+logp+hba+hbd+tpsa+mol_formula+preferred_name
```

### FDA drugs sorted by molecular weight
```
GET /substances/subsets/fda.json:zinc_id+preferred_name+mwt?sort=mwt&count=10
```

### Drug-like compounds (Lipinski filters)
```
GET /substances/subsets/for-sale.json?mwt-le=500&logp-le=5&hbd-le=5&hba-le=10&count=20
```

### Find compounds targeting a specific gene
```
GET /genes/EGFR/substances.json:zinc_id+preferred_name+smiles?count=10
```

## Response Format

```json
[
  {
    "zinc_id": "ZINC000000000053",
    "smiles": "CC(=O)Oc1ccccc1C(=O)O",
    "preferred_name": "aspirin",
    "mwt": 180.159,
    "logp": 1.31,
    "hba": 3,
    "hbd": 1,
    "tpsa": 63,
    "mol_formula": "C9H8O4",
    "inchikey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
    "purchasable": 5
  }
]
```

Responses are JSON arrays. Single-record lookups (by ZINC ID) return a JSON object.

## Rate Limits

No documented rate limits. The API is publicly funded (NIH NIGMS GM71896). Be respectful:
- Use `count=` to limit result sizes
- Use `sort=no` for faster bulk queries
- Similarity and substructure searches are computationally expensive — expect slower responses
- Avoid `count=all` on large result sets

## Special Notes

- ZINC contains **2+ billion** commercially available compounds — always use `count=` to limit results
- ZINC IDs have the format `ZINC000000000053` (15-digit zero-padded after "ZINC")
- The `.smi` format returns SMILES strings, useful for cheminformatics pipelines
- The `.sdf` format returns 3D structures suitable for docking software
- Subsets can be combined with `+` (e.g., `fda+in-stock` = FDA-approved AND in-stock)
- For virtual screening workflows, use tranches (`/tranches/`) to partition by molecular weight and LogP
