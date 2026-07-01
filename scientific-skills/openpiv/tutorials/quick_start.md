# OpenPIV Skill Tutorial

## Quick Start (Tweetable Format)

```
🐟 Fluid flow analysis in 3 commands:

1️⃣ Install:  uv pip install -e .
2️⃣ Process:  python -m openpiv_skills.runner --image img1.bmp --image img2.bmp
3️⃣ Analyze:  from openpiv_skills.analyze import PypivAnalyzer
             PypivAnalyzer("results/params.npz").plot_vector_field()

📊 Output: vectors.txt + vector_field.png + params.npz
```

## Full Tutorial

### Step 1: Run PIV Analysis

```bash
cd /home/user/Documents/GitHub/openpiv-skills
python -m openpiv_skills.runner \
    --image openpiv_skills/tutorials/sample_data/exp1_001_a.bmp \
    --image openpiv_skills/tutorials/sample_data/exp1_001_b.bmp \
    --output_dir results \
    --verbose
```

### Step 2: Analyze Results

```python
from openpiv_skills.analyze import PypivAnalyzer

analyzer = PypivAnalyzer("results/params.npz")
analyzer.plot_vector_field()

# Compute vorticity
vorticity = analyzer.compute_vorticity()

# Get velocity magnitude
magnitude = analyzer.get_velocity_magnitude()
```

## Sample Output

| File | Description |
|------|-------------|
| `results/vectors.txt` | Velocity vectors (x, y, u, v, flags) |
| `results/params.npz` | NumPy arrays with all data |
| `results/vector_field.png` | Visual vector plot |

## Try It Now

```python
# Quick one-liner
from openpiv_skills import run_openpiv
run_openpiv("img_a.bmp", "img_b.bmp", verbose=True)
```