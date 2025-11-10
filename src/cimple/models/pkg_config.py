import tomllib
import typing

import pydantic

from cimple.models import pkg as models_pkg

if typing.TYPE_CHECKING:
    import pathlib


class PkgConfigPkgSection(pydantic.BaseModel):
    """
    pkg section of a cimple package config
    """

    # TODO: get a enum of all possible platforms
    supported_platforms: list[str]

    build_depends: typing.Annotated[
        list[models_pkg.BinPkgId], pydantic.BeforeValidator(models_pkg.bin_pkg_id_list_validator)
    ]

    @pydantic.field_serializer("build_depends")
    def serialize_build_depends(self, build_depends: list[models_pkg.BinPkgId]) -> list[str]:
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
        list[models_pkg.BinPkgId],
        pydantic.BeforeValidator(models_pkg.bin_pkg_id_list_validator),
    ] = []

    @pydantic.field_serializer("depends")
    def serialize_depends(self, depends: list[models_pkg.BinPkgId]) -> list[str]:
        return [dep.name for dep in depends]


class PkgConfigCustom(pydantic.BaseModel):
    """
    Config for a cimple PI package
    """

    schema_version: typing.Literal[0]
    pkg_type: typing.Literal["custom"] = "custom"

    name: str
    version: str

    pkg: PkgConfigPkgSection
    input: PkgConfigInputSection
    rules: PkgConfigRulesSection
    binaries: typing.Annotated[
        dict[models_pkg.BinPkgId, PkgConfigBinarySection],
        pydantic.BeforeValidator(lambda b: {models_pkg.BinPkgId(k): v for k, v in b.items()}),
    ]

    @pydantic.field_serializer("binaries")
    def serialize_binaries(
        self, binaries: dict[models_pkg.BinPkgId, PkgConfigBinarySection]
    ) -> dict[str, typing.Any]:
        return {k.name: v for k, v in binaries.items()}

    @property
    def id(self) -> models_pkg.SrcPkgId:
        return models_pkg.SrcPkgId(self.name)

    @property
    def binary_packages(self) -> list[models_pkg.BinPkgId]:
        # TODO: support multiple binaries per source
        return [models_pkg.BinPkgId(self.name)]

    @property
    def build_depends(self) -> list[models_pkg.BinPkgId]:
        return self.pkg.build_depends


class PkgConfigCygwin(pydantic.BaseModel):
    """
    Config for a Cygwin package
    """

    schema_version: typing.Literal[0]
    pkg_type: typing.Literal["cygwin"] = "cygwin"
    name: str
    version: str

    @property
    def id(self) -> models_pkg.SrcPkgId:
        return models_pkg.SrcPkgId(self.name)

    @property
    def binary_packages(self) -> list[models_pkg.BinPkgId]:
        # Cygwin integration pulls in Cygwin binary packages directly,
        # so it's impossible to have multiple binary packages per source
        return [models_pkg.BinPkgId(self.name)]

    @property
    def build_depends(self) -> list[models_pkg.BinPkgId]:
        return []


class PkgConfig(pydantic.RootModel):
    root: typing.Union[PkgConfigCustom, PkgConfigCygwin] = pydantic.Field(discriminator="pkg_type")  # noqa: UP007


def load_pkg_config(pi_path: pathlib.Path, package: models_pkg.SrcPkgId, package_version: str):
    config_path = pi_path / "pkg" / package.name / package_version / "pkg.toml"
    with config_path.open("rb") as f:
        config_dict = tomllib.load(f)
        return PkgConfig.model_validate(config_dict)
