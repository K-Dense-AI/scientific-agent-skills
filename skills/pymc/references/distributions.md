# PyMC Distributions Reference

Targets PyMC 6.3.2, reviewed 2026-10-01. This reference provides a selected catalog of probability distributions available in PyMC, organized by category. Use this to select appropriate distributions for priors and likelihoods when building Bayesian models.

## Continuous Distributions

Continuous distributions define probability densities over real-valued domains.

### Common Continuous Distributions

**`pm.Normal(name, mu, sigma)`**
- Normal (Gaussian) distribution
- Parameters: `mu` (mean), `sigma` (standard deviation)
- Support: (-∞, ∞)
- Common uses: Default prior for unbounded parameters, likelihood for continuous data with additive noise

**`pm.HalfNormal(name, sigma)`**
- Half-normal distribution (positive half of normal)
- Parameters: `sigma` (underlying Normal scale; not the half-normal standard deviation)
- Support: [0, ∞)
- Common uses: Prior for scale/standard deviation parameters

**`pm.Uniform(name, lower, upper)`**
- Uniform distribution
- Parameters: `lower`, `upper` (bounds)
- Support: [lower, upper]
- Common uses: Weakly informative prior when parameter must be bounded

**`pm.Beta(name, alpha, beta)`**
- Beta distribution
- Parameters: `alpha`, `beta` (shape parameters)
- Support: [0, 1]
- Common uses: Prior for probabilities and proportions

**`pm.Gamma(name, alpha, beta)`**
- Gamma distribution
- Parameters: `alpha` (shape), `beta` (rate)
- Support: (0, ∞)
- Common uses: Prior for positive parameters, rate parameters

**`pm.Exponential(name, lam)`**
- Exponential distribution
- Parameters: `lam` (rate parameter)
- Support: [0, ∞)
- Common uses: Prior for scale parameters, waiting times

**`pm.LogNormal(name, mu, sigma)`**
- Log-normal distribution
- Parameters: `mu`, `sigma` (parameters of underlying normal)
- Support: (0, ∞)
- Common uses: Prior for positive parameters with multiplicative effects

**`pm.StudentT(name, nu=nu, mu=mu, sigma=sigma)`**
- Student's t-distribution
- Parameters: `nu` (degrees of freedom), `mu` (location), `sigma` (scale)
- Support: (-∞, ∞)
- Common uses: Robust alternative to normal for outlier-resistant models

**`pm.Cauchy(name, alpha, beta)`**
- Cauchy distribution
- Parameters: `alpha` (location), `beta` (scale)
- Support: (-∞, ∞)
- Common uses: Heavy-tailed alternative to normal

**`pm.HalfStudentT(name, nu, sigma)`**
- Positive half-Student-t distribution
- Common uses: Heavy-tailed prior for scale parameters

### Specialized Continuous Distributions

**`pm.Laplace(name, mu, b)`** - Laplace (double exponential) distribution

**`pm.AsymmetricLaplace(name, kappa, mu, b)`** - Asymmetric Laplace distribution

**`pm.InverseGamma(name, alpha, beta)`** - Inverse gamma distribution

**`pm.Weibull(name, alpha, beta)`** - Weibull distribution for reliability analysis

**`pm.Logistic(name, mu, s)`** - Logistic distribution

**`pm.LogitNormal(name, mu, sigma)`** - Logit-normal distribution for (0,1) support

**`pm.Pareto(name, alpha, m)`** - Pareto distribution for power-law phenomena

**`pm.ChiSquared(name, nu)`** - Chi-squared distribution

**`pm.ExGaussian(name, mu=mu, sigma=sigma, nu=nu)`** - Exponentially modified Gaussian

**`pm.VonMises(name, mu, kappa)`** - Von Mises (circular normal) distribution

**`pm.SkewNormal(name, mu=mu, sigma=sigma, alpha=alpha)`** - Skew-normal distribution

**`pm.Triangular(name, lower=lower, c=c, upper=upper)`** - Triangular distribution

**`pm.Gumbel(name, mu, beta)`** - Gumbel distribution for extreme values

**`pm.PolyaGamma(name, h, z)`** - Polya-gamma distribution for data augmentation patterns

