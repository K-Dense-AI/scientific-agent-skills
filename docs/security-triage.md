# Security Scan Triage

Review notes for the [security report](security-report.md) and its
[machine-readable companion](security-report.json). Automated findings require code review;
neither a finding nor the scanner's `is_safe` field is a security certification.

## Current report: 2026-09-13

**Report generated:** 2026-09-13 14:32 UTC, scanner 2.1.0, model `claude-opus-5`.
The report covers all **165 skills**: **661 findings** (28 CRITICAL, 4 HIGH,
188 MEDIUM, 440 LOW, 1 INFO). Of these, **155 are per-skill findings** and
**506 are cross-skill findings**. Cross-skill details are in the JSON; the generated
Markdown summary does not show them individually. The reported 154/165 safe skills
is the scanner's per-skill severity classification, not a count of fully verified skills.

The refresh scanned 18 new or changed skills and reused 147 unchanged results from
September 7. A second pass retried incomplete LLM analyses for `geomaster` and
`labarchive-integration`; both completed. The report's final-run metadata therefore
says **2 rescanned / 163 reused**. Per-skill `last_scanned` dates and `content_hash`
values identify the underlying evidence; the last full scan remains September 7.

### Current high-severity review

| Findings | Evidence checked | Assessment |
|---|---|---|
| 28 CRITICAL `BEHAVIOR_*EXFILTRATION*` findings across eight skills | Named credential reads and API destinations in `autoskill`, `citation-management`, `infographics`, `latex-posters`, `literature-review`, `research-lookup`, `scientific-schematics`, and `scientific-slides` | These repeat the service-authentication pattern documented below. The cited reads use service-specific credentials. Configurable destinations, especially Autoskill's foundry endpoint, still require trust and authorization; HTTPS validation alone does not establish either. |
| 3 HIGH `MDBLOCK_PYTHON_EVAL_EXEC` findings | `histolab/references/filters_preprocessing.md`, `modal/references/functions.md`, `waypoint-bio/references/python-api.md` | False positives for the stated `eval`/`exec` claim: the first uses the OpenCV constant `cv2.CV_64F`; the other two call a model's `.eval()` method. This verdict does not audit model loading or remote tokenizer code. |
| 1 HIGH `CROSS_SKILL_DATA_RELAY` finding | Cross-skill JSON entry, which groups possible collectors and network-capable skills | An overlap heuristic, without an executed relay or demonstrated transfer between those skills. Keep it visible for composition review; it is not evidence of a confirmed attack and is not cleared by the per-skill safe count. |

### Remaining scanner limitations

Eight skills still record behavioral `FindingContract` errors for
`BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` and
`BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` (`UNKNOWN_BUNDLED_PYTHON_RULE`). They are
the same eight skills in the first row above. These errors remain in
`analyzers_failed`; no incomplete analyzer is silently treated as a successful pass.
There are no remaining recorded LLM analyzer failures after the retry.

