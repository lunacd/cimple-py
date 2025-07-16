import pathlib
import shutil
import stat


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


def fix_permissions(path: pathlib.Path):
    for item in path.rglob("*"):
        if item.is_file() or item.is_dir():
            # Get current permissions
            mode = item.stat().st_mode

            # Add user/group/other execute bits
            writable_mode = mode | stat.S_IWUSR
            item.chmod(writable_mode)
