from typing import TYPE_CHECKING

import cimple.models.snapshot
import cimple.models.stream
import cimple.snapshot.core

if TYPE_CHECKING:
    import pathlib


def load_stream(pi_path: pathlib.Path, stream_name: str) -> cimple.models.stream.Stream:
    """
    Load a stream configuration by name.
    """
    stream_path = pi_path / "stream" / f"{stream_name}.json"
    return cimple.models.stream.Stream.model_validate_json(stream_path.read_text())


def resolve_snapshot_changes(
    stream_data: cimple.models.stream.Stream, current_snapshot: cimple.snapshot.core.CimpleSnapshot
) -> cimple.models.snapshot.SnapshotChanges:
    """
    Given a stream config, resolve the list of package IDs that should be included in the target
    snapshot.
    """
    snapshot_changes = cimple.models.snapshot.SnapshotChanges(add=[], remove=[], update=[])

    for target_pkg in stream_data.pkgs:
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
        if current_pkg not in stream_data.all_pkgs:
            snapshot_changes.remove.append(current_pkg)

    return snapshot_changes
