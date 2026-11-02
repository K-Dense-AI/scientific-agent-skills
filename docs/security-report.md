# Security Scan Report

**Generated:** 2026-11-02 09:23 UTC  
**Skills scanned:** 177  
**Total findings:** 472  
**Critical:** 32 | **High:** 21 | **Safe skills:** 159/177

**Scanner:** cisco-ai-skill-scanner 2.3.2 · **Model:** claude-opus-5  
**This run:** full rescan of all 177 skill(s).  

## Summary

| Skill | Severity | Findings | Safe | Duration |
|-------|----------|----------|------|----------|
| autoskill | 🔴 CRITICAL | 6 | ❌ | 21.2s |
| citation-management | 🔴 CRITICAL | 6 | ❌ | 34.8s |
| infographics | 🔴 CRITICAL | 4 | ❌ | 20.5s |
| literature-review | 🔴 CRITICAL | 3 | ❌ | 19.7s |
| latex-posters | 🔴 CRITICAL | 4 | ❌ | 24.7s |
| open-notebook | 🔴 CRITICAL | 4 | ❌ | 18.9s |
| research-lookup | 🔴 CRITICAL | 3 | ❌ | 15.8s |
| scientific-schematics | 🔴 CRITICAL | 3 | ❌ | 18.6s |
| scientific-slides | 🔴 CRITICAL | 4 | ❌ | 32.0s |
| esm | 🟠 HIGH | 4 | ❌ | 20.1s |
| geomaster | 🟠 HIGH | 3 | ❌ | 21.9s |
| hugging-science | 🟠 HIGH | 1 | ❌ | 17.9s |
| modal | 🟠 HIGH | 8 | ❌ | 22.0s |
| pytorch-lightning | 🟠 HIGH | 1 | ❌ | 20.5s |
| torch-geometric | 🟠 HIGH | 4 | ❌ | 13.4s |
| torchdrug | 🟠 HIGH | 4 | ❌ | 12.5s |
| transformers | 🟠 HIGH | 1 | ❌ | 13.0s |
| waypoint-bio | 🟠 HIGH | 2 | ❌ | 25.8s |
| biopython | 🟡 MEDIUM | 6 | ✅ | 15.3s |
| dnanexus-integration | 🟡 MEDIUM | 1 | ✅ | 14.3s |
| genomic-intelligence | 🟡 MEDIUM | 2 | ✅ | 11.4s |
| glycoengineering | 🟡 MEDIUM | 2 | ✅ | 8.8s |
| paperclip | 🟡 MEDIUM | 1 | ✅ | 15.3s |
| aeon | 🔵 LOW | 1 | ✅ | 21.5s |
| arboreto | 🔵 LOW | 1 | ✅ | 21.8s |
| benchling-integration | 🔵 LOW | 1 | ✅ | 12.4s |
| bioservices | 🔵 LOW | 1 | ✅ | 17.5s |
| cirq | 🔵 LOW | 1 | ✅ | 16.6s |
| etetoolkit | 🔵 LOW | 1 | ✅ | 16.0s |
| latchbio-integration | 🔵 LOW | 1 | ✅ | 17.6s |
| markitdown | 🔵 LOW | 1 | ✅ | 19.3s |
| matplotlib | 🔵 LOW | 1 | ✅ | 16.0s |
| medchem | 🔵 LOW | 1 | ✅ | 16.1s |
| networkx | 🔵 LOW | 1 | ✅ | 14.9s |
| pufferlib | 🔵 LOW | 1 | ✅ | 17.8s |
| pyzotero | 🔵 LOW | 1 | ✅ | 13.3s |
| scientific-visualization | 🔵 LOW | 1 | ✅ | 16.9s |
| scientific-writing | 🔵 LOW | 1 | ✅ | 25.6s |
| statistical-power | 🔵 LOW | 1 | ✅ | 14.1s |
| zarr-python | 🔵 LOW | 1 | ✅ | 21.7s |
| ncats-arax | ⚪ INFO | 1 | ✅ | 14.3s |
| 13c-metabolic-flux | 🟢 SAFE | 0 | ✅ | 14.5s |
| anndata | 🟢 SAFE | 0 | ✅ | 15.8s |
| arbor | 🟢 SAFE | 0 | ✅ | 16.3s |
| adaptyv | 🟢 SAFE | 0 | ✅ | 19.1s |
| analytical-method-validation | 🟢 SAFE | 0 | ✅ | 20.4s |
| bgpt-paper-search | 🟢 SAFE | 0 | ✅ | 7.2s |
| astropy | 🟢 SAFE | 0 | ✅ | 12.1s |
| alphagenome | 🟢 SAFE | 0 | ✅ | 26.5s |
| bids | 🟢 SAFE | 0 | ✅ | 9.6s |
| cantera | 🟢 SAFE | 0 | ✅ | 8.3s |
| cellprofiler | 🟢 SAFE | 0 | ✅ | 8.7s |
| bulk-rnaseq | 🟢 SAFE | 0 | ✅ | 10.3s |
| cellxgene-census | 🟢 SAFE | 0 | ✅ | 7.9s |
| consciousness-council | 🟢 SAFE | 0 | ✅ | 6.7s |
| clinical-decision-support | 🟢 SAFE | 0 | ✅ | 11.4s |
| clinical-reports | 🟢 SAFE | 0 | ✅ | 11.1s |
| dask | 🟢 SAFE | 0 | ✅ | 10.5s |
| datalad | 🟢 SAFE | 0 | ✅ | 6.7s |
| cobrapy | 🟢 SAFE | 0 | ✅ | 15.9s |
| datamol | 🟢 SAFE | 0 | ✅ | 8.6s |
| deepspot-m | 🟢 SAFE | 0 | ✅ | 8.6s |
| depmap | 🟢 SAFE | 0 | ✅ | 7.6s |
| deepchem | 🟢 SAFE | 0 | ✅ | 10.9s |
| deeptools | 🟢 SAFE | 0 | ✅ | 10.4s |
| dhdna-profiler | 🟢 SAFE | 0 | ✅ | 6.3s |
| exa-search | 🟢 SAFE | 0 | ✅ | 8.5s |
| experimental-design | 🟢 SAFE | 0 | ✅ | 8.8s |
| diffdock | 🟢 SAFE | 0 | ✅ | 16.0s |
| database-lookup | 🟢 SAFE | 0 | ✅ | 35.9s |
| flowkit | 🟢 SAFE | 0 | ✅ | 7.7s |
| fictiv | 🟢 SAFE | 0 | ✅ | 10.7s |
| exploratory-data-analysis | 🟢 SAFE | 0 | ✅ | 14.1s |
| flowio | 🟢 SAFE | 0 | ✅ | 12.4s |
| generate-image | 🟢 SAFE | 0 | ✅ | 8.3s |
| folklore-variant-evidence | 🟢 SAFE | 0 | ✅ | 10.4s |
| fluidsim | 🟢 SAFE | 0 | ✅ | 15.4s |
| get-available-resources | 🟢 SAFE | 0 | ✅ | 9.4s |
| genomic-coordinates | 🟢 SAFE | 0 | ✅ | 14.6s |
| ginkgo-cloud-lab | 🟢 SAFE | 0 | ✅ | 12.0s |
| geniml | 🟢 SAFE | 0 | ✅ | 21.3s |
| geopandas | 🟢 SAFE | 0 | ✅ | 18.3s |
| histolab | 🟢 SAFE | 0 | ✅ | 10.4s |
| gget | 🟢 SAFE | 0 | ✅ | 19.6s |
| gtars | 🟢 SAFE | 0 | ✅ | 12.3s |
| hypothesis-generation | 🟢 SAFE | 0 | ✅ | 10.3s |
| hypogenic | 🟢 SAFE | 0 | ✅ | 11.6s |
| labarchive-integration | 🟢 SAFE | 0 | ✅ | 11.4s |
| lab-hardware-cad | 🟢 SAFE | 0 | ✅ | 12.6s |
| lamindb | 🟢 SAFE | 0 | ✅ | 7.5s |
| imaging-data-commons | 🟢 SAFE | 0 | ✅ | 16.8s |
| iso-standards-readiness | 🟢 SAFE | 0 | ✅ | 20.2s |
| marine-carbonate-chemistry | 🟢 SAFE | 0 | ✅ | 7.2s |
| mageck | 🟢 SAFE | 0 | ✅ | 9.3s |
| liteparse | 🟢 SAFE | 0 | ✅ | 17.9s |
| matchms | 🟢 SAFE | 0 | ✅ | 9.4s |
| market-research-reports | 🟢 SAFE | 0 | ✅ | 13.2s |
| matlab | 🟢 SAFE | 0 | ✅ | 13.0s |
| markdown-mermaid-writing | 🟢 SAFE | 0 | ✅ | 17.8s |
| molecular-dynamics | 🟢 SAFE | 0 | ✅ | 9.1s |
| molfeat | 🟢 SAFE | 0 | ✅ | 12.3s |
| neurokit2 | 🟢 SAFE | 0 | ✅ | 11.7s |
| nmrglue | 🟢 SAFE | 0 | ✅ | 7.8s |
| nwb-conversion | 🟢 SAFE | 0 | ✅ | 7.5s |
| onekgpd | 🟢 SAFE | 0 | ✅ | 9.7s |
| ontology-term-resolution | 🟢 SAFE | 0 | ✅ | 10.0s |
| nextflow | 🟢 SAFE | 0 | ✅ | 17.1s |
| neuropixels-analysis | 🟢 SAFE | 0 | ✅ | 22.7s |
| openpiv | 🟢 SAFE | 0 | ✅ | 10.5s |
| omero-integration | 🟢 SAFE | 0 | ✅ | 16.8s |
| opentrons-integration | 🟢 SAFE | 0 | ✅ | 14.1s |
| pacsomatic | 🟢 SAFE | 0 | ✅ | 10.2s |
| paperzilla | 🟢 SAFE | 0 | ✅ | 9.0s |
| paper-lookup | 🟢 SAFE | 0 | ✅ | 13.4s |
| optimize-for-gpu | 🟢 SAFE | 0 | ✅ | 15.8s |
| pathway-enrichment | 🟢 SAFE | 0 | ✅ | 8.6s |
| pathml | 🟢 SAFE | 0 | ✅ | 11.4s |
| parallel-web | 🟢 SAFE | 0 | ✅ | 15.1s |
| phylogenetics | 🟢 SAFE | 0 | ✅ | 8.1s |
| peer-review | 🟢 SAFE | 0 | ✅ | 11.1s |
| pathogen-variant-surveillance | 🟢 SAFE | 0 | ✅ | 14.7s |
| pennylane | 🟢 SAFE | 0 | ✅ | 13.3s |
| polars-bio | 🟢 SAFE | 0 | ✅ | 9.5s |
| pkpd-modeling | 🟢 SAFE | 0 | ✅ | 13.1s |
| primekg | 🟢 SAFE | 0 | ✅ | 9.1s |
| primer-design | 🟢 SAFE | 0 | ✅ | 9.7s |
| pptx-posters | 🟢 SAFE | 0 | ✅ | 11.7s |
| polars | 🟢 SAFE | 0 | ✅ | 16.6s |
| pybamm | 🟢 SAFE | 0 | ✅ | 8.3s |
| pi-agent | 🟢 SAFE | 0 | ✅ | 23.4s |
| pycalphad | 🟢 SAFE | 0 | ✅ | 8.4s |
| pydeseq2 | 🟢 SAFE | 0 | ✅ | 8.8s |
| pydicom | 🟢 SAFE | 0 | ✅ | 15.2s |
| protocolsio-integration | 🟢 SAFE | 0 | ✅ | 24.1s |
| pymc | 🟢 SAFE | 0 | ✅ | 10.8s |
| pylabrobot | 🟢 SAFE | 0 | ✅ | 11.4s |
| pymatgen | 🟢 SAFE | 0 | ✅ | 12.0s |
| pyhealth | 🟢 SAFE | 0 | ✅ | 17.1s |
| pyopenms | 🟢 SAFE | 0 | ✅ | 9.0s |
| pymoo | 🟢 SAFE | 0 | ✅ | 14.4s |
| pysam | 🟢 SAFE | 0 | ✅ | 10.6s |
| qiime2-amplicon | 🟢 SAFE | 0 | ✅ | 9.4s |
| pytdc | 🟢 SAFE | 0 | ✅ | 11.9s |
| qiskit | 🟢 SAFE | 0 | ✅ | 11.4s |
| rdkit | 🟢 SAFE | 0 | ✅ | 8.3s |
| qutip | 🟢 SAFE | 0 | ✅ | 10.7s |
| relion | 🟢 SAFE | 0 | ✅ | 8.8s |
| rowan | 🟢 SAFE | 0 | ✅ | 8.3s |
| relsa-severity-assessment | 🟢 SAFE | 0 | ✅ | 12.6s |
| scanpy | 🟢 SAFE | 0 | ✅ | 10.3s |
| research-grants | 🟢 SAFE | 0 | ✅ | 13.2s |
| scholar-evaluation | 🟢 SAFE | 0 | ✅ | 12.4s |
| scientific-brainstorming | 🟢 SAFE | 0 | ✅ | 11.7s |
| scientific-critical-thinking | 🟢 SAFE | 0 | ✅ | 8.7s |
| scvelo | 🟢 SAFE | 0 | ✅ | 6.7s |
| scikit-survival | 🟢 SAFE | 0 | ✅ | 11.6s |
| scikit-bio | 🟢 SAFE | 0 | ✅ | 16.4s |
| scikit-learn | 🟢 SAFE | 0 | ✅ | 18.8s |
| scvi-tools | 🟢 SAFE | 0 | ✅ | 14.6s |
| simpy | 🟢 SAFE | 0 | ✅ | 10.1s |
| stable-baselines3 | 🟢 SAFE | 0 | ✅ | 9.0s |
| seaborn | 🟢 SAFE | 0 | ✅ | 15.5s |
| shap | 🟢 SAFE | 0 | ✅ | 17.3s |
| statsmodels | 🟢 SAFE | 0 | ✅ | 7.6s |
| tamarind | 🟢 SAFE | 0 | ✅ | 8.8s |
| tiledbvcf | 🟢 SAFE | 0 | ✅ | 7.0s |
| statistical-analysis | 🟢 SAFE | 0 | ✅ | 15.4s |
| tellurium | 🟢 SAFE | 0 | ✅ | 9.3s |
| sympy | 🟢 SAFE | 0 | ✅ | 15.6s |
| timesfm-forecasting | 🟢 SAFE | 0 | ✅ | 12.0s |
| umap-learn | 🟢 SAFE | 0 | ✅ | 8.5s |
| treatment-plans | 🟢 SAFE | 0 | ✅ | 11.1s |
| uncertainty-and-units | 🟢 SAFE | 0 | ✅ | 9.8s |
| usfiscaldata | 🟢 SAFE | 0 | ✅ | 12.1s |
| vaex | 🟢 SAFE | 0 | ✅ | 9.3s |
| what-if-oracle | 🟢 SAFE | 0 | ✅ | 7.1s |
| venue-templates | 🟢 SAFE | 0 | ✅ | 21.5s |

