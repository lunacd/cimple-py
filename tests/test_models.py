import pytest

import cimple.models.pkg_config
import cimple.models.snapshot
import cimple.models.stream


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
            "binaries": {"cmake": {"depends": ["cygwin"], "output_dir": None}},
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
            "changes": {
                "add": [{"name": "pkg1", "version": "1.0"}],
                "remove": ["pkg2"],
                "update": [{"name": "pkg3", "from": "2.0", "to": "2.1"}],
            },
        }
    ],
)
def test_snapshot_model_round_trip(snapshot):
    # WHEN: loading and then serializing a snapshot model
    model = cimple.models.snapshot.SnapshotModel.model_validate(snapshot)
    result = model.model_dump(by_alias=True)

    # THEN: the result matches the original snapshot data
    assert result == snapshot


@pytest.mark.parametrize(
    "stream",
    [
        {
            "schema_version": "0",
            "bootstrap_pkgs": ["pkgA", "pkgB"],
            "toolchain_pkgs": ["pkgC"],
            "pkgs": [
                {"name": "pkg1", "version": "1.0"},
                {"name": "pkg2", "version": "2.0"},
            ],
        }
    ],
)
def test_stream_model_round_trip(stream):
    # WHEN: loading and then serializing a stream model
    model = cimple.models.stream.StreamConfig.model_validate(stream)
    result = model.model_dump()

    # THEN: the result matches the original stream data
    assert result == stream
