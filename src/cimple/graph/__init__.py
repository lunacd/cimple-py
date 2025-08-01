import networkx as nx

from cimple import models


def get_dep_graph(snapshot_map: models.snapshot.SnapshotMap) -> nx.DiGraph:
    """
    Constructs a directed graph representing the dependencies of packages.

    There are three types of dependencies:
    1. Source package depends on binary packages (build-depends)
    2. Binary package depends on other binary packages (depends)
    3. Binary package depends on the source package that built it (build)
    """
    graph = nx.DiGraph()

    for pkg in snapshot_map.pkgs.values():
        graph.add_node(pkg.full_name)

    for pkg in snapshot_map.pkgs.values():
        if models.snapshot.snapshot_pkg_is_src(pkg.root):
            # Binary packages depends on source package that built them
            for bin_pkg in pkg.root.binary_packages:
                dep = f"bin:{bin_pkg}"
                if not graph.has_node(dep):
                    raise RuntimeError(
                        "Corrupted snapshot! "
                        f"Binary package {bin_pkg} of {pkg.full_name} not found in snapshot."
                    )
                graph.add_edge(f"bin:{bin_pkg}", pkg.full_name)

            # Source package build-depends on other source packages
            for dep in pkg.root.build_depends:
                dep_name = f"bin:{dep}"
                if not graph.has_node(dep_name):
                    raise RuntimeError(
                        f"Corrupted snapshot! Binary package {dep_name} not found in snapshot. "
                        f"Required by build-depends of {pkg.full_name}."
                    )
                graph.add_edge(pkg.full_name, dep_name)

        elif models.snapshot.snapshot_pkg_is_bin(pkg.root):
            # Binary package depends on other binary packages
            for dep in pkg.root.depends:
                dep_name = f"bin:{dep}"
                if not graph.has_node(dep_name):
                    raise RuntimeError(
                        f"Corrupted snapshot! Binary package {dep_name} not found in snapshot. "
                        f"Required by depends of {pkg.full_name}."
                    )
                graph.add_edge(pkg.full_name, dep_name)

    return graph


def get_build_depends(dep_graph: nx.DiGraph, src_pkg: models.pkg.SrcPkgId) -> list[str]:
    """
    Get all binary packages that are required during the build a source package.
    """
    descendents = nx.descendants(dep_graph, f"src:{src_pkg.name}")
    binary_deps = filter(lambda item: models.pkg.str_pkg_is_bin(item), descendents)
    return list(binary_deps)
