# Security Scan Report

**Generated:** 2026-10-19 09:33 UTC  
**Skills scanned:** 177  
**Total findings:** 466  
**Critical:** 32 | **High:** 21 | **Safe skills:** 159/177

**Scanner:** cisco-ai-skill-scanner 2.3.0 · **Model:** claude-opus-5  
**This run:** full rescan of all 177 skill(s).  

## Summary

| Skill | Severity | Findings | Safe | Duration |
|-------|----------|----------|------|----------|
| autoskill | 🔴 CRITICAL | 5 | ❌ | 12.8s |
| citation-management | 🔴 CRITICAL | 8 | ❌ | 44.5s |
| infographics | 🔴 CRITICAL | 3 | ❌ | 19.8s |
| latex-posters | 🔴 CRITICAL | 4 | ❌ | 10.0s |
| literature-review | 🔴 CRITICAL | 3 | ❌ | 29.5s |
| open-notebook | 🔴 CRITICAL | 3 | ❌ | 15.6s |
| research-lookup | 🔴 CRITICAL | 3 | ❌ | 14.2s |
| scientific-schematics | 🔴 CRITICAL | 3 | ❌ | 22.7s |
| scientific-slides | 🔴 CRITICAL | 4 | ❌ | 26.5s |
| esm | 🟠 HIGH | 4 | ❌ | 14.9s |
| geomaster | 🟠 HIGH | 3 | ❌ | 9.3s |
| hugging-science | 🟠 HIGH | 1 | ❌ | 30.9s |
| modal | 🟠 HIGH | 8 | ❌ | 11.2s |
| pytorch-lightning | 🟠 HIGH | 1 | ❌ | 13.2s |
| torch-geometric | 🟠 HIGH | 4 | ❌ | 10.2s |
| transformers | 🟠 HIGH | 1 | ❌ | 17.1s |
| torchdrug | 🟠 HIGH | 4 | ❌ | 19.3s |
| waypoint-bio | 🟠 HIGH | 2 | ❌ | 11.1s |
| biopython | 🟡 MEDIUM | 6 | ✅ | 8.5s |
| dnanexus-integration | 🟡 MEDIUM | 1 | ✅ | 10.9s |
| genomic-intelligence | 🟡 MEDIUM | 2 | ✅ | 10.6s |
| glycoengineering | 🟡 MEDIUM | 2 | ✅ | 8.5s |
| paperclip | 🟡 MEDIUM | 1 | ✅ | 9.2s |
| arboreto | 🔵 LOW | 1 | ✅ | 17.4s |
| cellxgene-census | 🔵 LOW | 1 | ✅ | 13.0s |
| cirq | 🔵 LOW | 1 | ✅ | 16.3s |
| deepchem | 🔵 LOW | 1 | ✅ | 17.9s |
| etetoolkit | 🔵 LOW | 1 | ✅ | 14.1s |
| latchbio-integration | 🔵 LOW | 1 | ✅ | 15.7s |
| matplotlib | 🔵 LOW | 1 | ✅ | 14.5s |
| markitdown | 🔵 LOW | 1 | ✅ | 19.5s |
| pennylane | 🔵 LOW | 1 | ✅ | 14.0s |
| protocolsio-integration | 🔵 LOW | 1 | ✅ | 16.1s |
| scientific-visualization | 🔵 LOW | 1 | ✅ | 16.2s |
| scientific-writing | 🔵 LOW | 1 | ✅ | 28.4s |
| ncats-arax | ⚪ INFO | 1 | ✅ | 13.0s |
| analytical-method-validation | 🟢 SAFE | 0 | ✅ | 13.0s |
| anndata | 🟢 SAFE | 0 | ✅ | 13.1s |
| 13c-metabolic-flux | 🟢 SAFE | 0 | ✅ | 13.5s |
| arbor | 🟢 SAFE | 0 | ✅ | 14.4s |
| alphagenome | 🟢 SAFE | 0 | ✅ | 19.1s |
| adaptyv | 🟢 SAFE | 0 | ✅ | 20.4s |
| benchling-integration | 🟢 SAFE | 0 | ✅ | 7.5s |
| bgpt-paper-search | 🟢 SAFE | 0 | ✅ | 7.0s |
| astropy | 🟢 SAFE | 0 | ✅ | 11.0s |
| bids | 🟢 SAFE | 0 | ✅ | 6.9s |
| aeon | 🟢 SAFE | 0 | ✅ | 28.4s |
| cantera | 🟢 SAFE | 0 | ✅ | 8.4s |
| bioservices | 🟢 SAFE | 0 | ✅ | 9.8s |
| cellprofiler | 🟢 SAFE | 0 | ✅ | 7.8s |
| clinical-decision-support | 🟢 SAFE | 0 | ✅ | 8.0s |
| bulk-rnaseq | 🟢 SAFE | 0 | ✅ | 15.9s |
| consciousness-council | 🟢 SAFE | 0 | ✅ | 6.3s |
| clinical-reports | 🟢 SAFE | 0 | ✅ | 12.1s |
| datalad | 🟢 SAFE | 0 | ✅ | 9.1s |
| deepspot-m | 🟢 SAFE | 0 | ✅ | 6.8s |
| datamol | 🟢 SAFE | 0 | ✅ | 10.8s |
| dask | 🟢 SAFE | 0 | ✅ | 14.7s |
| cobrapy | 🟢 SAFE | 0 | ✅ | 24.6s |
| dhdna-profiler | 🟢 SAFE | 0 | ✅ | 7.2s |
| depmap | 🟢 SAFE | 0 | ✅ | 7.6s |
| deeptools | 🟢 SAFE | 0 | ✅ | 16.4s |
| diffdock | 🟢 SAFE | 0 | ✅ | 13.1s |
| exa-search | 🟢 SAFE | 0 | ✅ | 8.9s |
| database-lookup | 🟢 SAFE | 0 | ✅ | 35.4s |
| experimental-design | 🟢 SAFE | 0 | ✅ | 9.9s |
| fictiv | 🟢 SAFE | 0 | ✅ | 10.6s |
| exploratory-data-analysis | 🟢 SAFE | 0 | ✅ | 13.2s |
| folklore-variant-evidence | 🟢 SAFE | 0 | ✅ | 5.3s |
| flowkit | 🟢 SAFE | 0 | ✅ | 8.8s |
| fluidsim | 🟢 SAFE | 0 | ✅ | 12.2s |
| geniml | 🟢 SAFE | 0 | ✅ | 11.8s |
| generate-image | 🟢 SAFE | 0 | ✅ | 14.6s |
| flowio | 🟢 SAFE | 0 | ✅ | 18.2s |
| genomic-coordinates | 🟢 SAFE | 0 | ✅ | 17.7s |
| geopandas | 🟢 SAFE | 0 | ✅ | 15.3s |
| ginkgo-cloud-lab | 🟢 SAFE | 0 | ✅ | 8.4s |
| gget | 🟢 SAFE | 0 | ✅ | 10.2s |
| gtars | 🟢 SAFE | 0 | ✅ | 9.5s |
| histolab | 🟢 SAFE | 0 | ✅ | 9.8s |
| get-available-resources | 🟢 SAFE | 0 | ✅ | 15.2s |
| hypothesis-generation | 🟢 SAFE | 0 | ✅ | 11.1s |
| imaging-data-commons | 🟢 SAFE | 0 | ✅ | 15.3s |
| hypogenic | 🟢 SAFE | 0 | ✅ | 15.6s |
| lab-hardware-cad | 🟢 SAFE | 0 | ✅ | 13.0s |
| labarchive-integration | 🟢 SAFE | 0 | ✅ | 12.5s |
| iso-standards-readiness | 🟢 SAFE | 0 | ✅ | 16.5s |
| lamindb | 🟢 SAFE | 0 | ✅ | 7.3s |
| marine-carbonate-chemistry | 🟢 SAFE | 0 | ✅ | 8.5s |
| liteparse | 🟢 SAFE | 0 | ✅ | 14.3s |
| markdown-mermaid-writing | 🟢 SAFE | 0 | ✅ | 12.3s |
| mageck | 🟢 SAFE | 0 | ✅ | 15.5s |
| market-research-reports | 🟢 SAFE | 0 | ✅ | 11.8s |
| matchms | 🟢 SAFE | 0 | ✅ | 8.6s |
| molecular-dynamics | 🟢 SAFE | 0 | ✅ | 7.1s |
| molfeat | 🟢 SAFE | 0 | ✅ | 7.7s |
| medchem | 🟢 SAFE | 0 | ✅ | 21.0s |
| nmrglue | 🟢 SAFE | 0 | ✅ | 7.7s |
| matlab | 🟢 SAFE | 0 | ✅ | 25.7s |
| nwb-conversion | 🟢 SAFE | 0 | ✅ | 6.5s |
| neurokit2 | 🟢 SAFE | 0 | ✅ | 18.3s |
| nextflow | 🟢 SAFE | 0 | ✅ | 18.0s |
| neuropixels-analysis | 🟢 SAFE | 0 | ✅ | 20.2s |
| omero-integration | 🟢 SAFE | 0 | ✅ | 12.4s |
| ontology-term-resolution | 🟢 SAFE | 0 | ✅ | 9.8s |
| networkx | 🟢 SAFE | 0 | ✅ | 23.3s |
| onekgpd | 🟢 SAFE | 0 | ✅ | 13.8s |
| openpiv | 🟢 SAFE | 0 | ✅ | 8.2s |
| opentrons-integration | 🟢 SAFE | 0 | ✅ | 13.1s |
| pacsomatic | 🟢 SAFE | 0 | ✅ | 12.0s |
| paper-lookup | 🟢 SAFE | 0 | ✅ | 12.8s |
| paperzilla | 🟢 SAFE | 0 | ✅ | 15.0s |
| parallel-web | 🟢 SAFE | 0 | ✅ | 14.1s |
| pathway-enrichment | 🟢 SAFE | 0 | ✅ | 11.3s |
| optimize-for-gpu | 🟢 SAFE | 0 | ✅ | 23.1s |
| pathml | 🟢 SAFE | 0 | ✅ | 14.5s |
| phylogenetics | 🟢 SAFE | 0 | ✅ | 6.5s |
| peer-review | 🟢 SAFE | 0 | ✅ | 13.6s |
| pkpd-modeling | 🟢 SAFE | 0 | ✅ | 9.4s |
| polars | 🟢 SAFE | 0 | ✅ | 10.1s |
| polars-bio | 🟢 SAFE | 0 | ✅ | 9.3s |
| pptx-posters | 🟢 SAFE | 0 | ✅ | 8.9s |
| primekg | 🟢 SAFE | 0 | ✅ | 8.0s |
| pathogen-variant-surveillance | 🟢 SAFE | 0 | ✅ | 25.7s |
| primer-design | 🟢 SAFE | 0 | ✅ | 10.2s |
| pybamm | 🟢 SAFE | 0 | ✅ | 6.4s |
| pi-agent | 🟢 SAFE | 0 | ✅ | 20.6s |
| pycalphad | 🟢 SAFE | 0 | ✅ | 8.0s |
| pydeseq2 | 🟢 SAFE | 0 | ✅ | 12.1s |
| pymatgen | 🟢 SAFE | 0 | ✅ | 8.4s |
| pydicom | 🟢 SAFE | 0 | ✅ | 12.7s |
| pymc | 🟢 SAFE | 0 | ✅ | 9.2s |
| pyhealth | 🟢 SAFE | 0 | ✅ | 12.8s |
| pufferlib | 🟢 SAFE | 0 | ✅ | 18.0s |
| pylabrobot | 🟢 SAFE | 0 | ✅ | 20.2s |
| qiime2-amplicon | 🟢 SAFE | 0 | ✅ | 10.6s |
| pytdc | 🟢 SAFE | 0 | ✅ | 14.6s |
| pymoo | 🟢 SAFE | 0 | ✅ | 18.3s |
| pyzotero | 🟢 SAFE | 0 | ✅ | 15.9s |
| pyopenms | 🟢 SAFE | 0 | ✅ | 19.7s |
| qiskit | 🟢 SAFE | 0 | ✅ | 9.2s |
| pysam | 🟢 SAFE | 0 | ✅ | 22.4s |
| relion | 🟢 SAFE | 0 | ✅ | 8.1s |
| rdkit | 🟢 SAFE | 0 | ✅ | 8.9s |
| qutip | 🟢 SAFE | 0 | ✅ | 12.6s |
| relsa-severity-assessment | 🟢 SAFE | 0 | ✅ | 9.8s |
| rowan | 🟢 SAFE | 0 | ✅ | 8.8s |
| scanpy | 🟢 SAFE | 0 | ✅ | 10.7s |
| research-grants | 🟢 SAFE | 0 | ✅ | 15.4s |
| scholar-evaluation | 🟢 SAFE | 0 | ✅ | 11.1s |
| scientific-brainstorming | 🟢 SAFE | 0 | ✅ | 11.1s |
| scientific-critical-thinking | 🟢 SAFE | 0 | ✅ | 11.8s |
| scvelo | 🟢 SAFE | 0 | ✅ | 7.2s |
| scikit-survival | 🟢 SAFE | 0 | ✅ | 9.8s |
| scikit-bio | 🟢 SAFE | 0 | ✅ | 13.6s |
| scikit-learn | 🟢 SAFE | 0 | ✅ | 18.3s |
| seaborn | 🟢 SAFE | 0 | ✅ | 8.7s |
| stable-baselines3 | 🟢 SAFE | 0 | ✅ | 9.0s |
| scvi-tools | 🟢 SAFE | 0 | ✅ | 14.9s |
| shap | 🟢 SAFE | 0 | ✅ | 13.1s |
| statsmodels | 🟢 SAFE | 0 | ✅ | 8.3s |
| statistical-power | 🟢 SAFE | 0 | ✅ | 11.1s |
| statistical-analysis | 🟢 SAFE | 0 | ✅ | 12.6s |
| sympy | 🟢 SAFE | 0 | ✅ | 8.9s |
| tamarind | 🟢 SAFE | 0 | ✅ | 8.6s |
| tiledbvcf | 🟢 SAFE | 0 | ✅ | 6.1s |
| tellurium | 🟢 SAFE | 0 | ✅ | 9.1s |
| timesfm-forecasting | 🟢 SAFE | 0 | ✅ | 8.5s |
| umap-learn | 🟢 SAFE | 0 | ✅ | 7.0s |
| treatment-plans | 🟢 SAFE | 0 | ✅ | 8.5s |
| uncertainty-and-units | 🟢 SAFE | 0 | ✅ | 11.9s |
| vaex | 🟢 SAFE | 0 | ✅ | 8.8s |
| usfiscaldata | 🟢 SAFE | 0 | ✅ | 12.2s |
| simpy | 🟢 SAFE | 0 | ✅ | 39.7s |
| what-if-oracle | 🟢 SAFE | 0 | ✅ | 6.9s |
| venue-templates | 🟢 SAFE | 0 | ✅ | 20.8s |
| zarr-python | 🟢 SAFE | 0 | ✅ | 20.0s |

