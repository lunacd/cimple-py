import os
import pathlib
import subprocess

import cimple.system


def merge_env(base: dict[str, str] | os._Environ, override: dict[str, str]) -> dict[str, str]:
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
    if cimple.system.is_windows():
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

        tmpdir = os.environ["TEMP"]
        system_root = os.environ["SYSTEMROOT"]

        baseline_env = {
            # Standard system utilities like cmd.exe is available in system32
            "PATH": f"{system_root}\\System32",
            "SYSTEMROOT": system_root,
        }

        for env in windows_required_envs:
            baseline_env[env] = os.environ[env]

        baseline_env = merge_env(baseline_env, get_msvc_envs())
    else:
        tmpdir = os.environ.get("TMPDIR", "/tmp")

        baseline_env = {"PATH": ""}

    # Reproducible builds
    baseline_env["SOURCE_DATE_EPOCH"] = "0"

    # Set temporary directory
    for var in ["TMP", "TEMP", "TMPDIR"]:
        baseline_env[var] = tmpdir

    return baseline_env


_msvc_path = "C:\\Program Files (x86)\\Microsoft Visual Studio\\18\\BuildTools"


def get_msvc_envs() -> dict[str, str]:
    """
    Get MSVC environment variables from the current environment.
    """
    if not pathlib.Path(_msvc_path).exists():
        raise RuntimeError("MSVC installation not found")

    # Run the Visual Studio Developer PowerShell to get the environment variables
    mscv_dev_shell_command = [
        "C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
        "-Command",
        f"&{{Import-Module '{_msvc_path}\\Common7\\Tools\\Microsoft.VisualStudio."
        f"DevShell.dll'; Enter-VsDevShell -VsInstallPath '{_msvc_path}'"
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

    return raw_envs
