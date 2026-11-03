#!/usr/bin/env bash
# Example invocation: SORT1 minor salivary gland ge-eQTL slice.
# Network required (~1-5 MB tabix fetch from EBI eQTL Catalogue FTP).

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -c "
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path('${DIR}').parent))

from eqtl_catalogue_region_fetch import EQTLCatalogueClient

with open('${DIR}/input.json') as f:
    cfg = json.load(f)

client = EQTLCatalogueClient()
result = client.fetch_region(
    dataset_id=cfg['dataset_id'],
    molecular_trait_id=cfg.get('molecular_trait_id'),
    chromosome=cfg['chromosome'],
    start_bp=cfg['start_bp'],
    end_bp=cfg['end_bp'],
)
print(f'n_variants: {result.n_variants}')
print(f'release.study_label: {result.release.study_label}')
print(f'release.tissue_label: {result.release.tissue_label}')
print(f'release.quant_method: {result.release.quant_method}')
print(f'first 3 variants:')
for v in result.variants[:3]:
    print(f'  {v.variant_id}\\tbeta={v.beta:.4f}\\tse={v.se:.4f}\\tp={v.p_value:.2e}')
"
