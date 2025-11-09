import os
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
    tmpdir = os.environ["TMP"]
    baseline_env = {"TMP": tmpdir, "TEMP": tmpdir, "TMPDIR": tmpdir, "SOURCE_DATE_EPOCH": "0"}
    if cimple.system.is_windows():
        baseline_env.update(get_msvc_envs())

    return baseline_env


def get_msvc_envs() -> dict[str, str]:
    """
    Get MSVC environment variables from the current environment.
    """
    msvc_path = "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community"

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
    envs["DevEnvDir"] = raw_envs["DevEnvDir"]
    envs["INCLUDE"] = raw_envs["INCLUDE"]
    envs["EXTERNAL_INCLUDE"] = raw_envs["EXTERNAL_INCLUDE"]
    envs["LIB"] = raw_envs["LIB"]
    envs["LIBPATH"] = raw_envs["LIBPATH"]

    return envs
