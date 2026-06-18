# Feature Detection and Linking

## Overview

Feature detection identifies persistent signals (chromatographic peaks) in LC-MS data. Feature linking combines features across multiple samples for quantitative comparison.

> **Ready-to-run scripts:** The skill ships CLIs that implement these workflows end to end: `scripts/detect_features_metabo.py` (metabolomics), `scripts/detect_features_centroided.py` (proteomics/centroided), `scripts/align_link_quantify.py` (alignment + linking + quant matrix), and `scripts/detect_adducts.py` (adduct grouping). Use them directly, or adapt the code below.

> **API note (pyOpenMS 3.5.0):** The old `FeatureFinder` class and its `run("centroided", ...)` API were **removed**. Metabolomics now uses the `MassTraceDetection` -> `ElutionPeakDetection` -> `FeatureFindingMetabo` pipeline, and centroided/proteomics data uses `FeatureFinderAlgorithmPicked`. The patterns below reflect the current API.

## Feature Detection Basics

A feature represents a chromatographic peak characterized by:
- m/z value (mass-to-charge ratio)
- Retention time (RT)
- Intensity
- Quality score
- Convex hull (spatial extent in RT-m/z space)

## Feature Finding

### Feature Finding for Metabolomics (FeatureFindingMetabo)

For small molecules, run the three-stage pipeline that replaced the removed `FeatureFinder`: detect mass traces, split them into elution peaks, then assemble isotope-grouped features.

```python
import pyopenms as ms

# Load centroided data
exp = ms.MSExperiment()
ms.MzMLFile().load("centroided.mzML", exp)
exp.sortSpectra(True)

# Stage 1: mass trace detection
mtd = ms.MassTraceDetection()
p = mtd.getDefaults()
p.setValue("mass_error_ppm", 10.0)
p.setValue("noise_threshold_int", 1000.0)
mtd.setParameters(p)
mass_traces = []
mtd.run(exp, mass_traces, 0)

# Stage 2: elution peak detection
epd = ms.ElutionPeakDetection()
p = epd.getDefaults()
p.setValue("width_filtering", "fixed")
epd.setParameters(p)
mt_split = []
epd.detectPeaks(mass_traces, mt_split)

# Stage 3: feature assembly with isotope grouping
ffm = ms.FeatureFindingMetabo()
p = ffm.getDefaults()
p.setValue("isotope_filtering_model", "metabolites (5% RMS)")  # or "none"
p.setValue("remove_single_traces", "true")
p.setValue("charge_lower_bound", 1)
p.setValue("charge_upper_bound", 3)
ffm.setParameters(p)
features = ms.FeatureMap()
chrom_out = []
ffm.run(mt_split, features, chrom_out)

print(f"Detected {features.size()} features")

# Save features
ms.FeatureXMLFile().store("features.featureXML", features)
```

### Feature Finding for Proteomics (FeatureFinderAlgorithmPicked)

For centroided peptide data, use `FeatureFinderAlgorithmPicked` (replaces the removed `FeatureFinder` "centroided" workflow):

```python
exp = ms.MSExperiment()
ms.MzMLFile().load("centroided.mzML", exp)
exp.sortSpectra(True)
exp.updateRanges()

ff = ms.FeatureFinderAlgorithmPicked()
params = ff.getDefaults()
params.setValue("isotopic_pattern:charge_low", 1)
params.setValue("isotopic_pattern:charge_high", 4)

features = ms.FeatureMap()
seeds = ms.FeatureMap()
# signature: run(input_map, output, param, seeds)
ff.run(exp, features, params, seeds)

print(f"Detected {features.size()} features")
ms.FeatureXMLFile().store("features.featureXML", features)
```

## Accessing Feature Data

### Iterate Through Features

