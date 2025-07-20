import pathlib

from cimple import common


def get_image_specific_builtin_variables(
    platform: str, arch: str, variant: str, variables: dict[str, str]
) -> dict[str, str]:
    """
    Returns built-in variables specific to the image platform, architecture, and variant.
    """
    if platform == "windows" and variant == "bootstrap_msys":
        return {
            "cimple_output_dir_cygwin": common.system.to_cygwin_path(
                pathlib.Path(variables["cimple_output_dir"])
            ).as_posix(),
            "cimple_build_dir_cygwin": common.system.to_cygwin_path(
                pathlib.Path(variables["cimple_build_dir"])
            ).as_posix(),
            "cimple_image_dir_cygwin": common.system.to_cygwin_path(
                pathlib.Path(variables["cimple_image_dir"])
            ).as_posix(),
            "cimple_deps_dir_cygwin": common.system.to_cygwin_path(
                pathlib.Path(variables["cimple_deps_dir"])
            ).as_posix(),
        }

    return {}
