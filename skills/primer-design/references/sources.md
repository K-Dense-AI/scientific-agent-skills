# Sources and maintenance notes

Checked 2026-09-30. Links below are upstream documentation or primary publications.
Their availability does not imply that remote services, specialized assays, or
every API option were exercised by the bundled test suite.

## Executable design and analysis

- [Primer3 manual](https://primer3.org/manual.html): authoritative Boulder-IO design
  tags, coordinates, constraint semantics, and output definitions. Distinguish
  template binding length from products that include overhangs.
- [primer3-py documentation](https://libnano.github.io/primer3-py/): documentation
  currently identifies release 2.3.1 and links the Primer3 2.6.1 manual. Package and
  embedded engine versions are distinct; record both at runtime.
- [Primary Python API](https://libnano.github.io/primer3-py/api/bindings.html):
  `design_primers`, Tm/structure functions, physical parameters, and length limits.
- [Thermodynamic result API](https://libnano.github.io/primer3-py/api/thermoanalysis.html):
  result units, structure flags, and `get_libprimer3_version`.

## Reference specificity

- [NCBI Primer-BLAST](https://www.ncbi.nlm.nih.gov/tools/primer-blast/): current
  assay-design/specificity interface and field-level help.
- [NCBI search tips](https://www.ncbi.nlm.nih.gov/tools/primer-blast/search_tips.html):
  accession-based inputs, target assignment, and search interpretation.
- [Ye et al. (2012), Primer-BLAST](https://pmc.ncbi.nlm.nih.gov/articles/PMC3412702/):
  combined design, alignment, and amplicon-level specificity workflow.
- [BLAST+ nucleotide options](https://www.ncbi.nlm.nih.gov/sites/books/NBK279684/table/appendices.T.blastn_application_options/):
  short-query tasks and search settings. Consult the installed executable's help
  because the Bookshelf table also contains historical release information.

## Thermodynamic foundations

- [SantaLucia (1998)](https://pubmed.ncbi.nlm.nih.gov/9465037/): DNA nearest-neighbor
  parameter framework, DOI `10.1073/pnas.95.4.1460`.
- [Owczarzy et al. (2008)](https://pubmed.ncbi.nlm.nih.gov/18422348/): mixed-ion
  corrections, DOI `10.1021/bi702363u`.
- [Owczarzy et al. (2011)](https://pubmed.ncbi.nlm.nih.gov/21928795/): LNA-specific
  thermodynamics and mismatch behavior, DOI `10.1021/bi200904e`.

## Assay-specific evidence

- [Bustin et al. (2025), MIQE 2.0](https://academic.oup.com/clinchem/article/71/6/634/8119148):
  current qPCR assay reporting and validation guidance,
  DOI `10.1093/clinchem/hvaf043`.
- [NEB overlap-assembly primer guidance](https://www.neb.com/en-sg/tools-and-resources/video-library/primer-design-and-fragment-assembly-using-gibson-assembly?autoplay=1):
  connecting annealing regions to assembly overlaps.
- [Brown et al., PrimerPooler](https://pubmed.ncbi.nlm.nih.gov/32161789/): multiplex
  pool allocation; consult the linked erratum when reproducing published details.
- [Rose et al. (2003), CODEHOP](https://pubmed.ncbi.nlm.nih.gov/12824413/):
  protein-alignment-guided degenerate primers, DOI `10.1093/nar/gkg524`.
- [Li and Dahiya (2002), MethPrimer](https://pubmed.ncbi.nlm.nih.gov/12424112/):
  bisulfite-specific design constraints, DOI `10.1093/bioinformatics/18.11.1427`.
- [Tusnády et al. (2005), BiSearch](https://pubmed.ncbi.nlm.nih.gov/15653630/):
  converted-reference mispriming analysis, DOI `10.1093/nar/gni012`.

## When maintaining this skill

Check upstream parameter names, supported alphabets/lengths, concentrations, output
coordinates, and returned warnings before changing package pins. Re-run the
repository suite and documented examples. Test off-target products and negative
cases, not only whether a program returns primers. Preserve the distinction between
locally tested numerical behavior, external service documentation, and empirical
assay validation. A newer package or web interface does not justify upgrading old
assay claims without rerunning their evidence.
