import typing

import pydantic


class BinPkgId(pydantic.BaseModel):
    """
    A BinPkgId uniquely identifies a binary package.
    """

    name: str
    sha256: str
    pkg_type: typing.Literal["bin"] = "bin"

    @property
    def full_name(self) -> str:
        return f"{self.pkg_type}:{self.name}"


class SrcPkgId(pydantic.BaseModel):
    """
    A SrcPkgId uniquely identifies a source package.
    """

    name: str
    version: str
    pkg_type: typing.Literal["src"] = "src"

    @property
    def full_name(self) -> str:
        return f"{self.pkg_type}:{self.name}"


class PkgId(pydantic.RootModel):
    """
    A PkgId uniquely identifies a package.
    """

    root: typing.Union[SrcPkgId, BinPkgId] = pydantic.Field(discriminator="pkg_type")  # noqa: UP007


def pkg_is_src(pkg_id: SrcPkgId | BinPkgId) -> typing.TypeGuard[SrcPkgId]:
    return pkg_id.pkg_type == "src"


def pkg_is_bin(pkg_id: SrcPkgId | BinPkgId) -> typing.TypeGuard[BinPkgId]:
    return pkg_id.pkg_type == "bin"


def str_pkg_is_src(pkg_str: str) -> bool:
    return pkg_str.startswith("src:")


def str_pkg_is_bin(pkg_str: str) -> bool:
    return pkg_str.startswith("bin:")
