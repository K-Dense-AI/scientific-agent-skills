# Metabolomics Workbench REST API

## Base URL
```
https://www.metabolomicsworkbench.org/rest/
```

## Auth
No API key required. Fully public.

## URL Structure
```
/rest/{context}/{input_item}/{input_value}/{output_item}
```

Contexts: `study`, `compound`, `refmet`, `gene`, `protein`, `moverz`, `exactmass`

## Key Endpoints

### Study Context
| URL Pattern | Description |
|---|---|
| `/rest/study/study_id/{ST_ID}/summary` | Study summary metadata |
| `/rest/study/study_id/{ST_ID}/metabolites` | Metabolites in a study |
| `/rest/study/study_id/{ST_ID}/analysis` | Analysis details |
| `/rest/study/study_id/{ST_ID}/factors` | Experimental factors |
| `/rest/study/study_id/{ST_ID}/data` | Named metabolite data matrix |
| `/rest/study/study_id/{ST_ID}/species` | Species information |
| `/rest/study/study_id/{ST_ID}/disease` | Disease information |
| `/rest/study/study_title/{keyword}/summary` | Search studies by title keyword |
| `/rest/study/study_type/{type}/summary` | Search by study type |
| `/rest/study/analysis_id/{AN_ID}/summary` | Summary by analysis ID |

Study IDs: `ST######` (e.g., `ST000001`). Analysis IDs: `AN######`.

### Compound Context
| URL Pattern | Description |
|---|---|
| `/rest/compound/name/{NAME}/summary` | Search compound by name |
| `/rest/compound/pubchem_cid/{CID}/summary` | Search by PubChem CID |
| `/rest/compound/hmdb_id/{HMDB_ID}/summary` | Search by HMDB ID |
| `/rest/compound/kegg_id/{KEGG_ID}/summary` | Search by KEGG ID |
| `/rest/compound/inchi_key/{KEY}/summary` | Search by InChI key |
| `/rest/compound/regno/{REGNO}/classification` | Compound classification |
| `/rest/compound/regno/{REGNO}/molfile` | MOL file (structure) |

### RefMet (Standardized Nomenclature)
| URL Pattern | Description |
|---|---|
| `/rest/refmet/name/{NAME}/all` | Full RefMet record |
| `/rest/refmet/match/{NAME}/name` | Match name to standardized RefMet name |

### Gene / Protein Context
| URL Pattern | Description |
|---|---|
| `/rest/gene/gene_symbol/{SYMBOL}/all` | Gene info by symbol |
| `/rest/gene/gene_id/{ID}/all` | Gene info by Entrez ID |
| `/rest/protein/uniprot_id/{ID}/all` | Protein by UniProt ID |

### Mass Search (MoverZ / ExactMass)
```
/rest/moverz/mz/{MZ_VALUE}/tol/{TOLERANCE}/mode/{pos|neg}
/rest/exactmass/mass/{MASS_VALUE}/tol/{TOLERANCE}
```

## Example Calls

```
# Study summary
https://www.metabolomicsworkbench.org/rest/study/study_id/ST000001/summary

# Metabolites in a study
https://www.metabolomicsworkbench.org/rest/study/study_id/ST000001/metabolites

# Search studies by title
https://www.metabolomicsworkbench.org/rest/study/study_title/diabetes/summary

# Compound by name
https://www.metabolomicsworkbench.org/rest/compound/name/glucose/summary

# Compound by PubChem CID
https://www.metabolomicsworkbench.org/rest/compound/pubchem_cid/5793/summary

# RefMet standardized name match
https://www.metabolomicsworkbench.org/rest/refmet/match/alpha-D-Glucose/name

# m/z search in positive mode
https://www.metabolomicsworkbench.org/rest/moverz/mz/175.0354/tol/0.005/mode/pos

# Exact mass search
https://www.metabolomicsworkbench.org/rest/exactmass/mass/174.0282/tol/0.005
```

## Response Format
Default is JSON. `mwtab` output returns MWTab text. `molfile` returns MOL/SDF text. No pagination — full results returned.

## Rate Limits
No published limits. Be reasonable. Add 0.5-1s delay for batch calls.
