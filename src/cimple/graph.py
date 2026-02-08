import typing
from typing import TYPE_CHECKING

import networkx as nx

import cimple.models.pkg

if TYPE_CHECKING:
    import collections.abc


T = typing.TypeVar("T")


class Graph[T]:
    """
    A wrapper around networkx DiGraph.

    The only difference is that it does not by default remove all edges when a node is removed.
    Instead, it keeps track of those "broken edges".

    This incidentally supports better typing for the graph, but it's not the point of this class.
    """

    def __init__(self) -> None:
        self.graph: nx.DiGraph[T] = nx.DiGraph()

        # The broken edges are from value to key
        self.broken_edges: dict[T, set[T]] = {}

    def _remove_from_broken_edges(self, from_node: T, to_node: T) -> bool:
        """
        Remove the edge from broken_edges if it exists.

        Returns True if the edge was in broken_edges.
        """
        if to_node in self.broken_edges and from_node in self.broken_edges[to_node]:
            self.broken_edges[to_node].remove(from_node)
            if len(self.broken_edges[to_node]) == 0:
                del self.broken_edges[to_node]
            return True
        return False

    def add_node(self, node: T) -> None:
        """
        Add a node. Restore any broken edges to this node if they exist.
        """
        self.graph.add_node(node)
        if node in self.broken_edges:
            for from_node in self.broken_edges[node]:
                self.graph.add_edge(from_node, node)
            del self.broken_edges[node]

    def add_edge(self, from_node: T, to_node: T) -> None:
        """
        Adds the edge to graph.

        If the edge already exists as a broken edge, remove it from broken_edges.
        """
        self.graph.add_edge(from_node, to_node)
        self._remove_from_broken_edges(from_node, to_node)

    def remove_edge(self, from_node: T, to_node: T) -> None:
        """
        Remove an edge from the graph. If it's a broken edge, remove from broken_edges instead.
        """
        if not self._remove_from_broken_edges(from_node, to_node):
            self.graph.remove_edge(from_node, to_node)

    def remove_node(self, node: T) -> None:
        """
        Remove a node from the graph, and mark all its edges as broken edges.
        """
        if node not in self.graph:
            return

        # Mark all edges to and from this node as broken edges
        for neighbor in self.graph.successors(node):
            self.broken_edges.setdefault(neighbor, set()).add(node)
        for neighbor in self.graph.predecessors(node):
            self.broken_edges.setdefault(node, set()).add(neighbor)

        self.graph.remove_node(node)

    def has_node(self, node: T) -> bool:
        return self.graph.has_node(node)

    def is_broken(self) -> bool:
        """
        Check if the graph has any broken edges.
        """
        return len(self.broken_edges) > 0

    def generic_bfs_edges(
        self, source: T, neighbors: typing.Callable[[T], typing.Iterable[T]] | None = None
    ) -> typing.Iterable[tuple[T, T]]:
        assert not self.is_broken(), "Cannot traverse a graph with broken edges"
        return nx.generic_bfs_edges(self.graph, source=source, neighbors=neighbors)

    def neighbors(self, node: T) -> typing.Iterator[T]:
        assert not self.is_broken(), "Cannot traverse a graph with broken edges"
        return self.graph.neighbors(node)

    def reverse(self, copy: bool = True) -> Graph[T]:
        """
        Return the reverse of the graph.
        """
        assert not self.is_broken(), "Cannot reverse a graph with broken edges"
        reversed_graph = Graph()
        reversed_graph.graph = self.graph.reverse(copy=copy)
        return reversed_graph

    def descendants(self, node: T) -> set[T]:
        """
        Return the descendants of a node in the graph.
        """
        assert not self.is_broken(), "Cannot get descendants of a graph with broken edges"
        return nx.descendants(self.graph, node)

    def subgraph(self, nodes: typing.Iterable[T]) -> Graph[T]:
        """
        Return the subgraph induced by the given nodes.
        """
        assert not self.is_broken(), "Cannot get subgraph of a graph with broken edges"
        subgraph = Graph()
        subgraph.graph = typing.cast("nx.DiGraph[T]", self.graph.subgraph(nodes).copy())
        return subgraph

    def in_degrees(self) -> typing.Iterable[tuple[T, int]]:
        assert not self.is_broken(), "Cannot get in-degrees of a graph with broken edges"
        return self.graph.in_degree()

    def in_degree(self, node: T) -> int:
        assert not self.is_broken(), "Cannot get in-degree of a graph with broken edges"
        return self.graph.in_degree(node)

    def number_of_nodes(self) -> int:
        return self.graph.number_of_nodes()

    def has_edge(self, from_node: T, to_node: T) -> bool:
        """
        Check if the graph has the edge from from_node to to_node.
        Broken edges are not considered as edges in the graph.
        """
        return self.graph.has_edge(from_node, to_node)

    def edges(self) -> typing.Iterable[tuple[T, T]]:
        """
        Return the edges in the graph. Broken edges are not included.
        """
        return self.graph.edges()

    def nodes(self) -> typing.Iterable[T]:
        return self.graph.nodes()


