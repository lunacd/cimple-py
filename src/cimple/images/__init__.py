__all__ = ["ops"]

import shutil
import tarfile
import typing

import requests

import cimple.constants
import cimple.logging
from cimple.images import ops

# Re-exports
from cimple.tarfile import writable_extract_filter

if typing.TYPE_CHECKING:
    import pathlib


def get_image(image_name: str):
    if not cimple.constants.cimple_image_dir.is_dir():
        cimple.constants.cimple_image_dir.mkdir(parents=True)

    image_file_name = f"{image_name}.tar.gz"
    target_path = cimple.constants.cimple_image_dir / image_file_name
    if target_path.is_file():
        cimple.logging.info("Using existing image %s", image_file_name)
        return
    url = f"https://cimple-pi.lunacd.com/image/{image_file_name}"
    r = requests.get(url, allow_redirects=True)
    r.raise_for_status()
    with target_path.open("wb") as f:
        f.write(r.content)


def prepare_image(platform: str, arch: str, variant: str) -> pathlib.Path:
    if not cimple.constants.cimple_image_dir.is_dir():
        cimple.constants.cimple_image_dir.mkdir(parents=True)

    image_name = f"{platform}-{variant}-{arch}"
    target_path = cimple.constants.cimple_extracted_image_dir / image_name

    if target_path.is_dir():
        cimple.logging.info("Using existing %s image", image_name)
    else:
        cimple.logging.info("Downloading %s image", image_name)
        get_image(image_name)

        cimple.logging.info("Extracting %s image", image_name)
        with tarfile.open(
            str(cimple.constants.cimple_image_dir / f"{image_name}.tar.gz"),
            "r:gz",
        ) as tar:
            tar.extractall(path=target_path, filter=writable_extract_filter)

    return target_path


def clean_images():
    if cimple.constants.cimple_image_dir.is_dir():
        shutil.rmtree(cimple.constants.cimple_image_dir)
    if cimple.constants.cimple_extracted_image_dir.is_dir():
        shutil.rmtree(cimple.constants.cimple_extracted_image_dir)