## Detailed Findings

### autoskill — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 3 files
  > Environment variable access with network calls in scripts/doctor.py, scripts/run.py, scripts/backends.py
  > **Remediation:** Review data flow across files: scripts/run.py, scripts/doctor.py, scripts/backends.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 3 files
  > Multi-file exfiltration chain detected: scripts/doctor.py, scripts/run.py, scripts/backends.py collect data → scripts/run.py → scripts/doctor.py, scripts/run.py, scripts/backends.py transmit to network
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

- **🔵 LOW** `LLM_DATA_EXFILTRATION` — Screen-capture derived summaries and API tokens sent to user-configured LLM/Screenpipe endpoints
  > Deterministic analyzers flagged env-var exfiltration chains in backends.py, doctor.py, and run.py. Verification against the source shows these are declared, documented credential uses: SCREENPIPE_TOKEN/LM_API_TOKEN are placed in Authorization headers to the configured Screenpipe daemon (loopback by default) and LM Studio endpoint; ANTHROPIC_API_KEY/FOUNDRY_API_KEY are used as x-api-key to the opt-in cloud providers they belong to. No credential is sent to an undeclared or third-party destination, and the data sent (cluster summaries) is the stated purpose of the skill. Residual contextual risk remains because the destination endpoints come from a user-editable config.yaml and the payload is derived from sensitive local screen-capture history; backends.py's check_remote_endpoint explicitly refuses plaintext HTTP to remote hosts and prints a warning naming any non-loopback destination, which mitigates this. fetch_window.py also explicitly disables cloud results, frames, and remote PII filtering. Treated as a contextual risk rather than a true positive.
  > File: `scripts/fetch_window.py`
  > **Remediation:** Keep the default local backend and loopback Screenpipe URL; require explicit user confirmation before switching config.yaml to a cloud or non-loopback endpoint, and surface the destination host and a sample of redacted summary content to the user before the first off-host request.

