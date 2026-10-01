# GNU Octave 11.3.0 Compatibility

GNU Octave 11.3.0 is the current stable release as of 2026-10-01 (released
2026-06-01). It is free software under GPLv3+. MATLAB R2026a is proprietary.
Do not describe Octave as MATLAB, a licensed toolbox substitute, or a
drop-in guarantee.

## Compatibility policy

Use three labels:

- **portable subset**: tested in both exact target versions;
- **MATLAB-only**: depends on MATLAB syntax, objects, projects, products, or
  deployment;
- **Octave-only**: uses Octave syntax, packages, BIST, or runtime behavior.

Source resemblance is not enough. Compare outputs with scientific tolerances,
edge cases, warnings, graphics, performance, and file round trips.

## Current release changes

Octave 11 introduced improved `classdef` support, broadcasting for sparse,
diagonal, and permutation matrices, more MATLAB-compatible `nanflag`/`vecdim`
behavior, and many function/performance changes. It is still not fully
compatible. NEWS-11 also records behavior changes that can break older Octave
code, including stricter accepted types for several statistics functions.

Read both the current manual and NEWS before migrating to 11.3.0. The online
`latest` manual reviewed on this date identifies its generated content as
11.1.0 while the project download/news page identifies 11.3.0 as current;
consult NEWS-11 for the maintenance-release delta.

## Command-line differences

Reviewed Octave argv usually includes:

```text
["octave", "--no-init-all", "--no-history", "--quiet", "--no-gui", "main.m"]
```

The bundled planner returns argv but never executes it.

Current manual behavior:

- `--eval`/`-e` evaluates code and exits unless `--persist` is set;
- a filename executes and exits;
- `--no-gui` selects CLI;
- `--no-window-system` disables graphics/window-system use;
- `--no-init-all`/`--norc` skips system and user initialization;
- `--path` adds a function path;
- `--quiet` suppresses greeting; `--no-history` avoids history writes.

Octave startup can execute site/version files, user configuration,
project-local `.octaverc`, and MATLAB-compatible `startup.m`. Skipping all
startup files can improve reproducibility but can also remove expected package
or path setup. Review the plan.

MATLAB uses `-batch`, has different startup processing, and has no Octave
`--no-init-all` option. Never pass the same flags to both.

## Syntax: portable versus Octave-only

Prefer:

- `%` comments;
- `...` continuation;
- `end` block terminators;
- explicit `x = x + 1`;
- intermediate variables before indexing a function result;
- short-circuit `&&`/`||` for scalar conditions;
- ordinary `.m` functions with matching filenames.

Avoid these Octave-only extensions in portable code:

- `#` comments;
- `endif`, `endfor`, `endfunction`;
- `++`, `--`, `+=`, and related compound assignment;
- `do ... until`;
- indexing directly into an expression result;
- backslash line continuation;
- Octave package/BIST directives in MATLAB production files unless isolated.

Both support implicit expansion/broadcasting in many modern cases, but special
classes and edge cases differ. Octave 11 expanded broadcasting for special
matrix types. Test orientation, sparse output, empty dimensions, and mixed
classes in both.

## MATLAB features with no assumed Octave equivalent

The current Octave manual does not establish drop-in equivalents for:

- MATLAB `arguments` blocks and all validators/name-value semantics;
- `table`/`timetable` workflows and their R2026a JSON conversions;
- MATLAB Projects, dependency analyzer, Project Upgrade, or project-aware
  `runtests`;
- `matlab.unittest`, MATLAB Test, Code Quality Dashboard;
- live scripts `.mlx`, App Designer `.mlapp`, `.fig` object compatibility;
- Simulink and MathWorks toolbox APIs;
- MATLAB Engine API for Python, MATLAB Compiler/Runtime, MATLAB Coder, or
  MathWorks deployment products;
- full MATLAB `classdef`, events/listeners, serialization, and metaclass
  behavior.

Use feature detection and separate adapters only after testing. Do not silently
replace a missing MATLAB toolbox function with a similarly named Octave
package function.

## Packages versus toolboxes

