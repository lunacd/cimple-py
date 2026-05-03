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
from cimple.pkg import ops as pkg_ops


class VersionedSourcePackage(pydantic.BaseModel):
    id: cimple.models.pkg.SrcPkgId
    version: str


def execute_build_graph(
    build_graph: cimple.graph.BuildGraph,
    *,
    snapshot: cimple.snapshot.core.CimpleSnapshot,
    pkg_processor: pkg_ops.PkgOps,
    pkg_index_path: pathlib.Path,
    parallel: int,
    extra_paths: list[str] | None = None,
):
    """
    Execute the build graph.
    """

    while not build_graph.is_empty():
        [next_pkg] = build_graph.get_pkgs_to_build(max_count=1)

        # Build package
        is_bootstrap = snapshot.is_in_bootstrap(next_pkg)
        output_paths = pkg_processor.build_pkg(
            next_pkg,
            pi_path=pkg_index_path,
            cimple_snapshot=snapshot,
            build_options=cimple.pkg.ops.PackageBuildOptions(
                parallel=parallel, extra_paths=extra_paths or []
            ),
            bootstrap=is_bootstrap,
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
            bin_pkg_id = cimple.models.pkg.BinPkgId(binary_name)
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
    extra_paths: list[str] | None = None,
) -> None:
    """
    Process snapshot changes (add, remove, update).
    """
    pkg_processor = pkg_ops.PkgOps()

    # Construct new snapshot graph
    build_graph = origin_snapshot.update_with_changes(
        pkg_changes=pkg_changes,
        bootstrap_changes=bootstrap_changes,
        pkg_processor=pkg_processor,
        pkg_index_path=pkg_index_path,
    )

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
