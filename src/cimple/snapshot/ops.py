import datetime
import pathlib
import tarfile
import tempfile

import cimple.common as common
import cimple.models as models
import cimple.pkg as pkg


def add(
    origin_snapshot: models.snapshot.Snapshot,
    packages: list[models.pkg.PkgId],
    pkg_index_path: pathlib.Path,
    parallel: int,
) -> models.snapshot.Snapshot:
    # Ensure needed paths exist
    common.util.ensure_path(common.constants.cimple_snapshot_dir)
    common.util.ensure_path(common.constants.cimple_pkg_dir)

    snapshot_data = origin_snapshot

    # Add package to snapshot
    for package in packages:
        package_path = pkg_index_path / "pkg" / package.name / package.version
        pkg_config = pkg.pkg_config.load_pkg_config(package_path)
        snapshot_data.pkgs.append(
            models.snapshot.SnapshotPkg(
                name=package.name,
                version=package.version,
                depends=pkg_config.pkg.depends,
                build_depends=pkg_config.pkg.build_depends,
                compression_method="xz",
                sha256="to_be_built",
            )
        )

    # TODO: walk dependency graph to determine the list of packages to build
    # For now, assume it's only the added packages that needs building
    packages_to_build = packages

    # Build package
    for package in packages_to_build:
        package_path = pkg_index_path / "pkg" / package.name / package.version
        output_path = pkg.ops.build_pkg(
            package_path, parallel=parallel, snapshot_data=origin_snapshot
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

        # NOTE: This is O(num of packages), revisit when package index grows larger
        next(filter(lambda item: item.name == package.name, snapshot_data.pkgs)).sha256 = tar_hash

    return snapshot_data


def remove():
    pass


def dump_snapshot(snapshot_data: models.snapshot.Snapshot):
    snapshot_name = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d-%H%M%S")
    snapshot_manifest = common.constants.cimple_snapshot_dir / f"{snapshot_name}.json"
    if snapshot_manifest.exists():
        raise RuntimeError(f"Snapshot {snapshot_name} already exists!")
    with snapshot_manifest.open("w") as f:
        f.write(snapshot_data.model_dump_json())


def load_snapshot(name: str) -> models.snapshot.Snapshot:
    if name == "root":
        return models.snapshot.Snapshot(
            version=0,
            pkgs=[],
            ancestor="root",
            changes=models.snapshot.SnapshotChanges(add=[], remove=[]),
        )

    snapshot_path = common.constants.cimple_snapshot_dir / f"{name}.json"
    with snapshot_path.open("r") as f:
        return models.snapshot.Snapshot.model_validate_json(f.read())


def get_pkg_from_snapshot(
    pkg_name: str, snapshot_data: models.snapshot.Snapshot
) -> models.snapshot.SnapshotPkg | None:
    # TODO: this is O(n), revisit when package index grows larger
    pkg_data: models.snapshot.SnapshotPkg | None = next(
        filter(lambda item: item.name == pkg_name, snapshot_data.pkgs), None
    )

    return pkg_data