**`pm.Rice(name, nu, sigma)`** - Rice (Rician) distribution

**`pm.Moyal(name, mu, sigma)`** - Moyal distribution

**`pm.Kumaraswamy(name, a, b)`** - Kumaraswamy distribution (Beta alternative)

**`pm.Wald(name, mu, lam)`** - Wald / inverse Gaussian distribution

**`pm.Interpolated(name, x_points, pdf_points)`** - Custom distribution from interpolation

## Discrete Distributions

Discrete distributions define probabilities over integer-valued domains.

### Common Discrete Distributions

**`pm.Bernoulli(name, p)`**
- Bernoulli distribution (binary outcome)
- Parameters: `p` (success probability)
- Support: {0, 1}
- Common uses: Binary classification, coin flips

**`pm.Binomial(name, n, p)`**
- Binomial distribution
- Parameters: `n` (number of trials), `p` (success probability)
- Support: {0, 1, ..., n}
- Common uses: Number of successes in fixed trials

**`pm.Poisson(name, mu)`**
- Poisson distribution
- Parameters: `mu` (rate parameter)
- Support: {0, 1, 2, ...}
- Common uses: Count data, rates, occurrences

**`pm.Categorical(name, p)`**
- Categorical distribution
- Parameters: `p` (probability vector)
- Support: {0, 1, ..., K-1}
- Common uses: Multi-class classification

**`pm.DiscreteUniform(name, lower, upper)`**
- Discrete uniform distribution
- Parameters: `lower`, `upper` (bounds)
- Support: {lower, ..., upper}
- Common uses: Uniform prior over finite integers

**`pm.NegativeBinomial(name, mu, alpha)`**
- Negative binomial distribution
- Parameters: `mu` (mean), `alpha` (dispersion)
- Support: {0, 1, 2, ...}
- Common uses: Overdispersed count data

**`pm.Geometric(name, p)`**
- Geometric distribution
- Parameters: `p` (success probability)
- Support: {1, 2, 3, ...}
- Common uses: Trial count through the first success (includes that success)

### Specialized Discrete Distributions

**`pm.BetaBinomial(name, alpha, beta, n)`** - Beta-binomial (overdispersed binomial)

**`pm.HyperGeometric(name, N, k, n)`** - Hypergeometric distribution

**`pm.DiscreteWeibull(name, q, beta)`** - Discrete Weibull distribution

**`pm.OrderedLogistic(name, eta, cutpoints)`** - Ordered logistic for ordinal data

**`pm.OrderedProbit(name, eta, cutpoints)`** - Ordered probit for ordinal data

## Multivariate Distributions

Multivariate distributions define joint probability distributions over vector-valued random variables.

### Common Multivariate Distributions

**`pm.MvNormal(name, mu, cov)`**
- Multivariate normal distribution
- Parameters: `mu` (mean vector), `cov` (covariance matrix)
- Common uses: Correlated continuous variables, Gaussian processes

**`pm.Dirichlet(name, a)`**
- Dirichlet distribution
- Parameters: `a` (concentration parameters)
- Support: Simplex (sums to 1)
- Common uses: Prior for probability vectors, topic modeling

**`pm.Multinomial(name, n, p)`**
- Multinomial distribution
- Parameters: `n` (number of trials), `p` (probability vector)
- Common uses: Count data across multiple categories

**`pm.DirichletMultinomial(name, n, a)`**
- Dirichlet-multinomial distribution
- Common uses: Overdispersed categorical counts

**`pm.MvStudentT(name, nu=nu, mu=mu, scale=scale)`**
- Multivariate Student's t-distribution
- Parameters: `nu` (degrees of freedom), `mu` (location), `scale` (scale matrix; covariance is nu/(nu-2) times this matrix for nu > 2)
- Common uses: Robust multivariate modeling

### Specialized Multivariate Distributions

**`pm.LKJCorr(name, n, eta)`** - LKJ correlation matrix prior (for correlation matrices)

**`pm.LKJCholeskyCov(name, n=n, eta=eta, sd_dist=sd_dist)`** - LKJ prior with Cholesky decomposition

