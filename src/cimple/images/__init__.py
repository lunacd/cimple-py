__all__ = ["windows_bootstrap_msys_x86_64"]

import pathlib
import shutil
import tarfile

import requests

import cimple.common as common

# Re-exports
import cimple.images.windows_bootstrap_msys_x86_64 as windows_bootstrap_msys_x86_64


def get_image(image_name: str):
    if not common.constants.cimple_image_dir.is_dir():
        common.constants.cimple_image_dir.mkdir(parents=True)

    image_file_name = f"{image_name}.tar.gz"
    target_path = common.constants.cimple_image_dir / image_file_name
    url = f"https://cimple-pi.lunacd.com/image/{image_file_name}"
    r = requests.get(url, allow_redirects=True)
    r.raise_for_status()
    with target_path.open("wb") as f:
        f.write(r.content)


def prepare_image(platform: str, arch: str, variant: str) -> pathlib.Path:
    if not common.constants.cimple_image_dir.is_dir():
        common.constants.cimple_image_dir.mkdir(parents=True)

    image_name = f"{platform}-{variant}-{arch}"
    target_path = common.constants.cimple_extracted_image_dir / image_name

    if target_path.is_dir():
        common.logging.info("Using existing %s image", image_name)
    else:
        common.logging.info("Downloading %s image", image_name)
        get_image(image_name)

        common.logging.info("Extracting %s image", image_name)
        with tarfile.open(
            str(common.constants.cimple_image_dir / f"{image_name}.tar.gz"),
            "r:gz",
        ) as tar:
            tar.extractall(path=target_path)

    return target_path


def clean_images():
    if common.constants.cimple_image_dir.is_dir():
        shutil.rmtree(common.constants.cimple_image_dir)
    if common.constants.cimple_extracted_image_dir.is_dir():
        shutil.rmtree(common.constants.cimple_extracted_image_dir)
