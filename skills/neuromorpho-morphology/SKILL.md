---
name: neuromorpho-morphology
description: Find and compare digital neuron reconstructions on NeuroMorpho.Org through its public REST API, by brain region, cell type, species or lab archive; read their morphometry (length, surface, volume, branching, path distance); download standardized SWC files; and give the three citations NeuroMorpho requires. Use for questions about dendritic or axonal shape, or when someone needs real neuron morphologies for analysis or modeling.
license: MIT
compatibility: Python 3.9+ standard library only. Needs network access to neuromorpho.org; no credentials.
metadata:
  version: "1.0"
  skill-author: Wyatt Stanczyk
---

# Neuron morphology from NeuroMorpho.Org

NeuroMorpho.Org holds hundreds of thousands of traced neurons, each with metadata (species, region, cell type, lab, protocol) and standard morphometry computed the same way for every cell.

## When to Use

- Find reconstructions of a cell type in a region and species, such as rat CA1 pyramidal cells.
- Compare shape measures (total length, branching, path distance) across neurons or groups.
- Get SWC files for analysis or modeling, with the citations they require.

## Workflow

1. **Search** with `search(field, value, species=...)`. The API matches whole field values, so give one term: a region (`CA1`, `neocortex`), a cell type (`pyramidal`, `Purkinje`) or an archive (lab) name. Useful fields are `brain_region`, `cell_type`, `species` and `archive`. A search with no matches answers HTTP 404, which the helper returns as an empty result.
2. **Open a neuron** with `neuron(name)` for its metadata, and `morphometry(neuron_id)` for its measures.
3. **Compare fairly.** Check `domain` (the reconstructed parts) before comparing lengths: a neuron traced as "Dendrites, Soma, No Axon" can't be compared on axon length. Also check `protocol` (in vivo or in vitro), slice thickness and shrinkage correction, which change measured sizes.
4. **Download the standardized SWC** with `swc_url(neuron)` and analyze it (below), or with NeuroM or navis for full analysis.

## Examples

```python
import json, math, urllib.error, urllib.parse, urllib.request

API = "https://neuromorpho.org/api"

def _get(path):
    with urllib.request.urlopen(API + path, timeout=60) as r:
        return json.load(r)

def search(field, value, species=None, size=5):
    """Returns (total matches, neurons on the first page). NeuroMorpho answers 404 for no matches."""
    q = f"/neuron/select?q={field}:{urllib.parse.quote(value)}&size={size}&page=0"
    if species:
        q += f"&fq=species:{urllib.parse.quote(species.lower())}"
    try:
        page = _get(q)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return 0, []
        raise
    return page["page"]["totalElements"], page["_embedded"]["neuronResources"]

def neuron(name):
    return _get(f"/neuron/name/{urllib.parse.quote(name)}")

def morphometry(neuron_id):
    return _get(f"/morphometry/id/{neuron_id}")

def swc_url(n):
    archive = urllib.parse.quote(n["archive"].lower())
    return f"https://neuromorpho.org/dableFiles/{archive}/CNG%20version/{urllib.parse.quote(n['neuron_name'])}.CNG.swc"

total, found = search("brain_region", "CA1", species="rat")
print(total, [n["neuron_name"] for n in found])

n = neuron("n419")
m = morphometry(n["neuron_id"])
print(n["species"], n["brain_region"], n["cell_type"], n["domain"])
print("length", m["length"], "um; bifurcations", m["n_bifs"], "; max path", m["pathDistance"], "um")
print(swc_url(n))
```

SWC is plain text, one point per line: `id type x y z radius parent`. Type 1 is soma, 2 axon, 3 basal dendrite, 4 apical dendrite. The standardized (CNG) version has its soma at the origin and lengths in µm. Total dendritic length, no libraries needed:

```python
import math, urllib.request

url = "https://neuromorpho.org/dableFiles/turner/CNG%20version/n419.CNG.swc"
points = {}
for line in urllib.request.urlopen(url, timeout=60).read().decode().splitlines():
    if line.strip() and not line.startswith("#"):
        i, t, x, y, z, r, parent = line.split()[:7]
        points[int(i)] = (int(t), float(x), float(y), float(z), int(parent))

length = sum(
    math.dist(p[1:4], points[p[4]][1:4])
    for p in points.values()
    if p[4] in points and p[0] in (3, 4)
)
print(f"dendritic length: {length:.0f} um")
```

## Notes

- Be gentle with the API: one request per question, no bulk crawling. Use the archive's download pages for whole datasets.
- `png_url` in a neuron's metadata links a picture of the reconstruction.

## Licenses and credit

NeuroMorpho.Org content is CC BY 4.0. Its terms ask for all three of these whenever its material is used:

1. the original paper describing the reconstructions (from the neuron's `reference_doi` or `reference_pmid`)
2. NeuroMorpho.Org (RRID:SCR_002145)
3. Tecuatl C, Ljungquist B, Ascoli GA (2024) Accelerating the continuous community sharing of digital neuromorphology data. FASEB Bioadv. 6(7):207-221.

Pass all three on unchanged.
