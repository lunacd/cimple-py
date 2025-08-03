import importlib.resources
import pathlib
import tempfile

import pytest

from cimple import common, pkg


def mock_cygwin_release_content(*args, **kwargs):
    class MockResponse:
        def __init__(self, content: bytes):
            self.content = content
            self.status_code = 200
            self.ok = True

        @property
        def text(self):
            return self.content.decode("utf-8")

        def raise_for_status(self):
            if not self.ok:
                raise RuntimeError(f"HTTP error: {self.status_code}")

    class Mock404Response:
        def __init__(self):
            self.status_code = 404
            self.ok = False

    url: str = args[0]
    assert url.startswith(common.constants.cygwin_pkg_url), "Unexpected access to non-Cygwin URL"

    # Use data/cygwin directory to mock Cygwin repository files
    with importlib.resources.path("tests", "data/cygwin") as cygwin_data_root:
        relative_path = url[len(common.constants.cygwin_pkg_url) :].lstrip("/")
        mock_file_path = cygwin_data_root / relative_path
        if mock_file_path.exists():
            return MockResponse(mock_file_path.read_bytes())
        return Mock404Response()


def test_download_cygwin_file(mocker):
    mocker.patch("cimple.pkg.cygwin.requests.get", side_effect=mock_cygwin_release_content)

    url_path = "x86_64/setup.xz"
    with tempfile.TemporaryDirectory() as tmpdir:
        # WHEN: Downloading the Cygwin file
        downloaded_file = pkg.cygwin.download_cygwin_file(url_path, pathlib.Path(tmpdir))

        # THEN: The file should be downloaded and exist at the target path
        assert downloaded_file.exists(), f"Downloaded file does not exist at {downloaded_file}"
        assert downloaded_file.name == "setup.xz", "Downloaded file has unexpected name"


@pytest.mark.parametrize(
    "package_name,package_version,install_path",
    [
        ("bash", "4.4.12-3", "x86_64/release/bash/bash-4.4.12-3.tar.xz"),
        ("make", "4.4.1-2", "x86_64/release/make/make-4.4.1-2.tar.xz"),
    ],
)
def test_parse_cygwin_release_for_package(
    mocker, package_name: str, package_version: str, install_path: str
):
    mocker.patch("cimple.pkg.cygwin.requests.get", side_effect=mock_cygwin_release_content)

    # WHEN: Parsing the Cygwin release for the package
    returned_install_path = pkg.cygwin.parse_cygwin_release_for_package(
        package_name, package_version
    )

    # THEN: The function should return the correct package install_path
    assert returned_install_path == install_path
