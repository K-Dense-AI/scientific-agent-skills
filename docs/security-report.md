# Security Scan Report

**Generated:** 2026-10-26 09:35 UTC  
**Skills scanned:** 177  
**Total findings:** 471  
**Critical:** 32 | **High:** 21 | **Safe skills:** 159/177

**Scanner:** cisco-ai-skill-scanner 2.3.1 · **Model:** claude-opus-5  
**This run:** full rescan of all 177 skill(s).  

## Summary

| Skill | Severity | Findings | Safe | Duration |
|-------|----------|----------|------|----------|
| autoskill | 🔴 CRITICAL | 5 | ❌ | 22.2s |
| citation-management | 🔴 CRITICAL | 6 | ❌ | 38.8s |
| infographics | 🔴 CRITICAL | 3 | ❌ | 21.8s |
| latex-posters | 🔴 CRITICAL | 6 | ❌ | 27.2s |
| literature-review | 🔴 CRITICAL | 3 | ❌ | 25.7s |
| open-notebook | 🔴 CRITICAL | 3 | ❌ | 15.9s |
| research-lookup | 🔴 CRITICAL | 4 | ❌ | 19.0s |
| scientific-schematics | 🔴 CRITICAL | 3 | ❌ | 16.1s |
| scientific-slides | 🔴 CRITICAL | 4 | ❌ | 32.4s |
| esm | 🟠 HIGH | 4 | ❌ | 13.6s |
| geomaster | 🟠 HIGH | 3 | ❌ | 11.1s |
| hugging-science | 🟠 HIGH | 1 | ❌ | 12.1s |
| modal | 🟠 HIGH | 8 | ❌ | 20.9s |
| pytorch-lightning | 🟠 HIGH | 1 | ❌ | 15.4s |
| torch-geometric | 🟠 HIGH | 4 | ❌ | 16.4s |
| transformers | 🟠 HIGH | 1 | ❌ | 14.1s |
| torchdrug | 🟠 HIGH | 4 | ❌ | 16.7s |
| waypoint-bio | 🟠 HIGH | 2 | ❌ | 30.2s |
| biopython | 🟡 MEDIUM | 6 | ✅ | 12.5s |
| dnanexus-integration | 🟡 MEDIUM | 1 | ✅ | 14.4s |
| genomic-intelligence | 🟡 MEDIUM | 2 | ✅ | 7.2s |
| glycoengineering | 🟡 MEDIUM | 2 | ✅ | 8.3s |
| paperclip | 🟡 MEDIUM | 1 | ✅ | 16.1s |
| bioservices | 🔵 LOW | 1 | ✅ | 16.6s |
| diffdock | 🔵 LOW | 1 | ✅ | 12.3s |
| etetoolkit | 🔵 LOW | 1 | ✅ | 22.7s |
| genomic-coordinates | 🔵 LOW | 1 | ✅ | 15.3s |
| histolab | 🔵 LOW | 1 | ✅ | 11.9s |
| gtars | 🔵 LOW | 1 | ✅ | 16.2s |
| medchem | 🔵 LOW | 1 | ✅ | 13.4s |
| nextflow | 🔵 LOW | 2 | ✅ | 19.9s |
| matlab | 🔵 LOW | 1 | ✅ | 40.5s |
| opentrons-integration | 🔵 LOW | 1 | ✅ | 17.8s |
| paperzilla | 🔵 LOW | 1 | ✅ | 20.6s |
| polars | 🔵 LOW | 1 | ✅ | 14.8s |
| pyopenms | 🔵 LOW | 1 | ✅ | 17.0s |
| pyzotero | 🔵 LOW | 1 | ✅ | 20.8s |
| usfiscaldata | 🔵 LOW | 1 | ✅ | 17.9s |
| ncats-arax | ⚪ INFO | 1 | ✅ | 13.7s |
| analytical-method-validation | 🟢 SAFE | 0 | ✅ | 12.6s |
| arbor | 🟢 SAFE | 0 | ✅ | 14.7s |
| alphagenome | 🟢 SAFE | 0 | ✅ | 14.7s |
| arboreto | 🟢 SAFE | 0 | ✅ | 16.1s |
| 13c-metabolic-flux | 🟢 SAFE | 0 | ✅ | 16.8s |
| adaptyv | 🟢 SAFE | 0 | ✅ | 18.6s |
| aeon | 🟢 SAFE | 0 | ✅ | 21.0s |
| bgpt-paper-search | 🟢 SAFE | 0 | ✅ | 5.4s |
| bids | 🟢 SAFE | 0 | ✅ | 6.4s |
| anndata | 🟢 SAFE | 0 | ✅ | 24.4s |
| benchling-integration | 🟢 SAFE | 0 | ✅ | 11.8s |
| astropy | 🟢 SAFE | 0 | ✅ | 17.6s |
| bulk-rnaseq | 🟢 SAFE | 0 | ✅ | 8.3s |
| cantera | 🟢 SAFE | 0 | ✅ | 8.0s |
| cellprofiler | 🟢 SAFE | 0 | ✅ | 7.8s |
| cellxgene-census | 🟢 SAFE | 0 | ✅ | 7.8s |
| clinical-reports | 🟢 SAFE | 0 | ✅ | 10.6s |
| consciousness-council | 🟢 SAFE | 0 | ✅ | 7.0s |
| clinical-decision-support | 🟢 SAFE | 0 | ✅ | 12.7s |
| cirq | 🟢 SAFE | 0 | ✅ | 13.6s |
| dask | 🟢 SAFE | 0 | ✅ | 7.8s |
| cobrapy | 🟢 SAFE | 0 | ✅ | 16.9s |
| datalad | 🟢 SAFE | 0 | ✅ | 7.3s |
| datamol | 🟢 SAFE | 0 | ✅ | 8.7s |
| deepspot-m | 🟢 SAFE | 0 | ✅ | 7.7s |
| deepchem | 🟢 SAFE | 0 | ✅ | 10.2s |
| dhdna-profiler | 🟢 SAFE | 0 | ✅ | 5.7s |
| deeptools | 🟢 SAFE | 0 | ✅ | 10.3s |
| depmap | 🟢 SAFE | 0 | ✅ | 7.8s |
| database-lookup | 🟢 SAFE | 0 | ✅ | 23.1s |
| exa-search | 🟢 SAFE | 0 | ✅ | 7.4s |
| experimental-design | 🟢 SAFE | 0 | ✅ | 10.7s |
| exploratory-data-analysis | 🟢 SAFE | 0 | ✅ | 8.7s |
| flowkit | 🟢 SAFE | 0 | ✅ | 8.1s |
| fictiv | 🟢 SAFE | 0 | ✅ | 12.2s |
| folklore-variant-evidence | 🟢 SAFE | 0 | ✅ | 7.0s |
| flowio | 🟢 SAFE | 0 | ✅ | 12.5s |
| geniml | 🟢 SAFE | 0 | ✅ | 12.7s |
| generate-image | 🟢 SAFE | 0 | ✅ | 14.2s |
| geopandas | 🟢 SAFE | 0 | ✅ | 9.6s |
| fluidsim | 🟢 SAFE | 0 | ✅ | 20.0s |
| get-available-resources | 🟢 SAFE | 0 | ✅ | 14.4s |
| ginkgo-cloud-lab | 🟢 SAFE | 0 | ✅ | 12.4s |
| gget | 🟢 SAFE | 0 | ✅ | 17.9s |
| hypogenic | 🟢 SAFE | 0 | ✅ | 13.9s |
| imaging-data-commons | 🟢 SAFE | 0 | ✅ | 11.6s |
| hypothesis-generation | 🟢 SAFE | 0 | ✅ | 15.5s |
| iso-standards-readiness | 🟢 SAFE | 0 | ✅ | 12.3s |
| lab-hardware-cad | 🟢 SAFE | 0 | ✅ | 14.5s |
| latchbio-integration | 🟢 SAFE | 0 | ✅ | 11.3s |
| labarchive-integration | 🟢 SAFE | 0 | ✅ | 15.1s |
| lamindb | 🟢 SAFE | 0 | ✅ | 14.6s |
| liteparse | 🟢 SAFE | 0 | ✅ | 8.7s |
| marine-carbonate-chemistry | 🟢 SAFE | 0 | ✅ | 6.9s |
| mageck | 🟢 SAFE | 0 | ✅ | 8.4s |
| markitdown | 🟢 SAFE | 0 | ✅ | 8.4s |
| markdown-mermaid-writing | 🟢 SAFE | 0 | ✅ | 12.3s |
| market-research-reports | 🟢 SAFE | 0 | ✅ | 13.8s |
| matchms | 🟢 SAFE | 0 | ✅ | 13.3s |
| matplotlib | 🟢 SAFE | 0 | ✅ | 12.8s |
| molecular-dynamics | 🟢 SAFE | 0 | ✅ | 7.6s |
| networkx | 🟢 SAFE | 0 | ✅ | 7.3s |
| molfeat | 🟢 SAFE | 0 | ✅ | 15.0s |
| nmrglue | 🟢 SAFE | 0 | ✅ | 6.7s |
| nwb-conversion | 🟢 SAFE | 0 | ✅ | 10.4s |
| omero-integration | 🟢 SAFE | 0 | ✅ | 11.6s |
| onekgpd | 🟢 SAFE | 0 | ✅ | 9.6s |
| neuropixels-analysis | 🟢 SAFE | 0 | ✅ | 21.5s |
| ontology-term-resolution | 🟢 SAFE | 0 | ✅ | 11.3s |
| neurokit2 | 🟢 SAFE | 0 | ✅ | 28.2s |
| openpiv | 🟢 SAFE | 0 | ✅ | 8.0s |
| pacsomatic | 🟢 SAFE | 0 | ✅ | 9.6s |
| optimize-for-gpu | 🟢 SAFE | 0 | ✅ | 13.0s |
| paper-lookup | 🟢 SAFE | 0 | ✅ | 14.5s |
| pathml | 🟢 SAFE | 0 | ✅ | 10.7s |
| pennylane | 🟢 SAFE | 0 | ✅ | 8.4s |
| pathway-enrichment | 🟢 SAFE | 0 | ✅ | 13.4s |
| peer-review | 🟢 SAFE | 0 | ✅ | 9.5s |
| parallel-web | 🟢 SAFE | 0 | ✅ | 20.0s |
| pathogen-variant-surveillance | 🟢 SAFE | 0 | ✅ | 14.2s |
| phylogenetics | 🟢 SAFE | 0 | ✅ | 7.3s |
| polars-bio | 🟢 SAFE | 0 | ✅ | 9.4s |
| primer-design | 🟢 SAFE | 0 | ✅ | 9.9s |
| pkpd-modeling | 🟢 SAFE | 0 | ✅ | 11.3s |
| protocolsio-integration | 🟢 SAFE | 0 | ✅ | 10.3s |
| primekg | 🟢 SAFE | 0 | ✅ | 11.7s |
| pycalphad | 🟢 SAFE | 0 | ✅ | 6.8s |
| pi-agent | 🟢 SAFE | 0 | ✅ | 24.9s |
| pybamm | 🟢 SAFE | 0 | ✅ | 9.7s |
| pydeseq2 | 🟢 SAFE | 0 | ✅ | 13.4s |
| pylabrobot | 🟢 SAFE | 0 | ✅ | 11.1s |
| pymatgen | 🟢 SAFE | 0 | ✅ | 10.1s |
| pyhealth | 🟢 SAFE | 0 | ✅ | 21.8s |
| pymoo | 🟢 SAFE | 0 | ✅ | 13.1s |
| pufferlib | 🟢 SAFE | 0 | ✅ | 30.1s |
| pptx-posters | 🟢 SAFE | 0 | ✅ | 39.7s |
| pysam | 🟢 SAFE | 0 | ✅ | 11.5s |
| pymc | 🟢 SAFE | 0 | ✅ | 22.2s |
| pydicom | 🟢 SAFE | 0 | ✅ | 35.4s |
| qutip | 🟢 SAFE | 0 | ✅ | 9.8s |
| qiskit | 🟢 SAFE | 0 | ✅ | 11.3s |
| rdkit | 🟢 SAFE | 0 | ✅ | 8.3s |
| relion | 🟢 SAFE | 0 | ✅ | 7.8s |
| qiime2-amplicon | 🟢 SAFE | 0 | ✅ | 15.6s |
| pytdc | 🟢 SAFE | 0 | ✅ | 20.6s |
| rowan | 🟢 SAFE | 0 | ✅ | 6.5s |
| relsa-severity-assessment | 🟢 SAFE | 0 | ✅ | 9.9s |
| research-grants | 🟢 SAFE | 0 | ✅ | 12.5s |
| scanpy | 🟢 SAFE | 0 | ✅ | 13.0s |
| scientific-brainstorming | 🟢 SAFE | 0 | ✅ | 11.3s |
| scientific-critical-thinking | 🟢 SAFE | 0 | ✅ | 10.1s |
| scholar-evaluation | 🟢 SAFE | 0 | ✅ | 18.9s |
| scientific-visualization | 🟢 SAFE | 0 | ✅ | 10.3s |
| scikit-bio | 🟢 SAFE | 0 | ✅ | 12.1s |
| scvelo | 🟢 SAFE | 0 | ✅ | 6.6s |
| scikit-survival | 🟢 SAFE | 0 | ✅ | 11.5s |
| seaborn | 🟢 SAFE | 0 | ✅ | 9.7s |
| scvi-tools | 🟢 SAFE | 0 | ✅ | 13.0s |
| scikit-learn | 🟢 SAFE | 0 | ✅ | 19.3s |
| shap | 🟢 SAFE | 0 | ✅ | 10.1s |
| stable-baselines3 | 🟢 SAFE | 0 | ✅ | 10.0s |
| statistical-analysis | 🟢 SAFE | 0 | ✅ | 8.0s |
| scientific-writing | 🟢 SAFE | 0 | ✅ | 28.2s |
| statistical-power | 🟢 SAFE | 0 | ✅ | 8.5s |
| simpy | 🟢 SAFE | 0 | ✅ | 17.8s |
| tiledbvcf | 🟢 SAFE | 0 | ✅ | 6.4s |
| tellurium | 🟢 SAFE | 0 | ✅ | 7.3s |
| tamarind | 🟢 SAFE | 0 | ✅ | 8.5s |
| statsmodels | 🟢 SAFE | 0 | ✅ | 12.8s |
| umap-learn | 🟢 SAFE | 0 | ✅ | 5.9s |
| timesfm-forecasting | 🟢 SAFE | 0 | ✅ | 12.5s |
| sympy | 🟢 SAFE | 0 | ✅ | 20.0s |
| treatment-plans | 🟢 SAFE | 0 | ✅ | 12.2s |
| what-if-oracle | 🟢 SAFE | 0 | ✅ | 4.5s |
| vaex | 🟢 SAFE | 0 | ✅ | 11.1s |
| uncertainty-and-units | 🟢 SAFE | 0 | ✅ | 19.0s |
| zarr-python | 🟢 SAFE | 0 | ✅ | 17.8s |
| venue-templates | 🟢 SAFE | 0 | ✅ | 38.2s |