**`pm.OrderedMultinomial(name, eta, cutpoints, n)`** - Ordered multinomial outcomes

**`pm.StickBreakingWeights(name, alpha, K)`** - Stick-breaking weights for mixture models

**`pm.ZeroSumNormal(name, sigma)`** - Normal prior constrained to sum to zero

**`pm.Wishart(name, nu, V)`** - Wishart distribution (for covariance matrices; prefer LKJ-based priors for most covariance models)

There is no public `pm.InverseWishart` in PyMC 6.3.2. Prefer an explicit
scientifically justified covariance model, usually LKJ with marginal scales.

**`pm.WishartBartlett(name, S, nu)`** - Wishart with Bartlett decomposition

**`pm.MatrixNormal(name, mu=mu, rowcov=rowcov, colcov=colcov)`** - Matrix normal distribution

**`pm.KroneckerNormal(name, mu=mu, covs=covs, sigma=sigma)`** - Kronecker-structured normal

**`pm.CAR(name, mu, W, alpha, tau)`** - Conditional autoregressive (spatial)

**`pm.ICAR(name, W, sigma)`** - Intrinsic conditional autoregressive (spatial)

## Mixture Distributions

Mixture distributions combine multiple component distributions.

**`pm.Mixture(name, w, comp_dists)`**
- General mixture distribution
- Parameters: `w` (weights), `comp_dists` (component distributions)
- Common uses: Clustering, multi-modal data

**`pm.NormalMixture(name, w, mu, sigma)`**
- Mixture of normal distributions
- Common uses: Mixture of Gaussians clustering

### Zero-Inflated and Hurdle Models

**`pm.ZeroInflatedPoisson(name, psi, mu)`** - Excess zeros in count data

**`pm.ZeroInflatedBinomial(name, psi, n, p)`** - Zero-inflated binomial

**`pm.ZeroInflatedNegativeBinomial(name, psi, mu, alpha)`** - Zero-inflated negative binomial

**`pm.HurdlePoisson(name, psi, mu)`** - Hurdle Poisson (two-part model)

**`pm.HurdleNegativeBinomial(name, psi, mu, alpha)`** - Hurdle negative binomial for overdispersed counts with structural zeros

**`pm.HurdleGamma(name, psi, alpha, beta)`** - Hurdle gamma

**`pm.HurdleLogNormal(name, psi, mu, sigma)`** - Hurdle log-normal

## Time Series Distributions

Distributions designed for temporal data and sequential modeling.

**`pm.AR(name, rho=rho, sigma=sigma, init_dist=init_dist)`**
- Autoregressive process
- Parameters: `rho` (AR coefficients), `sigma` (innovation std), `init_dist` (initial distribution)
- Common uses: Time series modeling, sequential data

**`pm.GaussianRandomWalk(name, mu=mu, sigma=sigma, init_dist=init_dist)`**
- Gaussian random walk
- Parameters: `mu` (drift), `sigma` (step size), `init_dist` (initial value)
- Common uses: Cumulative processes, random walk priors

**`pm.MvGaussianRandomWalk(name, mu=mu, cov=cov, init_dist=init_dist)`**
- Multivariate Gaussian random walk

**`pm.MvStudentTRandomWalk(name, nu=nu, mu=mu, scale=scale, init_dist=init_dist)`**
- Heavy-tailed multivariate random walk

**`pm.GARCH11(name, omega=omega, alpha_1=alpha_1, beta_1=beta_1, initial_vol=initial_vol)`**
- GARCH(1,1) volatility model
- Common uses: Financial time series, volatility modeling

**`pm.EulerMaruyama(name, dt, sde_fn, sde_pars, init_dist=init_dist)`**
- Stochastic differential equation via Euler-Maruyama discretization
- Common uses: Continuous-time processes

## Special Distributions

**`pm.Deterministic(name, var)`**
- Deterministic transformation (not a random variable)
- Use for computed quantities derived from other variables

**`pm.Potential(name, logp)`**
- Add arbitrary log-probability contribution; ignored by prior/posterior forward
  sampling, so a Potential alone does not define a generative likelihood
- Use for custom likelihood components or constraints

