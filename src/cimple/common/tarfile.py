import collections.abc
import pathlib
import stat
import tarfile
import typing

import cimple.common.system


def writable_extract_filter(tarinfo: tarfile.TarInfo, dest_path: str) -> tarfile.TarInfo | None:
    # Colon is not a valid character in a path on Windows
    if cimple.common.system.platform_name().startswith("windows-") and ":" in tarinfo.name:
        return None

    if tarinfo.isdir() or tarinfo.isreg():
        tarinfo.mode |= stat.S_IWUSR

    return tarfile.tar_filter(tarinfo, str(dest_path))


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
    operation: typing.Literal["r", "w"], compression: typing.Literal["gz", "xz"]
) -> typing.Literal["w:gz", "r:gz", "w:xz", "r:xz"]:
    """
    This is more importantly working around type checking than code reuse.
    """

    return f"{operation}:{compression}"  # pyright: ignore[reportReturnType]
