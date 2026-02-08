import pathlib
import tarfile
import tempfile

import pydantic

import cimple.graph
import cimple.models.pkg
import cimple.models.snapshot
import cimple.pkg.ops
import cimple.snapshot.core
from cimple import constants, logging
from cimple import hash as cimple_hash
from cimple import tarfile as cimple_tarfile
from cimple.models import pkg as pkg_models
from cimple.pkg import ops as pkg_ops


class VersionedSourcePackage(pydantic.BaseModel):
    id: pkg_models.SrcPkgId
    version: str


def compute_build_graph(
    snapshot: cimple.snapshot.core.CimpleSnapshot,
    pkg_changes: cimple.models.snapshot.SnapshotChanges,
    bootstrap_changes: cimple.models.snapshot.SnapshotChanges,
) -> cimple.graph.BuildGraph:
    """
    Compute the build order for the packages in the snapshot.

    The given snapshot needs to already have the changes applied to it.

    The returned graph is a requirement graph, where an edge from A -> B means A requires B to be
    available first. This is essentially the reverse of the dependency graph.
    """
    requirement_graph: cimple.graph.Graph[pkg_models.PkgId] = snapshot.graph.reverse(copy=True)

    pkgs_to_build = set()

    # Because additions and removals are split between changes and bootstrap_changes,
    # "newly added" packages can have dependents in the unchanged build graph. For example,
    # package A can be removed as a normal package, but its bootstrap version can be newly added.
    # Therefore, we need to traverse the dependents of all added and updated packages in both sets.
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

    # Get subgraph of packages to build
    return cimple.graph.BuildGraph(requirement_graph.subgraph(pkgs_to_build))


def execute_build_graph(
    build_graph: cimple.graph.BuildGraph,
    *,
    snapshot: cimple.snapshot.core.CimpleSnapshot,
    pkg_processor: pkg_ops.PkgOps,
    pkg_index_path: pathlib.Path,
    parallel: int,
    extra_paths: list[pathlib.Path] | None = None,
):
    """
    Execute the build graph.
    """

    while not build_graph.is_empty():
        [next_pkg] = build_graph.get_pkgs_to_build(max_count=1)

        # Build package
        output_paths = pkg_processor.build_pkg(
            next_pkg,
            pi_path=pkg_index_path,
            cimple_snapshot=snapshot,
            build_options=cimple.pkg.ops.PackageBuildOptions(
                parallel=parallel, extra_paths=extra_paths or []
            ),
        )

        # Tar it up and add to pkg store
        # Initially tar it up in a generic name because the sha cannot yet be determined
        for binary_name, output_path in output_paths.items():
            with tempfile.TemporaryDirectory() as tmp_dir:
                tar_path = pathlib.Path(tmp_dir) / "pkg.tar.xz"
                with tarfile.open(tar_path, "w:xz") as out_tar:
                    # TODO: is TarFile.add deterministic?
                    out_tar.add(output_path, ".", filter=cimple_tarfile.reproducible_add_filter)

                # Move tarball to pkg store
                tar_hash = cimple_hash.hash_file(tar_path, "sha256")
                new_file_name = f"{binary_name}-{tar_hash}.tar.xz"
                new_file_path = constants.cimple_pkg_dir / new_file_name
                if new_file_path.exists():
                    logging.info("Reusing %s", new_file_name)
                else:
                    _ = tar_path.rename(new_file_path)

            # Commit SHA into snapshot
            bin_pkg_id = pkg_models.BinPkgId(binary_name)
            snapshot.bin_pkg_map[bin_pkg_id].sha256 = tar_hash

        # Mark package as built in the build graph
        build_graph.mark_pkgs_built(next_pkg)


def process_changes(
    origin_snapshot: cimple.snapshot.core.CimpleSnapshot,
    pkg_changes: cimple.models.snapshot.SnapshotChanges,
    bootstrap_changes: cimple.models.snapshot.SnapshotChanges,
    *,
    pkg_index_path: pathlib.Path,
    parallel: int,
    extra_paths: list[pathlib.Path] | None = None,
) -> None:
    """
    Process snapshot changes (add, remove, update).
    """
    pkg_processor = pkg_ops.PkgOps()

    # Construct new snapshot graph
    origin_snapshot.update_with_changes(
        pkg_changes=pkg_changes,
        bootstrap_changes=bootstrap_changes,
        pkg_processor=pkg_processor,
        pkg_index_path=pkg_index_path,
    )

    # Compute build graph
    build_graph = compute_build_graph(origin_snapshot, pkg_changes, bootstrap_changes)

    # Execute build graph
    execute_build_graph(
        build_graph,
        snapshot=origin_snapshot,
        pkg_processor=pkg_processor,
        pkg_index_path=pkg_index_path,
        parallel=parallel,
        extra_paths=extra_paths,
    )

    # Make sure all binary packages are built, if not, there's a bug
    if not origin_snapshot.binary_pkgs_are_complete():
        raise RuntimeError("Not all binary packages have been built! This is a bug.")
