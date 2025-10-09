import typing

import pytest

from cimple import common
from cimple.models import pkg as pkg_models
from cimple.models import snapshot as snapshot_models
from cimple.snapshot import ops as snapshot_ops

if typing.TYPE_CHECKING:
    import pathlib

    from pytest_mock import MockerFixture

    import tests.conftest


@pytest.mark.usefixtures("basic_cimple_store")
def test_snapshot_add_unresolvable_dep(
    cimple_pi: pathlib.Path,
    cygwin_release_content_side_effect: typing.Callable[
        [str], tests.conftest.MockHttpResponse | tests.conftest.MockHttp404Response
    ],
    mocker: MockerFixture,
    helpers: tests.conftest.Helpers,
):
    # GIVEN: a root snapshot
    _ = mocker.patch(
        "cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect
    )
    root_snapshot = helpers.mock_cimple_snapshot([])

    # WHEN: adding a package to the snapshot
    # THEN: an exception is raised because cygwin is not in the snapshot
    with pytest.raises(
        RuntimeError,
        match="Binary dependency bin:cygwin for package src:make not found in snapshot",
    ):
        _ = snapshot_ops.add(
            root_snapshot,
            [
                snapshot_ops.VersionedSourcePackage(
                    name=pkg_models.src_pkg_id("make"), version="4.4.1-2"
                )
            ],
            cimple_pi,
            parallel=1,
        )


@pytest.mark.usefixtures("basic_cimple_store")
def test_snapshot_add_simple(
    cimple_pi: pathlib.Path,
    cygwin_release_content_side_effect: typing.Callable[
        [str], tests.conftest.MockHttpResponse | tests.conftest.MockHttp404Response
    ],
    mocker: MockerFixture,
    helpers: tests.conftest.Helpers,
):
    # GIVEN: a snapshot with make's binary dependencies
    _ = mocker.patch(
        "cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect
    )
    snapshot = helpers.mock_cimple_snapshot(
        [
            pkg_models.bin_pkg_id("cygwin"),
            pkg_models.bin_pkg_id("libguile3.0_1"),
            pkg_models.bin_pkg_id("libintl8"),
        ]
    )

    # WHEN: adding a package to the snapshot
    new_snapshot = snapshot_ops.add(
        snapshot,
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


@pytest.mark.usefixtures("basic_cimple_store")
def test_snapshot_add_multiple_packages(
    cimple_pi: pathlib.Path,
    cygwin_release_content_side_effect: typing.Callable[
        [str], tests.conftest.MockHttpResponse | tests.conftest.MockHttp404Response
    ],
    mocker: MockerFixture,
    helpers: tests.conftest.Helpers,
):
    # GIVEN: a snapshot with make's binary dependencies, except cygwin
    _ = mocker.patch(
        "cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect
    )
    snapshot = helpers.mock_cimple_snapshot(
        [
            pkg_models.bin_pkg_id("libguile3.0_1"),
            pkg_models.bin_pkg_id("cygwin"),
            pkg_models.bin_pkg_id("libiconv2"),
        ]
    )

    # WHEN: adding both make and cygwin to the snapshot
    # Note that cygwin is specified after make, in the reverse order of their dependency
    # relationship. This is to verify that the order of packages specified does not matter.
    new_snapshot = snapshot_ops.add(
        snapshot,
        [
            snapshot_ops.VersionedSourcePackage(
                name=pkg_models.src_pkg_id("make"), version="4.4.1-2"
            ),
            snapshot_ops.VersionedSourcePackage(
                name=pkg_models.src_pkg_id("libintl8"), version="0.22.5-1"
            ),
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
