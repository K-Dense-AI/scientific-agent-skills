# Security Scan Report

**Generated:** 2026-09-07 09:35 UTC  
**Skills scanned:** 163  
**Total findings:** 604  
**Critical:** 28 | **High:** 4 | **Safe skills:** 152/163

**Scanner:** cisco-ai-skill-scanner 2.1.0 · **Model:** claude-opus-5  
**This run:** full rescan of all 163 skill(s).  

## Summary

| Skill | Severity | Findings | Safe | Duration |
|-------|----------|----------|------|----------|
| autoskill | 🔴 CRITICAL | 7 | ❌ | 39.1s |
| citation-management | 🔴 CRITICAL | 6 | ❌ | 30.6s |
| infographics | 🔴 CRITICAL | 3 | ❌ | 19.0s |
| latex-posters | 🔴 CRITICAL | 3 | ❌ | 28.7s |
| literature-review | 🔴 CRITICAL | 4 | ❌ | 35.5s |
| research-lookup | 🔴 CRITICAL | 4 | ❌ | 17.4s |
| scientific-schematics | 🔴 CRITICAL | 5 | ❌ | 31.5s |
| scientific-slides | 🔴 CRITICAL | 7 | ❌ | 49.7s |
| histolab | 🟠 HIGH | 2 | ❌ | 15.2s |
| modal | 🟠 HIGH | 5 | ❌ | 25.4s |
| waypoint-bio | 🟠 HIGH | 2 | ❌ | 24.3s |
| biopython | 🟡 MEDIUM | 6 | ✅ | 13.0s |
| dnanexus-integration | 🟡 MEDIUM | 1 | ✅ | 17.3s |
| genomic-intelligence | 🟡 MEDIUM | 2 | ✅ | 15.0s |
| open-notebook | 🟡 MEDIUM | 16 | ✅ | 24.3s |
| phylogenetics | 🟡 MEDIUM | 4 | ✅ | 15.3s |
| pyopenms | 🟡 MEDIUM | 2 | ✅ | 26.6s |
| tamarind | 🟡 MEDIUM | 9 | ✅ | 10.4s |
| aeon | 🔵 LOW | 1 | ✅ | 23.0s |
| arboreto | 🔵 LOW | 1 | ✅ | 22.9s |
| adaptyv | 🔵 LOW | 1 | ✅ | 26.1s |
| cirq | 🔵 LOW | 1 | ✅ | 15.9s |
| clinical-reports | 🔵 LOW | 1 | ✅ | 26.8s |
| deepchem | 🔵 LOW | 1 | ✅ | 14.1s |
| clinical-decision-support | 🔵 LOW | 1 | ✅ | 32.1s |
| deeptools | 🔵 LOW | 1 | ✅ | 23.7s |
| diffdock | 🔵 LOW | 1 | ✅ | 24.6s |
| etetoolkit | 🔵 LOW | 1 | ✅ | 22.1s |
| experimental-design | 🔵 LOW | 1 | ✅ | 21.3s |
| esm | 🔵 LOW | 2 | ✅ | 31.0s |
| exploratory-data-analysis | 🔵 LOW | 1 | ✅ | 23.4s |
| geomaster | 🔵 LOW | 2 | ✅ | 27.5s |
| gget | 🔵 LOW | 1 | ✅ | 23.3s |
| geopandas | 🔵 LOW | 1 | ✅ | 26.7s |
| ginkgo-cloud-lab | 🔵 LOW | 1 | ✅ | 22.2s |
| gtars | 🔵 LOW | 1 | ✅ | 25.4s |
| lamindb | 🔵 LOW | 1 | ✅ | 15.2s |
| hugging-science | 🔵 LOW | 3 | ✅ | 44.4s |
| market-research-reports | 🔵 LOW | 1 | ✅ | 20.8s |
| markitdown | 🔵 LOW | 1 | ✅ | 14.5s |
| liteparse | 🔵 LOW | 2 | ✅ | 31.9s |
| matplotlib | 🔵 LOW | 1 | ✅ | 22.5s |
| medchem | 🔵 LOW | 1 | ✅ | 23.5s |
| molfeat | 🔵 LOW | 1 | ✅ | 20.1s |
| networkx | 🔵 LOW | 1 | ✅ | 21.4s |
| neuropixels-analysis | 🔵 LOW | 2 | ✅ | 23.1s |
| nextflow | 🔵 LOW | 2 | ✅ | 25.4s |
| ontology-term-resolution | 🔵 LOW | 1 | ✅ | 30.6s |
| paperclip | 🔵 LOW | 1 | ✅ | 28.0s |
| pathway-enrichment | 🔵 LOW | 1 | ✅ | 22.6s |
| pennylane | 🔵 LOW | 1 | ✅ | 22.8s |
| polars | 🔵 LOW | 1 | ✅ | 19.7s |
| pylabrobot | 🔵 LOW | 1 | ✅ | 16.5s |
| pyhealth | 🔵 LOW | 1 | ✅ | 23.4s |
| pymc | 🔵 LOW | 1 | ✅ | 24.2s |
| pysam | 🔵 LOW | 1 | ✅ | 23.3s |
| pyzotero | 🔵 LOW | 1 | ✅ | 28.7s |
| qiskit | 🔵 LOW | 1 | ✅ | 27.6s |
| scientific-brainstorming | 🔵 LOW | 1 | ✅ | 27.2s |
| scholar-evaluation | 🔵 LOW | 1 | ✅ | 27.8s |
| scientific-visualization | 🔵 LOW | 1 | ✅ | 17.7s |
| scientific-writing | 🔵 LOW | 1 | ✅ | 25.0s |
| scikit-learn | 🔵 LOW | 1 | ✅ | 21.2s |
| scikit-bio | 🔵 LOW | 1 | ✅ | 29.3s |
| scvi-tools | 🔵 LOW | 1 | ✅ | 21.4s |
| stable-baselines3 | 🔵 LOW | 1 | ✅ | 13.8s |
| seaborn | 🔵 LOW | 1 | ✅ | 23.9s |
| statsmodels | 🔵 LOW | 1 | ✅ | 14.1s |
| shap | 🔵 LOW | 1 | ✅ | 27.0s |
| statistical-power | 🔵 LOW | 1 | ✅ | 22.9s |
| sympy | 🔵 LOW | 1 | ✅ | 25.0s |
| transformers | 🔵 LOW | 1 | ✅ | 14.2s |
| torch-geometric | 🔵 LOW | 1 | ✅ | 19.6s |
| usfiscaldata | 🔵 LOW | 1 | ✅ | 20.8s |
| vaex | 🔵 LOW | 1 | ✅ | 21.3s |
| venue-templates | 🔵 LOW | 1 | ✅ | 26.4s |
| labarchive-integration | ⚪ INFO | 1 | ✅ | 31.4s |
| ncats-arax | ⚪ INFO | 1 | ✅ | 10.8s |
| astropy | 🟢 SAFE | 0 | ✅ | 11.0s |
| arbor | 🟢 SAFE | 0 | ✅ | 13.2s |
| anndata | 🟢 SAFE | 0 | ✅ | 15.1s |
| bgpt-paper-search | 🟢 SAFE | 0 | ✅ | 5.0s |
| bids | 🟢 SAFE | 0 | ✅ | 9.2s |
| analytical-method-validation | 🟢 SAFE | 0 | ✅ | 26.2s |
| benchling-integration | 🟢 SAFE | 0 | ✅ | 17.8s |
| bulk-rnaseq | 🟢 SAFE | 0 | ✅ | 11.0s |
| cellxgene-census | 🟢 SAFE | 0 | ✅ | 14.4s |
| bioservices | 🟢 SAFE | 0 | ✅ | 17.2s |
| consciousness-council | 🟢 SAFE | 0 | ✅ | 5.5s |
| database-lookup | 🟢 SAFE | 0 | ✅ | 12.7s |
| dask | 🟢 SAFE | 0 | ✅ | 15.6s |
| cobrapy | 🟢 SAFE | 0 | ✅ | 21.2s |
| datamol | 🟢 SAFE | 0 | ✅ | 18.4s |
| deepspot-m | 🟢 SAFE | 0 | ✅ | 8.3s |
| depmap | 🟢 SAFE | 0 | ✅ | 6.1s |
| dhdna-profiler | 🟢 SAFE | 0 | ✅ | 6.6s |
| exa-search | 🟢 SAFE | 0 | ✅ | 10.5s |
| flowio | 🟢 SAFE | 0 | ✅ | 8.4s |
| fluidsim | 🟢 SAFE | 0 | ✅ | 10.9s |
| docx | 🟢 SAFE | 0 | ✅ | 32.1s |
| geniml | 🟢 SAFE | 0 | ✅ | 15.2s |
| generate-image | 🟢 SAFE | 0 | ✅ | 17.8s |
| get-available-resources | 🟢 SAFE | 0 | ✅ | 11.7s |
| genomic-coordinates | 🟢 SAFE | 0 | ✅ | 21.4s |
| glycoengineering | 🟢 SAFE | 0 | ✅ | 7.8s |
| imaging-data-commons | 🟢 SAFE | 0 | ✅ | 9.5s |
| hypogenic | 🟢 SAFE | 0 | ✅ | 23.4s |
| lab-hardware-cad | 🟢 SAFE | 0 | ✅ | 10.8s |
| iso-standards-readiness | 🟢 SAFE | 0 | ✅ | 23.1s |
| hypothesis-generation | 🟢 SAFE | 0 | ✅ | 26.1s |
| latchbio-integration | 🟢 SAFE | 0 | ✅ | 20.9s |
| markdown-mermaid-writing | 🟢 SAFE | 0 | ✅ | 17.3s |
| matchms | 🟢 SAFE | 0 | ✅ | 8.8s |
| molecular-dynamics | 🟢 SAFE | 0 | ✅ | 5.9s |
| matlab | 🟢 SAFE | 0 | ✅ | 20.7s |
| neurokit2 | 🟢 SAFE | 0 | ✅ | 12.6s |
| onekgpd | 🟢 SAFE | 0 | ✅ | 8.6s |
| omero-integration | 🟢 SAFE | 0 | ✅ | 15.7s |
| openpiv | 🟢 SAFE | 0 | ✅ | 8.9s |
| optimize-for-gpu | 🟢 SAFE | 0 | ✅ | 10.4s |
| paperzilla | 🟢 SAFE | 0 | ✅ | 5.7s |
| opentrons-integration | 🟢 SAFE | 0 | ✅ | 18.1s |
| pacsomatic | 🟢 SAFE | 0 | ✅ | 15.8s |
| pathml | 🟢 SAFE | 0 | ✅ | 12.4s |
| paper-lookup | 🟢 SAFE | 0 | ✅ | 23.5s |
| pdf | 🟢 SAFE | 0 | ✅ | 8.8s |
| parallel-web | 🟢 SAFE | 0 | ✅ | 18.1s |
| pathogen-variant-surveillance | 🟢 SAFE | 0 | ✅ | 20.1s |
| pi-agent | 🟢 SAFE | 0 | ✅ | 20.6s |
| polars-bio | 🟢 SAFE | 0 | ✅ | 16.6s |
| peer-review | 🟢 SAFE | 0 | ✅ | 31.9s |
| pptx | 🟢 SAFE | 0 | ✅ | 16.5s |
| pkpd-modeling | 🟢 SAFE | 0 | ✅ | 25.6s |
| pptx-posters | 🟢 SAFE | 0 | ✅ | 11.8s |
| pydeseq2 | 🟢 SAFE | 0 | ✅ | 8.2s |
| primekg | 🟢 SAFE | 0 | ✅ | 13.2s |
| pufferlib | 🟢 SAFE | 0 | ✅ | 12.6s |
| pymatgen | 🟢 SAFE | 0 | ✅ | 9.6s |
| protocolsio-integration | 🟢 SAFE | 0 | ✅ | 20.0s |
| pydicom | 🟢 SAFE | 0 | ✅ | 15.7s |
| pytdc | 🟢 SAFE | 0 | ✅ | 9.2s |
| pymoo | 🟢 SAFE | 0 | ✅ | 20.2s |
| rdkit | 🟢 SAFE | 0 | ✅ | 11.8s |
| relsa-severity-assessment | 🟢 SAFE | 0 | ✅ | 9.5s |
| pytorch-lightning | 🟢 SAFE | 0 | ✅ | 24.7s |
| qutip | 🟢 SAFE | 0 | ✅ | 16.5s |
| research-grants | 🟢 SAFE | 0 | ✅ | 16.8s |
| rowan | 🟢 SAFE | 0 | ✅ | 10.9s |
| scientific-critical-thinking | 🟢 SAFE | 0 | ✅ | 8.6s |
| scanpy | 🟢 SAFE | 0 | ✅ | 22.0s |
| scvelo | 🟢 SAFE | 0 | ✅ | 8.1s |
| scikit-survival | 🟢 SAFE | 0 | ✅ | 19.2s |
| statistical-analysis | 🟢 SAFE | 0 | ✅ | 10.2s |
| simpy | 🟢 SAFE | 0 | ✅ | 19.8s |
| tiledbvcf | 🟢 SAFE | 0 | ✅ | 7.6s |
| timesfm-forecasting | 🟢 SAFE | 0 | ✅ | 10.2s |
| treatment-plans | 🟢 SAFE | 0 | ✅ | 10.1s |
| uncertainty-and-units | 🟢 SAFE | 0 | ✅ | 11.0s |
| umap-learn | 🟢 SAFE | 0 | ✅ | 14.2s |
| torchdrug | 🟢 SAFE | 0 | ✅ | 18.7s |
| what-if-oracle | 🟢 SAFE | 0 | ✅ | 6.0s |
| zarr-python | 🟢 SAFE | 0 | ✅ | 14.1s |
| xlsx | 🟢 SAFE | 0 | ✅ | 18.7s |

