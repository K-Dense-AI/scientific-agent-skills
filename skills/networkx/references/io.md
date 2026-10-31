# NetworkX Input/Output

API patterns assume `import networkx as nx`, suitable input files and the optional packages named below. See [review.md](review.md) for tested round trips. Preserve a separate node table, graph class, node-ID schema, units and attribute schema; compare them after every conversion. Edge tables alone omit isolated nodes.

## Reading Graphs from Files

### Adjacency List Format
```python
# Read adjacency list (simple text format)
G = nx.read_adjlist('graph.adjlist')

# With node type conversion
G = nx.read_adjlist('graph.adjlist', nodetype=int)

# For directed graphs
G = nx.read_adjlist('graph.adjlist', create_using=nx.DiGraph())

# Write adjacency list
nx.write_adjlist(G, 'graph.adjlist')
```

Example adjacency list format:
```
# node neighbors
0 1 2
1 0 3 4
2 0 3
3 1 2 4
4 1 3
```

### Edge List Format
```python
# Read edge list
G = nx.read_edgelist('graph.edgelist')

# With node types and edge data
G = nx.read_edgelist('graph.edgelist',
                     nodetype=int,
                     data=(('weight', float),))

# Read weighted edge list
G = nx.read_weighted_edgelist('weighted.edgelist')

# Write edge list
nx.write_edgelist(G, 'graph.edgelist')

# Write weighted edge list
nx.write_weighted_edgelist(G, 'weighted.edgelist')
```

Example edge list format:
```
# source target
0 1
1 2
2 3
3 0
```

Example weighted edge list:
```
# source target weight
0 1 0.5
1 2 1.0
2 3 0.75
```

### GML (Graph Modelling Language)
```python
# Read GML (supported GML attributes; default label="label")
G = nx.read_gml('graph.gml')

# Write GML
nx.write_gml(G, 'graph.gml')
```

GML is a text format, not XML. It supports a constrained attribute/type schema; reserved keys such as `id`/`label` have structural meanings. It is not an arbitrary Python-object round trip.

### GraphML Format
```python
# Read GraphML (XML-based format)
G = nx.read_graphml('graph.graphml')

# Write GraphML
nx.write_graphml(G, 'graph.graphml')

# With specific encoding
nx.write_graphml(G, 'graph.graphml', encoding='utf-8')
```

GraphML supports scalar strings, booleans and numeric attributes, not arbitrary lists/dicts/arrays/None. Node IDs are strings on read unless `node_type=` is specified. Use `force_multigraph=True` and an explicit `edge_key_type` to preserve a multigraph class with no parallel edges. GraphML defaults stay in `G.graph`; they are not filled into every node/edge. Mixed directed/undirected graphs and hyperedges are unsupported.

### GEXF (Graph Exchange XML Format)
```python
# Read GEXF
G = nx.read_gexf('graph.gexf')

# Write GEXF
nx.write_gexf(G, 'graph.gexf')
```

GEXF has reserved attribute names and requires compatible attribute types across nodes/edges; mixed types can raise. Validate dynamic attributes separately. GraphML/GEXF readers use XML parsers: only parse trusted files or sanitize XML before this workflow.

### Pajek Format
```python
# Read Pajek .net files
G = nx.read_pajek('graph.net')

# Write Pajek format
nx.write_pajek(G, 'graph.net')
```

### LEDA Format
```python
# Read LEDA format (read-only; NetworkX has no LEDA writer)
G = nx.read_leda('graph.leda')
```

## Working with Pandas

### From Pandas DataFrame
```python
import pandas as pd

# Create graph from edge list DataFrame
df = pd.DataFrame({
    'source': [1, 2, 3, 4],
    'target': [2, 3, 4, 1],
    'weight': [0.5, 1.0, 0.75, 0.25]
})

# Create graph
G = nx.from_pandas_edgelist(df,
                            source='source',
                            target='target',
                            edge_attr='weight')

# With multiple edge attributes: columns must actually exist
df["color"] = "blue"
df["type"] = "interaction"
G = nx.from_pandas_edgelist(df,
                            source='source',
                            target='target',
                            edge_attr=['weight', 'color', 'type'])

# Create directed graph
G = nx.from_pandas_edgelist(df,
                            source='source',
                            target='target',
                            edge_attr='weight',
                            create_using=nx.DiGraph())
```

