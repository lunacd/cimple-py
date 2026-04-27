import functools
import platform


@functools.cache
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
    if python_machine == "x86_64" or python_machine == "AMD64":
        arch = "x86_64"
    else:
        raise RuntimeError(f"Unsupported architecture: {python_machine}")

    return f"{os_name}-{arch}"


def is_windows() -> bool:
    """
    Returns True if the current platform is Windows.
    """
    return platform_name().startswith("windows")
