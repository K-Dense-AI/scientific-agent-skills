# Data Import, Tables, Timetables, and MAT Files

This reference targets MATLAB R2026a. Treat every external file as untrusted
until its provenance, size, structure, and parser risk are reviewed.

## Safe import workflow

1. Accept one named local path under a confirmed root.
2. Reject URLs, traversal, symlinks, device files, and unexpected extensions.
3. Bound compressed and uncompressed size, rows, columns, variables, nesting,
   strings, and HDF5 objects.
4. Inventory format and metadata before loading values.
5. Define schema, classes, units, encoding, missing sentinels, time zones, and
   duplicate policy.
6. Import the narrowest columns/ranges needed.
7. Validate before computation.
8. Write to a new local output; refuse accidental overwrite.

Do not use a broad directory scan or environment dump to find data. Remote
imports add network, redirect, credential, and changing-content risks; download
them through a separately approved, checksum-recorded workflow.

## High-level text and spreadsheet import

Choose the output model intentionally:

```matlab
options = detectImportOptions("measurements.csv", ...
    TextType="string");
options.SelectedVariableNames = ...
    ["SampleID" "Timestamp" "Value" "Quality"];
options = setvartype(options, "SampleID", "string");
T = readtable("measurements.csv", options);
```

- `readtable`: mixed, named column-oriented data.
- `readmatrix`: homogeneous numeric data.
- `readcell`: heterogeneous cells when a table schema is inappropriate.
- `readlines`/`fileread`: bounded text, with explicit encoding expectations.
- `readtimetable`: time-indexed data when row-time semantics are known.

Use `writetable`, `writematrix`, `writecell`, `writelines`, or
`writetimetable` for corresponding exports. Text/spreadsheet round trips can
change formatting, precision, names, multidimensional variables, empty values,
or types. If exact MATLAB structure matters and the file is trusted, a MAT file
can preserve it—but MAT files have object/code risks and are not a universal
interchange format.

R2026a adds JSON read/write support for tables and timetables. Define the JSON
orientation/schema and test consumers; "JSON" alone does not specify table
shape, time representation, or missing semantics.

## Tables and timetables

```matlab
required = ["SampleID" "Timestamp" "Value"];
assert(all(ismember(required, string(T.Properties.VariableNames))));
assert(isstring(T.SampleID));
assert(isdatetime(T.Timestamp));
assert(isnumeric(T.Value));
```

Table rules:

- all variables have the same row count;
- variables may differ in class and width;
- `T(rows,vars)` preserves a table;
- `T{rows,vars}` extracts/concatenates contents;
- `T.Var` extracts one variable;
- properties can store units and descriptions but are not always preserved by
  external formats.

Timetable rules:

- row times are distinct metadata, not an ordinary variable;
- sort and validate row times;
- preserve or normalize `TimeZone`;
- define duplicates before `retime` or `synchronize`;
- choose interpolation/aggregation and union/intersection deliberately;
- validate missing row times separately from `ismissing(TT)`.

## Missing values

Standard indicators:

| Class | Standard missing |
|---|---|
| `double`, `single`, `duration`, `calendarDuration` | `NaN` |
| `datetime` | `NaT` |
| `string` | `<missing>` |
| `categorical` | `<undefined>` |
| cell array of character vectors | empty character vector |
| integer/logical | none |

Use `standardizeMissing` when source sentinels are documented. Include
`missing` in a custom indicator list when you intend to preserve standard
indicators too. `Inf` is not missing by default.

Never call `rmmissing` as generic cleaning without reporting what rows,
variables, groups, or time coverage were removed.

## MAT file versions

MAT files are MATLAB binary workspace containers:

| Version | `save` option | Compression | Key capability/limit |
|---|---|---|---|
| 4 | `"-v4"` | no | 2-D double, character, sparse; legacy |
| 6 | `"-v6"` | no | N-D, cell, structure; under 2 GiB per variable |
| 7 | `"-v7"` | yes | Unicode and v6 features; under 2 GiB per variable |
| 7.3 | `"-v7.3"` | yes/chunked | HDF5-based, partial access, variables at least 2 GiB on 64-bit |

Factory-default `save` operations use version 7, but the user can change the
default in MAT and FIG Files settings. Explicitly specify `-v7` or `-v7.3`
when exchange compatibility matters. Creating a new file with
`matfile` defaults to version 7.3. File-system limits still apply. Version 7.3
adds HDF5 metadata/chunk overhead and can be larger for heterogeneous
containers.

Do not label arbitrary HDF5 as MATLAB v7.3. The format is HDF5-based but has
MATLAB conventions, references, metadata, and type encodings. GNU Octave 11
cannot save MATLAB v7.3 and has only limited HDF5-based read support.

## MAT safety

