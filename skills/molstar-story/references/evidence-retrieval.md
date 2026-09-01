# Evidence Retrieval And Selection

Use this route when the user supplies a scientific question, protein, ligand,
variant, state, or phenomenon but not a frozen and already accepted evidence
package. Search precedes Story planning because the available evidence can
change both the comparison and the claim.

## Resolve The Entity First

Establish the exact protein or molecular entity before searching structures:

- canonical accession and entry name;
- organism and isoform or construct;
- family/domain identity and relevant numbering system;
- ligand, partner, variant, or experimental-state terminology in the question.

Use UniProt as the default protein identity anchor. Preserve ambiguity when a
name maps to multiple species, paralogs, or isoforms; do not merge them into one
candidate set.

## Route By Evidence Need

Query only sources that can change the decision. Prefer structured APIs for the
candidate census, then inspect original entry records and primary publications
for shortlisted evidence.

| Need | Authoritative route | Use and boundary |
|---|---|---|
| Protein identity, sequence, domains, database cross-references | [UniProt REST API](https://www.uniprot.org/help/api_queries), for example `https://rest.uniprot.org/uniprotkb/{accession}.json` | Identity anchor and candidate links; a PDB cross-reference does not establish state or comparability. |
| Experimental structure census, text/sequence/3D similarity | [RCSB Search API](https://search.rcsb.org/) | Generate the candidate universe; search rank is not scientific rank. |
| Entry, entity, assembly, citation, method, resolution, mutation and sequence metadata | [RCSB Data API](https://data.rcsb.org/) | Verify shortlisted structures and exact polymer entities. Never infer active/inactive state from title alone. |
| GPCR state, preferred chain, ligand function and signalling partner | [GPCRdb web services](https://docs.gpcrdb.org/web_services.html), especially `https://gpcrdb.org/services/structure/` | Domain-specific annotation for GPCR candidates; verify decisive claims against the entry and original paper. |
| Independent entry, assembly, compound, experiment and validation metadata | [PDBe API](https://www.ebi.ac.uk/pdbe/api/doc/) | Cross-check shortlisted PDB metadata and expose conflicts rather than silently choosing one source. |
| Primary publication identity and accessible abstract/full text | [Europe PMC REST API](https://europepmc.org/RestfulWebService) | Recover what the authors actually reported. Citation metadata without text does not authorize a reported mechanistic or quantitative claim. |
| Cryo-EM map, fitted model and map metadata | [EMDB API](https://www.ebi.ac.uk/emdb/api/) | Required when density support or model-to-map fit is part of the question. |
| PDB ligand identity and chemistry | [RCSB Chemical Component Dictionary](https://www.rcsb.org/ligand) or PDBe compound endpoints | Confirm component identity, synonyms, covalent links and stereochemistry; a three-letter code alone can be ambiguous. |

Use a domain-specific source when it carries semantics absent from the general
archive, such as GPCR generic numbering/state or curated variant annotation.
Keep the general archive and original publication in the evidence chain.

## Build A Candidate Structure Matrix

Create a TSV, CSV, or JSON matrix before selecting primary structures. Include
the fields material to the question, not every database field. For a state or
ligand comparison, normally capture:

| Field | Why it matters |
|---|---|
| Protein accession, species, entity and chain | Prevent paralog/species/entity mixing. |
| State and how it was assigned | Distinguish curated annotation, author claim, and inference. |
| Ligand identity/function and covalency | Apo, agonist, antagonist and inhibitor are not interchangeable. |
| Partner or transducer | A G protein, nanobody or arrestin can stabilize the compared state. |
| Construct, mutations, fusion, truncation and PTM | Expose engineered differences that can mimic motion. |
| Assembly and relevant chain coverage | Ensure the biological object and moving regions are actually present. |
| Method, resolution/confidence and model quality | Judge whether the measurement is supported. |
| Primary citation and source identifiers | Make every selected fact recoverable. |
| Exclusion or unresolved reason | Keep missing evidence visible. |

Apply hard comparability gates first, then use explicit Pareto reasoning among
survivors. Do not hide the choice in an invented weighted score. Choose one
primary comparison for the question, preserve decision-relevant supplements or
counterexamples, and record why plausible alternatives were not primary.

Resolution alone never wins over wrong state, mismatched protein, absent moving
segments, or a confounded construct. Conversely, a familiar historical PDB is
not preferred when a better-supported comparable structure exists.

## Let Retrieval Reframe The Story

Search can invalidate the user's requested comparison. Examples:

- no comparable experimental apo structure exists;
- the apparent holo structure is antagonist-bound and inactive;
- the active structure requires a transducer absent from the reference;
- a candidate omits the helix, loop, ligand, or map needed for the claim;
- reported state labels conflict across sources.

In that case, state the failed premise and choose the strongest answerable
question, such as inactive antagonist-bound versus agonist/transducer-bound,
rather than fabricating an apo/holo story. Ask the user only when multiple
scientifically distinct reframings remain equally plausible and materially
change the requested decision.

## Separate Evidence Origins

Every quantitative or mechanistic statement must be one of:

1. **retrieved fact** — identity, state annotation, ligand, method, assembly, or
   another fact obtained from a named source;
2. **reported analysis** — a conclusion or measurement explicitly present in a
   primary publication or accepted report;
3. **computed analysis** — a locally reproduced mapping, alignment, contact,
   displacement, geometry, confidence, or density result.

Do not silently turn a database annotation into an author-reported mechanism or
present a local calculation as a published value. Reuse a reported quantitative
result when its definition and structures match; otherwise recompute and explain
the mismatch.

## Track Mechanism Edges And Gaps

For a mechanism question, a flat claim list is insufficient. Write the directed
chain that the Story is expected to explain, then assign evidence to every
material edge. Each edge should record:

- `from` and `to` states, sites, geometries or functional events;
- the strongest requested wording and the strongest wording allowed by current
  evidence;
- required evidence type and actual retrieved/reported/computed evidence IDs;
- status as `evidenced`, `gap`, or `not-applicable`;
- alternative explanations or construct/condition confounders.

Static endpoint structures can establish occupancy, spatial compatibility,
steric incompatibility under a declared overlay, and correlation between frozen
geometries. They do not by themselves establish that a displacement *causes*,
*enables*, is *required for*, or is *necessary for* binding or function. Reserve
those terms for matching reported functional/perturbation evidence or a locally
computed analysis whose contract genuinely tests the claim. Otherwise use
bounded wording such as “the outward state geometrically accommodates the
partner tail” and record the causal or necessity edge as a gap.

Continue retrieval or computation when a missing edge is essential to the user
question. If suitable evidence is unavailable, keep the gap in the coverage
ledger and final scene rather than silently shortening the question to the
available structures.

## Preserve The Evidence Chain

Write a project-local evidence snapshot and selection record before structural
computation. A minimal claim ledger can use this shape:

```json
{
  "evidence": [
    {
      "id": "E03",
      "kind": "computed_analysis",
      "source": "derived/comparison_metrics.json",
      "statement": "TM6 mean endpoint displacement is 3.35 A"
    }
  ],
  "claims": [
    {
      "id": "C04",
      "statement": "The endpoint difference is concentrated at cytoplasmic TM6",
      "evidence_ids": ["E03"],
      "scene_ids": ["motion", "decision"]
    }
  ]
}
```

Record retrieval time, query or endpoint, identifiers, local artifact paths,
selection/exclusion reasons, and unresolved fields. Bundle the final ledger with
the trusted Story source and show claim/evidence IDs in major scene descriptions.
The required chain is:

`source -> evidence -> analysis -> claim -> scene`.

The Story may summarize this chain, but it must not become the only copy of the
retrieval or analysis truth.
