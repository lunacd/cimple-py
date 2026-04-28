import typing

import cimple.models.pkg
import cimple.models.pkg_config

if typing.TYPE_CHECKING:
    import pathlib


def test_load_pkg_config(cimple_pi: pathlib.Path):
    # GIVEN: a basic simple store
    # WHEN: loading a pkg config
    pkg_config = cimple.models.pkg_config.load_pkg_config(
        cimple_pi, cimple.models.pkg.SrcPkgId("pkg1"), "2.0-1"
    )

    # THEN: the pkg config is loaded correctly
    assert pkg_config.id == cimple.models.pkg.SrcPkgId("pkg1")
    assert pkg_config.version == "2.0-1"


def test_load_pkg_config_bootstrap(cimple_pi: pathlib.Path):
    # GIVEN: a basic simple store
    # WHEN: loading a pkg config
    pkg_config = cimple.models.pkg_config.load_pkg_config(
        cimple_pi, cimple.models.pkg.SrcPkgId("bootstrap:bootstrap1"), "1.0.0-1"
    )

    # THEN: the pkg config is loaded correctly
    assert pkg_config.id == cimple.models.pkg.SrcPkgId("bootstrap1")
    assert pkg_config.version == "1.0.0-1"
