import pathlib
import tomllib
import typing

import pydantic


class PkgConfigPkg(pydantic.BaseModel):
    """
    pkg section of a cimple package config
    """

    name: str

    # TODO: get a enum of all possible platforms
    supported_platforms: list[str]

    version: str

    depends: list[str]
    build_depends: list[str]


class PkgConfigInput(pydantic.BaseModel):
    """
    input section of a cimple package config
    """

    sha256: str
    source_version: str
    tarball_root_dir: str
    tarball_compression: typing.Literal["gz", "xz"] = "gz"
    image_type: str = "default"
    patches: list[str] = []


class PkgConfigRule(pydantic.BaseModel):
    """
    A detailed package rule with more configuration options
    """

    # This is a string not Path because it could refer to builtin variables
    cwd: str | None = None

    env: dict[str, str] | None = None
    rule: str | list[str]


class PkgConfigRules(pydantic.BaseModel):
    """
    rules section of a cimple package config
    """

    default: list[str | PkgConfigRule]


class PkgConfig(pydantic.BaseModel):
    """
    Config for a cimple PI package
    """

    schema_version: typing.Literal[0]
    pkg: PkgConfigPkg
    input: PkgConfigInput
    rules: PkgConfigRules


def load_pkg_config(pkg_path: pathlib.Path):
    config_path = pkg_path / "pkg.toml"
    with config_path.open("rb") as f:
        config_dict = tomllib.load(f)
        return PkgConfig.model_validate(config_dict)
