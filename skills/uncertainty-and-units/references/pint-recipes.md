# Pint recipes

Verified against pint 0.26.1 with NumPy 2.5.3. Core recipes were rerun on 2026-10-01; optional pandas/xarray integrations are
documentation-verified only. Last-digit floating-point formatting can vary.

## One registry per process

A `Quantity` belongs to the registry that created it. Two registries produce quantities
that cannot interact, and the failure is a bare `ValueError` far from the cause:

```python
import pint

first = pint.UnitRegistry()
second = pint.UnitRegistry()
first.Quantity(1, "m") + second.Quantity(1, "m")
# ValueError: Cannot operate with Quantity and Quantity of different registries.
```

This bites hardest across module boundaries, where each module innocently creates its
own registry at import time, and after unpickling, because a pickled quantity is
restored against the *application* registry rather than the one that created it.

Build one registry and share it, or use the application registry everywhere:

```python
import pint

ureg = pint.UnitRegistry()
pint.set_application_registry(ureg)

# in every other module
ureg = pint.get_application_registry()
```

## Offset units

Degrees Celsius and Fahrenheit measure a point on a scale, not an amount, so
multiplication and addition are undefined for them. Pint refuses the ambiguous operations shown below. Since 0.26, string parsing
such as `ureg("20 degC")` is supported, but that does not make offset arithmetic valid:

```python
Q = ureg.Quantity
Q(20, "degC") * 2
# OffsetUnitCalculusError: Ambiguous operation with offset unit (degree_Celsius).
Q(20, "degC") + Q(5, "degC")
# OffsetUnitCalculusError: Ambiguous operation with offset unit (...).
```

The delta units carry temperature *differences*, and mixed arithmetic works:

```python
Q(20, "degC") + Q(5, "delta_degC")   # 25 degree_Celsius
Q(25, "degC") - Q(20, "degC")        # 5 delta_degree_Celsius
```

Note the second line: subtracting two absolute temperatures yields a delta unit
automatically, which is correct and often surprising downstream.

An uncertainty on a temperature is always a difference. `u = 0.5 degC` means
`0.5 delta_degC`; converting it to Fahrenheit multiplies by 9/5 and applies no offset,
giving `0.9 delta_degF`. Converting the *value* 20 degC to Fahrenheit applies the
offset and gives 68 degF. Two different conversions on the same line of a report.

`pint.UnitRegistry(autoconvert_offset_to_baseunit=True)` makes arithmetic proceed by
converting to kelvin first. It removes the exception, not the ambiguity; enable it
deliberately, not to silence an error.

## Logarithmic units

Pint models dB, dBm, and friends as non-multiplicative units, and `+` on them means
what it means in log space — multiplication of the underlying linear quantities:

```python
Q(10, "dBm").to("mW")        # 10.000000000000002 milliwatt
Q(10, "dBm") + Q(10, "dBm")  # 0.00010000000000000005 kilogram**2 * meter**4 / second**6
```

The second line is 10 mW × 10 mW = 10^-4 W², not 20 mW and not 13 dBm. Nothing raises.
Convert to a linear unit, do the arithmetic, convert back.

## Contexts

Some conversions are physical relations rather than dimensional identities. Pint
performs them only inside a named context, which is a feature: it forces the physics to
be stated.

```python
Q(532, "nm").to("THz", "sp")     # 563.5196578947367 terahertz
Q(532, "nm").to("1/cm", "sp")    # 18796.992481203004 / centimeter
Q(532, "nm").to("eV", "sp")      # 2.3305300457368467 electron_volt
Q(532, "nm").to("THz")           # DimensionalityError

Q(1, "g").to("mol", "chemistry", mw=Q(180.156, "g/mol"))   # 0.005550744909966918 mole
Q(298.15, "K").to("eV", "boltzmann")                       # 0.02569257912108585 electron_volt
Q(1, "gauss").to("T", "Gaussian")                          # 9.999999999338245e-05 tesla
```

The registry ships `spectroscopy` (`sp`), `chemistry` (`chem`), `boltzmann`, `energy`,
`textile`, `Gaussian` (`Gau`), and `ESU` (`esu`). `ureg.enable_contexts("sp")` turns one
on for every subsequent conversion and `ureg.disable_contexts()` turns it off again;
prefer passing the context per call so the assumption stays visible at the point of use.

The spectroscopy context accepts a refractive index `n`, defaulting to 1 (vacuum). It
matters more than it looks:

```python
Q(532, "nm").to("THz", "sp")            # 563.5196578947367 terahertz
Q(532, "nm").to("THz", "sp", n=1.33)    # 423.69899089829823 terahertz
```

Note that `gauss` fails without the Gaussian context: CGS electromagnetic units have
different *dimensions* from SI ones, not merely different scales.

## Stripping the unit

