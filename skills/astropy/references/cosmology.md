# Cosmological Calculations (astropy.cosmology)

The `astropy.cosmology` subpackage provides tools for cosmological calculations based on various cosmological models. Requires SciPy for these workflows.
Pass redshifts positionally in 8.0.1. The shorter formula fragments below assume
`cosmo`, `z`, and any measured magnitudes are defined for the science case.

> **Import paths:** Always import classes and functions directly from `astropy.cosmology` (as shown in all examples below). The old submodule import paths (`astropy.cosmology.flrw`, `.core`, `.funcs`, `.connect`, `.parameter`) were deprecated in v7.1 and removed in Astropy 8.0.

## Using Built-in Cosmologies

Preloaded cosmologies based on WMAP and Planck observations:

```python
from astropy.cosmology import Planck18, Planck15, Planck13
from astropy.cosmology import WMAP9, WMAP7, WMAP5
from astropy import units as u

# Use Planck 2018 cosmology
cosmo = Planck18

# Calculate distance to z=4
d = cosmo.luminosity_distance(4)
print(f"Luminosity distance at z=4: {d}")

# Age of universe at z=0
age = cosmo.age(0)
print(f"Current age of universe: {age.to(u.Gyr)}")
```

## Creating Custom Cosmologies

### FlatLambdaCDM (Most Common)

Flat universe with cosmological constant:

```python
from astropy.cosmology import FlatLambdaCDM

# Define cosmology
cosmo = FlatLambdaCDM(
    H0=70 * u.km / u.s / u.Mpc,  # Hubble constant at z=0
    Om0=0.3,                      # Matter density parameter at z=0
    Tcmb0=2.725 * u.K             # CMB temperature (optional)
)
```

### LambdaCDM (Non-Flat)

Non-flat universe with cosmological constant:

```python
from astropy.cosmology import LambdaCDM

cosmo = LambdaCDM(
    H0=70 * u.km / u.s / u.Mpc,
    Om0=0.3,
    Ode0=0.7  # Dark energy density parameter
)
```

### wCDM and w0wzCDM

Dark energy with equation of state parameter:

```python
from astropy.cosmology import FlatwCDM, w0wzCDM

# Constant w
cosmo_w = FlatwCDM(H0=70 * u.km/u.s/u.Mpc, Om0=0.3, w0=-0.9)

# Evolving w(z) = w0 + wz * z
cosmo_wz = w0wzCDM(H0=70 * u.km/u.s/u.Mpc, Om0=0.3, Ode0=0.7,
                   w0=-1.0, wz=0.1)
```

`w0wzCDM` extrapolates `w(z)` linearly; upstream does not recommend it for
`z > 1`. Its age integral samples to infinity and can fail numerically for
parameters like `wz=0.1`; a finite low-redshift distance does not validate that
extrapolation. Choose an appropriate physical model before interpreting ages.

## Distance Calculations

### Comoving Distance

Line-of-sight comoving distance:

```python
d_c = cosmo.comoving_distance(z)
```

### Luminosity Distance

Distance for calculating luminosity from observed flux:

```python
d_L = cosmo.luminosity_distance(z)

# Calculate absolute magnitude from apparent magnitude
M = m - 5*np.log10(d_L.to(u.pc).value) + 5
```

### Angular Diameter Distance

Distance for calculating physical size from angular size:

```python
d_A = cosmo.angular_diameter_distance(z)

# Calculate physical size from angular size
theta = 10 * u.arcsec  # Angular size
physical_size = d_A * theta.to(u.radian).value
```

### Comoving Transverse Distance

Transverse comoving distance (equals comoving distance in flat universe):

```python
d_M = cosmo.comoving_transverse_distance(z)
```

### Distance Modulus

```python
dm = cosmo.distmod(z)
# Relates apparent and absolute magnitudes: m - M = dm
```

## Scale Calculations

### kpc per Arcminute

Physical scale at a given redshift:

```python
scale = cosmo.kpc_proper_per_arcmin(z)
# Returns proper kpc / arcmin; keep the angular unit when applying the scale.
```

### Comoving Volume

Volume element for survey volume calculations:

```python
vol = cosmo.comoving_volume(z)  # Total volume to redshift z
vol_element = cosmo.differential_comoving_volume(z)  # dV / (dz dOmega), Mpc3 / sr
```

## Time Calculations

### Age of Universe

Age at a given redshift:

```python
age = cosmo.age(z)
age_now = cosmo.age(0)  # Current age
age_at_z1 = cosmo.age(1)  # Age at z=1
```

### Lookback Time

Time since photons were emitted:

```python
t_lookback = cosmo.lookback_time(z)
# Time between z and z=0
```

## Hubble Parameter

Hubble parameter as function of redshift:

```python
H_z = cosmo.H(z)  # H(z) in km/s/Mpc
E_z = cosmo.efunc(z)  # E(z) = H(z)/H0
```

