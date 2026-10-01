"""Execute the maintained documentation recipes on bounded synthetic graphs."""
from copy import deepcopy
import json
from pathlib import Path
import re
import textwrap

import pytest

nx = pytest.importorskip("networkx", minversion="3.7")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "networkx"


def blocks(relative):
    return [textwrap.dedent(s) for s in re.findall(
        r"```python\n(.*?)```", (SKILL_ROOT / relative).read_text(), re.S
    )]


def recipe(relative, marker, **context):
    code, = [s for s in blocks(relative) if marker in s]
    scope = {"nx": nx, **context}
    exec(compile(code, str(SKILL_ROOT / relative), "exec"), scope)
    return scope


def weighted_graph():
    graph = nx.path_graph(range(1, 6))
    nx.set_edge_attributes(graph, 1.0, "weight")
    nx.set_edge_attributes(graph, 1.0, "distance")
    nx.set_edge_attributes(graph, 1.0, "strength")
    nx.set_edge_attributes(graph, 3, "capacity")
    return graph


def test_weighted_route_matches_reported_length():
    result = recipe("SKILL.md", "# Same distance model")
    assert result["length"] == nx.path_weight(result["G"], result["path"], "distance")
    assert nx.shortest_path(result["G"], 1, 5) != result["path"]


def test_parallel_edge_keys_and_shallow_copy_semantics():
    result = recipe("references/graph-basics.md", 'key="replicate-1"')
    graph = result["M"]
    assert graph.is_directed() and graph.is_multigraph()
    assert graph["A"]["B"]["replicate-2"]["strength"] == 3
    graph.nodes["A"]["observations"] = [1]
    copied = graph.subgraph(["A", "B"]).copy()
    copied.nodes["A"]["observations"].append(2)
    assert graph.nodes["A"]["observations"] == [1, 2]
    copied.add_node("C")
    assert "C" not in graph


def test_reverse_is_view_and_closeness_is_inward():
    graph = nx.DiGraph([(1, 2), (2, 3)])
    nx.set_edge_attributes(graph, 1, "distance")
    inward = nx.closeness_centrality(graph, distance="distance")
    reverse = graph.reverse(copy=False)
    outward = nx.closeness_centrality(reverse, distance="distance")
    assert inward[1] == 0 and outward[3] == 0
    assert inward[3] == outward[1] > 0
    graph.add_edge(3, 4)
    assert reverse.has_edge(4, 3)


ALGORITHM_MARKERS = [
    "# Dijkstra:", "# Floyd-Warshall", "# A* algorithm", "# Check if connected",
    "# Minimum node/edge cut", "# Fraction of shortest paths", "# Reciprocal",
    "# Centrality based", "# Google's", "# Clustering coefficient",
    "# Overall clustering", "# Count triangles", "# Greedy modularity",
    "communities = community.leiden_communities", "# Fast community",
    "# Hierarchical community", "# Approximate weighted vertex", "# Kruskal",
    "# Check if graph is tree", "# Maximum flow value", "# Minimum cost flow",
    "# All maximal cliques", "# Greedy coloring", "# Check if graphs are isomorphic",
    "# Search for an induced", "# DFS edges", "# BFS edges",
]


@pytest.mark.parametrize("marker", ALGORITHM_MARKERS)
def test_algorithm_recipes(marker):
    pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    graph = weighted_graph()
    result = recipe(
        "references/algorithms.md", marker, G=graph,
        G1=nx.path_graph(5), G2=nx.path_graph(3),
        community=nx.community, isomorphism=nx.isomorphism,
        process=lambda tree: None,
    )
    if marker == "# Floyd-Warshall":
        assert result["lengths"][1][5] == 4
    elif marker == "# BFS edges":
        assert result["bfs_pred"] == {2: 1, 3: 2, 4: 3, 5: 4}
    elif marker == "# Search for an induced":
        assert result["is_subgraph_iso"]
    elif marker == "# Maximum flow value":
        assert result["flow_value"] == result["cut_value"] == 3
    elif marker == "# Google's":
        assert sum(result["pagerank"].values()) == pytest.approx(1)


