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

## Expression: select a transcript, then build the window

Expression scores one half-open slice
`sequence[tss_index - 4599 : tss_index + 4599]`. In a 9,198-bp gene-sense
window the **TSS base is at offset 4,599**: 4,599 upstream bases, the TSS base,
and 4,598 downstream bases. Its asymmetry reverses in genomic coordinates.

Use the intended transcript, or explicitly choose Ensembl's canonical transcript
from the expanded lookup. On plus strand its TSS is transcript start; on minus
strand it is transcript end. Gene-body boundaries can differ substantially and
are not a substitute. Canonical status is a reference convention, not evidence
that this transcript is active in the assayed cell type.

The MCP helper prefers a canonical transcript but **falls back to the gene
boundary if none is available**. Check `data.tss_source == "canonical-transcript"`
or resolve the intended transcript yourself; an exact 9,198-bp length alone
does not establish correct TSS placement.

```python
def expression_region(tss, strand):
    """Return 1-based inclusive genomic bounds with gene-sense TSS offset 4599."""
    if not isinstance(tss, int) or isinstance(tss, bool) or tss < 1:
        raise ValueError("tss must be a positive 1-based integer")
    if isinstance(strand, bool) or strand not in (-1, 1):
        raise ValueError("strand must be +1 or -1")
    start, end = ((tss - 4599, tss + 4598) if strand == 1
                  else (tss - 4598, tss + 4599))
    if start < 1:
        raise ValueError("TSS window extends before chromosome start")
    return start, end

# HBB minus-strand canonical TSS in the reviewed GRCh38 reference:
assert expression_region(5227071, -1) == (5222473, 5231670)
# After fetching with strand=-1, 5231670 - 4599 == 5227071.
```

Also reject a chromosome-end truncation: check the returned length is exactly
9,198 and preserve the transcript accession/version, assembly and fetch region.
For a wider gene-sense locus, compute `tss_index = tss - start` on plus strand
or `end - tss` on minus strand, after stripping sequence whitespace. Require
`4599 <= tss_index <= len(sequence) - 4599`. Direct expression does not pad or
find TSSs. Verify `meta.sequence_length`, `data.input.tss_index`, and
`meta.task_specific_counts.scored_window` against those expected values.

## Other tasks

Gene-body sequence is appropriate only when it includes the relevant regulatory
context. For promoter work fetch upstream/flanking sequence or a TSS-centered
region; an unflanked gene body can omit the promoter. For splice, keep transcript
orientation and sufficient locus context. For annotation and the composite,
plus-strand genomic input gives straightforward coordinate mapping while models
can find transcripts on both strands. Match the chosen model's organism and
context window (2,000/15,000/249/1,000 bp for current promoter/splice/enhancer/
chromatin defaults); a request above its admission floor can still be padded.
