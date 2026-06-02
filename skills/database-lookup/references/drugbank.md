# DrugBank API

## Important: DrugBank's full API is commercial (paid license required)

**Free alternatives for drug data:**
- **ChEMBL** — extensive bioactivity data, free API
- **PubChem** — free compound data
- **OpenFDA** — drug labels, adverse events
- **DGIdb** (https://dgidb.org/api) — drug-gene interactions, free

## Base URL (Paid API)
```
https://api.drugbank.com/v1
```

## Auth
API key required: `Authorization: Bearer <api_key>`

## Key Endpoints (Paid API)

| Endpoint | Description |
|----------|-------------|
| `/drugs/{drugbank_id}` | Get drug by DrugBank ID |
| `/drugs?q={query}` | Search drugs |
| `/drugs/{id}/interactions` | Drug-drug interactions |
| `/drugs/{id}/targets` | Drug targets |
| `/drugs/{id}/enzymes` | Metabolizing enzymes |
| `/drugs/{id}/pathways` | Associated pathways |
| `/drugs/{id}/adverse_effects` | Adverse effects |
| `/drug_interactions?drugbank_id={id1},{id2}` | Check specific interactions |

## Example Calls
```
GET /drugs/DB00945  (aspirin)
GET /drugs?q=aspirin
GET /drugs/DB00945/interactions
GET /drugs/DB00945/targets
```

## Response Format
```json
{
  "drugbank_id": "DB00945",
  "name": "Acetylsalicylic acid",
  "cas_number": "50-78-2",
  "groups": ["approved"],
  "targets": [{"name": "Prostaglandin G/H synthase 1", "uniprot_id": "P23219", "gene_name": "PTGS1", "actions": ["inhibitor"]}],
  "external_ids": {"chembl": "CHEMBL25", "pubchem_compound": "2244"}
}
```

## Free Access Options
- **DrugBank Open Data**: ~2,500 FDA-approved drugs as XML/CSV download from https://go.drugbank.com/releases/latest
- **Academic License**: Free for non-commercial use, provides data downloads (not API)
