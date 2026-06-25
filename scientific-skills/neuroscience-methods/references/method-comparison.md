# Method Comparison: Detailed Parameters and Software for Neural Population Analysis

This reference document supplements `SKILL.md` with extended method comparisons, parameter tables, and software recommendations.

## Full Method Comparison Table

| Method | Type | Temporal? | Task-driven? | Single-trial? | Key assumption | Best for | Source |
|---|---|---|---|---|---|---|---|
| PCA | Linear, static | No | No | Optional | Orthogonal components | Quick exploration; condition-averaged trajectories | Cunningham & Yu, 2014 |
| Factor Analysis | Linear, static | No | No | Yes | Shared + private variance | When noise structure matters | Cunningham & Yu, 2014 |
| GPFA | Linear, dynamic | Yes | No | Yes | Gaussian process smoothness | Single-trial latent trajectories | Yu et al., 2009 |
| dPCA | Linear, task-driven | Implicit | Yes | No (trial-avg) | Factorial design | Demixing task variables | Kobak et al., 2016 |
| jPCA | Linear, dynamic | Yes | No | No (trial-avg) | Rotational dynamics | Motor cortex dynamics | Churchland et al., 2012 |
| t-SNE | Nonlinear | No | No | Optional | Local distance preservation | Visualization ONLY | van der Maaten & Hinton, 2008 |
| UMAP | Nonlinear | No | No | Optional | Topological structure | Visualization ONLY | McInnes et al., 2018 |
| LFADS | Nonlinear, dynamic | Yes | No | Yes | RNN dynamics | Large datasets; complex dynamics | Pandarinath et al., 2018 |

## PCA Parameters

### Soft Normalization Details

The soft normalization procedure (Churchland et al., 2012):

```
For each neuron i:
 1. Compute mean firing rate across all conditions and time: mean_i
 2. Compute the range (max - min) of the condition-averaged PSTH: range_i
 3. Normalized rate = (rate_i - mean_i) / (range_i + alpha)
```

where `alpha = 5 spikes/s` is the soft normalization constant. This value was chosen to prevent low-firing neurons (range < 5 sp/s) from dominating while still allowing moderate-to-high firing neurons to contribute proportionally (Churchland et al., 2012).

### Alternative: Square-Root Transform

```
transformed = sqrt(spike_count / bin_width + 0.5)
```

The addition of 0.5 stabilizes the transform for zero counts. This is a variance-stabilizing transform for Poisson-distributed spike counts (Churchland et al., 2012).

### Parallel Analysis for Dimensionality (Humphries, 2021)

1. Compute eigenvalues from actual data PCA
2. Generate null data: for each neuron, shuffle the data (or use random Gaussian data matched in size)
3. Compute eigenvalues from null data PCA
4. Repeat null step 100--1000 times
5. For each PC, compute the 95th percentile of null eigenvalues
6. Signal dimensions = number of real eigenvalues exceeding the 95th percentile null

## GPFA Implementation Details

### Expectation-Maximization (EM) Algorithm

GPFA uses EM to learn model parameters (Yu et al., 2009):

- **E-step**: Infer latent trajectories given current parameters
- **M-step**: Update loading matrix C, private noise variances d, and GP hyperparameters
- **Convergence**: Monitor log-likelihood; typically converges within 50--200 iterations
- **Initialization**: Initialize with Factor Analysis solution

### Cross-Validation for Dimensionality

1. Hold out one neuron at a time (leave-one-neuron-out)
2. Fit GPFA on remaining neurons
3. Predict held-out neuron's activity from the inferred latent trajectories
4. Compute log-likelihood of held-out data
5. Average across held-out neurons
6. Choose dimensionality maximizing average held-out log-likelihood

### Bin Size Considerations

| Bin size | Temporal resolution | SNR | Typical application | Source |
|---|---|---|---|---|
| 10 ms | High | Low | Fast dynamics (e.g., saccades) | Expert consensus |
| 20 ms | Good | Medium | Motor cortex reaching | Yu et al., 2009 |
| 50 ms | Moderate | High | Slower cognitive tasks | Yu et al., 2009 |
| 100 ms | Low | Very high | Very slow processes; prefrontal dynamics | Expert consensus |

## dPCA Implementation Details

### Marginalization Procedure (Kobak et al., 2016)

For a factorial design with stimulus (S), decision (D), and time (T):

