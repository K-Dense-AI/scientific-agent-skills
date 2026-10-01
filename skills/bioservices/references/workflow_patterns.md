# BioServices workflow patterns

These workflows target 1.16.0. Core public lookups were smoke-tested on
2026-09-30; BLAST submission and exhaustive organism-wide analyses remain
illustrative. Record the query, database release and retrieval date for every
export. See [service contracts](services_reference.md) for endpoint details.

## Protein characterization

1. Use a stable UniProt accession where possible. A broad free-text query can
   return multiple species, isoforms, fragments, or similarly named proteins.
2. Retrieve the entry JSON and FASTA. Use `primaryAccession` and
   `organism.taxonId` in downstream requests, and check the sequence header.
3. Map UniProt to KEGG using `results[*].from/to`, preserving all gene mappings.
   `get_pathway_by_gene` returns a dictionary of pathway IDs to names.
4. Retrieve QuickGO annotation JSON across every `pageInfo.total` page. Keep
   evidence and qualifiers in a raw export; separately summarize distinct terms.
5. Use STRING with the verified taxon for associations. Preserve evidence-channel
   scores and distinguish physical evidence from the default functional network.
6. Submit EMBL-EBI BLAST only if sequence comparison is needed and an actual
   contact address is available. Poll to a deadline; save the job ID and retrieve
   only after `FINISHED`.

```bash
python scripts/protein_analysis_workflow.py P43403 --skip-blast
# Optional job submission, illustrative (uses your real contact address):
export NCBI_EMAIL=you@lab.org
python scripts/protein_analysis_workflow.py P43403
```

The script reports console summaries. It is not a durable raw-data archive.
The QuickGO summary excludes NOT-qualified annotations and deduplicates GO IDs;
it must not be treated as an annotation evidence table or enrichment result.
The helper bounds pagination to 1,000 pages and rejects malformed or changing
page metadata instead of returning a partial summary. A pagination error requires
rerunning the query; the function returns no partial result.
The search fallback uses the first displayed hit, so pass a verified accession
for unattended work. PSICQUIC is absent in the targeted release.

## Annotation table with pandas and Biopython

```python
from io import StringIO
import pandas as pd
from Bio import SeqIO
from bioservices import UniProt

u = UniProt(verbose=False)
tsv = u.search("gene_exact:ZAP70 AND organism_id:9606 AND reviewed:true",
               frmt="tsv", columns="accession,gene_names,length,organism_name",
               size=5, limit=5)
if not isinstance(tsv, str):
    raise RuntimeError("Search failed")
table = pd.read_csv(StringIO(tsv), sep="\t")
print(table)
fasta = u.retrieve("P43403", frmt="fasta")
if not isinstance(fasta, str) or not fasta.startswith(">"):
    raise RuntimeError("Sequence retrieval failed")
record = SeqIO.read(StringIO(fasta), "fasta")
assert len(record.seq) > 0
print(record.id, len(record.seq))
```

`size=limit` avoids the 1.16.0 pagination mismatch for a bounded query. A query
that reaches its limit may be incomplete; preserve that fact in reports.

## KEGG pathway export

```bash
python scripts/pathway_analysis.py hsa output_directory/ --limit 2
```

The script produces a CSV summary, combined SIF, and per-pathway relation CSVs.
The summary labels are `Num_Entries` and `Num_Relation_Records`: entries include
compounds, groups, and linked maps; multiple subtypes expand one relation into
multiple rows. Counts summed across pathways are not counts of unique genes.
The combined SIF uses `pathway#local_entry_id`; look up biological identifiers
through the corresponding KGML entry `name`, retaining multi-gene/group semantics.

For a small inspection:

```python
from bioservices import KEGG
k = KEGG(verbose=False)
k.services.url = "https://rest.kegg.jp"
ids = [line.split("\t", 1)[0] for line in
       k.services.http_get("list/pathway/hsa", frmt="txt").splitlines()]
kgml = k.parse_kgml_pathway("hsa04660")
entries = {entry["id"]: entry for entry in kgml["entries"]}
for relation in kgml["relations"][:5]:
    print(relation["link"], relation["name"],
          entries[relation["entry1"]]["name"], entries[relation["entry2"]]["name"])
```

Some pathways lack KGML. Report skipped pathways instead of implying full
coverage. `pathway2sif(..., uniprot=False)` is a smaller activation/inhibition
projection; its output is not equivalent to all KGML relations.

## Compound identity before property joins

```bash
python scripts/compound_cross_reference.py Geldanamycin --output compound_report.txt
```

The script requires a unique exact KEGG name/synonym match, or a sole search hit. It retrieves the flat-file
entry and preserves all ChEBI cross-references. A unique ChEBI candidate can be
queried through UniChem; a unique resulting ChEMBL ID permits a molecule lookup.
The report retains unresolved ChEBI candidates. Its optional ChEBI/ChEMBL detail
lookups are console output, not a complete property archive.

Names and cross-references alone do not prove the intended stereochemistry or
salt form. Review structural identity before downstream scientific use. ChEBI
uses its REST API in 1.16.0; `getCompleteEntity` returns a dict-like entity with
legacy attribute aliases. ChEMBL's molecule properties and structures can be null.
A failed request must not become a claim that no chemical mapping exists.

## Batch mapping

```bash
python scripts/batch_id_converter.py ids.txt --from UniProtKB_AC-ID --to KEGG \
    --chunk-size 100 --delay 0.5 --save-failed -o mapping.csv
```

The input is one ID per line; blank lines and `#` comments are ignored. The
converter normalizes current UniProt response envelopes and produces one row per
unique source with semicolon-separated target IDs. `Success`, `Unmapped` and
`Failed` are different states. Individual retries after batch failure are bounded
by the input list; do not repeatedly rerun large failed batches during outages.
See [mapping guide](identifier_mapping.md) for target-record handling.

## Association network with stable identifiers

This small export pattern is illustrative; choose species and evidence settings
for the study, and record the STRING version before publication.

```python
from bioservices import STRING
import networkx as nx

client = STRING(verbose=False)
version = client.get_version()
rows = client.get_interactions(["P43403", "P06239", "O43561"], species=9606,
                               required_score=700, network_type="functional",
                               caller_identity="scientific-agent-skills-bioservices")
if not isinstance(rows, list):
    raise RuntimeError("STRING request failed")
network = nx.Graph()
for row in rows:
    network.add_edge(row["stringId_A"], row["stringId_B"], score=row["score"])
network.graph["string_version"] = str(version.get("string_version", "unknown"))
nx.write_gml(network, "protein_network.gml")
```

Do not substitute gene-name aliases for stable IDs when merging networks.
STRING scores are association confidence, not effect sizes; an undirected graph
cannot encode causal direction. An absent edge can reflect thresholds or coverage.

## Comparing organisms

Retrieve `/list/pathway/{organism}` through the KEGG transport and inspect
pathway names. The SDK's organism setter and `lookfor_pathway` depend on the
organism catalogue, which returned HTTP 400 in review. A missing keyword match does not establish biological
absence, and similarly named pathways are not evidence of orthology. Compare
explicit pathway/ortholog identifiers and annotation coverage before conclusions.

## Failures and provenance

BioServices may return `None`, integer-like HTTP errors, HTML, strings, lists or
dictionaries. Validate the expected shape before counting or parsing. Persist raw
responses and unresolved IDs separately from derived summaries when the work
will be reused. Configure the actual transport's timeout (`client.services.TIMEOUT`
for composed clients), preserve release information, and obey each provider's
rate and access rules. The STRING wrapper bypasses those shared controls in
1.16.0; its request timeout must be bounded by the surrounding application.
