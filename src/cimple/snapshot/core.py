import datetime
import itertools
import typing

import networkx as nx

import cimple.constants
import cimple.graph
import cimple.models
import cimple.models.pkg_config
import cimple.models.snapshot
import cimple.pkg.core
import cimple.pkg.ops
from cimple.models import pkg as pkg_models
from cimple.models import snapshot as snapshot_models

if typing.TYPE_CHECKING:
    import pathlib


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

    def build_depends_of(self, src_pkg: pkg_models.SrcPkgId) -> list[pkg_models.BinPkgId]:
        """
        Get all binary packages that are required during the build a source package.
        """
        edges = nx.generic_bfs_edges(
            self.graph,
            src_pkg,
            neighbors=lambda node: cimple.graph.binary_neighbors(self.graph, node),
        )
        descendants: list[pkg_models.BinPkgId] = []
        for _, node in edges:
            assert node.type == "bin"
            descendants.append(node)
        return descendants

    def runtime_depends_of(self, bin_pkg: pkg_models.BinPkgId) -> list[pkg_models.BinPkgId]:
        """
        Get all binary packages that are required at runtime by a binary package.
        """
        edges = nx.generic_bfs_edges(
            self.graph,
            bin_pkg,
            neighbors=lambda node: cimple.graph.binary_neighbors(self.graph, node),
        )
        descendants: list[pkg_models.BinPkgId] = []
        for _, node in edges:
            assert node.type == "bin"
            descendants.append(node)
        return descendants

    def build_dependents_of(self, src_pkg: pkg_models.SrcPkgId) -> list[pkg_models.SrcPkgId]:
        """
        Get all source packages that depend on the given source package for building.
        """
        reversed_graph = self.graph.reverse(copy=False)
        produced_binary_pkgs = self.src_pkg_map[src_pkg].binary_packages
        ancestors: list[pkg_models.SrcPkgId] = []
        for bin_pkg in produced_binary_pkgs:
            edges = nx.generic_bfs_edges(
                reversed_graph,
                bin_pkg,
                neighbors=lambda node: cimple.graph.src_neighbors(reversed_graph, node),
            )
            for _, node in edges:
                assert node.type == "src"
                ancestors.append(node)
        return ancestors

    def dump_snapshot(self):
        """
        Dump the snapshot to a JSON file.
        """
        # Check that binary packages have their SHA256 filled in
        for bin_pkg in self.bin_pkg_map.values():
            if not bin_pkg.sha256 or bin_pkg.sha256 == "placeholder":
                raise RuntimeError(f"Binary package {bin_pkg.name} has no valid SHA256!")

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
        Add a source package to the snapshot.
        This does not add its binary packages; they should be added separately.
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
        assert pkg_id not in self.bin_pkg_map, f"Package {pkg_id} already exists in snapshot."

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
        src_snapshot_pkg.binary_packages.append(pkg_id)

        # Add package to graph
        self.graph.add_node(pkg_id)
        for dep in depends:
            self.graph.add_edge(pkg_id, dep)

    def add_pkg(
        self,
        pkg_config: cimple.models.pkg_config.PkgConfig,
        dependency_data: cimple.pkg.core.PackageDependencies,
    ) -> None:
        """
        Add a package and its binary packages to the snapshot.
        This is a convenience method that dispatches add_src_pkg and add_bin_pkg.
        """
        self.add_src_pkg(
            pkg_id=pkg_models.SrcPkgId(pkg_config.root.name),
            pkg_version=pkg_config.root.version,
            build_depends=dependency_data.build_depends,
        )
        for binary_package in pkg_config.root.binary_packages:
            if binary_package in self.bin_pkg_map:
                raise RuntimeError(f"Binary package {binary_package} already exists in snapshot.")
            self.add_bin_pkg(
                pkg_id=binary_package,
                src_pkg=pkg_config.root.id,
                pkg_sha256="placeholder",  # SHA will be filled in separately
                depends=dependency_data.depends[binary_package],
            )

    def remove_pkg(self, pkg_id: pkg_models.SrcPkgId) -> None:
        """
        Remove a source package and its binary packages from the snapshot.
        """
        assert pkg_id in self.src_pkg_map, f"Package {pkg_id} does not exist in snapshot."

        # Remove binary packages first
        src_snapshot_pkg = self.src_pkg_map[pkg_id]
        for bin_pkg_id in src_snapshot_pkg.binary_packages:
            bin_pkg_data = self.bin_pkg_map[bin_pkg_id]

            # Remove all dependency edges for this binary package
            for dep in bin_pkg_data.depends:
                self.graph.remove_edge(bin_pkg_id, dep)

            del self.bin_pkg_map[bin_pkg_id]
            self.graph.remove_node(bin_pkg_id)

        # Remove all build dependency edges for this source package
        for dep in src_snapshot_pkg.build_depends:
            self.graph.remove_edge(pkg_id, dep)

        # Remove source package
        del self.src_pkg_map[pkg_id]
        self.graph.remove_node(pkg_id)

    def validate_depends(self, pkg_id: pkg_models.SrcPkgId) -> bool:
        """
        Validate that all build and runtime dependencies of a source package are satisfied.
        """
        assert pkg_id in self.src_pkg_map, f"Package {pkg_id} does not exist in snapshot."

        src_snapshot_pkg = self.src_pkg_map[pkg_id]

        # Validate build dependencies
        for build_dep in src_snapshot_pkg.build_depends:
            if build_dep not in self.bin_pkg_map:
                return False

        # Validate runtime dependencies for each binary package
        for bin_pkg_id in src_snapshot_pkg.binary_packages:
            bin_snapshot_pkg = self.bin_pkg_map[bin_pkg_id]
            for runtime_dep in bin_snapshot_pkg.depends:
                if runtime_dep not in self.bin_pkg_map:
                    return False

        return True

    def update_with_changes(
        self,
        *,
        changes: cimple.models.snapshot.SnapshotChanges,
        pkg_processor: cimple.pkg.ops.PkgOps,
        pkg_index_path: pathlib.Path,
    ):
        """
        Compute the build order for the packages to be added/updated.
        Also computes the new build dependency graph as part of the process.
        """
        # First process additions, because updates may depend on newly added packages
        for pkg_add in changes.add:
            dependency_data = pkg_processor.resolve_dependencies(
                pkg_add.id, pkg_add.version, pi_path=pkg_index_path
            )
            config = cimple.models.pkg_config.load_pkg_config(
                pkg_index_path, pkg_add.id, pkg_add.version
            )
            self.add_pkg(config, dependency_data)

        # Then process updates
        for pkg_update in changes.update:
            # Remove old package
            self.remove_pkg(pkg_update.id)

            # Add new package
            config = cimple.models.pkg_config.load_pkg_config(
                pkg_index_path, pkg_models.SrcPkgId(pkg_update.name), pkg_update.to_version
            )
            dependency_data = pkg_processor.resolve_dependencies(
                pkg_models.SrcPkgId(pkg_update.name),
                pkg_update.to_version,
                pi_path=pkg_index_path,
            )
            self.add_pkg(config, dependency_data)

        # Finally process removal
        for pkg_remove in changes.remove:
            self.remove_pkg(pkg_remove)

        # Resolve all build and runtime dependencies and make sure they are satisfied
        for pkg in itertools.chain(changes.add, changes.update):
            deps_are_valid = self.validate_depends(pkg.id)
            if not deps_are_valid:
                raise RuntimeError(f"Unable to resolve dependencies for package {pkg.id.name}")

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
