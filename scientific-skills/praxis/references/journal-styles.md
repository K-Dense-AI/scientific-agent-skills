# Praxis — Journal Style Specifications

## Usage

```python
from core.utils import apply_style
apply_style("nature")  # Apply before plotting
```

Or set globally for a session:
```
/praxis:style nature
```

## Specifications

| Journal | Single col | Double col | Min font | Font | Min DPI |
|---------|-----------|-----------|----------|------|---------|
| Nature | 89 mm (3.50") | 183 mm (7.20") | 7 pt | Arial | 300 |
| Science | 90 mm (3.54") | 180 mm (7.09") | 6 pt | Helvetica | 300 |
| ACS | 82.5 mm (3.25") | 178 mm (7.00") | 6 pt | Arial | 300 |
| Elsevier | 90 mm (3.54") | 190 mm (7.48") | 6 pt | Helvetica/Times | 300 |
| Wiley | 80 mm (3.15") | 170 mm (6.69") | 6 pt | Arial | 300 |
| RSC | 84 mm (3.31") | 170 mm (6.69") | 6 pt | Arial/Helvetica | 300 |
| Springer | 84 mm (3.31") | 174 mm (6.85") | 6 pt | Arial | 300 |
| IEEE | 89 mm (3.50") | 182 mm (7.16") | 8 pt | Helvetica/TNR | 300 |
| MDPI | 85 mm (3.35") | 180 mm (7.09") | 8 pt | Arial | 300 |

## Colour Palettes

All styles default to colourblind-safe palettes (Okabe-Ito or Tol).

### Okabe-Ito (default)
Orange, sky blue, bluish green, yellow, blue, vermillion, reddish purple, black.

### Tol Bright
Blue, red, green, yellow, cyan, purple, grey.

### Tol Muted
Indigo, cyan, teal, green, olive, sand, rose, wine, purple.

## Tips

- Always check your target journal's author guidelines for the latest requirements
- Use vector formats (SVG, PDF, EPS) where possible — they scale without loss
- For raster: 300 dpi minimum, 600 dpi for line art
- Ensure all text in figures meets minimum font size after scaling
- Test printing in greyscale to check that lines/markers remain distinguishable
