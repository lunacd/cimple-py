import datetime
import typing

import networkx as nx

from cimple import common, models


class CimpleSnapshot:
    """
    A class to represent a directed graph of package dependencies.
    It provides methods to build the dependency graph and compute build dependencies.
    """

    def __init__(self, snapshot_data: models.snapshot.Snapshot):
        """
        Constructs a directed graph representing the dependencies of packages.

        There are three types of dependencies:
        1. Source package depends on binary packages (build-depends)
        2. Binary package depends on other binary packages (depends)
        3. Binary package depends on the source package that built it (build)
        """
        # Build dependency graph
        self.graph = nx.DiGraph()

        for package in snapshot_data.pkgs:
            self.graph.add_node(package.full_name)

        for package in snapshot_data.pkgs:
            if models.snapshot.snapshot_pkg_is_src(package.root):
                # Binary packages depends on source package that built them
                for bin_pkg in package.root.binary_packages:
                    dep = f"bin:{bin_pkg}"
                    if not self.graph.has_node(dep):
                        raise RuntimeError(
                            "Corrupted snapshot! "
                            f"Binary package {bin_pkg} of {package.full_name} "
                            "not found in snapshot."
                        )
                    self.graph.add_edge(f"bin:{bin_pkg}", package.full_name)

                # Source package build-depends on other source packages
                for dep in package.root.build_depends:
                    dep_name = f"bin:{dep}"
                    if not self.graph.has_node(dep_name):
                        raise RuntimeError(
                            f"Corrupted snapshot! Binary package {dep_name} not found in snapshot. "
                            f"Required by build-depends of {package.full_name}."
                        )
                    self.graph.add_edge(package.full_name, dep_name)

            elif models.snapshot.snapshot_pkg_is_bin(package.root):
                # Binary package depends on other binary packages
                for dep in package.root.depends:
                    dep_name = f"bin:{dep}"
                    if not self.graph.has_node(dep_name):
                        raise RuntimeError(
                            f"Corrupted snapshot! Binary package {dep_name} not found in snapshot. "
                            f"Required by depends of {package.full_name}."
                        )
                    self.graph.add_edge(package.full_name, dep_name)

        # Build package map for quick access
        self.pkg_map = {pkg.full_name: pkg for pkg in snapshot_data.pkgs}

        # Store snapshot metadata
        self.version: typing.Literal[0] = snapshot_data.version
        self.name = snapshot_data.name
        self.ancestor = snapshot_data.ancestor
        self.changes = snapshot_data.changes

    def build_depends_of(self, src_pkg: models.pkg.SrcPkgId) -> list[models.pkg.BinPkgId]:
        """
        Get all binary packages that are required during the build a source package.
        """
        descendents: list[models.pkg.PkgId] = nx.descendants(self.graph, src_pkg)
        return list(filter(lambda item: models.pkg.pkg_is_bin(item), descendents))

    def runtime_depends_of(self, bin_pkg: models.pkg.BinPkgId) -> list[models.pkg.BinPkgId]:
        """
        Get all binary packages that are required at runtime by a binary package.
        """
        descendents: list[models.pkg.PkgId] = nx.descendants(self.graph, bin_pkg)
        return list(filter(lambda item: models.pkg.pkg_is_bin(item), descendents))

    def dump_snapshot(self):
        """
        Dump the snapshot to a JSON file.
        """
        snapshot_name = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d-%H%M%S")
        snapshot_data = models.snapshot.Snapshot(
            version=self.version,
            name=snapshot_name,
            pkgs=list(self.pkg_map.values()),
            ancestor=self.ancestor,
            changes=self.changes,
        )

        snapshot_manifest = common.constants.cimple_snapshot_dir / f"{snapshot_name}.json"
        if snapshot_manifest.exists():
            raise RuntimeError(f"Snapshot {snapshot_name} already exists!")

        with snapshot_manifest.open("w") as f:
            f.write(snapshot_data.model_dump_json())

    def get_snapshot_pkg(
        self,
        pkg_id: models.pkg.PkgId,
    ) -> models.snapshot.SnapshotPkg | None:
        return self.pkg_map.get(pkg_id, None)


def load_snapshot(name: str) -> CimpleSnapshot:
    if name == "root":
        snapshot_data = models.snapshot.Snapshot(
            version=0,
            name="root",
            pkgs=[],
            ancestor="root",
            changes=models.snapshot.SnapshotChanges(add=[], remove=[]),
        )
    else:
        snapshot_path = common.constants.cimple_snapshot_dir / f"{name}.json"
        with snapshot_path.open("r") as f:
            snapshot_data = models.snapshot.Snapshot.model_validate_json(f.read())

    return CimpleSnapshot(snapshot_data)
