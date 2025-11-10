import dataclasses
import typing


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


PkgId = SrcPkgId | BinPkgId


# def pkg_is_src(pkg_str: PkgId) -> typing.TypeGuard[SrcPkgId]:
#     return pkg_str.type == "src"
#
#
# def pkg_is_bin(pkg_str: PkgId) -> typing.TypeGuard[BinPkgId]:
#     return pkg_str.startswith("bin:")


# def is_pkg_id(obj: typing.Any) -> typing.TypeGuard[PkgId]:
#     return isinstance(obj, str) and (obj.startswith("src:") or obj.startswith("bin:"))


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