def test_maximum_cardinality_differs_from_maximum_weight():
    graph = nx.Graph()
    graph.add_weighted_edges_from([(1, 2, 1), (2, 3, 100), (3, 4, 1)])
    assert len(nx.max_weight_matching(graph)) == 1
    result = recipe("references/algorithms.md", "# Maximum cardinality,", G=graph)
    assert len(result["matching"]) == 2 and result["is_perfect"]


def test_directed_connectivity_recipe():
    graph = nx.DiGraph([(1, 2), (2, 3)])
    result = recipe("references/algorithms.md", "# Strong connectivity", G=graph)
    assert result["is_weakly_connected"] and not result["is_strongly_connected"]
    with pytest.raises(nx.NetworkXError):
        nx.average_shortest_path_length(graph)


def test_null_and_disconnected_graph_contracts():
    with pytest.raises(nx.NetworkXPointlessConcept):
        nx.is_connected(nx.Graph())
    result = recipe("references/algorithms.md", "# All maximal cliques", G=nx.Graph())
    assert result["clique_number"] == 0
    forest = nx.minimum_spanning_tree(nx.Graph([(1, 2), (3, 4)]))
    assert nx.is_forest(forest) and not nx.is_tree(forest)


def test_generators_and_null_model_degree_contracts():
    context = dict(nx=nx, G=nx.path_graph(4), G1=nx.path_graph(3), G2=nx.path_graph(range(3, 6)),
                   degree_sequence=[3, 3, 2, 2, 2, 2], in_sequence=[2, 2, 2, 1, 1],
                   out_sequence=[2, 2, 1, 2, 1])
    for code in blocks("references/generators.md"):
        scope = context.copy()
        exec(compile(code, "generators.md", "exec"), scope)
        assert isinstance(scope["G"], nx.Graph)
    graph = nx.configuration_model([3, 3, 2, 2, 2, 2], seed=42)
    simple = nx.Graph(graph)
    simple.remove_edges_from(list(nx.selfloop_edges(simple)))
    assert list(dict(graph.degree()).values()) != list(dict(simple.degree()).values())
    result = recipe("references/generators.md", "# Ordered random DAG")
    assert set(result["G"]) == set(range(20))


def test_dense_and_sparse_roundtrips_keep_zero_edge_direction_and_isolate():
    pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    dense = recipe("references/io.md", "# Simple directed weighted fixture")
    sparse = recipe("references/io.md", "# Preserve ordering and directedness", G=dense["G"])
    graph = sparse["H"]
    assert set(graph) == {"A", "B", "isolate"}
    assert graph.has_edge("A", "B") and not graph.has_edge("B", "A")
    assert graph["A"]["B"]["weight"] == 0


def test_node_link_schemas_preserve_parallel_keys_and_isolates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    graph = nx.MultiDiGraph(name="test")
    graph.add_node("isolate", kind="control")
    graph.add_edge("A", "B", key="first", weight=2)
    graph.add_edge("A", "B", key="second", weight=3)
    result = recipe("references/io.md", "# To node-link format", G=graph)
    assert nx.utils.graphs_equal(graph, result["G"])
    assert "edges" in json.loads((tmp_path / "graph.json").read_text())
    assert "links" in result["legacy_data"]


def test_graphml_typed_ids_and_restricted_attributes(tmp_path):
    pytest.importorskip("numpy")
    graph = nx.MultiDiGraph()
    graph.add_node(7, control=True)
    graph.add_edge(1, 2, key="a", strength=0.5)
    path = tmp_path / "graph.graphml"
    nx.write_graphml(graph, path)
    restored = nx.read_graphml(path, node_type=int, edge_key_type=str, force_multigraph=True)
    assert set(restored) == {1, 2, 7}
    assert restored[1][2]["a"]["strength"] == 0.5
    graph.nodes[7]["unsupported"] = [1, 2]
    with pytest.raises((TypeError, nx.NetworkXError)):
        nx.write_graphml(graph, path)


