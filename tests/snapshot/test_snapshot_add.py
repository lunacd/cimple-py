from cimple import common
from cimple.models import pkg as pkg_models
from cimple.models import snapshot as snapshot_models
from cimple.snapshot import core as snapshot_core
from cimple.snapshot import ops as snapshot_ops


def test_snapshot_add(cimple_pi, basic_cimple_store, cygwin_release_content_side_effect, mocker):
    # GIVEN: a root snapshot
    mocker.patch("cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect)
    root_snapshot = snapshot_core.load_snapshot("root")

    # WHEN: adding a package to the snapshot
    new_snapshot = snapshot_ops.add(
        root_snapshot,
        [
            snapshot_ops.VersionedSourcePackage(
                name=pkg_models.src_pkg_id("make"), version="4.4.1-2"
            )
        ],
        cimple_pi,
        parallel=1,
    )

    # THEN: the package should be in the snapshot
    assert pkg_models.src_pkg_id("make") in new_snapshot.pkg_map
    assert pkg_models.bin_pkg_id("make") in new_snapshot.pkg_map

    # THEN: pkg exists in the pkg store
    make_bin_pkg = new_snapshot.pkg_map[pkg_models.bin_pkg_id("make")].root
    assert snapshot_models.snapshot_pkg_is_bin(make_bin_pkg)
    sha256 = make_bin_pkg.sha256
    assert (common.constants.cimple_pkg_dir / f"make-4.4.1-2-{sha256}.tar.xz").exists()

    # THEN: the depends are correct
    assert make_bin_pkg.depends == ["bin:cygwin", "bin:libguile3.0_1", "bin:libintl8"]
