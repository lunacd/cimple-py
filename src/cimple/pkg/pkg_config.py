import pydantic


class PkgConfigPkg(pydantic.BaseModel):
    """
    pkg section of a cimple package config
    """

    name: str

    # TODO: get a enum of all possible platforms
    supported_platforms: list[str]

    version: str


class PkgConfigInput(pydantic.BaseModel):
    """
    input section of a cimple package config
    """

    sha256: str
    tarball_root_dir: str
    tarball_compression: str = "gz"
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

    pkg: PkgConfigPkg
    input: PkgConfigInput
    rules: PkgConfigRules
