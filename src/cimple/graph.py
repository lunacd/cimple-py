from typing import TYPE_CHECKING

import cimple.models.pkg

if TYPE_CHECKING:
    import networkx as nx


class BuildGraph:
    """
    A build graph for packages.
    """

    def __init__(self, graph: nx.DiGraph[cimple.models.pkg.PkgId]) -> None:
        self.graph = graph
        self.pkgs_ready_to_build = [
            n for n, deg in graph.in_degree() if deg == 0 and n.type == "src"
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

        # Remove the source package from the graph
        # This also removes edges from the source package to its binary packages
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
