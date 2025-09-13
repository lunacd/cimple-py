import copy
import pathlib
import tarfile
import tempfile

import pydantic

from cimple import common
from cimple.models import pkg as pkg_models
from cimple.pkg import ops as pkg_ops
from cimple.snapshot import core as snapshot_core


class VersionedSourcePackage(pydantic.BaseModel):
    name: pkg_models.SrcPkgId
    version: str


def add(
    origin_snapshot: snapshot_core.CimpleSnapshot,
    packages: list[VersionedSourcePackage],
    pkg_index_path: pathlib.Path,
    parallel: int,
) -> snapshot_core.CimpleSnapshot:
    # Ensure needed paths exist
    common.util.ensure_path(common.constants.cimple_snapshot_dir)
    common.util.ensure_path(common.constants.cimple_pkg_dir)

    new_snapshot = copy.deepcopy(origin_snapshot)

    # TODO: walk dependency graph to determine the list of packages to build
    # For now, assume it's only the added packages that needs building
    packages_to_build = packages

    pkg_processor = pkg_ops.PkgOps()

    # Build package
    for package in packages_to_build:
        # Resolve dependencies
        # TODO: make sure dependencies are resolvable before proceeding with build
        dependency_data = pkg_processor.resolve_dependencies(
            package.name, package.version, pi_path=pkg_index_path
        )

        # Add package to snapshot
        new_snapshot.add_src_pkg(
            pkg_id=package.name,
            pkg_version=package.version,
            build_depends=dependency_data.build_depends,
        )

        # Build package
        output_path = pkg_processor.build_pkg(
            package.name,
            package.version,
            pi_path=pkg_index_path,
            parallel=parallel,
            cimple_snapshot=new_snapshot,
        )

        # Tar it up and add to snapshot
        # Initially tar it up in a generic name because the sha cannot yet be determined
        with tempfile.TemporaryDirectory() as tmp_dir:
            tar_path = pathlib.Path(tmp_dir) / "pkg.tar.xz"
            with tarfile.open(tar_path, "w:xz") as out_tar:
                # TODO: is TarFile.add deterministic?
                out_tar.add(output_path, ".", filter=common.tarfile.reproducible_add_filter)

            # Move tarball to pkg store
            tar_hash = common.hash.hash_file(tar_path, "sha256")
            new_file_name = f"{(pkg_models.unqualified_pkg_name(package.name))}-{package.version}-{
                tar_hash
            }.tar.xz"
            new_file_path = common.constants.cimple_pkg_dir / new_file_name
            if new_file_path.exists():
                common.logging.info("Reusing %s", new_file_name)
            else:
                tar_path.rename(new_file_path)

        # TODO: this needs to be repeated for each binary package
        bin_pkg_id = pkg_models.bin_pkg_id(pkg_models.unqualified_pkg_name(package.name))
        new_snapshot.add_bin_pkg(
            pkg_id=bin_pkg_id,
            src_pkg=package.name,
            pkg_sha256=tar_hash,
            depends=dependency_data.depends[bin_pkg_id],
        )

    return new_snapshot


def remove():
    pass
