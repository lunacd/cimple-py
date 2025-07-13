__all__ = ["pkg_config"]

import pathlib
import tarfile

import patch_ng
import pydantic
import requests

import cimple.common as common
import cimple.pkg.pkg_config as pkg_config


class PkgId(pydantic.BaseModel):
    name: str
    version: str


def build_pkg(pkg_path: pathlib.Path) -> pathlib.Path:
    config = pkg_config.load_pkg_config(pkg_path)

    # Prepare chroot image
    common.logging.info("Preparing image")
    # TODO: support multiple platforms and arch
    image_path = common.image.prepare_image("windows", "x86_64", config.input.image_type)

    # TODO: parepare dependency tree

    # Ensure needed directories exist
    common.util.ensure_path(common.constants.cimple_orig_dir)
    common.util.ensure_path(common.constants.cimple_pkg_build_dir)
    common.util.ensure_path(common.constants.cimple_pkg_output_dir)

    # Get source tarball
    common.logging.info("Fetching original source")
    pkg_full_name = f"{config.pkg.name}-{config.pkg.version}"
    pkg_tarball_name = (
        f"{config.pkg.name}-{config.input.source_version}.tar.{config.input.tarball_compression}"
    )
    orig_file = common.constants.cimple_orig_dir / pkg_tarball_name
    if not orig_file.exists():
        source_url = f"https://cimple-pi.lunacd.com/orig/{pkg_tarball_name}"
        res = requests.get(source_url)
        res.raise_for_status()
        with orig_file.open("wb") as f:
            f.write(res.content)

    # Verify source tarball
    common.logging.info("Verifying original source")
    orig_hash = common.hash.sha256_file(orig_file)
    if orig_hash != config.input.sha256:
        raise RuntimeError(
            "Corrupted original source tarball, expecting SHA256 %s but got %s.",
            config.input.sha256,
            orig_hash,
        )

    # Prepare build and output directories
    build_dir = common.constants.cimple_pkg_build_dir / pkg_full_name
    output_dir = common.constants.cimple_pkg_output_dir / pkg_full_name
    common.util.clear_path(build_dir)
    common.util.clear_path(output_dir)

    # Extract source tarball
    # TODO: make this unique per build somehow
    common.logging.info("Extracting original source")
    with tarfile.open(orig_file, f"r:{config.input.tarball_compression}") as tar:
        common.tarfile.extract_directory_from_tar(tar, config.input.tarball_root_dir, build_dir)

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

    common.logging.info("Build result is available in %s", output_dir)
    return output_dir
