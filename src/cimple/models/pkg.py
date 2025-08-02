import typing

SrcPkgId = typing.NewType("SrcPkgId", str)
BinPkgId = typing.NewType("BinPkgId", str)

PkgId = SrcPkgId | BinPkgId


def pkg_is_src(pkg_str: PkgId) -> typing.TypeGuard[SrcPkgId]:
    return pkg_str.startswith("src:")


def pkg_is_bin(pkg_str: PkgId) -> typing.TypeGuard[BinPkgId]:
    return pkg_str.startswith("bin:")