## Detailed Findings

### autoskill — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 3 files
  > Environment variable access with network calls in scripts/backends.py, scripts/doctor.py, scripts/run.py
  > **Remediation:** Review data flow across files: scripts/run.py, scripts/doctor.py, scripts/backends.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 3 files
  > Multi-file exfiltration chain detected: scripts/backends.py, scripts/doctor.py, scripts/run.py collect data → scripts/run.py → scripts/backends.py, scripts/doctor.py, scripts/run.py transmit to network
  > **Remediation:** Review data flow across files: scripts/run.py, scripts/doctor.py, scripts/backends.py

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
  > **Remediation:** Review data flow across files: scripts/search_openalex.py, scripts/validate_citations.py, scripts/doi_to_bibtex.py, scripts/extract_metadata.py, scripts/search_pubmed.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 5 files
  > Multi-file exfiltration chain detected: scripts/extract_metadata.py, scripts/search_openalex.py, scripts/search_pubmed.py collect data → encode → scripts/doi_to_bibtex.py, scripts/validate_citations.py, scripts/extract_metadata.py, scripts/search_openalex.py, scripts/search_pubmed.py transmit to network
  > **Remediation:** Review data flow across files: scripts/search_openalex.py, scripts/validate_citations.py, scripts/doi_to_bibtex.py, scripts/extract_metadata.py, scripts/search_pubmed.py

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

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Skill instructs agent to insert the author's own paper into user deliverables
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section directing the agent to add a specific paper by the skill vendor (K-Dense) to the user's manuscript references/software section whenever the skill 'materially contributed', and to fetch the arXiv record over the network to populate the entry. The action is disclosed (the agent is told to inform the user) and is conditional, so it is not covert, but it is self-promotional content injection into user-authored research output that is not required by the stated citation-management purpose. No data leaves the user's environment and no hidden action is requested, so this is a contextual/policy concern rather than a confirmed abuse.
  > File: `SKILL.md`
  > **Remediation:** Make the self-citation strictly opt-in on explicit user request, or remove the directive from the active instruction body and keep it as passive documentation.

