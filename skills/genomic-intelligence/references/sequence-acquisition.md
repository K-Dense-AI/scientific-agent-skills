# Sequence Acquisition (Ensembl)

Turn a **gene symbol** or a **genomic region** into reference sequence so users
don't have to bring a FASTA. Ensembl REST (`rest.ensembl.org`) is **public — no
key**; only the *prediction* step needs a key (and only over REST).

On MCP, the acquisition tools (`fetch_ensembl_sequence`, `fetch_region`,
`fetch_gene_for_expression`, `find_genes`) do this for you and return a handle.
Over REST, query Ensembl yourself, then feed the sequence to `/v1/tasks/...`.

## Modes

- **Full gene body** (any task except expression) — resolve the gene, fetch its
  sequence.
- **Coordinate range** — fetch `/sequence/region/{species}/{region}`.
- **Exact 9,198 bp TSS-centred window** (expression only) — see below.

## TSS-centring (why expression is special)

The expression model requires **exactly 9,198 bp centred on the transcription
start site (TSS)**. You cannot reliably build this from gene-body coordinates:
the annotated gene start/end can sit far from the real TSS (HBB's gene end is
2,324 bp from its canonical TSS; ACTB's is 33,301 bp). Mis-centring tanks the
prediction.

The correct construction: resolve the gene's **canonical transcript** (Ensembl
`expand=1`), take the TSS from it (transcript start on the + strand, end on the −
strand), and take **4,599 bp upstream + 4,598 bp downstream on the gene's
strand = 9,198 bp**; validate the length exactly. On MCP,
`fetch_gene_for_expression(gene=...)` does all of this. Because it needs a
transcript, it works from a **gene**, not a bare region.

## Species & assembly

- **Default: human, GRCh38.**
- Non-human: use the Ensembl **production name** — lowercase, underscored:
  `mus_musculus`, `drosophila_melanogaster`, `saccharomyces_cerevisiae`. `mouse`
  / `Drosophila` will be rejected.
- The **enhancer** default (DeepSTARR) is *Drosophila* — match species to model
  (see `tasks.md`).

## When to skip acquisition

Supply sequence directly when it is **not** reference genome — variant-bearing,
edited, synthetic, or from a non-Ensembl assembly. Acquisition only returns
reference sequence for the requested coordinates.

## Limits

Bounded by the task's own cap (500,000 bp for most; exactly 9,198 bp for
expression). Ensembl enforces its own per-request size limits; fetch very large
ranges in pieces.
