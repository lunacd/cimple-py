import pathlib
import tarfile

import cimple.common as common
import cimple.snapshot as snapshot


def install_pkg(target_path: pathlib.Path, pkg_name: str, snapshot_name: str):
    # TODO: install transitive dependencies

    pkg_full_name = snapshot.ops.get_pkg_from_snapshot(pkg_name, snapshot_name)

    if pkg_full_name is None:
        raise RuntimeError(f"Requested package {pkg_name} not found in snapshot {snapshot_name}.")

    with tarfile.open(common.constants.cimple_pkg_dir / pkg_full_name, "r") as tar:
        tar.extractall(target_path, filter=common.tarfile.writable_extract_filter)
