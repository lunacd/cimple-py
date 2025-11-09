import os
import pathlib
import subprocess

import cimple.system


def merge_env(base: dict[str, str], override: dict[str, str]) -> dict[str, str]:
    """
    Merge two environment variable dictionaries, with `override` taking precedence.
    """
    merged = base.copy()
    merged.update(override)
    return merged


def baseline_env() -> dict[str, str]:
    # TODO: support linux and macos
    # TODO: move this to image.json
    tmpdir = os.environ.get("TMP", "/tmp")
    baseline_env = {"TMP": tmpdir, "TEMP": tmpdir, "TMPDIR": tmpdir, "SOURCE_DATE_EPOCH": "0"}
    if cimple.system.is_windows():
        baseline_env.update(get_msvc_envs())

    return baseline_env


def find_msvc() -> pathlib.Path | None:
    """
    Find the MSVC installation path.
    """
    possible_paths = [
        "C:\\Program Files\\Microsoft Visual Studio\\2022\\Enterprise",
        "C:\\Program Files\\Microsoft Visual Studio\\2022\\Professional",
        "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community",
    ]

    for path_str in possible_paths:
        path = pathlib.Path(path_str)
        if path.is_dir():
            return path

    return None


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

    return envs
