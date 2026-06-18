# Metabolomics Workflows

## Overview

PyOpenMS provides specialized tools for untargeted metabolomics analysis including feature detection optimized for small molecules, adduct grouping, compound identification, and integration with metabolomics databases.

> **Code examples target pyOpenMS 3.5.0.** APIs removed in 3.5.0 (e.g. `FeatureFinder().run("centroided", ...)` and `MetaboliteAdductDecharger`) are not used here. The skill also ships ready-to-run scripts implementing these workflows end-to-end: `scripts/detect_features_metabo.py`, `scripts/align_link_quantify.py`, `scripts/consensus_to_matrix.py`, `scripts/detect_adducts.py`, `scripts/accurate_mass_search.py`, and `scripts/export_gnps_sirius.py`.

## Untargeted Metabolomics Pipeline

### Complete Workflow

```python
import pyopenms as ms

def metabolomics_pipeline(input_files, output_dir):
    """
    Complete untargeted metabolomics workflow.

    Args:
        input_files: List of mzML file paths (one per sample)
        output_dir: Directory for output files
    """

    # Step 1: Feature detection (MassTraceDetection ->
    # ElutionPeakDetection -> FeatureFindingMetabo)
    feature_maps = []

    for mzml_file in input_files:
        print(f"Processing {mzml_file}...")

        # Load data
        exp = ms.MSExperiment()
        ms.MzMLFile().load(mzml_file, exp)
        exp.sortSpectra(True)

        # Detect mass traces
        mtd = ms.MassTraceDetection()
        p = mtd.getDefaults()
        p.setValue("mass_error_ppm", 10.0)
        p.setValue("noise_threshold_int", 1000.0)
        mtd.setParameters(p)
        mass_traces = []
        mtd.run(exp, mass_traces, 0)

        # Split traces into elution peaks
        epd = ms.ElutionPeakDetection()
        p = epd.getDefaults()
        p.setValue("width_filtering", "fixed")
        epd.setParameters(p)
        mt_split = []
        epd.detectPeaks(mass_traces, mt_split)

        # Assemble metabolite features
        ffm = ms.FeatureFindingMetabo()
        p = ffm.getDefaults()
        p.setValue("isotope_filtering_model", "metabolites (5% RMS)")
        p.setValue("remove_single_traces", "true")
        p.setValue("charge_lower_bound", 1)
        p.setValue("charge_upper_bound", 3)
        ffm.setParameters(p)
        features = ms.FeatureMap()
        chrom_out = []
        ffm.run(mt_split, features, chrom_out)
        features.setUniqueIds()

        features.setPrimaryMSRunPath([mzml_file.encode()])
        feature_maps.append(features)

        print(f"  Detected {features.size()} features")

    # Step 2: Adduct detection and grouping
    print("Detecting adducts...")
    adduct_grouped_maps = []

    for fm in feature_maps:
        mfd = ms.MetaboliteFeatureDeconvolution()
        p = mfd.getDefaults()
        # potential_adducts uses Elements:Charge:Probability syntax
        p.setValue("potential_adducts",
                   [b"H:+:0.4", b"Na:+:0.25", b"NH4:+:0.25",
                    b"K:+:0.1", b"H-2O-1:0:0.05"])
        p.setValue("charge_min", 1)
        p.setValue("charge_max", 1)
        mfd.setParameters(p)

        fm_out = ms.FeatureMap()
        groups = ms.ConsensusMap()
        edges = ms.ConsensusMap()
        mfd.compute(fm, fm_out, groups, edges)  # 4 args
        adduct_grouped_maps.append(fm_out)

    # Step 3: RT alignment (PoseClustering: pick a reference,
    # then align each map in place against it)
    print("Aligning retention times...")
    aligner = ms.MapAlignmentAlgorithmPoseClustering()
    reference = adduct_grouped_maps[0]
    aligner.setReference(reference)

    transformer = ms.MapAlignmentTransformer()
    for fm in adduct_grouped_maps:
        trafo = ms.TransformationDescription()
        aligner.align(fm, trafo)
        transformer.transformRetentionTimes(fm, trafo, True)

    aligned_maps = adduct_grouped_maps

    # Step 4: Feature linking
    print("Linking features...")
    grouper = ms.FeatureGroupingAlgorithmQT()

    params = grouper.getParameters()
    params.setValue("distance_RT:max_difference", 60.0)  # seconds
    params.setValue("distance_MZ:max_difference", 5.0)  # ppm
    params.setValue("distance_MZ:unit", "ppm")
    grouper.setParameters(params)

    consensus_map = ms.ConsensusMap()
    grouper.group(aligned_maps, consensus_map)  # list of FeatureMap
    consensus_map.setUniqueIds()

    print(f"Created {consensus_map.size()} consensus features")

    # Step 5: Export results
    consensus_file = f"{output_dir}/consensus.consensusXML"
    ms.ConsensusXMLFile().store(consensus_file, consensus_map)

    # Export quant matrix for downstream analysis
    # get_intensity_df() -> features x samples; get_metadata_df() -> rt/mz/charge/quality
    intensities = consensus_map.get_intensity_df()
    metadata = consensus_map.get_metadata_df()
    csv_file = f"{output_dir}/metabolite_table.csv"
    metadata.join(intensities).to_csv(csv_file)

    print(f"Results saved to {output_dir}")

    return consensus_map

# Run pipeline
input_files = ["sample1.mzML", "sample2.mzML", "sample3.mzML"]
consensus = metabolomics_pipeline(input_files, "output")
```

