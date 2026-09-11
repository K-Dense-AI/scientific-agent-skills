# RegulomeDB

Regulatory evidence for **noncoding** SNVs: ENCODE TF ChIP, DNase, motifs,
QTLs. Rank `1a` (strongest) through `7` (nothing overlapping). Neighbour of
`encode.md` and `jaspar.md`. Not a consequence scorer — for missense impact
use Ensembl VEP (`ensembl.md` §6, `CADD=1`).

Search: `https://regulomedb.org/regulome-search/`
Help: https://regulomedb.org/regulome-help/
All figures verified 2026-09-10.

## Request

```
GET /regulome-search/?regions={rsID|chr:start-end}&genome=GRCh38&format=json
```

`genome` is `GRCh38` (preferred) or `GRCh37`. Default format is HTML.

Coordinates are **0-based half-open**, same as BED. A single GRCh38 base
at 1-based position `P` is `chrN:{P-1}-{P}`.

## Verified calls

```
GET ...?regions=rs6983267&genome=GRCh38&format=json
```

`regulome_score.ranking` **1a**, `probability` **0.93**. This is the
example of a regulatory hit.

```
GET ...?regions=rs28934578&genome=GRCh38&format=json
GET ...?regions=chr17:7675087-7675088&genome=GRCh38&format=json
```

Both: ranking **4**, probability **0.60906**. A coding missense with rank
4 is "not what this database is for," not "benign regulatory."

```
GET ...?regions=chr17:7674220-7674220&genome=GRCh38&format=json
```

HTTP 200, `variants: []`, no `regulome_score.ranking`. Zero-width /
1-based same-number ranges miss the base.

```
POST /regulome-search/   with a JSON body
```

HTTP 200, `@id` `/regulome-notfound`, `@type` includes `regulome-help`.
The old POST API is dead. Use GET.

## Traps

- Convert 1-based VEP/CADD positions before building `regions=`.
- Read `regulome_score.ranking`, not a legacy `regulomedb_score` field.
- `probability` is a string.
- Region queries without an rsID return common SNPs (MAF > 1%) in the
  window, not every possible SNV.
- Rank 7 / missing ranking is "no annotated overlap," not a proof the
  variant does nothing.
