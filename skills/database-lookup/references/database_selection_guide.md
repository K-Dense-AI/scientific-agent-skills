# Database Selection Guide

Which database answers which question, grouped by domain: physics and astronomy, earth and
environmental sciences, chemistry and drugs, materials science and crystallography,
biology and genomics, disease and clinical, patents and regulatory, economics and finance,
social sciences and demographics, and cross-domain queries.

## Database Selection Guide

Match the user's intent to the right database(s). Many queries benefit from hitting multiple databases.

### Physics & Astronomy
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Near-Earth objects, asteroids | NASA (NeoWs) | — |
| Mars rover images | NASA (Mars Rover Photos) | — |
| Exoplanets, orbital parameters | NASA Exoplanet Archive | — |
| Astronomical objects by name/coordinates | SIMBAD | SDSS |
| Galaxy/star spectra, photometry | SDSS | SIMBAD |
| Physical constants | NIST | — |
| Atomic spectra, spectral lines | NIST (ASD) | — |

### Earth & Environmental Sciences
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Earthquakes, seismic events | USGS Earthquakes | — |
| Water data, streamflow, groundwater | USGS Water Services | — |
| Weather (current, forecast, historical) | OpenWeatherMap | NOAA |
| Climate data, historical weather stations | NOAA (CDO) | — |
| Air quality, toxic releases | EPA (Envirofacts) | — |

### Chemistry & Drugs
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Chemical compounds, molecules | PubChem | ChEMBL |
| Molecular properties (weight, formula, SMILES) | PubChem | — |
| Drug synonyms, CAS numbers | PubChem (synonyms) | DrugBank |
| Bioactivity data, IC50, binding assays | ChEMBL | BindingDB, PubChem |
| Drug binding affinities (Ki, IC50, Kd) | ChEMBL, BindingDB | PubChem |
| Drug-target interactions | ChEMBL, DrugBank | BindingDB, Open Targets |
| Ligands for a protein target (by UniProt) | BindingDB | ChEMBL |
| Target identification from compound structure | BindingDB (SMILES similarity) | ChEMBL |
| Drug labels, adverse events, recalls | FDA (OpenFDA) | DailyMed |
| Drug labels (structured product labels) | DailyMed | FDA (OpenFDA) |
| Drug pharmacology, indications | DrugBank | FDA |
| Chemical cross-referencing | PubChem (xrefs) | ChEMBL |
| Commercially available compounds for screening | ZINC | PubChem |
| Similarity/substructure search (purchasable) | ZINC | PubChem, ChEMBL |
| Drug-like compound libraries, building blocks | ZINC | — |
| FDA-approved drug structures | ZINC (fda subset) | PubChem, FDA |
| Compound purchasability, vendor catalogs | ZINC | — |

### Materials Science & Crystallography
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Materials by formula or elements | Materials Project | COD |
| Band gap, electronic structure | Materials Project | — |
| Crystal structures, CIF files | COD | Materials Project |
| Elastic/mechanical properties | Materials Project | — |
| Formation energy, thermodynamics | Materials Project | — |
| Cell parameters, space groups | COD | Materials Project |

### Biology & Genomics
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Biological pathways | Reactome, KEGG | — |
| What pathways a gene/protein is in | Reactome (mapping), KEGG | — |
| Enzyme kinetics, catalytic activity | BRENDA | KEGG |
| Metabolomics studies, metabolite profiles | Metabolomics Workbench | PubChem |
| m/z or exact mass lookup | Metabolomics Workbench (moverz/exactmass) | PubChem |
| Protein sequence, function, annotation | UniProt | Ensembl |
| Protein-protein interactions | STRING | BioGRID |
| Gene information, genomic location | NCBI Gene | Ensembl |
| Genome sequences, variants, transcripts | Ensembl | NCBI Gene |
| Gene expression datasets | GEO (NCBI E-utilities) | — |
| Gene expression across tissues | GTEx | Human Protein Atlas |
| Gene expression signatures (CMap/L1000) | LINCS L1000 | GEO |
| Gene set enrichment vs GEO | RummaGEO | GEO |
| Protein sequences (NCBI) | NCBI Protein | UniProt |
| Taxonomic classification | NCBI Taxonomy | — |
| SNP/variant data (dbSNP) | dbSNP | ClinVar, gnomAD |
| Population variant frequencies | gnomAD | dbSNP |
| Sequencing run metadata | SRA | ENA, GEO |
| Nucleotide sequences (European archive) | ENA | SRA, NCBI Gene |
| Genome assemblies, raw reads (European) | ENA | SRA, Ensembl |
| Cross-references from sequence accessions | ENA (xref) | NCBI Gene, UniProt |
| Viral sequence datasets with NCBI Virus-style filters | `gget virus` deterministic layer | SRA, ENA, NCBI Protein |
| Genome annotations, tracks | UCSC Genome Browser | Ensembl |
| 3D protein structures (experimental) | PDB (RCSB) | EMDB |
| 3D protein structures (predicted) | AlphaFold DB | PDB |
| EM maps, cryo-EM structures | EMDB | PDB |
| Protein families, domains | InterPro | UniProt |
| Chemical entities (biological) | ChEBI | PubChem |
| Protein/genetic interactions | BioGRID | STRING |
| Gene function annotations (GO terms) | QuickGO | Gene Ontology |
| Regulatory elements, ChIP-seq, ATAC-seq | ENCODE | — |
| TF binding profiles/motifs | JASPAR | ENCODE |
| Protein expression across tissues | Human Protein Atlas | UniProt |
| Single-cell atlas projects | Human Cell Atlas | — |
| Proteomics datasets | PRIDE | — |
| Mouse gene data | MouseMine | NCBI Gene |
| Plasmid repository | Addgene | — |

