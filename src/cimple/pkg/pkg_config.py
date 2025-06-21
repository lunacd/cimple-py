import pydantic


class PkgConfigPkg(pydantic.BaseModel):
    """
    pkg section of a cimple package config
    """

    name: str

    # TODO: get a enum of all possible platforms
    supported_platforms: list[str]


class PkgConfigInput(pydantic.BaseModel):
    """
    input section of a cimple package config
    """

    url: str
    sha256: str


class PkgConfigOutput(pydantic.BaseModel):
    """
    output section of a cimple package config
    """

    sha256: str


class PkgConfigRules(pydantic.BaseModel):
    """
    rules section of a cimple package config
    """

    default: list[str]


class PkgConfig(pydantic.BaseModel):
    """
    Config for a cimple PI package
    """

    version: int
    pkg: PkgConfigPkg
    input: PkgConfigInput
    output: PkgConfigOutput
    rules: PkgConfigRules
