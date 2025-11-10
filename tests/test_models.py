import pytest

import cimple.models.pkg_config
import cimple.models.snapshot


@pytest.mark.parametrize(
    "config",
    [
        # Cygwin package
        {"schema_version": 0, "pkg_type": "cygwin", "name": "name", "version": "5.2.21-1"},
        # Custom package
        {
            "schema_version": 0,
            "pkg_type": "custom",
            "name": "name",
            "version": "1.2.3",
            "pkg": {"supported_platforms": ["windows-x86_64"], "build_depends": ["dep1"]},
            "input": {
                "image_type": "image",
                "patches": ["patch1", "patch2"],
                "sha256": "1234",
                "source_version": "1.2.3",
                "tarball_compression": "gz",
                "tarball_root_dir": "root",
            },
            "rules": {
                "default": [
                    "cmake -S . -B build -DCMAKE_BUILD_TYPE=Release",
                    {"cwd": "/build/dir", "env": {"VAR1": "value1"}, "rule": ["make", "-j4"]},
                ]
            },
            "binaries": {"cmake": {"depends": ["cygwin"]}},
        },
    ],
)
def test_pkg_config_model_round_trip(config):
    # WHEN: loading and then serializing a package config model
    model = cimple.models.pkg_config.PkgConfig.model_validate(config)
    result = model.model_dump()

    # THEN: the result matches the original config
    assert result == config


@pytest.mark.parametrize(
    "snapshot",
    [
        {
            "version": 0,
            "name": "test_snapshot",
            "pkgs": [
                {
                    "name": "pkg1",
                    "version": "1.0",
                    "pkg_type": "src",
                    "build_depends": ["pkg2-bin"],
                    "binary_packages": ["pkg1-bin"],
                },
                {
                    "name": "pkg1-bin",
                    "sha256": "a4defb8341593d4deea245993aeb3ce54de060affb10cb9ae60ec3789dd3f241",
                    "pkg_type": "bin",
                    "compression_method": "xz",
                    "depends": [],
                },
            ],
            "ancestor": "root",
            "changes": {"add": ["pkg1"], "remove": ["pkg2"]},
        }
    ],
)
def test_snapshot_model_round_trip(snapshot):
    # WHEN: loading and then serializing a snapshot model
    model = cimple.models.snapshot.SnapshotModel.model_validate(snapshot)
    result = model.model_dump()

    # THEN: the result matches the original snapshot data
    assert result == snapshot
