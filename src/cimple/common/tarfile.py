import collections.abc
import tarfile
import pathlib


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
