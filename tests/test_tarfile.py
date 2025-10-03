import importlib.resources
import tarfile
import tempfile

import cimple.common.tarfile


def test_extract_with_colon_path():
    # GIVEN: a temp path
    with (
        importlib.resources.path(
            "tests", "data/cygwin/x86_64/release/bash/bash-5.2.21-1.tar.xz"
        ) as tarfile_path,
        tempfile.TemporaryDirectory() as tempdir,
        tarfile.open(tarfile_path) as tar,
    ):
        # WHEN: extracting the tarball
        tar.extractall(tempdir, filter=cimple.common.tarfile.writable_extract_filter)