## Adduct Detection

### Configure Adduct Types

Adducts are configured with the `Elements:Charge:Probability` syntax (e.g.
`b"Na:+:0.25"`), not bracket notation like `[M+Na]+`. Probabilities across the
list should sum to ~1.0.

```python
# Create adduct detector
mfd = ms.MetaboliteFeatureDeconvolution()

# Configure common adducts
params = mfd.getDefaults()

# Positive mode adducts (Elements:Charge:Probability)
positive_adducts = [
    b"H:+:0.4",
    b"Na:+:0.25",
    b"NH4:+:0.25",
    b"K:+:0.1",
    b"H-2O-1:0:0.05",  # neutral water loss
]

# Negative mode adducts (set negative_mode="true" when using these)
negative_adducts = [
    b"H-1:-:0.6",
    b"Cl:-:0.2",
]

# Set for positive mode
params.setValue("potential_adducts", positive_adducts)
params.setValue("charge_min", 1)
params.setValue("charge_max", 1)
mfd.setParameters(params)

# Apply adduct detection (4 args: in, out, groups, edges)
feature_map_out = ms.FeatureMap()
groups = ms.ConsensusMap()
edges = ms.ConsensusMap()
mfd.compute(feature_map, feature_map_out, groups, edges)
```

### Access Adduct Information

```python
# Check adduct annotations
for feature in feature_map_out:
    # Get adduct type if annotated
    if feature.metaValueExists("adduct"):
        adduct = feature.getMetaValue("adduct")
        neutral_mass = feature.getMetaValue("neutral_mass")
        print(f"m/z: {feature.getMZ():.4f}")
        print(f"  Adduct: {adduct}")
        print(f"  Neutral mass: {neutral_mass:.4f}")
```

## Compound Identification

### Accurate Mass Search (HMDB)

The built-in `AccurateMassSearchEngine` annotates a `FeatureMap` against HMDB
and writes results as mzTab.

> **Caveat:** the pip wheel ships `HMDBMappingFile.tsv` but **not**
> `HMDB2StructMapping.tsv`, so `engine.init()` fails unless you supply the
> struct file yourself. Download it from
> https://github.com/OpenMS/OpenMS/blob/develop/share/OpenMS/CHEMISTRY/HMDB2StructMapping.tsv
> and point `db:struct` at it.

```python
engine = ms.AccurateMassSearchEngine()
p = engine.getDefaults()
p.setValue("mass_error_value", 5.0)
p.setValue("mass_error_unit", "ppm")
p.setValue("ionization_mode", "positive")
# If the struct file is missing from the wheel, supply it:
# p.setValue("db:struct", b"/path/to/HMDB2StructMapping.tsv")
engine.setParameters(p)
engine.init()

mztab = ms.MzTab()
engine.run(feature_map, mztab)
ms.MzTabFile().store("out.mzTab", mztab)
```

### Mass-Based Annotation (custom database)

