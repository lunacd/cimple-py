import pytest

import cimple.snapshot.core as snapshot_core
from cimple.models import pkg as pkg_models


@pytest.mark.usefixtures("basic_cimple_store")
def test_get_build_depends():
    # Given: a basic snapshot
    cimple_snapshot = snapshot_core.load_snapshot("test-snapshot")

    # When: getting the build dependencies for a package
    build_deps = cimple_snapshot.build_depends_of(pkg_models.SrcPkgId("pkg1"))

    # Then: returns the correct build dependencies, direct and transitive
    assert all(d.type == "bin" for d in build_deps)
    assert sorted([d.name for d in build_deps]) == ["pkg2-bin", "pkg3-bin"]