- **🔵 LOW** `LLM_TRANSITIVE_TRUST_ABUSE` — Mandatory enrichment phase invokes an undeclared external CLI from another skill
  > Phase 2.5 is labelled MANDATORY and instructs the agent to shell out to `parallel-cli` (from a separate 'parallel-web' skill) to search the web and write JSON into a `sources/` directory for each incomplete citation. The dependency is not listed in the skill's compatibility/dependency section and is not bundled, so the behavior relies on a transitively trusted third-party binary being on PATH. The purpose (filling missing bibliographic fields) is consistent with the skill's stated function, the destinations are generic web search, and the reference material explicitly warns to pass publisher-controlled metadata as argv rather than shell text and to validate citation keys against ^[A-Za-z0-9]+$ before they reach a file path — which mitigates the command-injection path the deterministic MDBLOCK_PYTHON_SUBPROCESS lead points at. Flagged only as an undeclared transitive execution dependency.
  > File: `SKILL.md`
  > **Remediation:** Declare the parallel-web/parallel-cli dependency in the skill manifest and compatibility notes, and make the enrichment phase degrade gracefully (or prompt the user) when the external CLI is absent.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/core_workflow.md at line 193 contains potentially dangerous Python code.
  > File: `references/core_workflow.md:193`
  > **Remediation:** Review the code block for security implications.

