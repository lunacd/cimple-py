import typing

import pydantic


class Stream(pydantic.BaseModel):
    schema_version: typing.Literal["0"]
    bootstrap_pkgs: list[str]
    toolchain_pkgs: list[str]
    pkgs: dict[str, str]
