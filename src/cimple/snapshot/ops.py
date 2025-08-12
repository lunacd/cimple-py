import copy
import pathlib
import tarfile
import tempfile

import pydantic

from cimple import common, pkg
from cimple.models import pkg as pkg_models
from cimple.models import pkg_config
from cimple.snapshot import core


class VersionedSourcePackage(pydantic.BaseModel):
    name: pkg_models.SrcPkgId
    version: str


def add(
    origin_snapshot: core.CimpleSnapshot,
    packages: list[VersionedSourcePackage],
    pkg_index_path: pathlib.Path,
    parallel: int,
) -> core.CimpleSnapshot:
    # Ensure needed paths exist
    common.util.ensure_path(common.constants.cimple_snapshot_dir)
    common.util.ensure_path(common.constants.cimple_pkg_dir)

    new_snapshot = copy.deepcopy(origin_snapshot)

    # TODO: walk dependency graph to determine the list of packages to build
    # For now, assume it's only the added packages that needs building
    packages_to_build = packages

    # Build package
    for package in packages_to_build:
        config = pkg_config.load_pkg_config(pkg_index_path, package.name, package.version)

        # Add package to snapshot
        new_snapshot.add_src_pkg(
            pkg_id=package.name,
            pkg_version=package.version,
            build_depends=config.root.build_depends,
        )

        # Build package
        output_path = pkg.ops.build_pkg(
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
            new_file_name = f"{package.name}-{package.version}-{tar_hash}.tar.xz"
            new_file_path = common.constants.cimple_pkg_dir / new_file_name
            if new_file_path.exists():
                common.logging.info("Reusing %s", new_file_name)
            else:
                tar_path.rename(new_file_path)

        # TODO: this needs to be repeated for each binary package
        new_snapshot.add_bin_pkg(
            pkg_id=pkg_models.bin_pkg_id(pkg_models.unqualified_pkg_name(package.name)),
            src_pkg=package.name,
            pkg_sha256=tar_hash,
            depends=[],
        )

    return new_snapshot


def remove():
    pass