## Detailed Findings

### autoskill — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 3 files
  > Environment variable access with network calls in scripts/backends.py, scripts/doctor.py, scripts/run.py
  > **Remediation:** Review data flow across files: scripts/backends.py, scripts/doctor.py, scripts/run.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 3 files
  > Multi-file exfiltration chain detected: scripts/backends.py, scripts/doctor.py, scripts/run.py collect data → scripts/run.py → scripts/backends.py, scripts/doctor.py, scripts/run.py transmit to network
  > **Remediation:** Review data flow across files: scripts/backends.py, scripts/doctor.py, scripts/run.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/autoskill/scripts/backends.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/autoskill/scripts/backends.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/autoskill/scripts/doctor.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/autoskill/scripts/doctor.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/autoskill/scripts/run.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/autoskill/scripts/run.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

### citation-management — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 5 files
  > Environment variable access with network calls in scripts/extract_metadata.py, scripts/search_openalex.py, scripts/search_pubmed.py
  > **Remediation:** Review data flow across files: scripts/doi_to_bibtex.py, scripts/validate_citations.py, scripts/search_pubmed.py, scripts/extract_metadata.py, scripts/search_openalex.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 5 files
  > Multi-file exfiltration chain detected: scripts/extract_metadata.py, scripts/search_openalex.py, scripts/search_pubmed.py collect data → encode → scripts/doi_to_bibtex.py, scripts/validate_citations.py, scripts/extract_metadata.py, scripts/search_openalex.py, scripts/search_pubmed.py transmit to network
  > **Remediation:** Review data flow across files: scripts/doi_to_bibtex.py, scripts/validate_citations.py, scripts/search_pubmed.py, scripts/extract_metadata.py, scripts/search_openalex.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/citation-management/scripts/extract_metadata.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/citation-management/scripts/extract_metadata.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/citation-management/scripts/search_openalex.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/citation-management/scripts/search_openalex.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/citation-management/scripts/search_pubmed.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/citation-management/scripts/search_pubmed.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/core_workflow.md at line 193 contains potentially dangerous Python code.
  > File: `references/core_workflow.md:193`
  > **Remediation:** Review the code block for security implications.

