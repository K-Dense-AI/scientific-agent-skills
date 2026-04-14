# Hodgkin-Huxley Model: Full Parameter Tables

This reference document supplements `SKILL.md` with the complete Hodgkin-Huxley parameter set and its variants.

## Original Hodgkin-Huxley Parameters (Squid Giant Axon)

All parameters from Hodgkin & Huxley (1952) at 6.3 degrees C:

### Membrane Properties

| Parameter | Symbol | Value | Unit |
|---|---|---|---|
| Membrane capacitance | C_m | 1.0 | uF/cm^2 |
| Resting potential | V_rest | -65 | mV |

### Ionic Conductances

| Channel | Max conductance (g) | Reversal potential (E) | Source |
|---|---|---|---|
| Sodium (Na) | 120 mS/cm^2 | +50 mV | Hodgkin & Huxley, 1952 |
| Potassium (K) | 36 mS/cm^2 | -77 mV | Hodgkin & Huxley, 1952 |
| Leak (L) | 0.3 mS/cm^2 | -54.4 mV | Hodgkin & Huxley, 1952 |

### Gating Variable Rate Functions

The rate functions alpha and beta for each gating variable (m, h, n) at membrane potential V (in mV, shifted so resting = -65 mV):

**Sodium activation (m)**:
```
alpha_m(V) = 0.1 * (V + 40) / (1 - exp(-(V + 40) / 10))
beta_m(V) = 4.0 * exp(-(V + 65) / 18)
```

**Sodium inactivation (h)**:
```
alpha_h(V) = 0.07 * exp(-(V + 65) / 20)
beta_h(V) = 1.0 / (1 + exp(-(V + 35) / 10))
```

**Potassium activation (n)**:
```
alpha_n(V) = 0.01 * (V + 55) / (1 - exp(-(V + 55) / 10))
beta_n(V) = 0.125 * exp(-(V + 65) / 80)
```

### Steady-State and Time Constant Summary

At resting potential (V = -65 mV):

| Variable | Steady state | Time constant (ms) | Source |
|---|---|---|---|
| m | 0.053 | 0.15 | Hodgkin & Huxley, 1952 |
| h | 0.596 | 5.57 | Hodgkin & Huxley, 1952 |
| n | 0.318 | 4.66 | Hodgkin & Huxley, 1952 |

## Temperature Correction

The original parameters were measured at 6.3 degrees C. For simulations at physiological temperature (37 degrees C), apply a Q10 correction factor (Hodgkin & Huxley, 1952):

```
rate_corrected = rate_original * Q10^((T - 6.3) / 10)
```

Typical Q10 values:
- Q10 = **3** for rate functions (alpha, beta)

At 37 degrees C, this means rates are approximately 10x faster than original parameters.

## Cortical Neuron HH Variants

For mammalian cortical neurons (not squid axon), common modifications:

### Wang-Buzsaki Fast-Spiking Interneuron Model

Adjusted for cortical interneurons (Wang & Buzsaki, 1996):

| Parameter | Value | Unit |
|---|---|---|
| C_m | 1.0 | uF/cm^2 |
| g_Na | 35 | mS/cm^2 |
| g_K | 9 | mS/cm^2 |
| g_L | 0.1 | mS/cm^2 |
| E_Na | 55 | mV |
| E_K | -90 | mV |
| E_L | -65 | mV |

### Traub-Miles Pyramidal Cell Model

For cortical pyramidal cells (Traub & Miles, 1991):

| Parameter | Value | Unit |
|---|---|---|
| C_m | 1.0 | uF/cm^2 |
| g_Na | 100 | mS/cm^2 |
| g_K | 80 | mS/cm^2 |
| g_L | 0.1 | mS/cm^2 |
| E_Na | 50 | mV |
| E_K | -100 | mV |
| E_L | -67 | mV |

## Integration Methods for HH Models

| Method | Order | Stability | Recommended dt | Notes |
|---|---|---|---|---|
| Forward Euler | 1st | Conditionally stable | 0.01 ms | Simple but requires very small dt |
| Runge-Kutta 4 (RK4) | 4th | Better stability | 0.025--0.05 ms | Standard for HH; good accuracy/speed tradeoff |
| Exponential Euler | 1st (adapted) | Unconditionally stable for linear parts | 0.05 ms | Exploits linear structure of gating variables |
| Implicit methods (Crank-Nicolson) | 2nd | Unconditionally stable | 0.05--0.1 ms | More complex implementation; useful for stiff systems |

> **Recommendation**: Use RK4 with dt = 0.025 ms as the default for HH simulations. Use exponential Euler for large networks where speed matters more than high accuracy on action potential shape (Rotter & Diesmann, 1999).

## References

- Hodgkin, A. L., & Huxley, A. F. (1952). A quantitative description of membrane current and its application to conduction and excitation in nerve. *Journal of Physiology*, 117(4), 500--544.
- Rotter, S., & Diesmann, M. (1999). Exact digital simulation of time-invariant linear systems with applications to neuronal modeling. *Biological Cybernetics*, 81(5--6), 381--402.
- Traub, R. D., & Miles, R. (1991). *Neuronal Networks of the Hippocampus*. Cambridge University Press.
- Wang, X.-J., & Buzsaki, G. (1996). Gamma oscillation by synaptic inhibition in a hippocampal interneuronal network model. *Journal of Neuroscience*, 16(20), 6402--6413.
