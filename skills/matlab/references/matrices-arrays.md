# Arrays, Indexing, Data Types, and Performance

This reference targets MATLAB R2026a. Verify GNU Octave behavior separately.

## Array model

MATLAB is 1-based and column-major. Most numeric literals are `double`.
Orientation and trailing singleton dimensions matter.

```matlab
row = 1:5;                 % 1-by-5
column = (1:5).';          % 5-by-1, nonconjugate transpose
A = reshape(1:12, 3, 4);   % values fill down columns

sameShape = zeros(size(A), "like", A);
singleData = zeros(100, 1, "single");
logicalMask = false(size(A));
```

Use `.'` for a plain transpose and `'` for a conjugate transpose. Use
`size(A,dim)`, `numel`, and `ndims`; avoid `length` when a specific dimension
is intended.

### Core storage choices

| Type | Use | Caution |
|---|---|---|
| dense numeric/logical array | homogeneous computation | implicit conversion and memory |
| sparse numeric/logical array | low-density 2-D matrices | not every operation preserves sparsity |
| string array | text with missing values | differs from character arrays |
| categorical | finite labels and ordering | undefined category is missing |
| cell array | heterogeneous containers | `{}` versus `()` semantics |
| structure | named heterogeneous fields | structure arrays complicate shape |
| table | named, equal-height variables | `()` versus `{}` versus dot indexing |
| timetable | table with row times | time zone, sorting, duplicates, alignment |
| datetime/duration | time points/elapsed time | time zones and calendar duration differ |

Choose integer classes for storage or exact integer semantics, not as a drop-in
for floating computation. Integer overflow and mixed-class operations need
explicit tests. Preserve units in names or metadata.

## Indexing

```matlab
value = A(2, 3);       % row 2, column 3
linear = A(5);         % column-major linear index
row = A(2, :);
lastRows = A(max(1,end-2):end, :);
positive = A(A > 0);
A(A < 0) = 0;

[r, c] = ind2sub(size(A), linearIndex);
linearIndex = sub2ind(size(A), r, c);
```

Prefer logical indexing for selection and `find` only when numeric indices are
needed. Verify mask shape. Deleting with `A(index)=[]` changes shape and can be
ambiguous for multidimensional arrays.

R2026b changes an easy-to-miss edge case: linear logical deletion with an
all-false mask can still reshape built-in arrays into a row vector. Preserve
and check the intended shape even when no values match, and include a
no-match case in migration tests.

### Cell, structure, and table indexing

```matlab
C = {42, "sample"; [1 2], datetime("today")};
cellContainer = C(1, :);  % still a cell array
cellContent = C{1, 1};    % contained value

S.SampleID = "S01";
name = S.("SampleID");

tableSlice = T(1:10, ["Time" "Value"]); % table
numericValues = T{:, "Value"};          % underlying content
oneVariable = T.Value;                  % variable content
```

Curly extraction from a table succeeds only when selected variable contents
can concatenate. Preserve table form when variable names and metadata matter.

## Operators and implicit expansion

| Operation | Matrix | Element-wise |
|---|---|---|
| multiply | `A*B` | `A.*B` |
| divide | `A/B`, `A\B` | `A./B`, `A.\B` |
| power | `A^n` | `A.^n` |

Addition, subtraction, comparisons, and many element-wise functions use
compatible-size implicit expansion. Since R2016b, a column and row can create
an outer result:

```matlab
x = (1:3).';
y = 10:10:40;
outerSum = x + y;   % 3-by-4
```

Before relying on expansion, assert intended orientation:

```matlab
assert(iscolumn(x));
assert(isrow(y));
```

Do not use `repmat` solely to emulate supported implicit expansion, but use it
when an explicitly materialized tiled array is actually needed.

## Missing and nonfinite values

Standard missing values are type-specific:

- `NaN`: `double`, `single`, `duration`, `calendarDuration`
- `NaT`: `datetime`
- `<missing>`: `string`
- `<undefined>`: `categorical`
- `''` inside a cell array of character vectors

Integer and logical arrays have no standard missing value. A sentinel such as
`-99` is a data contract, not a MATLAB default.

```matlab
missingMask = ismissing(T);
anyMissing = anymissing(T);
clean = rmmissing(T);
filled = fillmissing(T, "linear", DataVariables="Value");
```

