# nf-core Tools CLI Reference

`nf-core` is a Python CLI for creating, linting, testing, and running nf-core-style pipelines, modules, and subworkflows. Source: https://nf-co.re/docs/nf-core-tools

## Install

```bash
pip install nf-core            # PyPI
conda install -c bioconda nf-core
nf-core --version
```

In tools **v3+** the commands are grouped under `pipelines`, `modules`, `subworkflows`, and `test-datasets`. (Older flat commands like `nf-core create`/`nf-core lint` still work but emit deprecation warnings — use the grouped form.) Run `nf-core --help` or `nf-core <group> --help` to see current options, or `nf-core interface` for a graphical TUI command explorer.

For `modules`/`subworkflows`, group-level options go **before** the subcommand, e.g. to target a non-default component repo: `nf-core modules -g <git-url> -b <branch> install fastqc`.

## Pipelines

| Command | Purpose |
|---------|---------|
| `nf-core pipelines list [keywords]` | List/search nf-core pipelines (`--json`, `--sort`) |
| `nf-core pipelines create` | Scaffold a new pipeline from the template (interactive TUI; `--name --description --author` for non-interactive) |
| `nf-core pipelines launch <name>` | Interactive, schema-validated run command + params file |
| `nf-core pipelines download <name>` | Download pipeline + containers for offline use (`--revision`, `--container-system singularity`, `--outdir`) |
| `nf-core pipelines lint` | Lint the pipeline in the current dir against nf-core standards (`--release`, `--fix`, `--dir`) |
| `nf-core pipelines schema build` | Create/update `nextflow_schema.json` (opens a web editor) |
| `nf-core pipelines schema validate <pipeline> <params.json>` | Validate params against the schema |
| `nf-core pipelines schema lint` | Lint the schema file |
| `nf-core pipelines schema docs` | Generate parameter docs from the schema |
| `nf-core pipelines create-params-file <name>` | Generate a documented YAML params file |
| `nf-core pipelines bump-version <ver>` | Bump the pipeline version across files |
| `nf-core pipelines sync` | Merge template updates into a pipeline (TEMPLATE branch) |
| `nf-core pipelines rocrate` | Generate an RO-Crate metadata record |
| `nf-core pipelines create-logo <text>` | Render an nf-core-style logo |

### Create a pipeline

```bash
nf-core pipelines create                # interactive: name, description, author
# non-interactive:
nf-core pipelines create --name mypipe --description "My pipeline" --author me
```

This generates the full nf-core template (see `references/developing.md` for the layout) with CI, linting, schema, and a `test` profile wired up. Develop on a feature branch; keep the `TEMPLATE` branch for `sync`.

### Lint before pushing

```bash
cd my-pipeline
nf-core pipelines lint                   # run in the repo root
nf-core pipelines lint --release         # stricter checks for a release
```

Linting enforces nf-core structure, required files, schema/params consistency, module versions, and formatting. CI runs this on every PR.

## Modules

Manage reusable process modules from the central [nf-core/modules](https://github.com/nf-core/modules) repo, or author your own.

| Command | Purpose |
|---------|---------|
| `nf-core modules list remote [keyword]` | List modules available in nf-core/modules |
| `nf-core modules list local` | List modules installed in the current pipeline |
| `nf-core modules info <tool>` | Show a module's inputs/outputs/description |
| `nf-core modules install <tool>` | Install a module into `modules/nf-core/` |
| `nf-core modules update <tool>` | Update an installed module (`--all`, `--diff`) |
| `nf-core modules remove <tool>` | Remove an installed module |
| `nf-core modules patch <tool>` | Record local changes to an installed module as a patch |
| `nf-core modules create [tool]` | Scaffold a new module (`main.nf`, `meta.yml`, `tests/`) |
| `nf-core modules lint <tool>` | Lint a module against module specs |
| `nf-core modules test <tool>` | Run the module's nf-test suite |
| `nf-core modules bump-versions` | Bump tool versions in modules |

```bash
# Reuse before you rebuild: install an existing module
nf-core modules install fastqc
nf-core modules install samtools/sort

# Author a new one, then lint + test it
nf-core modules create mytool
nf-core modules lint mytool
nf-core modules test mytool
```

Tool naming uses `tool` or `tool/subtool` (e.g. `samtools/sort`). Installed modules are pinned by git SHA in `modules.json`.

## Subworkflows

Same lifecycle as modules, for chains of modules. Source: https://nf-co.re/docs

| Command | Purpose |
|---------|---------|
| `nf-core subworkflows list remote/local` | List available/installed subworkflows |
| `nf-core subworkflows info <name>` | Show a subworkflow's interface |
| `nf-core subworkflows install <name>` | Install into `subworkflows/nf-core/` |
| `nf-core subworkflows update <name>` | Update an installed subworkflow |
| `nf-core subworkflows remove <name>` | Remove a subworkflow |
| `nf-core subworkflows create [name]` | Scaffold a new subworkflow |
| `nf-core subworkflows lint <name>` | Lint against subworkflow specs |
| `nf-core subworkflows test <name>` | Run the subworkflow's nf-test suite |

```bash
nf-core subworkflows install bam_sort_stats_samtools
nf-core subworkflows create align_bwa
nf-core subworkflows test align_bwa
```

## Test datasets

```bash
nf-core test-datasets list              # list test-data branches
nf-core test-datasets search <term>     # find small test files in nf-core/test-datasets
```

Use these tiny, version-controlled files in module/pipeline tests (see `references/testing.md`).

## Typical developer loop

```bash
nf-core pipelines create                       # scaffold
nf-core modules install fastqc                 # reuse community modules
nf-core modules create mytool                  # add a custom one
nf-core modules test mytool                    # nf-test it
nf-core subworkflows install bam_sort_stats_samtools
nf-core pipelines schema build                 # keep schema in sync with params
nf-core pipelines lint                          # validate everything
prettier --write .                             # format (Harshil alignment)
```

See `references/developing.md` for what each generated file should contain, and `references/testing.md` for nf-test details.
