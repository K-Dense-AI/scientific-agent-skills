# Praxis — Colour Palettes Reference

## Default: Okabe-Ito (colourblind-safe)

Recommended by Nature and widely used in scientific publishing.

| # | Colour | Hex | Usage |
|---|--------|-----|-------|
| 1 | Orange | #E69F00 | Primary data |
| 2 | Sky blue | #56B4E9 | Comparison |
| 3 | Bluish green | #009E73 | Third series |
| 4 | Yellow | #F0E442 | Highlights |
| 5 | Blue | #0072B2 | Alternative primary |
| 6 | Vermillion | #D55E00 | Emphasis |
| 7 | Reddish purple | #CC79A7 | Additional |
| 8 | Black | #000000 | Reference/baseline |

## Tol Bright

Paul Tol's optimised bright palette.

| # | Colour | Hex |
|---|--------|-----|
| 1 | Blue | #4477AA |
| 2 | Red | #EE6677 |
| 3 | Green | #228833 |
| 4 | Yellow | #CCBB44 |
| 5 | Cyan | #66CCEE |
| 6 | Purple | #AA3377 |
| 7 | Grey | #BBBBBB |

## Tol Muted

For figures with many series.

| # | Colour | Hex |
|---|--------|-----|
| 1 | Indigo | #332288 |
| 2 | Cyan | #88CCEE |
| 3 | Teal | #44AA99 |
| 4 | Green | #117733 |
| 5 | Olive | #999933 |
| 6 | Sand | #DDCC77 |
| 7 | Rose | #CC6677 |
| 8 | Wine | #882255 |
| 9 | Purple | #AA4499 |

## uchu (perceptually uniform OKLCh)

From [uchu.style](https://uchu.style/). Perceptually uniform palettes built in OKLCh colour space. Each hue has 9 shades from light (1) to dark (9).

### uchu (categorical — middle shade of each hue)

| # | Colour | Hex |
|---|--------|-----|
| 1 | Blue | #0965EF |
| 2 | Red | #E50E3F |
| 3 | Green | #3FCF4E |
| 4 | Yellow | #FED75C |
| 5 | Purple | #7532C8 |
| 6 | Orange | #FF8834 |
| 7 | Pink | #FFA6C8 |
| 8 | Yin | #828386 |

### Sequential sub-palettes (9 shades each)

Use for heatmaps, gradient fills, or when you need light-to-dark progression within one hue.

| Name | Hex codes (light to dark) |
|------|--------------------------|
| `uchu_blue` | #CCDEFC #9BC0F9 #6AA2F5 #3984F2 #0965EF #085CD8 #0853C1 #0949AC #084095 |
| `uchu_red` | #FACDD7 #F59CB1 #EF6D8B #EA3C65 #E50E3F #CF0C3A #B80C35 #A30D30 #8C0C2B |
| `uchu_green` | #D5F5D9 #AFECB6 #8AE293 #64D970 #3FCF4E #39BC47 #34A741 #2E943A #297F34 |
| `uchu_yellow` | #FFF5D8 #FFEEB9 #FEE69A #FEDF7B #FED75C #E5C255 #CCAE4B #B59944 #9C853C |
| `uchu_purple` | #E2D4F4 #C7ABE9 #AC83DE #915AD3 #7532C8 #6A2EB5 #5F2AA2 #542690 #49227D |
| `uchu_orange` | #FFE5D3 #FFCDAB #FFB783 #FF9F5B #FF8834 #E67C2F #CD6F2C #B56227 #9C5524 |
| `uchu_pink` | #FFEBF2 #FFD9E8 #FFC9DD #FFB7D3 #FFA6C8 #E697B5 #CD87A2 #B57790 #9C677D |
| `uchu_gray` | #F0F0F2 #E3E5E5 #D8D8DA #CBCDCD #BFC0C1 #ADAEAF #9B9B9D #878A8B #757779 |
| `uchu_yin` | #E3E4E6 #CCCCCF #B2B4B6 #9A9C9E #828386 #6A6B6E #515255 #383B3D #202225 |

## Usage

```python
from core.utils import get_palette, set_palette

# Set for all subsequent plots
set_palette("tol_bright")

# Get colours for manual use
colours = get_palette("okabe_ito", n=4)
```

## Guidelines

- Always use colourblind-safe palettes for publications
- Avoid red-green distinctions without additional cues (markers, line styles)
- Test in greyscale: add markers or dashes to distinguish overlapping lines
- For >7 series: combine palette colours with different markers/linestyles
- Sequential data: use matplotlib cmaps (viridis, plasma, inferno) — all perceptually uniform
