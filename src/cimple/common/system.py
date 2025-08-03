import pathlib
import platform


def platform_name() -> str:
    """
    Returns the name of the current platform.
    """
    python_system = platform.system()
    if python_system.startswith("Windows"):
        os_name = "windows"
    elif python_system.startswith("Linux"):
        os_name = "linux"
    elif python_system.startswith("Darwin"):
        os_name = "macos"
    else:
        raise RuntimeError(f"Unsupported platform: {platform.system()}")

    python_machine = platform.machine()
    if python_machine == "x86_64":
        arch = "x86_64"
    else:
        raise RuntimeError(f"Unsupported architecture: {python_machine}")

    return f"{os_name}-{arch}"


def is_windows() -> bool:
    """
    Check if the current operating system is Windows.
    """
    return platform.system().startswith("Windows")


def to_cygwin_path(path: pathlib.Path) -> pathlib.Path:
    """
    Convert a Windows path to a Cygwin-compatible path.
    """
    if not is_windows():
        return path

    first_segment = path.parts[0]
    if first_segment[1:2] == ":":
        cygwin_path_prefix = f"/cygdrive/{first_segment[0].lower()}"
        return pathlib.Path(cygwin_path_prefix, *path.parts[1:])

    return path
