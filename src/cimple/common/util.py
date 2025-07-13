import pathlib
import shutil


def ensure_path(path: pathlib.Path):
    """
    Ensure the given directory exists.
    """
    if not path.exists():
        path.mkdir(parents=True)
    elif not path.is_dir():
        raise RuntimeError(f"Unexpected: {path} is not a directory")


def clear_path(path: pathlib.Path):
    """
    Clears the given path.
    """

    if path.exists():
        shutil.rmtree(path)

    path.mkdir()
