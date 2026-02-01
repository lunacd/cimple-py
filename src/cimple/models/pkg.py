import dataclasses
import typing

import pydantic


@dataclasses.dataclass
class SrcPkgId:
    name: str
    type: typing.Literal["src"]

    def __init__(self, name: str) -> None:
        self.name = name
        self.type = "src"

    def __hash__(self):
        return hash(f"src:{self.name}")


@dataclasses.dataclass
class BinPkgId:
    name: str
    type: typing.Literal["bin"]

    def __init__(self, name: str) -> None:
        self.name = name
        self.type = "bin"

    def __hash__(self):
        return hash(f"bin:{self.name}")


class VersionedSrcPkg(pydantic.BaseModel):
    name: str
    version: str

    @property
    def id(self) -> SrcPkgId:
        return SrcPkgId(self.name)


def is_bin_pkg_list(pkgs: list[PkgId]) -> typing.TypeGuard[list[BinPkgId]]:
    return all(pkg.type == "bin" for pkg in pkgs)


PkgId = SrcPkgId | BinPkgId


def bin_pkg_id_list_validator(input: list[str]) -> list[typing.Any]:
    return [
        {
            "name": name,
            "type": "bin",
        }
        for name in input
    ]


def src_pkg_id_list_validator(input: list[str]) -> list[typing.Any]:
    return [
        {
            "name": name,
            "type": "src",
        }
        for name in input
    ]


def bootstrap_src_id(pkg_id: SrcPkgId) -> SrcPkgId:
    return SrcPkgId(f"bootstrap:{pkg_id.name}")


def bootstrap_bin_id(pkg_id: BinPkgId) -> BinPkgId:
    return BinPkgId(f"bootstrap:{pkg_id.name}")


def prev_src_id(pkg_id: SrcPkgId) -> SrcPkgId:
    return SrcPkgId(f"prev:{pkg_id.name}")


def prev_bin_id(pkg_id: BinPkgId) -> BinPkgId:
    return BinPkgId(f"prev:{pkg_id.name}")
