# Quantum machine learning

PennyLane 0.45.1 integrates with Autograd, PyTorch and JAX. TensorFlow maintenance
ended in 0.44 and KerasLayer was removed. The examples below exercise small local
models, not a claim of generalization or advantage over classical methods.

## TorchLayer: correct batch shapes and end-to-end gradients

Tested with PyTorch 2.14.1. The QNode has an `inputs` argument; all other arguments
are trainable weights with entries in `weight_shapes`. Avoid unrestricted `*args`
or `**kwargs`. `AngleEmbedding` handles the leading batch dimension.

```python
import pennylane as qml
import torch

torch.manual_seed(7)
dev = qml.device("default.qubit", wires=2)
@qml.qnode(dev, interface="torch", diff_method="backprop")
def qnode(inputs, weights):
    qml.AngleEmbedding(inputs, wires=[0, 1], rotation="Y")
    qml.StronglyEntanglingLayers(weights, wires=[0, 1])
    return [qml.expval(qml.Z(i)) for i in range(2)]

layer = qml.qnn.TorchLayer(qnode, {"weights": (2, 2, 3)})
model = torch.nn.Sequential(torch.nn.Linear(4, 2), layer, torch.nn.Linear(2, 2)).double()
X = torch.tensor([[0.2, 0.1, 0.4, -0.2], [-0.3, 0.2, -0.1, 0.4],
                  [0.5, 0.3, 0.0, -0.2], [-0.2, -0.3, 0.3, 0.5]], dtype=torch.float64)
y = torch.tensor([0, 1, 0, 1], dtype=torch.long)
optimizer = torch.optim.Adam(model.parameters(), lr=0.02)
optimizer.zero_grad()
logits = model(X)
assert logits.shape == (4, 2)
loss = torch.nn.functional.cross_entropy(logits, y)
loss.backward()
assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())
optimizer.step()
```

A manual QNode can promote input float32 to float64; align a custom surrounding
network's dtype. Do not convert trainable outputs through ordinary NumPy or
`torch.tensor(existing_tensor)`, which detaches gradients. Use `torch.stack` when
combining tensor results. Save model state plus circuit/weight-shape configuration.

## JAX: explicit dataset vectorization

Use the PennyLane-tested JAX/JAXlib 0.7.1 pair in a separate environment. JAX's latest
release is not a compatibility claim for PennyLane. Use explicit precision and
batch only the sample axis:

```python
import pennylane as qml
import jax
import jax.numpy as jnp

jax.config.update("jax_enable_x64", True)
dev = qml.device("default.qubit", wires=2)
@qml.qnode(dev, interface="jax", diff_method="backprop")
def prediction(x, weights):
    qml.AngleEmbedding(x, wires=[0, 1], rotation="Y")
    qml.RY(weights[0], 0)
    qml.RY(weights[1], 1)
    qml.CNOT([0, 1])
    return qml.expval(qml.Z(1))

predict_batch = jax.vmap(prediction, in_axes=(0, None))
@jax.jit
def loss_fn(weights, X, y):
    return jnp.mean((predict_batch(X, weights) - y)**2)

X = jnp.array([[0.1, 0.3], [0.2, -0.4], [-0.3, 0.5]])
y = jnp.array([1.0, -1.0, 1.0])
weights = jnp.array([0.1, 0.2])
value, grad = jax.value_and_grad(loss_fn)(weights, X, y)
assert jnp.isfinite(value) and jnp.isfinite(grad).all()
assert predict_batch(X, weights).shape == (3,)
weights = weights - 0.05 * grad
assert loss_fn(weights, X, y) < value
```

Finite-shot JAX workflows additionally need explicit PRNG keys, split for new
random draws. Validate the specific JIT, differentiation, measurement and device
combination; not all combinations support vector-valued Jacobians. Catalyst's
compiled quantum workflow is distinct from wrapping a simulator loss in `jax.jit`.

## Autograd classifier and stable loss

```python
import pennylane as qml
from pennylane import numpy as np

dev = qml.device("default.qubit", wires=2)
@qml.qnode(dev)
def classifier(x, weights):
    qml.AngleEmbedding(x, wires=[0, 1], rotation="Y")
    qml.StronglyEntanglingLayers(weights, wires=[0, 1])
    return qml.expval(qml.Z(0))

def binary_loss(weights, X, y):
    # Here P(y=1) = (1 + <Z>)/2 is an explicit label convention.
    z = np.stack([classifier(x, weights) for x in X])
    probability = np.clip((1 + z) / 2, 1e-8, 1 - 1e-8)
    return -np.mean(y * np.log(probability) + (1 - y) * np.log1p(-probability))

X = np.array([[0.1, 0.2], [0.9, -0.8]], requires_grad=False)
y = np.array([1.0, 0.0], requires_grad=False)
weights = np.array([[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]], requires_grad=True)
grad = qml.grad(binary_loss)(weights, X, y)
assert grad.shape == weights.shape and np.isfinite(grad).all()
```

For labels defined as the probability of the measured `|1>` outcome, instead use
`(1 - <Z>)/2`. Keep the convention consistent in training and scoring. Clipping
avoids logarithms of zero but saturates gradients at the boundary. A multiclass
model should return the promised number of logits/probabilities on allocated wires;
three observables cannot use an only-two-wire device.

## Encodings and model evaluation

- Angle embedding needs at most one feature per allocated wire; scale using training
  data only. Angular periodicity can alias features.
- Amplitude embedding needs a nonzero finite vector of size at most `2**n` with
  declared padding/normalization. State preparation can be expensive and feature
  differentiation is generally limited by its classical preprocessing.
- Basis embedding accepts binary vectors. IQP embedding includes feature-product
  phases; use the documented template when claiming that encoding.
- `ApproxTimeEvolution(H, time, n)` is a Trotter approximation; noncommuting terms
  need convergence checks. Specify the Hamiltonian and approximation order/steps.
- QCNN pooling must actually remove measured wires from later active-wire sets;
  allocating eight wires and measuring/discarding different indices is a different
  architecture. Recurrent models may return classical expectations as hidden state;
  distinguish that from persistent quantum memory.
- For transfer learning, encode the input before frozen layers, freeze the intended
  parameters in the native framework, and match layer shapes. Fit preprocessing on
  training data and compare with the same classical feature extractor and head.

Record split/group leakage controls, seed repetitions, shots, hyperparameter budget,
classical baselines and confidence intervals. A synthetic training loss decrease
is a gradient smoke test, not predictive validation or quantum advantage.

## Sources

- [TorchLayer](https://docs.pennylane.ai/en/stable/code/api/pennylane.qnn.TorchLayer.html)
- [Torch interface](https://docs.pennylane.ai/en/stable/introduction/interfaces/torch.html)
- [JAX interface](https://docs.pennylane.ai/en/stable/introduction/interfaces/jax.html)
- [Tested upstream dependencies](https://github.com/PennyLaneAI/pennylane/blob/v0.45.1/pyproject.toml)
- [Templates](https://docs.pennylane.ai/en/stable/introduction/templates.html)
