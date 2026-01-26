import typing

import pydantic

# cimple.models.pkg are used by pydantic models, which will be reflected upon
# So we need to import it always, instead of just in an TYPE_CHECKING block
import cimple.models.pkg  # noqa: TC001


class StreamConfig(pydantic.BaseModel):
    schema_version: typing.Literal["0"]
    pkgs: list[cimple.models.pkg.VersionedSrcPkg]
    bootstrap_pkgs: list[cimple.models.pkg.VersionedSrcPkg]


class StreamData(pydantic.BaseModel):
    """
    Stream data stored in the cimple store.
    """

    schema_version: typing.Literal["0"]
    name: str
    latest_snapshot: str
