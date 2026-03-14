import datetime
import itertools
import typing

import cimple.constants
import cimple.graph
import cimple.models
import cimple.models.pkg
import cimple.models.pkg_config
import cimple.models.snapshot
import cimple.pkg.core
import cimple.pkg.ops
import cimple.util
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
        # Build package map for quick access
        self.src_pkg_map = {
            pkg.root.id: pkg.root for pkg in snapshot_data.pkgs if pkg.root.pkg_type == "src"
        }
        self.bin_pkg_map = {
            pkg.root.id: pkg.root for pkg in snapshot_data.pkgs if pkg.root.pkg_type == "bin"
        }
        self.bootstrap_src_pkg_map = {
            pkg.root.id: pkg.root
            for pkg in snapshot_data.bootstrap_pkgs
            if pkg.root.pkg_type == "src"
        }
        self.bootstrap_bin_pkg_map = {
            pkg.root.id: pkg.root
            for pkg in snapshot_data.bootstrap_pkgs
            if pkg.root.pkg_type == "bin"
        }

        # Build dependency graph
        self.graph = cimple.graph.Graph[pkg_models.PkgId]()

        # Add bootstrap nodes
        # All bootstrap packages (source or binary) are translated to three nodes:
        # - pkg-name: the actual package node
        # - bootstrap:pkg-name: the bootstrap package used to build the above actual packages
        # Bootstrap packages are built by pulling their deps from the previous snapshot, those
        # packages are denoted with the "prev:" prefix. Because they are always available, we
        # do not need to add them to the graph.
        def add_edge(from_pkg: pkg_models.PkgId, to_pkg: pkg_models.PkgId):
            """
            Helper to add edge to graph with validation.
            """
            if not self.graph.has_node(from_pkg):
                raise RuntimeError(
                    f"Corrupted snapshot! Package {from_pkg} not found in snapshot. "
                    f"Required by {to_pkg}."
                )
            if not self.graph.has_node(to_pkg):
                raise RuntimeError(
                    f"Corrupted snapshot! Package {to_pkg} not found in snapshot. "
                    f"Required by {from_pkg}."
                )
            self.graph.add_edge(from_pkg, to_pkg)

        # Add all other packages
        for package in itertools.chain(snapshot_data.pkgs, snapshot_data.bootstrap_pkgs):
            self.graph.add_node(package.root.id)

        # Add dependency edges for normal packages
        for package in itertools.chain(snapshot_data.pkgs, snapshot_data.bootstrap_pkgs):
            if snapshot_models.snapshot_pkg_is_src(package.root):
                # Binary packages depends on source package that built them
                for bin_pkg in package.root.binary_packages:
                    add_edge(bin_pkg, package.root.id)

                # Source package build-depends on other source packages
                for dep in package.root.build_depends:
                    # Do not add edges for `prev:` packages, as they are always available
                    if cimple.models.pkg.is_prev_pkg(dep):
                        continue

                    add_edge(package.root.id, dep)

            elif snapshot_models.snapshot_pkg_is_bin(package.root):
                # Binary package depends on other binary packages
                for dep in package.root.depends:
                    add_edge(package.root.id, dep)

        # Store snapshot metadata
        self.version: typing.Literal[0] = snapshot_data.version
        self.name = snapshot_data.name
        self.ancestor = snapshot_data.ancestor
        self.changes = snapshot_data.changes
        self.bootstrap_changes = snapshot_data.bootstrap_changes

    def build_depends_of(self, src_pkg: pkg_models.SrcPkgId) -> list[pkg_models.BinPkgId]:
        """
        Get all binary packages that are required during the build a source package.
        """
        edges = self.graph.generic_bfs_edges(
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
        edges = self.graph.generic_bfs_edges(
            bin_pkg,
            neighbors=lambda node: cimple.graph.binary_neighbors(self.graph, node),
        )
        descendants: list[pkg_models.BinPkgId] = []
        for _, node in edges:
            assert node.type == "bin"
            descendants.append(node)
        return descendants

    def binary_pkgs_are_complete(self) -> bool:
        """
        Check that all binary packages in the snapshot have their SHA256 filled in.
        """
        return all(bin_pkg.sha256 != "placeholder" for bin_pkg in self.bin_pkg_map.values())

    def dump_snapshot(self):
        """
        Dump the snapshot to a JSON file.
        """
        # Check that binary packages have their SHA256 filled in
        if not self.binary_pkgs_are_complete():
            raise RuntimeError(
                "Cannot dump snapshot: some binary packages have placeholder SHA256."
            )

        snapshot_name = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d-%H%M%S")
        pkgs = [
            cimple.models.snapshot.SnapshotPkg(pkg)
            for pkg in itertools.chain(self.src_pkg_map.values(), self.bin_pkg_map.values())
        ]
        bootstrap_pkgs = [
            cimple.models.snapshot.SnapshotPkg(pkg)
            for pkg in itertools.chain(
                self.bootstrap_src_pkg_map.values(), self.bootstrap_bin_pkg_map.values()
            )
        ]

        snapshot_data = snapshot_models.SnapshotModel(
            version=self.version,
            name=snapshot_name,
            pkgs=pkgs,
            bootstrap_pkgs=bootstrap_pkgs,
            ancestor=self.ancestor,
            changes=self.changes,
            bootstrap_changes=self.bootstrap_changes,
        )

        cimple.util.ensure_path(cimple.constants.cimple_snapshot_dir)
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
        bootstrap: bool = False,
    ) -> None:
        """
        Add a source package to the snapshot.
        This does not add its binary packages; they should be added separately.
        """
        src_pkg_map = self.bootstrap_src_pkg_map if bootstrap else self.src_pkg_map
        if pkg_id in src_pkg_map:
            raise RuntimeError(f"Package {pkg_id} already exists in snapshot.")

        # Add package to snapshot map
        new_src_pkg = snapshot_models.SnapshotSrcPkg.model_construct(
            name=pkg_id.name,
            version=pkg_version,
            build_depends=build_depends,
            binary_packages=[],
            pkg_type="src",
        )
        src_pkg_map[pkg_id] = new_src_pkg

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
        bootstrap: bool = False,
    ) -> None:
        """
        Add a binary package to the snapshot.
        """
        bin_pkg_map = self.bootstrap_bin_pkg_map if bootstrap else self.bin_pkg_map
        src_pkg_map = self.bootstrap_src_pkg_map if bootstrap else self.src_pkg_map

        assert pkg_id not in bin_pkg_map, f"Package {pkg_id} already exists in snapshot."

        # Add package to snapshot map
        new_bin_pkg = snapshot_models.SnapshotBinPkg.model_construct(
            name=pkg_id.name,
            sha256=pkg_sha256,
            compression_method="xz",
            depends=depends,
            pkg_type="bin",
        )
        bin_pkg_map[pkg_id] = new_bin_pkg

        # Add binary package to its source package
        assert src_pkg in src_pkg_map, f"Source package {src_pkg} not found in snapshot."
        src_snapshot_pkg = src_pkg_map[src_pkg]
        src_snapshot_pkg.binary_packages.append(pkg_id)

        # Add package to graph
        self.graph.add_node(pkg_id)
        for dep in depends:
            self.graph.add_edge(pkg_id, dep)

    def add_pkg(
        self,
        pkg_config: cimple.models.pkg_config.PkgConfig,
        dependency_data: cimple.pkg.core.PackageDependencies,
        *,
        bootstrap: bool = False,
    ) -> None:
        """
        Add a package and its binary packages to the snapshot.
        This is a convenience method that dispatches add_src_pkg and add_bin_pkg.
        """
        self.add_src_pkg(
            pkg_id=pkg_config.root.id,
            pkg_version=pkg_config.root.version,
            build_depends=dependency_data.build_depends[pkg_config.root.id],
            bootstrap=bootstrap,
        )
        if bootstrap:
            bootstrap_src_id = cimple.models.pkg.bootstrap_src_id(pkg_config.root.id)
            self.add_src_pkg(
                pkg_id=bootstrap_src_id,
                pkg_version=pkg_config.root.version,
                build_depends=dependency_data.build_depends[bootstrap_src_id],
                bootstrap=bootstrap,
            )
        for binary_package in pkg_config.root.binary_packages:
            if binary_package in self.bin_pkg_map:
                raise RuntimeError(f"Binary package {binary_package} already exists in snapshot.")
            self.add_bin_pkg(
                pkg_id=binary_package,
                src_pkg=pkg_config.root.id,
                pkg_sha256="placeholder",  # SHA will be filled in separately
                depends=dependency_data.depends[binary_package],
                bootstrap=bootstrap,
            )
            self.graph.add_edge(binary_package, pkg_config.root.id)
            if bootstrap:
                bootstrap_bin_id = cimple.models.pkg.bootstrap_bin_id(binary_package)
                if bootstrap_bin_id in self.bin_pkg_map:
                    raise RuntimeError(
                        f"Binary package {bootstrap_bin_id} already exists in snapshot."
                    )
                self.add_bin_pkg(
                    pkg_id=bootstrap_bin_id,
                    src_pkg=cimple.models.pkg.bootstrap_src_id(pkg_config.root.id),
                    pkg_sha256="placeholder",  # SHA will be filled in separately
                    depends=dependency_data.depends[bootstrap_bin_id],
                    bootstrap=bootstrap,
                )
                self.graph.add_edge(
                    bootstrap_bin_id, cimple.models.pkg.bootstrap_src_id(pkg_config.root.id)
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

            # Remove connection with source package
            self.graph.remove_edge(bin_pkg_id, pkg_id)

            # Do not remove any runtime dependency on this package
            # When the node is removed, all edges to this node will be marked as broken edges.

            del self.bin_pkg_map[bin_pkg_id]
            self.graph.remove_node(bin_pkg_id)

        # Remove all build dependency edges for this source package
        for dep in src_snapshot_pkg.build_depends:
            self.graph.remove_edge(pkg_id, dep)

        # Remove source package
        del self.src_pkg_map[pkg_id]
        self.graph.remove_node(pkg_id)

    def get_src_pkg(self, pkg_id: pkg_models.SrcPkgId) -> snapshot_models.SnapshotSrcPkg:
        """
        Get source package data from snapshot.
        """
        if pkg_id in self.src_pkg_map:
            return self.src_pkg_map[pkg_id]

        if pkg_id in self.bootstrap_src_pkg_map:
            return self.bootstrap_src_pkg_map[pkg_id]

        raise RuntimeError(f"Package {pkg_id} does not exist in snapshot.")

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

    def is_broken(self) -> bool:
        """
        Check that the snapshot has no broken edges.
        """
        return self.graph.is_broken()

    def _update_with_adds(
        self,
        pkg_adds: list[cimple.models.snapshot.SnapshotChangeAdd],
        pkg_processor: cimple.pkg.ops.PkgOps,
        pkg_index_path: pathlib.Path,
        bootstrap: bool = False,
    ):
        """
        Helper to process package additions.
        """
        for pkg_add in pkg_adds:
            dependency_data = pkg_processor.resolve_dependencies(
                pkg_add.id, pkg_add.version, pi_path=pkg_index_path, is_bootstrap=bootstrap
            )
            config = cimple.models.pkg_config.load_pkg_config(
                pkg_index_path, pkg_add.id, pkg_add.version
            )
            self.add_pkg(config, dependency_data, bootstrap=bootstrap)

    def _update_with_updates(
        self,
        pkg_updates: list[cimple.models.snapshot.SnapshotChangeUpdate],
        pkg_processor: cimple.pkg.ops.PkgOps,
        pkg_index_path: pathlib.Path,
        bootstrap: bool = False,
    ):
        """
        Helper to process package updates.
        """
        for pkg_update in pkg_updates:
            # Remove old package
            self.remove_pkg(pkg_update.id)

            if bootstrap:
                bootstrap_src_id = cimple.models.pkg.bootstrap_src_id(pkg_update.id)
                self.remove_pkg(bootstrap_src_id)

            # Add new package
            config = cimple.models.pkg_config.load_pkg_config(
                pkg_index_path, pkg_update.id, pkg_update.to_version
            )
            dependency_data = pkg_processor.resolve_dependencies(
                pkg_update.id,
                pkg_update.to_version,
                pi_path=pkg_index_path,
                is_bootstrap=bootstrap,
            )
            self.add_pkg(config, dependency_data, bootstrap=bootstrap)

    def update_with_changes(
        self,
        *,
        pkg_changes: cimple.models.snapshot.SnapshotChanges,
        bootstrap_changes: cimple.models.snapshot.SnapshotChanges,
        pkg_processor: cimple.pkg.ops.PkgOps,
        pkg_index_path: pathlib.Path,
    ) -> cimple.graph.BuildGraph:
        """
        Compute the build order for the packages to be added/updated.
        Also computes the new build dependency graph as part of the process.

        Because the new updates are expected to built right after this, all sha256
        fields are set to "placeholder" and will be filled in later.
        """

        # Step 1: Apply changes to the graph
        # Changes to the graph is processed in the following order:
        # 1. Bootstrap and normal removal (this step might leave incomplete edges in the graph)
        # 2. Bootstrap addition
        # 3. Bootstrap updates (updates might depend on newly added bootstrap packages)
        # 4. Normal addition (normal additions can depend on bootstrap additions)
        # 5. Normal updates (normal updates can depend on bootstrap additions and normal additions)
        # 6. Validate that all dependencies are satisfied

        # Bootstrap removals
        for pkg_remove in bootstrap_changes.remove:
            self.remove_pkg(pkg_remove)
            self.remove_pkg(cimple.models.pkg.bootstrap_src_id(pkg_remove))

        # Normal removals
        for pkg_remove in pkg_changes.remove:
            self.remove_pkg(pkg_remove)

        # Bootstrap additions
        self._update_with_adds(bootstrap_changes.add, pkg_processor, pkg_index_path, bootstrap=True)

        # Bootstrap updates
        self._update_with_updates(
            bootstrap_changes.update, pkg_processor, pkg_index_path, bootstrap=True
        )

        # Normal additions
        self._update_with_adds(pkg_changes.add, pkg_processor, pkg_index_path, bootstrap=False)

        # Normal updates
        self._update_with_updates(
            pkg_changes.update, pkg_processor, pkg_index_path, bootstrap=False
        )

        # Resolve all build and runtime dependencies and make sure they are satisfied
        for pkg in itertools.chain(pkg_changes.add, pkg_changes.update):
            deps_are_valid = self.validate_depends(pkg.id)
            if not deps_are_valid:
                raise RuntimeError(f"Unable to resolve dependencies for package {pkg.id.name}")

        if self.is_broken():
            raise RuntimeError(
                "Snapshot has broken edges after applying changes! Broken edges:"
                f" {self.graph.broken_edges}"
            )

        # Step 2: Compute the build graph
        requirement_graph: cimple.graph.Graph[pkg_models.PkgId] = self.graph.reverse(copy=True)

        pkgs_to_build: set[cimple.models.pkg.PkgId] = set()

        # Because additions and removals are split between changes and bootstrap_changes,
        # "newly added" packages can have dependents in the unchanged build graph. For example,
        # package A can be removed as a normal package, but its bootstrap version can be newly
        # added. Therefore, we need to traverse the dependents of all added and updated packages in
        # both sets.
        all_affected_pkgs = [
            *[add.id for add in pkg_changes.add],
            *[update.id for update in pkg_changes.update],
            *[add.id for add in bootstrap_changes.add],
            *[update.id for update in bootstrap_changes.update],
            *[cimple.models.pkg.bootstrap_src_id(add.id) for add in bootstrap_changes.add],
            *[cimple.models.pkg.bootstrap_src_id(update.id) for update in bootstrap_changes.update],
        ]

        # All updated packages and their dependents need to be built
        for affected_pkg in all_affected_pkgs:
            pkgs_to_build.add(affected_pkg)
            pkgs_to_build.update(requirement_graph.descendants(affected_pkg))

        # Set the sha256 fields of the packages to be built to "placeholder"
        for pkg_id in pkgs_to_build:
            if pkg_id.type != "bin":
                continue

            if pkg_id in self.bootstrap_bin_pkg_map:
                self.bootstrap_bin_pkg_map[pkg_id].sha256 = "placeholder"
            else:
                self.bin_pkg_map[pkg_id].sha256 = "placeholder"

        # Get subgraph of packages to build
        return cimple.graph.BuildGraph(requirement_graph.subgraph(pkgs_to_build))

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
            bootstrap_pkgs=[],
            ancestor=None,
            changes=snapshot_models.SnapshotChanges(add=[], remove=[], update=[]),
            bootstrap_changes=snapshot_models.SnapshotChanges(add=[], remove=[], update=[]),
        )
    else:
        snapshot_path = cimple.constants.cimple_snapshot_dir / f"{name}.json"
        with snapshot_path.open("r") as f:
            snapshot_data = snapshot_models.SnapshotModel.model_validate_json(f.read())

    return CimpleSnapshot(snapshot_data)