The checks above cover the named high-severity patterns. They do not reclassify every
MEDIUM/LOW finding or establish that every possible workflow is safe. Inspect the
upstream [scanner documentation](https://github.com/cisco-ai-defense/skill-scanner)
when interpreting an unfamiliar rule.

### Reproduce the report

Run from the repository root with `SKILL_SCANNER_LLM_API_KEY` available. The wrapper
loads `.env` and writes the Markdown and JSON together:

```bash
# Match the scanner version used for this report without changing uv.lock.
uv run --frozen --with cisco-ai-skill-scanner==2.1.0 python scan_skills.py

# Force every skill through the analyzers, including unchanged skills.
uv run --frozen --with cisco-ai-skill-scanner==2.1.0 python scan_skills.py --full
```

The [weekly workflow](../.github/workflows/security-scan.yml) runs Mondays at
09:00 UTC and supports manual dispatch. The wrapper invalidates its cache on a
scanner/model change or after 30 days without a full scan. Review `skills_skipped`
and `analyzers_failed` as well as severity totals after every run.

## Historical review: 2026-07-27

The notes below preserve the earlier review against the July 27 10:38 UTC scan
(scanner 2.0.12, model `claude-opus-5`, 154 skills). Counts, line numbers, file
inventories, and package-release observations in this section describe that snapshot;
they are not current scan totals or blanket verdicts on later findings.

---

### Historical fixes

These were real. Each fix keeps the skill's documented behavior intact.

| Skill | Finding | What was actually wrong | Fix |
|-------|---------|------------------------|-----|
| `xlsx`, `docx`, `pptx` | `LLM_COMMAND_INJECTION` — runtime C compilation and LD_PRELOAD injection | `scripts/office/soffice.py` built its AF_UNIX shim at a fixed `/tmp/lo_socket_shim.so` and reused whatever was already there if the path merely existed. On a shared host, any local user could pre-plant a shared object there and have it `LD_PRELOAD`ed into every subsequent `soffice` run. The `.c` source was written to an equally predictable path before compilation. | Shim is built in a `tempfile.mkdtemp()` directory — unpredictable name, created `0700`, owned by the caller — memoized per process and removed at exit. No on-disk reuse across runs. |
| `imaging-data-commons` | `LLM_SUPPLY_CHAIN_ATTACK` — autonomous install with `--break-system-packages` | `SKILL.md` told the agent to run a version check **first** that shelled out to `pip3 install --break-system-packages` with no user confirmation, overriding a distribution safeguard unattended. Six other places recommended unpinned `pip install --upgrade idc-index`. | The startup block now only reports the version mismatch and prints a suggested command for the user to approve. All install guidance pinned to `idc-index==0.11.14` in a virtual environment. |
| `pacsomatic` | `LLM_COMMAND_INJECTION` — `--module-load` written unquoted into a generated launch script | Every other value in `write_launch_script()` passes through `shlex.quote()`; `args.module_load` alone was appended raw, so caller-supplied text became arbitrary shell in a script later executed by `bash`/`bsub`/`sbatch`/`qsub`. | `normalize_module_load()` validates the argument at input time: segments split on `&&`/`;`, each must start with `module` and contain no shell metacharacters, then re-emitted quoted. Every documented form (`module load nextflow/23.10.0`, `module purge && module load …`) still works. |
| `autoskill` | `LLM_DATA_EXFILTRATION` — arbitrary config-controlled endpoint for screen-derived data | `foundry.endpoint` from `config.yaml` was passed straight to `httpx.Client` with no scheme or host check, so summaries derived from screen-capture OCR plus an API key header could go to any URL, including plaintext `http://`. | `check_remote_endpoint()` rejects non-HTTP(S) schemes and plaintext HTTP to non-loopback hosts, and prints the destination host to stderr before any off-machine call. The default local LM Studio backend on `localhost:1234` is unaffected. |
| `hugging-science` | `LLM_PROMPT_INJECTION` — remote catalog rendered verbatim into agent context | `fetch_catalog.py` printed titles, descriptions, tags and URLs fetched from `huggingscience.co` with no framing or sanitization, so whoever controls or spoofs that host could place imperative prose or a runnable code block in a description field. | Output carries an explicit untrusted-data banner naming the source URL; entry text is defanged (code fences neutralized, bare `---` separators dropped); URLs outside `huggingface.co`/`hf.co`/`huggingscience.co` are labelled `[off-catalog host]`, with exact-or-subdomain matching so `evil-huggingface.co` does not pass. |
| `dhdna-profiler` | `LLM_DATA_EXFILTRATION` — profiling third parties and conversation history without consent | Independent of the phantom-script claims in the same finding (see below), this was real in the skill text: Self-Profile Mode mined conversation history silently, and nothing bounded profiling of people who are not in the conversation. | Added a Consent and Scope section: ask before reading back through conversation history, label third-party profiles as speculative inference, decline profiling that feeds hiring/clinical/disciplinary/credit decisions, keep profiles in-session. |
| `liteparse` | `LLM_SKILL_DISCOVERY_ABUSE` — activation-priority manipulation | The `description` instructed activation "even when the user does not name liteparse" and to "Prefer over MarkItDown" and "prefer over the pdf skill" — preemption directives that shadow sibling document skills. | Description rewritten to state capabilities factually. Parser-selection guidance already lived in `references/choosing_a_parser.md` and the in-body routing table, so nothing was lost. |

---

### Historical false-positive patterns

#### Previously reviewed CRITICAL and HIGH finding classes

The July review documented the following classes. Use their evidence to guide a new
review, not to dismiss all later CRITICAL or HIGH findings automatically.

**`BEHAVIOR_EVAL_SUBPROCESS` (CRITICAL ×4)** — claims `eval`/`exec` combined with `subprocess` in
`pacsomatic`, `research-lookup`, `scientific-slides`, `xlsx`. The July AST check found no built-in `eval`/`exec`/
`compile` call sites in the scanned skill scripts. The rule matches the *substring* `eval`/`exec` inside
ordinary identifiers that co-occur with `import subprocess` — `retrieval`, `evaluate`, `executor`,
`executable`. `scientific-slides/scripts/validate_presentation.py` and `xlsx/scripts/recalc.py`
contain neither substring at all.

```bash
# AST walk over every skill script: no eval/exec/compile, no os.system/os.popen,
# no shell=True, no env=os.environ.copy(), no iteration over os.environ.
python3 - <<'PY'
import ast, pathlib
def full(n):
    if isinstance(n, ast.Name): return n.id
    if isinstance(n, ast.Attribute): return f"{full(n.value)}.{n.attr}".lstrip(".")
    return ""
risky = {"os.system","os.popen","eval","exec","compile","subprocess.getoutput","os.execv"}
hits = []
for p in sorted(pathlib.Path("skills").rglob("*.py")):
    try: t = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError: continue
    for n in ast.walk(t):
        if isinstance(n, ast.Call):
            if full(n.func) in risky: hits.append((p, n.lineno, full(n.func)))
            for kw in n.keywords or []:
                if kw.arg == "shell" and getattr(kw.value, "value", None) is True:
                    hits.append((p, n.lineno, "shell=True"))
                if kw.arg == "env" and "os.environ" in ast.unparse(kw.value) and ".copy()" in ast.unparse(kw.value):
                    hits.append((p, n.lineno, "env=os.environ.copy()"))
        if isinstance(n, ast.For) and "os.environ" in ast.unparse(n.iter):
            hits.append((p, n.lineno, "iterates os.environ"))
print(hits or "clean")
PY
```

**`BEHAVIOR_ENV_VAR_EXFILTRATION` / `BEHAVIOR_CROSSFILE_ENV_VAR_EXFILTRATION` /
`BEHAVIOR_CROSSFILE_EXFILTRATION_CHAIN` (CRITICAL ×29)** — fire on "reads an env var + makes a
network call" anywhere in one package. In every flagged skill the variable read is the API key for
the service the skill exists to call:

| Skill | Env var read | Destination |
|-------|--------------|-------------|
| `autoskill` | `ANTHROPIC_API_KEY`, `FOUNDRY_API_KEY`, `SCREENPIPE_TOKEN` | `api.anthropic.com`, configured foundry endpoint, `localhost` |
| `citation-management` | `NCBI_API_KEY`, `NCBI_EMAIL`, `OPENROUTER_API_KEY` | `eutils.ncbi.nlm.nih.gov`, `openrouter.ai` |
| `research-lookup` | `OPENROUTER_API_KEY`, `PARALLEL_API_KEY` | `openrouter.ai`, `api.parallel.ai` |
| `infographics`, `latex-posters`, `literature-review`, `scientific-schematics`, `scientific-slides` | `OPENROUTER_API_KEY` | `openrouter.ai` |

That is service authentication, which [`SECURITY.md`](../SECURITY.md) places out of scope as "the
inherent capability of skills." The scanner's own LLM pass agreed in writing on an earlier run:
"standard API-key-based service authentication, not exfiltration."

**`MDBLOCK_PYTHON_EVAL_EXEC` (HIGH ×4)** — `geomaster/references/machine-learning.md:207,435` and
`modal/references/functions.md:82` are PyTorch `model.eval()`; `histolab/references/
filters_preprocessing.md:487` is the OpenCV constant `cv2.CV_64F`. The `modal` and `histolab` lines
already carry inline comments saying exactly this, from an earlier triage; the rule ignores them.

**`LLM_DATA_EXFILTRATION` / `LLM_UNAUTHORIZED_TOOL_USE` (HIGH ×3, all `dhdna-profiler`)** — rest
entirely on a claimed inventory of "8 Python scripts" performing "env var reads and network calls."
`dhdna-profiler` contains two files, both Markdown. The findings also cite `BEHAVIOR_*` static
results that appear nowhere in that skill's own findings list, i.e. the LLM analyzer was fed another
skill's static output. (The separate consent concern in the same finding was real and is fixed
above.)

