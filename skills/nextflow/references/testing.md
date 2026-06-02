# Testing with nf-test

nf-test is the standard test framework for Nextflow. nf-core requires nf-test coverage for every module, subworkflow, and pipeline. Sources: https://www.nf-test.com and https://nf-co.re/docs/developing/testing/overview

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

```bash
# install (one of)
conda install -c bioconda nf-test
curl -fsSL https://get.nf-test.com | bash

nf-test init        # creates nf-test.config + tests/ scaffolding in a project
```

Test files end in `.nf.test` and live next to the component (`tests/main.nf.test`). Expected results are stored in a sibling `.nf.test.snap` snapshot file.

## Test file structure

Three test scopes match what you're testing:

- `nextflow_process` — a single process/module
- `nextflow_workflow` — a (sub)workflow
- `nextflow_pipeline` — a whole pipeline (`main.nf`)

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
                    file(params.modules_testdata_base_path + 'genomics/sarscov2/illumina/bam/test.bam', checkIfExists: true)
                ]
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

- `input[0]`, `input[1]`, … bind positional process inputs.
- A `setup { }` block can run prerequisite processes to produce inputs.
- A `params { }` block sets parameters; a `config "..."` line loads a config for the test.
- nf-core requires a **stub test** alongside the real one — add `options "-stub"` inside a `test(...)` block to exercise the `stub:` script.

## Testing a module (process)

The `when` block supplies inputs; the `then` block asserts on results. Use a `setup` block when a module needs another module's output first:

```groovy
test("sort then index") {
    setup {
        run("SAMTOOLS_SORT") {
            script "../../sort/main.nf"
            process {
                """
                input[0] = [ [id:'test'], file(params.test_data + 'test.bam', checkIfExists:true) ]
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
| `process.success` / `process.failed` | Task completed / failed |
| `process.exitStatus == 0` | Exit code |
| `process.out.<emit>` | A named output channel's contents |
| `process.out.bam.get(0)` | First emitted item |
| `workflow.success`, `workflow.trace.tasks().size()` | Workflow outcome / task count |
| `path(process.out.bam[0][1]).exists()` | A file exists |
| `snapshot(...).match()` | Compare to stored snapshot |
| `assertContainsInAnyOrder(ch, [...])` | A channel contains the given items (order-agnostic) |

> There is **no** `assertContainsInOrder`. For ordered or substring checks on file contents, read the lines and assert directly, e.g. `assert path(out[0][1]).readLines().any { it.contains('Done') }` or `assert path(out[0][1]).readLines().last().contains('completed')`.

Plugins extend assertions for domain files (e.g. `nft-bam` for BAM, `nft-vcf` for VCF, `nft-utils`); nf-core enables these in `nf-test.config`. Example with a file-content assertion:

```groovy
then {
    assertAll(
        { assert process.success },
        { assert path(process.out.bam[0][1]).exists() },
        { assert snapshot(
            bam(process.out.bam[0][1]).getSamLinesMD5(),
            process.out.versions
          ).match() }
    )
}
```

## Snapshot testing

`snapshot(x).match()` serializes `x` and compares it to the `.nf.test.snap` file. The **first** run records the snapshot; later runs fail if output changes.

- Snapshot stable things: file MD5s/checksums, `versions.yml`, list sizes — not absolute paths or timestamps.
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
nf-test test --only-changed --ci               # CI mode: fail (don't write) on a missing snapshot
```

`nf-test.config` sets the test directory, default profile, and plugins. CI typically runs only changed components via `--changed-since` plus the nf-core `nf-test` GitHub Action.

## nf-core integration

For nf-core components, prefer the wrapper commands — they run nf-test with the correct profiles, tags, and snapshot handling, and `create` scaffolds the test files:

```bash
nf-core modules create mytool         # scaffolds tests/main.nf.test
nf-core modules test mytool            # runs the module's nf-test suite
nf-core subworkflows test mysubwf
```

Every nf-core module/subworkflow must ship passing nf-test tests (including a stub test) with committed snapshots; `nf-core modules lint` checks their presence. See `references/developing.md`.
