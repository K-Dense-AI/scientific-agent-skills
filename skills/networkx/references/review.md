# NetworkX 3.7 review and validation

Reviewed 2026-10-01 against the released NetworkX 3.7 wheel and official stable
reference, not the development `latest` documentation. Python requires >=3.12
and excludes 3.14.1. Record the installed version in each analysis.

## Executed scope

The repository suite `tests/networkx/test_examples.py` executes documentation
recipes against synthetic graphs and temporary files. Its checks cover:

- Weighted route/length agreement, inward directed closeness, connectivity
  preconditions, matching cardinality versus weight, flows, traversal, induced
  subgraph matching, clustering, centrality and community objectives.
- All generator code blocks, including degree-sequence preservation before
  simplification, current bipartite keywords and ordered-DAG isolate retention.
- Dense/sparse zero-weight edges, labels and directedness; parallel-edge keys
  and isolates through node-link JSON; GraphML types; GML/GEXF/Pajek topology;
  adjacency/tree/Cytoscape JSON; CSV rejection cases; compressed adjacency
  lists; local SQL and dense/sparse Matrix Market input.
- Matplotlib drawing blocks with a noninteractive backend, Plotly figure schema,
  standalone PyVis HTML without browser launch or mutation of the source graph,
  and a synthetic projected GeoPandas/momepy shapefile round trip.

Test stack: Python 3.13.3, NetworkX 3.7, NumPy 2.5.3, SciPy 1.18.1,
pandas 3.0.6, Matplotlib 3.11.2, Plotly 7.1.0, PyVis 0.3.2,
GeoPandas 1.2.0 and momepy 1.0.0. Run from the repository:

```bash
python tests/run_all.py --isolated networkx
```

The audit also resolved every referenced NetworkX symbol (excluding names
explicitly described as removed) and bound every documented NetworkX function
call against released signatures. Signature checks do not prove runtime behavior
for arbitrary data, graph classes or backends.

## Scientific and interoperability limits

Reference snippets are illustrative API patterns where they need user files,
preexisting graph variables or optional engines; they are not one sequential
program. Graphviz/pydot/pygraphviz rendering, LEDA input, accelerated backends and
interactive browser/notebook behavior were documentation-reviewed only. No
large empirical network or scientific null-ensemble inference was performed.
Numerical/serialization tests establish these local contracts, not biological,
social, causal or predictive validity.

- A weight called `weight` is not inherently a distance. Explicitly select
  cost/distance versus transition/interaction strength and validate missing,
  zero, negative and nonfinite values for the chosen method.
- Degree-preserving null graphs require preservation of the relevant graph
  class and constraints. A simple projection of a configuration multigraph
  changes its degrees. Seeded outputs do not establish unbiased sampling,
  adequate mixing, community significance or a fitted power-law distribution.
- Conversion success does not imply complete preservation. Save node order,
  isolates, IDs, graph class, multiedge keys and supported attribute schemas;
  check them after a round trip. A matrix typically sums parallel weights.
- A projected CRS can use feet or other units. momepy lengths use those units;
  projection suitability and a conversion to metres are separate decisions.
- Layout coordinates, marker size and color are presentation choices. Keep
  seeds, weight semantics, legends and mappings with the output.

## Official sources

- [NetworkX 3.7 release notes](https://networkx.org/documentation/stable/release/release_3.7.html):
  native Leiden, BFS-predecessor deprecation, Python changes and sparse-zero notes.
- [Current reference](https://networkx.org/documentation/stable/reference/index.html)
  and [graph classes](https://networkx.org/documentation/stable/reference/classes/index.html):
  graph types, views, attributes, degree and multiedge semantics.
- [Betweenness](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.centrality.betweenness_centrality.html),
  [closeness](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.centrality.closeness_centrality.html),
  [matching](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.matching.max_weight_matching.html)
  and [Leiden](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.leiden.leiden_communities.html):
  distance direction, approximation, objectives and return types.
- [Configuration model](https://networkx.org/documentation/stable/reference/generated/networkx.generators.degree_seq.configuration_model.html):
  multigraph degree and simplification contract.
- [Dense conversion](https://networkx.org/documentation/stable/reference/generated/networkx.convert_matrix.from_numpy_array.html),
  [sparse conversion](https://networkx.org/documentation/stable/reference/generated/networkx.convert_matrix.from_scipy_sparse_array.html),
  [node-link JSON](https://networkx.org/documentation/stable/reference/readwrite/generated/networkx.readwrite.json_graph.node_link_data.html)
  and [GraphML writer](https://networkx.org/documentation/stable/reference/readwrite/generated/networkx.readwrite.graphml.write_graphml.html):
  nonedge sentinel, explicit zeros, field names and supported interchange.
- [SciPy Matrix Market reader](https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.mmread.html):
  explicit sparse-array output and dense/sparse dispatch.
- [Spring layout](https://networkx.org/documentation/stable/reference/generated/networkx.drawing.layout.spring_layout.html)
  and [backends](https://networkx.org/documentation/stable/reference/backends.html):
  automatic method selection, weight semantics and dispatch limits.
- [Plotly network graphs](https://plotly.com/python/network-graphs/),
  [PyVis API](https://pyvis.readthedocs.io/en/latest/documentation.html),
  [momepy graph import](https://docs.momepy.org/stable/api/momepy.gdf_to_nx.html)
  and [graph export](https://docs.momepy.org/stable/api/momepy.nx_to_gdf.html):
  current optional-integration contracts, with released-wheel runtime checks.