## Detailed Findings

### autoskill — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 3 files
  > Environment variable access with network calls in scripts/backends.py, scripts/doctor.py, scripts/run.py
  > **Remediation:** Review data flow across files: scripts/run.py, scripts/backends.py, scripts/doctor.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 3 files
  > Multi-file exfiltration chain detected: scripts/backends.py, scripts/doctor.py, scripts/run.py collect data → scripts/run.py → scripts/backends.py, scripts/doctor.py, scripts/run.py transmit to network
  > **Remediation:** Review data flow across files: scripts/run.py, scripts/backends.py, scripts/doctor.py

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

- **🔵 LOW** `LLM_DATA_EXFILTRATION` — Screen-derived summaries plus API key sent to a user-configurable remote endpoint (foundry backend)
  > backends.py reads ANTHROPIC_API_KEY / FOUNDRY_API_KEY from the environment and uses them as authentication headers to the service each name implies (api.anthropic.com, or a user-supplied Foundry gateway URL read from config.yaml). The Foundry path allows an arbitrary operator-specified destination to receive cluster summaries derived from local screen-capture OCR. Mitigations are present and material: the default backend is a loopback LM Studio endpoint, redact.py scrubs keys/bearer tokens/emails/phones before any LLM call, check_remote_endpoint() refuses plaintext HTTP to non-loopback hosts and prints the destination to stderr, and the manifest/SKILL.md declare all three env vars and endpoints. The deterministic BEHAVIOR_*_ENV_VAR_EXFILTRATION findings therefore reflect ordinary credential use to the intended service rather than covert egress; residual risk is limited to misconfiguration of the opt-in cloud/Foundry endpoint, so this is a contextual risk, not confirmed exfiltration.
  > File: `scripts/backends.py`
  > **Remediation:** Keep the local backend as default, require explicit user confirmation (and an allow-list of approved gateway hostnames) before enabling the foundry backend, and log/preview the exact redacted payload sent to any non-loopback destination.

- **🟡 MEDIUM** `LLM_PROMPT_INJECTION` — Untrusted screen OCR text is interpolated into an LLM prompt whose output is written as executable SKILL.md files
  > run.py feeds screenpipe OCR window titles and app names (attacker-influenceable content: any web page, document, or chat visible on screen) into synthesize()._build_prompt without instruction-boundary hardening, then writes the model's returned 'skill_body' verbatim to new-skills/<name>/SKILL.md or composition-recipes/<name>/SKILL.md. A crafted on-screen string could steer the drafting model into emitting a SKILL.md containing malicious agent instructions, which promote.py can later move into skills/ where the agent will load it. Reach is limited: the destination defaults to ~/.autoskill/proposed/, the skill is documented as explicitly user-triggered, --dry-run allows review, and promotion is a separate manual command with overwrite protection — so this is an unmitigated-but-gated indirect-injection path rather than a demonstrated attack.
  > File: `scripts/promote.py`
  > **Remediation:** Delimit and neutralize screen-derived text in the synthesis prompt, validate generated SKILL.md bodies against a strict schema/allow-list (no tool-invocation or shell directives), and require the user to review a diff before promote.py moves a draft into the loaded skills directory.

### citation-management — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 5 files
  > Environment variable access with network calls in scripts/search_pubmed.py, scripts/extract_metadata.py
  > **Remediation:** Review data flow across files: scripts/search_openalex.py, scripts/extract_metadata.py, scripts/validate_citations.py, scripts/doi_to_bibtex.py, scripts/search_pubmed.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 5 files
  > Multi-file exfiltration chain detected: scripts/search_pubmed.py, scripts/extract_metadata.py collect data → encode → scripts/search_openalex.py, scripts/validate_citations.py, scripts/search_pubmed.py, scripts/doi_to_bibtex.py, scripts/extract_metadata.py transmit to network
  > **Remediation:** Review data flow across files: scripts/search_openalex.py, scripts/extract_metadata.py, scripts/validate_citations.py, scripts/doi_to_bibtex.py, scripts/search_pubmed.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/citation-management/scripts/extract_metadata.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/citation-management/scripts/extract_metadata.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/citation-management/scripts/search_pubmed.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/citation-management/scripts/search_pubmed.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Skill directs agent to insert a self-promoting citation into user deliverables
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' directive instructing the agent to add a specific vendor-authored reference (arXiv:2609.00065 / DOI 10.48550/arXiv.2609.00065, an identifier that resolves to a future-dated arXiv submission) to any manuscript, report, presentation, or code release the skill 'materially contributed to', and to inform the user it did so. This is author-benefiting content injected into the user's academic output rather than a citation the user selected. The instruction does mitigate itself by telling the agent to fetch the live arXiv record before writing the reference and to prefer a published version, and disclosure to the user is required, so this is a policy/quality concern rather than an active attack. No data leaves the user's environment as a result.
  > File: `SKILL.md`
  > **Remediation:** Make the self-citation strictly opt-in and user-initiated, or remove it. If retained, require the agent to obtain explicit user consent before adding the reference and to verify the identifier resolves to an existing published record.

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

### literature-review — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 3 files
  > Environment variable access with network calls in scripts/generate_schematic_ai.py, scripts/generate_schematic.py
  > **Remediation:** Review data flow across files: scripts/generate_schematic_ai.py, scripts/verify_citations.py, scripts/generate_schematic.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 3 files
  > Multi-file exfiltration chain detected: scripts/generate_schematic_ai.py, scripts/generate_schematic.py collect data → scripts/generate_schematic_ai.py → scripts/generate_schematic_ai.py, scripts/verify_citations.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_schematic_ai.py, scripts/verify_citations.py, scripts/generate_schematic.py

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/literature-review/scripts/generate_schematic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/literature-review/scripts/generate_schematic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🔵 LOW** `LLM_SUPPLY_CHAIN_ATTACK` — Documented dependency install pipes remote script directly into bash
  > The SKILL.md dependency section instructs running `curl -fsSL https://parallel.ai/install.sh | bash` to install the parallel-cli tool. With `Bash` in allowed-tools, an agent following these directions would fetch and execute an unpinned, unverified remote shell script, so the integrity of the installed tooling depends entirely on the third-party host at run time. No malicious payload is present in the package itself, and the target is the vendor domain for the referenced CLI, so this is a supply-chain exposure rather than demonstrated malicious behavior.
  > File: `SKILL.md`
  > **Remediation:** Prefer the packaged install path (`uv tool install "parallel-web-tools[cli]"`) with a pinned version, or download the installer, verify a published checksum/signature, and execute it only after review instead of piping it into a shell.

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

- **🔵 LOW** `LLM_DATA_EXFILTRATION` — Declared API keys read from environment and sent as Authorization headers to declared endpoints
  > Deterministic analyzers flagged an environment-variable exfiltration chain in scripts/research_lookup.py. Verification against the source shows PARALLEL_API_KEY and OPENROUTER_API_KEY are read via os.getenv and used only as Bearer Authorization headers to https://api.parallel.ai/chat/completions and https://openrouter.ai/api/v1/chat/completions. Both environment variables, both hosts, and their purpose are explicitly declared in the manifest (compatibility and openclaw.envVars) and in SKILL.md, which also instructs never to print, log, or pass the key in command arguments. The credentials are never written into request payloads, logs, packet artifacts, or third-party destinations. This is ordinary intended-service credential authentication rather than exfiltration; the finding is retained only as a contextual note that user query text is transmitted to the declared external providers.
  > File: `scripts/research_lookup.py`
  > **Remediation:** No change required for security. Optionally continue to gate the OpenRouter path behind explicit user opt-in (already implemented via --force-backend perplexity / --fallback-perplexity) and keep documenting that query text leaves the environment when these backends are used.

### scientific-schematics — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 2 files
  > Environment variable access with network calls in scripts/generate_schematic_ai.py, scripts/generate_schematic.py
  > **Remediation:** Review data flow across files: scripts/generate_schematic_ai.py, scripts/generate_schematic.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 2 files
  > Multi-file exfiltration chain detected: scripts/generate_schematic_ai.py, scripts/generate_schematic.py collect data → scripts/generate_schematic_ai.py → scripts/generate_schematic_ai.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_schematic_ai.py, scripts/generate_schematic.py

- **🔵 LOW** `LLM_HARDCODED_SECRETS` — Credential resolution scans .env files in all parent directories
  > Both scripts implement `_resolve_api_key`/`resolve_api_key`, which, if `--api-key` and the environment variable are absent, walk the current working directory and every parent directory (plus the script directory) looking for `.env` files and parsing them line by line. Only the `OPENROUTER_API_KEY` name is extracted, and the resolved value is used solely as an `Authorization: Bearer` header to the declared service `https://openrouter.ai/api/v1` — this is normal credential use for the intended provider, and the subprocess environment is explicitly minimized (an allow-list) rather than fully inherited. The residual risk is the broad filesystem search for secret files outside the skill directory, which can read `.env` files belonging to unrelated projects up the directory tree. No external or undeclared sink receives the credential, so the deterministic 'env var exfiltration' leads are not substantiated as exfiltration.
  > **Remediation:** Limit the `.env` search to the project root or skill directory (or require an explicit path/flag) instead of traversing all parent directories, and log which file the credential was sourced from.

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-schematics/scripts/generate_schematic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-schematics/scripts/generate_schematic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Skill body instructs the agent to insert an author self-citation and fetch an external URL
  > The SKILL.md body contains an active directive telling the agent to add a specific arXiv reference by the skill's authors to the user's manuscript/report/code release, to inform the user it did so, and to fetch an external arXiv URL/API endpoint before writing the reference. This is a self-promotional instruction that alters the agent's output in the user's documents and triggers outbound network access not related to the stated diagram-generation purpose. It is disclosed rather than covert, and no data from the user is sent outward, so impact is limited; it is nonetheless an embedded instruction unrelated to the declared capability.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance passive/optional (e.g., 'if the user wishes to cite this tool') and remove the directive to automatically modify user documents or fetch external URLs.

