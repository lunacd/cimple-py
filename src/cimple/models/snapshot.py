import typing

import pydantic

from cimple.models import pkg as pkg_models


class SnapshotSrcPkg(pydantic.BaseModel):
    name: str
    version: str
    build_depends: typing.Annotated[
        list[pkg_models.BinPkgId], pydantic.BeforeValidator(pkg_models.bin_pkg_id_list_validator)
    ]
    binary_packages: typing.Annotated[
        list[pkg_models.BinPkgId], pydantic.BeforeValidator(pkg_models.bin_pkg_id_list_validator)
    ]
    pkg_type: typing.Literal["src"]

    @pydantic.field_serializer("build_depends")
    def serialize_build_depends(self, build_depends: list[pkg_models.BinPkgId]) -> list[str]:
        return [pkg_id.name for pkg_id in build_depends]

    @pydantic.field_serializer("binary_packages")
    def serialize_binary_packages(self, binary_packages: list[pkg_models.BinPkgId]) -> list[str]:
        return [pkg_id.name for pkg_id in binary_packages]

    @property
    def id(self) -> pkg_models.SrcPkgId:
        return pkg_models.SrcPkgId(self.name)


class SnapshotBinPkg(pydantic.BaseModel):
    name: str
    sha256: str
    compression_method: typing.Literal["xz"]
    depends: typing.Annotated[
        list[pkg_models.BinPkgId], pydantic.BeforeValidator(pkg_models.bin_pkg_id_list_validator)
    ]
    pkg_type: typing.Literal["bin"]

    @pydantic.field_serializer("depends")
    def serialize_depends(self, depends: list[pkg_models.BinPkgId]) -> list[str]:
        return [pkg_id.name for pkg_id in depends]

    @property
    def id(self) -> pkg_models.BinPkgId:
        return pkg_models.BinPkgId(self.name)

    @property
    def tarball_name(self) -> str:
        return f"{self.name}-{self.sha256}.tar.{self.compression_method}"


class SnapshotPkg(pydantic.RootModel):
    root: typing.Union[SnapshotSrcPkg, SnapshotBinPkg] = pydantic.Field(discriminator="pkg_type")  # noqa: UP007


def snapshot_pkg_is_src(
    snapshot_pkg: SnapshotSrcPkg | SnapshotBinPkg,
) -> typing.TypeGuard[SnapshotSrcPkg]:
    return snapshot_pkg.pkg_type == "src"


def snapshot_pkg_is_bin(
    snapshot_pkg: SnapshotSrcPkg | SnapshotBinPkg,
) -> typing.TypeGuard[SnapshotBinPkg]:
    return snapshot_pkg.pkg_type == "bin"


class SnapshotChangeAdd(pydantic.BaseModel):
    name: str
    version: str

    @property
    def id(self) -> pkg_models.SrcPkgId:
        return pkg_models.SrcPkgId(self.name)


class SnapshotChangeUpdate(pydantic.BaseModel):
    name: str
    from_version: str = pydantic.Field(alias="from")
    to_version: str = pydantic.Field(alias="to")

    @property
    def id(self) -> pkg_models.SrcPkgId:
        return pkg_models.SrcPkgId(self.name)


class SnapshotChanges(pydantic.BaseModel):
    add: list[SnapshotChangeAdd]
    remove: typing.Annotated[
        list[pkg_models.SrcPkgId], pydantic.BeforeValidator(pkg_models.src_pkg_id_list_validator)
    ]
    update: list[SnapshotChangeUpdate]

    @pydantic.field_serializer("remove")
    def serialize_remove(self, remove: list[pkg_models.SrcPkgId]) -> list[str]:
        return [pkg_id.name for pkg_id in remove]


class SnapshotModel(pydantic.BaseModel):
    version: typing.Literal[0]
    name: str
    pkgs: list[SnapshotPkg]
    bootstrap_pkgs: list[SnapshotPkg]
    ancestor: str | None
    changes: SnapshotChanges
    bootstrap_changes: SnapshotChanges
