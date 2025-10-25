import copy
import pathlib
import tarfile
import tempfile
import typing

import pydantic

from cimple import constants, logging, util
from cimple import hash as cimple_hash
from cimple import tarfile as cimple_tarfile
from cimple.models import pkg as pkg_models
from cimple.pkg import ops as pkg_ops

if typing.TYPE_CHECKING:
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
    util.ensure_path(constants.cimple_snapshot_dir)
    util.ensure_path(constants.cimple_pkg_dir)

    new_snapshot = copy.deepcopy(origin_snapshot)

    # TODO: walk dependency graph to determine the list of packages to build
    # For now, assume it's only the added packages that needs building
    packages_to_build = packages

    pkg_processor = pkg_ops.PkgOps()

    # Resolve dependencies
    logging.info("Resolving dependencies")
    package_dependencies: dict[pkg_models.SrcPkgId, pkg_ops.PackageDependencies] = {}
    binaries_will_built: set[pkg_models.BinPkgId] = set()
    for package in packages_to_build:
        dependency_data = pkg_processor.resolve_dependencies(
            package.name, package.version, pi_path=pkg_index_path
        )
        package_dependencies[package.name] = dependency_data
        for bin_pkg in dependency_data.depends:
            binaries_will_built.add(bin_pkg)
    for package in packages_to_build:
        # Check build and runtime dependencies are available in the snapshot
        for dep in package_dependencies[package.name].build_depends:
            if dep not in new_snapshot.pkg_map:
                raise RuntimeError(
                    f"Build dependency {dep} for package {package.name} not found in snapshot"
                )
        for bin_dep_list in package_dependencies[package.name].depends.values():
            for dep in bin_dep_list:
                # Binary dependencies can be either in the snapshot or produced by the package being
                # built
                if dep not in new_snapshot.pkg_map and dep not in binaries_will_built:
                    raise RuntimeError(
                        f"Binary dependency {dep} for package {package.name} not found in snapshot"
                    )

    # Build package
    for package in packages_to_build:
        logging.info("Building %s-%s", package.name, package.version)

        # Add package to snapshot
        new_snapshot.add_src_pkg(
            pkg_id=package.name,
            pkg_version=package.version,
            build_depends=package_dependencies[package.name].build_depends,
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
                out_tar.add(output_path, ".", filter=cimple_tarfile.reproducible_add_filter)

            # Move tarball to pkg store
            tar_hash = cimple_hash.hash_file(tar_path, "sha256")
            new_file_name = f"{(pkg_models.unqualified_pkg_name(package.name))}-{package.version}-{
                tar_hash
            }.tar.xz"
            new_file_path = constants.cimple_pkg_dir / new_file_name
            if new_file_path.exists():
                logging.info("Reusing %s", new_file_name)
            else:
                _ = tar_path.rename(new_file_path)

        # TODO: this needs to be repeated for each binary package
        bin_pkg_id = pkg_models.bin_pkg_id(pkg_models.unqualified_pkg_name(package.name))
        new_snapshot.add_bin_pkg(
            pkg_id=bin_pkg_id,
            src_pkg=package.name,
            pkg_sha256=tar_hash,
            depends=package_dependencies[package.name].depends[bin_pkg_id],
        )

    return new_snapshot


def remove():
    pass
