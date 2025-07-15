import typing

import pydantic

import cimple.pkg as pkg


class SnapshotPkg(pydantic.BaseModel):
    name: str
    version: str
    sha256: str
    compression_method: typing.Literal["xz"]
    depends: list[str]
    build_depends: list[str]


class SnapshotChanges(pydantic.BaseModel):
    add: list[pkg.PkgId]
    remove: list[str]


class Snapshot(pydantic.BaseModel):
    version: typing.Literal[0]
    pkgs: list[SnapshotPkg]
    ancestor: str
    changes: SnapshotChanges