#### Confabulated file inventories

The scanner reported Python and shell files in skills that ship only Markdown. Any finding whose
premise is "undisclosed bundled code" in these skills is void:

| Skill | Scanner claimed | Actual |
|-------|-----------------|--------|
| `dhdna-profiler` | 8 Python + 12 Markdown (21 files) | 2 files, both `.md` |
| `seaborn` | 7 Python files | 8 files, all `.md` |
| `scikit-bio` | 2 Python + 1 bash | 2 files, both `.md` |
| `umap-learn` | 2 Python files | 2 files, both `.md` |
| `what-if-oracle` | 2 Python + 1 bash (8 files) | 2 files, both `.md` |

```bash
for s in dhdna-profiler scikit-bio seaborn umap-learn what-if-oracle; do
  printf "%-18s py=%s sh=%s md=%s\n" "$s" \
    "$(find skills/$s -name '*.py' | wc -l | tr -d ' ')" \
    "$(find skills/$s -name '*.sh' | wc -l | tr -d ' ')" \
    "$(find skills/$s -name '*.md' | wc -l | tr -d ' ')"
done
```

Note the arithmetic: `seaborn`'s "7 Python files" and `dhdna-profiler`'s "8 Python + 12 Markdown"
track those skills' Markdown counts, so the analyzer appears to be mis-typing files rather than
inventing them wholesale.

