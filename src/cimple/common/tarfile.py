import collections.abc
import pathlib
import tarfile
import typing


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

    tar.extractall(target_directory, get_directory_members())


def reproducible_filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
    tarinfo.mtime = 0
    return tarinfo


def get_tarfile_mode(
    operation: typing.Literal["r", "w"], compression: typing.Literal["gz", "xz"]
) -> typing.Literal["w:gz", "r:gz", "w:xz", "r:xz"]:
    """
    This is more importantly working around type checking than code reuse.
    """

    return f"{operation}:{compression}"  # type: ignore
