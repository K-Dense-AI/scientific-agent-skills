# Testing with nf-test

Targets **nf-test 0.9.5**, Nextflow **26.04.6**, and nf-core tools **4.1.0**. Sources: [nf-test test CLI](https://www.nf-test.com/docs/cli/test/), [assertions](https://www.nf-test.com/docs/assertions/assertions/), and [nf-core module testing](https://nf-co.re/docs/specifications/components/modules/testing). Installed-module/BAM-plugin examples below are illustrative and require their pinned module, tool, plugin and fixture. A tiny two-read BAM test exercised the teaching wrapper from `developing.md` with local SAMtools 1.24, including real sorting, stub versions, and snapshots.

## Table of Contents

- [Setup](#setup)
- [Test file structure](#test-file-structure)
- [Testing a module (process)](#testing-a-module-process)
- [Assertions](#assertions)
- [Snapshot testing](#snapshot-testing)
- [Testing workflows and pipelines](#testing-workflows-and-pipelines)
- [Running tests](#running-tests)
- [nf-core integration](#nf-core-integration)

## Setup

Installation alternatives below are illustrative; the tested runtime was the
pinned release archive. The official [installer](https://www.nf-test.com/installation/)
takes the release number as its first argument.

```bash
# Option 1: Conda
conda install -c conda-forge -c bioconda nf-test=0.9.5

# Option 2: upstream installer
curl -fsSL https://get.nf-test.com -o install-nf-test.sh
# Review the installer before executing it.
bash install-nf-test.sh 0.9.5
mkdir -p "$HOME/.local/bin"
mv nf-test "$HOME/.local/bin/"
export PATH="$HOME/.local/bin:$PATH"
nf-test version

nf-test init        # creates nf-test.config + tests/ scaffolding in a project
```

Test files end in `.nf.test` and live next to the component (`tests/main.nf.test`). Expected results are stored in a sibling `.nf.test.snap` snapshot file.

## Test file structure

Choose the scope matching what you test:

- `nextflow_process` — a single process/module
- `nextflow_workflow` — a (sub)workflow
- `nextflow_pipeline` — a whole pipeline (`main.nf`)
- `nextflow_function` is also available for testing a function.

Common layout:

```groovy
nextflow_process {

    name "Test SAMTOOLS_SORT"
    script "../main.nf"          // the module under test
    process "SAMTOOLS_SORT"

    tag "modules"
    tag "modules_nfcore"
    tag "samtools"
    tag "samtools/sort"

    test("sarscov2 - bam") {
        when {
            process {
                """
                input[0] = [
                    [ id:'test', single_end:false ],
                    file(params.modules_testdata_base_path + 'genomics/sarscov2/illumina/bam/test.paired_end.sorted.bam', checkIfExists: true)
                ]
                input[1] = [[:], [], []] // BAM input: no reference needed
                input[2] = ''            // do not request an inline index
                """
            }
        }
        then {
            assertAll(
                { assert process.success },
                { assert snapshot(process.out).match() }
            )
        }
    }
}
```

- `input[0]`, `input[1]`, … bind positional process inputs. The current `SAMTOOLS_SORT` example above has three inputs; a copied older module can differ. Always match the installed `main.nf`/`meta.yml`.
- A `setup { }` block can run prerequisite processes to produce inputs.
- A `params { }` block sets parameters; a `config "..."` line loads a config for the test.
- nf-core requires a **stub test** alongside the real one — add `options "-stub"` inside a `test(...)` block to exercise the `stub:` script.

## Testing a module (process)

The `when` block supplies inputs; the `then` block asserts on results. Use a `setup` block when a module needs another module's output first (the following test belongs in a `nextflow_process` scope targeting `SAMTOOLS_INDEX`):

```groovy
test("sort then index") {
    setup {
        run("SAMTOOLS_SORT") {
            script "../../sort/main.nf"
            process {
                """
                input[0] = [ [id:'test'], file(params.test_data + 'test.bam', checkIfExists:true) ]
                input[1] = [[:], [], []]
                input[2] = ''
                """
            }
        }
    }
    when {
        process {
            """
            input[0] = SAMTOOLS_SORT.out.bam
            """
        }
    }
    then {
        assert process.success
        assert snapshot(process.out).match()
    }
}
```

## Assertions

Inside `then`, wrap multiple checks in `assertAll(...)` so all failures are reported at once. Useful handles and helpers:

| Expression | Checks |
|------------|--------|
| `process.success` / `process.failed` | Test workflow run succeeded / failed (not an individual task’s scientific validity) |
| `process.exitStatus == 0` | Nextflow invocation exit code |
| `process.out.<emit>` | A named output channel's contents |
| `process.out.bam.get(0)` | First emitted item |
| `workflow.success`, `workflow.trace.tasks().size()` | Workflow outcome / task count |
| `path(process.out.bam[0][1]).exists()` | A file exists |
| `snapshot(...).match()` | Compare to stored snapshot |
| `assertContainsInAnyOrder(ch, [...])` | A channel contains the given items (order-agnostic) |

> There is **no** `assertContainsInOrder`. For ordered or substring checks on file contents, read the lines and assert directly, e.g. `assert path(out[0][1]).readLines().any { it.contains('Done') }` or `assert path(out[0][1]).readLines().last().contains('completed')`.

nf-test sorts captured channel values for assertions; indexed assertions do not prove task completion order. In 0.9.5, trace `succeeded()` counts `COMPLETED` entries, while cached entries are not classified as succeeded; do not interpret this helper as a universal cache-aware success check.

Plugins extend assertions for domain files (e.g. `nft-bam` for BAM, `nft-vcf` for VCF, `nft-utils`); nf-core enables these in `nf-test.config`. Pin the plugin version; the [nft-bam API](https://github.com/nvnieuwk/nft-bam/blob/main/docs/usage.md) defines the checksum helper used below. Example with a file-content assertion for a topic-based module:

```groovy
then {
    assertAll(
        { assert process.success },
        { assert path(process.out.bam[0][1]).exists() },
        { assert snapshot(
            bam(process.out.bam[0][1]).getSamLinesMD5(),
            process.out.versions_samtools
          ).match() }
    )
}
```

## Snapshot testing

`snapshot(x).match()` serializes `x` and compares it to the `.nf.test.snap` file. The **first** run records the snapshot; later runs fail if output changes.

- Snapshot stable things: deterministic file content/checksums, version tuples (or legacy YAML), and cardinalities. Verify records/sample identities and numeric tolerances separately. A new snapshot can preserve a wrong or empty result; review it against an independent expected answer.
- Stub output/success only tests wiring. A real tiny biological fixture with expected counts, coordinates, units and reference provenance is necessary to assess scientific behavior.
- Regenerate intentionally-changed snapshots with `nf-test test --update-snapshot`.
- Name multiple snapshots in one test with `.match("bam")`, `.match("versions")`.

## Testing workflows and pipelines

```groovy
nextflow_pipeline {
    name "Test full pipeline"
    script "../main.nf"
    test("default params") {
        when { params { outdir = "$outputDir"; input = "tests/samplesheet.csv" } }
        then {
            assert workflow.success
            assert workflow.trace.succeeded().size() > 0
        }
    }
}
```

Use tiny inputs from nf-core/test-datasets (`nf-core test-datasets search ...`) so tests stay fast.

## Running tests

```bash
nf-test test                                  # run everything
nf-test test modules/nf-core/samtools/sort/   # a directory
nf-test test tests/main.nf.test               # one file
nf-test test --tag samtools                    # by tag
nf-test test --profile docker                  # choose container engine
nf-test test --update-snapshot                 # accept new snapshots
nf-test test --changed-since HEAD^             # only components changed since a ref
nf-test test --only-changed --ci               # select current worktree changes; missing snapshots fail
```

`nf-test.config` sets the test directory, default profile, and plugins. CI typically runs only changed components via `--changed-since` plus the nf-core `nf-test` GitHub Action.

## nf-core integration

In nf-core/modules-like repositories, the wrapper runs tests twice to check snapshot stability (`--once` skips this). It does not work for modified modules inside pipeline repositories; use `nf-test test <path>` there. `create` scaffolds the test files:

```bash
nf-core modules create mytool         # scaffolds tests/main.nf.test
nf-core modules test mytool            # runs the module's nf-test suite
nf-core subworkflows test mysubwf
```

Select supported profiles explicitly and review generated snapshots rather than automatically accepting updates. Every nf-core module/subworkflow must ship passing nf-test tests (including a stub test) with committed snapshots; `nf-core modules lint` checks their presence. See `references/developing.md`.
