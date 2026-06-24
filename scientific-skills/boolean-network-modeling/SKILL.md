# Boolean Network Modeling

## Overview
Simulate and analyze dynamic biological regulatory networks using Boolean logic (via the `boolean2` Python engine). Predict system-level behaviors, identify steady-state attractors, and simulate genetic mutations (knockouts/over-expression).

## When to Use This Skill
- When a user provides boolean biological regulatory rules.
- To predict the outcome of a genetic perturbation or knockout.
- To identify attractors or steady states in a signaling pathway.

## Instructions for the AI
When using this skill, you MUST consult the documentation in the `references/` directory before writing any code:
1. **Defining Rules:** Read `references/01_booleannet_syntax.md` to understand how to correctly format biological activation and inhibition into `boolean2` string logic.
2. **Finding Steady States:** Read `references/02_attractor_analysis.md` for the boilerplate code to iterate through state spaces and find unique attractors.
3. **Simulating Mutations/Time:** Read `references/03_perturbation_knockouts.md` to see how to force a node to 0 (knockout) and plot the trajectory using matplotlib. 

## Dependencies
- `boolean2`
- `matplotlib`
- `pandas`