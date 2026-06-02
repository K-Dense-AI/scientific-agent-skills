# AlphaFold DB (Predicted Protein Structures)

## Base URL
```
https://alphafold.ebi.ac.uk/api/
```

## Auth
No auth required.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/prediction/{uniprot_accession}` | Prediction metadata by UniProt ID |

## Structure File URLs (direct download)
```
https://alphafold.ebi.ac.uk/files/AF-{UNIPROT}-F1-model_v4.pdb
https://alphafold.ebi.ac.uk/files/AF-{UNIPROT}-F1-model_v4.cif
https://alphafold.ebi.ac.uk/files/AF-{UNIPROT}-F1-predicted_aligned_error_v4.json
```

## Example Calls
```
# Get prediction metadata for EGFR
https://alphafold.ebi.ac.uk/api/prediction/P00533

# Download PDB structure
https://alphafold.ebi.ac.uk/files/AF-P00533-F1-model_v4.pdb

# Download PAE (predicted aligned error)
https://alphafold.ebi.ac.uk/files/AF-P00533-F1-predicted_aligned_error_v4.json
```

## Response Format
JSON for metadata. PDB/mmCIF for structures. PAE as JSON matrix.

## Rate Limits
No strict limits. Use FTP/Cloud for bulk downloads (~200M+ structures).