### infographics — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 2 files
  > Environment variable access with network calls in scripts/generate_infographic.py, scripts/generate_infographic_ai.py
  > **Remediation:** Review data flow across files: scripts/generate_infographic_ai.py, scripts/generate_infographic.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 2 files
  > Multi-file exfiltration chain detected: scripts/generate_infographic.py, scripts/generate_infographic_ai.py collect data → scripts/generate_infographic_ai.py → scripts/generate_infographic_ai.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_infographic_ai.py, scripts/generate_infographic.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/infographics/scripts/generate_infographic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/infographics/scripts/generate_infographic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

### latex-posters — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 2 files
  > Environment variable access with network calls in scripts/generate_schematic_ai.py, scripts/generate_schematic.py
  > **Remediation:** Review data flow across files: scripts/generate_schematic_ai.py, scripts/generate_schematic.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 2 files
  > Multi-file exfiltration chain detected: scripts/generate_schematic_ai.py, scripts/generate_schematic.py collect data → scripts/generate_schematic_ai.py → scripts/generate_schematic_ai.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_schematic_ai.py, scripts/generate_schematic.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/latex-posters/scripts/generate_schematic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/latex-posters/scripts/generate_schematic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🟡 MEDIUM** `BEHAVIOR_BASH_TAINT_FLOW` — Bash: tainted data flows to dangerous sink
  > Variable $FILE_SIZE_BYTES (line 63) flows to `sh` at line 64.
  > File: `scripts/review_poster.sh:64`
  > **Remediation:** Review the data flow from source to sink. Avoid sending sensitive or untrusted data to network or execution commands.