Octave packages are distributed separately from core Octave. MATLAB toolboxes
are separately licensed MathWorks products. APIs, algorithms, defaults,
validation, object models, and release schedules differ.

Never run `pkg install`, load an untrusted package, or alter `.octaverc`
automatically. Package installation can fetch/build/execute code. Record exact
package name/version/source/checksum and obtain approval.

`pkg load` mutates the function path and can shadow core or project functions.
Test `which`/resolution only in a trusted approved runtime.

## Tests

Octave's built-in self-test system scans `%!` blocks and uses `test`. It is not
`matlab.unittest`.

```matlab
%!test
%! observed = hypot(3, 4);
%! assert(observed, 5, 1e-12);
```

Portable production functions and runtime-specific test harnesses should be
separate when test syntax differs. The nonexecuting planner can prepare an
Octave BIST argv, but an approved runtime is required to run it.

## MAT and HDF5 compatibility

Octave 11 supports writing MATLAB v4, v6, and v7 binary formats. It **does not
implement saving MATLAB v7.3**.

Octave can save its own HDF5 representation when built with HDF5. Its `load
-hdf5` has limited ability to read MATLAB v7.3, mainly for supported numeric
content; many types are unsupported. An Octave HDF5 file is not automatically
a MATLAB v7.3 file.

Octave's current manual states that `classdef` objects are saved as structures
in supporting formats and are not restored as `classdef` objects. This differs
substantially from MATLAB object serialization.

Never load untrusted MAT/HDF5 files in either runtime. Use the bundled bounded
technical inventory first, then escalate object/opaque/function/external-link
content.

For portable simple data, use MATLAB v7 only after testing classes, shapes,
text, sparse/complex values, and metadata. Prefer schema-documented
language-neutral formats where feasible.

## Graphics

Basic calls such as `plot`, labels, legends, images, surfaces, and `print` are
similar, but renderers, fonts, properties, layout, transparency, callbacks,
and export formats differ.

Do not assume Octave implements R2026a `exportgraphics`, SVG/HTML web canvas,
`tiledlayout`, UI objects, or property behavior. Build a small compatibility
test and compare exported dimensions, font embedding, vector/raster content,
colors, and clipping.

Octave 11 NEWS documents graphics compatibility changes such as colorbar and
event-field behavior. Review NEWS for each update.

## Numerical differences

Even when both runtimes call similarly named LAPACK/BLAS-backed functions,
results can differ because of:

- linked libraries, versions, threads, and architecture;
- solver implementation/default/tolerance changes;
- sparse ordering and pivot choices;
- random generator algorithms and streams;
- toolbox/package algorithms;
- floating reduction order;
- unsupported or converted classes.

Compare residuals, invariants, objective/feasibility, and domain observables.
Do not demand identical eigenvector signs, cluster bases, or bitwise
floating-point output without a justified contract.

## Portability checklist

- [ ] Exact MATLAB and Octave versions recorded.
- [ ] Core versus toolbox/package requirements separated.
- [ ] Only portable syntax used in shared source.
- [ ] Shapes, missing values, strings, and implicit expansion tested.
- [ ] RNG algorithm/seed behavior tested separately.
- [ ] Numerical tolerances justified.
- [ ] MAT/HDF5 round trips cover every used class.
- [ ] Graphics compared from exported files.
- [ ] Runtime-specific tests and deployment kept separate.
- [ ] No package installation or code execution occurred implicitly.

## Sources (reviewed 2026-10-01)

- [GNU Octave home/current release](https://octave.org/)
- [GNU Octave 11 release notes](https://octave.org/NEWS-11.html)
- [GNU Octave current manual](https://docs.octave.org/latest/)
- [Command-Line Options](https://docs.octave.org/latest/Command-Line-Options.html)
- [Startup Files](https://docs.octave.org/latest/Startup-Files.html)
- [Simple File I/O and MAT v7.3 limitation](https://docs.octave.org/latest/Simple-File-I_002fO.html)
- [`classdef` compatibility status](https://docs.octave.org/latest/classdef-Classes.html)
- [Test Functions](https://docs.octave.org/latest/Test-Functions.html)
- [GNU GPL](https://octave.org/license.html)