1. **Full data tensor**: X(neuron, stimulus, decision, time, trial)
2. **Trial-average**: X_avg(neuron, stimulus, decision, time)
3. **Marginalizations**:
 - Time: average over stimulus and decision -> X_t(neuron, time)
 - Stimulus: average over decision -> X_s(neuron, stimulus, time) minus X_t
 - Decision: average over stimulus -> X_d(neuron, decision, time) minus X_t
 - Interaction: X_avg - X_t - X_s - X_d

4. **For each marginalization**: Find encoder/decoder pairs that maximize marginalized variance

### Regularization Selection

```
Lambda grid: logarithmically spaced from 1e-7 to 1e0
Cross-validation: hold out 20% of trials
Metric: reconstruction error on held-out trials
Select lambda minimizing held-out error
```

Typical optimal lambda values fall in the range 1e-4 to 1e-2 (Kobak et al., 2016).

## jPCA Details (Churchland et al., 2012)

### Procedure

1. Perform PCA to reduce to 6 dimensions (captures >90% of condition-averaged variance in motor cortex data)
2. Compute the time derivative of the PC trajectories: dX/dt
3. Fit a linear dynamical system: dX/dt = M * X
4. Decompose M into symmetric (M_symm) and skew-symmetric (M_skew) parts
5. jPCA finds the skew-symmetric component, which captures rotational dynamics
6. Project data onto the top jPCA plane

### Interpretation

- Strong rotational fit (R^2 > 0.5 for M_skew) suggests rotational dynamics in the population
- Rotational dynamics have been found in motor cortex (Churchland et al., 2012) and other areas
- Absence of rotational dynamics is also informative (suggests non-oscillatory population dynamics)

## Software Recommendations

| Software | Language | Methods | Source |
|---|---|---|---|
| **DataHigh** | MATLAB | GPFA, PCA, FA | Yu et al., 2009; Cowley et al., 2013 |
| **dPCA toolbox** | Python, MATLAB | dPCA | Kobak et al., 2016 (github.com/machenslab/dPCA) |
| **elephant** | Python | PCA, FA, GPFA | INCF (elephant.readthedocs.io) |
| **scikit-learn** | Python | PCA, FA, t-SNE | Pedregosa et al., 2011 |
| **LFADS** | Python (TF) | LFADS | Pandarinath et al., 2018 |
| **pyaldata** | Python | Population analysis utilities | Lawlor et al., 2018 |
| **UMAP** | Python | UMAP | McInnes et al., 2018 (umap-learn) |

### Key Software Notes

- For GPFA: the original MATLAB code from Yu et al. (2009) remains the reference implementation. The elephant Python library provides a maintained Python version.
- For dPCA: the official toolbox (github.com/machenslab/dPCA) provides both Python and MATLAB implementations with cross-validation and shuffle testing built in.
- For jPCA: the original MATLAB code from Churchland et al. (2012) is available from the Shenoy lab website.

## References

- Churchland, M. M., et al. (2012). Neural population dynamics during reaching. *Nature*, 487(7405), 51--56.
- Cowley, B. R., et al. (2013). DataHigh: Graphical user interface for visualizing and interacting with high-dimensional neural activity. *Journal of Neural Engineering*, 10(6), 066012.
- Cunningham, J. P., & Yu, B. M. (2014). Dimensionality reduction for large-scale neural recordings. *Nature Neuroscience*, 17(11), 1500--1509.
- Humphries, M. D. (2021). Strong and weak principles of neural dimension reduction. *Neuron*, 109(8), 1230--1234.
- Kobak, D., et al. (2016). Demixed principal component analysis of neural population data. *eLife*, 5, e10989.
- McInnes, L., Healy, J., & Melville, J. (2018). UMAP: Uniform manifold approximation and projection for dimension reduction. *arXiv:1802.03426*.
- Pandarinath, C., et al. (2018). Inferring single-trial neural population dynamics using sequential auto-encoders. *Nature Methods*, 15(10), 805--815.
- van der Maaten, L., & Hinton, G. (2008). Visualizing data using t-SNE. *Journal of Machine Learning Research*, 9, 2579--2605.
- Yu, B. M., et al. (2009). Gaussian-process factor analysis for low-dimensional single-trial analysis of neural population activity. *Journal of Neurophysiology*, 102(1), 614--635.
