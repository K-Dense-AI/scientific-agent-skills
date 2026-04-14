# Network Regimes and Parameter Sweeps

This reference document supplements `SKILL.md` with extended detail on the Brunel (2000) network regimes and practical parameter sweep guidance.

## Brunel (2000) Network Regimes

The behavior of a balanced random network of LIF neurons is determined by two key parameters (Brunel, 2000):

1. **g**: Relative inhibitory synaptic strength (g = |J_I| / J_E)
2. **nu_ext / nu_thr**: Ratio of external input rate to threshold rate

### Regime Map

| Regime | Abbreviation | g range | nu_ext/nu_thr | Firing pattern | Synchrony | Source |
|---|---|---|---|---|---|---|
| Synchronous Regular | SR | < 4 | > 1 | Regular (CV << 1) | High | Brunel, 2000 |
| Synchronous Irregular | SI | 4--8 | < 1 | Irregular (CV ~ 1) | High (oscillatory) | Brunel, 2000 |
| Asynchronous Regular | AR | < 4 | close to 1 | Regular (CV << 1) | Low | Brunel, 2000 |
| **Asynchronous Irregular** | **AI** | **4--8** | **> 1** | **Irregular (CV ~ 1)** | **Low** | **Brunel, 2000** |

The **AI regime** is the biologically relevant target for most cortical network models.

### Practical Parameter Recommendations for AI Regime

For a network of N_E = 8000 excitatory and N_I = 2000 inhibitory LIF neurons (Brunel, 2000):

| Parameter | Value | Notes |
|---|---|---|
| Connection probability (epsilon) | 0.1 | Each neuron receives C_E = 800 excitatory and C_I = 200 inhibitory inputs |
| Excitatory weight (J_E) | 0.1 mV (PSP amplitude) | Resulting in small unitary PSPs |
| Relative inhibition (g) | 5--6 | Ensures AI regime |
| External rate (nu_ext) | 2 * nu_thr | Drive just above threshold for sparse firing |
| Expected excitatory firing rate | 1--5 Hz | Depends on exact g and nu_ext |
| Expected inhibitory firing rate | 5--15 Hz | Higher than excitatory due to lower threshold or higher drive |

### Transition Boundaries

Key transitions as g increases (at fixed nu_ext > nu_thr):

1. **g < 4**: Network is excitation-dominated; synchronous bursts
2. **g ~ 4**: Transition to inhibition-dominated; onset of irregularity
3. **g = 4--8**: AI regime; irregular firing, low synchrony
4. **g > 8**: Firing rates drop substantially; may become quiescent

Key transitions as nu_ext changes (at fixed g = 5):

1. **nu_ext < nu_thr**: Subthreshold drive; network relies on recurrent excitation; SI regime with oscillations
2. **nu_ext ~ nu_thr**: Transition region
3. **nu_ext > nu_thr**: Suprathreshold drive; AI regime

## Parameter Sweep Protocol

When building a new network model, follow this systematic parameter sweep to find the AI regime:

### Step 1: Fix Network Architecture
- N_E = 4000, N_I = 1000 (or scale up by factor of 2)
- epsilon = 0.1 (connection probability)
- J_E = 0.1 mV (will be adjusted)

### Step 2: Sweep g and nu_ext
```
g_values = [3, 4, 5, 6, 7, 8]
nu_ext_values = [0.8, 1.0, 1.2, 1.5, 2.0, 3.0] * nu_thr
```

For each (g, nu_ext) pair:
1. Simulate for 1500 ms (discard first 500 ms)
2. Compute: mean firing rate, CV of ISI, synchrony index (chi)

### Step 3: Identify AI Regime
Select parameters where:
- Mean excitatory rate: 1--10 Hz
- CV of ISI: 0.8--1.2
- Synchrony index chi < 0.2

### Step 4: Fine-Tune
Once in the approximate AI regime, fine-tune with smaller parameter steps if needed.

## Weight Scaling Derivation

For a balanced network (Brunel, 2000; van Vreeswijk & Sompolinsky, 1998):

The mean input to a neuron:
```
mu = C_E * J_E * nu_E - C_I * J_I * nu_I + J_ext * C_ext * nu_ext
```

For balance (mu ~ 0 in the fluctuation-driven regime):
```
C_E * J_E * nu_E ~ C_I * J_I * nu_I
```

Since C_I/C_E = 1/4 (from the 80/20 split with equal connection probability):
```
J_I = 4 * J_E * (nu_E / nu_I)
```

For equal firing rates (nu_E ~ nu_I): J_I = 4 * J_E, hence g = 4 is the boundary.

The variance of the input (which drives the irregular firing) scales as:
```
sigma^2 = C_E * J_E^2 * nu_E + C_I * J_I^2 * nu_I
```

For the CV to be ~1, sigma must be of order (V_thresh - V_rest), which constrains J_E relative to C_E (i.e., J_E ~ 1/sqrt(C_E)).

## Multi-Population Extensions

For networks with more than one excitatory and one inhibitory population (e.g., Potjans & Diesmann, 2014 cortical column model):

### Potjans-Diesmann Cortical Column

| Layer | Population | N | Source |
|---|---|---|---|
| L2/3 | E | 20,683 | Potjans & Diesmann, 2014 |
| L2/3 | I | 5,834 | Potjans & Diesmann, 2014 |
| L4 | E | 21,915 | Potjans & Diesmann, 2014 |
| L4 | I | 5,479 | Potjans & Diesmann, 2014 |
| L5 | E | 4,850 | Potjans & Diesmann, 2014 |
| L5 | I | 1,065 | Potjans & Diesmann, 2014 |
| L6 | E | 14,395 | Potjans & Diesmann, 2014 |
| L6 | I | 2,948 | Potjans & Diesmann, 2014 |

Connection probabilities between populations form a 8x8 matrix. See Potjans & Diesmann (2014), Table 5 for the full connectivity matrix.

## References

- Brunel, N. (2000). Dynamics of sparsely connected networks of excitatory and inhibitory spiking neurons. *Journal of Computational Neuroscience*, 8(3), 183--208.
- Potjans, T. C., & Diesmann, M. (2014). The cell-type specific cortical microcircuit: Relating structure and activity in a full-scale spiking network model. *Cerebral Cortex*, 24(3), 785--806.
- van Vreeswijk, C., & Sompolinsky, H. (1998). Chaotic balanced state in a model of cortical circuits. *Neural Computation*, 10(6), 1321--1371.
