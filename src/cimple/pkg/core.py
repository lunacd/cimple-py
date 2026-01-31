import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import cimple.models.pkg


@dataclasses.dataclass
class PackageDependencies:
    build_depends: dict[cimple.models.pkg.SrcPkgId, list[cimple.models.pkg.BinPkgId]]
    depends: dict[cimple.models.pkg.BinPkgId, list[cimple.models.pkg.BinPkgId]]
