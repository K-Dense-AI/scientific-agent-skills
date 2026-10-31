# Release and verification notes

Reviewed 2026-10-01. Live [PyPI metadata](https://pypi.org/pypi/torch-geometric/json) reports `torch-geometric 2.8.0.post1`, Python >=3.10. The [2.8 release](https://github.com/pyg-team/pytorch_geometric/releases/tag/2.8.0) drops Torch 2.8 and consolidates spatial operators into `pyg-lib`; its published compatibility table covers Torch 2.9–2.12. Rolling docs identify 2.9.0, so these recipes were also checked against the installed released source, not inferred solely from `latest` docs.

## Executed CPU coverage

The tested macOS ARM stack is Python 3.13, Torch 2.14.1, PyG 2.8.0.post1, Captum 0.9.0, Lightning 2.6.6, NetworkX 3.7, pandas 3.0.6 and scikit-learn 1.9.1. Optional actual sampling used `pyg-lib 0.9.0+pt214` from the [official Torch 2.14 CPU wheel page](https://data.pyg.org/whl/torch-2.14.0+cpu.html). This page lists a Python >=3.10 ABI3 macOS ARM wheel. The index currently lists newer Torch builds than the release note table. Core compatibility and this one CPU backend were exercised; other OS, Python, CUDA and extension combinations were not.

The repository suite runs small native tests using definitions extracted from these Markdown examples, with synthetic graph fixtures:

- Node forward/backward, graph batching/pooling and isolated-node offsets.
- Custom GCN parity with native GCN, including an existing self-loop and an empty edge set; source-to-target messages; EdgeConv.
- GAT/GATv2/GIN/GraphSAGE/Transformer/RGCN and high-level model shapes, explicit RGCN relation IDs, feature normalization and transforms.
- RandomLinkSplit positive/reverse partitions, disjoint training supervision, validation/train-plus-validation message semantics and known-positive negative exclusion.
- Binary encoder loss, GAE positive/negative column slicing, GAE AUC/AP, VGAE output and KL shapes.
- `to_hetero`, bipartite GAT skip connections, HeteroConv and HGT; paired heterogeneous reverse-edge splitting.
- CSV ID alignment, duplicate/unknown/null endpoint rejection, empty `[2,0]` long edge tensors and stable categorical vocabularies.
- InMemoryDataset and tensor-only disk cache round trips, filter indexing and missing-file detection; NetworkX/sparse conversion, zero-weight edges and isolates.
- Actual NeighborLoader seed order and local/global IDs, LinkNeighborLoader relabeling, k-NN batch isolation and dynamic EdgeConv (optional backend tests).
- GNNExplainer, PGExplainer, AttentionExplainer, heterogeneous Captum output selection, metrics and PNG output paths.
- Current Lightning namespace/full loader and `torch.compile(backend='eager')` parity. This capture test does not test optimizing compiler performance.

Small random-label/short-epoch tests establish API/tensor mechanics only. They do not show learned scientific signal, stable explanations, predictive calibration, or generalization.

## Dataset and download contracts

These are SDK-managed public file downloads, not authenticated REST query endpoints. There is no query pagination or bearer-token contract to invent. Public loader execution completed for Cora and ENZYMES; all other locations below were checked in released dataset source but the large or restricted data were not downloaded. Preserve upstream license, source identity, preprocessing, checksum and split in real studies.

| API | Released download contract | Verification |
| --- | --- | --- |
| `Planetoid(..., name='Cora', split='public')` | Eight `ind.cora.*` files under `https://github.com/kimiyoung/planetoid/raw/master/data`; `geom-gcn` mode separately fetches split NPZ files from `graphdml-uiuc-jlu/geom-gcn` | Native download/process: 2,708 nodes, 10,556 directed entries, 1,433 features, 7 classes; public masks loaded. |
| `TUDataset(..., name='ENZYMES')` | `https://www.chrsmrrs.com/graphkerneldatasets/ENZYMES.zip`; `cleaned=True` uses `https://raw.githubusercontent.com/nd7141/graph_datasets/master/datasets` instead | Native download/process: 600 graphs, 3 default node-label features, 6 classes. Continuous node/edge attributes require `use_node_attr`/`use_edge_attr`. |
| `QM7b` | `https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/qm7b.mat` | Source-checked; PyG class is QM7b, not QM7. |
| `QM9` | DeepChem S3 `datasets/molnet_publish/qm9.zip`, Figshare file `3195404`; without RDKit, `https://data.pyg.org/datasets/qm9_v3.zip` | Source-checked; RDKit changes the processing path. |
| `MoleculeNet` | DeepChem S3 `datasets/{filename}` selected from the released class's `names` map | Source-checked; task-specific targets may contain NaN/missing labels. |
| `ShapeNet` | `https://shapenet.cs.stanford.edu/media/shapenetcore_partanno_segmentation_benchmark_v0_normal.zip` | Source-checked; k-NN preprocessing additionally needs pyg-lib. |
| `ModelNet(name='10'/'40')` | `http://3dvision.princeton.edu/projects/2014/3DShapeNets/ModelNet10.zip` / `http://modelnet.cs.princeton.edu/ModelNet40.zip` | Source-checked legacy HTTP URLs; availability/redirects untested. No silent replacement mirror. |
| `FAUST` | Released loader points to `http://faust.is.tue.mpg.de/` and requires a manually supplied registered dataset | Source-checked; it does not auto-download. |
| `OGB_MAG` | `http://snap.stanford.edu/ogb/data/nodeproppred/mag.zip`; optional `https://data.pyg.org/datasets/mag_metapath2vec_emb.zip` or `mag_transe_emb.zip` | Source-checked only; large download and embedding provenance remain user workflow requirements. |

Other OGB names in the overview are benchmark identifiers, not PyG dataset class constructors. Use the [official OGB graph property](https://ogb.stanford.edu/docs/graphprop/), [node property](https://ogb.stanford.edu/docs/nodeprop/) and [link property](https://ogb.stanford.edu/docs/linkprop/) APIs and their official evaluators/splits. Optional SentenceTransformer text encoding was checked against current [SDK documentation](https://sbert.net/docs/package_reference/sentence_transformer/model.html); a tiny locally constructed bag-of-words model also exercised `encode(convert_to_tensor=True).cpu()` with shape `[2,2]`. Pretrained MiniLM weights were not downloaded or run.

## Remaining execution boundaries

`torch-sparse` HGTLoader/GraphSAINT/ShaDow, multi-process CUDA DDP/AMP, and optimized compile backends are illustrative/source-verified, not executed. ClusterData's backend requirements must be checked on the deployment machine. The DDP example replicates graph storage and uses equal per-rank seed counts; it is not a distributed graph database. Model-choice guidance expresses assumptions, not a promise that one architecture is scientifically best.

Core sources: [installation](https://pytorch-geometric.readthedocs.io/en/latest/install/installation.html), [loaders](https://pytorch-geometric.readthedocs.io/en/latest/modules/loader.html), [heterogeneous graphs](https://pytorch-geometric.readthedocs.io/en/latest/tutorial/heterogeneous.html), [datasets](https://pytorch-geometric.readthedocs.io/en/latest/modules/datasets.html), [explainability](https://pytorch-geometric.readthedocs.io/en/latest/modules/explain.html). Topic-specific references link exact APIs.