**Organism/species matters.** Most biology databases cover multiple organisms. If the user's query is about a specific organism, pass it explicitly — don't assume human. Common patterns: Ensembl uses `{species}` in the URL path (e.g. `homo_sapiens`), STRING/BioGRID/QuickGO use NCBI taxon IDs (`species=9606` for human, `10090` for mouse), UniProt uses `organism_id:9606` in search queries, KEGG uses organism codes (`hsa`, `mmu`). GTEx and Human Protein Atlas are human-only. Check the reference file for each database's specific parameter.

**Viral sequence retrieval is high risk.** For NCBI Virus-style requests with filters such as host, geography, collection dates, sequence length, completeness, ambiguous bases, segment, lab passage, source database, or protein annotation, prefer the `gget` skill's `gget virus` deterministic retrieval layer over hand-assembling browser or API workflows. If you must use SRA/ENA/NCBI APIs directly, document which filters were enforced server-side and which were validated locally, then reconcile final accession counts.

### Disease & Clinical
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Somatic mutations in cancer | COSMIC | Open Targets, cBioPortal |
| Cancer genomics (TCGA) | GDC (TCGA) | COSMIC, cBioPortal |
| Cancer study mutations, CNA, expression | cBioPortal | GDC (TCGA), COSMIC |
| Tumor clinical data (survival, staging) | cBioPortal | GDC (TCGA) |
| Drug-target-disease associations | Open Targets | ChEMBL |
| Gene-disease associations | DisGeNET | Open Targets, Monarch |
| Mendelian disease-gene relationships | OMIM | NCBI Gene |
| Variant clinical significance | ClinVar (NCBI) | OMIM |
| GWAS SNP-trait associations | GWAS Catalog | — |
| Disease-phenotype-gene links | Monarch Initiative | HPO |
| Phenotype ontology, HPO terms | HPO | Monarch |
| Pharmacogenomics, drug-gene interactions | ClinPGx (PharmGKB) | DrugBank |
| Clinical trials for a drug/disease | ClinicalTrials.gov | FDA |
| Disease-related expression data | GEO | Open Targets |

### Patents & Regulatory
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Patents by keyword or technology | USPTO ODP PatentsView bulk (PatentSearch API paused) | — |
| Patents by inventor or assignee | USPTO ODP PatentsView bulk (PatentSearch API paused) | — |
| Patent prosecution status | USPTO (PEDS) | — |
| Trademark lookup | USPTO (TSDR) | — |
| SEC company filings, 10-K, 10-Q | SEC EDGAR | — |

### Economics & Finance
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| US economic time series (GDP, CPI, rates) | FRED | BEA |
| Employment, wages, labor statistics | BLS | FRED |
| GDP, national accounts | BEA | FRED, World Bank |
| International development indicators | World Bank | FRED |
| Interest rates, money supply | Federal Reserve | FRED |
| Euro exchange rates, ECB monetary stats | ECB | — |
| US debt, yield curves, fiscal data | US Treasury | FRED |
| Stock prices, forex, crypto | Alpha Vantage | — |
| Statistical data across many topics | Data Commons | — |

### Social Sciences & Demographics
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| US population, housing, income data | US Census | Data Commons |
| EU statistics (economy, trade, health) | Eurostat | World Bank |
| Global health indicators (mortality, disease) | WHO GHO | World Bank |

### Cross-domain queries
| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Everything about a compound | PubChem + ChEMBL + DrugBank | BindingDB, ZINC, Reactome, FDA |
| Everything about a gene | NCBI Gene + UniProt + Ensembl | Reactome, STRING, COSMIC, cBioPortal, ENA |
| Everything about a variant | dbSNP + ClinVar + gnomAD | GWAS Catalog, COSMIC, cBioPortal |
| Drug target pathways | ChEMBL + Reactome | Open Targets, GEO |
| Prior art for a chemical invention | USPTO + PubChem | ChEMBL |
| Everything about a material | Materials Project + COD | — |
| US economic overview | FRED + BLS + BEA | Federal Reserve |

When the user's query spans multiple domains (e.g. "what do we know about aspirin" or "find everything about BRCA1"), rank sources by authority and start with the 2-3 databases most likely to answer the question. Add more databases only when the first pass leaves a specific gap. Keep at most 5 independent API requests in flight at once.
