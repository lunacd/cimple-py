import importlib.resources
import pathlib
import tempfile

import pytest

import cimple.common.tarfile


@pytest.mark.parametrize(
    "path",
    [
        "misc/a_random_tar_gz.tar.gz",
        "misc/a_random_tar_zst.tar.zst",
        "misc/a_random_tar_xz.tar.xz",
    ],
)
def test_extract(path):
    # GIVEN: a temp path
    with (
        importlib.resources.path("tests", f"data/{path}") as tarfile_path,
        tempfile.TemporaryDirectory() as tempdir,
    ):
        tempdir_path = pathlib.Path(tempdir)

        # WHEN: extracting the tarball
        cimple.common.tarfile.extract(tarfile_path, tempdir_path)

        # THEN: it should succeed (by not throwing)
        assert (tempdir_path / "a.txt").exists()


def test_extract_colon_file():
    # GIVEN: a temp path
    with (
        importlib.resources.path("tests", "data/misc/colon.tar.gz") as tarfile_path,
        tempfile.TemporaryDirectory() as tempdir,
    ):
        tempdir_path = pathlib.Path(tempdir)

        # WHEN: extracting the tarball
        # THEN: it should succeed (by not throwing)
        cimple.common.tarfile.extract(tarfile_path, tempdir_path)
