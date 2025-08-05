import pytest

from cimple import common, pkg, snapshot


@pytest.mark.skipif(
    not common.system.platform_name().startswith("windows"),
    reason="Cygwin is only relevant on Windows",
)
def test_build_cygwin_pkg(
    basic_cimple_store, cimple_pi, cygwin_release_content_side_effect, mocker
):
    # GIVEN: A basic Cimple store with root snapshot
    mocker.patch("cimple.pkg.cygwin.requests.get", side_effect=cygwin_release_content_side_effect)
    cimple_snapshot = snapshot.core.load_snapshot("root")

    # WHEN: Building a Cygwin package (make)
    output_path = pkg.ops.build_pkg(cimple_pi / "make", cimple_snapshot=cimple_snapshot, parallel=8)

    # THEN:
    assert output_path.exists(), f"Output path does not exist: {output_path}"
    assert (output_path / "usr" / "bin" / "make.exe").exists(), "make.exe not found in output"
