import datetime
import pathlib
import tarfile
import tempfile

import cimple.common as common
import cimple.models as models
import cimple.pkg as pkg


def add(
    origin_snapshot_map: models.snapshot.SnapshotMap,
    packages: list[models.pkg.PkgId],
    pkg_index_path: pathlib.Path,
    parallel: int,
) -> models.snapshot.SnapshotMap:
    # Ensure needed paths exist
    common.util.ensure_path(common.constants.cimple_snapshot_dir)
    common.util.ensure_path(common.constants.cimple_pkg_dir)

    new_snapshot_map = origin_snapshot_map

    # Add package to snapshot
    for package in packages:
        package_path = pkg_index_path / "pkg" / package.name / package.version
        pkg_config = pkg.pkg_config.load_pkg_config(package_path)
        new_snapshot_map.pkgs[package.name] = models.snapshot.SnapshotPkg(
            name=package.name,
            version=package.version,
            depends=pkg_config.pkg.depends,
            build_depends=pkg_config.pkg.build_depends,
            compression_method="xz",
            sha256="to_be_built",
        )

    # TODO: walk dependency graph to determine the list of packages to build
    # For now, assume it's only the added packages that needs building
    packages_to_build = packages

    # Build package
    for package in packages_to_build:
        package_path = pkg_index_path / "pkg" / package.name / package.version
        output_path = pkg.ops.build_pkg(
            package_path, parallel=parallel, snapshot_map=origin_snapshot_map
        )

        # Tar it up and add to snapshot
        # Initially tar it up in a generic name because the sha cannot yet be determined
        with tempfile.TemporaryDirectory() as tmp_dir:
            tar_path = pathlib.Path(tmp_dir) / "pkg.tar.xz"
            with tarfile.open(tar_path, "w:xz") as out_tar:
                # TODO: is TarFile.add deterministic?
                out_tar.add(output_path, ".", filter=common.tarfile.reproducible_add_filter)

            # Move tarball to pkg store
            tar_hash = common.hash.sha256_file(tar_path)
            new_file_name = f"{package.name}-{package.version}-{tar_hash}.tar.xz"
            new_file_path = common.constants.cimple_pkg_dir / new_file_name
            if new_file_path.exists():
                common.logging.info("Reusing %s", new_file_name)
            else:
                tar_path.rename(new_file_path)

        new_snapshot_map.pkgs[package.name].sha256 = tar_hash

    return new_snapshot_map


def remove():
    pass


def dump_snapshot(snapshot_map: models.snapshot.SnapshotMap):
    snapshot_name = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d-%H%M%S")
    snapshot_map.name = snapshot_name
    snapshot_manifest = common.constants.cimple_snapshot_dir / f"{snapshot_name}.json"
    if snapshot_manifest.exists():
        raise RuntimeError(f"Snapshot {snapshot_name} already exists!")
    snapshot_data = models.snapshot.get_snapshot_json_from_map(snapshot_map)
    with snapshot_manifest.open("w") as f:
        f.write(snapshot_data.model_dump_json())


def load_snapshot(name: str) -> models.snapshot.SnapshotMap:
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

    return models.snapshot.get_snapshot_map_from_json(snapshot_data)