### infographics — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 2 files
  > Environment variable access with network calls in scripts/generate_infographic.py, scripts/generate_infographic_ai.py
  > **Remediation:** Review data flow across files: scripts/generate_infographic.py, scripts/generate_infographic_ai.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 2 files
  > Multi-file exfiltration chain detected: scripts/generate_infographic.py, scripts/generate_infographic_ai.py collect data → scripts/generate_infographic_ai.py → scripts/generate_infographic_ai.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_infographic.py, scripts/generate_infographic_ai.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/infographics/scripts/generate_infographic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/infographics/scripts/generate_infographic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

### latex-posters — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 2 files
  > Environment variable access with network calls in scripts/generate_schematic_ai.py, scripts/generate_schematic.py
  > **Remediation:** Review data flow across files: scripts/generate_schematic.py, scripts/generate_schematic_ai.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 2 files
  > Multi-file exfiltration chain detected: scripts/generate_schematic_ai.py, scripts/generate_schematic.py collect data → scripts/generate_schematic_ai.py → scripts/generate_schematic_ai.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_schematic.py, scripts/generate_schematic_ai.py

- **🔵 LOW** `LLM_DATA_EXFILTRATION` — Credential resolution from .env files forwarded to declared OpenRouter endpoint
  > Deterministic analyzers flagged an environment-variable exfiltration chain in the schematic helpers. Verification of the source shows the OPENROUTER_API_KEY is resolved from --api-key, the environment, or a project .env (walking up parent directories) and then used only as a Bearer Authorization header against the declared https://openrouter.ai/api/v1 endpoints, which the manifest and documentation explicitly declare as the skill's optional AI-schematic capability. The key is never placed in a request body, logged, or sent to any undeclared host; error strings are redacted and the subprocess environment is explicitly minimized rather than copying all parent variables. The only residual risk is the upward .env directory walk, which may pick up a credential from an unrelated parent project directory; this is credential-scope breadth, not exfiltration to a suspicious destination.
  > **Remediation:** Limit the .env search to the project root or the skill directory rather than walking all ancestor directories, and document the search order so users understand which credential file may be consumed.

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/latex-posters/scripts/generate_schematic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/latex-posters/scripts/generate_schematic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🔵 LOW** `LLM_COMMAND_INJECTION` — User-supplied PDF path interpolated into Poppler invocations in preflight script
  > The behavioral analyzer reported a bash taint flow at scripts/review_poster.sh. Review of the script shows the single positional argument is assigned to POSTER_FILE and passed to pdfinfo/pdffonts/pdfimages. The value is consistently double-quoted, a leading dash is neutralized by prefixing './', and existence is checked before use, so no shell metacharacter execution path is established. The script is read-only, performs no network access, and does not modify the PDF. This is retained only as a low contextual risk because the argument originates outside the script.
  > File: `scripts/review_poster.sh`
  > **Remediation:** No change strictly required; optionally use '--' separators before the filename argument for all Poppler invocations to further harden option parsing.

