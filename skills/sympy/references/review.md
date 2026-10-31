# SymPy review and execution scope

Reviewed 2026-10-01 against current official SymPy documentation and released
1.14.0 source. An audit of 260 imported API objects and matrix base classes
matched 114 installed Python source files byte-for-byte to the official 1.14.0
tag. SymPy has no hosted REST endpoint, authentication, pagination or
remote-data workflow in this skill. Core operations execute locally.

## Tested environment

Python 3.13.3; SymPy 1.14.0; mpmath 1.3.0; NumPy 2.5.3; SciPy 1.18.1;
Matplotlib 3.11.2; IPython 9.17.1; ipywidgets 8.1.9;
antlr4-python3-runtime 4.11.1. SymPy 1.14.0 declares `mpmath>=1.1,<1.4`, so
mpmath 1.4.x cannot replace this pin. Core SymPy supports Python 3.9+; the tested
optional NumPy/SciPy versions require Python 3.12+.

Every Python documentation block was executed as an ordered session within its
own file, except the two explicitly illustrative compiled-wrapper examples
(`autowrap` and `ufuncify`). 185 blocks passed. Notebook/widget code executed with
an Agg plotting backend; a live Jupyter frontend and visual notebook rendering
were not verified. Generated Python source was imported and compared with the
symbolic expression. C/Fortran source emission ran, but generated native code,
Cython/f2py compilation and LaTeX document rendering were not tested.

The repository suite `tests/sympy/test_examples.py` contains 30 native behavioral
checks. It covers exact arithmetic, assumptions/branches, excluded poles,
integral ordering, incomplete and local solver outputs, ODE residuals, linear
systems, complex condensed SVD, matrix functions/conditioning, discrete events,
mechanics linearization, beam/truss/cable equilibrium, unit conventions,
control-system conversion, musculotendon construction, quantum operators,
Python source generation, lambdify shapes and strict LaTeX parsing.

## Limits found during execution

- In SymPy 1.14.0, `P((X > 0) & (Y > 0))` for separately created independent
  standard normals raises `AttributeError` involving `ProductContinuousDomain`.
  The reference computes `P(X > 0) * P(Y > 0)` only for those independent variables.
  This factorization does not apply to dependent random variables.
- `roots` can return `{}` for an irreducible quintic that has five complex roots.
  `Poly.all_roots()` preserves exact roots as `CRootOf` where needed.
- The released distributed-load `Cable.solve` implementation consumes only its
  first positional argument (lowest-point x), despite docstring wording about
  both x and y. Equal-height centered supports do not determine sag. Its reaction
  formulas also require independent equilibrium checks. The validated cable
  example uses a symmetric point load with explicit geometry.
- Symbolic mechanics examples check small idealized systems, not calibrated
  physical experiments. Units, boundary conditions, admissible parameter ranges
  and force/sign conventions remain part of the problem definition.

## Official references used

- [Current documentation and release](https://docs.sympy.org/latest/index.html)
  and [1.14.0 dependency declarations](https://github.com/sympy/sympy/blob/sympy-1.14.0/setup.py).
- [Best practices](https://docs.sympy.org/latest/explanation/best-practices.html),
  [assumptions](https://docs.sympy.org/latest/guides/assumptions.html),
  [solveset](https://docs.sympy.org/latest/modules/solvers/solveset.html),
  [general solvers](https://docs.sympy.org/latest/modules/solvers/solvers.html),
  [polynomial roots](https://docs.sympy.org/latest/modules/polys/reference.html)
  and [calculus](https://docs.sympy.org/latest/modules/calculus/index.html).
- [Matrix methods](https://docs.sympy.org/latest/modules/matrices/matrices.html),
  [number theory](https://docs.sympy.org/latest/modules/ntheory.html),
  [permutation groups](https://docs.sympy.org/latest/modules/combinatorics/perm_groups.html),
  [sets](https://docs.sympy.org/latest/modules/sets.html),
  [geometry](https://docs.sympy.org/latest/modules/geometry/index.html),
  [statistics](https://docs.sympy.org/latest/modules/stats.html) and
  [special functions](https://docs.sympy.org/latest/modules/functions/special.html).
- [Kane/Lagrange methods](https://docs.sympy.org/latest/modules/physics/mechanics/api/kane_lagrange.html),
  [inertia/bodies](https://docs.sympy.org/latest/modules/physics/mechanics/api/part_bod.html),
  [joints](https://docs.sympy.org/latest/modules/physics/mechanics/api/joint.html),
  [active deprecations](https://docs.sympy.org/latest/explanation/active-deprecations.html),
  [quantum SHO released source](https://github.com/sympy/sympy/blob/sympy-1.14.0/sympy/physics/quantum/sho1d.py),
  [spin](https://docs.sympy.org/latest/modules/physics/quantum/spin.html),
  [gates](https://docs.sympy.org/latest/modules/physics/quantum/gate.html) and
  [gamma tensors](https://docs.sympy.org/latest/modules/physics/hep/index.html).
- [Unit systems](https://docs.sympy.org/latest/modules/physics/units/unitsystem.html),
  [quantities](https://docs.sympy.org/latest/modules/physics/units/quantities.html),
  [Gaussian optics](https://docs.sympy.org/latest/modules/physics/optics/gaussopt.html),
  [optical media](https://docs.sympy.org/latest/modules/physics/optics/medium.html),
  [beam](https://docs.sympy.org/latest/modules/physics/continuum_mechanics/beam.html),
  [truss](https://docs.sympy.org/latest/modules/physics/continuum_mechanics/truss.html),
  [cable](https://docs.sympy.org/latest/modules/physics/continuum_mechanics/cable.html),
  [control](https://docs.sympy.org/latest/modules/physics/control/lti.html) and
  [musculotendon](https://docs.sympy.org/latest/modules/physics/biomechanics/api/musculotendon.html).
- [lambdify](https://docs.sympy.org/latest/modules/utilities/lambdify.html),
  [codegen](https://docs.sympy.org/latest/modules/utilities/codegen.html),
  [autowrap/ufuncify](https://docs.sympy.org/latest/modules/utilities/autowrap.html),
  [printing](https://docs.sympy.org/latest/modules/printing.html) and
  [parsing](https://docs.sympy.org/latest/modules/parsing.html).
