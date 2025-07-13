__all__ = ["pkg_config"]

import pathlib
import shutil
import tarfile
import tomllib

import patch_ng
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
    if not (common.constants.cimple_pkg_output_dir.exists()):
        common.constants.cimple_pkg_output_dir.mkdir(parents=True)

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

    # Prepare build and output directories
    build_dir = common.constants.cimple_pkg_build_dir / pkg_full_name
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir()
    output_dir = common.constants.cimple_pkg_output_dir / pkg_full_name
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()

    # Extract source tarball
    # TODO: make this unique per build somehow
    common.logging.info("Extracting original source")
    with tarfile.open(orig_file, f"r:{config.input.tarball_compression}") as tar:
        common.tarfile.extract_directory_from_tar(tar, config.input.tarball_root_dir, build_dir)

    # TODO: support patching
    common.logging.info("Patching source")

    patch_dir = pkg_path / "patches"
    for patch_name in config.input.patches:
        common.logging.info("Applying %s", patch_name)
        patch_path = patch_dir / patch_name
        if not patch_path.exists():
            raise RuntimeError(f"Patch {patch_name} is not found in {patch_dir}.")

        patch = patch_ng.fromfile(patch_path)
        # NOTE: It'll be nice to check whether the patch applies correctly in this step and
        # give error message about what patch fails with what file. I haven't figured out
        # how to do this with patch-ng.
        patch_success = patch.apply(root=build_dir)
        if not patch_success:
            raise RuntimeError(f"Failed to apply {patch_name}.")

    common.logging.info("Starting build")

    # TODO: support overriding rules per-platform
    cimple_builtin_variables = {"cimple_output_dir": str(output_dir)}

    def interpolate_variables(input_str):
        return common.str_interpolation.interpolate(input_str, cimple_builtin_variables)

    for rule in config.rules.default:
        if isinstance(rule, str):
            cmd: list[str] = rule.split(" ")
            cwd = build_dir
            env = {}
        else:
            cmd = rule.rule if isinstance(rule.rule, list) else rule.rule.split(" ")
            cwd = pathlib.Path(interpolate_variables(rule.cwd)) if rule.cwd else build_dir
            env = rule.env if rule.env else {}

        interpolated_cmd = []
        interpolated_env = {}

        for cmd_item in cmd:
            interpolated_cmd.append(interpolate_variables(cmd_item))
        for env_key, env_val in env.items():
            interpolated_env[interpolate_variables(env_key)] = interpolate_variables(env_val)

        common.cmd.run_command(
            interpolated_cmd,
            image_path=image_path,
            dependency_path=None,
            cwd=cwd,
            env=interpolated_env,
        )
