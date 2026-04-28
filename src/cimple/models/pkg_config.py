import pathlib  # noqa: TC003
import tomllib
import typing

import pydantic

import cimple.models.pkg


class PkgConfigPkgSection(pydantic.BaseModel):
    """
    pkg section of a cimple package config
    """

    # TODO: get a enum of all possible platforms
    supported_platforms: list[str]

    build_depends: typing.Annotated[
        list[cimple.models.pkg.BinPkgId],
        pydantic.BeforeValidator(cimple.models.pkg.bin_pkg_id_list_validator),
    ]

    @pydantic.field_serializer("build_depends")
    def serialize_build_depends(self, build_depends: list[cimple.models.pkg.BinPkgId]) -> list[str]:
        return [dep.name for dep in build_depends]


class PkgConfigInputSection(pydantic.BaseModel):
    """
    input section of a cimple package config
    """

    sha256: str
    source_version: str
    tarball_root_dir: str | None = None
    tarball_compression: typing.Literal["gz", "xz"] = "gz"
    image_type: str | None = None
    patches: list[str] = []


class PkgConfigNormalizedRule(pydantic.BaseModel):
    """
    A set of rules, normalized based on the platforms and with variables instantiated.
    """

    cwd: pathlib.Path
    rule: list[str]
    env: dict[str, str]


class PkgConfigNormalizedRulesList(pydantic.RootModel):
    root: list[PkgConfigNormalizedRule]


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


class PkgConfigBinarySection(pydantic.BaseModel):
    """
    A binary package produced by a cimple package
    """

    depends: typing.Annotated[
        list[cimple.models.pkg.BinPkgId],
        pydantic.BeforeValidator(cimple.models.pkg.bin_pkg_id_list_validator),
    ] = []
    output_dir: str | None = None

    @pydantic.field_serializer("depends")
    def serialize_depends(self, depends: list[cimple.models.pkg.BinPkgId]) -> list[str]:
        return [dep.name for dep in depends]


class PkgConfig(pydantic.BaseModel):
    """
    Config for a cimple PI package
    """

    schema_version: typing.Literal[0]

    name: str
    version: str

    pkg: PkgConfigPkgSection
    input: PkgConfigInputSection
    rules: PkgConfigRulesSection
    binaries: typing.Annotated[
        dict[cimple.models.pkg.BinPkgId, PkgConfigBinarySection],
        pydantic.BeforeValidator(
            lambda b: {cimple.models.pkg.BinPkgId(k): v for k, v in b.items()}
        ),
    ]

    @pydantic.field_serializer("binaries")
    def serialize_binaries(
        self, binaries: dict[cimple.models.pkg.BinPkgId, PkgConfigBinarySection]
    ) -> dict[str, typing.Any]:
        return {k.name: v for k, v in binaries.items()}

    @property
    def id(self) -> cimple.models.pkg.SrcPkgId:
        return cimple.models.pkg.SrcPkgId(self.name)

    @property
    def binary_packages(self) -> list[cimple.models.pkg.BinPkgId]:
        return list(self.binaries.keys())

    @property
    def build_depends(self) -> list[cimple.models.pkg.BinPkgId]:
        return self.pkg.build_depends


def load_pkg_config(
    pi_path: pathlib.Path, package: cimple.models.pkg.SrcPkgId, package_version: str
):
    if cimple.models.pkg.is_bootstrap_pkg(package):
        package = cimple.models.pkg.SrcPkgId(package.name.removeprefix("bootstrap:"))
    config_path = pi_path / "pkg" / package.name / package_version / "pkg.toml"
    with config_path.open("rb") as f:
        config_dict = tomllib.load(f)
        return PkgConfig.model_validate(config_dict)
