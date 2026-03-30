import tomllib
import typing

import pydantic

import cimple.models.pkg
import cimple.str_interpolation

if typing.TYPE_CHECKING:
    import pathlib


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


class PkgConfigCygwin(pydantic.BaseModel):
    """
    Config for a Cygwin package
    """

    schema_version: typing.Literal[0]
    pkg_type: typing.Literal["cygwin"] = "cygwin"
    name: str
    version: str

    @property
    def id(self) -> cimple.models.pkg.SrcPkgId:
        return cimple.models.pkg.SrcPkgId(self.name)

    @property
    def binary_packages(self) -> list[cimple.models.pkg.BinPkgId]:
        # Cygwin integration pulls in Cygwin binary packages directly,
        # so it's impossible to have multiple binary packages per source
        return [cimple.models.pkg.BinPkgId(self.name)]

    @property
    def build_depends(self) -> list[cimple.models.pkg.BinPkgId]:
        return []


class PkgConfig(pydantic.RootModel):
    root: typing.Union[PkgConfigCustom, PkgConfigCygwin] = pydantic.Field(discriminator="pkg_type")  # noqa: UP007


def load_pkg_config(
    pi_path: pathlib.Path, package: cimple.models.pkg.SrcPkgId, package_version: str
):
    if cimple.models.pkg.is_bootstrap_pkg(package):
        package = cimple.models.pkg.SrcPkgId(package.name.removeprefix("bootstrap:"))
    config_path = pi_path / "pkg" / package.name / package_version / "pkg.toml"
    with config_path.open("rb") as f:
        config_dict = tomllib.load(f)
        return PkgConfig.model_validate(config_dict)


def normalize_rules(
    rules: PkgConfigRulesSection,
    default_cwd: pathlib.Path,
    builtin_variables: dict[str, str],
) -> list[PkgConfigNormalizedRule]:
    def interpolate_variables(input_str: str):
        return cimple.str_interpolation.interpolate(input_str, builtin_variables)

    # TODO: support overriding rules per-platform
    normalized_rules: list[PkgConfigNormalizedRule] = []
    for rule in rules.default:
        if isinstance(rule, str):
            normalized_rule = PkgConfigNormalizedRule(cwd=default_cwd, env={}, rule=rule.split(" "))
            continue

        normalized_rule = PkgConfigNormalizedRule(
            # TODO: Check to make sure cwd is valid and relative
            cwd=default_cwd / interpolate_variables(rule.cwd) if rule.cwd else default_cwd,
            env=rule.env if rule.env else {},
            rule=rule.rule if isinstance(rule.rule, list) else rule.rule.split(" "),
        )

        # NOTE: at this point, cwd is interpolated, but env and rules are not.
        normalized_rule.env = {
            interpolate_variables(k): interpolate_variables(v)
            for k, v in normalized_rule.env.items()
        }
        normalized_rule.rule = [interpolate_variables(segment) for segment in rule.rule]
        normalized_rules.append(normalized_rule)

    return normalized_rules