- **🟡 MEDIUM** `BEHAVIOR_BASH_TAINT_FLOW` — Bash: tainted data flows to dangerous sink
  > Variable $FILE_SIZE_BYTES (line 63) flows to `sh` at line 64.
  > File: `scripts/review_poster.sh:64`
  > **Remediation:** Review the data flow from source to sink. Avoid sending sensitive or untrusted data to network or execution commands.

### literature-review — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 3 files
  > Environment variable access with network calls in scripts/generate_schematic_ai.py, scripts/generate_schematic.py
  > **Remediation:** Review data flow across files: scripts/generate_schematic.py, scripts/generate_schematic_ai.py, scripts/verify_citations.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 3 files
  > Multi-file exfiltration chain detected: scripts/generate_schematic_ai.py, scripts/generate_schematic.py collect data → scripts/generate_schematic_ai.py → scripts/generate_schematic_ai.py, scripts/verify_citations.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_schematic.py, scripts/generate_schematic_ai.py, scripts/verify_citations.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/literature-review/scripts/generate_schematic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/literature-review/scripts/generate_schematic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

### open-notebook — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 1 files
  > Environment variable access with network calls in scripts/_common.py
  > **Remediation:** Review data flow across files: scripts/_common.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 1 files
  > Multi-file exfiltration chain detected: scripts/_common.py collect data → encode → scripts/_common.py transmit to network
  > **Remediation:** Review data flow across files: scripts/_common.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/open-notebook/scripts/_common.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/open-notebook/scripts/_common.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

