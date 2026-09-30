# Expected output — SORT1 minor salivary gland ge-eQTL slice

Input: `examples/input.json` — fetches a 1 Mb window around SORT1 from the
GTEx minor salivary gland ge-eQTL dataset (QTD000276).

## What you get

`RegionResult` dataclass with:

- `n_variants`: ~3000 variants (window-dependent; varies slightly per release)
- `release`:
  - `study_label`: `GTEx`
  - `tissue_label`: `minor salivary gland`
  - `quant_method`: `ge`
  - `dataset_release`: `v7+` (current eQTL Cat release)
- `variants`: list of `RegionVariant` rows in canonical schema:
  ```
  variant_id        chromosome  position    ref  alt  beta      se      p_value     maf     molecular_trait_id  dataset_id
  1_108774968_G_A   1           108774968   G    A    0.0123   0.045   0.78        0.12    ENSG00000134243     QTD000276
  ...
  1_109274968_G_T   1           109274968   G    T    0.6027   0.078   8.4e-15     0.31    ENSG00000134243     QTD000276
  ...
  ```

## What you should NOT see

- Variants for genes other than ENSG00000134243 (the `molecular_trait_id`
  filter restricts to SORT1).
- Variants outside [108774968, 109774968] (the tabix-fetched window).
- Variants with missing beta / SE / p (the fetcher drops these on harmonisation).

## Reproducing

```bash
bash run_example.sh
```

Network required (~1-5 MB tabix fetch from EBI eQTL Catalogue FTP).
