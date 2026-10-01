# ML Conference Introduction Drafting Example

**Reviewed: 2026-10-01.** Illustrative, unexecuted writing scaffold. “ExampleKernel”
is fictional; bracketed measurements, proofs, citations, and release links must
be replaced by real evidence. No FlashAttention result or implementation is claimed.

## Problem and gap

```text
[Application] requires processing [input regime] under [resource constraints].
Existing approaches address [part of the problem], but [specific, source-supported
limitation] remains in [setting]. We investigate whether [testable question].
```

State the bottleneck actually measured. Dense attention has quadratic arithmetic
in sequence length for fixed head dimension, but an optimized kernel need not
store an N-by-N matrix. Do not equate matrix size with total arithmetic cost or
assume every modern accelerator is memory-bound for every workload.

## Approach

```text
ExampleKernel uses [specific idea] to address [measured bottleneck]. The method
preserves [tested semantics or proved property] under [explicit assumptions].
It changes [implementation/design choice], with [known tradeoff].
```

Name a complexity result only if it has been proved, with its model of computation,
parameters, and assumptions. Do not recycle an incorrect symbolic IO bound to
make a writing example look rigorous.

## Contributions (optional structure)

```text
Our contributions are:
- [Method or analysis], with its difference from [verified prior work].
- [Theorem or diagnostic] under [assumptions], established in [section].
- [Measured result] against [baseline/version] on [workload], with [uncertainty].
- [Actually available resource] under [access/license conditions].
```

Contribution bullets are a convention, not a universal NeurIPS/ICML rule.
A negative result or explanatory analysis need not promise a benchmark win.

## Evidence checks

- Report absolute metrics and distinguish percentage points from relative percent.
- State workload, batch size, precision, hardware, and software for runtime claims.
- Report mean/dispersion over actual independent runs; do not invent three seeds.
- Keep setup, tuning, and accuracy constraints comparable across baselines.
- State code availability only after verifying the real artifact and review-link policy.

Use the official year's author kit. The 2026 NeurIPS and ICML initial limits are
9 and 8 content pages respectively; they do not prescribe the introduction's
length or authorize moving evidence essential to review into optional appendices.

Sources:
- https://neurips.cc/Conferences/2026/MainTrackHandbook
- https://icml.cc/Conferences/2026/AuthorInstructions
