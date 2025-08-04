import pathlib
import tempfile

import pytest

from cimple import pkg


def test_download_cygwin_file(cygwin_release_content_side_effect, mocker):
    mocker.patch("cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect)

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
    cygwin_release_content_side_effect,
    mocker,
    package_name: str,
    package_version: str,
    install_path: str,
):
    mocker.patch("cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect)

    # WHEN: Parsing the Cygwin release for the package
    returned_install_path = pkg.cygwin.parse_cygwin_release_for_package(
        package_name, package_version
    )

    # THEN: The function should return the correct package install_path
    assert returned_install_path == install_path