```python
# Load features
feature_map = ms.FeatureMap()
ms.FeatureXMLFile().load("features.featureXML", feature_map)

# Access individual features
for feature in feature_map:
    print(f"m/z: {feature.getMZ():.4f}")
    print(f"RT: {feature.getRT():.2f}")
    print(f"Intensity: {feature.getIntensity():.0f}")
    print(f"Charge: {feature.getCharge()}")
    print(f"Quality: {feature.getOverallQuality():.3f}")
    print(f"Width (RT): {feature.getWidth():.2f}")

    # Get convex hull
    hull = feature.getConvexHull()
    print(f"Hull points: {hull.getHullPoints().size()}")
```

### Feature Subordinates (Isotope Pattern)

```python
# Access isotopic pattern
for feature in feature_map:
    # Get subordinate features (isotopes)
    subordinates = feature.getSubordinates()

    if subordinates:
        print(f"Main feature m/z: {feature.getMZ():.4f}")
        for sub in subordinates:
            print(f"  Isotope m/z: {sub.getMZ():.4f}")
            print(f"  Isotope intensity: {sub.getIntensity():.0f}")
```

### Export to Pandas

```python
import pandas as pd

# Convert to DataFrame
df = feature_map.get_df()

print(df.columns)
# Columns are lowercase: rt, mz, intensity, charge, quality

# Analyze features
print(f"Mean intensity: {df['intensity'].mean()}")
print(f"RT range: {df['rt'].min():.1f} - {df['rt'].max():.1f}")
```

## Feature Linking

### Map Alignment

Align retention times before linking:

```python
# Load multiple feature maps
fm1 = ms.FeatureMap()
fm2 = ms.FeatureMap()
ms.FeatureXMLFile().load("sample1.featureXML", fm1)
ms.FeatureXMLFile().load("sample2.featureXML", fm2)
feature_maps = [fm1, fm2]

# Pick the largest map as the alignment reference
aligner = ms.MapAlignmentAlgorithmPoseClustering()
ref_idx = max(range(len(feature_maps)), key=lambda i: feature_maps[i].size())
aligner.setReference(feature_maps[ref_idx])

# Align each non-reference map in place against the reference
transformer = ms.MapAlignmentTransformer()
for i, fm in enumerate(feature_maps):
    if i == ref_idx:
        continue
    trafo = ms.TransformationDescription()
    aligner.align(fm, trafo)
    transformer.transformRetentionTimes(fm, trafo, True)
```

### Feature Linking Algorithm

Link features across samples:

```python
# Create feature grouping algorithm
grouper = ms.FeatureGroupingAlgorithmQT()

# Configure parameters
params = grouper.getParameters()
params.setValue("distance_RT:max_difference", 30.0)  # Max RT difference (s)
params.setValue("distance_MZ:max_difference", 10.0)  # Max m/z difference (ppm)
params.setValue("distance_MZ:unit", "ppm")
grouper.setParameters(params)

# Prepare feature maps
feature_maps = [fm1, fm2, fm3]

# Create consensus map
consensus_map = ms.ConsensusMap()

# Link features (feature_maps is a list of FeatureMap)
grouper.group(feature_maps, consensus_map)

# Assign unique IDs before storing
consensus_map.setUniqueIds()

print(f"Created {consensus_map.size()} consensus features")

# Save consensus map
ms.ConsensusXMLFile().store("consensus.consensusXML", consensus_map)
```

## Consensus Features

### Access Consensus Data

```python
# Load consensus map
consensus_map = ms.ConsensusMap()
ms.ConsensusXMLFile().load("consensus.consensusXML", consensus_map)

# Iterate through consensus features
for cons_feature in consensus_map:
    print(f"Consensus m/z: {cons_feature.getMZ():.4f}")
    print(f"Consensus RT: {cons_feature.getRT():.2f}")

    # Get features from individual maps
    for handle in cons_feature.getFeatureList():
        map_idx = handle.getMapIndex()
        intensity = handle.getIntensity()
        print(f"  Sample {map_idx}: intensity {intensity:.0f}")
```

