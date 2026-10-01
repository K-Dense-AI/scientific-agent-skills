# Programming, Projects, Analysis, and Tests

This reference targets MATLAB R2026a. Base MATLAB, separately licensed
products, and GNU Octave must not be conflated.

## Choose the right code artifact

| Artifact | Workspace | Best use | Main risk |
|---|---|---|---|
| script `.m` | caller/base workspace | small reviewed orchestration | hidden inputs, leaked variables, path/state dependence |
| function `.m` | local workspace | reusable computation and automation | implicit conversions or undocumented side effects |
| live script `.mlx` | script-like interactive workspace | narrative exploration and teaching | opaque archive, embedded output, weak text review |
| class `.m` | object state and methods | durable abstractions | constructors, listeners, serialization callbacks |
| MEX | native process code | approved performance/interface work | arbitrary native execution |

Prefer a function with explicit inputs, outputs, and an `arguments` block.
Keep a top-level script thin. Export reviewed live code to plain `.m` before
static inspection. Never open or run an untrusted project, live script, app,
class, MEX file, or package.

Scripts share the base workspace and leave variables there. Functions,
including local functions, have private workspaces. Since R2024a, local
functions in scripts can appear anywhere in the file except inside conditional
contexts. The main function should match its filename.

```matlab
function summary = summarizeSignal(signal, options)
%SUMMARIZESIGNAL Return deterministic summary statistics.
arguments
    signal (:,1) double {mustBeFinite}
    options.Center (1,1) logical = true
end

if options.Center
    signal = signal - mean(signal);
end
summary = struct( ...
    "Count", numel(signal), ...
    "Mean", mean(signal), ...
    "StandardDeviation", std(signal));
end
```

### Argument validation details

- A size declaration such as `(:,1)` permits a column of any height.
- Size declarations also reshape compatible vectors or expand scalars. If
  orientation must be rejected rather than normalized, use a validator such
  as `mustBeColumn` without a size declaration that reshapes first.
- A class declaration can convert compatible input. Do not mistake conversion
  for validation.
- Validators such as `mustBeFinite` check values without changing them.
- A default makes an argument optional. Required positional inputs precede
  optional inputs.
- Name-value inputs use a structure name in the signature and dotted fields in
  the block.
- `namelengthmax` is 2048 from R2025a onward; filesystem limits can be shorter.
  The bundled static helpers intentionally retain a 63-character subset.
- Code generation support is a MATLAB Coder capability with additional
  restrictions and a separate license; an `arguments` block alone does not
  make code generation available.

## Workspace and path hygiene

1. Derive files from a confirmed project root, not the user's incidental
   current folder.
2. Use `fullfile`; never construct paths by concatenating separators.
3. Add the narrowest reviewed directory. Avoid broad `genpath` because it can
   expose hidden, generated, test, private, or malicious files.
4. Do not silently mutate `path`, `userpath`, preferences, startup files, or
   Java/native search paths.
5. Avoid `global`, `persistent` cache state without invalidation, and broad
   clearing. `clear all` can clear loaded functions and disrupt debugging.
6. Use `onCleanup` for resources such as files and temporary state.
7. Pass loaded data through a structure (`S = load(...)`) rather than injecting
   names into a function or base workspace—but only after the MAT file is
   trusted.

MATLAB runs `startup.m` when it is found on the search path and `finish.m` on
normal exit. Projects can add paths and run startup/shutdown actions. Review all
of these before execution.

## Dynamic and external execution surfaces

Escalate any use of:

- `eval`, `evalin`, `assignin`, `str2func`, text-derived `feval`, dynamic
  property or callback names;
- shell entry points (`system`, `unix`, `dos`, `!`);
- Java class paths/methods, .NET assemblies, Python (`py.*`, `pyrun`,
  `pyrunfile`), MEX, C/C++ libraries, and generated code;
- timers, UI callbacks, listeners, project tasks, build tasks, package startup,
  and test fixtures with external effects;
- object loading (`loadobj`, `matlab.mixin.CustomElementSerialization`) and
  System object load hooks.

Function handles are safer than text dispatch only when the handle itself comes
from trusted code. Never pass untrusted text into a dispatch mechanism. Static
scanning is triage, not proof of absence.

## MATLAB Projects

A project can track files, control the path, declare references and packages,
run startup/shutdown tasks, integrate source control, and analyze dependencies.
Use project APIs only after reviewing project metadata and tasks.

Recommended project record:

- project name and root;
- MATLAB release and architecture;
- entry points and test roots;
- required and optional MathWorks products, each with license status
  `unknown`, `confirmed`, or `unavailable`;
- external system dependencies and generated artifacts;
- startup/shutdown actions and path changes;
- RNG/tolerance/data-schema policy.

Dependency Analyzer and `matlab.codetools.requiredFilesAndProducts` use static
analysis. Dynamic dispatch, overloaded methods, callbacks, generated names, and
conditional paths can cause misses or false positives. Their product lists do
not prove that a license can be checked out.

## Code Analyzer and compatibility checks

Use these only on trusted text:

- `codeIssues(path)` returns a structured Code Analyzer result and supports
  programmatic fixes for eligible issues.
