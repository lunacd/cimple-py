import typing

SrcPkgId = typing.NewType("SrcPkgId", str)
BinPkgId = typing.NewType("BinPkgId", str)

PkgId = SrcPkgId | BinPkgId


def src_pkg_id(name: str) -> SrcPkgId:
    return typing.cast("SrcPkgId", f"src:{name}")


def bin_pkg_id(name: str) -> BinPkgId:
    return typing.cast("BinPkgId", f"bin:{name}")


def unqualified_pkg_name(id: PkgId) -> str:
    return id.split(":", 1)[1]


def pkg_is_src(pkg_str: PkgId) -> typing.TypeGuard[SrcPkgId]:
    return pkg_str.startswith("src:")


def pkg_is_bin(pkg_str: PkgId) -> typing.TypeGuard[BinPkgId]:
    return pkg_str.startswith("bin:")


def is_pkg_id(obj: typing.Any) -> typing.TypeGuard[PkgId]:
    return isinstance(obj, str) and (obj.startswith("src:") or obj.startswith("bin:"))
