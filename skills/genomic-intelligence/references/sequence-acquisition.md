# Sequence acquisition and TSS coordinates

Acquire reference sequence by gene or genomic region, then submit it to GI.
Ensembl REST is public; GI REST prediction needs a key. `find_genes` is a
prediction tool, **not** a sequence acquisition tool.

## What the MCP acquisition tools actually retrieve

In reviewed `gi-mcp` 0.1.0a21, gene metadata first uses a bundled coordinate
catalog, then cached/live Ensembl lookup with stale-cache fallback. Sequence
bytes use cache, UCSC, Ensembl, then stale cache. The server may therefore answer
without a current Ensembl request. Record `meta.source`, `locus_source`,
`assembly`, `catalog_release`, and any stale indicators, along with `data.region`,
`strand`, and gene/transcript identifiers. Hosted HBB expression acquisition in
this review returned a catalog locus and cached GRCh38 bases; a 100-bp region
returned UCSC bases. Neither was a live Ensembl lookup.

The default human assembly is GRCh38. Use explicit Ensembl production names
for portable non-human requests (for example `mus_musculus`,
`drosophila_melanogaster`). Some aliases such as `human` and `mouse` are accepted;
the old blanket claim that `mouse` is rejected was incorrect. Do not silently
substitute assemblies: the GI VCF workflow separately targets GRCh37.

Reference acquisition does not incorporate a sample's variants or edits. Supply
validated local sequence for variant-bearing, synthetic or non-reference input.
The acquisition layer can admit broader IUPAC bases than the prediction API's
A/C/G/T/N alphabet. For raw-base input check before prediction and record any
deliberate masking; a handle-only preview cannot establish the whole alphabet.
For handles, surface any prediction-time alphabet failure and reacquire the
bases if a correction is needed rather than guessing from the preview.

## Direct Ensembl REST routes

| Purpose | Public GET route | Important parameters/result |
|---|---|---|
| Gene symbol | `/lookup/symbol/{species}/{symbol}` | `expand=1` includes transcripts; JSON contains gene coordinates, strand and assembly |
| Stable ID | `/lookup/id/{id}` | `expand=1` for gene transcripts; verify returned object type/species |
| Sequence region | `/sequence/region/{species}/{region}` | Region `11:5222473..5231670:-1`; request `Content-Type: text/plain` or FASTA and parse exactly one record |

Coordinates are **1-based, inclusive**; sequence length is `end - start + 1`.
A `strand=-1` region returns the reverse complement, so do not reverse it again.
Ensembl documents a 10-Mb region maximum; GI still accepts only up to 500,000 bp.
Use bounded HTTP timeouts, honor rate-limit responses, and validate status,
content type, alphabet and exact length before passing a response as DNA.
A successful HTML response is not sequence.