### Consensus Map Metadata

```python
# Access file descriptions (map metadata)
file_descriptions = consensus_map.getColumnHeaders()

for map_idx, description in file_descriptions.items():
    print(f"Map {map_idx}:")
    print(f"  Filename: {description.filename}")
    print(f"  Label: {description.label}")
    print(f"  Size: {description.size}")
```

### Building Quant Matrices from a ConsensusMap

`ConsensusMap` exposes two DataFrame helpers that make quantitative tables easy:

```python
# Feature intensities, features (rows) x samples (columns)
intensity_df = consensus_map.get_intensity_df()

# Per-consensus-feature metadata: rt, mz, charge, quality
metadata_df = consensus_map.get_metadata_df()

# Join into a single annotated quant matrix
quant = metadata_df.join(intensity_df)
```

## Adduct Detection

Identify different ionization forms of the same molecule. The class is `MetaboliteFeatureDeconvolution` (the old `MetaboliteAdductDecharger` does not exist in 3.5.0). Adducts are specified with `Elements:Charge:Probability` syntax, not bracket notation like `[M+H]+`:

```python
# Create adduct deconvolution
mfd = ms.MetaboliteFeatureDeconvolution()

# Configure parameters
p = mfd.getDefaults()
p.setValue("potential_adducts", [b"H:+:0.4", b"Na:+:0.25", b"NH4:+:0.25", b"K:+:0.1", b"H-2O-1:0:0.05"])
p.setValue("charge_min", 1)
p.setValue("charge_max", 1)
mfd.setParameters(p)

# Detect adducts: compute(in, out, cons_groups, cons_edges)
fm_out = ms.FeatureMap()
groups = ms.ConsensusMap()
edges = ms.ConsensusMap()
mfd.compute(feature_map, fm_out, groups, edges)
```

## Complete Feature Detection Workflow

### End-to-End Example

```python
import pyopenms as ms

def feature_detection_workflow(input_files, output_consensus):
    """
    Complete workflow: feature detection and linking across samples.

    Args:
        input_files: List of mzML file paths
        output_consensus: Output consensusXML file path
    """

    feature_maps = []

    # Step 1: Detect features in each file (metabolomics pipeline)
    for mzml_file in input_files:
        print(f"Processing {mzml_file}...")

        # Load experiment
        exp = ms.MSExperiment()
        ms.MzMLFile().load(mzml_file, exp)
        exp.sortSpectra(True)

        # Mass trace detection
        mtd = ms.MassTraceDetection()
        p = mtd.getDefaults()
        p.setValue("mass_error_ppm", 10.0)
        p.setValue("noise_threshold_int", 1000.0)
        mtd.setParameters(p)
        mass_traces = []
        mtd.run(exp, mass_traces, 0)

        # Elution peak detection
        epd = ms.ElutionPeakDetection()
        p = epd.getDefaults()
        p.setValue("width_filtering", "fixed")
        epd.setParameters(p)
        mt_split = []
        epd.detectPeaks(mass_traces, mt_split)

        # Feature assembly
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

        # Store filename in feature map
        features.setPrimaryMSRunPath([mzml_file.encode()])

        feature_maps.append(features)
        print(f"  Found {features.size()} features")

    # Step 2: Align retention times against the largest map
    print("Aligning retention times...")
    aligner = ms.MapAlignmentAlgorithmPoseClustering()
    ref_idx = max(range(len(feature_maps)), key=lambda i: feature_maps[i].size())
    aligner.setReference(feature_maps[ref_idx])
    transformer = ms.MapAlignmentTransformer()
    for i, fm in enumerate(feature_maps):
        if i == ref_idx:
            continue
        trafo = ms.TransformationDescription()
        aligner.align(fm, trafo)
        transformer.transformRetentionTimes(fm, trafo, True)

    # Step 3: Link features
    print("Linking features across samples...")
    grouper = ms.FeatureGroupingAlgorithmQT()
    params = grouper.getParameters()
    params.setValue("distance_RT:max_difference", 30.0)
    params.setValue("distance_MZ:max_difference", 10.0)
    params.setValue("distance_MZ:unit", "ppm")
    grouper.setParameters(params)

    consensus_map = ms.ConsensusMap()
    grouper.group(feature_maps, consensus_map)
    consensus_map.setUniqueIds()

    # Save results
    ms.ConsensusXMLFile().store(output_consensus, consensus_map)

    print(f"Created {consensus_map.size()} consensus features")
    print(f"Results saved to {output_consensus}")

    return consensus_map

# Run workflow
input_files = ["sample1.mzML", "sample2.mzML", "sample3.mzML"]
consensus = feature_detection_workflow(input_files, "consensus.consensusXML")
```