```python
# Annotate features against your own compound list.
# (Plain Python, no pyOpenMS-specific DB required.)

# Load compound database (example structure)
# In practice, use external database like HMDB, METLIN

compound_db = [
    {"name": "Glucose", "formula": "C6H12O6", "mass": 180.0634},
    {"name": "Citric acid", "formula": "C6H8O7", "mass": 192.0270},
    # ... more compounds
]

# Annotate features
mass_tolerance = 5.0  # ppm

for feature in feature_map:
    observed_mz = feature.getMZ()

    # Calculate neutral mass (assuming [M+H]+)
    neutral_mass = observed_mz - 1.007276  # Proton mass

    # Search database
    for compound in compound_db:
        mass_error_ppm = abs(neutral_mass - compound["mass"]) / compound["mass"] * 1e6

        if mass_error_ppm <= mass_tolerance:
            print(f"Potential match: {compound['name']}")
            print(f"  Observed m/z: {observed_mz:.4f}")
            print(f"  Expected mass: {compound['mass']:.4f}")
            print(f"  Error: {mass_error_ppm:.2f} ppm")
```

### MS/MS-Based Identification

```python
# Load MS2 data
exp = ms.MSExperiment()
ms.MzMLFile().load("data_with_ms2.mzML", exp)

# Extract MS2 spectra
ms2_spectra = []
for spec in exp:
    if spec.getMSLevel() == 2:
        ms2_spectra.append(spec)

print(f"Found {len(ms2_spectra)} MS2 spectra")

# Match to spectral library
# (Requires external tool or custom implementation)
```

## Data Normalization

### Total Ion Current (TIC) Normalization

```python
import numpy as np

# Load consensus map
consensus_map = ms.ConsensusMap()
ms.ConsensusXMLFile().load("consensus.consensusXML", consensus_map)

# Calculate TIC per sample
n_samples = len(consensus_map.getColumnHeaders())
tic_per_sample = np.zeros(n_samples)

for cons_feature in consensus_map:
    for handle in cons_feature.getFeatureList():
        map_idx = handle.getMapIndex()
        tic_per_sample[map_idx] += handle.getIntensity()

print("TIC per sample:", tic_per_sample)

# Normalize to median TIC
median_tic = np.median(tic_per_sample)
normalization_factors = median_tic / tic_per_sample

print("Normalization factors:", normalization_factors)

# Apply normalization
consensus_map_normalized = ms.ConsensusMap(consensus_map)
for cons_feature in consensus_map_normalized:
    feature_list = cons_feature.getFeatureList()
    for handle in feature_list:
        map_idx = handle.getMapIndex()
        normalized_intensity = handle.getIntensity() * normalization_factors[map_idx]
        handle.setIntensity(normalized_intensity)
```

## Quality Control

### Coefficient of Variation (CV) Filtering

```python
import pandas as pd
import numpy as np

# Export intensities to pandas (features x samples)
df = consensus_map.get_intensity_df()

# Assume QC samples are columns with 'QC' in name
qc_cols = [col for col in df.columns if 'QC' in col]

if qc_cols:
    # Calculate CV for each feature in QC samples
    qc_data = df[qc_cols]
    cv = (qc_data.std(axis=1) / qc_data.mean(axis=1)) * 100

    # Filter features with CV < 30% in QC samples
    good_features = df[cv < 30]

    print(f"Features before CV filter: {len(df)}")
    print(f"Features after CV filter: {len(good_features)}")
```

### Blank Filtering

```python
# Remove features present in blank samples
blank_cols = [col for col in df.columns if 'Blank' in col]
sample_cols = [col for col in df.columns if 'Sample' in col]

if blank_cols and sample_cols:
    # Calculate mean intensity in blanks and samples
    blank_mean = df[blank_cols].mean(axis=1)
    sample_mean = df[sample_cols].mean(axis=1)

    # Keep features with 3x higher intensity in samples than blanks
    ratio = sample_mean / (blank_mean + 1)  # Add 1 to avoid division by zero
    filtered_df = df[ratio > 3]

    print(f"Features before blank filtering: {len(df)}")
    print(f"Features after blank filtering: {len(filtered_df)}")
```

## Missing Value Imputation

```python
import pandas as pd
import numpy as np

# Load intensities (features x samples)
df = consensus_map.get_intensity_df()

# Replace zeros with NaN
df = df.replace(0, np.nan)

# Count missing values
missing_per_feature = df.isnull().sum(axis=1)
print(f"Features with >50% missing: {sum(missing_per_feature > len(df.columns)/2)}")

# Simple imputation: replace with minimum value
for col in df.columns:
    if df[col].dtype in [np.float64, np.int64]:
        min_val = df[col].min() / 2  # Half minimum
        df[col].fillna(min_val, inplace=True)
```

