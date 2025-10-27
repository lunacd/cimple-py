import dataclasses
import pathlib
import tarfile
import tempfile
import typing

import patch_ng
import requests

import cimple.constants
import cimple.hash
import cimple.logging
import cimple.process
import cimple.snapshot.core as snapshot_core
import cimple.str_interpolation
import cimple.tarfile
import cimple.util
from cimple import images
from cimple.models import pkg as pkg_models
from cimple.models import pkg_config as pkg_config_models
from cimple.models import snapshot as snapshot_models
from cimple.pkg import cygwin as pkg_cygwin


@dataclasses.dataclass
class PackageDependencies:
    build_depends: list[pkg_models.BinPkgId]
    depends: dict[pkg_models.BinPkgId, list[pkg_models.BinPkgId]]


class PkgOps:
    def __init__(self):
        self.cygwin_release: None | pkg_cygwin.CygwinRelease = None

    def initialize_cygwin(self):
        if self.cygwin_release is None:
            self.cygwin_release = pkg_cygwin.CygwinRelease()
            self.cygwin_release.parse_release_from_repo()

    def install_package_and_deps(
        self,
        target_path: pathlib.Path,
        pkg_id: pkg_models.BinPkgId,
        cimple_snapshot: snapshot_core.CimpleSnapshot,
    ):
        """
        Install a package and its transitive dependencies into the target path.
        """
        # Ensure the target path exists
        cimple.util.ensure_path(target_path)

        # Install the package itself
        self.install_pkg(target_path, pkg_id, cimple_snapshot)

        # Install transitive dependencies
        transitive_bin_deps = cimple_snapshot.runtime_depends_of(pkg_id)

        for dep in transitive_bin_deps:
            self.install_pkg(target_path, dep, cimple_snapshot)

    def install_pkg(
        self,
        target_path: pathlib.Path,
        pkg_id: pkg_models.BinPkgId,
        cimple_snapshot: snapshot_core.CimpleSnapshot,
    ):
        cimple.logging.info("Installing %s", pkg_id)

        pkg_data = cimple_snapshot.get_snapshot_pkg(pkg_id)
        if pkg_data is None:
            raise RuntimeError(
                f"Requested package {pkg_id} not found in snapshot {cimple_snapshot.name}."
            )
        assert snapshot_models.snapshot_pkg_is_bin(pkg_data.root)

        with tarfile.open(
            cimple.constants.cimple_pkg_dir / pkg_data.root.tarball_name,
            cimple.tarfile.get_tarfile_mode("r", pkg_data.root.compression_method),
        ) as tar:
            tar.extractall(target_path, filter=cimple.tarfile.writable_extract_filter)

    def _build_custom_pkg(
        self,
        config: pkg_config_models.PkgConfigCustom,
        *,
        pi_path: pathlib.Path,
        cimple_snapshot: snapshot_core.CimpleSnapshot,
        parallel: int,
    ) -> pathlib.Path:
        # Prepare chroot image
        cimple.logging.info("Preparing image")
        # TODO: support multiple platforms and arch
        if config.input.image_type is None:
            image_path = None
        else:
            image_path = images.prepare_image("windows", "x86_64", config.input.image_type)

        # Ensure needed directories exist
        cimple.util.ensure_path(cimple.constants.cimple_orig_dir)
        cimple.util.ensure_path(cimple.constants.cimple_pkg_build_dir)
        cimple.util.ensure_path(cimple.constants.cimple_pkg_output_dir)
        cimple.util.ensure_path(cimple.constants.cimple_deps_dir)

        # Get source tarball
        cimple.logging.info("Fetching original source")
        pkg_full_name = f"{config.name}-{config.version}"
        pkg_tarball_name = (
            f"{config.name}-{config.input.source_version}.tar.{config.input.tarball_compression}"
        )
        orig_file = cimple.constants.cimple_orig_dir / pkg_tarball_name
        if not orig_file.exists():
            source_url = f"https://cimple-pi.lunacd.com/orig/{pkg_tarball_name}"
            res = requests.get(source_url)
            res.raise_for_status()
            with orig_file.open("wb") as f:
                _ = f.write(res.content)

        # Verify source tarball
        cimple.logging.info("Verifying original source")
        orig_hash = cimple.hash.hash_file(orig_file, sha_type="sha256")
        if orig_hash != config.input.sha256:
            raise RuntimeError(
                "Corrupted original source tarball, "
                f"expecting SHA256 {config.input.sha256} but got {orig_hash}."
            )

        # Install dependencies
        cimple.logging.info("Installing dependencies")
        deps_dir = cimple.constants.cimple_deps_dir / pkg_full_name
        cimple.util.clear_path(deps_dir)
        for dep in config.pkg.build_depends:
            self.install_package_and_deps(deps_dir, dep, cimple_snapshot)

        # Prepare build and output directories
        build_dir = cimple.constants.cimple_pkg_build_dir / pkg_full_name
        output_dir = cimple.constants.cimple_pkg_output_dir / pkg_full_name
        cimple.util.clear_path(build_dir)
        cimple.util.clear_path(output_dir)

        # Extract source tarball
        # TODO: make this unique per build somehow
        cimple.logging.info("Extracting original source")
        with tarfile.open(
            orig_file, cimple.tarfile.get_tarfile_mode("r", config.input.tarball_compression)
        ) as tar:
            if config.input.tarball_root_dir is None:
                tar.extractall(build_dir, filter=cimple.tarfile.writable_extract_filter)
            else:
                cimple.tarfile.extract_directory_from_tar(
                    tar, config.input.tarball_root_dir, build_dir
                )

        cimple.logging.info("Patching source")
        pkg_path = pi_path / "pkg" / config.name / config.version
        patch_dir = pkg_path / "patches"
        for patch_name in config.input.patches:
            cimple.logging.info("Applying %s", patch_name)
            patch_path = patch_dir / patch_name
            if not patch_path.exists():
                raise RuntimeError(f"Patch {patch_name} is not found in {patch_dir}.")

            patch = patch_ng.fromfile(patch_path)
            if isinstance(patch, bool):
                raise RuntimeError(f"Failed to load patch {patch_name}")
            # NOTE: It'll be nice to check whether the patch applies correctly in this step and
            # give error message about what patch fails with what file. I haven't figured out
            # how to do this with patch-ng.
            patch_success = patch.apply(root=build_dir)
            if not patch_success:
                raise RuntimeError(f"Failed to apply {patch_name}.")

        cimple.logging.info("Starting build")

        # TODO: built-in variables will likely need a more organized way to pass around
        cimple_builtin_variables: dict[str, str] = {
            "cimple_output_dir": output_dir.as_posix(),
            "cimple_build_dir": build_dir.as_posix(),
            "cimple_image_dir": "" if image_path is None else image_path.as_posix(),
            "cimple_deps_dir": deps_dir.as_posix(),
            "cimple_parallelism": str(parallel),
        }
        # TODO: remove hard-coded platform and arch
        cimple_builtin_variables.update(
            images.ops.get_image_specific_builtin_variables(
                "windows", "x86_64", config.input.image_type, cimple_builtin_variables
            )
        )

        def interpolate_variables(input_str: str):
            return cimple.str_interpolation.interpolate(input_str, cimple_builtin_variables)

        # TODO: support overriding rules per-platform
        for rule in config.rules.default:
            if isinstance(rule, str):
                cmd: list[str] = rule.split(" ")
                cwd = build_dir
                env = {}
            else:
                cmd = rule.rule if isinstance(rule.rule, list) else rule.rule.split(" ")
                # TODO: Check to make sure cwd is valid and relative
                cwd = build_dir / interpolate_variables(rule.cwd) if rule.cwd else build_dir
                env = rule.env if rule.env else {}

            interpolated_cmd: list[str] = []
            interpolated_env: dict[str, str] = {}

            for cmd_item in cmd:
                interpolated_cmd.append(interpolate_variables(cmd_item))
            for env_key, env_val in env.items():
                interpolated_env[interpolate_variables(env_key)] = interpolate_variables(env_val)

            process = cimple.process.run_command(
                interpolated_cmd,
                image_path=image_path,
                dependency_path=deps_dir,
                cwd=cwd,
                env=interpolated_env,
            )
            if process.returncode != 0:
                raise RuntimeError(
                    f"Failed executing {' '.join(cmd)}, return code {process.returncode}."
                )

        cimple.logging.info("Build result is available in %s", output_dir)
        return output_dir

    def _build_cygwin_pkg(
        self,
        pkg_config: pkg_config_models.PkgConfigCygwin,
    ) -> pathlib.Path:
        # Download and parse Cygwin release file
        self.initialize_cygwin()
        assert self.cygwin_release is not None
        cygwin_install_path = self.cygwin_release.packages[
            f"{pkg_config.name}-{pkg_config.version}"
        ].install_path

        # Prepare output directory
        output_dir = (
            cimple.constants.cimple_pkg_output_dir / f"{pkg_config.name}-{pkg_config.version}"
        )
        cimple.util.clear_path(output_dir)

        # Download Cygwin tarball
        with tempfile.TemporaryDirectory() as temp_dir:
            downloaded_install_file = pkg_cygwin.download_cygwin_file(
                cygwin_install_path, pathlib.Path(temp_dir)
            )

            # Extract to output directory
            cimple.tarfile.extract(downloaded_install_file, output_dir)

        return output_dir

    def build_pkg(
        self,
        package_id: pkg_models.SrcPkgId,
        package_version: str,
        *,
        pi_path: pathlib.Path,
        cimple_snapshot: snapshot_core.CimpleSnapshot,
        parallel: int,
    ) -> pathlib.Path:
        config = pkg_config_models.load_pkg_config(pi_path, package_id, package_version)

        match config.root.pkg_type:
            case "custom":
                return self._build_custom_pkg(
                    typing.cast("pkg_config_models.PkgConfigCustom", config.root),
                    cimple_snapshot=cimple_snapshot,
                    pi_path=pi_path,
                    parallel=parallel,
                )
            case "cygwin":
                return self._build_cygwin_pkg(
                    typing.cast("pkg_config_models.PkgConfigCygwin", config.root),
                )
            case _:
                raise RuntimeError(f"Unknown package type {config.root.pkg_type}")

    def resolve_dependencies(
        self, package_id: pkg_models.SrcPkgId, package_version: str, *, pi_path: pathlib.Path
    ) -> PackageDependencies:
        config = pkg_config_models.load_pkg_config(pi_path, package_id, package_version)
        if config.root.pkg_type == "custom":
            # TODO: figure out multiple binary package for custom package
            depends: dict[pkg_models.BinPkgId, list[pkg_models.BinPkgId]] = {}
        elif config.root.pkg_type == "cygwin":
            self.initialize_cygwin()
            assert self.cygwin_release is not None
            pkg_full_name = f"{config.root.name}-{config.root.version}"
            if pkg_full_name not in self.cygwin_release.packages:
                raise RuntimeError(f"Package {pkg_full_name} not found in Cygwin release.")
            pkg_info = self.cygwin_release.packages[pkg_full_name]
            depends = {
                pkg_models.bin_pkg_id(pkg_models.unqualified_pkg_name(package_id)): [
                    pkg_models.bin_pkg_id(dep) for dep in pkg_info.depends
                ]
            }
        else:
            raise RuntimeError(f"Unknown package type {config.root.pkg_type}")
        return PackageDependencies(build_depends=config.root.build_depends, depends=depends)
