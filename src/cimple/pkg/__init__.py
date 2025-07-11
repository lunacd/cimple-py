__all__ = ["pkg_config"]

import shutil
import tarfile

import requests

import cimple.common as common
import cimple.pkg.pkg_config as pkg_config


def build_pkg():
    # with open("./pkg.toml", "rb") as f:
    #     config_dict = tomllib.load(f)
    #     config = pkg_config.PkgConfig.model_validate(config_dict)

    # Prepare chroot image
    common.logging.info("Preparing image")
    image_path = common.image.prepare_image("windows", "x86_64", "bootstrap_msys")

    # TODO: parepare dependency tree

    # Ensure needed directories exist
    if not common.constants.cimple_orig_dir.exists():
        common.constants.cimple_orig_dir.mkdir(parents=True)
    if not (common.constants.cimple_pkg_build_dir.exists()):
        common.constants.cimple_pkg_build_dir.mkdir(parents=True)

    # Get source tarball
    # TODO: read package manifest to find out the URL
    common.logging.info("Fetching original source")
    res = requests.get("https://cimple-pi.lunacd.com/orig/make-4.4.tar.gz")
    orig_file = common.constants.cimple_orig_dir / "make-4.4.tar.gz"
    with orig_file.open("wb") as f:
        f.write(res.content)

    # Extract source tarball
    # TODO: make this unique per build somehow
    common.logging.info("Extracting original source")
    build_dir = common.constants.cimple_pkg_build_dir / "make-4.4"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    with tarfile.open(orig_file, "r:gz") as tar:
        common.tarfile.extract_directory_from_tar(tar, "make-4.4", build_dir)

    # TODO: support patching

    common.logging.info("Starting build")
    commands = [["bash", "./configure"], ["make"]]

    for command in commands:
        common.cmd.run_command(command, image_path=image_path, dependency_path=None, cwd=build_dir)
