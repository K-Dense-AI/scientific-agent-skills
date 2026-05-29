# booleanNet Syntax and Rules Translation

This document defines how to translate biological network topology into string-based logic for the `boolean2` engine. You MUST format rules exactly as specified below.

## Rule Definition Syntax

All rules are defined as a single multi-line string.

The left side of the equation MUST be the node name followed by an asterisk (`*`), representing the state at the next time step `(t+1)`.

The right side uses standard Python logical operators: `and`, `or`, `not`.

Node names MUST be alphanumeric and cannot contain spaces.

### Biological Translations

| Biological Concept | Description | boolean2 Syntax Translation |
| ------------------ | ----------- | --------------------------- |
| Activation | Node A activates Node B | `B* = A` |
| Inhibition | Node A inhibits Node B | `B* = not A` |
| Independent Co-regulation | A OR B activates C | `C* = A or B` |
| Dependent Co-regulation | A AND B must be present to activate C | `C* = A and B` |
| Mixed Regulation | A activates C, but D inhibits C | `C* = A and not D`
| Constitutive Activation | A is always ON | `A* = True` (or `A* = 1`) |

## Model Initialization Modes

When calling `boolean2.Model(text=rules, mode=...)`, you MUST choose the appropriate mode:

`mode='async'` (Default/Recommended for Biology): Nodes update asynchronously (random order). This prevents artificial, perfectly-timed oscillations that do not occur in real biological systems. Use this for time-course simulations.

`mode='sync'` (Synchronous): All nodes update simultaneously. Use this ONLY when specifically requested, or when doing exhaustive attractor analysis on small networks.

Example valid rule string:

```
rules = """
EGF_receptor* = EGF
Ras* = EGF_receptor and not GAP
MAPK* = Ras
"""
```
