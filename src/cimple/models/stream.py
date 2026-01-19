import typing

import pydantic

import cimple.models.pkg


class Stream(pydantic.BaseModel):
    schema_version: typing.Literal["0"]
    bootstrap_pkgs: typing.Annotated[
        list[cimple.models.pkg.SrcPkgId],
        pydantic.BeforeValidator(cimple.models.pkg.src_pkg_id_list_validator),
    ]
    toolchain_pkgs: typing.Annotated[
        list[cimple.models.pkg.SrcPkgId],
        pydantic.BeforeValidator(cimple.models.pkg.src_pkg_id_list_validator),
    ]
    pkgs: list[cimple.models.pkg.VersionedSrcPkg]

    @property
    def all_pkgs(self) -> set[cimple.models.pkg.SrcPkgId]:
        return {pkg.id for pkg in self.pkgs}

    @pydantic.field_serializer("bootstrap_pkgs")
    def serialize_bootstrap_pkgs(
        self, bootstrap_pkgs: list[cimple.models.pkg.SrcPkgId]
    ) -> list[str]:
        return [pkg_id.name for pkg_id in bootstrap_pkgs]

    @pydantic.field_serializer("toolchain_pkgs")
    def serialize_toolchain_pkgs(
        self, toolchain_pkgs: list[cimple.models.pkg.SrcPkgId]
    ) -> list[str]:
        return [pkg_id.name for pkg_id in toolchain_pkgs]
