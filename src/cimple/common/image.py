import tarfile
import shutil
import requests

import cimple.common.constants as constants


def get_image(platform: str, arch: str, variant: str):
    if not constants.cimple_image_dir.is_dir():
        constants.cimple_image_dir.mkdir(parents=True)

    image_name = f"{platform}-{arch}-{variant}.tar.gz"
    target_path = constants.cimple_image_dir / image_name
    url = f"https://cimple-pi.lunacd.com/image/{image_name}"
    r = requests.get(url, allow_redirects=True)
    r.raise_for_status()
    open(target_path, "wb").write(r.content)


def prepare_image(platform: str, arch: str, variant: str):
    if not constants.cimple_image_dir.is_dir():
        constants.cimple_image_dir.mkdir(parents=True)

    target_path = constants.cimple_extracted_image_dir / f"{platform}-{arch}-{variant}"
    if not target_path.is_dir():
        get_image(platform, arch, variant)
        with tarfile.open(
            str(constants.cimple_image_dir / f"{platform}-{arch}-{variant}.tar.gz"),
            "r:gz",
        ) as tar:
            tar.extractall(path=target_path)


def clean_images():
    if constants.cimple_image_dir.is_dir():
        shutil.rmtree(constants.cimple_image_dir)
    if constants.cimple_extracted_image_dir.is_dir():
        shutil.rmtree(constants.cimple_extracted_image_dir)