### research-lookup — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 1 files
  > Environment variable access with network calls in scripts/research_lookup.py
  > **Remediation:** Review data flow across files: scripts/research_lookup.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 2 files
  > Multi-file exfiltration chain detected: scripts/research_lookup.py collect data → scripts/manuscript_packet.py → scripts/research_lookup.py transmit to network
  > **Remediation:** Review data flow across files: scripts/research_lookup.py, scripts/manuscript_packet.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/research-lookup/scripts/research_lookup.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/research-lookup/scripts/research_lookup.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🔵 LOW** `LLM_DATA_EXFILTRATION` — Environment-variable API keys used in outbound HTTP requests (declared, intended service auth)
  > Deterministic analyzers flagged an env-var-to-network chain. Verification against the source shows the only environment variables read are PARALLEL_API_KEY and OPENROUTER_API_KEY, both declared in the manifest's openclaw envVars block and in SKILL.md. They are used strictly as authentication headers ('x-api-key' to https://api.parallel.ai/v1beta/chat/completions and 'Authorization: Bearer' to https://openrouter.ai/api/v1/chat/completions), which are the documented services the skill exists to call. No credential is placed in a request body, written to disk, logged, or sent to an undeclared destination; SKILL.md explicitly instructs never to print, log, or pass keys as arguments. The OpenRouter path is opt-in only (--force-backend perplexity or --fallback-perplexity) and the code comments confirm key presence alone does not enable provider switching. This is normal credential use for the intended service, so the deterministic CRITICAL rating is not supported; retained only as a contextual note that a second-party destination (OpenRouter) can receive query text when the user explicitly enables it.
  > File: `SKILL.md`
  > **Remediation:** No change required. Optionally keep the existing user-facing disclosure that query text is transmitted to OpenRouter only when Perplexity is explicitly selected or the fallback flag is set.

### scientific-schematics — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 2 files
  > Environment variable access with network calls in scripts/generate_schematic_ai.py, scripts/generate_schematic.py
  > **Remediation:** Review data flow across files: scripts/generate_schematic.py, scripts/generate_schematic_ai.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 2 files
  > Multi-file exfiltration chain detected: scripts/generate_schematic_ai.py, scripts/generate_schematic.py collect data → scripts/generate_schematic_ai.py → scripts/generate_schematic_ai.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_schematic.py, scripts/generate_schematic_ai.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-schematics/scripts/generate_schematic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-schematics/scripts/generate_schematic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

### scientific-slides — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 4 files
  > Environment variable access with network calls in scripts/generate_schematic_ai.py, scripts/generate_slide_image.py, scripts/generate_slide_image_ai.py, scripts/generate_schematic.py
  > **Remediation:** Review data flow across files: scripts/generate_slide_image_ai.py, scripts/generate_schematic_ai.py, scripts/generate_schematic.py, scripts/generate_slide_image.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 4 files
  > Multi-file exfiltration chain detected: scripts/generate_schematic_ai.py, scripts/generate_slide_image.py, scripts/generate_slide_image_ai.py, scripts/generate_schematic.py collect data → scripts/generate_schematic_ai.py, scripts/generate_slide_image_ai.py → scripts/generate_schematic_ai.py, scripts/generate_slide_image_ai.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_slide_image_ai.py, scripts/generate_schematic_ai.py, scripts/generate_schematic.py, scripts/generate_slide_image.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-slides/scripts/generate_schematic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-slides/scripts/generate_schematic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-slides/scripts/generate_slide_image_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-slides/scripts/generate_slide_image_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

### esm — 🟠 HIGH

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in SKILL.md at line 109 contains potentially dangerous Python code.
  > File: `SKILL.md:109`
  > **Remediation:** Review the code block for security implications.

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/biohub-platform.md at line 77 contains potentially dangerous Python code.
  > File: `references/biohub-platform.md:77`
  > **Remediation:** Review the code block for security implications.

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/esm-c-api.md at line 15 contains potentially dangerous Python code.
  > File: `references/esm-c-api.md:15`
  > **Remediation:** Review the code block for security implications.

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/esm-c-api.md at line 68 contains potentially dangerous Python code.
  > File: `references/esm-c-api.md:68`
  > **Remediation:** Review the code block for security implications.

### geomaster — 🟠 HIGH

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/data-sources.md at line 106 contains potentially dangerous Python code.
  > File: `references/data-sources.md:106`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/gis-software.md at line 262 contains potentially dangerous Python code.
  > File: `references/gis-software.md:262`
  > **Remediation:** Review the code block for security implications.

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/machine-learning.md at line 154 contains potentially dangerous Python code.
  > File: `references/machine-learning.md:154`
  > **Remediation:** Review the code block for security implications.

### hugging-science — 🟠 HIGH

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/using-models.md at line 42 contains potentially dangerous Python code.
  > File: `references/using-models.md:42`
  > **Remediation:** Review the code block for security implications.

### modal — 🟠 HIGH

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in SKILL.md at line 352 contains potentially dangerous Python code.
  > File: `SKILL.md:352`
  > **Remediation:** Review the code block for security implications.

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/api_reference.md at line 137 contains potentially dangerous Python code.
  > File: `references/api_reference.md:137`
  > **Remediation:** Review the code block for security implications.

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/functions.md at line 101 contains potentially dangerous Python code.
  > File: `references/functions.md:101`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/gpu.md at line 161 contains potentially dangerous Python code.
  > File: `references/gpu.md:161`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/gpu.md at line 181 contains potentially dangerous Python code.
  > File: `references/gpu.md:181`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/gpu.md at line 192 contains potentially dangerous Python code.
  > File: `references/gpu.md:192`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/scheduled-jobs.md at line 150 contains potentially dangerous Python code.
  > File: `references/scheduled-jobs.md:150`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/web-endpoints.md at line 168 contains potentially dangerous Python code.
  > File: `references/web-endpoints.md:168`
  > **Remediation:** Review the code block for security implications.

