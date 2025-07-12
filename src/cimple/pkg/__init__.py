__all__ = ["pkg_config"]

import pathlib
import shutil
import tarfile
import tomllib

import requests

import cimple.common as common
import cimple.pkg.pkg_config as pkg_config


def build_pkg(pkg_path: pathlib.Path):
    config_path = pkg_path / "pkg.toml"
    with config_path.open("rb") as f:
        config_dict = tomllib.load(f)
        config = pkg_config.PkgConfig.model_validate(config_dict)

    # Prepare chroot image
    common.logging.info("Preparing image")
    # TODO: support multiple platforms and arch
    image_path = common.image.prepare_image("windows", "x86_64", config.input.image_type)

    # TODO: parepare dependency tree

    # Ensure needed directories exist
    if not common.constants.cimple_orig_dir.exists():
        common.constants.cimple_orig_dir.mkdir(parents=True)
    if not (common.constants.cimple_pkg_build_dir.exists()):
        common.constants.cimple_pkg_build_dir.mkdir(parents=True)

    # Get source tarball
    common.logging.info("Fetching original source")
    pkg_full_name = f"{config.pkg.name}-{config.pkg.version}"
    pkg_tarball_name = f"{pkg_full_name}.tar.{config.input.tarball_compression}"
    source_url = f"https://cimple-pi.lunacd.com/orig/{pkg_tarball_name}"
    res = requests.get(source_url)
    res.raise_for_status()
    orig_file = common.constants.cimple_orig_dir / pkg_tarball_name
    with orig_file.open("wb") as f:
        f.write(res.content)

    # Extract source tarball
    # TODO: make this unique per build somehow
    common.logging.info("Extracting original source")
    build_dir = common.constants.cimple_pkg_build_dir / pkg_full_name
    if build_dir.exists():
        shutil.rmtree(build_dir)
    with tarfile.open(orig_file, f"r:{config.input.tarball_compression}") as tar:
        common.tarfile.extract_directory_from_tar(tar, config.input.tarball_root_dir, build_dir)

    # TODO: support patching

    common.logging.info("Starting build")

    # TODO: support overriding rules per-platform
    for rule in config.rules.default:
        if isinstance(rule, str):
            cmd: list[str] = rule.split(" ")
            cwd = build_dir
            env = {}
        else:
            cmd = rule.rule if isinstance(rule.rule, list) else rule.rule.split(" ")
            cwd = rule.cwd if rule.cwd else build_dir
            env = rule.env if rule.env else {}

        common.cmd.run_command(cmd, image_path=image_path, dependency_path=None, cwd=cwd, env=env)
