# Biopython 1.88 review and verification

Reviewed 2026-09-30. The runnable examples target Biopython 1.88 on Python 3.13.
Python 3.10 remains accepted but its support is deprecated. The 1.88 release fixes
unsafe evaluation in the NEXUS parser; use this release when parsing external
NEXUS data. Sources: [release notes](https://github.com/biopython/biopython/blob/biopython-188/NEWS.rst)
and [removed APIs](https://github.com/biopython/biopython/blob/biopython-188/DEPRECATED.rst).

## Service contracts

The following were checked against official documentation and the installed
1.88 source. Entrez uses `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`.
The API key is optional; identify actual requests with a real email/tool.
`Entrez.read` expects supported NCBI XML in binary mode, not arbitrary XML, JSON,
or plain text. Database-specific response shapes differ.

| Route | Contract used by this skill |
| --- | --- |
| `einfo.fcgi` | No database gives `DbList`; `db` gives `DbInfo`, including fields and links. |
| `esearch.fcgi` | `db`, `term`, `retstart`, `retmax`; XML includes `Count`, `IdList`, and `QueryTranslation`. `usehistory=y` supplies `WebEnv`/`QueryKey`. |
| `esummary.fcgi` | `db` and IDs (or history); default PubMed XML summaries differ from `version=2.0` and other databases. PubChem example retrieves a summary, not chemical structure data. |
| `efetch.fcgi` | `db`, IDs or `WebEnv`/`query_key`, and explicit `rettype`/`retmode`. GenBank/FASTA and MEDLINE are text; Gene, Taxonomy and PubMed XML use `Entrez.read`. |
| `elink.fcgi` | `dbfrom`, `db`, source UIDs; a Python ID list preserves source-to-target mappings, while a comma-joined string merges links. Inspect `LinkSetDb`/`LinkName`; nucleotide-to-protein uses `nuccore_protein`. |
| `epost.fcgi` | POST of database IDs creates temporary history; parse `WebEnv`/`QueryKey`. This is a server-side operation and was not executed in the review. |
| `espell.fcgi` | `db`/`term`; parse `Query` and `CorrectedQuery`. |

Biopython chooses POST for sufficiently large Entrez requests. Its pacing is
process-local: shared API-key/IP limits need coordination across workers. PubMed
queries above 10,000 matches require a partition strategy or NCBI EDirect/bulk
access; history does not remove that cap. `egquery` is removed, despite some
older NCBI overview pages still listing it.

Sources: [Entrez API and return types](https://biopython.org/docs/latest/api/Bio.Entrez.html),
[released request implementation](https://github.com/biopython/biopython/blob/biopython-188/Bio/Entrez/__init__.py),
[NCBI PubMed limit notice](https://ncbiinsights.ncbi.nlm.nih.gov/2022/11/22/updated-pubmed-eutilities-live/),
and [NCBI link names](https://www.ncbi.nlm.nih.gov/entrez/query/static/entrezlinks.html).
The NCBI Bookshelf parameter page returned a browser challenge during review;
its HTTP 200 was not treated as successful documentation retrieval.

BLAST uses `https://blast.ncbi.nlm.nih.gov/Blast.cgi`, `CMD=Put` then `CMD=Get`
with a RID. Current documented `XML2_S` returns one XML document; `XML2` can be
zipped. `NCBIWWW.qblast` returns text, while the newer `Bio.Blast.qblast` returns
binary data. NCBI can replace `nt` with `core_nt`; preserve the returned database
and search metadata. Entrez API keys do not grant BLAST throughput. See the
[URL API](https://blast.ncbi.nlm.nih.gov/doc/blast-help/urlapi.html),
[usage limits](https://blast.ncbi.nlm.nih.gov/doc/blast-help/developerinfo.html),
and [XML parser API](https://biopython.org/docs/latest/api/Bio.Blast.NCBIXML.html).

PDB retrieval uses the current `PDBList` HTTPS archive path, with `file_format="mmCif"`
for mmCIF; do not infer the downloaded filename. A live 1CRN retrieval and parse
returned one model and 46 residues. This verifies one public structure download,
not obsolete entries or the full archive. See [PDBList](https://biopython.org/docs/latest/api/Bio.PDB.PDBList.html).

## Executed checks and limits

- Repository `tests/biopython/test_examples.py`: 23 checks passed with 1.88,
  including compression, annotation-aware reverse complement, aligner scoring,
  motifs, GenePop parsing, strand-aware segments/promoter candidates, tree
  construction/copy/collapse/rooted RF, atom transforms, same-chain ligand
  contacts, and element-specific mass handling.
- Entrez route/body/history serialization and BLAST XML2 request handling were
  checked with mocked transport. No authenticated Entrez calls, EPost operation,
  public BLAST search jobs, or large downloads were executed.
- A released upstream BLAST XML2 fixture parsed as one query with 11 hits using
  `NCBIXML`. Local BLAST+ 2.17.0+ built a tiny database and returned the expected
  240-base exact match in XML, standard tabular, and custom tabular formats.
- `python tests/run_all.py --isolated biopython` and `skills-ref validate` passed.
  Examples depending on user files remain templates, not universal analyses.
- MUSCLE 5, Clustal Omega, and DSSP executables were absent. Those command examples
  are illustrative; MUSCLE flags were checked against its
  [official manual](https://www.drive5.com/muscle5/manual/cmd_align.html).
  The Clustal website could not be retrieved, so its command was not reverified
  against a current upstream manual. DSSP key iteration was checked against its
  [current API](https://biopython.org/docs/latest/api/Bio.PDB.DSSP.html).

## Local API sources

- [SeqIO compression and conversion](https://biopython.org/docs/latest/Tutorial/chapter_seqio.html)
- [SeqRecord slicing/reverse complement](https://biopython.org/docs/latest/api/Bio.SeqRecord.html)
- [SeqFeature locations and strand](https://biopython.org/docs/latest/api/Bio.SeqFeature.html)
- [Current aligner gap names](https://biopython.org/docs/latest/Tutorial/chapter_pairwise.html)
- [Tree manipulation](https://biopython.org/docs/latest/api/Bio.Phylo.BaseTree.html) and
  [distance matrices](https://biopython.org/docs/latest/api/Bio.Phylo.TreeConstruction.html)
- [Structure analysis](https://biopython.org/docs/latest/Tutorial/chapter_pdb.html)
- [SeqUtils](https://biopython.org/docs/latest/api/Bio.SeqUtils.html),
  [ProtParam implementation](https://github.com/biopython/biopython/blob/biopython-188/Bio/SeqUtils/ProtParam.py),
  and [motifs](https://biopython.org/docs/latest/Tutorial/chapter_motifs.html)
