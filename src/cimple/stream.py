import tomllib
from typing import TYPE_CHECKING

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


def resolve_snapshot_changes(
    stream_config: cimple.models.stream.StreamConfig,
    current_snapshot: cimple.snapshot.core.CimpleSnapshot,
) -> cimple.models.snapshot.SnapshotChanges:
    """
    Given a stream config, resolve the list of package IDs that should be included in the target
    snapshot.
    """
    snapshot_changes = cimple.models.snapshot.SnapshotChanges(add=[], remove=[], update=[])

    for target_pkg in stream_config.pkgs:
        # Adds
        if target_pkg.id not in current_snapshot.src_pkg_map:
            snapshot_changes.add.append(
                cimple.models.snapshot.SnapshotChangeAdd(
                    name=target_pkg.name,
                    version=target_pkg.version,
                )
            )
            continue

        # Updates
        if current_snapshot.src_pkg_map[target_pkg.id].version != target_pkg.version:
            snapshot_changes.update.append(
                cimple.models.snapshot.SnapshotChangeUpdate.model_construct(
                    name=target_pkg.name,
                    from_version=current_snapshot.src_pkg_map[target_pkg.id].version,
                    to_version=target_pkg.version,
                )
            )
            continue

    # Removals
    for current_pkg in current_snapshot.src_pkg_map:
        if current_pkg not in stream_config.all_pkgs:
            snapshot_changes.remove.append(current_pkg)

    return snapshot_changes
