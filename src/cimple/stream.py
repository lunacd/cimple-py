import tomllib
import typing
from typing import TYPE_CHECKING

import cimple.models.pkg
import cimple.models.snapshot
import cimple.models.stream
import cimple.snapshot.core

if TYPE_CHECKING:
    import pathlib


def load_stream_config(
    pi_path: pathlib.Path, stream_name: str
) -> cimple.models.stream.StreamConfig:
    """
    Load a stream configuration by name.
    """
    stream_config_path = pi_path / "stream" / f"{stream_name}.toml"
    with stream_config_path.open("rb") as f:
        stream_config_dict = tomllib.load(f)
    return cimple.models.stream.StreamConfig.model_validate(stream_config_dict)


def _resolve_pkg_changes(
    current_src_pkgs: dict[cimple.models.pkg.SrcPkgId, cimple.models.snapshot.SnapshotSrcPkg],
    target_pkgs: list[cimple.models.pkg.VersionedSrcPkg],
) -> cimple.models.snapshot.SnapshotChanges:
    snapshot_changes = cimple.models.snapshot.SnapshotChanges(add=[], remove=[], update=[])

    for target_pkg in target_pkgs:
        # Adds
        if target_pkg.id not in current_src_pkgs:
            snapshot_changes.add.append(
                cimple.models.snapshot.SnapshotChangeAdd(
                    name=target_pkg.name,
                    version=target_pkg.version,
                )
            )
            continue

        # Updates
        if current_src_pkgs[target_pkg.id].version != target_pkg.version:
            snapshot_changes.update.append(
                cimple.models.snapshot.SnapshotChangeUpdate.model_construct(
                    name=target_pkg.name,
                    from_version=current_src_pkgs[target_pkg.id].version,
                    to_version=target_pkg.version,
                )
            )
            continue

    # Removals
    all_pkgs = {pkg.id for pkg in target_pkgs}
    for current_pkg in current_src_pkgs:
        if current_pkg not in all_pkgs:
            snapshot_changes.remove.append(current_pkg)

    return snapshot_changes


class ResolvedSnapshotChanges(typing.NamedTuple):
    pkg_changes: cimple.models.snapshot.SnapshotChanges
    bootstrap_changes: cimple.models.snapshot.SnapshotChanges

def resolve_snapshot_changes(
    stream_config: cimple.models.stream.StreamConfig,
    current_snapshot: cimple.snapshot.core.CimpleSnapshot,
) -> ResolvedSnapshotChanges:
    """
    Given a stream config, resolve the list of package IDs that should be included in the target
    snapshot.
    """

    pkg_changes = _resolve_pkg_changes(
        current_src_pkgs=current_snapshot.src_pkg_map, target_pkgs=stream_config.pkgs
    )

    bootstrap_changes = _resolve_pkg_changes(
        current_src_pkgs=current_snapshot.bootstrap_src_pkg_map,
        target_pkgs=stream_config.bootstrap_pkgs,
    )

    return ResolvedSnapshotChanges(
        pkg_changes=pkg_changes, bootstrap_changes=bootstrap_changes
    )
