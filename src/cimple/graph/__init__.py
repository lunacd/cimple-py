import networkx as nx

from cimple import models


def get_runtime_dep_graph(snapshot_data: models.snapshot.Snapshot) -> nx.DiGraph:
    """
    Constructs a directed graph representing the runtime dependencies of packages.
    """
    graph = nx.DiGraph()

    for pkg in snapshot_data.pkgs:
        graph.add_node(pkg.name)

    for pkg in snapshot_data.pkgs:
        for dep in pkg.depends:
            graph.add_edge(pkg.name, dep)

    return graph
