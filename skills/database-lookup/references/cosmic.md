# COSMIC — Catalogue of Somatic Mutations in Cancer

Use the [official COSMIC site](https://cancer.sanger.ac.uk/cosmic) to search genes,
mutations, tissues and Cancer Gene Census records. Programmatic bulk access is
through the [licensed download service](https://cancer.sanger.ac.uk/cosmic/help/file_download).
A COSMIC account and acceptance of the applicable data licence are required;
commercial access has separate licensing terms.

Workflow:
1. Sign in through COSMIC and select the dataset, release and genome assembly.
2. Use the download instructions supplied for that release/account. If the
   service supplies a temporary signed URL, download it promptly and keep it
   out of logs and published artifacts.
3. Record the release, file name, checksum, assembly and selected columns.
4. Filter locally by gene, tissue or variant; preserve sample identifiers and
   distinguish mutation counts from numbers of tested samples.

No current public documentation was found supporting a generic
`/cosmic/api/v1` mutation-search API or a JWT `/auth/login` workflow. Those
recipes have been removed. Authenticated downloads were not executed during
this review; consult the signed-in official instructions for exact routes.

COSMIC catalogue inclusion is evidence of observation in a cancer sample, not
proof of driver status, pathogenicity or response to a drug.