The [symbol lookup](https://rest.ensembl.org/documentation/info/symbol_lookup),
[ID lookup](https://rest.ensembl.org/documentation/info/lookup), and
[region sequence](https://rest.ensembl.org/documentation/info/sequence_region)
contracts were source-reviewed. Direct Ensembl documentation and sequence
probes returned HTTP 500 during this review; the equivalent hosted acquisition
checks succeeded through its cache/UCSC paths. Treat direct-network availability
as unverified, not a reason to claim the endpoint is retired.

## Expression: select a transcript, then size the flank from the model list

Every expression model admits the same input: at least 9,198 bp of gene-sense
sequence with the TSS at least 4,599 bp from each end, plus `tss_index` unless
the body is exactly 9,198 bp. What a model *reads* around `tss_index` differs:
a fixed-window model reads only `sequence[tss_index - 4599 : tss_index + 4599]`,
a long-context model reads tens of kb on each side. Each model publishes how
much to supply as `bio_spec.recommended_flank_bp`; read it at call time, because
new and longer-window models are added and become the default without notice.

**The flank F.** F is the largest `recommended_flank_bp` among the models
`GET /v1/tasks/expression/models` lists (public, no key), never below 4,599, and
with 2F within `request_max_bp`. One fetch at that F serves every listed model.
Fetch F bp before the TSS and F bp from the TSS onward, gene-sense, so the
**TSS base is at offset F**, and send `tss_index = F`. In 1-based genomic
coordinates that is `[tss - F, tss + F - 1]` on plus strand and
`[tss - F + 1, tss + F]` reverse-complemented (Ensembl `strand=-1`) on minus
strand; the asymmetry reverses with the strand. Fetching the plus-strand range
on a minus-strand gene puts the TSS at F - 1, still in range, so it returns a
confident `200` for the wrong window.

Use the intended transcript, or explicitly choose Ensembl's canonical transcript
from the expanded lookup. On plus strand its TSS is transcript start; on minus
strand it is transcript end. Gene-body boundaries can differ substantially and
are not a substitute. Canonical status is a reference convention, not evidence
that this transcript is active in the assayed cell type.

The MCP helper `fetch_gene_for_expression` sizes F from the model list itself
and records `tss_index` on the handle. It prefers a canonical transcript but
**falls back to the gene boundary if none is available**. Check
`data.tss_source == "canonical-transcript"` or resolve the intended transcript
yourself; a correct length alone does not establish correct TSS placement.

```python
import requests

FLOOR = 4599  # the contract's minimum flank; not a target

def expression_flank(base="https://api.genomicintelligence.ai"):
    """F: the largest listed recommended_flank_bp, >= 4599, 2F <= request_max_bp."""
    r = requests.get(f"{base}/v1/tasks/expression/models", timeout=30)
    r.raise_for_status()
    specs = [m.get("bio_spec") or {} for m in r.json()["models"]]
    flanks = [s["recommended_flank_bp"] for s in specs if s.get("recommended_flank_bp")]
    caps = [s["request_max_bp"] for s in specs if s.get("request_max_bp")]
    flank = max([FLOOR, *flanks])
    if caps:
        flank = min(flank, min(caps) // 2)
    return max(flank, FLOOR)

def expression_region(tss, strand, flank):
    """1-based inclusive genomic bounds with the gene-sense TSS at offset `flank`."""
    if not isinstance(tss, int) or isinstance(tss, bool) or tss < 1:
        raise ValueError("tss must be a positive 1-based integer")
    if isinstance(strand, bool) or strand not in (-1, 1):
        raise ValueError("strand must be +1 or -1")
    if not isinstance(flank, int) or flank < FLOOR:
        raise ValueError("flank must be an integer >= 4599")
    start, end = ((tss - flank, tss + flank - 1) if strand == 1
                  else (tss - flank + 1, tss + flank))
    if start < 1:
        raise ValueError("TSS flank extends before chromosome start")
    return start, end

# HBB minus-strand canonical TSS in the reviewed GRCh38 reference, at the
# 4,599 floor and at an illustrative larger F:
assert expression_region(5227071, -1, 4599) == (5222473, 5231670)
assert expression_region(5227071, -1, 20000) == (5207072, 5247071)
# After fetching with strand=-1 the TSS is at end - tss == flank.
```

Near a chromosome end, use the largest symmetric F that fits, down to 4,599,
and say so; a TSS closer than 4,599 bp to the end cannot be scored. Check the
returned length is exactly 2F (no silent truncation) and preserve the transcript
accession/version, assembly, fetch region and F. For a locus you did not cut
this way, compute `tss_index = tss - start` on plus strand or `end - tss` on
minus strand, after stripping sequence whitespace, and require
`4599 <= tss_index <= len(sequence) - 4599`. Direct expression does not pad or
find TSSs. Verify `meta.sequence_length`, `data.input.tss_index`, and that
`meta.task_specific_counts.scored_window` contains `tss_index`; its width is how
much the model read.

## Other tasks

Gene-body sequence is appropriate only when it includes the relevant regulatory
context. For promoter work fetch upstream/flanking sequence or a TSS-centered
region; an unflanked gene body can omit the promoter. For splice, keep transcript
orientation and sufficient locus context. For annotation and the composite,
plus-strand genomic input gives straightforward coordinate mapping while models
can find transcripts on both strands. Match the chosen model's organism and
context window (2,000/15,000/249/1,000 bp for current promoter/splice/enhancer/
chromatin defaults); a request above its admission floor can still be padded.
