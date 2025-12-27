import os
import pathlib
import subprocess

import cimple.system


def merge_env(base: dict[str, str], override: dict[str, str]) -> dict[str, str]:
    """
    Merge two environment variable dictionaries, with `override` taking precedence.
    """
    merged = base.copy()

    for key, value in override.items():
        if key == "PATH" and key in merged:
            merged["PATH"] = os.pathsep.join([value, base["PATH"]])
        else:
            merged[key] = value

    return merged


def baseline_env() -> dict[str, str]:
    # TODO: support linux and macos
    # TODO: move this to image.json
    windows_required_envs = [
        "HOMEDRIVE",
        "HOMEPATH",
        "LOGONSERVER",
        "SYSTEMDRIVE",
        "USERDOMAIN",
        "USERNAME",
        "USERPROFILE",
        "WINDIR",
    ]

    tmpdir = os.environ["TEMP"] if cimple.system.is_windows() else os.environ.get("TMPDIR", "/tmp")

    system_root = os.environ["SYSTEMROOT"]
    baseline_env = {
        "TMP": tmpdir,
        "TEMP": tmpdir,
        "TMPDIR": tmpdir,
        # Reproducible builds
        "SOURCE_DATE_EPOCH": "0",
        # Standard system utilities like cmd.exe is available in system32
        "PATH": f"{system_root}\\System32",
        "SYSTEMROOT": system_root,
    }

    for env in windows_required_envs:
        baseline_env[env] = os.environ[env]

    if cimple.system.is_windows():
        baseline_env = merge_env(baseline_env, get_msvc_envs())

    return baseline_env


_msvc_base_path = "C:\\Program Files\\Microsoft Visual Studio\\18"
_msvc_editions = ["Enterprise", "Professional", "Community"]


def find_msvc() -> pathlib.Path | None:
    """
    Find the MSVC installation path.
    """
    for edition in _msvc_editions:
        path = pathlib.Path(f"{_msvc_base_path}\\{edition}")
        if path.is_dir():
            return path

    return None


def filter_msvc_path(full_path: str) -> str:
    """
    Filter MSVC paths from the given PATH string.
    """
    path_parts = full_path.split(os.pathsep)
    filtered_parts = [part for part in path_parts if part.startswith(_msvc_base_path)]
    return os.pathsep.join(filtered_parts)


def get_msvc_envs() -> dict[str, str]:
    """
    Get MSVC environment variables from the current environment.
    """
    msvc_path = find_msvc()
    if msvc_path is None:
        raise RuntimeError("MSVC installation not found")

    # Run the Visual Studio Developer PowerShell to get the environment variables
    mscv_dev_shell_command = [
        "C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
        "-Command",
        f"&{{Import-Module '{msvc_path}\\Common7\\Tools\\Microsoft.VisualStudio."
        f"DevShell.dll'; Enter-VsDevShell -VsInstallPath '{msvc_path}'"
        "-SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64'; "
        'Get-ChildItem Env: | ForEach-Object { "$($_.Name)=$($_.Value)" } }',
    ]
    process = subprocess.run(
        mscv_dev_shell_command,
        check=True,
        text=True,
        capture_output=True,
    )

    # Parse the output into a dictionary
    raw_envs: dict[str, str] = {}
    for line in process.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        raw_envs[key] = value

    # Copy over the relevant environment variables
    envs: dict[str, str] = {}

    assert "INCLUDE" in raw_envs, "INCLUDE not found in MSVC environment"
    envs["INCLUDE"] = raw_envs["INCLUDE"]

    assert "EXTERNAL_INCLUDE" in raw_envs, "EXTERNAL_INCLUDE not found in MSVC environment"
    envs["EXTERNAL_INCLUDE"] = raw_envs["EXTERNAL_INCLUDE"]

    assert "LIB" in raw_envs, "LIB not found in MSVC environment"
    envs["LIB"] = raw_envs["LIB"]

    assert "LIBPATH" in raw_envs, "LIBPATH not found in MSVC environment"
    envs["LIBPATH"] = raw_envs["LIBPATH"]

    if "PATH" not in raw_envs and "Path" not in raw_envs:
        raise RuntimeError("PATH or Path not found in MSVC environment")
    envs["PATH"] = filter_msvc_path(raw_envs.get("PATH", raw_envs.get("Path", "")))

    return envs
