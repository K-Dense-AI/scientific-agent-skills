# Review and execution scope — 2026-10-01

This skill targets Pint 0.26.1, uncertainties 3.2.3, NumPy 2.5.3 and SciPy 1.18.1,
executed together on Python 3.13.3 in an isolated environment. Pint now requires
Python 3.12+ and NumPy 2+. Core local workflows require no credentials or service API.
No authenticated external scientific service was invoked.

## Reviewed contracts

- Pint: registries/application registry, Quantity conversion, offset and logarithmic
  arithmetic, context names and parameters, `wraps`, `check`, NumPy dispatch,
  custom definitions, formatting, and ufloat magnitudes. The 0.26 release adds offset
  string parsing, without making ambiguous offset arithmetic valid. Runtime checks
  cover spectroscopy, chemistry, Boltzmann and Gaussian conversions. Other bundled
  context definitions were inspected in released source, not exhaustively executed.
- uncertainties: `ufloat`, identity, `correlated_values`, `correlated_values_norm`,
  covariance/correlation matrices, derivatives, components, umath/unumpy, formatting,
  and `wrap`. Correlated variables use independent latent variables internally;
  their derivative dictionary is not indexed by the original correlated objects.
  Deprecated absolute-value helpers were replaced in the bundled evaluator.
- NumPy/SciPy: array functions and RNG distributions, positive-semidefinite correlation
  factors, quantiles, SD, Student-t factors, erf, CODATA accessors and weighted
  `curve_fit` covariance. `np.log` accepts an output buffer as its second positional
  argument; the evaluator explicitly implements a logarithm base instead.
- JCGM: Type A/B interpretation, covariance propagation, independent-input
  Welch-Satterthwaite limitations, reporting, numerical tolerance and the adaptive
  Monte Carlo requirement. The bundled fixed-trial comparison remains diagnostic:
  `endpoint_agreement` is a boolean and `gum_framework_validated` is null.
- Unit semantics: angular versus cyclic frequency, molecular mass versus molar mass,
  ppm kinds, pH activity, wavelength in a medium, exact versus measured constants,
  and uncertainty units for offset/logarithmic quantities.
- Plausibility: all 14 group formulas, 8 scales and 22 band conversions executed.
  Corrected reversed Damkohler interpretation and removed unconditional equilibrium,
  breakup, tracer-validity and thermal-noise conclusions. Bands remain explicitly
  illustrative; historical textbook sources were not all independently reread.

## Execution evidence and limits

The per-skill isolated suite passes 113 tests. A separate native smoke run passes
114 numerical/API checks and confirms five relevant released source files match the
installed wheels byte-for-byte. Documented command-line workflows and all six help
commands were executed. These are synthetic numerical checks, not measurement
traceability, calibrated coverage, experimental validation, clinical reference ranges,
or a certification of any physical model.

`pint-pandas` and `pint-xarray` are optional ecosystem pointers verified against their
current official documentation; neither integration was installed or executed.
Arbitrary user model/fit fragments are illustrative and need actual input data and
an appropriate error model. The helper does not sample Student-t inputs or estimated
variance uncertainty, propagate context-parameter uncertainties, or prove convergence
of reciprocal/heavy-tailed distributions. Finite samples with no NaN do not establish
that a distribution has a finite mean or variance.

## Primary sources

- [Pint release notes](https://pint.readthedocs.io/en/stable/changes.html)
- [Pint 0.26.1 unit/context definitions](https://github.com/hgrecco/pint/blob/0.26.1/pint/default_en.txt)
- [Pint 0.26.1 constants](https://github.com/hgrecco/pint/blob/0.26.1/pint/constants_en.txt)
- [Pint temperature arithmetic](https://pint.readthedocs.io/en/stable/user/nonmult.html)
- [Pint logarithmic units](https://pint.readthedocs.io/en/stable/user/log_units.html)
- [Pint contexts](https://pint.readthedocs.io/en/stable/user/contexts.html)
- [Pint wrapping](https://pint.readthedocs.io/en/stable/advanced/wrapping.html)
- [Pint NumPy integration](https://pint.readthedocs.io/en/stable/user/numpy.html)
- [Pint definitions](https://pint.readthedocs.io/en/stable/advanced/defining.html)
- [Pint formatting](https://pint.readthedocs.io/en/stable/user/formatting.html)
- [Pint serialization](https://pint.readthedocs.io/en/stable/advanced/serialization.html)
- [Pint-pandas](https://pint-pandas.readthedocs.io/en/latest/)
- [Pint-xarray](https://pint-xarray.readthedocs.io/en/stable/)
- [uncertainties user guide](https://uncertainties.readthedocs.io/en/latest/user_guide.html)
- [uncertainties technical guide](https://uncertainties.readthedocs.io/en/latest/tech_guide.html)
- [uncertainties 3.2.3 source](https://github.com/lmfit/uncertainties/blob/3.2.3/uncertainties/core.py)
- [NumPy multivariate sampling](https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.multivariate_normal.html)
- [NumPy standard deviation](https://numpy.org/doc/stable/reference/generated/numpy.std.html)
- [SciPy curve_fit](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.curve_fit.html)
- [SciPy constants](https://docs.scipy.org/doc/scipy/reference/constants.html)
- [SciPy 1.15 CODATA update](https://docs.scipy.org/doc/scipy-1.15.0/release/1.15.0-notes.html)
- [JCGM 100:2008](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf)
- [JCGM 101:2008](https://www.bipm.org/documents/20126/2071204/JCGM_101_2008_E.pdf)
- [JCGM GUM-6:2020 measurement models](https://www.bipm.org/documents/20126/2071204/JCGM_GUM_6_2020.pdf)
- [VIM measurement precision](https://jcgm.bipm.org/vim/en/2.15.html)
- [NIST TN 1297](https://nvlpubs.nist.gov/nistpubs/Legacy/TN/nbstechnicalnote1297.pdf)
- [BIPM SI Brochure, updated 2026](https://www.bipm.org/en/publications/si-brochure)
- [NIST CODATA 2022](https://physics.nist.gov/cuu/Constants/)
- [IUPAC pH](https://goldbook.iupac.org/terms/view/P04524)
- [ILAC G8 listing](https://ilac.org/publications-and-resources/ilac-guidance-series/)
- [NASA Reynolds number](https://www.grc.nasa.gov/www/k-12/airplane/reynolds.html)
- [NASA Mach number](https://www.grc.nasa.gov/www/k-12/airplane/mach.html)
- [Fogler reactor models](https://websites.umich.edu/~elements/7e/04chap/summary.html)
- [IAPWS viscosity](https://iapws.org/technical-guidance/release/viscosity)
- [IAPWS surface tension](https://iapws.org/documents/release/Surf-H2O.download)
- [CIE visible radiation](https://cie.co.at/eilvterm/17-21-003)

Some live documentation headers identify development builds (Pint) or the 1.18.0
manual (SciPy). Released-source checks and the stated installed versions bound the
execution claims. No general guarantee is inferred from a documentation URL returning
HTTP 200. The citation record was checked at the current arXiv landing page.
