__all__ = ["ops"]

import typing

import pydantic

import cimple.snapshot.ops as ops


class SnapshotPkg(pydantic.BaseModel):
    name: str
    version: str
    sha256: str
    depends: list[str]
    build_depends: list[str]


class Snapshot(pydantic.BaseModel):
    version: typing.Literal[0]
    pkgs: list[SnapshotPkg]
