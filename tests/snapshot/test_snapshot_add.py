from cimple import snapshot
from cimple.models import pkg as pkg_models


def test_snapshot_add(cimple_pi, basic_cimple_store, cygwin_release_content_side_effect, mocker):
    # GIVEN: a root snapshot
    mocker.patch("cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect)
    root_snapshot = snapshot.core.load_snapshot("root")

    # WHEN: adding a package to the snapshot
    new_snapshot = snapshot.ops.add(
        root_snapshot,
        [
            snapshot.ops.VersionedSourcePackage(
                name=pkg_models.src_pkg_id("make"), version="4.4.1-2"
            )
        ],
        cimple_pi,
        parallel=1,
    )

    # THEN: the package should be in the snapshot
    assert pkg_models.src_pkg_id("make") in new_snapshot.pkg_map
    assert pkg_models.bin_pkg_id("make") in new_snapshot.pkg_map

    # TODO: make sure package tarball exists and has the right hash
