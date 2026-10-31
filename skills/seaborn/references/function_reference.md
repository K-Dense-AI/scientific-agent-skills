# Seaborn Function Reference

This document provides a selected reference for major seaborn functions, organized by category. Reviewed against the [0.13.2 API](https://seaborn.pydata.org/api.html) and released signatures on 2026-10-01. Parameter lists below are selected, not complete signatures. Figure-level wrappers accept only parameters supported by their selected `kind`; they do not accept `ax`. Examples use illustrative input DataFrames.

## Relational Plots

### scatterplot()

**Purpose:** Create a scatter plot with points representing individual observations.

**Key Parameters:**
- `data` - DataFrame, array, or dict of arrays
- `x, y` - Variables for x and y axes
- `hue` - Grouping variable for color encoding
- `size` - Grouping variable for size encoding
- `style` - Grouping variable for marker style
- `palette` - Color palette name or list
- `hue_order` - Order for categorical hue levels
- `hue_norm` - Normalization for numeric hue (tuple or Normalize object)
- `sizes` - Size range for size encoding (tuple or dict)
- `size_order` - Order for categorical size levels
- `size_norm` - Normalization for numeric size
- `markers` - Marker style(s) (string, list, or dict)
- `style_order` - Order for categorical style levels
- `legend` - How to draw legend: "auto", "brief", "full", or False
- `ax` - Matplotlib axes to plot on

**Example:**
```python
sns.scatterplot(data=df, x='height', y='weight',
                hue='gender', size='age', style='smoker',
                palette='Set2', sizes=(20, 200))
```

### lineplot()

**Purpose:** Draw a line plot with aggregation and confidence intervals across observations at each x; repeated measures need an explicit sampling-unit strategy.

**Key Parameters:**
- `data` - DataFrame, array, or dict of arrays
- `x, y` - Variables for x and y axes
- `hue` - Grouping variable for color encoding
- `size` - Grouping variable for line width
- `style` - Grouping variable for line style (dashes)
- `units` - Separate trajectory for each sampling unit; also set `estimator=None` (no aggregation)
- `weights` - Observation weights; only mean estimation with CI or no error bars
- `estimator` - Function for aggregating across observations (default: mean)
- `errorbar` - Method for error bars: "sd", "se", "pi", ("ci", level), ("pi", level), or None
- `n_boot` - Number of bootstrap iterations for CI computation
- `seed` - Random seed for reproducible bootstrapping
- `sort` - Sort data before plotting
- `err_style` - "band" or "bars" for error representation
- `err_kws` - Additional parameters for error representation
- `markers` - Marker style(s) for emphasizing data points
- `dashes` - Dash style(s) for lines
- `legend` - How to draw legend
- `ax` - Matplotlib axes to plot on

**Example:**
```python
sns.lineplot(data=timeseries, x='time', y='signal',
             hue='condition', units='subject',
             estimator=None, errorbar=None, marker='o')
```

### relplot()

**Purpose:** Figure-level interface for drawing relational plots (scatter or line) onto a FacetGrid.

**Key Parameters:**
Parameters for the selected `kind` (`scatterplot` or `lineplot`), except `ax`, plus:
- `kind` - "scatter" or "line"
- `col` - Categorical variable for column facets
- `row` - Categorical variable for row facets
- `col_wrap` - Wrap columns after this many columns
- `col_order` - Order for column facet levels
- `row_order` - Order for row facet levels
- `height` - Height of each facet in inches
- `aspect` - Aspect ratio (width = height * aspect)
- `facet_kws` - Additional parameters for FacetGrid

**Example:**
```python
sns.relplot(data=df, x='time', y='measurement',
            hue='treatment', style='batch',
            col='cell_line', row='timepoint',
            kind='line', height=3, aspect=1.5)
```

## Distribution Plots

### histplot()

**Purpose:** Plot univariate or bivariate histograms with flexible binning.

**Key Parameters:**
- `data` - DataFrame, array, or dict
- `x, y` - Variables (y optional for bivariate)
- `hue` - Grouping variable
- `weights` - Variable for weighting observations
- `stat` - Aggregate statistic: "count", "frequency", "probability", "percent", "density"
- `bins` - Number of bins, bin edges, or method ("auto", "fd", "doane", "scott", "stone", "rice", "sturges", "sqrt")
- `binwidth` - Width of bins (overrides bins)
- `binrange` - Range for binning (tuple)
- `discrete` - Treat x as discrete (centers bars on values)
- `cumulative` - Compute cumulative distribution
- `common_bins` - Use same bins for all hue levels
- `common_norm` - Normalize across hue levels
- `multiple` - How to handle hue: "layer", "dodge", "stack", "fill"
- `element` - Visual element: "bars", "step", "poly"
- `fill` - Fill bars/elements
- `shrink` - Scale bar width (for multiple="dodge")
- `kde` - Overlay KDE estimate
- `kde_kws` - Parameters for KDE
- `line_kws` - Parameters for the KDE line when `kde=True`
- `thresh` - Minimum count threshold for bins
- `pthresh` - Minimum probability threshold
- `pmax` - Maximum probability for color scaling
- `log_scale` - Log scale for axis (bool or base)
- `legend` - Whether to show legend
- `ax` - Matplotlib axes

**Example:**
```python
sns.histplot(data=df, x='measurement', hue='condition',
             stat='density', bins=30, kde=True,
             multiple='layer', alpha=0.5)
```

### kdeplot()

**Purpose:** Plot univariate or bivariate kernel density estimates.

**Key Parameters:**
- `data` - DataFrame, array, or dict
- `x, y` - Variables (y optional for bivariate)
- `hue` - Grouping variable
- `weights` - Variable for weighting observations
- `palette` - Color palette
- `hue_order` - Order for hue levels
- `hue_norm` - Normalization for numeric hue
- `multiple` - How to handle hue: "layer", "stack", "fill"
- `common_norm` - Normalize across hue levels
- `common_grid` - Use same grid for all hue levels
- `cumulative` - Compute cumulative distribution
- `bw_method` - Method for bandwidth: "scott", "silverman", or scalar
- `bw_adjust` - Bandwidth multiplier (higher = smoother)
- `log_scale` - Log scale for axis
- `levels` - Number or increasing iso-proportion levels in [0, 1] (bivariate)
- `thresh` - Lowest iso-proportion contour level, not a raw density or p-value
- `gridsize` - Grid resolution
- `cut` - Extension beyond data extremes (in bandwidth units)
- `clip` - Data range for curve (tuple)
- `fill` - Fill area under curve/contours
- `legend` - Whether to show legend
- `ax` - Matplotlib axes

**Example:**
```python
# Univariate
sns.kdeplot(data=df, x='measurement', hue='condition',
            fill=True, common_norm=False, bw_adjust=1.5)

# Bivariate
sns.kdeplot(data=df, x='var1', y='var2',
            fill=True, levels=10, thresh=0.05)
```

### ecdfplot()

**Purpose:** Plot empirical cumulative distribution functions.

**Key Parameters:**
- `data` - DataFrame, array, or dict
- `x, y` - Variables (specify one)
- `hue` - Grouping variable
- `weights` - Variable for weighting observations
- `stat` - "proportion", "percent", or "count"
- `complementary` - Plot complementary CDF (1 - ECDF)
- `palette` - Color palette
- `hue_order` - Order for hue levels
- `hue_norm` - Normalization for numeric hue
- `log_scale` - Log scale for axis
- `legend` - Whether to show legend
- `ax` - Matplotlib axes

**Example:**
```python
sns.ecdfplot(data=df, x='response_time', hue='treatment',
             stat='proportion', complementary=False)
```

### rugplot()

**Purpose:** Plot tick marks showing individual observations along an axis.

**Key Parameters:**
- `data` - DataFrame, array, or dict
- `x, y` - Variable (specify one)
- `hue` - Grouping variable
- `height` - Height of ticks (proportion of axis)
- `expand_margins` - Add margin space for rug
- `palette` - Color palette
- `hue_order` - Order for hue levels
- `hue_norm` - Normalization for numeric hue
- `legend` - Whether to show legend
- `ax` - Matplotlib axes

**Example:**
```python
sns.rugplot(data=df, x='value', hue='category', height=0.05)
```

### displot()

**Purpose:** Figure-level interface for distribution plots onto a FacetGrid.

**Key Parameters:**
Parameters for the selected `kind` (`histplot`, `kdeplot`, or `ecdfplot`), except `ax`, plus:
- `kind` - "hist", "kde", "ecdf"
- `rug` - Add rug plot on marginal axes
- `rug_kws` - Parameters for rug plot
- `col` - Categorical variable for column facets
- `row` - Categorical variable for row facets
- `col_wrap` - Wrap columns
- `col_order` - Order for column facets
- `row_order` - Order for row facets
- `height` - Height of each facet
- `aspect` - Aspect ratio
- `facet_kws` - Additional parameters for FacetGrid

**Example:**
```python
sns.displot(data=df, x='measurement', hue='treatment',
            col='timepoint', kind='kde', fill=True,
            height=3, aspect=1.5, rug=True)
```

### jointplot()

**Purpose:** Draw a bivariate plot with marginal univariate plots.

**Key Parameters:**
- `data` - DataFrame
- `x, y` - Variables for x and y axes
- `hue` - Grouping variable
- `kind` - "scatter", "kde", "hist", "hex", "reg", "resid"
- `height` - Size of the figure (square)
- `ratio` - Ratio of joint to marginal axes
- `space` - Space between joint and marginal axes
- `dropna` - Drop missing values
- `xlim, ylim` - Axis limits (tuples)
- `marginal_ticks` - Show ticks on marginal axes
- `joint_kws` - Parameters for joint plot
- `marginal_kws` - Parameters for marginal plots
- `hue_order` - Order for hue levels
- `palette` - Color palette

**Example:**
```python
sns.jointplot(data=df, x='var1', y='var2', hue='group',
              kind='scatter', height=6, ratio=4,
              joint_kws={'alpha': 0.5})
```

### pairplot()

**Purpose:** Plot pairwise relationships in a dataset.

**Key Parameters:**
- `data` - DataFrame
- `hue` - Grouping variable for color encoding
- `hue_order` - Order for hue levels
- `palette` - Color palette
- `vars` - Variables to plot (default: all numeric)
- `x_vars, y_vars` - Variables for x and y axes (non-square grid)
- `kind` - "scatter", "kde", "hist", "reg"
- `diag_kind` - "auto", "hist", "kde", None
- `markers` - Marker style(s)
- `height` - Height of each facet
- `aspect` - Aspect ratio
- `corner` - Plot only lower triangle
- `dropna` - Drop missing values
- `plot_kws` - Parameters for non-diagonal plots
- `diag_kws` - Parameters for diagonal plots
- `grid_kws` - Parameters for PairGrid

**Example:**
```python
sns.pairplot(data=df, hue='species', palette='Set2',
             vars=['sepal_length', 'sepal_width', 'petal_length'],
             corner=True, height=2.5)
```

## Categorical Plots

### stripplot()

**Purpose:** Draw a categorical scatterplot with jittered points.

**Key Parameters:**
- `data` - DataFrame, array, or dict
- `x, y` - Variables (one categorical, one continuous)
- `hue` - Grouping variable
- `order` - Order for categorical levels
- `hue_order` - Order for hue levels
- `jitter` - Amount of jitter: True, float, or False
- `dodge` - Separate hue levels side-by-side
- `orient` - "v" or "h" (usually inferred)
- `color` - Single color for all elements
- `palette` - Color palette
- `size` - Marker size
- `edgecolor` - Marker edge color
- `linewidth` - Marker edge width
- `native_scale` - Use numeric scale for categorical axis
- `formatter` - Formats categorical values, affecting both grouping and tick labels
- `legend` - Whether to show legend
- `ax` - Matplotlib axes

**Example:**
```python
sns.stripplot(data=df, x='day', y='total_bill',
              hue='sex', dodge=True, jitter=0.2)
```

### swarmplot()

**Purpose:** Draw a categorical scatterplot with non-overlapping points.

**Key Parameters:**
Same as `stripplot()`, except:
- No `jitter` parameter
- `size` - Marker size (important for avoiding overlap)
- `warn_thresh` - Threshold for warning about too many points (default: 0.05)

**Note:** Dense swarms can fail to place points without overlap; the practical limit depends on axes size, marker size, and group density. Check warnings and reduce marker size or use stripplot when needed.

**Example:**
```python
sns.swarmplot(data=df, x='day', y='total_bill',
              hue='time', dodge=True, size=5)
```

### boxplot()

**Purpose:** Draw a box plot showing quartiles and outliers.

**Key Parameters:**
- `data` - DataFrame, array, or dict
- `x, y` - Variables (one categorical, one continuous)
- `hue` - Grouping variable
- `order` - Order for categorical levels
- `hue_order` - Order for hue levels
- `orient` - "v" or "h"
- `color` - Single color for boxes
- `palette` - Color palette
- `saturation` - Color saturation intensity
- `width` - Width of boxes
- `dodge` - Separate hue levels side-by-side
- `fliersize` - Size of outlier markers
- `linewidth` - Box line width
- `whis` - IQR multiplier for whiskers (default: 1.5)
- `notch` - Draw notched boxes
- `showcaps` - Show whisker caps
- `showmeans` - Show mean value
- `meanprops` - Properties for mean marker
- `boxprops` - Properties for boxes
- `whiskerprops` - Properties for whiskers
- `capprops` - Properties for caps
- `flierprops` - Properties for outliers
- `medianprops` - Properties for median line
- `native_scale` - Use numeric scale
- `formatter` - Formats categorical values, affecting both grouping and tick labels
- `legend` - Whether to show legend
- `ax` - Matplotlib axes

**Example:**
```python
sns.boxplot(data=df, x='day', y='total_bill',
            hue='smoker', palette='Set3',
            showmeans=True, notch=True)
```

### violinplot()

**Purpose:** Draw a violin plot combining boxplot and KDE.

**Key Parameters:**
Shares categorical mappings/order, color/palette, width/dodge/gap, native/log scales, formatter, legend and `ax`; box-specific `whis`, `notch`, `showmeans`, and box artist options do not apply. Additional parameters:
- `bw_method` - KDE bandwidth method
- `bw_adjust` - KDE bandwidth multiplier
- `cut` - KDE extension beyond extremes
- `density_norm` - "area", "count", "width"
- `common_norm` - Normalize density across all violins in this axes-level call; do not assume independent facets share normalization
- `inner` - "box", "quart", "point", "stick", None
- `split` - Split violins for hue comparison
- `inner_kws` - Additional parameters for interior artists
- `gridsize` - KDE grid resolution

**Example:**
```python
sns.violinplot(data=df, x='day', y='total_bill',
               hue='sex', split=True, inner='quart',
               density_norm='area', common_norm=False,
               palette='muted')
```

### boxenplot()

**Purpose:** Draw enhanced box plot for larger datasets showing more quantiles.

**Key Parameters:**
Shares categorical mappings/order, color/palette, width/dodge/gap, native/log scales, formatter, legend and `ax`. Use `box_kws`, `line_kws`, and `flier_kws` for artist control; do not pass boxplot-only options. Additional parameters:
- `k_depth` - "tukey", "proportion", "trustworthy", "full", or int
- `outlier_prop` - Proportion of data as outliers
- `trust_alpha` - Alpha for trustworthy depth
- `width_method` - How box widths represent distribution: "exponential", "linear", "area"
- `showfliers` - Show outlier points

**Example:**
```python
sns.boxenplot(data=df, x='day', y='total_bill',
              hue='time', width_method='area', palette='Set2')
```

### barplot()

**Purpose:** Draw a bar plot with error bars showing statistical estimates.

**Key Parameters:**
- `data` - DataFrame, array, or dict
- `x, y` - Variables (one categorical, one continuous)
- `hue` - Grouping variable
- `order` - Order for categorical levels
- `hue_order` - Order for hue levels
- `estimator` - Aggregation function (default: mean)
- `errorbar` - Error representation: "sd", "se", "pi", ("ci", level), ("pi", level), or None
- `n_boot` - Bootstrap iterations
- `seed` - Random seed
- `units` - Identifier for sampling units
- `weights` - Observation weights; only mean with CI or no error bars
- `orient` - "v" or "h"
- `color` - Single bar color
- `palette` - Color palette
- `saturation` - Color saturation
- `width` - Bar width
- `dodge` - Separate hue levels side-by-side
- `err_kws` - Matplotlib keyword arguments for error bars
- `capsize` - Error bar cap width
- `native_scale` - Use numeric scale
- `formatter` - Formats categorical values, affecting both grouping and tick labels
- `legend` - Whether to show legend
- `ax` - Matplotlib axes

**Example:**
```python
sns.barplot(data=df, x='day', y='total_bill',
            hue='sex', estimator='median',
            errorbar=('ci', 95), capsize=0.1,
            err_kws={'linewidth': 1.5})
```

### countplot()

**Purpose:** Show counts of observations in each categorical bin.

**Key Parameters:**
Shares categorical mappings/order, color/palette, width/dodge/gap, native/log scales, formatter, legend and `ax`.
- Specify only x or y (the categorical variable)
- No estimator, weights, units, bootstrap, or errorbar parameters
- `stat` - "count", "percent", "probability", or "proportion"; normalized across the whole plot, not separately within each hue

**Example:**
```python
sns.countplot(data=df, x='day', hue='time',
              palette='pastel', dodge=True)
```

### pointplot()

**Purpose:** Show point estimates and confidence intervals with connecting lines.

**Key Parameters:**
Shares mappings/order, estimator, errorbar, units, weights, seed/n_boot, native/log scales, formatter, legend and `ax`. It does not share bar geometry (`width`, `fill`, `gap`, `saturation`).
- `markers`, `linestyles` - Marker/line styles, optionally one per hue
- `markersize`, `linewidth` - Matplotlib artist sizes; replace deprecated `scale`
- `linestyles="none"` - Disable connections; replaces deprecated `join=False`
- `capsize`, `err_kws` - Error bar appearance
- `dodge` - Boolean or numeric separation along the categorical axis

**Example:**
```python
sns.pointplot(data=df, x='time', y='total_bill',
              hue='sex', markers=['o', 's'],
              linestyles=['-', '--'], capsize=0.1)
```

### catplot()

**Purpose:** Figure-level interface for categorical plots onto a FacetGrid.

**Key Parameters:**
Parameters for the selected categorical `kind`, except `ax`, plus:
- `kind` - "strip", "swarm", "box", "violin", "boxen", "bar", "point", "count"
- `col` - Categorical variable for column facets
- `row` - Categorical variable for row facets
- `col_wrap` - Wrap columns
- `col_order` - Order for column facets
- `row_order` - Order for row facets
- `height` - Height of each facet
- `aspect` - Aspect ratio
- `sharex, sharey` - Share axes across facets
- `legend` - Whether to show legend
- `legend_out` - Place legend outside figure
- `facet_kws` - Additional FacetGrid parameters

**Example:**
```python
sns.catplot(data=df, x='day', y='total_bill',
            hue='smoker', col='time',
            kind='violin', split=True,
            height=4, aspect=0.8)
```

## Regression Plots

### regplot()

**Purpose:** Plot data and a linear regression fit.

**Key Parameters:**
- `data` - DataFrame
- `x, y` - Variables or data vectors
- `x_estimator` - Apply estimator to x bins
- `x_bins` - Bin x for estimator
- `x_ci` - CI for binned estimates
- `scatter` - Show scatter points
- `fit_reg` - Plot regression line
- `ci` - CI for regression estimate (int or None)
- `n_boot` - Bootstrap iterations for CI
- `units` - Identifier for sampling units
- `seed` - Random seed
- `order` - Polynomial regression order
- `logistic` - Fit logistic regression
- `lowess` - Fit lowess smoother
- `robust` - Fit robust regression
- `logx` - Fit y against log(x), drawing in original coordinates; x must be positive
- `x_partial, y_partial` - Partial regression (regress out variables)
- `truncate` - Limit regression line to data range
- `dropna` - Drop missing values
- `x_jitter, y_jitter` - Add jitter to data
- `label` - Label for legend
- `color` - Color for all elements
- `marker` - Marker style
- `scatter_kws` - Parameters for scatter
- `line_kws` - Parameters for regression line
- `ax` - Matplotlib axes

**Example:**
```python
sns.regplot(data=df, x='total_bill', y='tip',
            order=2, ci=95, seed=7,
            scatter_kws={'alpha': 0.5})
```

### lmplot()

**Purpose:** Figure-level interface for regression plots onto a FacetGrid.

**Key Parameters:**
Selected regression options from `regplot()` (not `ax`, `label`, or arbitrary axis-level artist arguments), plus:
- `hue` - Grouping variable
- `col` - Column facets
- `row` - Row facets
- `palette` - Color palette
- `col_wrap` - Wrap columns
- `height` - Facet height
- `aspect` - Aspect ratio
- `markers` - Marker style(s)
- `facet_kws={"sharex": ..., "sharey": ...}` - Share axes; top-level forms are deprecated
- `hue_order` - Order for hue levels
- `col_order` - Order for column facets
- `row_order` - Order for row facets
- `legend` - Whether to show legend
- `facet_kws={"legend_out": ...}` - Legend position; top-level form is deprecated
- `facet_kws` - FacetGrid parameters

**Example:**
```python
sns.lmplot(data=df, x='total_bill', y='tip',
           hue='smoker', col='time', row='sex',
           height=3, aspect=1.2, ci=None)
```

### residplot()

**Purpose:** Plot residuals of a regression.

**Key Parameters:**
Uses `data`, `x`, `y`, `x_partial`, `y_partial`, `order`, `robust`, `dropna`, `label`, `color`, `scatter_kws`, `line_kws`, and `ax`. It has no `ci`, `logistic`, or `logx` parameter.
- Plots residuals (y - predicted) against x, not fitted values
- Adds a horizontal line at y=0
- `lowess=True` fits a smoother to residuals; requires statsmodels

**Example:**
```python
sns.residplot(data=df, x='x', y='y', lowess=True,
              scatter_kws={'alpha': 0.5})
```

## Matrix Plots

### heatmap()

**Purpose:** Plot rectangular data as a color-encoded matrix.

**Key Parameters:**
- `data` - 2D array-like data
- `vmin, vmax` - Anchor values for colormap
- `cmap` - Colormap name or object
- `center` - Value at colormap center
- `robust` - Use robust quantiles for colormap range
- `annot` - Annotate cells: True, False, or array
- `fmt` - Format string for annotations (e.g., ".2f")
- `annot_kws` - Parameters for annotations
- `linewidths` - Width of cell borders
- `linecolor` - Color of cell borders
- `cbar` - Draw colorbar
- `cbar_kws` - Colorbar parameters
- `cbar_ax` - Axes for colorbar
- `square` - Force square cells
- `xticklabels, yticklabels` - Tick labels (True, False, int, or list)
- `mask` - Boolean array to mask cells
- `ax` - Matplotlib axes

**Example:**
```python
# Correlation matrix
corr = df.select_dtypes(include='number').corr()
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(corr, mask=mask, annot=True, fmt='.2f',
            cmap='coolwarm', center=0, square=True,
            linewidths=1, cbar_kws={'shrink': 0.8})
```

### clustermap()

**Purpose:** Plot a hierarchically-clustered heatmap.

**Key Parameters:**
Many heatmap styling parameters through `**kwargs`, but owns its figure/axes; do not pass `ax` or `cbar_ax`. Additional parameters:
- `pivot_kws` - Parameters for pivoting (if needed)
- `method` - Linkage method: "single", "complete", "average", "weighted", "centroid", "median", "ward"
- `metric` - Distance metric for clustering
- `standard_scale` - Min-max scale to [0, 1]: 0 (rows), 1 (columns), or None; distinct from z-scoring
- `z_score` - Z-score normalize data: 0 (rows), 1 (columns), or None
- `row_cluster, col_cluster` - Cluster rows/columns
- `row_linkage, col_linkage` - Precomputed linkage matrices
- `row_colors, col_colors` - Additional color annotations
- `dendrogram_ratio` - Ratio of dendrogram to heatmap
- `colors_ratio` - Ratio of color annotations to heatmap
- `cbar_pos` - Colorbar position (tuple: x, y, width, height)
- `tree_kws` - Parameters for dendrogram
- `figsize` - Figure size

**Example:**
```python
sns.clustermap(data, method='average', metric='euclidean',
               z_score=0, cmap='viridis',
               row_colors=row_colors, col_colors=col_colors,
               figsize=(12, 12), dendrogram_ratio=0.1)
```

## Multi-Plot Grids

### FacetGrid

**Purpose:** Multi-plot grid for plotting conditional relationships.

**Initialization:**
```python
g = sns.FacetGrid(data, row=None, col=None, hue=None,
                  col_wrap=None, sharex=True, sharey=True,
                  height=3, aspect=1, palette=None,
                  row_order=None, col_order=None, hue_order=None,
                  hue_kws=None, dropna=False, legend_out=True,
                  despine=True, margin_titles=False,
                  xlim=None, ylim=None, subplot_kws=None,
                  gridspec_kws=None)
```

**Methods:**
- `map(func, *args, **kwargs)` - Apply function to each facet
- `map_dataframe(func, *args, **kwargs)` - Apply function with full DataFrame
- `set_axis_labels(x_var, y_var)` - Set axis labels
- `set_titles(template, **kwargs)` - Set subplot titles
- `set(**kwargs)` - Set attributes on all axes
- `add_legend(legend_data, title, label_order, **kwargs)` - Add legend
- `savefig(*args, **kwargs)` - Save figure

**Example:**
```python
g = sns.FacetGrid(df, col='time', row='sex', hue='smoker',
                  height=3, aspect=1.5, margin_titles=True)
g.map_dataframe(sns.scatterplot, x='total_bill', y='tip', alpha=0.7)
g.add_legend()
g.set_axis_labels('Total Bill ($)', 'Tip ($)')
g.set_titles('{col_name} | {row_name}')
```

### PairGrid

**Purpose:** Grid for plotting pairwise relationships in a dataset.

**Initialization:**
```python
g = sns.PairGrid(data, hue=None, vars=None,
                 x_vars=None, y_vars=None,
                 hue_order=None, palette=None,
                 hue_kws=None, corner=False,
                 diag_sharey=True, height=2.5,
                 aspect=1, layout_pad=0.5,
                 despine=True, dropna=False)
```

**Methods:**
- `map(func, **kwargs)` - Apply function to all subplots
- `map_diag(func, **kwargs)` - Apply to diagonal
- `map_offdiag(func, **kwargs)` - Apply to off-diagonal
- `map_upper(func, **kwargs)` - Apply to upper triangle
- `map_lower(func, **kwargs)` - Apply to lower triangle
- `add_legend(legend_data, **kwargs)` - Add legend
- `savefig(*args, **kwargs)` - Save figure

**Example:**
```python
g = sns.PairGrid(df, hue='species', vars=['a', 'b', 'c', 'd'],
                 corner=True, height=2.5)
# corner=True omits upper-triangle axes
g.map_lower(sns.kdeplot)
g.map_diag(sns.histplot, kde=True)
g.add_legend()
```

### JointGrid

**Purpose:** Grid for bivariate plot with marginal univariate plots.

**Initialization:**
```python
g = sns.JointGrid(data=None, x=None, y=None, hue=None,
                  height=6, ratio=5, space=0.2,
                  dropna=False, xlim=None, ylim=None,
                  marginal_ticks=False, hue_order=None,
                  palette=None)
```

**Methods:**
- `plot(joint_func, marginal_func, **kwargs)` - Plot both joint and marginals
- `plot_joint(func, **kwargs)` - Plot joint distribution
- `plot_marginals(func, **kwargs)` - Plot marginal distributions
- `refline(x, y, **kwargs)` - Add reference line
- `set_axis_labels(xlabel, ylabel, **kwargs)` - Set axis labels
- `savefig(*args, **kwargs)` - Save figure

**Example:**
```python
g = sns.JointGrid(data=df, x='x', y='y', hue='group',
                  height=6, ratio=5, space=0.2)
g.plot_joint(sns.scatterplot, alpha=0.5)
g.plot_marginals(sns.histplot, kde=True)
g.set_axis_labels('Variable X', 'Variable Y')
```

## Scientific constraints

- In 0.13 categorical plots, statistics are computed in the transformed space when a log scale is active. A displayed mean can therefore be geometric rather than arithmetic; precompute the intended estimate when necessary.

- `lineplot` removes missing rows before drawing: `estimator=None` alone does not preserve gaps. Split contiguous runs as in [patterns_and_troubleshooting.md](patterns_and_troubleshooting.md).
- Choose one regression mode: `order>1`, `logistic`, `robust`, `lowess`, and `logx` are mutually exclusive. Lowess has no bootstrap CI; advanced fits require statsmodels. These are exploratory fits, not a substitute for a specified inference model.
- KDE/violin bandwidth and support affect apparent modes. `cut=0` does not remove boundary bias. `common_norm=False` normalizes each underlying density separately, which hides sample-size differences; a truncated drawing need not integrate to one.
- Correlations use pairwise-complete observations; inspect sample counts and constant columns. A heatmap does not imply significance or causation.
- Clustering needs finite values; a heatmap mask does not make missing values valid clustering input. Reject zero-variance rows for `z_score=0` or zero-range rows for `standard_scale=0` (analogous for columns). Ward linkage requires Euclidean geometry. Choose scaling according to whether rows or features should be standardized, align annotation Series by labels, and save via the returned `ClusterGrid.savefig`.
