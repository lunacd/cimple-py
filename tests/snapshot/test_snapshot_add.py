import importlib
import importlib.resources
import typing

import pytest

import cimple.constants
import cimple.snapshot.core
from cimple.models import pkg as pkg_models
from cimple.models import snapshot as snapshot_models
from cimple.snapshot import ops as snapshot_ops

if typing.TYPE_CHECKING:
    import pathlib

    import pyfakefs.fake_filesystem
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
        match="Binary dependency cygwin for package make not found in snapshot",
    ):
        _ = snapshot_ops.add(
            root_snapshot,
            [
                snapshot_ops.VersionedSourcePackage(
                    id=pkg_models.SrcPkgId("make"), version="4.4.1-2"
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
            pkg_models.BinPkgId("cygwin"),
            pkg_models.BinPkgId("libguile3.0_1"),
            pkg_models.BinPkgId("libintl8"),
        ]
    )

    # WHEN: adding a package to the snapshot
    new_snapshot = snapshot_ops.add(
        snapshot,
        [snapshot_ops.VersionedSourcePackage(id=pkg_models.SrcPkgId("make"), version="4.4.1-2")],
        cimple_pi,
        parallel=1,
    )

    # THEN: the package should be in the snapshot
    assert pkg_models.SrcPkgId("make") in new_snapshot.pkg_map
    assert pkg_models.BinPkgId("make") in new_snapshot.pkg_map

    # THEN: pkg exists in the pkg store
    make_bin_pkg = new_snapshot.pkg_map[pkg_models.BinPkgId("make")].root
    assert snapshot_models.snapshot_pkg_is_bin(make_bin_pkg)
    sha256 = make_bin_pkg.sha256
    assert (cimple.constants.cimple_pkg_dir / f"make-{sha256}.tar.xz").exists()

    # THEN: the dependencies are correct
    assert all(d.type == "bin" for d in make_bin_pkg.depends)
    assert sorted([d.name for d in make_bin_pkg.depends]) == [
        "cygwin",
        "libguile3.0_1",
        "libintl8",
    ]


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
            pkg_models.BinPkgId("libguile3.0_1"),
            pkg_models.BinPkgId("cygwin"),
            pkg_models.BinPkgId("libiconv2"),
        ]
    )

    # WHEN: adding both make and cygwin to the snapshot
    # Note that cygwin is specified after make, in the reverse order of their dependency
    # relationship. This is to verify that the order of packages specified does not matter.
    new_snapshot = snapshot_ops.add(
        snapshot,
        [
            snapshot_ops.VersionedSourcePackage(id=pkg_models.SrcPkgId("make"), version="4.4.1-2"),
            snapshot_ops.VersionedSourcePackage(
                id=pkg_models.SrcPkgId("libintl8"), version="0.22.5-1"
            ),
        ],
        cimple_pi,
        parallel=1,
    )

    # THEN: the package should be in the snapshot
    assert pkg_models.SrcPkgId("make") in new_snapshot.pkg_map
    assert pkg_models.BinPkgId("make") in new_snapshot.pkg_map

    # THEN: pkg exists in the pkg store
    make_bin_pkg = new_snapshot.pkg_map[pkg_models.BinPkgId("make")].root
    assert snapshot_models.snapshot_pkg_is_bin(make_bin_pkg)
    sha256 = make_bin_pkg.sha256
    assert (cimple.constants.cimple_pkg_dir / f"make-{sha256}.tar.xz").exists()

    # THEN: the dependencies are correct
    assert all(d.type == "bin" for d in make_bin_pkg.depends)
    assert sorted([d.name for d in make_bin_pkg.depends]) == [
        "cygwin",
        "libguile3.0_1",
        "libintl8",
    ]


@pytest.mark.usefixtures("basic_cimple_store")
def test_snapshot_add_custom(
    cimple_pi: pathlib.Path, mocker: MockerFixture, fs: pyfakefs.fake_filesystem.FakeFilesystem
):
    # GIVEN: a snapshot with make's binary dependencies
    snapshot = cimple.snapshot.core.load_snapshot("test-snapshot")
    with importlib.resources.path("tests", "data", "dummy_output") as dummy_output_path:
        fs.makedirs(dummy_output_path.as_posix())
        fs.create_file(dummy_output_path / "custom.txt")
        mocker.patch("cimple.pkg.ops.PkgOps._build_custom_pkg", return_value=dummy_output_path)

    # WHEN: adding a package to the snapshot
    new_snapshot = snapshot_ops.add(
        snapshot,
        [snapshot_ops.VersionedSourcePackage(id=pkg_models.SrcPkgId("custom"), version="0.0.1-1")],
        cimple_pi,
        parallel=1,
    )

    # THEN: the package should be in the snapshot
    assert pkg_models.SrcPkgId("custom") in new_snapshot.pkg_map
    assert pkg_models.BinPkgId("custom") in new_snapshot.pkg_map

    # THEN: pkg exists in the pkg store
    make_bin_pkg = new_snapshot.pkg_map[pkg_models.BinPkgId("custom")].root
    assert snapshot_models.snapshot_pkg_is_bin(make_bin_pkg)
    sha256 = make_bin_pkg.sha256
    assert (cimple.constants.cimple_pkg_dir / f"custom-{sha256}.tar.xz").exists()

    # THEN: the dependencies are correct
    assert all(d.type == "bin" for d in make_bin_pkg.depends)
    assert sorted([d.name for d in make_bin_pkg.depends]) == [
        "pkg2-bin",
    ]