## Feature Filtering

### Filter by Quality

```python
# Filter features by quality score
filtered_features = ms.FeatureMap()

for feature in feature_map:
    if feature.getOverallQuality() > 0.5:  # Quality threshold
        filtered_features.push_back(feature)

print(f"Kept {filtered_features.size()} high-quality features")
```

### Filter by Intensity

```python
# Keep only intense features
min_intensity = 10000

filtered_features = ms.FeatureMap()
for feature in feature_map:
    if feature.getIntensity() >= min_intensity:
        filtered_features.push_back(feature)
```

### Filter by m/z Range

```python
# Extract features in specific m/z range
mz_min = 200.0
mz_max = 800.0

filtered_features = ms.FeatureMap()
for feature in feature_map:
    mz = feature.getMZ()
    if mz_min <= mz <= mz_max:
        filtered_features.push_back(feature)
```

## Feature Annotation

### Add Identification Information

```python
# Annotate features with peptide identifications
# Load identifications
# pyOpenMS 3.5+: peptide IDs must be a PeptideIdentificationList, not a plain list
protein_ids = []
peptide_ids = ms.PeptideIdentificationList()
ms.IdXMLFile().load("identifications.idXML", protein_ids, peptide_ids)

# Create ID mapper
mapper = ms.IDMapper()

# Map IDs to features
mapper.annotate(feature_map, peptide_ids, protein_ids)

# Check annotations
for feature in feature_map:
    peptide_ids_for_feature = feature.getPeptideIdentifications()
    if peptide_ids_for_feature:
        print(f"Feature at {feature.getMZ():.4f} m/z identified")
```

## Best Practices

### Parameter Optimization

Optimize parameters for your data type:

```python
# Test different mass-trace tolerance values (metabolomics pipeline)
mz_tolerances = [5.0, 10.0, 20.0]  # ppm

for tol in mz_tolerances:
    mtd = ms.MassTraceDetection()
    p = mtd.getDefaults()
    p.setValue("mass_error_ppm", tol)
    p.setValue("noise_threshold_int", 1000.0)
    mtd.setParameters(p)
    mass_traces = []
    mtd.run(exp, mass_traces, 0)

    epd = ms.ElutionPeakDetection()
    mt_split = []
    epd.detectPeaks(mass_traces, mt_split)

    ffm = ms.FeatureFindingMetabo()
    features = ms.FeatureMap()
    chrom_out = []
    ffm.run(mt_split, features, chrom_out)

    print(f"Tolerance {tol} ppm: {features.size()} features")
```

### Visual Inspection

Export features for visualization:

```python
# Convert to DataFrame for plotting
df = feature_map.get_df()

import matplotlib.pyplot as plt

plt.figure(figsize=(10, 6))
plt.scatter(df['rt'], df['mz'], s=df['intensity']/1000, alpha=0.5)
plt.xlabel('Retention Time (s)')
plt.ylabel('m/z')
plt.title('Feature Map')
plt.colorbar(label='Intensity (scaled)')
plt.show()
```