Specify `create_using=nx.MultiDiGraph()` and `edge_key="edge_id"` when repeated directed observations are separate edges. Simple graphs overwrite duplicate edge attributes; they do not sum them. Import the node table with `add_nodes_from` to retain isolates and node attributes. Check ID dtypes and missing IDs before conversion, especially mixed numeric tables.

### To Pandas DataFrame
```python
# Convert graph to edge list DataFrame
df = nx.to_pandas_edgelist(G)

# Rename endpoint columns (this does not select edge attributes)
df = nx.to_pandas_edgelist(G, source='node1', target='node2')
```

### Adjacency Matrix with Pandas
```python
# Create DataFrame from adjacency matrix
df = nx.to_pandas_adjacency(G, dtype=float)

# Create graph from adjacency DataFrame
G = nx.from_pandas_adjacency(df)

# For directed graphs
G = nx.from_pandas_adjacency(df, create_using=nx.DiGraph())
```

## NumPy and SciPy Integration

### Adjacency Matrix
```python
import numpy as np

# Simple directed weighted fixture, including a zero-cost edge and an isolate
G = nx.DiGraph()
G.add_nodes_from(["A", "B", "isolate"])
G.add_edge("A", "B", weight=0.0)
nodelist = list(G)
A = nx.to_numpy_array(G, nodelist=nodelist, dtype=float, nonedge=np.nan)
# NetworkX 3.7 supports nonedge= on import too
H = nx.from_numpy_array(
    A, nodelist=nodelist, create_using=nx.DiGraph, nonedge=np.nan
)
assert H.has_edge("A", "B") and H["A"]["B"]["weight"] == 0.0
assert set(nx.isolates(H)) == {"isolate"}
```

Dense arrays default to zero meaning **no edge**; a different `nonedge` sentinel is needed for genuine zero-weight edges. `dtype=int` truncates fractional weights. Matrices omit most attributes and aggregate parallel weights (sum by default); integer entries become edge counts only with a multigraph plus `parallel_edges=True`. For directed graphs, row i / column j represents i -> j.

### Sparse Matrix (SciPy)
```python
from scipy import sparse

# Preserve ordering and directedness explicitly
nodelist = list(G)
A = nx.to_scipy_sparse_array(G, nodelist=nodelist, format="csr")
H = nx.from_scipy_sparse_array(A, create_using=type(G))
H = nx.relabel_nodes(H, dict(enumerate(nodelist)))
# Explicitly stored zeros become edges. Call A.eliminate_zeros() only
# when those entries really mean absent edges, not zero-weight edges.
```

## JSON Format

### Node-Link Format
```python
import json

# To node-link format (good for d3.js)
data = nx.node_link_data(G, edges="edges")
with open('graph.json', 'w') as f:
    json.dump(data, f)

# From node-link format
with open('graph.json', 'r') as f:
    data = json.load(f)
G = nx.node_link_graph(data, edges="edges")

# Since NetworkX 3.6 the edge list is stored under the "edges" key.
# Older files (and some d3.js examples) use "links" — pass edges="links"
# to read or write that layout:
legacy_data = nx.node_link_data(G, edges="links")
G = nx.node_link_graph(legacy_data, edges="links")
```

Node-link includes graph class flags, node records (including isolates), edge keys and attributes. JSON values must be serializable; attribute keys become strings. Reserve `id` for node IDs and `source`/`target`/`key` for edge structure, or choose noncolliding keyword names consistently for both directions. Do not feed an `edges` document to a `links` reader.

