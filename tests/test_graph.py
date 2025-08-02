from cimple import graph, models, snapshot


def test_get_build_depends(basic_cimple_store: None):
    # Given: a basic snapshot
    snapshot_map = snapshot.ops.load_snapshot("test-snapshot")
    dep_graph = graph.get_dep_graph(snapshot_map)

    # When: getting the build dependencies for a package
    build_deps = graph.get_build_depends(dep_graph, models.pkg.SrcPkgId(name="pkg1", version="1.0"))

    # Then: returns the correct build dependencies, direct and transitive
    assert sorted(build_deps) == ["bin:pkg2-bin", "bin:pkg3-bin"]