`.magnitude` returns whatever number the quantity happens to be carrying, in whatever
unit it happens to be in. That is the single most common way a unit error enters a
correct-looking program:

```python
length = (12.7 * ureg.mm).magnitude          # 12.7 -- but of what?
length = (12.7 * ureg.mm).to("m").magnitude  # 0.0127 metres, stated
length = (12.7 * ureg.mm).m_as("m")          # same, shorter
```

Always name the unit at the point of extraction. `m_as` exists precisely so there is no
excuse.

## Boundary enforcement

Rather than sprinkling conversions through a function, convert once at its boundary:

```python
@ureg.wraps("J", ("N", "m"))
def work(force, distance):
    return force * distance

work(ureg.Quantity(2, "N"), ureg.Quantity(300, "cm"))   # 6.0 joule
```

`wraps` strips the declared units on the way in and reattaches the result unit on the
way out, so the body is plain floats and stays fast. It defaults to `strict=True`,
which rejects bare numbers:

```python
work(2.0, 3.0)
# ValueError: A wrapped function using strict=True requires quantity or a string
# for all arguments with not None units.
```

`strict=False` accepts bare numbers and assumes they are already in the declared units.
That is convenient and it is also exactly the assumption that unit tracking exists to
avoid; use it only at an edge you control.

`check` validates dimensionality without converting:

```python
@ureg.check("[length]", "[time]")
def speed(distance, elapsed):
    return distance / elapsed

speed(ureg.Quantity(10, "kg"), ureg.Quantity(2, "s"))
# DimensionalityError: Cannot convert from '10 kilogram' ([mass]) to 'a quantity of' ([length])
```

## NumPy interoperability

A quantity can wrap an array, and most ufuncs and many array functions are supported:

```python
import numpy as np

a = ureg.Quantity(np.array([1.0, 2.0, 3.0]), "m")
np.mean(a)                                             # 2.0 meter
np.concatenate([a, ureg.Quantity(np.array([100.0]), "cm")])   # [1.0 2.0 3.0 1.0] meter
np.concatenate([a, np.array([1.0])])
# DimensionalityError: Cannot convert from 'dimensionless' to 'meter'
```

Note that the mixed concatenation converted centimetres to metres correctly, and the
bare array was rejected rather than assumed. Both behaviours are what you want.

Wrapped arrays carry per-operation overhead. In an inner loop, convert at the boundary
with `wraps` or `m_as` and compute on raw arrays.

## Custom units and definitions

```python
ureg.define("cell = [cell_count] = cells")
ureg.define("od600 = [optical_density]")
ureg.define("percent_v_v = 0.01 = %v/v")
```

Defining a new base dimension in square brackets makes it dimensionally distinct from
everything else, which is the point: define each count kind with its own base dimension when needed.
A new name defined as a dimensionless scale factor is still freely convertible to
other dimensionless quantities. Load a whole file of them with `ureg.load_definitions("units.txt")`.

## Formatting

```python
q = ureg.Quantity(1.2345, "kg*m/s**2")
f"{q}"          # 1.2345 kilogram * meter / second ** 2
f"{q:~}"        # 1.2345 kg * m / s ** 2
f"{q:.3f~P}"    # 1.234 kg·m/s²
f"{q:~L}"       # 1.2345\ \frac{\mathrm{kg} \cdot \mathrm{m}}{\mathrm{s}^{2}}
```

`~` gives short unit symbols, `P` pretty Unicode, `L` LaTeX, `C` compact ASCII. Numeric
format specs come first and behave as usual.

## With uncertainties

The two libraries compose: a `ufloat` magnitude inside a pint quantity converts and
formats correctly.

```python
from uncertainties import ufloat

q = ufloat(2.5, 0.1) * ureg.meter
q.to("cm")         # 250+/-10 centimeter
f"{q:.2uS}"        # 2.50(10) meter
```

## Related packages

`pint-pandas` provides a pandas extension dtype so a DataFrame column carries a unit;
`pint-xarray` does the same for xarray. Both are separate installs and both inherit the
one-registry rule.

## Angular frequency is a semantic boundary

Pint treats radians as dimensionless: `Q(1, "Hz").to("rad/s")` gives 1 rad/s,
not 2*pi rad/s. For a cyclic frequency f, construct omega = 2*pi*f explicitly.
An `rpm` conversion includes the full revolution and does produce 2*pi/60 rad/s.

Current APIs: [changes](https://pint.readthedocs.io/en/stable/changes.html),
[contexts](https://pint.readthedocs.io/en/stable/user/contexts.html),
[wrapping](https://pint.readthedocs.io/en/stable/advanced/wrapping.html),
[NumPy](https://pint.readthedocs.io/en/stable/user/numpy.html), and
[definitions](https://pint.readthedocs.io/en/stable/advanced/defining.html).
