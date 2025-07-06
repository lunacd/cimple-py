import os
import pathlib
import subprocess
import shutil
import typing


def construct_path_env_var(
    image_path: typing.Optional[pathlib.Path],
    dependency_path: typing.Optional[pathlib.Path],
):
    """
    Build a PATH environment variable from the given image path and/or dependency path.
    """

    path_arr: list[str] = []
    if dependency_path is not None:
        # No /usr is allowed in the package index
        path_arr.append(str(dependency_path / "bin"))
    if image_path is not None:
        path_arr.append(str(image_path / "bin"))
        path_arr.append(str(image_path / "usr" / "bin"))

    return os.pathsep.join(path_arr)


def run_command(
    args: list[str],
    image_path: typing.Optional[pathlib.Path],
    dependency_path: typing.Optional[pathlib.Path],
    cwd: pathlib.Path,
) -> subprocess.CompletedProcess[str]:
    """
    Run a command within the constructed image and dependency tree.
    """

    path = construct_path_env_var(image_path, dependency_path)

    cmd = shutil.which(args[0], path=path)
    if cmd is None:
        raise RuntimeError(f"{args[0]} is not found in {path}")

    args[0] = cmd

    return subprocess.run(args, text=True, env={"PATH": path}, cwd=cwd)