### literature-review — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 3 files
  > Environment variable access with network calls in scripts/generate_schematic_ai.py, scripts/generate_schematic.py
  > **Remediation:** Review data flow across files: scripts/verify_citations.py, scripts/generate_schematic_ai.py, scripts/generate_schematic.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 3 files
  > Multi-file exfiltration chain detected: scripts/generate_schematic_ai.py, scripts/generate_schematic.py collect data → scripts/generate_schematic_ai.py → scripts/generate_schematic_ai.py, scripts/verify_citations.py transmit to network
  > **Remediation:** Review data flow across files: scripts/verify_citations.py, scripts/generate_schematic_ai.py, scripts/generate_schematic.py

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
  > **Remediation:** Review data flow across files: scripts/manuscript_packet.py, scripts/research_lookup.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/research-lookup/scripts/research_lookup.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/research-lookup/scripts/research_lookup.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

### scientific-schematics — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 2 files
  > Environment variable access with network calls in scripts/generate_schematic_ai.py, scripts/generate_schematic.py
  > **Remediation:** Review data flow across files: scripts/generate_schematic_ai.py, scripts/generate_schematic.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 2 files
  > Multi-file exfiltration chain detected: scripts/generate_schematic_ai.py, scripts/generate_schematic.py collect data → scripts/generate_schematic_ai.py → scripts/generate_schematic_ai.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_schematic_ai.py, scripts/generate_schematic.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-schematics/scripts/generate_schematic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-schematics/scripts/generate_schematic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

