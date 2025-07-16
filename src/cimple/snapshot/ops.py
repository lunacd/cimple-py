import datetime
import pathlib
import tarfile
import tempfile

import cimple.common as common
import cimple.pkg as pkg
import cimple.snapshot as snapshot


def add(
    origin_snapshot: snapshot.models.Snapshot,
    packages: list[pkg.PkgId],
    pkg_index_path: pathlib.Path,
) -> snapshot.models.Snapshot:
    # Ensure needed paths exist
    common.util.ensure_path(common.constants.cimple_snapshot_dir)
    common.util.ensure_path(common.constants.cimple_pkg_dir)

    snapshot_data = origin_snapshot

    # Add package to snapshot
    for package in packages:
        package_path = pkg_index_path / "pkg" / package.name / package.version
        pkg_config = pkg.pkg_config.load_pkg_config(package_path)
        snapshot_data.pkgs.append(
            snapshot.models.SnapshotPkg(
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
        output_path = pkg.build_pkg(package_path)

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


def dump_snapshot(snapshot_data: snapshot.models.Snapshot):
    snapshot_name = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d-%H%M%S")
    snapshot_manifest = common.constants.cimple_snapshot_dir / f"{snapshot_name}.json"
    if snapshot_manifest.exists():
        raise RuntimeError(f"Snapshot {snapshot_name} already exists!")
    with snapshot_manifest.open("w") as f:
        f.write(snapshot_data.model_dump_json())


def load_snapshot(name: str) -> snapshot.models.Snapshot:
    if name == "root":
        return snapshot.models.Snapshot(
            version=0,
            pkgs=[],
            ancestor="root",
            changes=snapshot.models.SnapshotChanges(add=[], remove=[]),
        )

    snapshot_path = common.constants.cimple_snapshot_dir / f"{name}.json"
    with snapshot_path.open("r") as f:
        return snapshot.models.Snapshot.model_validate_json(f.read())