### Adjacency Data Format
```python
# To adjacency format
data = nx.adjacency_data(G)
with open('graph.json', 'w') as f:
    json.dump(data, f)

# From adjacency format
with open('graph.json', 'r') as f:
    data = json.load(f)
G = nx.adjacency_graph(data)
```

### Tree Data Format
```python
# Requires a directed outward tree rooted at root (not an arbitrary Graph)
T = nx.bfs_tree(nx.path_graph(4), source=0)
data = nx.tree_data(T, root=0)
with open('tree.json', 'w') as f:
    json.dump(data, f)

# From tree format
with open('tree.json', 'r') as f:
    data = json.load(f)
G = nx.tree_graph(data)
```

Tree JSON preserves node attributes but omits graph/edge attributes. Use node-link when those matter.

## Pickle Format

### Binary Pickle
```python
import pickle

# Write pickle (preserves all Python objects)
with open('graph.pkl', 'wb') as f:
    pickle.dump(G, f)

# Read pickle
with open('graph.pkl', 'rb') as f:
    G = pickle.load(f)
```

Note: `nx.write_gpickle` / `nx.read_gpickle` were removed in NetworkX 3.0 — use the standard `pickle` module as shown above. Only unpickle files from trusted sources; pickle can execute arbitrary code on load.

## CSV Files

### Custom CSV Reading
```python
import csv

# Read a simple undirected edge table; reject duplicate observations
import math
G = nx.Graph()
with open("edges.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)) or not {"source", "target", "weight"} <= set(fields):
        raise ValueError("Missing or duplicate CSV headers")
    for row in reader:
        u, v = row["source"], row["target"]
        if None in row or not u or not v or row["weight"] is None:
            raise ValueError("Malformed edge record")
        if G.has_edge(u, v):
            raise ValueError("Repeated edge: choose aggregation or a multigraph explicitly")
        weight = float(row["weight"])
        if not math.isfinite(weight):
            raise ValueError("Nonfinite weight")
        G.add_edge(u, v, weight=weight)

# Write edges to CSV
with open('edges.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['source', 'target', 'weight'])
    for u, v, data in G.edges(data=True):
        writer.writerow([u, v, data['weight']])
```

## Database Integration

### SQL Databases
```python
import sqlite3
import pandas as pd

# Read from SQL database via pandas
conn = sqlite3.connect('network.db')
df = pd.read_sql_query("SELECT source, target, weight FROM edges", conn)
G = nx.from_pandas_edgelist(df, 'source', 'target', edge_attr='weight')
conn.close()

# When filtering on user-supplied values, always use parameterized queries —
# never interpolate user input into the SQL string:
conn = sqlite3.connect('network.db')
df = pd.read_sql_query(
    "SELECT source, target, weight FROM edges WHERE weight > ?",
    conn, params=(min_weight,)
)
G = nx.from_pandas_edgelist(df, "source", "target", edge_attr="weight")
conn.close()

# Write to SQL database
df = nx.to_pandas_edgelist(G)
conn = sqlite3.connect('network.db')
df.to_sql('edges', conn, if_exists='replace', index=False)
conn.close()
```

## Graph Formats for Visualization

### DOT Format (Graphviz)
```python
# Write DOT file for Graphviz
nx.drawing.nx_pydot.write_dot(G, 'graph.dot')

# Read DOT file
G = nx.drawing.nx_pydot.read_dot('graph.dot')

# Generate directly to image (requires pydot and the Graphviz executable)
from networkx.drawing.nx_pydot import to_pydot
pydot_graph = to_pydot(G)
pydot_graph.write_png('graph.png')
```

## Cytoscape Integration

### Cytoscape JSON
```python
# Export for Cytoscape
data = nx.cytoscape_data(G)
with open('cytoscape.json', 'w') as f:
    json.dump(data, f)

# Import from Cytoscape
with open('cytoscape.json', 'r') as f:
    data = json.load(f)
G = nx.cytoscape_graph(data)
```

## Specialized Formats