### scientific-slides — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 4 files
  > Environment variable access with network calls in scripts/generate_schematic_ai.py, scripts/generate_slide_image.py, scripts/generate_slide_image_ai.py, scripts/generate_schematic.py
  > **Remediation:** Review data flow across files: scripts/generate_slide_image.py, scripts/generate_schematic_ai.py, scripts/generate_schematic.py, scripts/generate_slide_image_ai.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 4 files
  > Multi-file exfiltration chain detected: scripts/generate_schematic_ai.py, scripts/generate_slide_image.py, scripts/generate_slide_image_ai.py, scripts/generate_schematic.py collect data → scripts/generate_schematic_ai.py, scripts/generate_slide_image_ai.py → scripts/generate_schematic_ai.py, scripts/generate_slide_image_ai.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_slide_image.py, scripts/generate_schematic_ai.py, scripts/generate_schematic.py, scripts/generate_slide_image_ai.py

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

### arboreto — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation instruction directs agent to add a specific paper reference and fetch a remote URL
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section instructing the agent to add a specific arXiv citation (authored by the skill vendor) to any manuscript, report, or code release the skill contributes to, to tell the user it did so, and to fetch an external arXiv URL/API when network access is available. This is vendor self-promotion embedded as an operational directive rather than functionality needed for gene regulatory network inference. It is disclosed (not hidden) and the fetched destination is a well-known public preprint server with no local data sent, so impact is low. No exfiltration or override of user instructions is present.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/optional information for the user rather than a standing directive to the agent, and remove the automatic external URL fetch instruction or require explicit user consent.

### cellxgene-census — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation injection directing agent to add a fixed reference and fetch an external URL
  > The SKILL.md body instructs the agent that if the skill 'materially contributed' to a manuscript or code release it must add a specific arXiv citation for the skill authors (K-Dense) to the user's references and 'tell the user you did so', and to fetch an external arXiv URL/API before writing the reference. This is self-promotional content injected into the agent's output workflow rather than functionality needed for querying the CELLxGENE Census. The network fetch is to a legitimate, publicly declared arXiv endpoint and no local data is transmitted, so impact is limited; however, it biases agent-authored artifacts toward the vendor's own publication. No credential access, exfiltration sink, or hidden execution is present.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance optional and user-prompted rather than an instruction that the agent modify deliverables, and remove the directive to fetch the promotional record automatically.