def binary_neighbors(
    graph: Graph[cimple.models.pkg.PkgId],
    node: cimple.models.pkg.PkgId,
) -> collections.abc.Generator[cimple.models.pkg.PkgId]:
    """
    Get the binary package neighbors of a given node.

    Given how the dependency graph is constructed, this will yield:
    - For a source package: all binary packages it build-depends on.
    - For a binary package: all binary packages it depends on.
    """
    for neighbor in graph.neighbors(node):
        if neighbor.type == "bin":
            yield neighbor


class BuildGraph:
    """
    A build graph for packages.
    """

    def __init__(self, graph: Graph[cimple.models.pkg.PkgId]) -> None:
        self.graph = graph
        self.pkgs_ready_to_build = [
            n for n, deg in graph.in_degrees() if deg == 0 and n.type == "src"
        ]
        self.built_pkgs: set[cimple.models.pkg.PkgId] = set()

    def get_pkgs_to_build(self, max_count: int) -> list[cimple.models.pkg.SrcPkgId]:
        """
        Get packages that are ready to build, up to max_count.
        """
        pkgs = self.pkgs_ready_to_build[:max_count]
        self.pkgs_ready_to_build = self.pkgs_ready_to_build[max_count:]
        return pkgs

    def _remove_binary_pkg_from_graph(
        self,
        binary_pkg: cimple.models.pkg.BinPkgId,
    ) -> None:
        """
        Remove a binary package from the graph, updating the graph accordingly.
        """
        for neighbor in list(self.graph.neighbors(binary_pkg)):
            self.graph.remove_edge(binary_pkg, neighbor)

            # Any source package that now has no build dependencies can be built
            if self.graph.in_degree(neighbor) == 0 and neighbor.type == "src":
                self.pkgs_ready_to_build.append(neighbor)

            # Any built binary package that now has all its requirements satisfied can be removed
            if (
                neighbor.type == "bin"
                and neighbor in self.built_pkgs
                and self.graph.in_degree(neighbor) == 0
            ):
                self._remove_binary_pkg_from_graph(neighbor)

        self.graph.remove_node(binary_pkg)

    def mark_pkgs_built(
        self,
        built_src: cimple.models.pkg.SrcPkgId,
    ) -> None:
        """
        Mark packages as built, updating the graph accordingly.
        """
        # Remove src package and its connection to binary packages from the graph
        assert self.graph.in_degree(built_src) == 0, (
            "Source package still has requirements, and should not have been built yet"
        )

        # Get all binary packages built from this source package
        binary_packages = list(self.graph.neighbors(built_src))
        assert cimple.models.pkg.is_bin_pkg_list(binary_packages), (
            "Expected all neighbors of source package to be binary packages"
        )

        # Remove the source package and its connection to its biniary packages from the graph
        for binary_pkg in binary_packages:
            self.graph.remove_edge(built_src, binary_pkg)
        self.graph.remove_node(built_src)

        # Remove binary packages that have all their requirements satisfied
        for pkg in binary_packages:
            # For those that still have requirements, store them in built_pkgs for later use
            if self.graph.in_degree(pkg) > 0:
                self.built_pkgs.add(pkg)
                continue

            # For those that have all requirements satisfied, remove them from the graph
            self._remove_binary_pkg_from_graph(pkg)

    def is_empty(self) -> bool:
        """
        Check if the build graph is empty, i.e. all packages have been scheduled to build.
        """
        return self.graph.number_of_nodes() == 0
