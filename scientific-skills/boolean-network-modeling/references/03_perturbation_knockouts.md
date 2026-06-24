# Simulating Perturbations, Knockouts, and Trajectories

Use this guide when the user asks to simulate a "knockout" (KO), "over-expression" (OE), "mutation", or requests a plot of the network's behavior over time.

## Defining Perturbations

To simulate a mutation, you MUST override the standard initialization by passing a custom function to `model.initialize()`.

Knockout (Loss of Function): Hardcode the node to `0`.

Over-expression (Gain of Function): Hardcode the node to `1`.

Wild-type (Baseline): Initialize randomly or to specific baseline conditions requested by the user.

## Full Simulation and Plotting Pattern

Always use `matplotlib.pyplot.step` with `where='post'` to visualize boolean state changes accurately.

```
import boolean2
import matplotlib.pyplot as plt

# Example Rules
rules = """
Signal* = Signal
Kinase* = Signal and not Phosphatase
TF* = Kinase
Phosphatase* = TF
"""

model = boolean2.Model(text=rules, mode='async')

# Scenario: Knockout of 'Phosphatase'
# We want to see how TF responds to 'Signal' when Phosphatase is gone.
def knockout_condition(node):
    if node == 'Phosphatase': 
        return 0  # Knockout -> always 0
    if node == 'Signal': 
        return 1  # Provide the stimulus -> always 1
    return 0      # Everything else starts at 0

model.initialize(knockout_condition)
model.iterate(steps=30)

# Extract data for visualization
states = model.states
time_steps = range(len(states))

plt.figure(figsize=(10, 6))

# Plot each node's trajectory
for node in model.nodes:
    values = [state[node] for state in states]
    # Use step plot for boolean data
    plt.step(time_steps, values, label=node, where='post', linewidth=2)

plt.ylim(-0.1, 1.2)
plt.yticks([0, 1], ['Off (0)', 'On (1)'])
plt.xlabel("Time Steps")
plt.ylabel("Activity State")
plt.title("Boolean Simulation: Phosphatase Knockout")
plt.legend(loc='upper right', bbox_to_anchor=(1.15, 1))
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()
```


## AI Instructions for Plotting

- DO NOT use standard line plots (`plt.plot`). You MUST use `plt.step(..., where='post')`.

- ALWAYS set y-limits slightly beyond 0 and 1 (`plt.ylim(-0.1, 1.2)`) so the lines do not overlap the plot borders.

- Include a legend outside the plot or in a non-obstructive location.