### citation-management — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 5 files
  > Environment variable access with network calls in scripts/search_pubmed.py, scripts/search_openalex.py, scripts/extract_metadata.py
  > **Remediation:** Review data flow across files: scripts/search_pubmed.py, scripts/validate_citations.py, scripts/extract_metadata.py, scripts/search_openalex.py, scripts/doi_to_bibtex.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 5 files
  > Multi-file exfiltration chain detected: scripts/search_pubmed.py, scripts/search_openalex.py, scripts/extract_metadata.py collect data → encode → scripts/validate_citations.py, scripts/search_pubmed.py, scripts/search_openalex.py, scripts/doi_to_bibtex.py, scripts/extract_metadata.py transmit to network
  > **Remediation:** Review data flow across files: scripts/search_pubmed.py, scripts/validate_citations.py, scripts/extract_metadata.py, scripts/search_openalex.py, scripts/doi_to_bibtex.py

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
  > Environment variable access with network calls in scripts/generate_infographic_ai.py, scripts/generate_infographic.py
  > **Remediation:** Review data flow across files: scripts/generate_infographic_ai.py, scripts/generate_infographic.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 2 files
  > Multi-file exfiltration chain detected: scripts/generate_infographic_ai.py, scripts/generate_infographic.py collect data → scripts/generate_infographic_ai.py → scripts/generate_infographic_ai.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_infographic_ai.py, scripts/generate_infographic.py