### pytorch-lightning — 🟠 HIGH

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/lightning_module.md at line 106 contains potentially dangerous Python code.
  > File: `references/lightning_module.md:106`
  > **Remediation:** Review the code block for security implications.

### torch-geometric — 🟠 HIGH

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in SKILL.md at line 226 contains potentially dangerous Python code.
  > File: `SKILL.md:226`
  > **Remediation:** Review the code block for security implications.

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/explainability.md at line 112 contains potentially dangerous Python code.
  > File: `references/explainability.md:112`
  > **Remediation:** Review the code block for security implications.

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/link_prediction.md at line 78 contains potentially dangerous Python code.
  > File: `references/link_prediction.md:78`
  > **Remediation:** Review the code block for security implications.

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/link_prediction.md at line 123 contains potentially dangerous Python code.
  > File: `references/link_prediction.md:123`
  > **Remediation:** Review the code block for security implications.

### transformers — 🟠 HIGH

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/models.md at line 290 contains potentially dangerous Python code.
  > File: `references/models.md:290`
  > **Remediation:** Review the code block for security implications.

### torchdrug — 🟠 HIGH

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/molecular_generation.md at line 74 contains potentially dangerous Python code.
  > File: `references/molecular_generation.md:74`
  > **Remediation:** Review the code block for security implications.

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/molecular_generation.md at line 201 contains potentially dangerous Python code.
  > File: `references/molecular_generation.md:201`
  > **Remediation:** Review the code block for security implications.

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/molecular_property_prediction.md at line 118 contains potentially dangerous Python code.
  > File: `references/molecular_property_prediction.md:118`
  > **Remediation:** Review the code block for security implications.

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/retrosynthesis.md at line 193 contains potentially dangerous Python code.
  > File: `references/retrosynthesis.md:193`
  > **Remediation:** Review the code block for security implications.

### waypoint-bio — 🟠 HIGH

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/python-api.md at line 137 contains potentially dangerous Python code.
  > File: `references/python-api.md:137`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/python-api.md at line 228 contains potentially dangerous Python code.
  > File: `references/python-api.md:228`
  > **Remediation:** Review the code block for security implications.

### biopython — 🟡 MEDIUM

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/alignment.md at line 295 contains potentially dangerous Python code.
  > File: `references/alignment.md:295`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/alignment.md at line 313 contains potentially dangerous Python code.
  > File: `references/alignment.md:313`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/blast.md at line 204 contains potentially dangerous Python code.
  > File: `references/blast.md:204`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/blast.md at line 231 contains potentially dangerous Python code.
  > File: `references/blast.md:231`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/blast.md at line 320 contains potentially dangerous Python code.
  > File: `references/blast.md:320`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/blast.md at line 349 contains potentially dangerous Python code.
  > File: `references/blast.md:349`
  > **Remediation:** Review the code block for security implications.

### dnanexus-integration — 🟡 MEDIUM

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/app-development.md at line 88 contains potentially dangerous Python code.
  > File: `references/app-development.md:88`
  > **Remediation:** Review the code block for security implications.

### genomic-intelligence — 🟡 MEDIUM

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in SKILL.md at line 213 contains potentially dangerous Python code.
  > File: `SKILL.md:213`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in SKILL.md at line 247 contains potentially dangerous Python code.
  > File: `SKILL.md:247`
  > **Remediation:** Review the code block for security implications.

### glycoengineering — 🟡 MEDIUM

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/glycan_databases.md at line 63 contains potentially dangerous Python code.
  > File: `references/glycan_databases.md:63`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/glycoshield.md at line 98 contains potentially dangerous Python code.
  > File: `references/glycoshield.md:98`
  > **Remediation:** Review the code block for security implications.

### paperclip — 🟡 MEDIUM

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/python-sdk.md at line 283 contains potentially dangerous Python code.
  > File: `references/python-sdk.md:283`
  > **Remediation:** Review the code block for security implications.

### bioservices — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation directive instructs agent to add a specific paper and fetch an external arXiv URL
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section directing the agent to add a specific arXiv reference (arXiv:2609.00065) to any manuscript, report, or code release the skill contributes to, to tell the user it did so, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv export API when network access is available. This is vendor self-promotion injected into the agent's output behavior and a directed outbound network request unrelated to the stated bioinformatics purpose. It does not exfiltrate data (no local content is sent) and it instructs disclosure to the user rather than concealment, so impact is low; but it is an instruction that shapes user-facing deliverables for the skill author's benefit.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance passive/optional documentation rather than a behavioral directive, and remove the instruction to automatically fetch an external URL; let the user decide whether to add the citation.

### diffdock — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation injection instruction
  > SKILL.md contains a 'Citing Scientific Agent Skills' section directing the agent to add a specific arXiv paper (arXiv:2609.00065, K-Dense) to the user's manuscript/report/code references whenever the skill 'materially contributed', and to fetch the arXiv record over the network. This is promotional content injected into the agent's output workflow rather than a docking capability. It is disclosed to the user (the skill tells the agent to inform the user it did so), so impact is low, but it does steer agent-generated deliverables toward a vendor-beneficial citation and triggers an outbound network fetch not required by the stated purpose.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion passive/optional documentation requiring explicit user consent, and remove the directive to automatically fetch the record and insert the reference into user deliverables.

