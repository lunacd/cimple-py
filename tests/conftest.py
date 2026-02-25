# pyright: reportUnknownMemberType=false

import importlib.resources
import pathlib
import typing

import pytest

import cimple.constants
import cimple.models.stream
from cimple.models import pkg as pkg_models
from cimple.snapshot import core as snapshot_core

if typing.TYPE_CHECKING:
    import pyfakefs.fake_filesystem


@pytest.fixture(name="basic_cimple_store")
def basic_cimple_store_fixture(fs: pyfakefs.fake_filesystem.FakeFilesystem) -> None:
    with importlib.resources.path("tests", "data/store") as store_path:
        fs.add_real_directory(
            store_path / "snapshot",
            target_path=cimple.constants.cimple_snapshot_dir,
        )
        fs.add_real_directory(
            store_path / "stream",
            target_path=cimple.constants.cimple_stream_dir,
        )
        fs.add_real_directory(
            store_path / "orig",
            target_path=cimple.constants.cimple_orig_dir,
        )
        fs.add_real_directory(
            store_path / "pkg",
            target_path=cimple.constants.cimple_pkg_dir,
        )
        fs.add_real_directory(
            store_path / "image",
            target_path=cimple.constants.cimple_image_dir,
        )


@pytest.fixture(name="cimple_pi")
def cimple_pi_fixture(fs: pyfakefs.fake_filesystem.FakeFilesystem) -> pathlib.Path:
    pi_target_path = pathlib.Path("/pi")
    with importlib.resources.path("tests", "data/pi") as pi_path:
        _ = fs.add_real_directory(pi_path, target_path=pi_target_path, read_only=True)
    return pi_target_path


class MockHttpResponse:
    def __init__(self, content: bytes):
        self.content: bytes = content
        self.status_code: int = 200
        self.ok: bool = True

    @property
    def text(self):
        return self.content.decode("utf-8")

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP error: {self.status_code}")


class MockHttp404Response:
    def __init__(self):
        self.status_code: int = 404
        self.ok: bool = False


@pytest.fixture(name="cygwin_release_content_side_effect")
def cygwin_release_content_side_effect_fixture(
    fs: pyfakefs.fake_filesystem.FakeFilesystem,
) -> typing.Callable[[str], MockHttpResponse | MockHttp404Response]:
    # It's not necessary for this mock to use pyfakefs.
    # But for test cases that do use pyfakefs, this mock would stop working if it doesn't use it.

    # Use data/cygwin directory to mock Cygwin repository files
    with importlib.resources.path("tests", "data/cygwin") as cygwin_data_root:
        _ = fs.add_real_directory(cygwin_data_root, target_path="/cygwin", read_only=True)

    def mock_cygwin_release_content(url: str):
        assert url.startswith(cimple.constants.cygwin_pkg_url), (
            "Unexpected access to non-Cygwin URL"
        )

        print(f"Mocking Cygwin release content for URL: {url}")

        cygwin_data_root = pathlib.Path("/cygwin")
        relative_path = url[len(cimple.constants.cygwin_pkg_url) :].lstrip("/")
        mock_file_path = cygwin_data_root / relative_path
        print(f"Using local Cygwin data: {mock_file_path}")

        if mock_file_path.exists():
            return MockHttpResponse(mock_file_path.read_bytes())

        return MockHttp404Response()

    return mock_cygwin_release_content


class Helpers:
    @staticmethod
    def mock_cimple_snapshot(
        bin_packages: list[pkg_models.BinPkgId],
    ) -> snapshot_core.CimpleSnapshot:
        snapshot = snapshot_core.load_snapshot("root")
        for bin_pkg in bin_packages:
            src_pkg_id = pkg_models.SrcPkgId(bin_pkg.name)
            snapshot.add_src_pkg(src_pkg_id, "0", [])
            snapshot.add_bin_pkg(bin_pkg, src_pkg_id, "0", [])
        return snapshot


@pytest.fixture(name="helpers")
def helpers_fixture() -> Helpers:
    return Helpers()