def test_tree_json_is_directed_and_drops_edge_attributes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = recipe("references/io.md", "# Requires a directed outward tree", json=json)
    assert nx.is_arborescence(result["G"])
    tree = result["T"]
    tree[0][1]["weight"] = 5
    restored = nx.tree_graph(nx.tree_data(tree, root=0))
    assert "weight" not in restored[0][1]


def test_pandas_attributes_and_duplicate_edge_contracts():
    pd = pytest.importorskip("pandas")
    result = recipe("references/io.md", "# Create graph from edge list DataFrame")
    assert result["G"].is_directed() and len(result["G"]) == 4
    table = pd.DataFrame({"source": ["A", "A"], "target": ["B", "B"], "weight": [1., 2.]})
    simple = nx.from_pandas_edgelist(table, edge_attr="weight")
    multi = nx.from_pandas_edgelist(table, edge_attr="weight", create_using=nx.MultiGraph)
    assert simple["A"]["B"]["weight"] == 2 and multi.number_of_edges() == 2


@pytest.mark.parametrize("contents,valid", [
    ("source,target,weight\nA,B,0.5\n", True),
    ("source,target,weight,weight\nA,B,1,2\n", False),
    ("source,target,weight\nA,B,1\nB,A,2\n", False),
    ("source,target,weight\nA,B,NaN\n", False),
    ("source,target,weight\n,B,2\n", False),
    ("source,target,weight\nA,B\n", False),
    ("source,target,weight\nA,B,1,extra\n", False),
])
def test_csv_recipe_validation(contents, valid, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "edges.csv").write_text(contents)
    if valid:
        result = recipe("references/io.md", "# Read a simple undirected edge table")
        assert result["G"]["A"]["B"]["weight"] == 0.5
    else:
        with pytest.raises(ValueError):
            recipe("references/io.md", "# Read a simple undirected edge table")


def test_compressed_adjlist_binary_contract(tmp_path, monkeypatch):
    import pickle
    pytest.importorskip("scipy")
    monkeypatch.chdir(tmp_path)
    graph = nx.Graph([("A", "B")])
    graph.add_node("isolate")
    result = recipe("references/io.md", "# NetworkX handles compression", G=graph, pickle=pickle)
    assert nx.utils.graphs_equal(graph, result["H"])
    assert (tmp_path / "graph.adjlist.gz").read_bytes()[:2] == b"\x1f\x8b"


