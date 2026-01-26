from typing import TYPE_CHECKING

import pytest

import cimple.models.pkg
import cimple.models.snapshot
import cimple.snapshot.core
import cimple.stream

if TYPE_CHECKING:
    import pathlib


class TestResolveSnapshotChanges:
    @pytest.mark.usefixtures("basic_cimple_store")
    def test_no_change(self, cimple_pi: pathlib.Path):
        # Given: a snapshot and a matching stream
        cimple_snapshot = cimple.snapshot.core.load_snapshot("test-snapshot")
        stream_data = cimple.stream.load_stream_config(cimple_pi, "test-stream")

        # When: resolving snapshot changes
        pkg_changes, bootstrap_changes = cimple.stream.resolve_snapshot_changes(
            stream_data, cimple_snapshot
        )

        # Then: there should be no changes
        assert pkg_changes.add == []
        assert pkg_changes.remove == []
        assert pkg_changes.update == []
        assert bootstrap_changes.add == []
        assert bootstrap_changes.remove == []
        assert bootstrap_changes.update == []

    @pytest.mark.usefixtures("basic_cimple_store")
    def test_with_changes(self, cimple_pi: pathlib.Path):
        # Given: a snapshot and a stream with changes
        cimple_snapshot = cimple.snapshot.core.load_snapshot("test-snapshot")
        stream_data = cimple.stream.load_stream_config(cimple_pi, "test-stream-with-changes")

        # When: resolving snapshot changes
        pkg_changes, bootstrap_changes = cimple.stream.resolve_snapshot_changes(
            stream_data, cimple_snapshot
        )

        # Then: the changes should be correctly identified
        assert pkg_changes.add == [
            cimple.models.snapshot.SnapshotChangeAdd(name="pkg5", version="1.0"),
        ]
        assert pkg_changes.remove == [cimple.models.pkg.SrcPkgId("pkg1")]
        assert pkg_changes.update == [
            cimple.models.snapshot.SnapshotChangeUpdate.model_construct(
                name="pkg2", from_version="1.0", to_version="2.0"
            )
        ]
        assert bootstrap_changes.add == [
            cimple.models.snapshot.SnapshotChangeAdd(name="bootstrap1", version="1.0")
        ]
        assert bootstrap_changes.remove == []
        assert bootstrap_changes.update == []
