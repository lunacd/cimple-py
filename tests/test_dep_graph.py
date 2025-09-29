import pytest

from cimple import snapshot
from cimple.models import pkg as pkg_models


@pytest.mark.usefixtures("basic_cimple_store")
def test_get_build_depends():
    # Given: a basic snapshot
    cimple_snapshot = snapshot.core.load_snapshot("test-snapshot")

    # When: getting the build dependencies for a package
    build_deps = cimple_snapshot.build_depends_of(pkg_models.src_pkg_id("pkg1"))

    # Then: returns the correct build dependencies, direct and transitive
    assert sorted(build_deps) == ["bin:pkg2-bin", "bin:pkg3-bin"]
