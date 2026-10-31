"""Input checks shared by the two centroided feature detectors."""
import pyopenms as ms


def centroided_ms1(exp, assume_centroided=False):
    """Copy only MS1 scans, require centroid metadata, and sort RT/m/z."""
    selected = []
    for spec in exp:
        if spec.getMSLevel() != 1:
            continue
        kind = spec.getType()
        if kind == ms.SpectrumSettings.SpectrumType.PROFILE:
            raise ValueError("Feature detection requires centroided MS1; peak-pick profile data first.")
        if kind == ms.SpectrumSettings.SpectrumType.UNKNOWN and not assume_centroided:
            raise ValueError("MS1 spectrum type is unknown; verify acquisition/conversion and use --assume-centroided only when justified.")
        selected.append(spec)
    if not selected:
        raise ValueError("No MS1 spectra available for feature detection.")
    result = ms.MSExperiment(exp)
    result.setSpectra(selected)
    result.setChromatograms([])
    result.sortSpectra(True)
    result.updateRanges()
    return result
