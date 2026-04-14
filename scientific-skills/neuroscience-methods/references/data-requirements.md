# Data Requirements for Neural Population Analysis Methods

This reference document supplements `SKILL.md` with detailed minimum data requirements for each population analysis method.

## Neuron Count Requirements

| Method | Minimum Neurons | Recommended Neurons | Rationale | Source |
|---|---|---|---|---|
| PCA (condition-avg) | 10--20 | 50+ | Fewer PCs than neurons; noise dominates with very few | Cunningham & Yu, 2014 |
| PCA (single-trial) | 30+ | 100+ | Single-trial noise requires more neurons for stable estimates | Cunningham & Yu, 2014 |
| Factor Analysis | 20+ | 50+ | Must estimate shared vs. private variance | Cunningham & Yu, 2014 |
| GPFA | 50+ | 100+ | Single-trial trajectory extraction requires overdetermined system | Yu et al., 2009 |
| dPCA | 20+ | 50+ | Must have enough neurons to capture variance in each marginalization | Kobak et al., 2016 |
| jPCA | 30+ | 50+ | Needs stable 6D PCA subspace first | Churchland et al., 2012 |
| t-SNE/UMAP | Any | N/A | Visualization only; fewer neurons = less meaningful | Expert consensus |

## Trial Count Requirements

| Method | Minimum Trials/Condition | Recommended Trials/Condition | Rationale | Source |
|---|---|---|---|---|
| PCA (condition-avg) | 20+ | 50+ | Trial averaging requires sufficient trials per condition to suppress noise | Cunningham & Yu, 2014 |
| PCA (single-trial) | 50+ | 100+ | Covariance estimation on single trials requires large sample | Cunningham & Yu, 2014 |
| GPFA | 50+ | 100+ | EM convergence and stable latent trajectory extraction | Yu et al., 2009 |
| dPCA | 20+ | 40+ | Cross-validation of regularization requires held-out trials | Kobak et al., 2016 |
| jPCA | 30+ | 50+ | Stable condition-averaged trajectories | Churchland et al., 2012 |
| Population decoding | 20+ | 50+ | Cross-validated classification requires sufficient trials per fold | Cunningham & Yu, 2014 |

## Recording Duration Guidelines

| Analysis Goal | Minimum Duration | Rationale | Source |
|---|---|---|---|
| Peri-event trajectories | Trial duration + 500 ms pre/post | Capture dynamics around events | Expert consensus |
| Slow dynamics (e.g., working memory) | Full trial including delay period | Must capture sustained activity | Expert consensus |
| Rotational dynamics (jPCA) | 200+ ms of movement-related activity | Rotations typically occur on 100--300 ms timescale | Churchland et al., 2012 |
| GPFA latent dynamics | 500+ ms per trial | GP timescale learning needs sufficient temporal extent | Yu et al., 2009 |

## Simultaneous vs. Sequential Recording

| Recording Type | Compatible Methods | Incompatible Methods | Notes |
|---|---|---|---|
| Simultaneous (multi-electrode array) | All methods | None | Gold standard; captures noise correlations |
| Sequential (single electrode, pseudopopulation) | PCA (condition-avg), dPCA | GPFA, noise correlation analysis | Cannot capture trial-by-trial co-variability; single-trial methods invalid |

> **Critical**: GPFA and any method requiring single-trial co-variability estimates MUST use simultaneously recorded neurons. Pseudopopulations (neurons recorded on different sessions stitched together) can be used for condition-averaged analyses like PCA or dPCA, but not for single-trial latent trajectory extraction (Cunningham & Yu, 2014).

## Practical Checklist Before Analysis

- [ ] Confirm recording type (simultaneous vs. sequential)
- [ ] Count total neurons passing quality criteria
- [ ] Count trials per condition (verify balance across conditions for dPCA)
- [ ] Check temporal extent of data relative to analysis goals
- [ ] Verify that neuron/trial counts meet minimum thresholds for chosen method
- [ ] If below minimums, consider simpler methods (e.g., PCA instead of GPFA) or pool across sessions (with caveats)

## References

- Churchland, M. M., et al. (2012). Neural population dynamics during reaching. *Nature*, 487(7405), 51--56.
- Cunningham, J. P., & Yu, B. M. (2014). Dimensionality reduction for large-scale neural recordings. *Nature Neuroscience*, 17(11), 1500--1509.
- Kobak, D., et al. (2016). Demixed principal component analysis of neural population data. *eLife*, 5, e10989.
- Yu, B. M., et al. (2009). Gaussian-process factor analysis for low-dimensional single-trial analysis of neural population activity. *Journal of Neurophysiology*, 102(1), 614--635.