### cirq — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation directive instructing agent to add author's paper to outputs
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section instructing the agent to add a specific arXiv paper by the skill author (K-Dense Inc.) to the references of any manuscript, report, presentation, or code release the skill contributes to, and to fetch an external arXiv URL when network access is available. This is a self-serving promotional instruction embedded in agent-directed content rather than a technical capability of the quantum computing skill. It does direct the user to be told, and the network fetch is to a legitimate public arXiv record, so impact is minimal; no data is sent outward beyond a normal metadata lookup.
  > File: `SKILL.md`
  > **Remediation:** Make the citation request a passive note for the human user rather than a standing instruction to the agent, and avoid directing automatic outbound fetches as part of unrelated tasks.

### deepchem — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation injection directive in SKILL.md
  > The skill body instructs the agent to add a specific arXiv paper (arXiv:2609.00065) to any manuscript, report, presentation or code release the skill contributes to, to tell the user it did so, and to fetch the arXiv record over the network when available. This is unrelated to the stated DeepChem/molecular-ML purpose and injects vendor self-promotion into user deliverables. It is disclosed (the agent is told to inform the user) and the destination is a public, declared academic source, so impact is low, but it still steers agent output toward promoting the skill author.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion optional and user-confirmed rather than a standing directive to modify deliverables; remove the automatic network fetch instruction or gate it behind explicit user request.