#### Other

**`liteparse` — `LLM_SUPPLY_CHAIN_ATTACK`**, "possibly non-existent version `liteparse==2.0.0`,
cites a future PyPI release dated May 2026." The package is real, published by Logan Markewich
(run-llama, `github.com/run-llama/liteparse`), and `2.0.0` was uploaded 2026-05-25 — matching the
skill's claim. The scanner could not verify a date past its knowledge cutoff.

```bash
curl -s https://pypi.org/pypi/liteparse/json | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(d['info']['author'], '2.0.0' in d['releases'], d['releases']['2.0.0'][0]['upload_time'])"
```

**`BEHAVIOR_ENV_VAR_HARVESTING` (MEDIUM ×24)** — "script iterates through environment variables."
What it matches is the hardened form introduced by an earlier triage: `{name: os.environ[name] for
name in FORWARDED_ENV_VARS if name in os.environ}`, an explicit allowlist that exists specifically
so a subprocess does *not* inherit the caller's secrets. The rule fires on the fix.

**`MDBLOCK_PYTHON_HTTP_POST` (×27), `MDBLOCK_PYTHON_SUBPROCESS` (×18)** — fire on any HTTP POST or
`subprocess` call shown in a `SKILL.md` code block, including the safe argument-list form the
scanner recommends elsewhere. A skill that documents calling an API necessarily documents an HTTP
call.

**`hugging-science` — `LLM_COMMAND_INJECTION`** on `trust_remote_code=True` guidance. Not fixed
because it is already handled as the finding itself acknowledges: `SKILL.md:117` requires the agent
to ask the user before setting the flag, naming the repo, and states that catalog presence "is not a
vetting signal." The underlying capability belongs to `transformers`, not to this skill.

---

## Reporting

If you think a verdict here is wrong, open an issue with the skill name, the rule ID, and the check
that contradicts it. See [`SECURITY.md`](../SECURITY.md) for the private channel for genuine
vulnerabilities.
