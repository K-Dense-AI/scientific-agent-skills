# PubChem PUG REST API

## Base URL

```
https://pubchem.ncbi.nlm.nih.gov/rest/pug
```

## URL Pattern

```
/{domain}/{namespace}/{identifiers}/{operation}/{output}
```

- **domain**: `compound`, `substance`, `assay`
- **namespace**: `cid`, `name`, `smiles`, `inchi`, `inchikey`, `fastformula`
- **operation**: `record`, `property`, `synonyms`, `description`, `cids`, `xrefs`
- **output**: `JSON`, `XML`, `CSV`, `TXT`, `SDF`, `PNG`

## Key Endpoints

### Search by name
```
GET /compound/name/{name}/JSON
```
Example: `/compound/name/aspirin/JSON`

### Search by CID
```
GET /compound/cid/{cid}/JSON
```
Example: `/compound/cid/2244/JSON`

Multiple CIDs: `/compound/cid/2244,5988,3672/JSON`

### Search by SMILES
```
GET /compound/smiles/{smiles}/JSON
```
For SMILES with special characters, use POST:
```
POST /compound/smiles/JSON
Content-Type: application/x-www-form-urlencoded
smiles=CC(=O)OC1=CC=CC=C1C(=O)O
```

### Search by InChIKey
```
GET /compound/inchikey/{inchikey}/JSON
```

### Search by InChI (POST only — InChI strings are too long for URLs)
```
POST /compound/inchi/JSON
Content-Type: application/x-www-form-urlencoded
inchi=InChI=1S/C9H8O4/...
```

### Search by molecular formula
```
GET /compound/fastformula/{formula}/JSON
```
Example: `/compound/fastformula/C9H8O4/JSON`

### Property retrieval
```
GET /compound/{namespace}/{id}/property/{property_list}/JSON
```
Properties are comma-separated. Available properties:

`MolecularFormula`, `MolecularWeight`, `CanonicalSMILES`, `IsomericSMILES`, `InChI`, `InChIKey`, `IUPACName`, `XLogP`, `ExactMass`, `MonoisotopicMass`, `TPSA`, `Complexity`, `Charge`, `HBondDonorCount`, `HBondAcceptorCount`, `RotatableBondCount`, `HeavyAtomCount`, `CID`

Example:
```
/compound/cid/2244/property/MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName/JSON
```

Response:
```json
{
  "PropertyTable": {
    "Properties": [
      {
        "CID": 2244,
        "MolecularFormula": "C9H8O4",
        "MolecularWeight": 180.16,
        "IUPACName": "2-acetyloxybenzoic acid",
        "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(O)=O"
      }
    ]
  }
}
```

### Synonym lookup
```
GET /compound/{namespace}/{id}/synonyms/JSON
```

### Compound description
```
GET /compound/cid/{cid}/description/JSON
```

### Get just CIDs from a name
```
GET /compound/name/{name}/cids/JSON
```

### Cross-references (patents, registry IDs)
```
GET /compound/cid/{cid}/xrefs/PatentID/JSON
GET /compound/cid/{cid}/xrefs/RegistryID/JSON
```

### Similarity search (POST, returns listkey for async retrieval)
```
POST /compound/fastsimilarity_2d/smiles/cids/JSON
smiles=CC(=O)OC1=CC=CC=C1C(=O)O&Threshold=90
```

### 2D structure image
```
GET /compound/cid/{cid}/PNG
GET /compound/cid/{cid}/PNG?image_size=300x300
```

## Rate Limits

- Max **5 requests per second**
- Max **400 requests per minute**
- Batch CIDs with commas (up to 100 per GET, ~10,000 per POST)
- Throttle error returns `PUGREST.ServerBusy` fault code

## Error Format

```json
{
  "Fault": {
    "Code": "PUGREST.NotFound",
    "Message": "No CID found",
    "Details": ["..."]
  }
}
```
