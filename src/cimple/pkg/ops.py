import pathlib
import tarfile

import patch_ng
import requests

from cimple import common, images, models, snapshot
from cimple.pkg import pkg_config


def install_package_and_deps(
    target_path: pathlib.Path,
    pkg_id: models.pkg.BinPkgId,
    cimple_snapshot: snapshot.core.CimpleSnapshot,
):
    """
    Install a package and its transitive dependencies into the target path.
    """
    # Ensure the target path exists
    common.util.ensure_path(target_path)

    # Install the package itself
    install_pkg(target_path, pkg_id, cimple_snapshot)

    # Install transitive dependencies
    transitive_bin_deps = cimple_snapshot.runtime_depends_of(pkg_id)

    for dep in transitive_bin_deps:
        install_pkg(target_path, dep, cimple_snapshot)


def install_pkg(
    target_path: pathlib.Path,
    pkg_id: models.pkg.BinPkgId,
    cimple_snapshot: snapshot.core.CimpleSnapshot,
):
    common.logging.info("Installing %s", pkg_id)

    pkg_data = cimple_snapshot.get_snapshot_pkg(pkg_id)
    if pkg_data is None:
        raise RuntimeError(
            f"Requested package {pkg_id} not found in snapshot {cimple_snapshot.name}."
        )
    assert models.snapshot.snapshot_pkg_is_bin(pkg_data.root)

    if pkg_data is None:
        raise RuntimeError(
            f"Requested package {pkg_id} not found in snapshot {cimple_snapshot.name}."
        )

    with tarfile.open(
        common.constants.cimple_pkg_dir / pkg_data.root.tarball_name,
        common.tarfile.get_tarfile_mode("r", pkg_data.root.compression_method),
    ) as tar:
        tar.extractall(target_path, filter=common.tarfile.writable_extract_filter)


def build_pkg(
    pkg_path: pathlib.Path, *, cimple_snapshot: snapshot.core.CimpleSnapshot, parallel: int
) -> pathlib.Path:
    config = pkg_config.load_pkg_config(pkg_path)

    # Prepare chroot image
    common.logging.info("Preparing image")
    # TODO: support multiple platforms and arch
    image_path = images.prepare_image("windows", "x86_64", config.input.image_type)

    # Ensure needed directories exist
    common.util.ensure_path(common.constants.cimple_orig_dir)
    common.util.ensure_path(common.constants.cimple_pkg_build_dir)
    common.util.ensure_path(common.constants.cimple_pkg_output_dir)
    common.util.ensure_path(common.constants.cimple_deps_dir)

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
            "Corrupted original source tarball, "
            f"expecting SHA256 {config.input.sha256} but got {orig_hash}."
        )

    # Install dependencies
    common.logging.info("Installing dependencies")
    deps_dir = common.constants.cimple_deps_dir / pkg_full_name
    common.util.clear_path(deps_dir)
    for dep in config.pkg.build_depends:
        install_package_and_deps(deps_dir, dep, snapshot_map)

    # Prepare build and output directories
    build_dir = common.constants.cimple_pkg_build_dir / pkg_full_name
    output_dir = common.constants.cimple_pkg_output_dir / pkg_full_name
    common.util.clear_path(build_dir)
    common.util.clear_path(output_dir)

    # Extract source tarball
    # TODO: make this unique per build somehow
    common.logging.info("Extracting original source")
    with tarfile.open(
        orig_file, common.tarfile.get_tarfile_mode("r", config.input.tarball_compression)
    ) as tar:
        if config.input.tarball_root_dir is None:
            tar.extractall(build_dir, filter=common.tarfile.writable_extract_filter)
        else:
            common.tarfile.extract_directory_from_tar(tar, config.input.tarball_root_dir, build_dir)

    common.logging.info("Patching source")
    patch_dir = pkg_path / "patches"
    for patch_name in config.input.patches:
        common.logging.info("Applying %s", patch_name)
        patch_path = patch_dir / patch_name
        if not patch_path.exists():
            raise RuntimeError(f"Patch {patch_name} is not found in {patch_dir}.")

        patch = patch_ng.fromfile(patch_path)
        if isinstance(patch, bool):
            raise RuntimeError(f"Failed to load patch {patch_name}")
        # NOTE: It'll be nice to check whether the patch applies correctly in this step and
        # give error message about what patch fails with what file. I haven't figured out
        # how to do this with patch-ng.
        patch_success = patch.apply(root=build_dir)
        if not patch_success:
            raise RuntimeError(f"Failed to apply {patch_name}.")

    common.logging.info("Starting build")

    # TODO: built-in variables will likely need a more organized way to pass around
    cimple_builtin_variables: dict[str, str] = {
        "cimple_output_dir": output_dir.as_posix(),
        "cimple_build_dir": build_dir.as_posix(),
        "cimple_image_dir": image_path.as_posix(),
        "cimple_deps_dir": deps_dir.as_posix(),
        "cimple_parallelism": str(parallel),
    }
    # TODO: remove hard-coded platform and arch
    cimple_builtin_variables.update(
        images.ops.get_image_specific_builtin_variables(
            "windows", "x86_64", config.input.image_type, cimple_builtin_variables
        )
    )

    def interpolate_variables(input_str):
        return common.str_interpolation.interpolate(input_str, cimple_builtin_variables)

    # TODO: support overriding rules per-platform
    for rule in config.rules.default:
        if isinstance(rule, str):
            cmd: list[str] = rule.split(" ")
            cwd = build_dir
            env = {}
        else:
            cmd = rule.rule if isinstance(rule.rule, list) else rule.rule.split(" ")
            # TODO: Check to make sure cwd is valid and relative
            cwd = build_dir / interpolate_variables(rule.cwd) if rule.cwd else build_dir
            env = rule.env if rule.env else {}

        interpolated_cmd = []
        interpolated_env = {}

        for cmd_item in cmd:
            interpolated_cmd.append(interpolate_variables(cmd_item))
        for env_key, env_val in env.items():
            interpolated_env[interpolate_variables(env_key)] = interpolate_variables(env_val)

        process = common.cmd.run_command(
            interpolated_cmd,
            image_path=image_path,
            dependency_path=deps_dir,
            cwd=cwd,
            env=interpolated_env,
        )
        if process.returncode != 0:
            raise RuntimeError(
                f"Failed executing {' '.join(cmd)}, return code {process.returncode}."
            )

    common.logging.info("Build result is available in %s", output_dir)
    return output_dir