def test_static_drawing_recipes(tmp_path, monkeypatch):
    mpl = pytest.importorskip("matplotlib")
    mpl.use("Agg", force=True)
    import matplotlib.pyplot as plt
    pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(plt, "show", lambda: None)
    skipped = ("import plotly", "from pyvis", "nx.nx_agraph", "from networkx.drawing.nx_pydot")
    for code in blocks("references/visualization.md"):
        if any(marker in code for marker in skipped):
            continue
        graph = nx.karate_club_graph()
        exec(compile(code, "visualization.md", "exec"), {
            "nx": nx, "plt": plt, "G": graph, "pos": nx.spring_layout(graph, seed=42)
        })
        plt.close("all")
    assert (tmp_path / "publication_graph.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert (tmp_path / "publication_graph.pdf").read_bytes().startswith(b"%PDF")


def test_plotly_current_colorbar_schema(monkeypatch):
    go = pytest.importorskip("plotly.graph_objects")
    pytest.importorskip("numpy")
    monkeypatch.setattr(go.Figure, "show", lambda self: None)
    result = recipe("references/visualization.md", "import plotly", G=nx.path_graph(4))
    figure = result["fig"].to_plotly_json()
    assert figure["data"][1]["marker"]["colorbar"]["title"]["text"] == "Node Connections"
    assert len(result["node_trace"].text) == 4


def test_pyvis_standalone_export_leaves_input_unchanged(tmp_path, monkeypatch):
    pytest.importorskip("pyvis")
    monkeypatch.chdir(tmp_path)
    graph = nx.Graph()
    graph.add_edge("A", "B", weight=0.5)
    before = deepcopy(graph)
    recipe("references/visualization.md", "from pyvis", G=graph)
    assert nx.utils.graphs_equal(graph, before)
    assert "vis-network" in (tmp_path / "graph.html").read_text()


def test_geographic_roundtrip_on_local_projected_fixture(tmp_path, monkeypatch):
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("momepy")
    from shapely.geometry import LineString
    monkeypatch.chdir(tmp_path)
    roads = gpd.GeoDataFrame({"road_id": ["one", "two"]}, geometry=[
        LineString([(0, 0), (1, 0)]), LineString([(1, 0), (1, 2)])
    ], crs="EPSG:3857")
    roads.to_file("roads.shp")
    result = recipe("references/io.md", "import momepy")
    assert result["G"].is_multigraph()
    assert sorted(result["edges_gdf"]["mm_len"]) == [1.0, 2.0]
    assert set(result["edges_gdf"]["road_id"]) == {"one", "two"}


def test_basic_removal_order_and_multigraph_update():
    result = recipe("SKILL.md", "# Modify: remove the edge")
    assert len(result["G"]) == 0
    graph = nx.Graph()
    graph.add_edge("A", "B", count=1)
    graph.add_edge("A", "B", count=2)
    assert graph.number_of_edges() == 1 and graph["A"]["B"]["count"] == 2


@pytest.mark.parametrize("format_name", ["gml", "gexf", "pajek"])
def test_other_exchange_formats_preserve_fixture_topology(format_name, tmp_path):
    graph = nx.Graph()
    graph.add_edge("A", "B", weight=0.5)
    graph.add_node("isolate")
    path = tmp_path / ("graph." + format_name)
    getattr(nx, "write_" + format_name)(graph, path)
    restored = getattr(nx, "read_" + format_name)(path)
    assert set(restored) == set(graph)
    assert set(nx.isolates(restored)) == {"isolate"}
    assert nx.is_isomorphic(nx.Graph(restored), graph)


def test_adjacency_and_cytoscape_json_recipes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    graph = nx.Graph()
    graph.add_edge("A", "B", weight=2)
    graph.add_node("isolate")
    adjacency = recipe("references/io.md", "# To adjacency format", G=graph, json=json)
    assert nx.utils.graphs_equal(adjacency["G"], graph)
    cytoscape = recipe("references/io.md", "# Export for Cytoscape", G=graph, json=json)
    assert set(cytoscape["G"]) == set(graph)
    assert cytoscape["G"]["A"]["B"]["weight"] == 2


def test_sql_recipe_uses_local_parameterized_query(tmp_path, monkeypatch):
    import sqlite3
    pytest.importorskip("pandas")
    monkeypatch.chdir(tmp_path)
    with sqlite3.connect("network.db") as conn:
        conn.execute("CREATE TABLE edges(source TEXT, target TEXT, weight REAL)")
        conn.executemany("INSERT INTO edges VALUES (?, ?, ?)", [("A", "B", 0.5), ("B", "C", 2)])
    result = recipe("references/io.md", "import sqlite3", min_weight=1)
    assert len(result["df"]) == 1
    assert "A" not in result["G"]
    assert result["G"]["B"]["C"]["weight"] == 2


def test_matrix_market_dense_and_sparse_imports(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    sparse = pytest.importorskip("scipy.sparse")
    io = pytest.importorskip("scipy.io")
    monkeypatch.chdir(tmp_path)
    adjacency = np.array([[0., 0.5], [0.5, 0.]])
    for matrix in (adjacency, sparse.csr_array(adjacency)):
        io.mmwrite("graph.mtx", matrix)
        result = recipe("references/io.md", "from scipy.io import mmread", sparse=sparse)
        assert result["G"][0][1]["weight"] == 0.5
