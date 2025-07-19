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

    def full_name(self) -> str:
        return f"{self.name}-{self.version}-{self.sha256}.tar.{self.compression_method}"


class SnapshotChanges(pydantic.BaseModel):
    add: list[pkg.PkgId]
    remove: list[str]


class Snapshot(pydantic.BaseModel):
    version: typing.Literal[0]
    name: str
    pkgs: list[SnapshotPkg]
    ancestor: str
    changes: SnapshotChanges


class SnapshotMap(pydantic.BaseModel):
    """
    A map of package names to their snapshot data.
    This is used to quickly look up package data by name.
    """

    version: typing.Literal[0]
    name: str
    pkgs: dict[str, SnapshotPkg]
    ancestor: str
    changes: SnapshotChanges


def get_snapshot_json_from_map(snapshot_map: SnapshotMap) -> Snapshot:
    """
    Convert a SnapshotMap to a Snapshot.
    """
    return Snapshot(
        version=snapshot_map.version,
        name=snapshot_map.name,
        pkgs=list(snapshot_map.pkgs.values()),
        ancestor=snapshot_map.ancestor,
        changes=snapshot_map.changes,
    )


def get_snapshot_map_from_json(snapshot_data: Snapshot) -> SnapshotMap:
    """
    Convert a Snapshot to a SnapshotMap.
    """
    return SnapshotMap(
        version=snapshot_data.version,
        name=snapshot_data.name,
        pkgs={pkg.name: pkg for pkg in snapshot_data.pkgs},
        ancestor=snapshot_data.ancestor,
        changes=snapshot_data.changes,
    )
