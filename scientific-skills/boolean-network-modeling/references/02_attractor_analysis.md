# Steady State and Attractor Analysis

Use this guide when the user asks to find "steady states", "attractors", or "stable states" of a boolean network.

## CRITICAL CONSTRAINT: Network Size

Before running state space analysis, count the number of nodes in the network ($N$).

- If $N \le 20$: Perform EXHAUSTIVE state space search.

- If $N > 20$: DO NOT perform exhaustive search ($2^n$ is too large and will crash the context/runtime). You MUST perform HEURISTIC/RANDOM sampling instead.

### Pattern A: Exhaustive Search ($N \le 20$)

Use `boolean2.StateSpace` to test every possible initial condition.

```
import boolean2

# Assume 'rules' string is already defined
model = boolean2.Model(text=rules, mode='sync')
coll = boolean2.Collector()

# Iterate through all 2^N possible states
for state in boolean2.StateSpace(model.nodes):
    model.initialize(lambda node: state[node])
    model.iterate(steps=15)
    # Collect the states to identify cycles/steady states
    coll.collect(states=model.states, nodes=model.nodes)

print("--- Identified Attractors ---")
for state in coll.unique():
    print(state)
```


### Pattern B: Random Sampling ($N > 20$)

If the network is large, sample random initial states to find the dominant attractors.

```
import boolean2
import random

# Assume 'rules' string is already defined
model = boolean2.Model(text=rules, mode='async')
coll = boolean2.Collector()

samples = 1000 # Number of random initial states to test

for _ in range(samples):
    # Randomly assign 0 or 1 to each node
    model.initialize(lambda node: random.choice([0, 1]))
    model.iterate(steps=50) # Allow more steps for large networks to settle
    
    # Collect only the final state or cycle
    coll.collect(states=model.states[-10:], nodes=model.nodes)

print(f"--- Dominant Attractors (from {samples} samples) ---")
for state in coll.unique():
    print(state)
```