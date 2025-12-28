import cimple.models.pkg
import cimple.models.snapshot
import cimple.models.stream
import cimple.snapshot.core


def resolve_snapshot_changes(
    stream_data: cimple.models.stream.Stream, current_snapshot: cimple.snapshot.core.CimpleSnapshot
) -> cimple.models.snapshot.SnapshotChanges:
    """
    Given a stream config, resolve the list of package IDs that should be included in the target
    snapshot.
    """
    snapshot_changes = cimple.models.snapshot.SnapshotChanges(add=[], remove=[], update=[])

    for target_pkg, target_pkg_version in stream_data.pkgs.items():
        if (
            target_pkg not in current_snapshot.src_pkg_map
            or target_pkg_version != current_snapshot.src_pkg_map[target_pkg].version
        ):
            snapshot_changes.add.append(
                cimple.models.snapshot.SnapshotChangeAdd(
                    name=target_pkg,
                    version=target_pkg_version,
                )
            )

    return snapshot_changes