## Metabolite Table Export

### Create Analysis-Ready Table

```python
import pandas as pd

def create_metabolite_table(consensus_map, output_file):
    """
    Create metabolite quantification table for statistical analysis.
    """

    # Get column headers (file descriptions)
    headers = consensus_map.getColumnHeaders()

    # Initialize data structure
    data = {
        'mz': [],
        'rt': [],
        'feature_id': []
    }

    # Add sample columns
    for map_idx, header in headers.items():
        sample_name = header.label or f"Sample_{map_idx}"
        data[sample_name] = []

    # Extract feature data
    for idx, cons_feature in enumerate(consensus_map):
        data['mz'].append(cons_feature.getMZ())
        data['rt'].append(cons_feature.getRT())
        data['feature_id'].append(f"F{idx:06d}")

        # Initialize intensities
        intensities = {map_idx: 0.0 for map_idx in headers.keys()}

        # Fill in measured intensities
        for handle in cons_feature.getFeatureList():
            map_idx = handle.getMapIndex()
            intensities[map_idx] = handle.getIntensity()

        # Add to data structure
        for map_idx, header in headers.items():
            sample_name = header.label or f"Sample_{map_idx}"
            data[sample_name].append(intensities[map_idx])

    # Create DataFrame
    df = pd.DataFrame(data)

    # Sort by RT
    df = df.sort_values('rt')

    # Save to CSV
    df.to_csv(output_file, index=False)

    print(f"Metabolite table with {len(df)} features saved to {output_file}")

    return df

# Create table
df = create_metabolite_table(consensus_map, "metabolite_table.csv")
```

## Integration with External Tools

### Export for MetaboAnalyst

```python
def export_for_metaboanalyst(df, output_file):
    """
    Format data for MetaboAnalyst input.

    Requires sample names as columns, features as rows.
    """

    # Transpose DataFrame
    # Remove metadata columns
    sample_cols = [col for col in df.columns if col not in ['mz', 'rt', 'feature_id']]

    # Extract sample data
    sample_data = df[sample_cols]

    # Transpose (samples as rows, features as columns)
    df_transposed = sample_data.T

    # Add feature identifiers as column names
    df_transposed.columns = df['feature_id']

    # Save
    df_transposed.to_csv(output_file)

    print(f"MetaboAnalyst format saved to {output_file}")

# Export
export_for_metaboanalyst(df, "for_metaboanalyst.csv")
```

## Best Practices

### Sample Size and Replicates

- Include QC samples (pooled sample) every 5-10 injections
- Run blank samples to identify contamination
- Use at least 3 biological replicates per group
- Randomize sample injection order

### Parameter Optimization

Test parameters on pooled QC sample:

```python
# Test different mass trace detection parameters
mass_errors_ppm = [3.0, 5.0, 10.0]
noise_thresholds = [500.0, 1000.0, 2000.0]

exp.sortSpectra(True)

for mass_err in mass_errors_ppm:
    for noise in noise_thresholds:
        mtd = ms.MassTraceDetection()
        p = mtd.getDefaults()
        p.setValue("mass_error_ppm", mass_err)
        p.setValue("noise_threshold_int", noise)
        mtd.setParameters(p)
        mass_traces = []
        mtd.run(exp, mass_traces, 0)

        epd = ms.ElutionPeakDetection()
        p = epd.getDefaults()
        p.setValue("width_filtering", "fixed")
        epd.setParameters(p)
        mt_split = []
        epd.detectPeaks(mass_traces, mt_split)

        ffm = ms.FeatureFindingMetabo()
        p = ffm.getDefaults()
        p.setValue("isotope_filtering_model", "metabolites (5% RMS)")
        p.setValue("remove_single_traces", "true")
        ffm.setParameters(p)
        features = ms.FeatureMap()
        chrom_out = []
        ffm.run(mt_split, features, chrom_out)

        print(f"mass_error_ppm={mass_err}, noise={noise}: "
              f"{features.size()} features")
```

### Retention Time Windows

Adjust based on chromatographic method:

```python
# For 10-minute LC gradient
params.setValue("distance_RT:max_difference", 30.0)  # 30 seconds

# For 60-minute LC gradient
params.setValue("distance_RT:max_difference", 90.0)  # 90 seconds
```