### Matrix Market Format
```python
from scipy.io import mmread, mmwrite

# Read Matrix Market
A = mmread('graph.mtx', spmatrix=False)
G = nx.from_scipy_sparse_array(A) if sparse.issparse(A) else nx.from_numpy_array(A)

# Write Matrix Market
A = nx.to_scipy_sparse_array(G)
mmwrite('graph.mtx', A)
```

### Geographic Networks (Shapefiles, GeoDataFrames)
`nx.read_shp` / `nx.write_shp` were removed in NetworkX 3.0. Use GeoPandas with momepy (or osmnx for street networks) instead:
```python
# uv pip install geopandas momepy
import geopandas as gpd
import momepy

# Read line geometries from a shapefile and convert to a graph
gdf = gpd.read_file('roads.shp')
# Choose an appropriate projected CRS; lengths are in its axis units
if gdf.crs is None or not gdf.crs.is_projected:
    raise ValueError("Reproject roads to an appropriate local projected CRS first")
G = momepy.gdf_to_nx(gdf, approach="primal", preserve_index=True)

# Convert back to GeoDataFrames
nodes_gdf, edges_gdf = momepy.nx_to_gdf(G)
```

This momepy route uses pre-noded LineStrings: crossings are not automatically intersections. It defaults to an undirected MultiGraph and stores segment length as `mm_len` in CRS units. For directed networks, coordinate order sets direction; use the documented `oneway_column` semantics. Geometry and tuple node IDs need conversion before GraphML export.

## Format Selection Guidelines

### Choose Based on Requirements

**Adjacency List** - Simple, human-readable, no attributes
- Best for: Simple unweighted graphs, quick viewing

**Edge List** - Simple, supports weights, human-readable; isolates/node metadata need a sidecar
- Best for: Weighted graphs, importing/exporting data

**GML/GraphML** - Typed text formats; GraphML is XML, GML is not
- Best for: Interchange of supported scalar attributes after a schema/identity round-trip check

**JSON** - Web-friendly, JavaScript integration
- Best for: Web applications, d3.js visualizations

**Pickle** - Fast, preserves Python objects, binary
- Best for: Python-only storage, complex attributes

**Pandas** - Data analysis integration, DataFrame operations
- Best for: Data processing pipelines, statistical analysis

**NumPy/SciPy** - Numerical computation, sparse matrices
- Best for: Matrix operations, scientific computing

**DOT** - Visualization, Graphviz integration
- Best for: Creating visual diagrams

## Performance Considerations

### Large Graphs
For large graphs, consider:
```python
# Use compressed formats
# NetworkX handles compression from the suffix; file handles must be binary
nx.write_adjlist(G, "graph.adjlist.gz")
H = nx.read_adjlist("graph.adjlist.gz")

# Use binary formats (faster than text formats)
with open('graph.pkl', 'wb') as f:
    pickle.dump(G, f)

# Use sparse matrices for adjacency
A = nx.to_scipy_sparse_array(G, format='csr')  # Memory efficient
```

### Incremental Loading
Linewise parsing reduces temporary input storage, but the final NetworkX graph still resides in memory. This two-column pattern does not preserve attributes or isolates:
```python
# Load graph incrementally from edge list
G = nx.Graph()
with open('huge_graph.edgelist') as f:
    for line in f:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        u, v = line.strip().split()
        G.add_edge(u, v)

        # Progress only; this does not free a chunk
        if G.number_of_edges() % 100000 == 0:
            print(f"Loaded {G.number_of_edges()} edges")
```

## Error Handling

### Robust File Reading
```python
try:
    G = nx.read_graphml('graph.graphml')
except nx.NetworkXError as e:
    print(f"Error reading GraphML: {e}")
except FileNotFoundError:
    raise  # A missing file is not evidence of an empty network

# Illustrative input inspection: parsing errors may include XML/type errors
import os
if os.path.exists('graph.txt'):
    with open('graph.txt') as f:
        first_line = f.readline()
        # Detect format and read accordingly
```
