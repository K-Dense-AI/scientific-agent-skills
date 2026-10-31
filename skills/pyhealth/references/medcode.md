# Medical codes and tokenizers

PyHealth 2.0.2 implements local lookup/mapping over **downloaded, cached** reference
tables. They are not all bundled in the wheel. First use needs public network access
to `https://storage.googleapis.com/pyhealth/resource/`; there is no API key, JSON
request body or pagination. SDK reads retrieve CSV resources by filename and cache
processed mappings. Record the resource snapshot/checksum for reproducible work;
package version alone does not pin the remote tables.

## Lookup within a system

```python
from pyhealth.medcode import InnerMap
icd9 = InnerMap.load("ICD9CM")
print(icd9.lookup("428.0"))
# Congestive heart failure, unspecified
print(icd9.get_ancestors("428.0"))
# ['428', '420-429.99', '390-459.99', '001-999.99']
atc = InnerMap.load("ATC")
print(atc.lookup("M01AE51"))
# ibuprofen, combinations
```

These calls and results were executed with 2.0.2. Supported vocabulary classes
include `ICD9CM`, `ICD10CM`, `ICD9PROC`, `ICD10PCS`, `ATC`, `NDC`, `RxNorm`, `CCSCM`
and `CCSPROC`. A class being available does not guarantee every cross-map exists.
Validate unknown codes instead of inventing a description.

## Cross-map

```python
from pyhealth.medcode import CrossMap
print(CrossMap.load("ICD9CM", "CCSCM").map("428.0"))  # ['108']
print(CrossMap.load("NDC", "RxNorm").map("50580049698"))  # ['209387']
ndc_to_atc = CrossMap.load("NDC", "ATC")
print(ndc_to_atc.map("00527051210"))  # ['A11CC01']
print(ndc_to_atc.map("00527051210", target_kwargs={"level": 3}))  # ['A11C']
```

These mapping examples were executed. `CrossMap` first tries
`<source>_to_<target>.csv` and on an HTTP error tries the reversed filename; the CSV
columns still identify the requested direction. If neither resource exists, handle
the failure explicitly. A source code may yield `[]` or multiple targets. Keep NDCs
as strings to preserve leading zeros. Never assume mappings are bijective,
lossless, current regulatory coding guidance, or enough to eliminate cohort shift.

Do not promise arbitrary ICD-9/ICD-10 conversion merely because both vocabularies
load. Verify the desired map resource and its version. When combining MIMIC-IV
codes, preserve each row's `icd_version` before conversion. Report unmapped and
multiply mapped fractions, normalization decisions and any discarded records.
For code reduction, inspect the actual vocabulary; there is no universal fixed CCS
category count across resources and editions.

## Tokenizer dimensions

```python
from pyhealth.tokenizer import Tokenizer
vocab = ["A01A", "A02A", "A02B", "A03C", "A03D", "A04A"]
tok = Tokenizer(tokens=vocab, special_tokens=["<pad>", "<unk>"])
encoded_2d = tok.batch_encode_2d([["A03C", "A03D"], ["A04A", "B035"]])
assert encoded_2d == [[5, 6], [7, 1]]
print(tok.batch_decode_2d(encoded_2d))
# [['A03C', 'A03D'], ['A04A', '<unk>']]
encoded_3d = tok.batch_encode_3d([[["A03C", "A03D"], ["A04A"]], [["B035"]]])
print(tok.batch_decode_3d(encoded_3d))
# [[['A03C', 'A03D'], ['A04A']], [['<unk>']]]
```

Decode a 3D encoding with `batch_decode_3d`, not `batch_decode_2d`. Padding is
removed by default; unknown tokens cannot be reconstructed. The reserved indices
are 0 and 1 only because the special-token order above specifies them. Fit/reuse a
training vocabulary; changing token order after loading weights invalidates the
embedding semantics. Normal dataset processors usually handle tokenization.

Sources: [MedCode](https://pyhealth.readthedocs.io/en/latest/api/medcode.html),
[Tokenizer](https://pyhealth.readthedocs.io/en/latest/api/tokenizer.html), and released
2.0.2 `medcode/utils.py`, `cross_map.py`, `inner_map.py`, `tokenizer.py`.