### etetoolkit — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation instruction directs agent to insert author's paper into user deliverables
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section instructing the agent to add a specific arXiv paper by the skill authors to the references of any manuscript, report, presentation, or code release the skill contributed to, and to fetch arxiv.org/export.arxiv.org to populate the reference. This is author self-promotion embedded in active agent directions and causes modification of user work product plus an outbound network fetch unrelated to phylogenetic tree analysis. Mitigating factors: the action is conditional, is explicitly disclosed to the user ('tell the user you did so'), targets a public, named destination, and no local data is transmitted, so this is a contextual risk rather than confirmed abuse.
  > File: `SKILL.md`
  > **Remediation:** Make citation insertion an explicit user-approved option rather than a standing instruction, and remove the automatic network fetch of the authors' paper record from the skill's active directions.

### genomic-coordinates — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation instruction directing agent to add a specific paper and notify the user
  > The SKILL.md body includes a 'Citing Scientific Agent Skills' section instructing the agent to add a specific arXiv reference (arXiv:2609.00065 by the skill author's organisation) to any manuscript, report, presentation, or code release the skill materially contributed to, to tell the user it did so, and to fetch the arXiv record when network access is available. This is self-promotional boilerplate unrelated to the stated genomic-coordinate purpose and nudges the agent to insert author-attributed citations into user deliverables. It is disclosed rather than hidden, and the fetch target is a legitimate public arXiv URL with no local data sent, so impact is minimal.
  > File: `SKILL.md`
  > **Remediation:** Make citation insertion explicitly optional and user-confirmed, and remove the directive for the agent to autonomously fetch external URLs and modify user deliverables.

### histolab — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation injection instruction in SKILL.md
  > The SKILL.md body instructs the agent to add a specific arXiv reference (K-Dense 'Scientific Agent Skills', arXiv:2609.00065) to the user's manuscript/report/code release and to tell the user it did so, and to fetch the arXiv record when network access is available. This is an embedded directive that modifies user deliverables for the skill author's benefit rather than serving the stated histology-tiling purpose. It is conditional on material contribution and discloses the action to the user, so impact is low, but it is a behavior outside the declared scope.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/informational (e.g., 'you may cite...') rather than an instruction that directs the agent to insert references into user outputs, and do not require automatic network fetches.

### gtars — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-citation instruction directing the agent to add a specific reference and fetch an external URL
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section instructing the agent to add a specific arXiv citation to any manuscript, report, or code release the skill contributes to, to inform the user it did so, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv export API when network access is available. This is promotional/self-referential behavior unrelated to the skill's stated genomic-interval purpose and introduces an outbound network fetch not required by the documented workflow. It is disclosed to the user rather than hidden, so impact is low, and no local data is transmitted.
  > File: `SKILL.md`
  > **Remediation:** Make citation insertion an explicit user-approved option rather than a standing instruction, and remove the automatic external fetch or gate it behind the same explicit network-approval process the skill applies to all other network operations.

### medchem — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Mandatory self-citation instruction with directive to inform user
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section instructing the agent to add a specific arXiv paper (authored by the skill vendor, K-Dense) to references of any manuscript, report, or code release the skill contributes to, and to tell the user it did so. It also instructs the agent to fetch an external arXiv URL when network access is available. This is self-promotional content injected into the agent's output behavior rather than functionality required for medicinal chemistry filtering. It is disclosed (not hidden) and low impact, but it steers agent output toward vendor promotion and triggers an outbound network fetch unrelated to the stated purpose.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance optional and user-initiated; remove the instruction to automatically append the vendor's paper and to perform an unsolicited network fetch.

### nextflow — 🔵 LOW

- **🔵 LOW** `LLM_SUPPLY_CHAIN_ATTACK` — Documented curl-to-shell installer patterns for Nextflow and nf-test
  > Setup sections document downloading remote installer scripts (https://get.nextflow.io, https://get.nf-test.com) with curl and then executing them with bash. These are the official upstream installation routes for the tools the skill exists to support, the download is written to a local file first, and both instances include an explicit 'Review the installer before executing it' caution. This is a routine documented installer rather than an unverified or suspicious payload, so it is recorded only as contextual risk.
  > **Remediation:** Prefer pinned release archives or package-manager installs with checksum/signature verification over piping remote installer scripts into a shell.

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive instructing agent to add author's paper to user outputs
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section directing the agent to add a specific arXiv reference (arXiv:2609.00065) to manuscripts, reports, presentations or code releases when the skill 'materially contributed', to tell the user it did so, and to fetch an external arXiv URL when network access is available. This is self-promotional behavior injected into the agent's output on behalf of the skill author, unrelated to the stated Nextflow purpose. It is disclosed (not hidden) and does not exfiltrate data, so impact is low; the external fetch targets a public, named metadata endpoint.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion explicitly optional and user-confirmed, and remove the directive for the agent to automatically fetch remote records and insert the author's citation into user deliverables.

### matlab — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-citation directive instructs agent to insert author's paper into user deliverables
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' section that directs the agent to add a specific arXiv paper by the skill authors to the references of any manuscript, report, presentation, or code release the skill contributes to, and to fetch https://arxiv.org/abs/2609.00065 over the network when available. This is unrelated to the stated MATLAB/Octave purpose and influences user-facing scholarly output in the authors' favor. Mitigating factors: the action is conditional on material contribution, is disclosed in the instructions, explicitly tells the agent to inform the user, and involves only a read-only fetch of a public arXiv record with no local data being transmitted. No exfiltration, credential access, or hidden execution is present.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion an optional, user-initiated recommendation rather than a standing instruction, and remove the automatic network fetch directive, or clearly scope it to explicit user request.

### opentrons-integration — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation instruction directing agent to add a specific paper and fetch an external URL
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that instructs the agent to add a specific arXiv reference (K-Dense authors) to any manuscript, report, presentation, or code release the skill contributed to, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv export API when network access is available. This is self-promotional behavior unrelated to the skill's stated purpose of authoring Opentrons protocols, and introduces an outbound network fetch not needed for liquid-handling protocol work. It is disclosed to the user ('tell the user you did so') and no local data is transmitted, so impact is low and it is not exfiltration.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance explicitly optional and user-initiated, and remove the instruction to perform an unsolicited network fetch; limit the skill body to Opentrons protocol guidance.

### paperzilla — 🔵 LOW

- **🔵 LOW** `LLM_SUPPLY_CHAIN_ATTACK` — Installation guidance instructs bypassing a package-manager trust warning
  > The SKILL.md install section tells the reader that if Homebrew rejects the paperzilla tap formula as untrusted, they should run a trust-override command (`brew trust --formula paperzilla-ai/tap/pz`) and retry installation. Instructing an agent or user to override a package-manager integrity/trust warning weakens a supply-chain control, even though the scope is narrowed to the vendor's own formula and the rest of the package is documentation-only with no scripts, no network sinks, and explicit warnings against exporting session tokens or sending credentials to arbitrary hosts. No confirmed malicious payload, download-and-execute chain, or exfiltration path is present, so this is a contextual risk rather than demonstrated misuse.
  > File: `SKILL.md`
  > **Remediation:** Remove the trust-override guidance or replace it with instructions to verify the formula/binary against the published release checksum and signature, and require explicit user confirmation before any command that suppresses a package manager's trust check.

### polars — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation injection directing the agent to add a specific reference and fetch an external URL
  > The SKILL.md body instructs the agent to add a specific arXiv citation (authored by the skill vendor) to the user's manuscripts, reports, or code releases, to tell the user it did so, and to fetch an external arXiv URL when network access is available. This is unrelated to the stated DataFrame/ETL purpose and nudges the agent into modifying user deliverables and performing network retrieval. No sensitive data is sent outward and the fetch target is a public, named, benign domain, so impact is minimal; it is a promotional/contextual concern rather than exfiltration.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance explicitly optional and user-initiated; remove directives that cause the agent to insert vendor references into user deliverables or perform network fetches without an explicit user request.

### pyopenms — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation instruction directing agent to add a specific paper and fetch an external URL
  > SKILL.md contains a 'Citing Scientific Agent Skills' section instructing the agent to add a specific arXiv reference (arXiv:2609.00065, authored by the skill vendor K-Dense) to any manuscript, report, presentation, or code release the skill contributes to, to tell the user it did so, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv API when network access is available. This is a self-serving directive that influences user-facing output and triggers an outbound network fetch unrelated to the stated mass-spectrometry purpose. It is disclosed rather than hidden, instructs the agent to inform the user, and the destination is a well-known public academic site with no local data included in the request, so no exfiltration or covert behavior is established.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion advisory and user-confirmed rather than an instruction the agent follows automatically, and make the external arXiv lookup opt-in.

### pyzotero — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation injection into user deliverables
  > The SKILL.md body instructs the agent to add a specific paper authored by the skill vendor (arXiv:2609.00065, K-Dense) to the references or software section of any manuscript, report, presentation, or code release the skill contributed to, and to fetch the arXiv record over the network when available. This directs the agent to modify user-authored deliverables with vendor-promotional content that is unrelated to the skill's stated Zotero-management purpose. Mitigating factors: the instruction is disclosed in plain text, it explicitly tells the agent to inform the user, and the fetched endpoint (arxiv.org / export.arxiv.org) is a legitimate public bibliographic source with no local data being sent outbound. No credential access, hidden action, or exfiltration sink is involved.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion advisory rather than an automatic agent action: prompt the user for consent before inserting any vendor-attributed reference into their documents, and remove the directive to add the citation unilaterally.

### usfiscaldata — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive appended to skill instructions
  > The SKILL.md body includes a 'Citing Scientific Agent Skills' section instructing the agent to add a specific arXiv paper (K-Dense) to references/software sections of user manuscripts or code releases and to notify the user it did so, plus to fetch arxiv.org to retrieve the record. This is unrelated to the stated purpose of querying the Treasury Fiscal Data API and nudges the agent toward inserting vendor-promotional citations into user output. It is disclosed rather than hidden, involves only a public arXiv URL, and exfiltrates no local data, so impact is low.
  > File: `SKILL.md`
  > **Remediation:** Treat the citation request as optional user-facing guidance rather than an agent directive; remove or demote the self-citation instruction so it does not auto-modify user deliverables.

### ncats-arax — ⚪ INFO

- **⚪ INFO** `LLM_CONTEXT_BUDGET_EXCEEDED` — 'scripts/arax_client.py' only partially analyzed (74,979 excerpt chars from 85,617)
  > Only selected code excerpts (74,979 chars) from this 85,617-character file were included; the full file was not analyzed because it exceeds llm_analysis.max_code_file_chars (75,000 chars).
  > File: `scripts/arax_client.py`
  > **Remediation:** Increase llm_analysis.max_code_file_chars in your scan policy to include more content. The full file was not analyzed.