Never `load` an untrusted MAT file, even if selecting one variable. A MAT file
can contain:

- MATLAB objects whose classes customize deserialization with `loadobj` or
  custom element serialization;
- constructors, listeners, or System object load hooks reachable from class
  restoration;
- function handles and opaque values;
- Java objects and data interpreted by installed code;
- deeply nested/compressed structures that exhaust resources.

`whos("-file", path)` is useful inside an already approved MATLAB environment,
but invoking MATLAB is itself execution. The bundled
`scripts/inventory_mat_file.py` never launches MATLAB and:

- identifies the header/version;
- optionally uses `scipy.io.whosmat` for Level-5 metadata only;
- optionally uses `h5py` for bounded HDF5 names, shapes, dtypes, links, and
  attribute names;
- never calls `scipy.io.loadmat`;
- never reads dataset values or follows soft/external HDF5 links;
- never deserializes objects or Python pickle.

HDF5 inventory distinguishes null dataspaces (`shape: null`) from scalar
datasets (`shape: []`) and zero-length arrays (for example, `shape: [0]`).
All three are valid HDF5 metadata states, and none is proof of MATLAB v7.3.

An inventory is triage, not a safety certificate. Object-like, opaque,
function, external-link, malformed, or unsupported content requires
quarantine and expert review.

R2026b changes failure recovery for loading some scalar and non-heterogeneous
object arrays: MATLAB can substitute default-constructed objects, or return
an empty class array if replacement fails. In trusted migration tests, check
load warnings, classes, dimensions, and field invariants; successful completion
alone does not prove the saved scientific state was restored.

## Partial access

For a trusted version 7.3 file:

```matlab
file = matfile("trusted-large.mat");
shape = size(file, "measurements");
block = file.measurements(1:1000, :);
```

`matfile` avoids loading an entire variable, but it still processes a MAT file
and can expose class/content risks. Partial read performance depends on HDF5
chunk layout. Do not use it as a security sandbox.

## Low-level I/O

Use `onCleanup` to close reviewed files:

```matlab
[fid, message] = fopen("trusted-input.bin", "rb");
assert(fid >= 0, message);
cleanup = onCleanup(@() fclose(fid));
values = fread(fid, [4 1000], "single=>single");
```

Specify byte order, element type, dimensions, record framing, and maximum
length. Validate `fread` counts and check arithmetic for overflow before
allocating.

HDF5, netCDF, CDF, FITS, Parquet, audio, video, images, databases, and
spreadsheets each have format/library/product/platform constraints. Use their
official current documentation and enforce parser-specific bounds.

## Export and provenance

Record:

- source and output checksums;
- schema/version, encoding, delimiter, locale, and numeric precision;
- variable names, classes, units, dimensions, missing rules;
- timestamp/time-zone representation;
- sort/group order;
- MAT version or external format/library;
- MATLAB release and required products.

Prefer a documented language-neutral format for exchange:

- CSV/TSV for simple rectangular values with a sidecar schema;
- JSON for bounded structured data with an explicit schema;
- Parquet for typed tabular interchange when all consumers agree;
- HDF5/netCDF for scientific arrays with documented conventions;
- MAT only for trusted MATLAB-oriented storage.

Python pickle is executable deserialization, not a scientific interchange
format. Never create, load, or recommend pickle for MATLAB exchange.

## Sources (reviewed 2026-10-01)

- [Data Import and Export](https://www.mathworks.com/help/matlab/data-import-and-export.html)
- [`detectImportOptions`](https://www.mathworks.com/help/matlab/ref/detectimportoptions.html)
- [`readtable`](https://www.mathworks.com/help/matlab/ref/readtable.html)
- [`writetable`](https://www.mathworks.com/help/matlab/ref/writetable.html)
- [Tables](https://www.mathworks.com/help/matlab/tables.html)
- [Timetables](https://www.mathworks.com/help/matlab/timetables.html)
- [`ismissing`](https://www.mathworks.com/help/matlab/ref/ismissing.html)
- [MAT File Versions](https://www.mathworks.com/help/matlab/import_export/mat-file-versions.html)
- [`MatFile`](https://www.mathworks.com/help/matlab/ref/matlab.io.matfile.html)
- [Object Save and Load](https://www.mathworks.com/help/matlab/save-and-load.html)
- [`loadobj`](https://www.mathworks.com/help/matlab/ref/loadobj.html)
- [HDF5 Files](https://www.mathworks.com/help/matlab/hdf5-files.html)
- [MATLAB release notes](https://www.mathworks.com/help/matlab/release-notes.html)

- [SciPy MAT metadata inventory](https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.whosmat.html)
- [h5py null dataspaces](https://docs.h5py.org/en/stable/high/dataset.html#creating-and-reading-empty-or-null-datasets-and-attributes)
