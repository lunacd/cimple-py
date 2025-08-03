import pathlib
import tomllib
import typing

import pydantic


class PkgConfigPkgSection(pydantic.BaseModel):
    """
    pkg section of a cimple package config
    """

    name: str

    # TODO: get a enum of all possible platforms
    supported_platforms: list[str]

    version: str

    depends: list[str]
    build_depends: list[str]


class PkgConfigInputSection(pydantic.BaseModel):
    """
    input section of a cimple package config
    """

    sha256: str
    source_version: str
    tarball_root_dir: str | None = None
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


class PkgConfigRulesSection(pydantic.BaseModel):
    """
    rules section of a cimple package config
    """

    default: list[str | PkgConfigRule]


class PkgConfigCustom(pydantic.BaseModel):
    """
    Config for a cimple PI package
    """

    schema_version: typing.Literal[0]
    pkg_type: typing.Literal["custom"] = "custom"
    pkg: PkgConfigPkgSection
    input: PkgConfigInputSection
    rules: PkgConfigRulesSection


class PkgConfigCygwinSection(pydantic.BaseModel):
    """
    Cygwin package section of a cimple package config
    """

    name: str
    version: str

    cygwin_location: dict[str, str]
    """
    Maps from platform to Cygwin repository location.
    """


class PkgConfigCygwin(pydantic.BaseModel):
    """
    Config for a Cygwin package
    """

    schema_version: typing.Literal[0]
    pkg_type: typing.Literal["cygwin"] = "cygwin"

    cygwin: PkgConfigCygwinSection


class PkgConfig(pydantic.RootModel):
    root: typing.Union[PkgConfigCustom, PkgConfigCygwin] = pydantic.Field(discriminator="pkg_type")  # noqa: UP007


def load_pkg_config(pkg_path: pathlib.Path):
    config_path = pkg_path / "pkg.toml"
    with config_path.open("rb") as f:
        config_dict = tomllib.load(f)
        return PkgConfig.model_validate(config_dict)