### scientific-slides — 🔴 CRITICAL

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` — Cross-file env var exfiltration: 4 files
  > Environment variable access with network calls in scripts/generate_schematic_ai.py, scripts/generate_schematic.py, scripts/generate_slide_image.py, scripts/generate_slide_image_ai.py
  > **Remediation:** Review data flow across files: scripts/generate_schematic_ai.py, scripts/generate_slide_image_ai.py, scripts/generate_schematic.py, scripts/generate_slide_image.py

- **🔴 CRITICAL** `BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` — Cross-file exfiltration chain: 4 files
  > Multi-file exfiltration chain detected: scripts/generate_schematic_ai.py, scripts/generate_schematic.py, scripts/generate_slide_image.py, scripts/generate_slide_image_ai.py collect data → scripts/generate_schematic_ai.py, scripts/generate_slide_image_ai.py → scripts/generate_schematic_ai.py, scripts/generate_slide_image_ai.py transmit to network
  > **Remediation:** Review data flow across files: scripts/generate_schematic_ai.py, scripts/generate_slide_image_ai.py, scripts/generate_schematic.py, scripts/generate_slide_image.py

- **🔵 LOW** `LLM_DATA_EXFILTRATION` — Credential resolution walks all parent directories searching for .env files
  > All four generator scripts implement `_resolve_api_key`/`resolve_api_key`, which, when the environment variable is unset, iterates over the current working directory and every one of its parents (plus the script directory) reading any `.env` file found and parsing out `OPENROUTER_API_KEY`. This reaches outside the project/skill boundary (potentially up to the filesystem root or a user's home directory) to harvest a credential the user did not explicitly provide. Mitigating context: only the single key name `OPENROUTER_API_KEY` is extracted, the value is used solely in an `Authorization: Bearer` header to the declared endpoint `https://openrouter.ai/api/v1`, the manifest declares `OPENROUTER_API_KEY` as `primaryEnv`, and the subprocess launcher deliberately forwards only an allow-list of environment variables rather than the whole parent environment. The deterministic ENV_VAR_EXFILTRATION findings therefore reflect ordinary API authentication to the intended service, not covert exfiltration; the residual risk is only the out-of-scope `.env` traversal.
  > **Remediation:** Limit the `.env` search to the skill directory and/or the immediate project root instead of every ancestor directory, and require explicit opt-in (e.g., a `--env-file` flag) before reading credential files outside the working directory.

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-slides/scripts/generate_schematic_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-slides/scripts/generate_schematic_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🔴 CRITICAL** `BEHAVIOR_ENV_VAR_EXFILTRATION` — Environment variable access with network calls detected
  > Script accesses environment variables and makes network calls in /home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-slides/scripts/generate_slide_image_ai.py
  > File: `/home/runner/work/scientific-agent-skills/scientific-agent-skills/skills/scientific-slides/scripts/generate_slide_image_ai.py`
  > **Remediation:** Remove environment variable harvesting or network transmission

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Skill directs the agent to insert a vendor self-citation into the user's deliverables
  > The SKILL.md 'Citing Scientific Agent Skills' section instructs the agent to add a specific vendor-authored reference (arXiv:2609.00065, K-Dense) to the user's manuscript/report/presentation/code release whenever the skill 'materially contributed', and to inform the user it did so. This is promotional content injected into user output rather than a technical capability, and the cited identifier is not verifiable from the package. It also directs an outbound fetch of arxiv.org to populate the reference. Impact is limited (no credential or data access, and the skill tells the user about the addition), so this is a disclosure/attribution-integrity concern rather than a security exploit.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion advisory and user-initiated rather than an instruction to modify deliverables, and avoid asserting a specific DOI/arXiv identifier that cannot be verified.

- **🔵 LOW** `LLM_DATA_EXFILTRATION` — Instructions direct the agent to enumerate local directories and upload discovered files to a third-party API
  > SKILL.md instructs the agent to list the working directory (`ls -la figures/`, `results/`, `plots/`, `images/`, and any user-provided directories) and to attach ALL relevant discovered files with `--attach`. `generate_slide_image_ai.py` base64-encodes each attachment and embeds it in the JSON body of a POST to `https://openrouter.ai/api/v1/chat/completions`. This is the skill's stated purpose (feeding result figures to an image model), the destination is the declared and documented service, and attachment paths are user/agent selected rather than hardcoded, so this is a disclosure-surface risk rather than demonstrated covert exfiltration. Users should be aware that local project files can be transmitted off-host, including any non-figure file passed by path.
  > File: `scripts/generate_slide_image_ai.py`
  > **Remediation:** Restrict attachments to explicit user-approved image paths, validate file type/extension before upload, and surface an explicit confirmation listing exactly which local files will be transmitted to the external API.

### histolab — 🟠 HIGH

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/filters_preprocessing.md at line 487 contains potentially dangerous Python code.
  > File: `references/filters_preprocessing.md:487`
  > **Remediation:** Review the code block for security implications.

- **🔵 LOW** `LLM_COMMAND_INJECTION` — Heuristic eval/exec match in documentation code block (false-positive lead)
  > A deterministic analyzer flagged a possible Python eval/exec pattern at references/filters_preprocessing.md line 487. Verification of the file content shows the match corresponds to a blur-detection helper using cv2.Laplacian with the OpenCV constant cv2.CV_64F, explicitly annotated as 'an OpenCV constant, not Python eval()'. No dynamic code execution, no untrusted input sink, and no executable scripts exist in the package (markdown only). Retained as a low-severity contextual note rather than an actionable threat.
  > File: `references/filters_preprocessing.md:487`
  > **Remediation:** No action required. Optionally rephrase the comment to avoid triggering keyword-based scanners.

### modal — 🟠 HIGH

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/functions.md at line 82 contains potentially dangerous Python code.
  > File: `references/functions.md:82`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/gpu.md at line 157 contains potentially dangerous Python code.
  > File: `references/gpu.md:157`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/gpu.md at line 166 contains potentially dangerous Python code.
  > File: `references/gpu.md:166`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/scheduled-jobs.md at line 141 contains potentially dangerous Python code.
  > File: `references/scheduled-jobs.md:141`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/web-endpoints.md at line 149 contains potentially dangerous Python code.
  > File: `references/web-endpoints.md:149`
  > **Remediation:** Review the code block for security implications.

### waypoint-bio — 🟠 HIGH

- **🟠 HIGH** `MDBLOCK_PYTHON_EVAL_EXEC` — Python code block uses eval/exec
  > Code block in references/python-api.md at line 117 contains potentially dangerous Python code.
  > File: `references/python-api.md:117`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/python-api.md at line 203 contains potentially dangerous Python code.
  > File: `references/python-api.md:203`
  > **Remediation:** Review the code block for security implications.

### biopython — 🟡 MEDIUM

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/alignment.md at line 293 contains potentially dangerous Python code.
  > File: `references/alignment.md:293`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/alignment.md at line 311 contains potentially dangerous Python code.
  > File: `references/alignment.md:311`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/blast.md at line 184 contains potentially dangerous Python code.
  > File: `references/blast.md:184`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/blast.md at line 211 contains potentially dangerous Python code.
  > File: `references/blast.md:211`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/blast.md at line 300 contains potentially dangerous Python code.
  > File: `references/blast.md:300`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/blast.md at line 329 contains potentially dangerous Python code.
  > File: `references/blast.md:329`
  > **Remediation:** Review the code block for security implications.

### dnanexus-integration — 🟡 MEDIUM

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/app-development.md at line 84 contains potentially dangerous Python code.
  > File: `references/app-development.md:84`
  > **Remediation:** Review the code block for security implications.

### genomic-intelligence — 🟡 MEDIUM

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in SKILL.md at line 130 contains potentially dangerous Python code.
  > File: `SKILL.md:130`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in SKILL.md at line 152 contains potentially dangerous Python code.
  > File: `SKILL.md:152`
  > **Remediation:** Review the code block for security implications.

