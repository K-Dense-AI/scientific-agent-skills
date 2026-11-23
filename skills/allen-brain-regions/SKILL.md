---
name: allen-brain-regions
description: Look up and standardize brain region names with the Allen Institute's structure ontology (the adult mouse CCFv3 regions, plus the human and developing mouse atlases) through the public Allen Brain Map API, and pick a BrainGlobe reference atlas. Use when matching region names across datasets or papers, finding a region's acronym, numeric id or parent regions, checking whether two labels overlap, or choosing an atlas for registration.
license: MIT
compatibility: Python 3.9+ standard library only for the lookups. Needs network access to api.brain-map.org and brainglobe.s3.us-west-2.amazonaws.com; no credentials. The optional atlas example needs brainglobe-atlasapi.
metadata:
  version: "1.0"
  skill-author: Wyatt Stanczyk
---

# Allen brain regions and atlases

Labs write the same region many ways: "CA1", "field CA1", "hippocampal CA1", "Field CA1 of hippocampus". The Allen ontology gives each region one acronym, one numeric id and a place in a hierarchy, so data from different sources can be lined up.

## When to Use

- Normalize region labels from several datasets or papers to one vocabulary.
- Find a region's acronym, id, full name, atlas color or parent chain.
- Decide whether two labels overlap (one contains the other) or are distinct.
- Choose a BrainGlobe atlas for registration or for drawing region masks.

## Workflow

1. **Pick the structure graph.** `1` is the adult mouse brain (the CCFv3 regions), `10` the human brain, `17` the developing mouse brain. Human names differ from mouse ones; try adjectives like `hippocampal` if a noun finds nothing.
2. **Look up the region** with `find_region` below: an exact acronym first (`CA1`, `VISp`, `MOs`), then names containing the text (`primary visual`). Each result has the acronym, name, id, color and the chain of parents, such as `root > grey > CH > CTX > CTXpl > HPF > HIP > CA > CA1`.
3. **Compare labels with the parent chain.** A dataset labeled `HPF` (hippocampal formation) contains CA1, CA3, DG and more. Say that one label contains the other rather than treating them as the same region.
4. **Choose an atlas** with `list_atlases`: BrainGlobe's atlases for mouse, rat, human, zebrafish and others, with their current versions.

## Examples

```python
import json, re, urllib.parse, urllib.request

ALLEN = "https://api.brain-map.org/api/v2/data/query.json?criteria="

def _allen(criteria):
    url = ALLEN + urllib.parse.quote(criteria, safe="[]$:,'*=")
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)["msg"]

def find_region(term, graph_id=1, limit=5):
    """Exact acronym match first, then names containing the term, shallowest first."""
    term = re.sub(r"[^\w ,.()/-]", "", term).strip()[:80]  # keep the query's quotes intact
    base = f"model::Structure,rma::criteria,[graph_id$eq{graph_id}]"
    opts = f",rma::options[num_rows$eq{limit}][order$eq'depth']"
    rows = _allen(f"{base},[acronym$il'{term}']{opts}") or _allen(f"{base},[name$il'*{term}*']{opts}")
    ids = {int(i) for r in rows for i in r["structure_id_path"].strip("/").split("/")}
    parents = {}
    if ids:
        found = _allen(f"model::Structure,rma::criteria,[id$in{','.join(map(str, ids))}],rma::options[num_rows$eq{len(ids)}]")
        parents = {p["id"]: p["acronym"] for p in found}
    return [{
        "acronym": r["acronym"], "name": r["name"], "id": r["id"],
        "color": "#" + r["color_hex_triplet"],
        "path": " > ".join(parents.get(int(i), "?") for i in r["structure_id_path"].strip("/").split("/")),
    } for r in rows]

def list_atlases(*words):
    """BrainGlobe atlases whose names contain every word, with their latest version."""
    url = "https://brainglobe.s3.us-west-2.amazonaws.com/atlas/atlases/last_versions.conf"
    with urllib.request.urlopen(url, timeout=30) as r:
        text = r.read().decode()
    pairs = re.findall(r"^\s*([\w.-]+)\s*=\s*([\d.]+)\s*$", text, re.M)
    return [(n, v) for n, v in pairs if all(w.lower() in n.lower() for w in words)]

print(find_region("CA1")[0])
print(find_region("primary visual")[0]["acronym"])
print(list_atlases("allen_mouse"))  # [("allen_mouse_100um", "3.1"), ...]
```

Using an atlas once chosen (illustrative; needs `pip install brainglobe-atlasapi`, which downloads the atlas on first use):

```python
from brainglobe_atlasapi import BrainGlobeAtlas

atlas = BrainGlobeAtlas("allen_mouse_25um")
ca1 = atlas.structures["CA1"]              # same acronym and id as the Allen ontology
mask = atlas.get_structure_mask("CA1")     # 3D boolean volume in atlas space
```

## Notes

- `$il` is a case-insensitive match in the Allen query language; `*` is a wildcard. Keep terms to letters, numbers and simple punctuation so they can't break the single-quoted value.
- The Allen API returns at most `num_rows` rows; raise `limit` for broad terms.

## Licenses and credit

- Allen Institute content may be used for research and other noncommercial purposes only, derivative works included. Flag this if the user's use could be commercial, and credit the Allen Institute as its citation policy asks (alleninstitute.org/citation-policy).
- For mouse regions, cite the CCFv3 paper: Wang Q, Ding SL, Li Y, et al. (2020) The Allen Mouse Brain Common Coordinate Framework: A 3D Reference Atlas. Cell 181(4):936-953.
- Each BrainGlobe atlas has its own citation in its metadata; cite BrainGlobe too (Claudi F, et al. (2020) BrainGlobe Atlas API. JOSS 5(54):2668).
