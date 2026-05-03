import dataclasses
import os
import subprocess
import typing

import cimple.env
import cimple.logging
import cimple.system

if typing.TYPE_CHECKING:
    import pathlib


@dataclasses.dataclass
class OciMount:
    source: pathlib.Path
    target: pathlib.Path
    read_only: bool = False


def start_container(image: str, mounts: list[OciMount]) -> str:
    """
    Start a container with the given image.
    Returns the container ID.
    """
    mount_flags: list[str] = []
    for mount in mounts:
        mount_flags.append("--mount")
        mount_flags.append(
            f"type=bind,src={mount.source},dst={mount.target}"
            f"{',readonly' if mount.read_only else ''}"
        )

    env_flags: list[str] = []
    if os.environ.get("CIMPLE_DEBUG") == "true":
        env_flags.append("--env")
        env_flags.append("CIMPLE_DEBUG=true")

    if cimple.system.is_windows():
        # A build can take a maximum of 2 hours
        docker_process = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                *mount_flags,
                *env_flags,
                image,
                "powershell",
                "-Command",
                "Start-Sleep -Seconds 7200",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        return docker_process.stdout.strip()

    raise NotImplementedError()


def run_command_in_container(
    container_id: str,
    args: list[str],
) -> subprocess.CompletedProcess[str]:
    """
    Run a command within a container.
    """

    cimple.logging.debug("Executing %s", args)
    return subprocess.run(["docker", "exec", container_id] + args, text=True)


def stop_container(container_id: str):
    """
    Stop a container
    """

    cimple.logging.debug("Trying to stop %s", container_id)
    subprocess.run(["docker", "stop", container_id], check=True)
    subprocess.run(["docker", "rm", container_id], check=True)