Define whether `Inf` is valid separately; it is not a standard missing
floating-point value. `isfinite` distinguishes finite values. `ismissing`
ignores timetable row times, so validate row times explicitly.

## Tables and timetables

Every table variable has the same row count but can have a different type and
width. Timetables add row times.

```matlab
T = table(sampleID, group, value, ...
    VariableNames=["SampleID" "Group" "Value"]);

TT = timetable(time, value, quality, ...
    VariableNames=["Value" "Quality"]);
TT = sortrows(TT);
hourly = retime(TT, "hourly", "mean");
aligned = synchronize(TT1, TT2, "intersection");
```

Before time alignment:

1. normalize or record time zones;
2. define duplicate-time policy;
3. sort row times;
4. choose union/intersection and interpolation/aggregation deliberately;
5. record daylight-saving and calendar assumptions.

Direct calculations on tables/timetables are supported for compatible
variables, but mixed nonnumeric variables can invalidate an operation.
Selecting numeric variables first is often clearer:

```matlab
numericT = T(:, vartype("numeric"));
```

## Concatenation and reshaping

```matlab
wide = [A B];
tall = [A; B];
flat = A(:);
B = reshape(A, [], 4);
C = permute(X, [2 1 3]);
```

Concatenated dimensions and classes must be compatible. `squeeze` can remove
different dimensions depending on input shape; avoid it in APIs whose output
rank must be stable.

## Performance without folklore

1. Write the clearest correct array code.
2. Use representative data and `timeit`; use the profiler for call-level
   diagnosis.
3. Preallocate when a loop's output shape is known.
4. Vectorize operations that map naturally to array kernels.
5. Keep a loop when vectorization creates large temporaries or obscures logic.
6. Preserve sparsity and data class where appropriate.
7. Benchmark each supported release/platform; R2026a includes implementation
   speedups that can change old trade-offs.

```matlab
y = zeros(size(x), "like", x);
for k = 1:numel(x)
    y(k) = localTransform(x(k));
end
```

Avoid growing arrays in a loop. However, do not preallocate the wrong class or
shape. `zeros(size(x),"like",x)` is usually safer than an unqualified `zeros`.

Parallel arrays, GPU arrays, tall arrays, `parfor`, and distributed arrays
require specific products and supported functions. They also change ordering,
reduction, RNG, and tolerance concerns. Do not suggest them merely because a
loop exists.

## Numerical review checklist

- [ ] Shapes and orientation are asserted where expansion matters.
- [ ] Matrix versus element-wise operators are intentional.
- [ ] Conjugation behavior is intentional.
- [ ] Indexing preserves expected rank and container type.
- [ ] Missing, nonfinite, and sentinel policies are explicit.
- [ ] Table variable names/types and timetable time zones are preserved.
- [ ] Integer overflow and mixed-class conversion are tested.
- [ ] Sparse inputs remain sparse where required.
- [ ] Preallocation and vectorization are measured, not assumed.
- [ ] Memory estimates include temporaries and expanded outputs.

## Sources (reviewed 2026-10-01)

- [Array Indexing](https://www.mathworks.com/help/matlab/math/array-indexing.html)
- [Compatible Array Sizes for Basic Operations](https://www.mathworks.com/help/matlab/matlab_prog/compatible-array-sizes-for-basic-operations.html)
- [MATLAB Data Types](https://www.mathworks.com/help/matlab/data-types.html)
- [Tables](https://www.mathworks.com/help/matlab/tables.html)
- [Timetables](https://www.mathworks.com/help/matlab/timetables.html)
- [`ismissing`](https://www.mathworks.com/help/matlab/ref/ismissing.html)
- [Missing Data in MATLAB](https://www.mathworks.com/help/matlab/data_analysis/missing-data-in-matlab.html)
- [Vectorization](https://www.mathworks.com/help/matlab/matlab_prog/vectorization.html)
- [Preallocation](https://www.mathworks.com/help/matlab/matlab_prog/preallocating-arrays.html)
- [`timeit`](https://www.mathworks.com/help/matlab/ref/timeit.html)
- [Profile MATLAB Code](https://www.mathworks.com/help/matlab/matlab_prog/profiling-for-improving-performance.html)
- [R2026b release notes: logical deletion](https://www.mathworks.com/help/matlab/release-notes.html)
