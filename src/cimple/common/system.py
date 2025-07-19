import pathlib


def to_cygwin_path(path: pathlib.Path) -> pathlib.Path:
    """
    Convert a Windows path to a Cygwin-compatible path.
    """
    first_segment = path.parts[0]
    if first_segment[1:2] == ":":
        cygwin_path_prefix = f"/cygdrive/{first_segment[0].lower()}"
        return pathlib.Path(cygwin_path_prefix, *path.parts[1:])

    return path
