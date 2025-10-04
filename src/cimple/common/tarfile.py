import collections.abc
import pathlib
import stat
import tarfile
import tempfile
import typing

import zstandard

import cimple.common.system


def writable_extract_filter(tarinfo: tarfile.TarInfo, dest_path: str) -> tarfile.TarInfo | None:
    # Colon is not a valid character in a path on Windows
    if cimple.common.system.platform_name().startswith("windows-") and ":" in tarinfo.name:
        return None

    if tarinfo.isdir() or tarinfo.isreg():
        tarinfo.mode |= stat.S_IWUSR

    return tarfile.tar_filter(tarinfo, str(dest_path))


def extract(tar_path: pathlib.Path, dest_path: pathlib.Path) -> None:
    """
    Extracts a tarball to a destination path, making files writable.
    """
    tarfile_type = tar_path.suffix[1:]
    if tarfile_type not in ("gz", "xz", "zst"):
        raise ValueError(f"Unsupported tarfile type: {tarfile_type}")

    # This tempdir is only needed for zst extraction
    # Creating it anyway for simplicity
    with tempfile.TemporaryDirectory() as temp_dir:
        if tarfile_type == "zst":
            # Extract zstd first
            zstd_ctx = zstandard.ZstdDecompressor()
            tarball_to_extract = pathlib.Path(temp_dir) / "intermediate.tar"
            with (
                tar_path.open("rb") as f,
                zstd_ctx.stream_reader(f) as reader,
                tarball_to_extract.open("wb") as out_f,
            ):
                out_f.write(reader.read())
            extraction_type = ""
            pass
        else:
            extraction_type = tarfile_type
            tarball_to_extract = tar_path

        tar_mode = get_tarfile_mode("r", extraction_type)

        with tarfile.open(tarball_to_extract, tar_mode) as tar:
            tar.extractall(dest_path, filter=writable_extract_filter)


def reproducible_add_filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
    tarinfo.mtime = 0
    return tarinfo


def extract_directory_from_tar(
    tar: tarfile.TarFile, directory: str, target_directory: pathlib.Path
) -> None:
    """
    Extracts a directory from tarfile.
    """

    def get_directory_members() -> collections.abc.Generator[tarfile.TarInfo]:
        members = tar.getmembers()
        prefix = f"{directory}/"
        for member in members:
            if member.name.startswith(prefix):
                member.name = member.name.removeprefix(prefix)
                yield member

    tar.extractall(target_directory, get_directory_members(), filter=writable_extract_filter)


def get_tarfile_mode(
    operation: typing.Literal["r", "w"], compression: typing.Literal["gz", "xz", ""]
) -> typing.Literal["w:", "r:", "w:gz", "r:gz", "w:xz", "r:xz"]:
    """
    This is more importantly working around type checking than code reuse.
    """

    return f"{operation}:{compression}"  # pyright: ignore[reportReturnType]
