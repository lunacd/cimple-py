import pytest

import cimple.graph
import cimple.snapshot.core as snapshot_core
from cimple.models import pkg as pkg_models


@pytest.mark.usefixtures("basic_cimple_store")
def test_get_build_depends():
    # Given: a basic snapshot
    cimple_snapshot = snapshot_core.load_snapshot("test-snapshot")

    # When: getting the build dependencies for a package
    build_deps = cimple_snapshot.build_depends_of(pkg_models.SrcPkgId("pkg1"))

    # Then: returns the correct build dependencies, direct and transitive
    # The dep-graph is as follows:
    # pkg1 -> pkg2-bin -> pkg3-bin
    # pkg2 -> pkg4-bin
    # If graph traversal incorrectly considers build-depends of runtime deps,
    # pkg1 would also depend on pkg4-bin, which is incorrect.
    assert all(d.type == "bin" for d in build_deps)
    assert sorted([d.name for d in build_deps]) == ["pkg2-bin", "pkg3-bin"]


@pytest.mark.usefixtures("basic_cimple_store")
def test_build_graph():
    # Given: a build graph, constructed from a reversed dep graph
    cimple_snapshot = snapshot_core.load_snapshot("test-snapshot")
    build_graph = cimple.graph.BuildGraph(cimple_snapshot.graph.reverse())

    # When: getting 1 package to build
    pkgs_to_build = build_graph.get_pkgs_to_build(max_count=1)

    # Then: returns either pkg3 or pkg4, as they have no build dependencies
    assert len(pkgs_to_build) == 1
    assert pkgs_to_build[0] in {
        pkg_models.SrcPkgId("pkg3"),
        pkg_models.SrcPkgId("pkg4"),
    }

    # When: getting 2 packages to build
    pkgs_to_build = build_graph.get_pkgs_to_build(max_count=2)

    # Then: returns the remaining package that has no build dependencies
    assert len(pkgs_to_build) == 1
    assert pkgs_to_build[0] in {
        pkg_models.SrcPkgId("pkg3"),
        pkg_models.SrcPkgId("pkg4"),
    }

    # When: marking pkg4 as built
    build_graph.mark_pkgs_built(pkg_models.SrcPkgId("pkg4"))

    # And when: getting 2 more packages to build
    pkgs_to_build = build_graph.get_pkgs_to_build(max_count=2)

    # Then: returns pkg2, as its build dependency pkg4-bin is now built
    assert len(pkgs_to_build) == 1
    assert pkgs_to_build[0] == pkg_models.SrcPkgId("pkg2")

    # When: marking pkg2 as built
    build_graph.mark_pkgs_built(pkg_models.SrcPkgId("pkg2"))

    # And when: getting 2 more packages to build
    pkgs_to_build = build_graph.get_pkgs_to_build(max_count=2)

    # Then: no packages are ready to build yet, as pkg1 depends on pkg2-bin, and pkg2-bin depends on
    # pkg3-bin
    assert len(pkgs_to_build) == 0

    # When: marking pkg3 as built
    build_graph.mark_pkgs_built(pkg_models.SrcPkgId("pkg3"))

    # And when: getting 2 more packages to build
    pkgs_to_build = build_graph.get_pkgs_to_build(max_count=2)

    # Then: returns pkg1, as its build dependency pkg2-bin is now built
    assert len(pkgs_to_build) == 1
    assert pkgs_to_build[0] == pkg_models.SrcPkgId("pkg1")

    # When: marking pkg1 as built
    build_graph.mark_pkgs_built(pkg_models.SrcPkgId("pkg1"))

    # Then: the build graph is now empty
    assert build_graph.is_empty()
