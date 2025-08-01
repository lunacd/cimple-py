import typing

import pydantic

import cimple.models.pkg as pkg


class SnapshotSrcPkg(pydantic.BaseModel):
    name: str
    version: str
    build_depends: list[str] = []
    binary_packages: list[str]
    pkg_type: typing.Literal["src"]

    @property
    def id(self) -> pkg.SrcPkgId:
        return pkg.SrcPkgId(name=self.name, version=self.version)


class SnapshotBinPkg(pydantic.BaseModel):
    name: str
    sha256: str
    compression_method: typing.Literal["xz"]
    depends: list[str]
    pkg_type: typing.Literal["bin"]

    @property
    def id(self) -> pkg.BinPkgId:
        return pkg.BinPkgId(name=self.name, sha256=self.sha256)

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
        pkgs={pkg.full_name: pkg for pkg in snapshot_data.pkgs},
        ancestor=snapshot_data.ancestor,
        changes=snapshot_data.changes,
    )


def get_snapshot_pkg_from_str_id(snapshot_map: SnapshotMap, pkg_str: str) -> SnapshotPkg | None:
    """
    Get a package from a snapshot by its string ID.
    """
    if pkg_str in snapshot_map.pkgs:
        return snapshot_map.pkgs[pkg_str]
    return None


def get_snapshot_pkg_from_pkg_id(
    snapshot_map: SnapshotMap, pkg_id: pkg.PkgId
) -> SnapshotPkg | None:
    return get_snapshot_pkg_from_str_id(snapshot_map, pkg_id.root.full_name)