## Density Parameters

Evolution of density parameters with redshift:

```python
Om_z = cosmo.Om(z)        # Matter density at z
Ode_z = cosmo.Ode(z)      # Dark energy density at z
Ok_z = cosmo.Ok(z)        # Curvature density at z
Ogamma_z = cosmo.Ogamma(z)  # Photon density at z
Onu_z = cosmo.Onu(z)      # Neutrino density at z
```

## Critical and Characteristic Densities

```python
rho_c = cosmo.critical_density(z)  # Critical density at z
rho_m = cosmo.critical_density(z) * cosmo.Om(z)  # Matter density
```

## Inverse Calculations

Find redshift corresponding to a specific value:

```python
from astropy.cosmology import z_at_value

# Find z at specific lookback time
z = z_at_value(cosmo.lookback_time, 10*u.Gyr)

# Find z at specific luminosity distance
z = z_at_value(cosmo.luminosity_distance, 1000*u.Mpc)

# Find z at specific age
z = z_at_value(cosmo.age, 1*u.Gyr)
```

Angular-diameter distance is not monotonic. Select a scientifically justified
`zmin`/`zmax` branch and check the forward residual; a two-point Brent `bracket`
does not constrain the solution to that interval.

```python
z_low = z_at_value(Planck18.angular_diameter_distance, 1500*u.Mpc, zmax=1.5)
z_high = z_at_value(Planck18.angular_diameter_distance, 1500*u.Mpc, zmin=2.5, zmax=10)
```

## Array Operations

All methods accept array inputs:

```python
import numpy as np

z_array = np.linspace(0, 5, 100)
d_L_array = cosmo.luminosity_distance(z_array)
H_array = cosmo.H(z_array)
age_array = cosmo.age(z_array)
```

## Neutrino Effects

Include massive neutrinos:

```python
from astropy.cosmology import FlatLambdaCDM

# With massive neutrinos
cosmo = FlatLambdaCDM(
    H0=70 * u.km/u.s/u.Mpc,
    Om0=0.3,
    Tcmb0=2.725 * u.K,
    Neff=3.04,  # Effective number of neutrino species
    m_nu=[0., 0., 0.06] * u.eV  # Neutrino masses
)
```

Massive neutrinos can make evaluations slower. Choose their masses and `Neff`
from the intended physical model; adding them does not establish model accuracy.
The default `Tcmb0=0` disables photons and neutrinos, even when `m_nu` is given.

## Cloning and Modifying Cosmologies

Cosmology objects are immutable. Clone an already named model. Astropy 8.0.1
raises `TypeError` when cloning an unnamed model with changes, even if a new
`name` is passed; give custom models a name when constructing them.

```python
# Start from a named built-in model
cosmo = Planck18
# Clone with different H0
cosmo_new = cosmo.clone(name="Modified H0", H0=72 * u.km/u.s/u.Mpc)

# Clone with modified name
cosmo_named = cosmo.clone(name="My Custom Cosmology")
```

## Common Use Cases

### Calculating Absolute Magnitude

```python
# From apparent magnitude and redshift
z = 1.5
m_app = 24.5  # Apparent magnitude
d_L = cosmo.luminosity_distance(z)
M_abs = m_app - cosmo.distmod(z).value  # Distance-only; no extinction or K correction
```

### Survey Volume Calculations

```python
# Full-sky comoving volume between two redshifts; multiply by survey solid angle / (4*pi*sr)
z_min, z_max = 0.5, 1.5
volume = cosmo.comoving_volume(z_max) - cosmo.comoving_volume(z_min)

# Convert to Gpc^3
volume_gpc3 = volume.to(u.Gpc**3)
```

### Physical Size from Angular Size

```python
theta = 1 * u.arcsec  # Angular size
z = 2.0
d_A = cosmo.angular_diameter_distance(z)
size_kpc = (d_A * theta.to_value(u.rad)).to(u.kpc)  # Small-angle approximation
```

### Time Since Big Bang

```python
# Age at specific redshift
z_formation = 6
age_at_formation = cosmo.age(z_formation)
time_since_formation = cosmo.age(0) - age_at_formation
```

## Comparison of Cosmologies

```python
# Compare different models
from astropy.cosmology import Planck18, WMAP9

z = 1.0
print(f"Planck18 d_L: {Planck18.luminosity_distance(z)}")
print(f"WMAP9 d_L: {WMAP9.luminosity_distance(z)}")
```

## Performance Considerations

- Calculations are fast for most purposes
- Massive neutrinos reduce speed significantly
- Array operations are vectorized and efficient
- Numerical evaluation is not evidence of physical validity at a chosen redshift;
  record model parameters, radiation/neutrino assumptions and domain.
- Check distance duality `d_L = (1+z)**2 * d_A` for these standard FLRW models,
  and record the named cosmology or all custom parameters in output provenance.