- `checkcode(path)` remains useful for text-oriented or legacy automation.
- `codeCompatibilityReport(path)` finds potential issues after a release
  upgrade.
- Project Upgrade can check and apply some release migrations and produce a
  report.

Do not auto-apply fixes across a scientific codebase without tests. Analyzer
silence does not establish numerical correctness, security, toolbox
availability, or Octave compatibility.

Migration sequence:

1. Freeze representative outputs and tolerance rationale in the old release.
2. Record release, products, compilers, BLAS/threading context, RNG algorithm
   and seed, and external data schema.
3. Run static compatibility and dependency analysis.
4. Read every relevant product's release notes and bug reports.
5. Migrate shared libraries before applications.
6. Run unit, integration, numerical-equivalence, graphics, and performance
   checks.
7. Investigate differences rather than automatically widening tolerances.

R2026a-specific checks include changed/removed APIs in release notes, new JSON
table/timetable I/O, Python 3.13 support, string-array Python conversion,
interactive HTML graphics export, and platform/compiler support. R2026a no
longer ships new MATLAB releases for Intel Macs.

## Unit testing

Base MATLAB includes script-, function-, and class-based `matlab.unittest`
testing. Keep tests deterministic and independent of order.

```matlab
classdef TestSummarizeSignal < matlab.unittest.TestCase
    methods (Test)
        function centersFiniteColumn(testCase)
            actual = summarizeSignal([1; 2; 3]);
            testCase.verifyEqual(actual.Count, 3);
            testCase.verifyEqual(actual.Mean, 0, AbsTol=1e-14);
        end

        function rejectsNonfiniteInput(testCase)
            testCase.verifyError( ...
                @() summarizeSignal([1; NaN]), ...
                "MATLAB:validators:mustBeFinite");
        end
    end
end
```

Use domain-derived `AbsTol` and `RelTol`; exact checks remain appropriate for
integers, strings, dimensions, and invariants. Isolate file output in temporary
folders and refuse network, interactive dialogs, or real credentials in unit
tests.

Product boundaries:

- `runtests`, `testsuite`, `matlab.unittest.TestCase`, and ordinary framework
  plugins are base MATLAB.
- Parallel test execution requires Parallel Computing Toolbox.
- Dependency-based test selection, MATLAB Test Manager, Code Quality Dashboard,
  advanced coverage, generated tests, and equivalence workflows can require
  MATLAB Test.
- Requirements traceability can require Requirements Toolbox; generated-code
  workflows can require MATLAB Coder, MATLAB Compiler SDK, Embedded Coder, or
  other named products.

In R2026a, `runtests` automatically opens a project for tests belonging to a
project that is not already open and closes it afterward. This may execute
reviewed project startup and shutdown actions; it is not safe for untrusted
projects.

## Review checklist

- [ ] Main function and filename agree.
- [ ] Inputs, shapes, classes, units, missingness, and outputs are documented.
- [ ] No hidden base-workspace dependency.
- [ ] Dynamic/external execution surfaces are absent or explicitly approved.
- [ ] Paths are project-local and narrow.
- [ ] Resources close on both success and failure.
- [ ] Errors have stable identifiers where tests rely on them.
- [ ] Tests cover edge shapes, empty values, missing values, nonfinite values,
      numerical tolerances, and failure behavior.
- [ ] Required products are declared separately from confirmed license status.
- [ ] Migration evidence includes release notes and representative baselines.

## Sources (reviewed 2026-10-01)

- [Scripts vs. Functions](https://www.mathworks.com/help/matlab/matlab_prog/scripts-and-functions.html)
- [Create Scripts](https://www.mathworks.com/help/matlab/matlab_prog/create-scripts.html)
- [`arguments`](https://www.mathworks.com/help/matlab/ref/arguments.html)
- [`mustBeColumn`](https://www.mathworks.com/help/matlab/ref/mustbecolumn.html)
- [`namelengthmax`](https://www.mathworks.com/help/matlab/ref/namelengthmax.html)
- [Local Functions](https://www.mathworks.com/help/matlab/matlab_prog/local-functions.html)
- [MATLAB Projects](https://www.mathworks.com/help/matlab/projects.html)
- [Analyze Project Dependencies](https://www.mathworks.com/help/matlab/matlab_prog/analyze-project-dependencies.html)
- [`requiredFilesAndProducts`](https://www.mathworks.com/help/matlab/ref/matlab.codetools.requiredfilesandproducts.html)
- [MATLAB Code Analyzer Report](https://www.mathworks.com/help/matlab/matlab_prog/matlab-code-analyzer-report.html)
- [`codeCompatibilityReport`](https://www.mathworks.com/help/matlab/ref/codecompatibilityreport.html)
- [Project Upgrade](https://www.mathworks.com/help/matlab/matlab_prog/upgrade-projects.html)
- [Run Unit Tests](https://www.mathworks.com/help/matlab/run-unit-tests.html)
- [`runtests` R2026a history](https://www.mathworks.com/help/matlab/ref/runtests.html)
- [MATLAB Test product boundary](https://www.mathworks.com/products/matlab-test.html)
- [MATLAB release notes](https://www.mathworks.com/help/matlab/release-notes.html)