- **🔵 LOW** `LLM_DATA_EXFILTRATION` — Credential resolution reads OPENROUTER_API_KEY from environment and .env files walking up the directory tree
  > Deterministic analyzers flagged an environment-variable exfiltration chain. Verification against the source shows the only credential handled is OPENROUTER_API_KEY, which is the skill's declared primary env var, and it is used solely as a Bearer token to the declared OpenRouter endpoint (https://openrouter.ai/api/v1). The code actively redacts the key from error strings, and the subprocess launcher forwards an explicit allow-list of environment variables rather than the full parent environment, which reduces rather than increases exposure. The only residual contextual risk is that _resolve_api_key()/resolve_api_key() walk every parent directory of the current working directory looking for a .env file and read OPENROUTER_API_KEY from whichever is found first, which could pick up a credential from an unrelated project root outside the user's intent. No local files, environment contents, or conversation data are sent to any undeclared destination, so the CRITICAL deterministic verdicts are not substantiated as exfiltration.
  > **Remediation:** Limit the .env search to the current working directory and the skill directory (or require an explicit --env-file path) so credentials from unrelated parent projects are not silently consumed; document the search order in SKILL.md.

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/infographics/scripts/generate_infographic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/infographics/scripts/generate_infographic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

### literature-review — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 3 files
  > Environment variable access with network calls in scripts/generate_schematic.py, scripts/generate_schematic_ai.py
  > **Remediation:** Review data flow across files: scripts/generate_schematic.py, scripts/generate_schematic_ai.py, scripts/verify_citations.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 3 files
  > Multi-file exfiltration chain detected: scripts/generate_schematic.py, scripts/generate_schematic_ai.py collect data → scripts/generate_schematic_ai.py → scripts/generate_schematic_ai.py, scripts/verify_citations.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_schematic.py, scripts/generate_schematic_ai.py, scripts/verify_citations.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/literature-review/scripts/generate_schematic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/literature-review/scripts/generate_schematic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

