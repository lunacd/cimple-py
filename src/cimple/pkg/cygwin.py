import lzma
import pathlib
import tempfile

import pydantic
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


class CygwinRelease:
    """
    Represents a Cygwin release, providing methods to download and parse package information.
    """

    class CygwinPackage(pydantic.BaseModel):
        """
        Represents a Cygwin package with its name, version, and install path.
        """

        name: str
        version: str
        install_path: str
        depends: list[str]

    def __init__(self):
        self.packages: dict[str, CygwinRelease.CygwinPackage] = {}
        self.initialized = False

    def parse_release_file(self, release_content: str) -> None:
        current_package: str | None = None
        current_version: str | None = None
        install_path: str | None = None
        dependencies: list[str] | None = None

        in_field = False
        field_key = None
        field_value = None
        is_test_section = False

        def reset_package_fields():
            nonlocal current_version, install_path, dependencies
            current_version = None
            install_path = None
            dependencies = None

        def record_package(current_package, current_version, install_path, dependencies):
            # Only record if all required fields are present
            if not current_package or not current_version or not install_path:
                return
            # Skip test versions
            if is_test_section:
                return
            key = f"{current_package}-{current_version}"
            self.packages[key] = self.CygwinPackage(
                name=current_package,
                version=current_version,
                install_path=install_path,
                depends=dependencies if dependencies is not None else [],
            )

        for line in release_content.splitlines():
            # Quoted field values
            if in_field:
                assert field_value is not None, (
                    "Field value should not be None when in_field is True"
                )
                if line.strip().endswith('"'):
                    field_value += "\n" + line.strip()[:-1]
                    # TODO: We currently discard quoted field values immediately
                    in_field = False
                    field_key = None
                    field_value = None
                else:
                    field_value += "\n" + line.strip()
                continue

            # Start of package section
            if line.startswith("@ "):
                current_package = line[2:].strip()
                continue

            # key : value
            if ":" in line:
                field_key, field_value = line.split(":", 1)
                field_key = field_key.strip()
                field_value = field_value.strip()

                # Value quoted on the same line
                if (
                    field_value.startswith('"')
                    and field_value.endswith('"')
                    and len(field_value) > 2
                ):
                    field_value = field_value[1:-1].strip()
                # Value that starts a quote but do not end it
                elif field_value.startswith('"'):
                    in_field = True
                    field_value = field_value[1:].strip()
                    continue

                # Parse fields of interest
                if field_key == "version":
                    if current_package is None:
                        raise RuntimeError(f"Version line '{line}' found without a package section")
                    current_version = field_value
                elif field_key == "install":
                    if current_package is None or current_version is None:
                        raise RuntimeError(
                            "Install line found without a package section or version"
                        )
                    install_path = field_value.split()[0]
                elif field_key == "depends2":
                    if current_package is None or current_version is None:
                        raise RuntimeError(
                            "Depends line found without a package section or version"
                        )
                    dependencies = [dep.strip() for dep in field_value.split(",")]

                continue

            # End of package section
            if len(line.strip()) == 0:
                record_package(current_package, current_version, install_path, dependencies)
                current_package = None
                reset_package_fields()
                is_test_section = False
                continue

            # End of a version section
            if line.strip() == "[prev]":
                record_package(current_package, current_version, install_path, dependencies)
                reset_package_fields()
                is_test_section = False
                continue

            if line.strip() == "[test]":
                record_package(current_package, current_version, install_path, dependencies)
                reset_package_fields()
                is_test_section = True
                continue

        # Record last package if file does not end with newline
        record_package(current_package, current_version, install_path, dependencies)
        self.initialized = True

    def parse_release_from_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file_path = download_cygwin_file("x86_64/setup.xz", pathlib.Path(tmpdir))
            with lzma.open(output_file_path, "rt", encoding="utf-8") as f:
                release_content = f.read()

        self.parse_release_file(release_content)
        self.initialized = True
