import copy
import pathlib
import tarfile
import tempfile
import typing

import pydantic

import cimple.pkg.ops
from cimple import constants, logging, util
from cimple import hash as cimple_hash
from cimple import tarfile as cimple_tarfile
from cimple.models import pkg as pkg_models
from cimple.pkg import ops as pkg_ops

if typing.TYPE_CHECKING:
    from cimple.snapshot import core as snapshot_core


class VersionedSourcePackage(pydantic.BaseModel):
    id: pkg_models.SrcPkgId
    version: str


def add(
    origin_snapshot: snapshot_core.CimpleSnapshot,
    packages: list[VersionedSourcePackage],
    pkg_index_path: pathlib.Path,
    parallel: int,
    extra_paths: list[pathlib.Path] | None = None,
) -> snapshot_core.CimpleSnapshot:
    if extra_paths is None:
        extra_paths = []

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
            package.id, package.version, pi_path=pkg_index_path
        )
        package_dependencies[package.id] = dependency_data
        for bin_pkg in dependency_data.depends:
            binaries_will_built.add(bin_pkg)
    for package in packages_to_build:
        # Check build and runtime dependencies are available in the snapshot
        for dep in package_dependencies[package.id].build_depends:
            if dep not in new_snapshot.bin_pkg_map:
                raise RuntimeError(
                    f"Build dependency {dep} for package {package.id.name} not found in snapshot"
                )
        for bin_dep_list in package_dependencies[package.id].depends.values():
            for dep in bin_dep_list:
                # Binary dependencies can be either in the snapshot or produced by the package being
                # built
                if dep not in new_snapshot.bin_pkg_map and dep not in binaries_will_built:
                    raise RuntimeError(
                        f"Binary dependency {dep.name} for package {package.id.name}"
                        " not found in snapshot"
                    )

    # Build package
    for package in packages_to_build:
        logging.info("Building %s-%s", package.id.name, package.version)

        # Add package to snapshot
        new_snapshot.add_src_pkg(
            pkg_id=package.id,
            pkg_version=package.version,
            build_depends=package_dependencies[package.id].build_depends,
        )

        # Build package
        output_paths = pkg_processor.build_pkg(
            package.id,
            package.version,
            pi_path=pkg_index_path,
            cimple_snapshot=new_snapshot,
            build_options=cimple.pkg.ops.PackageBuildOptions(
                parallel=parallel, extra_paths=extra_paths
            ),
        )

        # Tar it up and add to snapshot
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

            bin_pkg_id = pkg_models.BinPkgId(binary_name)
            new_snapshot.add_bin_pkg(
                pkg_id=bin_pkg_id,
                src_pkg=package.id,
                pkg_sha256=tar_hash,
                depends=package_dependencies[package.id].depends[bin_pkg_id],
            )

    return new_snapshot


def remove():
    pass
