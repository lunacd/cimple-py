import os
import shutil
import subprocess
import typing

import cimple.env
import cimple.logging
import cimple.system

if typing.TYPE_CHECKING:
    import pathlib


def construct_path_env_var(
    dependency_path: pathlib.Path | None,
    extra_paths: list[pathlib.Path],
):
    """
    Build a PATH environment variable from the given image path and/or dependency path.
    """

    path_arr: list[str] = [p.as_posix() for p in extra_paths]
    if dependency_path is not None:
        path_arr.append(str(dependency_path / "bin"))

    return os.pathsep.join(path_arr)


def start_container(image: str) -> str:
    """
    Start a container with the given image.
    Returns the container ID.
    """
    if cimple.system.is_windows():
        # A build can take a maximum of 2 hours
        docker_process = subprocess.run(
            ["docker", "run", "-d", image, "powershell", "-Command", "Start-Sleep -Seconds 7200"],
            check=True,
            text=True,
            capture_output=True,
        )
        return docker_process.stdout.strip()

    raise NotImplementedError()


def run_command(
    container_id: str,
    args: list[str],
    dependency_path: pathlib.Path | None,
    cwd: pathlib.Path,
    env: dict[str, str] | None,
    extra_paths: list[pathlib.Path] | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Run a command within the constructed image and dependency tree.
    """

    if extra_paths is None:
        extra_paths = []

    path = construct_path_env_var(dependency_path, extra_paths)

    cmd = shutil.which(args[0], path=path)
    if cmd is None:
        raise RuntimeError(f"{args[0]} is not found in {path}")

    args[0] = cmd

    if env is None:
        env = {}
    env = cimple.env.merge_env(env, cimple.env.baseline_env())
    env = cimple.env.merge_env(env, {"PATH": path})

    cimple.logging.debug("Executing %s in %s, env %s", " ".join(args), cwd, env)
    return subprocess.run(args, text=True, env=env, cwd=cwd)
