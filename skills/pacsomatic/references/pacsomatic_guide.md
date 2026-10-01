# Upstream review and scientific interpretation

Reviewed 2026-10-01 against nf-core/pacsomatic development commit
`24c84cb371b0339c1d65a4de9451671945e19772`. No GitHub releases or tags existed
at review time; internal manifest `1.0.0` is not a published release. The manifest
requires Nextflow >=24.04.2 and pins nf-schema 2.3.0. Current Nextflow 26.04.6
was used only for a tiny local launcher smoke test, not the complete pipeline.

## Scientific boundaries

- Inputs are PacBio **HiFi** tumor/normal sequencing BAMs, usually unaligned.
  Upstream realigns with pbmm2, then sorts/indexes. Coordinate-sorted input and
  existing BAI/CSI are not requirements of this helper's raw-BAM workflow.
- Match patient/sample identity and provenance independently. Two different
  paths and labels do not establish a biological match or absence of cross-sample
  contamination. Record chemistry/instrument/read-quality and relevant read groups.
- PacBio PBI indexes store PacBio-specific per-read information; BAI/CSI index
  coordinate alignments. Check that an optional PBI is from the same BAM.
- Methylation needs suitable modification tags and the phasing branches; absence
  of MM/ML evidence must not become an inferred unmethylated result.
- FASTA, caller model, VEP species/assembly/cache, repeats, SV controls,
  gene annotations, heterozygous-site panel and GC profiles must agree with the
  intended assembly/contigs. `GRCh38` is an iGenomes key, not an exhaustive
  specification of all analysis resources. `hg38` and `GRCh38` are not blindly
  interchangeable resource names.
- Tumor purity, coverage, normal contamination, ploidy and calling thresholds
  affect sensitivity and false positives. Successful completion does not
  establish clinical validity, somatic truth or an interpretable HRD estimate.
- The paired workflow combines tumor/normal records by patient. The helper
  intentionally generates only one pair; multiple normals/tumors need an explicit
  pairing design, not duplicated rows that silently create extra combinations.

## Branch-specific configuration

Use the pinned parameter schema and source to choose resources/skips. In the
reviewed code, VEP needs `vep_assembly` and `vep_species`; clonality checks name
`heterozygous_sites`, `gc_profile`, and `ensembl_data_dir`; WES CNVkit needs
`cnv_target_bed`. Missing resources may warn, skip or fail downstream. Methylation
needs phasing, and signature/HRD branches depend on relevant SNV/SV results.
Do not present the minimal generated params YAML as sufficient for every branch.

Retain pipeline revision, Nextflow/Java versions, configs, actual container/tool
versions, BAM/reference/resource checksums, samplesheet and parameters. Upstream
loads nf-core/configs from a mutable branch by default; pin `custom_config_version`
in your params file for stronger reproducibility and review external assets.
The helper doesn't fetch or validate those resources or institutional credentials.

## Official sources checked

- [Pipeline usage](https://nf-co.re/pacsomatic/latest/docs/usage/)
- [Current parameters](https://nf-co.re/pacsomatic/latest/parameters/)
- [Output guide](https://nf-co.re/pacsomatic/latest/docs/output/)
- [Release listing](https://github.com/nf-core/pacsomatic/releases)
- [Pinned manifest and runtime profiles](https://github.com/nf-core/pacsomatic/blob/24c84cb371b0339c1d65a4de9451671945e19772/nextflow.config)
- [Pinned samplesheet schema](https://github.com/nf-core/pacsomatic/blob/24c84cb371b0339c1d65a4de9451671945e19772/assets/schema_input.json)
- [Pinned parameter schema](https://github.com/nf-core/pacsomatic/blob/24c84cb371b0339c1d65a4de9451671945e19772/nextflow_schema.json)
- [Pinned workflow and pairing](https://github.com/nf-core/pacsomatic/blob/24c84cb371b0339c1d65a4de9451671945e19772/workflows/pacsomatic.nf)
- [Pinned parameter/sample checks](https://github.com/nf-core/pacsomatic/blob/24c84cb371b0339c1d65a4de9451671945e19772/subworkflows/local/utils_pacsomatic_pipeline/main.nf)
- [Nextflow installation and Java compatibility](https://docs.seqera.io/nextflow/install)
- [Nextflow executor selection](https://docs.seqera.io/nextflow/executor)
- [Nextflow command line](https://docs.seqera.io/nextflow/cli)
- [Slurm sbatch](https://slurm.schedmd.com/sbatch.html)
- [Nextflow LSF memory conventions](https://docs.seqera.io/nextflow/executor/lsf)
- [Nextflow PBS Pro](https://docs.seqera.io/nextflow/executor/pbspro)
- [Nextflow SGE](https://docs.seqera.io/nextflow/executor/sge)
- [Sanger-specific profile](https://nf-co.re/configs/sanger/)
- [PacBio BAM metadata and modification tags](https://pacbiofileformats.readthedocs.io/en/13.0/BAM.html)
- [PacBio PBI specification](https://pacbiofileformats.readthedocs.io/en/13.0/PacBioBamIndex.html)
- [IBM LSF runtime limit](https://www.ibm.com/docs/en/spectrum-lsf/10.1.0?topic=o-w-1)
- [IBM LSF memory-unit examples](https://www.ibm.com/docs/en/spectrum-lsf/10.1.0?topic=o-r)

There is no PACS/DICOM API or hosted service client in this skill. Its network
interfaces are upstream Git/Nextflow fetches and remote input URIs; the helper
implements no HTTP request body, authentication, response or pagination contract.
Local artifacts/mocked submissions are tested separately from those external
services. No human genomic data, production scheduler or full pipeline was used.
