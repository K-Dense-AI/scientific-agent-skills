# BindingDB REST API

## Base URLs
```
https://bindingdb.org/rest/
https://bindingdb.org/axis2/services/BDBService/
```

## Auth
No API key required. Fully open and free.

## Response Format
Default is XML. Append `&response=application/json` to any endpoint for JSON.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/rest/getLigandsByUniprot` | Ligands for a single protein target |
| `/rest/getLigandsByUniprots` | Ligands for multiple protein targets |
| `/rest/getLigandsByPDBs` | Ligands by PDB structure IDs |
| `/rest/getTargetByCompound` | Targets for a compound (SMILES similarity) |

## Endpoint Details

### Get ligands for a single target
```
GET https://bindingdb.org/rest/getLigandsByUniprot?uniprot={UNIPROT_ID};{IC50_cutoff_nM}&response=application/json
```
- `uniprot` — UniProt ID followed by `;` and affinity cutoff in nM
- Returns monomerIDs, SMILES, affinity types (IC50, Ki, Kd), and values
- Returns empty string if UniProt ID not found

Example:
```
https://bindingdb.org/rest/getLigandsByUniprot?uniprot=P35355;100&response=application/json
```

### Get ligands for multiple targets
```
GET https://bindingdb.org/rest/getLigandsByUniprots?uniprot={IDs}&cutoff={nM}&response=application/json
```
- `uniprot` — Comma-separated UniProt IDs
- `cutoff` — Affinity cutoff in nM
- Returns empty string if no matching IDs

Example:
```
https://bindingdb.org/rest/getLigandsByUniprots?uniprot=P00176,P00183&cutoff=10000&response=application/json
```

### Get ligands by PDB structure
```
GET https://bindingdb.org/rest/getLigandsByPDBs?pdb={PDBs}&cutoff={nM}&identity={percent}&response=application/json
```
- `pdb` — Comma-separated PDB IDs
- `cutoff` — Affinity cutoff in nM
- `identity` — Sequence identity cutoff (percent, e.g. 92)

Example:
```
https://bindingdb.org/rest/getLigandsByPDBs?pdb=1Q0L,3ANM&cutoff=100&identity=92&response=application/json
```

### Find targets for a compound (similarity search)
```
GET https://bindingdb.org/rest/getTargetByCompound?smiles={SMILES}&cutoff={similarity}&response=application/json
```
- `smiles` — Compound SMILES (must be URL-encoded)
- `cutoff` — Tanimoto similarity cutoff (decimal, e.g. 0.85)
- Returns similar compounds with their protein targets and affinities

Example:
```
https://bindingdb.org/rest/getTargetByCompound?smiles=CCC%5BN%2B%5D%28C%29%28C%29CCn1nncc1COc1cc%28%3DO%29n%28C%29c2ccccc12&cutoff=0.85&response=application/json
```

## Rate Limits
No documented limit. Keep requests to ~1 per second as a courtesy.

## Notes
- The API surface is small (4 endpoints) but focused on binding affinity data
- For compound-name search, resolve to SMILES first via PubChem, then use `getTargetByCompound`
- For bulk data access, use downloadable TSV/SDF files from https://www.bindingdb.org/bind/chemsearch/marvin/Download.jsp
- Contains ~3.2M binding measurements for ~1.4M compounds and ~11.4K targets
