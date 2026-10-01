# Identifier mapping with BioServices 1.16.0

Reviewed 2026-09-30. Resolve species and identifier namespace before mapping;
identical gene symbols across organisms are not equivalent entities.

## UniProt request and response

```python
from bioservices import UniProt
u = UniProt(verbose=False)
source, target = "UniProtKB_AC-ID", "KEGG"
if target not in u.valid_mapping.get(source, []):
    raise ValueError("Unsupported mapping pair")
response = u.mapping(fr=source, to=target, query="P43403,P04637")
if not isinstance(response, dict) or "results" not in response:
    raise RuntimeError("UniProt mapping did not complete")
by_source = {}
for row in response["results"]:
    by_source.setdefault(row["from"], []).append(row["to"])
print(by_source)
print("Explicitly unmapped:", response.get("failedIds", []))
```

The SDK submits form data to `https://rest.uniprot.org/idmapping/run`, gets a
`jobId`, polls `idmapping/status/{jobId}`, and follows result links. The response
is `results` plus optional `failedIds`. A live P43403 -> KEGG lookup returned
`{"from": "P43403", "to": "hsa:7535"}` within `results`. Do not call
`response.get("P43403")` or merge envelopes with `dict.update` across batches.

A reverse lookup uses `fr="KEGG", to="UniProtKB", query="hsa:7535"`. Its `to`
value is a full protein record; normalize with `row["to"]["primaryAccession"]`.
The source code `UniProtKB_AC-ID` is not a valid target. Alias `--to uniprot`
in the bundled converter becomes `UniProtKB`, while `--from uniprot` becomes
`UniProtKB_AC-ID`.

`u.valid_mapping` is populated from the live
[mapping catalogue](https://rest.uniprot.org/configure/idmapping/fields).
Its rules constrain allowed pairs; a database can be source-only or target-only.
Common current codes include KEGG, Ensembl, Ensembl_Protein,
Ensembl_Transcript, GeneID, RefSeq_Protein, RefSeq_Nucleotide, HGNC, PDB,
Reactome, STRING, and BioGRID. HGNC expects an HGNC identifier, not a bare symbol.
GO, Pfam, InterPro, PRIDE and PaxDb were **absent** from the reviewed mapping
catalogue; retrieve their cross-references or annotation fields from UniProt
records instead of inventing a mapping job.

```python
record = u.retrieve("P43403", frmt="json")
links = [item for item in record["uniProtKBCrossReferences"]
         if item["database"] in {"GO", "Pfam", "InterPro"}]
```

The service permits up to 100,000 input IDs per job; output/enrichment/filter
limits differ. Small chunks of 50–100 in the bundled converter are a workflow
choice, not the provider's maximum. `max_waiting_time` bounds the SDK wait and
may yield `None`. A `failedIds`-only completion can time out in 1.16.0 because
its loop expects `results`; classify that as unresolved, not proven absent.
For large jobs, use the provider's explicit job/status/details/results workflow
so the job ID can be retained and resumed.

[SDK mapping implementation](https://bioservices.readthedocs.io/en/main/_modules/bioservices/uniprot.html)
and [UniProt mapping help](https://www.uniprot.org/help/id_mapping) describe the
job contract. Search a symbol with `gene_exact:ZAP70 AND organism_id:9606` and
review all candidate accessions before conversion. Searching reviewed records
is useful when appropriate, but excludes unreviewed biology by design.

## Bundled batch converter

```bash
python scripts/batch_id_converter.py ids.txt --from UniProtKB_AC-ID --to KEGG -o mapping.csv
python scripts/batch_id_converter.py kegg_ids.txt --from KEGG --to UniProtKB --save-failed
```

`mapping_to_lists` normalizes current result rows, preserves distinct targets,
and extracts `primaryAccession`, `uniParcId`, or `id` from supported record
targets. Unknown record shapes fail explicitly. Its internal values are:

| Value | CSV status | Meaning |
| --- | --- | --- |
| Nonempty target list | Success | One or more returned mappings |
| `[]` | Unmapped | ID explicitly present in `failedIds` |
| `None` | Failed | Request failed, timed out, or omitted the ID |

`--save-failed` includes both Unmapped and Failed identifiers for later review.
The CSV preserves unique input IDs, not duplicate input row multiplicity. Never
report a mapping rate using only returned successful rows as the denominator.

## KEGG links

The REST API returns TSV for `/conv/{target}/{source}` and `/link/{target}/{source}`.
BioServices converts these to dictionaries, which can lose repeated source
keys. For one-to-many membership preserve the raw rows:

```python
from bioservices import KEGG
k = KEGG(verbose=False)
k.services.url = "https://rest.kegg.jp"
raw = k.services.http_get("link/pathway/hsa:7535", frmt="txt")
if not isinstance(raw, str):
    raise RuntimeError("KEGG links request failed")
pairs = [tuple(line.split("\t")) for line in raw.splitlines() if line]
```

`get_pathway_by_gene("7535", "hsa")` parses the PATHWAY section to a dictionary;
use `.items()`, not list slicing. To retrieve pathway genes, `k.parse(k.get(id))`
provides the `GENE` section; a hand-written loop can accidentally skip the first
GENE line. For a compound, preserve every DBLINKS ChEBI candidate. KEGG's PubChem
cross-reference uses a **SID**, not necessarily a CID.
[KEGG conversion/link semantics](https://www.kegg.jp/kegg/rest/keggapi.html).

## UniChem compound mapping

```python
from bioservices import UniChem
uc = UniChem(verbose=False)
response = uc.get_compounds("BSYNRYMUTXBXSQ-UHFFFAOYSA-N", "inchikey")
if not isinstance(response, dict) or "compounds" not in response:
    raise RuntimeError("UniChem lookup failed")
pairs = sorted({(source["shortName"], source["compoundId"])
                for match in response["compounds"]
                for source in match.get("sources", [])})
print(pairs)
```

The aspirin InChIKey and `("CHEBI:15365", "chebi")` queries yielded CHEMBL25
in review. `get_compounds` sends JSON to `/unichem/api/v1/compounds` with
`compound`, `type`, `sourceID`; it is a search POST, not an external mutation.
Discover supported names through `source_ids`; do not reuse historical numeric
source IDs or assume KEGG is accepted. Some legacy UniChem methods remain in the
SDK, but the examples here use the current API v1 route.

Mapping must preserve chemical identity. KEGG C00022, for example, links multiple
ChEBI forms; selecting the first can mix a neutral acid and an anion. The bundled
compound script leaves multiple KEGG search hits, multiple ChEBI forms, or
multiple ChEMBL mappings unresolved. Review salts, stereochemistry, protonation,
and connectivity before joining potency or physicochemical data.
[UniChem API](https://www.ebi.ac.uk/unichem/api/docs).
