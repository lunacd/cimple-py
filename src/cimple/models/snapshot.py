import typing

import pydantic

from cimple.models import pkg


class SnapshotSrcPkg(pydantic.BaseModel):
    name: str
    version: str
    build_depends: list[str] = []
    binary_packages: list[str]
    pkg_type: typing.Literal["src"]

    @property
    def id(self) -> pkg.SrcPkgId:
        return typing.cast("pkg.SrcPkgId", f"src:{self.name}-{self.version}")


class SnapshotBinPkg(pydantic.BaseModel):
    name: str
    sha256: str
    compression_method: typing.Literal["xz"]
    depends: list[str]
    pkg_type: typing.Literal["bin"]

    @property
    def id(self) -> pkg.BinPkgId:
        return typing.cast("pkg.BinPkgId", f"bin:{self.name}")

    @property
    def tarball_name(self) -> str:
        return f"{self.name}-{self.sha256}.tar.{self.compression_method}"


class SnapshotPkg(pydantic.RootModel):
    root: typing.Union[SnapshotSrcPkg, SnapshotBinPkg] = pydantic.Field(description="pkg_type")  # noqa: UP007

    @property
    def full_name(self) -> str:
        return f"{self.root.pkg_type}:{self.root.name}"


def snapshot_pkg_is_src(
    snapshot_pkg: SnapshotSrcPkg | SnapshotBinPkg,
) -> typing.TypeGuard[SnapshotSrcPkg]:
    return pkg.pkg_is_src(snapshot_pkg.id)


def snapshot_pkg_is_bin(
    snapshot_pkg: SnapshotSrcPkg | SnapshotBinPkg,
) -> typing.TypeGuard[SnapshotBinPkg]:
    return pkg.pkg_is_bin(snapshot_pkg.id)


class SnapshotChanges(pydantic.BaseModel):
    add: list[pkg.PkgId]
    remove: list[str]


class Snapshot(pydantic.BaseModel):
    version: typing.Literal[0]
    name: str
    pkgs: list[SnapshotPkg]
    ancestor: str
    changes: SnapshotChanges
