import collections.abc
import datetime
import itertools
import typing

import networkx as nx

import cimple.constants
import cimple.models
import cimple.models.snapshot
from cimple.models import pkg as pkg_models
from cimple.models import snapshot as snapshot_models

if typing.TYPE_CHECKING:
    import collections.abc


class CimpleSnapshot:
    """
    A class to represent a directed graph of package dependencies.
    It provides methods to build the dependency graph and compute build dependencies.
    """

    def __init__(self, snapshot_data: snapshot_models.SnapshotModel):
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
            self.graph.add_node(package.root.id)

        for package in snapshot_data.pkgs:
            if snapshot_models.snapshot_pkg_is_src(package.root):
                # Binary packages depends on source package that built them
                for bin_pkg in package.root.binary_packages:
                    if not self.graph.has_node(bin_pkg):
                        raise RuntimeError(
                            "Corrupted snapshot! "
                            f"Binary package {bin_pkg} of {package.root.id} "
                            "not found in snapshot."
                        )
                    self.graph.add_edge(bin_pkg, package.root.id)

                # Source package build-depends on other source packages
                for dep in package.root.build_depends:
                    if not self.graph.has_node(dep):
                        raise RuntimeError(
                            f"Corrupted snapshot! Binary package {dep} not found in snapshot. "
                            f"Required by build-depends of {package.root.id}."
                        )
                    self.graph.add_edge(package.root.id, dep)

            elif snapshot_models.snapshot_pkg_is_bin(package.root):
                # Binary package depends on other binary packages
                for dep in package.root.depends:
                    if not self.graph.has_node(dep):
                        raise RuntimeError(
                            f"Corrupted snapshot! Binary package {dep} not found in snapshot. "
                            f"Required by depends of {package.root.id}."
                        )
                    self.graph.add_edge(package.root.id, dep)

        # Build package map for quick access
        self.src_pkg_map = {
            pkg.root.id: pkg.root
            for pkg in snapshot_data.pkgs
            if snapshot_models.snapshot_pkg_is_src(pkg.root)
        }
        self.bin_pkg_map = {
            pkg.root.id: pkg.root
            for pkg in snapshot_data.pkgs
            if snapshot_models.snapshot_pkg_is_bin(pkg.root)
        }

        # Store snapshot metadata
        self.version: typing.Literal[0] = snapshot_data.version
        self.name = snapshot_data.name
        self.ancestor = snapshot_data.ancestor
        self.changes = snapshot_data.changes

    def _binary_neighbors(
        self,
        node: pkg_models.PkgId,
    ) -> collections.abc.Generator[pkg_models.PkgId]:
        """
        Get the binary package neighbors of a given node.

        Given how the dependency graph is constructed, this will yield:
        - For a source package: all binary packages it build-depends on.
        - For a binary package: all binary packages it depends on.
        """
        for neighbor in nx.neighbors(self.graph, node):
            if neighbor.type == "bin":
                yield neighbor

    def build_depends_of(self, src_pkg: pkg_models.SrcPkgId) -> list[pkg_models.BinPkgId]:
        """
        Get all binary packages that are required during the build a source package.
        """
        edges = nx.generic_bfs_edges(self.graph, src_pkg, neighbors=self._binary_neighbors)
        descendants: list[pkg_models.BinPkgId] = []
        for _, node in edges:
            assert node.type == "bin"
            descendants.append(node)
        return descendants

    def runtime_depends_of(self, bin_pkg: pkg_models.BinPkgId) -> list[pkg_models.BinPkgId]:
        """
        Get all binary packages that are required at runtime by a binary package.
        """
        edges = nx.generic_bfs_edges(self.graph, bin_pkg, neighbors=self._binary_neighbors)
        descendants: list[pkg_models.BinPkgId] = []
        for _, node in edges:
            assert node.type == "bin"
            descendants.append(node)
        return descendants

    def dump_snapshot(self):
        """
        Dump the snapshot to a JSON file.
        """
        snapshot_name = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d-%H%M%S")
        pkgs = [
            cimple.models.snapshot.SnapshotPkg(pkg)
            for pkg in itertools.chain(self.src_pkg_map.values(), self.bin_pkg_map.values())
        ]
        snapshot_data = snapshot_models.SnapshotModel(
            version=self.version,
            name=snapshot_name,
            pkgs=pkgs,
            ancestor=self.ancestor,
            changes=self.changes,
        )

        snapshot_manifest = cimple.constants.cimple_snapshot_dir / f"{snapshot_name}.json"
        if snapshot_manifest.exists():
            raise RuntimeError(f"Snapshot {snapshot_name} already exists!")

        with snapshot_manifest.open("w") as f:
            f.write(snapshot_data.model_dump_json(by_alias=True))

    def add_src_pkg(
        self,
        pkg_id: pkg_models.SrcPkgId,
        pkg_version: str,
        build_depends: list[pkg_models.BinPkgId],
    ) -> None:
        """
        Add a package to the snapshot.
        """
        if pkg_id in self.src_pkg_map:
            raise RuntimeError(f"Package {pkg_id} already exists in snapshot.")

        # Add package to snapshot map
        new_src_pkg = snapshot_models.SnapshotSrcPkg.model_construct(
            name=pkg_id.name,
            version=pkg_version,
            build_depends=build_depends,
            binary_packages=[],
            pkg_type="src",
        )
        self.src_pkg_map[pkg_id] = new_src_pkg

        # Add package to changes
        self.changes.add.append(
            cimple.models.snapshot.SnapshotChangeAdd(
                name=pkg_id.name,
                version=pkg_version,
            )
        )

        # Add package to graph
        self.graph.add_node(pkg_id)
        for dep in build_depends:
            self.graph.add_edge(pkg_id, dep)

    def add_bin_pkg(
        self,
        pkg_id: pkg_models.BinPkgId,
        src_pkg: pkg_models.SrcPkgId,
        pkg_sha256: str,
        depends: list[pkg_models.BinPkgId],
    ) -> None:
        """
        Add a binary package to the snapshot.
        """
        if pkg_id in self.bin_pkg_map:
            raise RuntimeError(f"Package {pkg_id} already exists in snapshot.")

        # Add package to snapshot map
        new_bin_pkg = snapshot_models.SnapshotBinPkg.model_construct(
            name=pkg_id.name,
            sha256=pkg_sha256,
            compression_method="xz",
            depends=depends,
            pkg_type="bin",
        )
        self.bin_pkg_map[pkg_id] = new_bin_pkg

        # Add binary package to its source package
        assert src_pkg in self.src_pkg_map, f"Source package {src_pkg} not found in snapshot."
        src_snapshot_pkg = self.src_pkg_map[src_pkg]
        assert snapshot_models.snapshot_pkg_is_src(src_snapshot_pkg)
        src_snapshot_pkg.binary_packages.append(pkg_id)

        # Add package to graph
        self.graph.add_node(pkg_id)
        for dep in depends:
            self.graph.add_edge(pkg_id, dep)

    def compare_pkgs_with(self, rhs: CimpleSnapshot) -> None | pkg_models.PkgId:
        """
        Compare packages with another snapshot.
        When they are identical, return None.
        When they are different, return the package ID where things are different.
        """
        # Compare source packages
        for pkg_id, pkg in self.src_pkg_map.items():
            rhs_pkg = rhs.src_pkg_map.get(pkg_id)
            if rhs_pkg is None or rhs_pkg != pkg:
                return pkg_id

        # Compare binary packages
        for pkg_id, pkg in self.bin_pkg_map.items():
            rhs_pkg = rhs.bin_pkg_map.get(pkg_id)
            if rhs_pkg is None or rhs_pkg != pkg:
                return pkg_id

        return None

    def __eq__(self, rhs: typing.Any) -> bool:
        if not isinstance(rhs, CimpleSnapshot):
            return False
        return (
            self.compare_pkgs_with(rhs) is None
            and self.name == rhs.name
            and self.ancestor == rhs.ancestor
            and self.changes == rhs.changes
            and self.version == rhs.version
        )


def load_snapshot(name: str) -> CimpleSnapshot:
    if name == "root":
        snapshot_data = snapshot_models.SnapshotModel(
            version=0,
            name="root",
            pkgs=[],
            ancestor="root",
            changes=snapshot_models.SnapshotChanges(add=[], remove=[], update=[]),
        )
    else:
        snapshot_path = cimple.constants.cimple_snapshot_dir / f"{name}.json"
        with snapshot_path.open("r") as f:
            snapshot_data = snapshot_models.SnapshotModel.model_validate_json(f.read())

    return CimpleSnapshot(snapshot_data)