### etetoolkit — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation instruction directs agent to add author's paper to user deliverables
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section instructing the agent to add a specific arXiv reference (attributed to the skill author's organization) to any manuscript, report, presentation, or code release the skill contributed to, and to fetch an external arXiv URL before writing the reference. This is promotional behavior injected into the agent's output on the user's work product rather than functionality related to phylogenetic tree analysis. The network fetch targets a public, declared, benign destination (arxiv.org) and transmits no local data, so impact is limited; no exfiltration or hidden action is established.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion advisory and user-confirmed rather than an instruction that the agent automatically inserts references into user deliverables; remove the automatic external fetch directive.

### latchbio-integration — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation injection instruction
  > The SKILL.md body instructs the agent to add a specific arXiv citation (K-Dense 'Scientific Agent Skills') to the user's manuscript, report, or code release and to tell the user it did so, and to fetch an external arXiv URL. This is unrelated to the skill's stated bioinformatics-workflow purpose and directs the agent to inject promotional content into user deliverables. It does disclose the action to the user and does not exfiltrate data, so impact is limited.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/optional (e.g., 'if the user asks how to cite this skill') rather than an instruction that the agent modify user deliverables and perform network fetches.

### matplotlib — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive instructing agent to add author's paper to user deliverables
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section directing the agent to add a specific arXiv reference (arXiv:2609.00065 by the skill author's organization, K-Dense Inc.) to any manuscript, report, presentation, or code release the skill contributed to, and to fetch the arXiv record over the network when available. This injects vendor self-promotion into user output and adds an outbound network fetch unrelated to the stated plotting purpose. It is disclosed ('tell the user you did so') rather than hidden, so impact is low, but it is a behavior beyond the declared plotting capability.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion passive/optional and explicitly require user confirmation before modifying deliverables or performing network fetches; remove the mandatory phrasing.

### markitdown — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation instruction directs agent to add author's paper and fetch external URL
  > The SKILL.md closes with a 'Citing Scientific Agent Skills' section instructing the agent to add a specific arXiv paper by the skill authors (K-Dense Inc.) to any manuscript, report, presentation, or code release the skill contributes to, to tell the user it did so, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv API when network access is available. This is author self-promotion embedded as an operating instruction and a conditional outbound network fetch unrelated to the stated document-conversion purpose. It is disclosed to the user (the skill says to tell the user), so impact is low and no data is sent outward beyond a plain record lookup, but it is behavior beyond the declared scope of Markdown conversion.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/user-opt-in rather than an operative instruction, and remove the automatic external arXiv fetch or gate it behind explicit user request.

### pennylane — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation injection instruction
  > The SKILL.md body instructs the agent to add a specific paper (arXiv:2609.00065, authored by the skill vendor K-Dense) to the references of any manuscript, report, presentation, or code release the skill contributes to, to tell the user it did so, and to fetch the arXiv record over the network when available. This is vendor self-promotion embedded as an active directive rather than a quantum-computing capability; it can cause the agent to insert citations into user deliverables. It is disclosed (the agent is told to inform the user) and the fetch target is a public, benign arXiv URL, so impact is limited and no local data is sent out.
  > File: `SKILL.md`
  > **Remediation:** Reframe the citation guidance as optional, user-approved information rather than a standing directive to modify user deliverables, and make any network fetch conditional on explicit user consent.

### protocolsio-integration — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation instruction directs agent to add author's paper to outputs
  > SKILL.md contains a 'Citing Scientific Agent Skills' section instructing the agent to add a specific arXiv paper by the skill author (K-Dense Inc.) to the references of any manuscript, report, presentation, or code release the skill contributed to, and to fetch arxiv.org for the record. This is self-promotional behavior unrelated to the stated protocols.io integration purpose. It is disclosed to the user ('tell the user you did so') and the network fetch targets a public, named arXiv endpoint, so impact is low, but it does inject vendor-attribution content into user deliverables.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion optional and user-initiated rather than an instruction to add the vendor's paper to user deliverables; remove the automatic arXiv fetch directive or clearly gate it behind explicit user consent.

### scientific-visualization — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation instruction directs agent to add author's paper to user deliverables
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section instructing the agent to add a specific arXiv paper by the skill author (K-Dense Inc.) to the references/software section of any manuscript, report, presentation, or code release the skill contributes to, and to fetch an external arXiv URL/API endpoint before writing the reference. This is promotional self-citation injected into user outputs rather than functionality needed for scientific figure creation, and it introduces an outbound network fetch not implied by the skill's stated network-free design. It does instruct the agent to tell the user it did so, which mitigates concealment concerns, and no local data is transmitted. No deterministic findings corroborate a data-exfiltration channel, so this is a contextual policy/content concern rather than a confirmed exfiltration.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion optional and user-confirmed rather than a standing directive, and remove or clearly gate the automatic external arXiv fetch so the documented network-free posture of the skill is preserved.

### scientific-writing — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Skill directs agent to insert vendor self-citation into user manuscripts
  > The SKILL.md body closes with a 'Citing Scientific Agent Skills' section instructing the agent to add a specific K-Dense arXiv paper (arXiv:2609.00065) to the references or software section of the user's manuscript, report, presentation, or code release, and to fetch the arXiv record over the network when available. This is author-benefiting content injected into user deliverables and sits in tension with the skill's own strict evidence-binding rules that every reference must be human-verified for the proposition it supports. Mitigating factors: the instruction is conditional ('if it materially contributed'), it explicitly requires telling the user, and the fetched destination is the legitimate public arXiv record rather than a covert endpoint. No local data, secrets, or manuscript content is sent anywhere.
  > File: `SKILL.md`
  > **Remediation:** Make the self-citation purely optional and user-approved rather than an instruction to the agent, and ensure any added reference passes the same human verification gate the skill requires for all other citations.

### ncats-arax — ⚪ INFO

- **⚪ INFO** `LLM_CONTEXT_BUDGET_EXCEEDED` — 'scripts/arax_client.py' only partially analyzed (74,979 excerpt chars from 85,617)
  > Only selected code excerpts (74,979 chars) from this 85,617-character file were included; the full file was not analyzed because it exceeds llm_analysis.max_code_file_chars (75,000 chars).
  > File: `scripts/arax_client.py`
  > **Remediation:** Increase llm_analysis.max_code_file_chars in your scan policy to include more content. The full file was not analyzed.