**`pm.Flat(name)`**
- Improper flat prior (constant density); cannot draw prior predictive samples
- Use sparingly; can cause sampling issues

**`pm.HalfFlat(name)`**
- Improper flat prior on positive reals; cannot draw prior predictive samples
- Use sparingly; can cause sampling issues

## Distribution Modifiers

**`pm.Truncated(name, dist, lower, upper)`**
- Truncate a supported univariate `.dist()` distribution to specified bounds;
  support and inverse-CDF/rejection-sampling limitations depend on the base distribution

**`pm.Censored(name, dist, lower, upper)`**
- Handle censored observations (observed bounds, not exact values)

**`pm.CustomDist(name, ..., logp, random)`**
- Define custom distributions with user-specified log-probability and random sampling functions

**`pm.Simulator(name, fn, params, ...)`**
- Custom distributions via simulation (for likelihood-free inference)

## Usage Tips

### Choosing Priors

1. **Scale parameters** (σ, τ): Use `HalfNormal`, `HalfCauchy`, `Exponential`, or `Gamma`
2. **Probabilities**: Use `Beta` or `Uniform(0, 1)`
3. **Unbounded parameters**: Use `Normal` or `StudentT` (for robustness)
4. **Positive parameters**: Use `LogNormal`, `Gamma`, or `Exponential`
5. **Correlation/covariance matrices**: Prefer `LKJCholeskyCov` for covariance models; use `LKJCorr` when only correlations are needed
6. **Count data**: Use `Poisson` or `NegativeBinomial` (for overdispersion)

### Shape Broadcasting

PyMC distributions support NumPy-style broadcasting. Use the `shape` parameter to create vectors or arrays of random variables:

```python
# Vector of 5 independent normals
beta = pm.Normal('beta', mu=0, sigma=1, shape=5)

# 3x4 matrix of independent gammas
tau = pm.Gamma('tau', alpha=2, beta=1, shape=(3, 4))
```

### Using dims for Named Dimensions

Instead of shape, use `dims` for more readable models:

```python
with pm.Model(coords={'predictors': ['age', 'income', 'education']}) as model:
    beta = pm.Normal('beta', mu=0, sigma=1, dims='predictors')
```

## Parameterization and scientific caveats

- Entries list important parameters, not exhaustive positional signatures. Prefer
  keywords: several distributions have keyword-only parameters. Catalog names and
  constructor signatures were checked against released source; specialized
  distributions were not all fit or sampled in this review.
- NegativeBinomial has variance `mu + mu**2 / alpha`. InverseGamma `beta` is a
  scale, while Gamma `beta` is a rate. PolyaGamma needs the optional `polyagamma`
  package for relevant numerical operations.
- In zero-inflated models `psi` is the weight on the ordinary count component,
  not the probability of a structural zero. In hurdle models it is the weight
  on the positive component. HurdleGamma/HurdleLogNormal are intended as observed
  likelihoods or forward-sampled RVs; ordinary MCMC does not correctly sample
  their mixed point-mass/continuous latent support.
- `LKJCholeskyCov(..., compute_corr=True)` returns `(chol, corr, stds)` by default.
  `LKJCorr` ordinarily returns packed upper-triangle correlations, not a full
  correlation matrix. `eta=1` is uniform over correlation matrices, not uniform
  independent marginal correlations for arbitrary dimension.
- `pm.Censored` is not `pm.Truncated`: censoring puts probability mass at recorded
  limits; truncation conditions on being included inside limits. Selection and
  measurement processes decide the correct likelihood.
- A density definition without a `random`/generative implementation can support
  fitting but not meaningful forward simulation. Check `CustomDist` event/batch
  shapes, log-density normalization and gradient behavior independently.
- Ordinary `dims` names annotate arrays; they do not align symbolic arithmetic.
  Multivariate event dimensions and batch dimensions have different meanings.

Sources: [distribution catalog](https://www.pymc.io/projects/docs/en/stable/api/distributions.html),
[released distribution source](https://github.com/pymc-devs/pymc/tree/v6.3.2/pymc/distributions),
[forward sampling source](https://www.pymc.io/projects/docs/en/stable/_modules/pymc/sampling/forward.html).
