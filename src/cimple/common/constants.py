import pathlib

cimple_data_dir = pathlib.Path.home() / ".cimple"

cimple_share_dir = cimple_data_dir / "share"
cimple_local_dir = cimple_data_dir / "local"

cimple_image_dir = cimple_share_dir / "image"
cimple_orig_dir = cimple_share_dir / "orig"
cimple_snapshot_dir = cimple_share_dir / "snapshot"
cimple_pkg_dir = cimple_share_dir / "pkg"

cimple_extracted_image_dir = cimple_local_dir / "extracted_image"
cimple_pkg_build_dir = cimple_local_dir / "pkg_build"
cimple_pkg_output_dir = cimple_local_dir / "pkg_output"
