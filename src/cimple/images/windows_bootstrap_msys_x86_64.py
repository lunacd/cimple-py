"""
Create MSYS bootstrap image.
"""

import pathlib
import subprocess
import os
import functools
import tempfile
import tarfile
import zstandard

import cimple.common as common

# TODO: extract this to a config file
msys2_packages = [
    "bash",
    "gcc",
    "make",
    "coreutils",
    "sed",
    "grep",
    # Dependencies
    "msys2-runtime",
    "gmp",
    "libintl",
    "libiconv",
    "gcc-libs",
    "binutils",
    "gmp",
    "isl",
    "mpc",
    "mpfr",
    "zlib",
    "libpcre",
    "msys2-runtime-devel",
    "msys2-w32api-headers",
    "msys2-w32api-runtime",
    "windows-default-manifest",
]


def pkg_info_from_filename(filename: str) -> tuple[str, str]:
    """
    Extract the package name from the filename.
    """
    # libidn2-2.3.8-1-x86_64.pkg.tar.zst
    filename = filename.removesuffix(".pkg.tar.zst")
    # -1: arch
    # -2: revision
    # -3: version
    # everything else: name
    segments = filename.split("-")
    if len(segments) < 4:
        raise ValueError(f"Invalid package filename: {filename}")
    name = "-".join(segments[:-3])
    version = "-".join(segments[-3:-1])
    return name, version


def make_image(msys_path: pathlib.Path, target_path: pathlib.Path):
    common.logging.info("Making windows bootstrap_msys image")

    pacman_path = msys_path / "usr" / "bin" / "pacman.exe"
    subprocess.run([pacman_path, "-Syuw", "--noconfirm"] + msys2_packages, check=True)

    cache_path = msys_path / "var" / "cache" / "pacman" / "pkg"
    cache_files = os.listdir(cache_path)

    available_packages: dict[str, list[tuple[str, str]]] = {}

    for filename in cache_files:
        if not filename.endswith(".pkg.tar.zst"):
            continue

        name, version = pkg_info_from_filename(filename)
        available_packages.setdefault(name, []).append((version, filename))

    zstd_ctx = zstandard.ZstdDecompressor()

    def extract_msys_package(package: str, extraction_target: str):
        common.logging.info("Installing %s", package)

        # Get latest version of each package
        if package not in available_packages:
            raise ValueError(f"Package {install_package} not found in cache.")

        versions = available_packages[install_package]
        versions.sort(
            key=functools.cmp_to_key(
                lambda a, b: common.version.version_compare(a[0], b[0])
            )
        )

        def extraction_filter(member: tarfile.TarInfo, path: str):
            """
            Filters out .BUILDINFO, .MTREE, and .PKGINFO in archives
            Then passes to data_filter
            """
            if member.name in [".PKGINFO", ".MTREE", ".BUILDINFO"]:
                return None
            return tarfile.data_filter(member, path)

        # Untar latest version of the package
        with (cache_path / versions[-1][1]).open("rb") as f:
            with zstd_ctx.stream_reader(f) as reader:
                # Open the tar archive from the decompressed stream
                with tarfile.open(fileobj=reader, mode="r:") as tar:
                    # Extract all members to the specified directory
                    tar.extractall(path=extraction_target, filter=extraction_filter)

    with tempfile.TemporaryDirectory() as tempdir:
        for install_package in msys2_packages:
            extract_msys_package(install_package, tempdir)

        # Make ./tmp
        # This is needed for programs like bash
        os.mkdir(os.path.join(tempdir, "tmp"))

        # TODO: hash this somehow
        common.logging.info("Tarring things up")
        output_file = target_path / "windows-bootstrap_msys-x86_64.tar.gz"
        with tarfile.open(output_file, "w:gz") as out_tar:
            out_tar.add(tempdir, ".")
