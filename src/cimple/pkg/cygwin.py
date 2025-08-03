import lzma
import pathlib
import tempfile

import requests

from cimple import common


def _parse_checksum_file(file_content: str) -> dict[str, str]:
    """
    Parses the checksum file content and returns a dictionary mapping file names to their checksums.
    """
    checksums = {}
    for line in file_content.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        checksum, pkg_name = parts[0], parts[1]
        checksums[pkg_name] = checksum
    return checksums


def download_cygwin_file(url_path: str, target_path: pathlib.Path) -> pathlib.Path:
    """
    Downloads a file from the Cygwin repository and saves it to the target path.
    """
    file_name = url_path.split("/")[-1]
    file_dir = "/".join(url_path.rsplit("/")[:-1])
    output_path = target_path / file_name
    checksum_file_url = f"{common.constants.cygwin_pkg_url}/{file_dir}/sha512.sum"
    file_url = f"{common.constants.cygwin_pkg_url}/{url_path}"

    # Download checksum file
    checksum_res = requests.get(checksum_file_url)
    if not checksum_res.ok:
        raise RuntimeError(f"Checksum file does not exist at {checksum_file_url}")
    checksums = _parse_checksum_file(checksum_res.text)
    file_checksum = checksums.get(file_name)

    # Download the file
    response = requests.get(file_url)
    response.raise_for_status()
    with output_path.open("wb") as f:
        f.write(response.content)

    # Verify checksum
    actual_hash = common.hash.hash_file(output_path, "sha512")
    if actual_hash != file_checksum:
        raise RuntimeError(
            f"Checksum mismatch for {file_name}: expected {file_checksum}, got {actual_hash}"
        )

    return output_path


def parse_cygwin_release_for_package(package_name: str, package_version: str) -> str:
    """
    Parse the Cygwin release file to get package information.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file_path = download_cygwin_file("x86_64/setup.xz", pathlib.Path(tmpdir))
        with lzma.open(output_file_path, "rt") as f:
            release_content = f.read()

    # Parse the release content to find the package section
    package_section: list[str] = []
    in_section = False
    for line in release_content.splitlines():
        # Package section starts with "@ package_name"
        if line.startswith(f"@ {package_name}"):
            in_section = True
            continue

        # Sections are separated by empty lines
        if in_section:
            if len(line) == 0:
                break

            package_section.append(line)

    found_version = False
    install_path = None
    for line in package_section:
        # TODO: This assumes version field always precedes install field
        if line.startswith(f"version: {package_version}"):
            found_version = True
            continue

        if found_version and line.startswith("install:"):
            install_path = line.split()[1]
            break

    if not found_version:
        raise RuntimeError(f"Package {package_name} version {package_version} not found.")

    if install_path is None:
        raise RuntimeError(
            f"Install path for package {package_name} version {package_version} not found."
        )

    return install_path
