# Importing and Exporting (matchms 0.33.1)

Use this reference for file-format selection, return types, streaming behavior,
and safe serialization. The authoritative APIs are the matchms
[`importing`](https://matchms.readthedocs.io/en/latest/api/matchms.importing.html)
and
[`exporting`](https://matchms.readthedocs.io/en/latest/api/matchms.exporting.html)
packages.

## Recommended Entry Points

Use extension-based helpers for ordinary local files:

```python
from matchms.importing import load_spectra
from matchms.exporting import save_spectra

spectra = list(load_spectra("library.msp"))
save_spectra(spectra, "cleaned.mgf")
```

`load_spectra()` supports mzML, mzXML, MGF, MSP, JSON, and `.pickle`.
`save_spectra()` supports MGF, MSP, JSON, and `.pickle` in 0.33.1. Use
format-specific functions when you need an MS level, file-like MGF input,
mzSpecLib output, or precise writer options.

`save_spectra()` refuses to overwrite an existing output unless
`append=True`, and append mode is restricted to MGF and MSP. This makes it
safer than direct writers, whose MGF/MSP defaults are append mode.

## Import Matrix

### MGF

```python
from matchms.importing import load_from_mgf

spectra = list(load_from_mgf("queries.mgf"))
```

Signature:

```text
load_from_mgf(filename: str | Path | TextIO,
              metadata_harmonization: bool = True) -> Generator[Spectrum]
```

MGF is a practical interchange format for centroided MS/MS spectra and supports
streaming iteration. It can also read an already-open text handle:

```python
with open("queries.mgf", encoding="utf-8") as handle:
    spectra = list(load_from_mgf(handle))
```

### MSP

```python
from matchms.importing import load_from_msp

library = list(load_from_msp("library.msp"))
```

Signature:

```text
load_from_msp(filename: str,
              metadata_harmonization: bool = True) -> Generator[Spectrum]
```

MSP is common for reference libraries. Matchms 0.29+ includes support for
GOLM-style MSP data, but source metadata still varies substantially by library.

### mzML and mzXML

```python
from matchms.importing import load_from_mzml, load_from_mzxml

ms2 = list(load_from_mzml("sample.mzML", ms_level=2))
ms1 = list(load_from_mzxml("legacy.mzXML", ms_level=1))
```

Signatures:

```text
load_from_mzml(filename: str | Path, ms_level: int = 2,
               metadata_harmonization: bool = True) -> Generator[Spectrum]
load_from_mzxml(filename: str | Path, ms_level: int = 2,
                metadata_harmonization: bool = True) -> Generator[Spectrum]
```

These readers select one MS level. For chromatograms, binary arrays beyond the
Spectrum abstraction, vendor-specific metadata, or more complex raw-data
parsing, use pyteomics, pymzML, or pyopenms.

### JSON

```python
from matchms.importing import load_from_json

spectra = load_from_json("spectra.json")
```

Signature:

```text
load_from_json(filename: str,
               metadata_harmonization: bool = True) -> list[Spectrum]
```

The JSON reader returns a list, not a generator. It supports matchms JSON and
GNPS-style spectral-library JSON and skips spectra with zero peaks.

### Metabolomics USI

```python
from matchms.importing import load_from_usi

spectrum = load_from_usi(
    "mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00000424840"
)
```

Signature:

```text
load_from_usi(
    usi: str,
    server: str = "https://metabolomics-usi.gnps2.org",
    metadata_harmonization: bool = True,
)
```

The 0.33.1 helper makes an unauthenticated GET to
`https://metabolomics-usi.gnps2.org/json/?usi1=<USI>` with a 10-second timeout.
It expects one JSON object with nonempty `peaks` pairs and `precursor_mz`; there
is no pagination. It returns one `Spectrum` or `None`, not a generator.
Only `usi`, `server`, and `precursor_mz` are retained as metadata: the resolver
also returns fields such as `precursor_charge` and `splash`, which the helper
does not retain. Save the raw response separately when those fields matter.

The helper handles some invalid/404 responses with `None` but does not fully
validate HTTP/schema failures; request, header, or malformed-peak exceptions
can propagate. Check the result before scoring. Use `load_from_usi` directly: the
generic `load_spectra` has a `.usi` dispatch branch but first checks local file
existence, so it is not a reliable entry point for a USI string. Preserve USI,
resolver, retrieval date, and original response alongside analysis outputs.

### Pickle

```python
from matchms.importing import load_from_pickle

spectra = load_from_pickle("trusted-cache.pickle", metadata_harmonization=True)
```

The `metadata_harmonization` argument is required in 0.33.1.

**Security:** Python pickle is executable serialization. Loading an untrusted
pickle can run arbitrary code. Use MGF, MSP, JSON, or mzSpecLib for exchanged or
downloaded data. Restrict pickle to trusted, local, reproducible caches.

## Generator and Memory Semantics

MGF, MSP, mzML, and mzXML readers yield generators. JSON and pickle readers
return lists. Converting a generator with `list(...)` loads all spectra and peak
arrays into memory.

Pairwise scoring requires materialized collections. Before scoring, estimate:

```python
pair_count = len(references) * len(queries)
```

For preprocessing-only MGF/MSP workflows, stream one spectrum at a time:

```python
from pathlib import Path

from matchms.exporting import save_spectra
from matchms.filtering import default_filters, normalize_intensities
from matchms.importing import load_from_mgf

output = Path("cleaned.mgf")
if output.exists():
    raise FileExistsError(output)

first_write = True
for spectrum in load_from_mgf("large.mgf"):
    spectrum = default_filters(spectrum)
    spectrum = normalize_intensities(spectrum)
    if spectrum is None:
        continue
    save_spectra([spectrum], str(output), append=not first_write)
    first_write = False
```

For many spectra, writing larger batches is usually faster than one record per
call.

## Metadata Harmonization

The importers default to `metadata_harmonization=True`. This harmonizes keys
and selected values while constructing each `Spectrum`. In 0.33.1, disabling
this flag skips value harmonization but **still harmonizes keys**, including
lowercasing and alias replacement; it does not preserve source keys.

Keep harmonization enabled for cross-source comparisons. Disable it only when:

- automatic value harmonization must be deferred for inspection;
- you have a documented custom normalization layer; or
- you are investigating an importer/harmonization issue.

When source fidelity matters, retain the original file and export a metadata
audit before applying repair filters.

## Export Matrix

### Generic writer

```python
from matchms.exporting import save_spectra

save_spectra(spectra, "output.mgf", export_style="matchms")
save_spectra(spectra, "output.msp", export_style="nist")
save_spectra(spectra, "output.json", export_style="gnps")
```

Signature:

```text
save_spectra(spectra, file: str,
             export_style: str = "matchms",
             append: bool = False) -> None
```

Supported export styles are `matchms`, `massbank`, `nist`, `riken`, and `gnps`.
Non-matchms export styles retain only their mapped fields, so custom provenance
fields can disappear. These styles rename metadata; they are not complete
format-specific validators. In 0.33.1, `massbank`-style MGF/MSP/JSON fails to
restore `precursor_mz` on matchms reimport in the synthetic roundtrip check.
Prefer `matchms` style for a local roundtrip; reopen converted data and compare
identifiers, precursor values, peak counts, and representative peaks.

### Direct MGF writer

```text
save_as_mgf(spectra, filename, export_style="matchms", file_mode="a")
```

The direct writer's default is append mode. Pass `file_mode="w"` when creating a
fresh output, or prefer `save_spectra()` for overwrite protection.

### Direct MSP writer

```text
save_as_msp(spectra, filename, write_peak_comments=True,
            mode="a", style="matchms", peak_sep="\t")
```

The direct writer also defaults to append mode. Peak comments can be retained
when supported by the input and output style.

### JSON writer

```text
save_as_json(spectra, filename, export_style="matchms")
```

JSON is portable and preserves matchms-oriented structured metadata better than
plain text library formats, but it is not a raw-data archive.

### mzSpecLib writer

```python
from matchms.exporting import save_as_mzspeclib

save_as_mzspeclib(spectra, "library.mzspeclib.txt")
```

`save_as_mzspeclib()` is a direct text writer; it does not use psims and has no
matching matchms importer. In 0.33.1 it overwrites an existing file and formats
intensities to two decimals, so small normalized peaks can become zero. Its
`collision_energy` handler expects text and labels the extracted number as eV;
do not pass normalized collision energy or an unconverted unit. Validate the
result with the downstream mzSpecLib consumer before treating it as an archive.

### Pickled spectra

The generic writer recognizes a `.pickle` extension:

```python
save_spectra(spectra, "trusted-cache.pickle")
```

Use the full `.pickle` suffix; `.pkl` is not recognized by `save_spectra()` in
0.33.1. Pickle is Python-specific, version-sensitive, and unsafe for untrusted
inputs.

## Score Serialization

A `Scores` object has dedicated serializers:

```python
scores.to_json("scores.json")
scores.to_pickle("scores.pickle")
```

Prefer JSON for exchange. Pickled `Scores` objects have the same arbitrary-code
execution risk as pickled spectra.

Reload score JSON with the public loader:

```python
from matchms.importing import scores_from_json

restored = scores_from_json("scores.json")
assert restored.score_names == scores.score_names
```

`scores_from_pickle` exists for trusted local caches only.

## Conversion Pattern

```python
from matchms.exporting import save_spectra
from matchms.importing import load_from_mzml, load_spectra

spectra = list(load_from_mzml("sample.mzML", ms_level=2))
save_spectra(spectra, "sample-ms2.mgf")

roundtrip = list(load_spectra("sample-ms2.mgf"))
assert len(roundtrip) == len(spectra)
for before, after in zip(spectra[:10], roundtrip[:10], strict=True):
    assert len(before.peaks) == len(after.peaks)
```

Do not assume conversion preserves all acquisition metadata. MGF and MSP are
spectral interchange/library formats, not lossless replacements for mzML.

## Output Validation Checklist

- Reopen the output with matchms or the intended downstream consumer.
- Compare spectrum count and non-empty peak count.
- Compare precursor m/z, charge, ion mode, and identifiers.
- Compare m/z and intensity arrays for representative records.
- Confirm the chosen export style and append/overwrite mode.
- Preserve the original source alongside converted data.
- Never load exchanged pickle data.
