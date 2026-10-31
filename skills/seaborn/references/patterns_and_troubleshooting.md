# Common Patterns and Troubleshooting

Frequently needed plot recipes, then the errors seaborn most often raises and what they
actually mean.

## Common Patterns

### Exploratory Data Analysis

```python
# Quick overview of all relationships
sns.pairplot(data=df, hue='target', corner=True)

# Distribution exploration
sns.displot(data=df, x='variable', hue='group',
            kind='kde', fill=True, col='category')

# Correlation analysis
corr = df.select_dtypes(include='number').corr()
sns.heatmap(corr, annot=True, cmap='coolwarm', center=0)
```

### Publication-Quality Figures

```python
sns.set_theme(style='ticks', context='paper', font_scale=1.1)

g = sns.catplot(data=df, x='treatment', y='response',
                col='cell_line', kind='box', height=3, aspect=1.2)
g.set_axis_labels('Treatment Condition', 'Response (μM)')
g.set_titles('{col_name}')
sns.despine(trim=True)

g.savefig('figure.pdf', dpi=300, bbox_inches='tight')
```

### Complex Multi-Panel Figures

```python
# Using matplotlib subplots with seaborn
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

sns.scatterplot(data=df, x='x1', y='y', hue='group', ax=axes[0, 0])
sns.histplot(data=df, x='x1', hue='group', ax=axes[0, 1])
sns.violinplot(data=df, x='group', y='y', ax=axes[1, 0])
sns.heatmap(df.pivot_table(values='y', index='x1', columns='x2'),
            ax=axes[1, 1], cmap='viridis')

plt.tight_layout()
```

### Time Series with Confidence Bands

```python
# Lineplot aggregates; sd shows data spread, not a confidence interval
sns.lineplot(data=timeseries, x='date', y='measurement',
             hue='sensor', style='location', errorbar='sd')

# For more control
g = sns.relplot(data=timeseries, x='date', y='measurement',
                col='location', hue='sensor', kind='line',
                height=4, aspect=1.5, errorbar=('ci', 95))
g.set_axis_labels('Date', 'Measurement (units)')
```

## Troubleshooting

### Issue: Legend Outside Plot Area

Figure-level functions place legends outside by default. To move inside:

```python
g = sns.relplot(data=df, x='x', y='y', hue='category')
sns.move_legend(g, "center right", bbox_to_anchor=(0.9, 0.5))
```

### Issue: Overlapping Labels

```python
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
```

### Issue: Figure Too Small

For figure-level functions:
```python
sns.relplot(data=df, x='x', y='y', height=6, aspect=1.5)
```

For axes-level functions:
```python
fig, ax = plt.subplots(figsize=(10, 6))
sns.scatterplot(data=df, x='x', y='y', ax=ax)
```

### Issue: Colors Not Distinct Enough

```python
# Use a different palette
sns.set_palette("bright")

# Or specify number of colors
palette = sns.color_palette("husl", n_colors=len(df['category'].unique()))
sns.scatterplot(data=df, x='x', y='y', hue='category', palette=palette)
```

### Issue: KDE Too Smooth or Jagged

```python
# Adjust bandwidth
sns.kdeplot(data=df, x='x', bw_adjust=0.5)  # Less smooth
sns.kdeplot(data=df, x='x', bw_adjust=2)    # More smooth
```

### Preserve missing-observation gaps

`lineplot` drops missing rows before drawing and can connect observations on either
side. Reindex to the study's expected sampling schedule first when absent rows
should also count as missing; do not assume every irregular interval is a gap.
This offline example has one subject, one expected observation per integer time,
and an explicit missing row. For several subjects, build runs independently
within each subject (and condition) before assigning a unique segment ID.

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

series = pd.DataFrame({'time': [0, 1, 2, 3, 4], 'value': [1., 2., np.nan, 4., 5.]})
valid = series['value'].notna()
series['segment'] = (~valid).cumsum()
fig, ax = plt.subplots()
sns.lineplot(data=series.loc[valid], x='time', y='value', units='segment',
             estimator=None, errorbar=None, marker='o', sort=True, ax=ax)
ax.set(xlabel='Time', ylabel='Response', title='Gap retained at time 2')
fig.savefig('missing-gap.png', dpi=150)
```

Segmenting is for raw observations. For aggregate trajectories and bands, compute
the estimate and valid intervals with the intended sampling units, then split
those output arrays at undefined or missing timepoints too. Never replace missing
measurements with zero just to obtain a continuous curve.

### Statistical units and normalization

A CI at each x is not automatically a paired or longitudinal analysis. `units`
with `estimator=None` draws individual lines; categorical `units` can request a
multilevel bootstrap but does not fit a mixed model. Keep biological and technical
replication separate and report group sizes. `common_norm=True` normalizes density
across groups together; use `False` for each group's shape, and still disclose n.

Reviewed against [lineplot](https://seaborn.pydata.org/generated/seaborn.lineplot.html),
[error bars](https://seaborn.pydata.org/tutorial/error_bars.html), and the released
0.13.2 drawing code; the gap recipe is checked through its actual line coordinates.