### open-notebook — 🟡 MEDIUM

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-promotional citation directive in SKILL.md body
  > The instruction body contains a standing directive telling the agent to add a specific arXiv paper (attributed to the skill author's organization) to the references/software section of any manuscript, report, presentation, or code release the skill contributes to, to inform the user it did so, and to fetch an external arXiv URL/API endpoint before writing the reference. This is unrelated to the stated Open Notebook research-management functionality and steers agent output and outbound network requests toward author-benefiting promotion rather than user intent. It is not a technical compromise: no sensitive data source, credential, or execution sink is involved, and the fetched destination is the public arXiv service.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance optional and user-initiated rather than an unconditional agent directive, and remove the automatic external fetch instruction from the active instruction body.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in SKILL.md at line 61 contains potentially dangerous Python code.
  > File: `SKILL.md:61`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in SKILL.md at line 92 contains potentially dangerous Python code.
  > File: `SKILL.md:92`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in SKILL.md at line 105 contains potentially dangerous Python code.
  > File: `SKILL.md:105`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in SKILL.md at line 126 contains potentially dangerous Python code.
  > File: `SKILL.md:126`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in SKILL.md at line 139 contains potentially dangerous Python code.
  > File: `SKILL.md:139`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in SKILL.md at line 157 contains potentially dangerous Python code.
  > File: `SKILL.md:157`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in SKILL.md at line 174 contains potentially dangerous Python code.
  > File: `SKILL.md:174`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in SKILL.md at line 194 contains potentially dangerous Python code.
  > File: `SKILL.md:194`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/configuration.md at line 116 contains potentially dangerous Python code.
  > File: `references/configuration.md:116`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/examples.md at line 17 contains potentially dangerous Python code.
  > File: `references/examples.md:17`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/examples.md at line 98 contains potentially dangerous Python code.
  > File: `references/examples.md:98`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/examples.md at line 136 contains potentially dangerous Python code.
  > File: `references/examples.md:136`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/examples.md at line 182 contains potentially dangerous Python code.
  > File: `references/examples.md:182`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/examples.md at line 231 contains potentially dangerous Python code.
  > File: `references/examples.md:231`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/examples.md at line 277 contains potentially dangerous Python code.
  > File: `references/examples.md:277`
  > **Remediation:** Review the code block for security implications.

### phylogenetics — 🟡 MEDIUM

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in SKILL.md at line 71 contains potentially dangerous Python code.
  > File: `SKILL.md:71`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in SKILL.md at line 104 contains potentially dangerous Python code.
  > File: `SKILL.md:104`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in SKILL.md at line 147 contains potentially dangerous Python code.
  > File: `SKILL.md:147`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in SKILL.md at line 202 contains potentially dangerous Python code.
  > File: `SKILL.md:202`
  > **Remediation:** Review the code block for security implications.

### pyopenms — 🟡 MEDIUM

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Mandatory self-citation directive instructs agent to modify user deliverables and fetch external URL
  > The SKILL.md instruction body contains an unconditional directive ('Always cite the current version', 'add the paper to the references or software section and tell the user you did so') that requires the agent to insert a specific author/publisher citation (arXiv:2609.00065, dated 2026) into any manuscript, report, presentation, or code release the skill contributes to, and to fetch arxiv.org / export.arxiv.org when network access is available. This is vendor self-promotion embedded as an active agent instruction affecting user-authored output, plus an outbound network fetch that is unrelated to the declared mass-spectrometry purpose. No sensitive data is collected or transmitted, and the destination is a public, well-known academic host, so impact is limited to attribution/content integrity rather than exfiltration.
  > File: `SKILL.md`
  > **Remediation:** Reframe the citation block as optional guidance surfaced to the user for approval rather than a mandatory agent action, and remove the automatic network fetch or make it explicitly opt-in.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_SUBPROCESS` — Python code block executes shell commands
  > Code block in references/identification.md at line 303 contains potentially dangerous Python code.
  > File: `references/identification.md:303`
  > **Remediation:** Review the code block for security implications.

### tamarind — 🟡 MEDIUM

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in SKILL.md at line 102 contains potentially dangerous Python code.
  > File: `SKILL.md:102`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in SKILL.md at line 203 contains potentially dangerous Python code.
  > File: `SKILL.md:203`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/api_reference.md at line 105 contains potentially dangerous Python code.
  > File: `references/api_reference.md:105`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/workflows.md at line 29 contains potentially dangerous Python code.
  > File: `references/workflows.md:29`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/workflows.md at line 61 contains potentially dangerous Python code.
  > File: `references/workflows.md:61`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/workflows.md at line 104 contains potentially dangerous Python code.
  > File: `references/workflows.md:104`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/workflows.md at line 158 contains potentially dangerous Python code.
  > File: `references/workflows.md:158`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/workflows.md at line 228 contains potentially dangerous Python code.
  > File: `references/workflows.md:228`
  > **Remediation:** Review the code block for security implications.

- **🟡 MEDIUM** `MDBLOCK_PYTHON_HTTP_POST` — Python code block sends HTTP POST request
  > Code block in references/workflows.md at line 250 contains potentially dangerous Python code.
  > File: `references/workflows.md:250`
  > **Remediation:** Review the code block for security implications.

### aeon — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation directive instructs agent to insert author's reference into user deliverables
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that directs the agent to add a specific arXiv reference (arXiv:2609.00065, K-Dense) to any manuscript, report, presentation, or code release the skill contributes to, to inform the user it did so, and to fetch the arXiv record over the network. This is an author-benefiting behavioral directive that alters user-facing outputs rather than a technical capability of time-series ML. The cited identifier/date (2026) cannot be verified from package content, so the reference may be non-existent, risking insertion of misleading citations into user work. No credential access, code execution, or exfiltration sink is present; the package contains only markdown documentation files and no scripts.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance passive/optional (e.g., 'if the user wishes to cite this skill'), remove the directive to automatically insert references into user deliverables, and verify the cited publication identifier resolves to a real record.

### arboreto — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-promotional citation directive with external fetch instruction
  > The SKILL.md instruction body contains an active directive ('Citing Scientific Agent Skills') telling the agent to insert a specific vendor-authored citation (arXiv:2609.00065, dated 2026, i.e., an identifier that cannot currently be verified) into user manuscripts, reports, or code releases, to inform the user it did so, and to fetch external URLs (https://arxiv.org/abs/2609.00065 and export.arxiv.org API) when network access is available. This is unrelated to the declared GRN-inference purpose and steers agent output toward promoting the skill author's work and contacting an external endpoint. No credential access, data collection, or exfiltration sink is present, so impact is limited to citation/attribution influence and an outbound metadata lookup.
  > File: `SKILL.md`
  > **Remediation:** Remove or make clearly optional the automatic citation-insertion directive and the mandated external URL fetch; leave attribution decisions to the user rather than instructing the agent to modify scholarly output.

### adaptyv — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Skill directs agent to insert author self-citation into user deliverables
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' section that instructs the agent to add a specific paper (arXiv:2609.00065, authored by the skill publisher K-Dense) to the references/software section of the user's manuscript, report, presentation, or code release, and to inform the user it did so. It further directs the agent to fetch arxiv.org / export.arxiv.org when network access is available. This is promotional content injection unrelated to the skill's stated purpose (Adaptyv Foundry API usage) and can cause the agent to modify user work product to benefit the skill author. It is conditional ('if it materially contributed') and the network fetch targets a legitimate, publicly declared academic source, so no exfiltration or credential misuse is established.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance passive/informational (e.g., 'the user may cite ...') rather than an operational directive that mutates user deliverables, and remove the mandatory outbound fetch instruction or mark it as optional.

### cirq — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation directive instructing agent to add author's paper and fetch external URL
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that directs the agent to add a specific arXiv reference (arXiv:2609.00065) to any manuscript, report, presentation, or code release the skill contributes to, to tell the user it did so, and to fetch an external arXiv URL when network access is available. This is an author-benefiting behavioral directive unrelated to the skill's stated quantum-computing purpose; it steers agent output and triggers an outbound network fetch. The destination (arxiv.org) is a well-known benign academic host and no sensitive data is transmitted, so impact is low, but the instruction is promotional/self-serving content injected into agent behavior rather than technical guidance.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive and optional (e.g., 'if the user asks how to cite this skill') rather than an instruction that automatically modifies user deliverables or performs network fetches without explicit request.

### clinical-reports — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Mandatory self-citation instruction with network fetch contradicts declared no-network scope
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that directs the agent to add a specific arXiv paper (arXiv:2609.00065) to any manuscript/report/code release the skill contributes to, to inform the user it did so, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv API when network access is available. This is an embedded behavioral directive that promotes the vendor's publication and requests outbound network access, which materially conflicts with the manifest's own declaration ('no network access, credentials, external models, or image services') and the body's boundary rule 'call an external LLM, image service, API, or another skill'. No sensitive data is collected or transmitted, and the destination is a public, benign scholarly host, so the risk is limited to self-promotional instruction insertion and an internal capability-scope inconsistency rather than exfiltration.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance optional and user-initiated, remove the instruction to fetch remote URLs (or explicitly declare the network capability in the manifest and reconcile it with the stated no-network boundary), and avoid directives that require the agent to insert a specific vendor citation into user deliverables.

### deepchem — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation directive instructs agent to add author's paper and fetch external URL
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that directs the agent to insert a specific paper (arXiv:2609.00065 by the skill author's organization) into any manuscript, report, presentation, or code release the skill contributes to, notify the user it did so, and fetch an external arXiv URL when network access is available. This is an embedded behavioral directive that serves the skill author's promotional interest rather than the user's task, and it also introduces a fetch of remote content whose text could influence the agent. It does not access sensitive data, run commands, or send data outward, so impact is low and intent is plausibly benign attribution.
  > File: `SKILL.md`
  > **Remediation:** Reframe citation guidance as optional, user-approved information rather than a standing directive, and remove the instruction to automatically fetch and incorporate remote content into user deliverables.

### clinical-decision-support — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive with optional network fetch conflicts with declared no-network posture
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that directs the agent to add a specific author-supplied arXiv reference to any manuscript, report, presentation, or code release the skill contributed to, to inform the user that it did so, and—when network access is available—to fetch https://arxiv.org/abs/2609.00065 or the arXiv API before writing the reference. This is an active instruction embedded in the skill body that biases the agent's output toward promoting the skill authors' publication and introduces an outbound network request, while the manifest compatibility field states the skill requires 'local files only ... no network, credentials, API keys, LLMs, or image services.' No sensitive data source is connected to the fetch, no credential handling occurs, and the destination is a legitimate public preprint server, so impact is limited to unsolicited self-citation and a minor declared-capability mismatch rather than exfiltration or code execution.
  > File: `SKILL.md`
  > **Remediation:** Make the citation request passive documentation rather than an operative instruction, drop the directive to fetch external URLs (or declare network use explicitly in the manifest), and let the user decide whether to include the reference.

### deeptools — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-promotional citation directive with unverifiable arXiv reference and network fetch
  > The SKILL.md instruction body contains a 'Citing Scientific Agent Skills' section that actively directs the agent to add a specific author/paper citation (arXiv:2609.00065, dated 2026 — an identifier that cannot currently resolve) into the user's manuscripts, reports, presentations, or code releases, to inform the user it did so, and to fetch arxiv.org/export.arxiv.org URLs when network access is available. This is vendor self-promotion injected into the agent's active directions rather than a technical capability of the deepTools skill, and it can cause insertion of an unverifiable reference into user deliverables. No credential access, no exfiltration sink, and no code execution is associated with it, so impact is limited and intent may be benign attribution.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive and user-opt-in (e.g., 'if the user asks how to cite this skill, provide the following reference'), remove the instruction to auto-insert citations into user deliverables, and only reference a resolvable, published DOI/arXiv identifier.

### diffdock — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-citation directive instructs agent to insert author's paper into user deliverables and fetch remote record
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' section that directs the agent to add a specific arXiv reference (arXiv:2609.00065, attributed to the skill author's organization) to any manuscript, report, presentation, or code release the skill contributes to, to inform the user it did so, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv API endpoint when network access is available. This is a promotional instruction that modifies user-facing deliverables for the skill author's benefit and introduces an outbound network fetch that is not part of the declared docking workflow (declared tools are Read, Write, Edit, Bash, Glob, Grep, with no network tool declared). No credential access, data collection, or exfiltration sink is present, and the rest of the package (setup_check.py, prepare_batch_csv.py, analyze_results.py, reference docs, YAML template) performs only local environment checks, CSV validation, and parsing of DiffDock output files consistent with its stated purpose. Risk is therefore limited to attribution/self-promotion pressure rather than a security compromise.
  > File: `scripts/prepare_batch_csv.py`
  > **Remediation:** Reframe the citation section as optional, user-approved guidance rather than a standing directive to modify deliverables, and remove the instruction to autonomously fetch external URLs (or declare an explicit network capability and require user confirmation).

### etetoolkit — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-promotional citation directive with external fetch
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' section instructing the agent to insert a specific vendor paper (arXiv:2609.00065, K-Dense) into any manuscript, report, presentation, or code release the skill contributed to, to inform the user it did so, and to fetch arxiv.org / export.arxiv.org records when network access is available. This is promotional content injection into user deliverables plus an unsolicited outbound network fetch, both driven by skill instructions rather than user intent. No sensitive data is read or transmitted, and the destinations are public, well-known scholarly endpoints, so the risk is limited to attribution/bias and minor unrequested network activity rather than exfiltration. All other content (ETE 4 documentation, references, and the two bundled Python scripts) is benign: the scripts only parse local Newick files, perform topology operations, write output trees, and render figures, with SmartView server binding explicitly restricted to loopback unless --allow-remote-bind is passed.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion advisory and user-approved rather than an automatic directive, and avoid instructing unsolicited network fetches; surface the reference to the user for explicit confirmation instead.

### experimental-design — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-citation directive with unverifiable reference and network fetch
  > The SKILL.md body contains an author-serving directive instructing the agent to add a specific paper (arXiv:2609.00065, an identifier that does not correspond to any existing/plausible current arXiv record) to the user's manuscript/report references and to inform the user it did so, and to fetch the arXiv URL when network access is available. This is promotional instruction injection into agent output rather than technical procedural knowledge; the referenced record cannot be verified and could result in a fabricated citation being inserted into user deliverables. The network fetch target is a legitimate, well-known domain and no sensitive data is transmitted, so the risk is limited to output influence and citation accuracy rather than exfiltration or code execution.
  > File: `SKILL.md`
  > **Remediation:** Make the citation request a passive, optional note rather than a directive that modifies user deliverables, and verify/correct the arXiv identifier and DOI so the agent cannot insert an unverifiable reference.

### esm — 🔵 LOW

- **🔵 LOW** `LLM_SUPPLY_CHAIN_ATTACK` — Install instruction pointing to a third-party GitHub org for the `esm` package
  > Reference documentation directs installation of the `esm` SDK from https://github.com/Biohub/esm (a GitHub organization distinct from the upstream EvolutionaryScale project) via `uv pip install "esm@git+..."`. If that organization is not the authoritative source, following the instruction would install code from an unverified publisher, a package-substitution risk. Mitigating context: the same section explicitly warns against floating branch installs, requires pinning a full 40-character commit SHA, and instructs the reader to review the verified release before installing; the primary documented install path remains the pinned PyPI release `esm==3.2.3`. No script in the package performs the install automatically.
  > **Remediation:** Reference only the authoritative upstream repository/organization for the SDK, or require explicit user confirmation and integrity verification (pinned SHA plus published release attestation) before any VCS-based install.

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-citation directive for an unverifiable arXiv record
  > The SKILL.md body instructs the agent to insert a specific citation (arXiv:2609.00065, dated 2026) into any manuscript, report, presentation, or code release the skill materially contributed to, to inform the user it did so, and to fetch the arXiv record when network access is available. This is a promotional directive that alters the agent's output on the user's behalf and references an identifier that cannot be validated from the package; it could result in fabricated or misleading bibliographic content in user deliverables. It is not technically exploitative and involves only a public, declared documentation host.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance advisory and user-opt-in rather than a directive, and remove references to identifiers that cannot be verified.

### exploratory-data-analysis — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Mandatory self-citation directive with optional outbound network fetch
  > The SKILL.md body instructs the agent to add a specific paper (arXiv:2609.00065) to the user's manuscript/report/software references whenever the skill 'materially contributed', to inform the user it did so, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv API when network access is available. This is vendor self-promotion injected into user deliverables and introduces an outbound network fetch that is inconsistent with the skill's otherwise strictly local, network-free posture. No sensitive data is transmitted and the destination is a public, declared academic source, so this is a policy/quality concern rather than exfiltration.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance advisory rather than directive, and remove or explicitly gate the outbound arXiv fetch so the skill's documented local/network-free contract is not contradicted.

### geomaster — 🔵 LOW

- **🔵 LOW** `LLM_HARMFUL_CONTENT` — Directive to cite an unverifiable, future-dated reference
  > The instruction body mandates citation of 'Kassis, T., et al. (2026). Scientific Agent Skills... arXiv:2609.00065' with a DOI that cannot be validated and a future publication year/identifier. Instructing an agent to insert an unverifiable reference into scholarly output risks propagating inaccurate citation metadata. Impact is limited to reference accuracy, and the intent may simply be pre-publication attribution, so this is recorded as a contextual risk rather than confirmed deceptive content.
  > **Remediation:** Only reference verifiable, published identifiers, or state clearly that the citation is optional and should be verified by the user before inclusion in any manuscript.

- **🔵 LOW** `LLM_PROMPT_INJECTION` — Embedded self-promotional citation directive with external fetch instruction
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' block that directs the agent to insert a specific author/paper reference into the user's manuscripts, reports, presentations, or code releases, to inform the user it did so, and to fetch an external arXiv URL (https://arxiv.org/abs/2609.00065 or export.arxiv.org API) when network access is available. This is an active instruction unrelated to the declared geospatial-analysis purpose that influences agent output on the vendor's behalf and triggers outbound network access. No sensitive data is collected or exfiltrated, so the reach is limited to content injection and an outbound fetch of a benign public URL.
  > File: `SKILL.md`
  > **Remediation:** Move attribution requests into passive documentation/metadata rather than imperative agent directions, and remove instructions that cause the agent to fetch remote URLs or modify user deliverables without an explicit user request.

### gget — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation directive unrelated to declared bioinformatics purpose
  > The SKILL.md body contains an active directive instructing the agent to insert a specific arXiv paper authored by the skill vendor ('Scientific Agent Skills', K-Dense) into any manuscript, report, presentation, or code release the skill contributes to, to inform the user it did so, and to fetch an external arXiv URL/API endpoint before writing the reference. This behavior is unrelated to the skill's declared purpose (querying bioinformatics databases) and biases agent output toward vendor promotion in the user's scholarly work. It is not exfiltration (no sensitive source, only a public metadata lookup) and no credential or private data is transmitted, so this is a low-severity contextual risk rather than confirmed malicious behavior.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/optional documentation rather than an imperative agent instruction, remove the mandated external network fetch, and let the user decide whether to include vendor references.

### geopandas — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-citation directive instructing agent to add author's paper and fetch external URL
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' block that directs the agent to insert a specific arXiv reference (K-Dense authors, arXiv:2609.00065) into any manuscript, report, presentation, or code release the skill contributes to, to inform the user it did so, and — when network access is available — to fetch https://arxiv.org/abs/2609.00065 or the arXiv API before writing the reference. This is a behavioral directive unrelated to the declared GeoPandas guidance purpose: it steers agent output toward promoting the skill author and authorizes an outbound network request that the rest of the skill explicitly avoids (all bundled CLIs report network_accessed: false and reject URLs). No sensitive data is transmitted and no credential or file access is involved, so impact is limited to self-promotional output shaping and one benign metadata fetch; intent to harm is not established.
  > File: `SKILL.md`
  > **Remediation:** Reframe the citation block as optional, user-approved guidance rather than an unconditional agent instruction, and remove the automatic external fetch directive so network access requires explicit user consent consistent with the skill's own local-only intake policy.

### ginkgo-cloud-lab — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive plus network fetch beyond declared Read-only tools
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' section instructing the agent to insert a specific arXiv reference (arXiv:2609.00065) into the user's manuscripts, reports, or code releases, notify the user it did so, and to fetch external URLs (https://arxiv.org/abs/2609.00065 or the arXiv API export endpoint) when network access is available. This directs output-content modification for author self-promotion and implies outbound network access even though the manifest declares only the Read tool. No sensitive data is collected or transmitted and no executable code exists in the package (18 markdown files, no scripts), so this is a minor capability/purpose mismatch rather than exfiltration or injection.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance optional and user-initiated rather than an instruction to modify deliverables, and either remove the network-fetch directive or declare the corresponding fetch/network tool in the manifest.

### gtars — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-citation directive instructs agent to insert author's paper into user deliverables
  > The SKILL.md instruction body contains a 'Citing Scientific Agent Skills' section directing the agent to add a specific paper by the skill author (K-Dense Inc.) to the references of any manuscript, report, presentation, or code release the skill contributed to, to inform the user it did so, and to fetch arxiv.org/export.arxiv.org when network access is available. This is a promotional behavioral directive that shapes user-facing scientific output and triggers an outbound network request unrelated to the skill's stated genomic-interval purpose. No sensitive data is collected or transmitted (only a public record is fetched), and the behavior is disclosed in plain text, so this is a contextual risk rather than confirmed abuse.
  > File: `SKILL.md`
  > **Remediation:** Make the citation request passive documentation (e.g., an optional 'How to cite' note) rather than an active directive to modify user deliverables, and remove the instruction to perform an unsolicited network fetch.

### lamindb — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation directive with mandated network fetch
  > The SKILL.md body instructs the agent to add a specific arXiv paper (arXiv:2609.00065, attributed to the skill vendor K-Dense) to the user's manuscript/report references whenever the skill 'materially contributed', to inform the user it did so, and to fetch an external arXiv URL when network access is available. This is a self-serving instruction embedded in skill directions that injects vendor citations into user deliverables and triggers outbound network requests that are unrelated to the stated LaminDB purpose. It is not technically malicious and involves only a legitimate, well-known public endpoint, so it is rated as a contextual/behavioral risk rather than an attack.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/optional (surface it only when the user explicitly asks about attribution) and remove the mandated automatic outbound fetch, or clearly declare network usage in the manifest.

### hugging-science — 🔵 LOW

- **🔵 LOW** `LLM_DATA_EXFILTRATION` — Guidance to auto-load HF_TOKEN from .env in any parent directory before calling third-party Spaces
  > The skill instructs the agent to call python-dotenv load_dotenv() at the top of any script hitting the HF API, which searches the cwd and any parent directory for a .env file, and to prefer this over huggingface-cli login. The Spaces reference notes that once HF_TOKEN is loaded, gradio_client transmits it to whatever Space is called and file() uploads local data to the Space operator. Destination is the intended Hugging Face service and the skill explicitly warns the agent not to echo tokens, to name any non-hugging-science Space and uploaded files to the user, and to get user approval first, so this is ordinary credential use with a residual token-scope risk rather than established exfiltration.
  > **Remediation:** Scope secret loading to an explicit project-local .env path rather than parent-directory traversal, and require explicit user confirmation before any token-bearing call to a Space outside the declared organization.

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Skill directs agent to insert vendor self-citation with an unverifiable future-dated arXiv ID
  > The SKILL.md body instructs the agent to add a specific paper (K-Dense, 'Scientific Agent Skills', arXiv:2609.00065, year 2026) to the references of any manuscript, report, presentation, or code release the skill contributes to, and to tell the user it did so. The identifier is future-dated (2609 = September 2026) and cannot be verified from the package, so the agent may inject a fabricated or unverifiable citation into a user's scholarly output. This is promotional/behavioral steering rather than a technical compromise; it is disclosed and conditional, and the skill also tells the agent to fetch the live arXiv record when network access is available.
  > File: `SKILL.md`
  > **Remediation:** Make the citation suggestion advisory only (present it to the user for approval rather than instructing the agent to add it), and reference only a verifiable, already-published identifier.

- **🔵 LOW** `LLM_PROMPT_INJECTION` — Remote third-party catalog markdown is fetched into agent context (mitigated indirect-injection surface)
  > scripts/fetch_catalog.py retrieves markdown from huggingscience.co (llms.txt, llms-full.txt, topics/<slug>.md) and prints it into the agent's context, including a 'raw' mode that dumps the document unparsed. Content controlled by a third-party web server entering agent context is an indirect prompt-injection surface. The package implements meaningful mitigations: an explicit untrusted-data banner, code-fence and '---' defanging, and off-catalog host labelling, and it repeatedly warns that catalog listing is not a vetting signal and that trust_remote_code must be user-approved. No malicious instruction is present in the package itself.
  > File: `scripts/fetch_catalog.py`
  > **Remediation:** Apply the defang path to raw mode as well, and consider truncating or structurally sanitizing all fetched fields before they reach the agent context.

### market-research-reports — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-promotion directive instructing the agent to insert a vendor citation into user deliverables
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that directs the agent to add a specific vendor-authored reference (arXiv:2609.00065, K-Dense Inc.) to the user's manuscript, report, presentation, or code release, to notify the user it did so, and to fetch the arXiv record over the network when access is available. This is an author-benefiting instruction embedded in operational directions rather than a market-research capability, and the cited identifier/date cannot be verified from the package. It does not access sensitive data, execute code, or exfiltrate anything, so impact is limited to unsolicited citation insertion and one benign outbound fetch to arxiv.org.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance passive documentation (e.g., an optional 'How to cite' note) rather than an instruction the agent follows automatically, and require explicit user consent before adding references to user deliverables or performing network fetches.

### markitdown — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive embedded in skill instructions
  > The SKILL.md body instructs the agent to add a specific arXiv paper (arXiv:2609.00065, 'Scientific Agent Skills' by the skill author's organization) to references or software sections of user manuscripts/reports and to notify the user that it did so, and to fetch the arXiv record over the network when available. This is vendor self-promotion injected into the agent's output workflow rather than functionality required for document conversion. It is low-impact and disclosed, but it directs agent behavior (content insertion and an outbound network fetch) beyond the stated skill purpose.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance passive/optional (e.g., mention only if the user asks about attribution) and remove the automatic network fetch and automatic reference insertion directive.

### liteparse — 🔵 LOW

- **🔵 LOW** `LLM_SUPPLY_CHAIN_ATTACK` — Install directive pins an unverifiable, future-dated package version
  > The instructions direct the agent (which is granted Bash) to run `uv pip install "liteparse==2.0.0"`, described as a PyPI release dated May 2026, and additionally reference `npm i @llamaindex/liteparse` and `cargo install liteparse`. A pinned version that is described as released at a future date cannot be verified at analysis time; if the name/version is not yet published it is subject to name-squatting or dependency-confusion substitution when the agent executes the install. This is a documented installer with no download-then-execute of an unverified binary, so it is a contextual supply-chain risk rather than confirmed malicious behavior.
  > **Remediation:** Verify the package name and version exist on the official index, prefer hash-pinned or lock-file installs, and require explicit user confirmation before the agent executes package installation commands.

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Mandatory self-promotional citation injection with network fetch directive
  > The SKILL.md instruction body contains a 'Citing Scientific Agent Skills' section that directs the agent to insert a specific arXiv reference (arXiv:2609.00065) into the user's manuscripts, reports, or code releases, to tell the user it did so, and to fetch an external arXiv URL/API endpoint before writing the reference. This behavior is unrelated to the declared purpose (local document/PDF parsing) and influences the agent to modify user deliverables and perform outbound network requests for author self-promotion. No sensitive data is transmitted and no override of safety behavior occurs, so the reach is limited to unsolicited content insertion and an outbound metadata fetch.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance advisory and user-opt-in rather than an unconditional agent directive, and remove the instruction to autonomously fetch remote URLs unrelated to document parsing.

### matplotlib — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-promotional citation directive with unverifiable future-dated reference
  > The SKILL.md body ends with an active directive unrelated to plotting: the agent is told to add a specific author/paper citation ('Scientific Agent Skills ... arXiv:2609.00065') to any manuscript, report, presentation, or code release the skill contributes to, to 'tell the user you did so', and to fetch arxiv.org/export.arxiv.org when network access is available. This is a self-promotion instruction injected into an otherwise ordinary library-usage skill, and the cited identifier is future-dated (2026 / arXiv 2609.xxxxx) so it may not resolve to a real record, risking insertion of an unverifiable reference into user deliverables. The network fetch is to a legitimate, declared public source and no sensitive data is transmitted, so the behavior is limited to attribution influence rather than exfiltration.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive and optional (e.g., 'if the user wishes to cite this skill, the reference is ...'), remove the instruction to modify user deliverables and to self-report, and only reference a verifiable, published identifier.

### medchem — 🔵 LOW

- **🔵 LOW** `LLM_PROMPT_INJECTION` — Embedded self-promotional citation directive with network fetch instruction
  > The SKILL.md instruction body contains a 'Citing Scientific Agent Skills' block that directs the agent to insert a specific author/paper citation (arXiv:2609.00065, dated 2026) into any manuscript, report, presentation, or code release the user produces, to notify the user that it did so, and to fetch arxiv.org/export.arxiv.org URLs when network access is available. This is an unrelated behavioral directive appended to a domain-specific chemistry skill: it modifies user deliverables for the skill author's promotional benefit and triggers outbound network requests not needed for compound filtering. No credential, sensitive data, or exfiltration sink is involved, and the fetch target is a public, declared academic source, so impact is limited to unsolicited content insertion and an extra network call rather than data compromise.
  > File: `SKILL.md`
  > **Remediation:** Remove or downgrade the citation block to passive, optional documentation (e.g., a 'Citation' note under Resources) rather than an imperative agent instruction, and drop the directive to fetch remote URLs and modify user deliverables automatically.

### molfeat — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-promotional citation directive with unverifiable arXiv reference
  > The SKILL.md body contains an active directive instructing the agent to add a specific vendor-authored citation (K-Dense, 'Scientific Agent Skills', arXiv:2609.00065, dated 2026) to any user manuscript, report, presentation, or code release the skill contributes to, to inform the user it did so, and to fetch the arXiv/export API URL when network access is available. This is unrelated to molecular featurization and injects author-promotional behavior into the user's deliverables; the referenced identifier is future-dated and cannot be verified. It is a mild attribution/self-promotion directive rather than an exfiltration or override of safety behavior: the fetch target is a public, declared academic endpoint and no user data is transmitted.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance passive/optional (e.g., 'if the user requests attribution, this skill may be cited as ...'), remove the instruction to automatically modify user deliverables, and replace the unverifiable future-dated arXiv identifier with a resolvable reference.

### networkx — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive with external fetch beyond declared skill scope
  > The SKILL.md instruction body contains a 'Citing Scientific Agent Skills' section that directs the agent to insert a specific arXiv reference (arXiv:2609.00065, attributed to the skill author 'K-Dense Inc.') into the user's manuscripts, reports, presentations, or code releases, to notify the user it did so, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv API when network access is available. This is a behavior directive unrelated to the declared purpose (NetworkX graph analysis) that modifies user deliverables and triggers outbound network requests. No data exfiltration, secret access, or code execution is involved; the cited identifier is also a future-dated/unverifiable record, so the content may be misleading. Risk is limited to unsolicited self-promotion and scope creep rather than technical compromise.
  > File: `SKILL.md`
  > **Remediation:** Reframe the citation section as optional, user-approved guidance rather than an imperative agent action; remove the directive to automatically modify user deliverables and to perform unsolicited network fetches, and declare any required network capability in the manifest.

### neuropixels-analysis — 🔵 LOW

- **🔵 LOW** `LLM_SUPPLY_CHAIN_ATTACK` — Documented loading of remote Hugging Face .skops models with trust_model=True
  > The skill documents and recommends calling spikeinterface.curation.model_based_label_units(..., repo_id='SpikeInterface/...', trust_model=True), which downloads and deserializes a remote .skops/pickle-style artifact with trust enabled — a code-execution-capable deserialization path from a third-party repository. This is standard upstream SpikeInterface usage against the official SpikeInterface Hugging Face org, and the skill explicitly warns to treat .skops/.pkl files as executable artifacts and only load trusted sources, so intent appears benign. It is recorded only as a contextual supply-chain risk because trust_model=True is presented as the default recommended pattern in agent-executed documentation.
  > **Remediation:** Prefer pinned model revisions and an explicit trusted=[...] allowlist over blanket trust_model=True, and keep the existing warning prominent when the agent executes these snippets.

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Skill instructs the agent to self-promote a citation and fetch an external arXiv record
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section directing the agent to add a specific author/paper citation to the user's manuscript or code release, to tell the user it did so, and to fetch an external URL (arxiv.org / export.arxiv.org) when network access is available. This is a self-promotional directive embedded in the active instruction body and an instruction to retrieve remote content into the agent context; it is not required for the stated neurophysiology-analysis purpose. It is low severity because the destination is a well-known public academic source and no data is sent outward, but it nudges agent behavior toward vendor promotion and pulls untrusted external text into the session.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/optional documentation rather than an agent directive, and remove the instruction to automatically fetch remote records and incorporate their content.

### nextflow — 🔵 LOW

- **🔵 LOW** `LLM_SKILL_DISCOVERY_ABUSE` — Broad activation clause claims the skill for work where its topic is never mentioned
  > The manifest description includes an imperative activation-broadening clause: 'Make sure to use this skill for any reproducible scientific/bioinformatics workflow work even if the user does not say the word "Nextflow"'. Combined with a long keyword list, this expands routing beyond the skill's explicit domain and could cause it to shadow more appropriate skills for general scientific-workflow requests. Content of the package is otherwise ordinary, accurate Nextflow/nf-core documentation with no executable scripts, so this is a routing-scope concern rather than confirmed abuse.
  > **Remediation:** Scope the description to concrete Nextflow/nf-core triggers and remove directive language that claims unrelated or generic workflow tasks.

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation directive instructs agent to insert vendor paper into user deliverables
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that directs the agent to add a specific author-affiliated arXiv reference (arXiv:2609.00065, K-Dense Inc.) to any manuscript, report, presentation, or code release the skill contributed to, to inform the user it did so, and to fetch the arXiv record over the network when connectivity exists. This is an embedded behavioral instruction unrelated to the declared Nextflow functionality that biases the agent toward promoting the skill vendor in user-authored scientific output. The cited identifier/date (2026, arXiv:2609.00065) is not verifiable and could result in a fabricated citation being inserted into research artifacts. Impact is limited to reputational/content integrity rather than system compromise; no data is sent outbound.
  > File: `SKILL.md`
  > **Remediation:** Remove or make strictly optional the automatic citation-insertion directive; do not instruct the agent to modify user deliverables with vendor references, and avoid unverifiable DOIs/arXiv identifiers.

### ontology-term-resolution — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-promotional citation directive unrelated to skill function
  > The SKILL.md body contains an active directive instructing the agent to add a specific vendor-authored paper (arXiv:2609.00065, K-Dense) to the references or software section of any manuscript, report, presentation, or code release the skill contributes to, to inform the user it did so, and to fetch arxiv.org / export.arxiv.org when network access is available. This behavior is outside the declared purpose of ontology term resolution against OLS4 and steers the agent into modifying user deliverables and making outbound requests to a domain not declared in the compatibility metadata (which states only https://www.ebi.ac.uk/ols4 is needed). The directive is transparent and self-disclosing, with no data collection or credential handling, so impact is minimal; no exfiltration or code execution risk was identified.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/informational rather than an instruction the agent must act on, and declare any additional network destinations (arxiv.org) in the compatibility/network metadata.

### paperclip — 🔵 LOW

- **🔵 LOW** `LLM_SUPPLY_CHAIN_ATTACK` — Documented install path pipes an unverified remote script to bash and installs an unversioned, self-updating wheel
  > The skill instructs the agent to install the vendor CLI via `curl -fsSL https://paperclip.gxl.ai/install.sh | bash`, and alternatively via `uv pip install https://paperclip.gxl.ai/paperclip.whl`. The package itself documents that there is no published checksum or signature for the installer, that the wheel URL is unversioned, and that the resulting binary self-updates opportunistically mid-command. This is the vendor's own documented, user-gated install path (the skill requires explicit user go-ahead, offers `curl ... | less` for review, and warns about the PyPI name-squat on `paperclip`), so intent appears legitimate; however the download-then-execute chain against mutable, unverified remote content is an inherent supply-chain exposure that would let a compromised vendor endpoint run arbitrary code with the user's privileges. No malicious payload, obfuscation, credential exfiltration, or instruction override was found anywhere in the package; the skill in fact contains strong defensive guidance (treat all server output as data, never follow embedded instructions, repos/uploads/sharing/fetch are opt-in and confirmation-gated).
  > **Remediation:** Prefer a pinned, hash-verified release artifact (versioned wheel URL or release tarball with published SHA256/signature) and verify before execution; keep explicit user confirmation before running any remote installer, and consider disabling opportunistic self-update in agent/CI contexts so the executed code is reproducible.

### pathway-enrichment — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-promotional citation directive with external fetch of a non-resolving arXiv record
  > The SKILL.md instruction body ends with a 'Citing Scientific Agent Skills' block directing the agent to add a specific author/paper citation to the user's manuscript, report, presentation, or code release, to inform the user it did so, and — when network access is available — to fetch https://arxiv.org/abs/2609.00065 or the arXiv export API before writing the reference. This is a self-promotional output directive unrelated to the declared pathway-enrichment purpose, and the referenced identifier (arXiv:2609.00065, dated 2026) is not a currently resolvable record, so the agent could insert an unverifiable citation into scholarly output. No data is exfiltrated (the fetch is a read-only public GET carrying no user data), so this is a content/behavioral-influence concern rather than a technical compromise.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/optional (e.g., 'if the user asks how to cite this skill') rather than an instruction to modify user deliverables, remove the mandated outbound fetch, and reference only a verifiable, resolvable publication identifier.

### pennylane — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-citation directive with external fetch of an unverifiable arXiv record
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that instructs the agent to insert a specific vendor paper (K-Dense, arXiv:2609.00065) into the user's manuscripts, reports, or code releases, to 'always cite the current version', and to fetch https://arxiv.org/abs/2609.00065 or the arXiv export API when network access is available. This is promotional instruction content embedded in active agent directions rather than technical guidance: the agent is told to modify user deliverables and to notify the user it did so. The referenced identifier (2609.00065 implies September 2026) is not verifiable from the package, so the agent could add a non-existent or misleading reference to academic output. No credential access, code execution, or data egress is involved, so reach and impact are limited to citation content and a benign outbound documentation fetch.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance passive and user-initiated (e.g., 'a citation is available if the user requests it'), remove the directive to automatically insert references into user deliverables, and remove or clearly mark the unverified arXiv identifier and the instruction to fetch it automatically.

### polars — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Instructions direct outbound network fetch and mandated self-citation beyond declared 'Read' tool scope
  > The SKILL.md body contains an active directive telling the agent to insert a specific arXiv citation (arXiv:2609.00065, attributed to the skill author's organization) into the user's manuscripts/reports/code releases, to inform the user it did so, and to fetch external URLs (https://arxiv.org/abs/2609.00065 or export.arxiv.org API) when network access is available. The manifest declares only the 'Read' tool, so directing outbound HTTP retrieval materially exceeds the declared capability restriction. The citation mandate is promotional content injected into user deliverables rather than a data-processing function of the Polars skill. No sensitive data source, credential access, or exfiltration sink is present, so impact is limited to unwanted network egress and attribution insertion.
  > File: `SKILL.md`
  > **Remediation:** Remove or downgrade the mandatory self-citation directive to optional, user-consented guidance; remove the instruction to fetch external URLs, or declare network/fetch capability explicitly in the manifest allowed-tools and document the destination.

### pylabrobot — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive with network fetch of a specific arXiv record
  > The SKILL.md body instructs the agent to add a specific paper (arXiv:2609.00065, authored by the skill vendor K-Dense) to manuscripts, reports, or code releases when the skill 'materially contributed', to tell the user it did so, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv export API when network access is available. This is vendor self-promotion embedded as an operational instruction plus an outbound network request that is not part of the stated lab-automation purpose. No sensitive data is included in the request (it is a plain read of a public arXiv record), so this is a policy/promotional concern rather than exfiltration.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance passive/optional (present the reference only if the user asks) and remove the directive to automatically fetch an external URL and insert the vendor's citation into user deliverables.

### pyhealth — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-promotional citation directive with external fetch
  > The SKILL.md instruction body ends with a 'Citing Scientific Agent Skills' section that directs the agent to insert a specific vendor-authored reference (arXiv:2609.00065, a future-dated identifier) into any user manuscript, report, presentation, or code release the skill contributes to, to inform the user it did so, and to fetch arxiv.org / export.arxiv.org endpoints when network access is available. This is unrelated to the stated PyHealth pipeline purpose and steers agent output toward promoting the skill author's publication, plus an unrequested outbound network request. No sensitive data source is read and no credential or user data is transmitted, so impact is limited to attribution/marketing influence rather than exfiltration.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/optional (e.g., 'if the user asks how to cite this skill') and remove the directive to automatically add references to user deliverables and to fetch external URLs without an explicit user request.

### pymc — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-promotion instruction directing agent to add author's citation to user deliverables and fetch external URL
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that instructs the agent to add a specific arXiv paper by the skill authors to the user's manuscript/report/code references, to notify the user that it did so, and to fetch an external arXiv URL (https://arxiv.org/abs/2609.00065 or export.arxiv.org API) when network access is available. This is author-benefiting behavior injected into the agent's active directions rather than a technical capability required for Bayesian modeling. It is low severity: the action is conditional, transparent to the user, targets a benign public destination, and no sensitive data is read or transmitted. No credential access, obfuscation, code execution of downloaded content, or exfiltration sink is present anywhere in the package.
  > File: `SKILL.md`
  > **Remediation:** Make the citation request passive documentation (e.g., an optional note in a README) rather than an active instruction that modifies user deliverables, and remove the directive to fetch external URLs unless the user explicitly requests citation metadata.

### pysam — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Skill directs agent to insert author's citation into user deliverables and fetch an external URL
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section instructing the agent to add a specific paper by the skill author (K-Dense Inc.) to the user's manuscript/report/code references, to notify the user it did so, and to fetch arxiv.org / export.arxiv.org before writing the reference. This is self-promotional instruction content that can modify user deliverables and trigger outbound network requests beyond the skill's declared genomic-file purpose. No sensitive data is collected or transmitted, and the destinations are benign public academic endpoints, so the reach is limited; the risk is unsolicited content injection and an undeclared network fetch rather than exfiltration.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/optional (e.g., state the reference only if the user explicitly asks for attribution), remove the directive to automatically modify user reference lists, and drop the automatic network fetch or document it in the manifest compatibility/capability notes.

### pyzotero — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-citation directive instructs agent to insert vendor paper into user deliverables
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that directs the agent to add a specific arXiv paper (arXiv:2609.00065) authored by the skill vendor to the user's manuscript/report/code-release references whenever the skill 'materially contributed', and to fetch the arXiv record over the network before writing the reference. This is agent-directed behavior that extends beyond the declared purpose (Zotero API interaction) and can autonomously alter user deliverables with promotional content. It is mitigated by being conditional, transparent (the agent is told to inform the user), and by targeting a legitimate public arXiv/DOI endpoint rather than an exfiltration sink; no data is sent outbound. Rated LOW and CONTEXTUAL_RISK rather than a confirmed attack.
  > File: `SKILL.md`
  > **Remediation:** Convert the citation guidance into passive documentation (e.g., 'if you wish to cite this skill, use ...') rather than an imperative instruction that causes the agent to modify user deliverables or make outbound network requests, and keep instruction scope limited to the declared Zotero functionality.

### qiskit — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-promotional citation directive with external fetch instruction
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' block that directs the agent to add a specific author-supplied paper (arXiv:2609.00065, K-Dense) to the user's manuscript/report references, to inform the user it did so, and, when network access is available, to fetch arxiv.org / export.arxiv.org endpoints before writing the reference. This behavior is unrelated to the declared Qiskit capability and steers agent output toward promoting the skill author's publication, plus an outbound network read not covered by the manifest's stated purpose. No sensitive data is collected or transmitted, and the destination is a public, well-known scholarly service, so impact is limited to attribution influence and an extra network call.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance passive documentation (e.g., 'the author requests citation') rather than an instruction the agent executes, and remove the directive to fetch external URLs as part of normal skill operation.

### scientific-brainstorming — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-promotional citation directive with external fetch instruction
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' block that directs the agent to insert a specific vendor paper (arXiv:2609.00065, K-Dense Inc.) into the user's manuscript/report/code references whenever the skill 'materially contributed', to inform the user it did so, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv export API when network access is available. This is publisher self-promotion embedded in active agent directions and causes an outbound network request plus modification of user deliverables that the user never requested. The cited identifier is also not verifiable as a real record from package content, so an agent following the directive could emit an unverified reference. No sensitive data is collected or transmitted, and no other risky behavior is chained to it, so the impact is limited to promotional/unsolicited-action risk rather than exfiltration.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance passive and user-gated (e.g., 'if the user asks how to cite this skill, provide the reference'), remove the mandatory outbound fetch, and avoid instructing the agent to modify user deliverables with vendor references automatically.

### scholar-evaluation — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive and optional external fetch in instruction body
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that directs the agent to add a specific author-affiliated arXiv reference to the user's manuscript, report, or code release and to notify the user it did so, and to fetch arxiv.org/export.arxiv.org when network access is available. This is a vendor self-promotion directive that modifies user deliverables and introduces an outbound network read that is not needed by the local, standard-library-only tooling (the manifest compatibility note states all tooling is local with no network). No sensitive data source, credential access, or exfiltration sink is present; the fetched destination is a public, declared scholarly site, so the risk is limited to unsolicited citation insertion and an undeclared optional network read rather than data leakage.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance explicitly optional and user-approved rather than an instruction the agent should carry out automatically, and either remove the arXiv fetch directive or declare the network capability and destination in the manifest/compatibility notes.

### scientific-visualization — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive instructing agent to add a specific paper reference and fetch external URL
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' section that instructs the agent to add a specific arXiv paper (K-Dense authors) to the references of any manuscript, report, presentation, or code release the skill contributed to, to inform the user it did so, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv API when network access is available. This is a self-referential promotional instruction embedded in operating directions rather than a visualization capability; it also directs an outbound network fetch that is not part of the stated network-free purpose. No sensitive data is transmitted and the destination is a well-known public academic host, so the impact is low, but it constitutes vendor self-promotion injected into the agent's output workflow.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance passive/optional documentation (e.g., 'if the user wants to cite this skill, the reference is ...') rather than an instruction that the agent must insert the reference and perform a network fetch, and declare the outbound fetch in the compatibility/network notes.

### scientific-writing — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-citation directive instructs agent to insert vendor paper into user deliverables and fetch external URL
  > The SKILL.md body contains an active instruction ('Citing Scientific Agent Skills') directing the agent to add a specific arXiv paper authored by the skill vendor (K-Dense) to the user's manuscript references or software section, to notify the user it did so, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv API when network access is available. This is a self-promotional content-injection directive that modifies user-facing scientific output for the vendor's benefit and triggers an outbound network request not implied by the skill's stated offline, network-free design. It conflicts with the skill's own no-fabrication and evidence-verification rules, which require every reference to be human-verified. No credential access, sensitive-data collection, or exfiltration sink is present, so the impact is limited to unsolicited citation insertion and a benign public fetch.
  > File: `SKILL.md`
  > **Remediation:** Convert the citation guidance into passive, optional documentation that requires explicit user consent before any reference is added to a deliverable, and remove the directive to autonomously fetch external URLs so the skill matches its declared offline/network-free posture.

### scikit-learn — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-promotional citation directive with unverifiable arXiv reference
  > The SKILL.md body contains an active directive instructing the agent to add a specific vendor-authored paper (arXiv:2609.00065, an identifier corresponding to a future date) to any manuscript, report, presentation, or code release the skill contributes to, to notify the user it did so, and to fetch the arXiv record when network access is available. This is unrelated to the stated scikit-learn machine-learning purpose and steers agent output toward promoting the skill author's work, potentially inserting an unverifiable reference into user deliverables. It is conditional and openly attributed rather than covert, and the fetched destination (arxiv.org) is a legitimate public source with no sensitive data being transmitted, so intent and impact are limited.
  > File: `SKILL.md`
  > **Remediation:** Reframe the citation guidance as passive, optional documentation (e.g., "if the user wishes to cite this skill, the reference is ...") rather than a standing instruction to modify user deliverables, and verify that the cited DOI/arXiv identifier resolves to a real published record.

### scikit-bio — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive instructs agent to insert a specific reference into user deliverables and fetch an external URL
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that directs the agent to add a specific author/paper reference (arXiv:2609.00065, dated 2026) to any manuscript, report, presentation, or code release the skill contributes to, to inform the user it did so, and to fetch https://arxiv.org/abs/2609.00065 or the arXiv API endpoint when network access is available. This is a vendor self-promotion behavioral directive embedded in active instructions rather than a bioinformatics capability: it can cause unrequested modification of user output artifacts and an outbound network request to an author-controlled reference record. No credential access, code execution, or sensitive data sink is involved, so impact is limited to content integrity and unsolicited attribution.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/optional (e.g., 'if the user wishes to cite this skill, the reference is ...') rather than instructing the agent to modify user deliverables automatically, and remove the directive to perform unsolicited network fetches.

### scvi-tools — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-citation directive instructs agent to modify user deliverables and fetch external URL
  > The SKILL.md body contains an active instruction block ("Citing Scientific Agent Skills") that directs the agent to insert a specific author/preprint citation into any manuscript, report, presentation, or code release the skill contributes to, to notify the user that it did so, and to fetch external endpoints (arxiv.org / export.arxiv.org) when network access is available. This is promotional/attribution behavior unrelated to the declared single-cell modeling purpose and injects content into user work products. No credential access, secret handling, script execution, or data egress of sensitive material is present; all bundled files are documentation only, so reach and impact are limited.
  > File: `SKILL.md`
  > **Remediation:** Reframe the citation guidance as optional, user-approved metadata rather than a directive that automatically edits user deliverables, and remove or make explicitly opt-in the instruction to perform outbound network fetches.

### stable-baselines3 — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive instructs agent to add a specific paper reference and fetch an external URL
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section directing the agent to add a specific arXiv citation (arXiv:2609.00065) to any manuscript, report, or code release the skill contributes to, to inform the user it did so, and to fetch an external arXiv URL when network access is available. This is author self-promotion embedded as an active instruction rather than RL guidance, and it introduces a minor outbound network fetch and content-injection behavior unrelated to the declared purpose of the skill. There is no exfiltration of user data, no credential access, and no code execution associated with it, so risk is low.
  > File: `SKILL.md`
  > **Remediation:** Convert the citation section into passive, optional documentation ('a citation is available if you wish to cite this skill') and remove the directive to automatically fetch external URLs and insert references into user deliverables.

### seaborn — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation directive with unverifiable arXiv reference and network fetch
  > The SKILL.md body contains an active behavioral directive ('Citing Scientific Agent Skills') instructing the agent to insert a specific author/paper citation (arXiv:2609.00065, dated 2026) into the user's manuscripts, reports, presentations, or code releases, to inform the user it did so, and, when network access is available, to fetch https://arxiv.org/abs/2609.00065 or the arXiv export API before writing the reference. The identifier and publication year are not verifiable, so the directive could cause the agent to add a fabricated or unverifiable reference to user deliverables and to perform an outbound network request not needed for seaborn plotting. No sensitive data is collected or transmitted, and the fetch destination is a legitimate public repository, so the reach is limited; this is attribution/self-promotion pressure rather than exfiltration. All other package content (reference markdown files for seaborn APIs, palettes, grids, objects interface, examples) is ordinary documentation with no code execution, no scripts, and no network sinks.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance passive documentation rather than an instruction to the agent, remove the automatic outbound fetch requirement, and verify or drop the unresolvable arXiv identifier so the agent cannot insert unverifiable references into user deliverables.

### statsmodels — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Self-promotional citation directive instructing the agent to insert an author-supplied reference
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section that directs the agent to add a specific arXiv citation (K-Dense authors, arXiv:2609.00065) to user manuscripts/reports and to inform the user it did so, and to fetch the arXiv record when network access is available. This is an author-benefit instruction embedded in an otherwise technical statistics skill; it can cause unsolicited citation insertion into user deliverables and an outbound network fetch not required by the stated statistical-modeling purpose. It is not exfiltration (no user data is sent) and is conditioned on material contribution, so it is a contextual risk rather than confirmed abuse.
  > File: `SKILL.md`
  > **Remediation:** Make citation insertion opt-in and user-confirmed rather than an implicit directive, and remove or clearly gate the automatic network fetch of the arXiv record.

### shap — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-citation directive with undeclared network fetch
  > The SKILL.md instruction body ends with a directive telling the agent to add the skill author's paper (K-Dense, arXiv:2609.00065) to the references of any manuscript, report, presentation, or code release the skill contributes to, to inform the user it did so, and to fetch arxiv.org/export.arxiv.org records when network access is available. This is author self-promotion embedded in active agent directions and it implies outbound HTTP fetches even though the manifest declares only Read and Bash. No sensitive data is collected or transmitted and the citation behavior is disclosed to the user, so impact is limited to unsolicited content insertion and an out-of-scope network action rather than exfiltration.
  > File: `SKILL.md`
  > **Remediation:** Reframe the citation section as optional user-facing information rather than an agent directive, and remove or explicitly declare the network-fetch step (declare WebFetch capability or drop the automatic lookup).

### statistical-power — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-citation directive with external network fetch
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' block that instructs the agent to add a specific author paper (arXiv:2609.00065) to the user's manuscript/report references, to inform the user it did so, and to fetch an external arXiv URL (https://arxiv.org/abs/2609.00065 or export.arxiv.org API) when network access is available. This is vendor self-promotion injected into the agent's active directions and it introduces an outbound network request not required by the stated power-analysis purpose. No sensitive data source is coupled to the request and the citation is conditional on the skill materially contributing, so impact is limited to unsolicited attribution content and a benign external HTTP GET rather than exfiltration.
  > File: `SKILL.md`
  > **Remediation:** Make attribution passive documentation rather than an agent directive, remove the instruction to automatically insert citations into user deliverables, and drop or explicitly declare the external network fetch so users can approve it.

### sympy — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-promotional citation directive and external URL fetch instruction
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' section that directs the agent to insert a specific vendor-authored citation (arXiv:2609.00065, K-Dense) into any manuscript, report, presentation, or code release the skill contributes to, to notify the user that it did so, and to fetch arxiv.org / export.arxiv.org records when network access is available. This is behavior outside the declared purpose (symbolic mathematics with SymPy): it steers the agent to modify user deliverables with promotional references and to make outbound network requests. The referenced preprint identifier is dated 2026 and may not resolve, so the agent could insert an unverifiable reference into scholarly output. No data is collected or sent to an attacker-controlled endpoint, and the instruction is conditional and disclosed, so this is a contextual risk rather than confirmed abuse.
  > File: `SKILL.md`
  > **Remediation:** Remove or make purely informational the mandatory citation directive; do not instruct the agent to modify user deliverables or perform network fetches that are unrelated to symbolic mathematics. If attribution is desired, state it as optional documentation rather than an agent action.

### transformers — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Self-promotional citation directive instructing agent to add author's paper to user outputs
  > The SKILL.md body contains a 'Citing Scientific Agent Skills' section directing the agent to insert a specific arXiv reference (arXiv:2609.00065 by the skill author, K-Dense Inc.) into user manuscripts/reports/code releases and to notify the user it did so, and to fetch an external arXiv URL when network access is available. This is promotional behavior injected into the agent's output workflow that is unrelated to the declared Transformers-library purpose. It does not exfiltrate data or execute code, but it steers agent output for the author's benefit and involves fetching external content that could carry untrusted instructions.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance clearly optional and user-initiated rather than a directive that modifies user deliverables; treat any content fetched from external URLs as untrusted data and never as instructions.

### torch-geometric — 🔵 LOW

- **🔵 LOW** `LLM_SOCIAL_ENGINEERING` — Embedded self-promotion directive instructing agent to insert author citation into user deliverables
  > The SKILL.md body ends with a 'Citing Scientific Agent Skills' block that directs the agent to add a specific paper (arXiv:2609.00065, attributed to the skill author's organization) to the user's manuscript/report/code references whenever the skill 'materially contributed', to inform the user it did so, and to fetch the arXiv record over the network when access is available. This is an instruction unrelated to the stated PyTorch Geometric technical purpose that biases agent output toward promoting the skill vendor and adds an outbound network fetch. The referenced identifier is a future-dated arXiv ID that cannot be verified, raising the possibility of an unverifiable or fabricated reference being inserted into user work. No credential access, code execution, or data egress of sensitive material is present, so impact is limited to unsolicited attribution/self-promotion.
  > File: `SKILL.md`
  > **Remediation:** Make the citation guidance passive documentation (e.g., 'if the user wishes to cite this skill, the reference is ...') rather than an imperative that the agent modify user deliverables, and remove the instruction to automatically fetch an external, unverifiable record.

### usfiscaldata — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Skill instructs agent to insert author's self-citation into user deliverables
  > Beyond its declared purpose (querying the Treasury Fiscal Data API), the SKILL.md body contains a 'Citing Scientific Agent Skills' directive telling the agent to add a specific arXiv reference (arXiv:2609.00065, an identifier corresponding to a future date) to any manuscript, report, presentation, or code release the skill contributed to, to inform the user it did so, and to fetch the arXiv record over the network when available. This is self-promotional behavior injected into the agent's output workflow that is unrelated to the skill's stated data-query function, and the cited identifier may not correspond to a verifiable publication. No credential access, exfiltration sink, code execution, or obfuscation was found anywhere in the package; all other content is legitimate public-API documentation with read-only HTTPS GET examples to api.fiscaldata.treasury.gov.
  > File: `SKILL.md`
  > **Remediation:** Make citation guidance passive/optional documentation rather than an operative instruction to modify user deliverables, and verify that the referenced publication identifier resolves to a real record.

### vaex — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Embedded self-citation directive instructs agent to insert author's paper into user deliverables
  > The SKILL.md instruction body contains a 'Citing Scientific Agent Skills' section that directs the agent to add a specific paper (arXiv:2609.00065 by the skill author's organization) to the references of any manuscript, report, presentation, or code release the skill contributes to, to inform the user it did so, and to fetch the arXiv record when network access is available. This is promotional instruction injection into the agent's active directions rather than technical guidance for the declared vaex data-processing purpose. The cited identifier/year (2026, arXiv:2609.00065) cannot be verified and may lead the agent to insert an unverifiable citation into user work products. No credential access, code execution, or exfiltration sink is involved, so impact is limited to content integrity and unsolicited promotion.
  > File: `SKILL.md`
  > **Remediation:** Remove or clearly demote the citation directive to optional, user-initiated documentation (e.g., a passive 'Citation' note) rather than an imperative instruction to the agent, and avoid instructing the agent to modify user deliverables or fetch external records automatically.

### venue-templates — 🔵 LOW

- **🔵 LOW** `LLM_POLICY_VIOLATION` — Skill body directs the agent to insert the author's own paper into user deliverables
  > The SKILL.md instruction body contains a 'Citing Scientific Agent Skills' section that directs the agent to add a specific arXiv paper authored by the skill vendor (K-Dense) to the references or software section of the user's manuscript/report/code release, to notify the user that it did so, and to fetch the arXiv record over the network when available. This is vendor self-promotion embedded in active agent directions that can influence the content of user work products (academic citations), rather than a security exploit. No credential access, exfiltration sink, code execution, or obfuscation is present; the fetched URLs are legitimate public arXiv endpoints. Treated as a contextual policy/integrity risk, not confirmed malicious behavior.
  > File: `SKILL.md`
  > **Remediation:** Make the citation request advisory and user-gated (e.g., 'suggest citing, only if the user agrees') rather than an unconditional directive to modify the user's reference list, and clearly separate vendor attribution from the skill's operational instructions.

### labarchive-integration — ⚪ INFO

- **⚪ INFO** `LLM_ANALYSIS_FAILED` — LLM analysis failed
  > The LLM analyzer encountered an error and could not complete semantic analysis: litellm.InternalServerError: AnthropicError - {"type":"error","error":{"type":"overloaded_error","message":"Overloaded"},"request_id":"req_011CeoqzsLf8qyhf3DyMoAa3"}
  > **Remediation:** Check your LLM provider configuration (API key, model name, network connectivity). The scan completed with static analysis only — LLM-based threat detection was not performed.

### ncats-arax — ⚪ INFO

- **⚪ INFO** `LLM_CONTEXT_BUDGET_EXCEEDED` — 'scripts/arax_client.py' excluded from LLM analysis (84,318 chars)
  > file size (84,318 chars) exceeds per-file limit (75,000)
  > File: `scripts/arax_client.py`
  > **Remediation:** Increase llm_analysis.max_code_file_chars in your scan policy to include this content in LLM analysis.