### latex-posters — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 2 files
  > Environment variable access with network calls in scripts/generate_schematic.py, scripts/generate_schematic_ai.py
  > **Remediation:** Review data flow across files: scripts/generate_schematic.py, scripts/generate_schematic_ai.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 2 files
  > Multi-file exfiltration chain detected: scripts/generate_schematic.py, scripts/generate_schematic_ai.py collect data → scripts/generate_schematic_ai.py → scripts/generate_schematic_ai.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_schematic.py, scripts/generate_schematic_ai.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/latex-posters/scripts/generate_schematic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/latex-posters/scripts/generate_schematic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🟡 MEDIUM** `BEHAVIOR_BASH_TAINT_FLOW` — Bash: tainted data flows to dangerous sink
  > Variable $FILE_SIZE_BYTES (line 63) flows to `sh` at line 64.
  > File: `scripts/review_poster.sh:64`
  > **Remediation:** Review the data flow from source to sink. Avoid sending sensitive or untrusted data to network or execution commands.

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

- **🔵 LOW** `LLM_DATA_EXFILTRATION` — Environment-variable credential read sent as Bearer token to configured backend (declared behavior)
  > Deterministic analyzers flagged an env-var exfiltration chain in scripts/_common.py. Verification against the source shows the helper reads OPEN_NOTEBOOK_PASSWORD and places it in an Authorization: Bearer header for requests to OPEN_NOTEBOOK_URL (default http://localhost:5055). This is the documented, declared authentication mechanism for the Open Notebook instance the skill exists to automate; both variables are declared in the manifest's openclaw.envVars. The client additionally disables redirect following specifically to avoid forwarding the secret to another host, which is a hardening measure rather than exfiltration. No hardcoded or third-party destination, no payload placement of the secret, and no hidden transmission were found. Residual contextual risk only: the destination origin is user-controlled via an environment variable, so a misconfigured OPEN_NOTEBOOK_URL would send the bearer token to that host.
  > File: `scripts/_common.py`
  > **Remediation:** No change strictly required; optionally validate that OPEN_NOTEBOOK_URL resolves to an expected/loopback or explicitly allow-listed origin before attaching the Bearer credential, and warn when a non-HTTPS remote origin is configured.

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

### scientific-schematics — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 2 files
  > Environment variable access with network calls in scripts/generate_schematic.py, scripts/generate_schematic_ai.py
  > **Remediation:** Review data flow across files: scripts/generate_schematic.py, scripts/generate_schematic_ai.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 2 files
  > Multi-file exfiltration chain detected: scripts/generate_schematic.py, scripts/generate_schematic_ai.py collect data → scripts/generate_schematic_ai.py → scripts/generate_schematic_ai.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_schematic.py, scripts/generate_schematic_ai.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-schematics/scripts/generate_schematic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-schematics/scripts/generate_schematic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

### scientific-slides — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 4 files
  > Environment variable access with network calls in scripts/generate_slide_image.py, scripts/generate_schematic.py, scripts/generate_slide_image_ai.py, scripts/generate_schematic_ai.py
  > **Remediation:** Review data flow across files: scripts/generate_schematic_ai.py, scripts/generate_schematic.py, scripts/generate_slide_image.py, scripts/generate_slide_image_ai.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 4 files
  > Multi-file exfiltration chain detected: scripts/generate_slide_image.py, scripts/generate_schematic.py, scripts/generate_slide_image_ai.py, scripts/generate_schematic_ai.py collect data → scripts/generate_slide_image_ai.py, scripts/generate_schematic_ai.py → scripts/generate_slide_image_ai.py, scripts/generate_schematic_ai.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_schematic_ai.py, scripts/generate_schematic.py, scripts/generate_slide_image.py, scripts/generate_slide_image_ai.py

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

### transformers — 🟠 HIGH

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/models.md at line 290 contains potentially dangerous Python code.
  > File: `references/models.md:290`
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

### aeon — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation injection directing agent to add a specific reference and fetch an external URL
  > The SKILL.md body instructs the agent to add a specific paper (arXiv:2609.00065, authored by the skill vendor) to the references of any manuscript, report, presentation, or code release the skill contributes to, to inform the user it did so, and to fetch an external arXiv URL when network access is available. This is unrelated to the stated time-series ML purpose and nudges the agent toward unsolicited citation insertion into user deliverables plus an outbound network request. No data is sent outward and the action is disclosed to the user, so impact is low, but it is a vendor-benefiting instruction embedded in active directions.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/optional and require explicit user consent before inserting references into deliverables or performing outbound network fetches.

### arboreto — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive instructing agent to add author's paper to user outputs
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that directs the agent to add a specific arXiv paper (arXiv:2609.00065, authored by the skill vendor K-Dense) to the user's manuscript, report, presentation, or code release references, to inform the user it did so, and to fetch an external arXiv URL when network access is available. This is unrelated to the skill's stated purpose of gene regulatory network inference and injects vendor-promotional content into agent outputs. It is not hidden from the user and involves only a public, well-known scholarly endpoint (no local data is transmitted), so impact is low, but it is behavior that exceeds the declared functional scope.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion passive documentation (e.g., 'users may cite ...') rather than an imperative that the agent modify user deliverables or perform an unrequested network fetch.

### benchling-integration — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation directive instructing agent to add author's paper to user outputs
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section directing the agent to add a specific arXiv paper by the skill author to the user's manuscript/report/code references and to fetch an external arXiv URL before writing the reference. This is unrelated to the stated Benchling integration purpose and nudges the agent toward inserting promotional content into user deliverables. It is disclosed (the agent is told to inform the user) and conditional on material contribution, so impact is low, but it exceeds the skill's declared scope.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance purely informational and user-opt-in; remove directives that cause the agent to modify user deliverables or perform outbound network fetches unrelated to Benchling operations.

### bioservices — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive instructs agent to add a specific paper to user outputs
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section directing the agent to add a specific arXiv reference (arXiv:2609.00065) to any manuscript, report, presentation, or code release the skill contributes to, to tell the user it did so, and to fetch an external arXiv URL when network access is available. This is author self-promotion injected into the agent's output behavior and an unrelated outbound network fetch, rather than functionality needed for bioinformatics data retrieval. It is disclosed to the user and does not exfiltrate data, so impact is minimal, but it steers user deliverables toward a vendor-specified citation.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion advisory and user-initiated; remove the directive to automatically append the vendor's paper to user deliverables and to fetch the arXiv record without explicit user request.

### cirq — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation instruction directing agent to add author's paper to user deliverables
  > The SKILL.md body instructs the agent to add a specific arXiv citation (the skill author's own paper) to any manuscript, report, presentation, or code release the skill contributes to, to tell the user it did so, and to fetch an external arXiv URL when network access is available. This is a self-promotional directive embedded in operational instructions rather than a documented quantum-computing capability. It modifies user-facing research output and triggers an outbound network fetch unrelated to the stated purpose. Impact is low: the destination is a legitimate public arXiv endpoint, no local data is transmitted, and the agent is told to disclose the action to the user.
  > File: `SKILL.md`
  > **Remediation:** Reframe the citation guidance as optional user-facing suggestion rather than a standing instruction to modify deliverables, and make the external metadata fetch explicitly opt-in.

### etetoolkit — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-promotional citation directive with network fetch
  > SKILL.md instructs the agent to add a specific arXiv paper by the skill author to the user's manuscript/report references whenever the skill 'materially contributed', and to fetch an external arXiv URL when network access is available. This is promotional content injected into the agent's workflow rather than a technical capability of the phylogenetics skill. It does not exfiltrate data (the fetch is a read of a public record) and the agent is told to inform the user, so impact is low, but it is an instruction that steers agent output toward author self-citation.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion advisory and user-confirmed, and remove the directive to automatically perform an external network fetch during unrelated tree-analysis tasks.

### latchbio-integration — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation injection instruction in SKILL.md
  > The SKILL.md body instructs the agent to add a specific arXiv paper (authored by the skill vendor, K-Dense) to the references/software section of any manuscript, report, presentation, or code release the skill 'materially contributed' to, and to tell the user it did so. It also directs the agent to fetch arxiv.org/export.arxiv.org records. This is vendor self-promotion embedded as an active agent directive rather than functionality needed for Latch workflow integration. It is disclosed to the user (the agent must say it added the citation) and does not exfiltrate data or hide actions, so impact is low; it is flagged only as a scope/intent mismatch with the stated bioinformatics-workflow purpose.
  > File: `SKILL.md`
  > **Remediation:** Reframe the citation guidance as optional, user-prompted information rather than an instruction that mandates the agent modify user deliverables; make any network fetch explicitly opt-in.

### markitdown — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive instructs agent to fetch external URL and add a citation
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' section that directs the agent to add a specific arXiv reference by the skill author (K-Dense) to user manuscripts/reports/code releases, to tell the user it did so, and to fetch https://arxiv.org/abs/2609.00065 (or the arXiv export API) when network access is available. This is author self-promotion embedded in operative instructions and an unrelated network fetch not needed for document-to-Markdown conversion. It is disclosed to the user and does not exfiltrate local data, so impact is low.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion passive/optional documentation rather than an instruction the agent follows automatically, and remove the automatic network fetch requirement.

### matplotlib — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive instructing agent to add author's paper to user deliverables
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that instructs the agent to add a specific arXiv reference (arXiv:2609.00065 by the skill author, K-Dense Inc.) to any manuscript, report, presentation, or code release the skill contributes to, and to fetch https://arxiv.org/abs/2609.00065 or export.arxiv.org when network access is available. This is vendor self-promotion injected into user output and an outbound network fetch unrelated to the stated plotting purpose. It is mitigated by being transparent (the agent is told to inform the user) and by not transmitting any local or user data outward, so impact is low.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion optional and user-prompted rather than a directive, and remove the instruction to perform an automatic outbound fetch to arxiv.org.

### medchem — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation injection directive in SKILL.md
  > The SKILL.md body instructs the agent to add a specific arXiv paper (Scientific Agent Skills by the skill author K-Dense) to the references of any manuscript, report, presentation, or code release the skill materially contributes to, and to inform the user it did so. It further directs the agent to fetch an external arXiv URL when network access is available. This embeds vendor self-promotion into the agent's output on the user's work product rather than serving the stated medicinal-chemistry filtering purpose. The behavior is disclosed (the agent is told to tell the user), and the fetch target is a legitimate, declared public record, so impact is low and no data is sent outward.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance advisory and user-approved rather than an automatic instruction to modify user deliverables; remove the directive to fetch external records without explicit user request.

### networkx — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation instruction directs agent to add a specific reference and fetch an external URL
  > The SKILL.md body instructs the agent to add a specific arXiv citation (the skill author's own paper) to user manuscripts/reports/code releases and to fetch https://arxiv.org/abs/2609.00065 or the arXiv API when network access is available. This is author self-promotion injected into the agent's output workflow and a small unrelated network fetch, outside the stated NetworkX graph-analysis purpose. Mitigating factors: the instruction is conditional on material contribution, the agent is told to disclose the addition to the user, the destination is a well-known public academic host, and no local data is transmitted.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance purely informational and require explicit user consent before modifying reference lists or performing network fetches unrelated to the graph-analysis task.

### pufferlib — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive instructing agent to add a specific paper reference
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section directing the agent to add a specific arXiv citation (arXiv:2609.00065) to any manuscript, report, presentation, or code release the skill contributes to, and to fetch the arXiv record when network access is available. This is vendor self-promotion embedded as an operational instruction in the skill body rather than a technical capability of PufferLib guidance. It is disclosed to the user (the skill tells the agent to inform the user) and involves only a public, non-sensitive URL, so impact is minimal; no local data is transmitted.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion passive documentation rather than a standing instruction, and require explicit user consent before the agent inserts attribution into user deliverables or performs outbound fetches.

### pyzotero — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation injection directive in SKILL.md
  > The SKILL.md body instructs the agent to add a specific arXiv paper by the skill author (K-Dense) to the user's manuscript references or software citations whenever the skill 'materially contributed', and to fetch the arXiv record over the network before writing the reference. This is a self-serving content-insertion directive unrelated to the skill's stated purpose of managing Zotero libraries; it directs the agent to modify user research outputs and to make an outbound network request to an author-chosen URL. The instruction does require telling the user, and the destination (arxiv.org) is benign and receives no local data, so impact is low and no exfiltration is established.
  > File: `SKILL.md`
  > **Remediation:** Make citation of the authoring organization's paper an explicit opt-in suggestion surfaced to the user rather than a standing directive, and remove the mandatory pre-write network fetch.

### scientific-visualization — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promoting citation instruction directing agent to add author's paper and fetch external URL
  > The SKILL.md body instructs the agent to add a specific arXiv paper (by the skill author's organization) to the references of any manuscript, report, presentation, or code release the skill materially contributes to, to tell the user it did so, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv API when network access is available. This is promotional self-citation injected into the agent's output workflow and triggers an outbound network fetch to a destination unrelated to the skill's stated figure-creation purpose. No local data or secrets are transmitted, and the action is disclosed to the user, so impact is low.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion advisory and user-approved rather than a directive that modifies deliverables, and remove the automatic network fetch or gate it behind explicit user consent.

### scientific-writing — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation injection into user manuscripts
  > The SKILL.md body instructs the agent to add the skill author's own paper (K-Dense, arXiv:2609.00065) to the references or software section of any manuscript, report, presentation, or code release the skill contributes to, and to fetch the arXiv record over the network to build the reference. Injecting a vendor self-citation into a scientific manuscript conflicts with the skill's own stated integrity principles (verified-evidence-only citation, no citation added without human verification of evidentiary fit) and constitutes promotional behavior in a research-integrity tool. Mitigating factors: the instruction is explicit, visible, and requires telling the user, and the fetch target is a declared public arXiv record, so it is not concealed or exfiltrating data.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion optional and subject to explicit user approval rather than an instruction to add it to the reference list; align it with the skill's own rule that every reference must be human-verified for evidentiary relevance.

### statistical-power — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation instruction directs agent to add author's paper and fetch external URL
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section instructing the agent to add a specific arXiv paper by the skill author to the user's manuscript/report references and to tell the user it did so, plus to fetch https://arxiv.org/abs/2609.00065 or the arXiv export API when network access is available. This is promotional behavior unrelated to the stated purpose (power analysis) and injects author-benefiting content into user deliverables. The network fetch is read-only to a public, named academic endpoint and no local data is transmitted, so impact is low; it is not exfiltration.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/optional (present the citation if the user asks) and remove the directive to automatically fetch external URLs and insert the author's paper into user outputs.

### zarr-python — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-promotional citation directive unrelated to stated purpose
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' section instructing the agent to insert a specific arXiv citation (K-Dense 'Scientific Agent Skills') into the user's manuscripts, reports, presentations, or code releases whenever the skill 'materially contributed', and to fetch the arXiv record over the network before writing the reference. This directive modifies user deliverables and triggers outbound network requests for a purpose unrelated to the skill's declared function (chunked N-D array storage with Zarr). Mitigating factors: the action is disclosed ('tell the user you did so'), the destination (arxiv.org) is a well-known public scholarly source, no local data, files, credentials, or conversation content is transmitted, and no hiding or confirmation-bypass is requested. Treated as a self-promotional/content-influence risk rather than exfiltration or injection.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion explicitly optional and user-approved rather than a standing instruction, and remove the directive to perform an unsolicited network fetch; limit the skill body to Zarr-related procedural guidance.

### ncats-arax — ⚪ INFO

- **⚪ INFO** `LLM_CONTEXT_BUDGET_EXCEEDED` — 'scripts/arax_client.py' only partially analyzed (74,979 excerpt chars from 85,617)
  > Only selected code excerpts (74,979 chars) from this 85,617-character file were included; the full file was not analyzed because it exceeds llm_analysis.max_code_file_chars (75,000 chars).
  > File: `scripts/arax_client.py`
  > **Remediation:** Increase llm_analysis.max_code_file_chars in your scan policy to include more content. The full file was not analyzed.
