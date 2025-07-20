import os
import pathlib
import shutil
import subprocess

import cimple.common as common


def baseline_env() -> dict[str, str]:
    # TODO: support linux and macos
    # TODO: move this to image.json
    tmpdir = os.environ["TMP"]
    return {"TMP": tmpdir, "TEMP": tmpdir, "TMPDIR": tmpdir, "SOURCE_DATE_EPOCH": "0"}


def construct_path_env_var(
    image_path: pathlib.Path | None,
    dependency_path: pathlib.Path | None,
):
    """
    Build a PATH environment variable from the given image path and/or dependency path.
    """

    path_arr: list[str] = []
    if dependency_path is not None:
        # No /usr is allowed in the package index
        path_arr.append(str(dependency_path / "bin"))
    if image_path is not None:
        path_arr.append(str(image_path / "usr" / "bin"))

    return os.pathsep.join(path_arr)


def run_command(
    args: list[str],
    image_path: pathlib.Path | None,
    dependency_path: pathlib.Path | None,
    cwd: pathlib.Path,
    env: dict[str, str] | None,
) -> subprocess.CompletedProcess[str]:
    """
    Run a command within the constructed image and dependency tree.
    """

    path = construct_path_env_var(image_path, dependency_path)

    cmd = shutil.which(args[0], path=path)
    if cmd is None:
        raise RuntimeError(f"{args[0]} is not found in {path}")

    args[0] = cmd

    if env is None:
        env = {}
    env.update(baseline_env())
    # TODO: if PATH is specified in env, merge with it.
    env.update({"PATH": path})

    common.logging.debug("Executing %s in %s, env %s", " ".join(args), cwd, env)
    return subprocess.run(args, text=True, env=env, cwd=cwd)
