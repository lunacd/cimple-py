import typing

import pydantic

import cimple.models.pkg as pkg


class SnapshotPkg(pydantic.BaseModel):
    name: str
    version: str
    sha256: str
    compression_method: typing.Literal["xz"]
    depends: list[str]
    build_depends: list[str]

    @pydantic.computed_field
    @property
    def full_name(self) -> str:
        return f"{self.name}-{self.version}-{self.sha256}.tar.{self.compression_method}"


class SnapshotChanges(pydantic.BaseModel):
    add: list[pkg.PkgId]
    remove: list[str]


class Snapshot(pydantic.BaseModel):
    version: typing.Literal[0]
    pkgs: list[SnapshotPkg]
    ancestor: str
    changes: SnapshotChanges
