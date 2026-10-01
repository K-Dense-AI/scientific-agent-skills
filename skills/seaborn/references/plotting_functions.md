# Plotting Functions by Category

Relational, distribution, categorical, regression, and matrix plots: which function to
reach for, its key parameters, and worked examples.

## Plotting Functions by Category

### Relational Plots (Relationships Between Variables)

**Use for:** Exploring how two or more variables relate to each other

- `scatterplot()` - Display individual observations as points
- `lineplot()` - Show trends and changes (automatically aggregates and computes CI)
- `relplot()` - Figure-level interface with automatic faceting

**Key parameters:**
- `x`, `y` - Primary variables
- `hue` - Color encoding for additional categorical/continuous variable
- `size` - Point/line size encoding
- `style` - Marker/line style encoding
- `col`, `row` - Facet into multiple subplots (figure-level only)

```python
# Scatter with multiple semantic mappings
sns.scatterplot(data=df, x='total_bill', y='tip',
                hue='time', size='size', style='sex')

# Line plot with confidence intervals
sns.lineplot(data=timeseries, x='date', y='value', hue='category')

# Faceted relational plot
sns.relplot(data=df, x='total_bill', y='tip',
            col='time', row='sex', hue='smoker', kind='scatter')
```

### Distribution Plots (Single and Bivariate Distributions)

**Use for:** Understanding data spread, shape, and probability density

- `histplot()` - Bar-based frequency distributions with flexible binning
- `kdeplot()` - Smooth density estimates using Gaussian kernels
- `ecdfplot()` - Empirical cumulative distribution (no parameters to tune)
- `rugplot()` - Individual observation tick marks
- `displot()` - Figure-level interface for univariate and bivariate distributions
- `jointplot()` - Bivariate plot with marginal distributions
- `pairplot()` - Matrix of pairwise relationships across dataset

**Key parameters:**
- `x`, `y` - Variables (y optional for univariate)
- `hue` - Separate distributions by category
- `stat` - Normalization: "count", "frequency", "probability", "density"
- `bins` / `binwidth` - Histogram binning control
- `bw_adjust` - KDE bandwidth multiplier (higher = smoother)
- `fill` - Fill area under curve
- `multiple` - How to handle hue: "layer", "stack", "dodge", "fill"

```python
# Histogram with density normalization
sns.histplot(data=df, x='total_bill', hue='time',
             stat='density', multiple='stack')

# Bivariate KDE with contours
sns.kdeplot(data=df, x='total_bill', y='tip',
            fill=True, levels=5, thresh=0.1)

# Joint plot with marginals
sns.jointplot(data=df, x='total_bill', y='tip',
              kind='scatter', hue='time')

# Pairwise relationships
sns.pairplot(data=df, hue='species', corner=True)
```

### Categorical Plots (Comparisons Across Categories)

**Use for:** Comparing distributions or statistics across discrete categories

**Categorical scatterplots:**
- `stripplot()` - Points with jitter to show all observations
- `swarmplot()` - Non-overlapping points (beeswarm algorithm)

**Distribution comparisons:**
- `boxplot()` - Quartiles and outliers
- `violinplot()` - KDE + quartile information
- `boxenplot()` - Enhanced boxplot for larger datasets

**Statistical estimates:**
- `barplot()` - Mean/aggregate with confidence intervals
- `pointplot()` - Point estimates with connecting lines
- `countplot()` - Count of observations per category

**Figure-level:**
- `catplot()` - Faceted categorical plots (set `kind` parameter)

**Key parameters:**
- `x`, `y` - Variables (one typically categorical)
- `hue` - Additional categorical grouping
- `order`, `hue_order` - Control category ordering
- `native_scale` - Preserve numeric/datetime scale on the categorical axis
- `log_scale` - Apply log scaling without dropping down to matplotlib
- `formatter` - Format categorical values; affects both grouping and tick labels
- `dodge` - Separate hue levels; `gap` applies to box/violin/boxen/bar/count, not every categorical function
- `orient` - "x"/"y" or "v"/"h" to specify the categorical axis
- `legend` - True/False or "auto", "brief", "full"
- `kind` - Plot type for catplot: "strip", "swarm", "box", "violin", "boxen", "bar", "point", "count"

```python
# Swarm plot showing all points
sns.swarmplot(data=df, x='day', y='total_bill', hue='sex')

# Violin plot with split for comparison
sns.violinplot(data=df, x='day', y='total_bill',
               hue='sex', split=True)

# Bar plot with error bars
sns.barplot(data=df, x='day', y='total_bill',
            hue='sex', estimator='mean', errorbar=('ci', 95))

# Faceted categorical plot
sns.catplot(data=df, x='day', y='total_bill',
            col='time', kind='box')
```

### Regression Plots (Linear Relationships)

**Use for:** Visualizing linear regressions and residuals

- `regplot()` - Axes-level regression plot with scatter + fit line
- `lmplot()` - Figure-level with faceting support
- `residplot()` - Residual plot for assessing model fit

**Key parameters:**
- `x`, `y` - Variables to regress
- `order` - Polynomial regression order
- `logistic` - Fit logistic regression
- `robust` - Use robust regression (less sensitive to outliers)
- `ci` - Confidence interval width (default 95)
- `scatter_kws`, `line_kws` - Customize scatter and line properties

```python
# Simple linear regression
sns.regplot(data=df, x='total_bill', y='tip')

# Polynomial regression with faceting
sns.lmplot(data=df, x='total_bill', y='tip',
           col='time', order=2, ci=95)

# Check residuals
sns.residplot(data=df, x='total_bill', y='tip')
```

### Matrix Plots (Rectangular Data)

**Use for:** Visualizing matrices, correlations, and grid-structured data

- `heatmap()` - Color-encoded matrix with annotations
- `clustermap()` - Hierarchically-clustered heatmap

**Key parameters:**
- `data` - 2D rectangular dataset (DataFrame or array)
- `annot` - Display values in cells
- `fmt` - Format string for annotations (e.g., ".2f")
- `cmap` - Colormap name
- `center` - Value at colormap center (for diverging colormaps)
- `vmin`, `vmax` - Color scale limits
- `square` - Force square cells
- `linewidths` - Gap between cells

```python
# Correlation heatmap
corr = df.select_dtypes(include='number').corr()
sns.heatmap(corr, annot=True, fmt='.2f',
            cmap='coolwarm', center=0, square=True)

# Clustered heatmap
sns.clustermap(data, cmap='viridis',
               standard_scale=1, figsize=(10, 10))
```

These are selected parameters, not a union accepted by every function. Check [function_reference.md](function_reference.md) for estimator, missing-data, regression, and clustering constraints. APIs reviewed against the [stable API index](https://seaborn.pydata.org/api.html), 2026-10-01.
