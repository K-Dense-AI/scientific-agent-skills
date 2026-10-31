# Source ledger — reviewed 2026-10-01

## Execution evidence

The bundled CLI suite and synthetic smoke examples were run in isolated Python with NumPy 2.5.3
and SciPy 1.18.1. Tests cover analytical linear-PK identities, NCA, individual fitting, ordinary BE,
DDI arithmetic, TDM, scaling, event validation and PD helpers. Analytical and synthetic agreement
is numerical verification, not clinical validation or qualification for a regulatory application.

Pharmpy 2.2.0 was installed in a separate isolated environment. Seven transformations on the bundled
pheno model executed: QSS TMDD, indirect/direct/effect-compartment PD, allometry, transit absorption
and Michaelis-Menten elimination. Signatures for those methods, annotate_unit and
calculate_eta_shrinkage were inspected. Nineteen run_* tools were enumerated. No licensed NLME
estimation, R workflow or PBPK simulation was executed.

## Current interfaces and package metadata

- [Pharmpy changelog](https://pharmpy.github.io/latest/changelog.html):2.2.0, Python>=3.12 except 3.14.1,
  annotate_unit rename; [tools](https://pharmpy.github.io/latest/tools.html),
  [TMDD API](https://pharmpy.github.io/latest/api/pharmpy.modeling.set_tmdd.html),
  [shrinkage API](https://pharmpy.github.io/latest/api/pharmpy.modeling.calculate_eta_shrinkage.html).
- [NumPy trapezoid](https://numpy.org/doc/stable/reference/generated/numpy.trapezoid.html),
  [SciPy least_squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html),
  [solve_ivp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html).
- [nlmixr2 CRAN](https://cran.r-project.org/web/packages/nlmixr2/index.html):7.0.1, R>=4.1,
  rxode2>=5.0.0; [rxode2 changes](https://nlmixr2.github.io/rxode2/news/index.html).
- [OSP releases](https://github.com/Open-Systems-Pharmacology/Suite/releases):Suite 12 Update 3;
  [R interface news](https://github.com/Open-Systems-Pharmacology/OSPSuite-R/blob/main/NEWS.md):12.3.2.
- [ICON NONMEM](https://www.iconplc.com/solutions/technologies/nonmem):7.6 capabilities. Vendor
  legacy guide endpoints could not be fully fetched; no installed licensed engine was available.
- [PKPy authors](https://github.com/Gumgo91/PKPy); PyPI pkpy returned 404 at review. PyPI JSON
  metadata confirmed chi-drm1.0.3, pints0.6.1 and lmfit1.3.4; their APIs were not exercised.

## Scientific/regulatory corrections and primary evidence

- [ICH M12 full text](https://www.pmda.go.jp/files/000268574.pdf): TDI5×Cmax,u, distinct MATE/systemic
  efflux cutoffs, fu reliability, inlet/enterocyte concentrations and separate mechanism evaluation.
  Per-minute/per-hour consistency and full-inhibition ceilings were checked algebraically.
- [FDA BE  May 2026](https://www.fda.gov/media/163638/download): design-specific replicate models,
  squared-contrast bias correction and upper chi-square quantile. The CLI now rejects unsupported
  raw replicate/scaled analysis. [PowerTOST](https://cran.r-project.org/web/packages/PowerTOST/vignettes/vignette.html)
  informs planning comparisons; the bundled quantile-grid method remains an approximation.
- [Phoenix8.4 guide](https://onlinehelp.certara.com/phoenix/8.4/responsive_html5_%21MasterPage%21/WinNonlin_Guide.pdf):
  automatic terminal selection differs from the helper's strict extension-improvement rule.
- [Vancomycin consensus](https://www.idsociety.org/practice-guideline/vancomycin/): serious MRSA,
  total AUC24 400–600 mg·h/L with MIC 1 mg/L assumption; not a universal antimicrobial index target.
- E11A, E14/S7B, FIH, M13A/B/C and M15 primary sources and regional dates are listed in
  [regulatory guidance](regulatory-guidance.md). M13B is now EMA Step 5, not draft Step 2b.

## Deliberate boundaries

No script calls a remote clinical/data API; it reads local CSV/CLI values. External URLs are
primary documentation links, not service/authentication endpoints. Phantom endpoints were not
introduced. No patient data, outcome validation, licensed engine run, prospective clinical workflow
or submission review was performed. Product-specific guidance is not enumerated. Sparse-data
identifiability, priors, censoring assumptions, parameter uncertainty and extrapolation remain the
analyst's responsibility; the supplied tools cannot resolve them from convergence alone.
