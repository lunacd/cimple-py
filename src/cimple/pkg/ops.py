import dataclasses
import pathlib
import tarfile
import tempfile

import patch_ng
import requests

import cimple.constants
import cimple.hash
import cimple.logging
import cimple.models.pkg
import cimple.models.pkg_config
import cimple.pkg.core
import cimple.process
import cimple.snapshot.core
import cimple.str_interpolation
import cimple.tarfile
import cimple.util
from cimple import images
from cimple.models import pkg as pkg_models
from cimple.models import pkg_config as pkg_config_models
from cimple.models import snapshot as snapshot_models


@dataclasses.dataclass
class PackageBuildOptions:
    parallel: int = 1
    extra_paths: list[str] = dataclasses.field(default_factory=list)


class PkgOps:
    def install_package_and_deps(
        self,
        target_path: pathlib.Path,
        pkg_id: pkg_models.BinPkgId,
        cimple_snapshot: cimple.snapshot.core.CimpleSnapshot,
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

    @staticmethod
    def install_pkg(
        target_path: pathlib.Path,
        pkg_id: pkg_models.BinPkgId,
        cimple_snapshot: cimple.snapshot.core.CimpleSnapshot,
    ):
        cimple.logging.info("Installing %s", pkg_id.name)

        # Load and install from previous snapshot for `prev:` packages
        if cimple.models.pkg.is_prev_pkg(pkg_id):
            prev_snapshot_name = cimple_snapshot.ancestor
            assert prev_snapshot_name is not None, (
                "Cannot install package from previous snapshot without an ancestor snapshot"
            )
            prev_snapshot = cimple.snapshot.core.load_snapshot(prev_snapshot_name)
            PkgOps.install_pkg(
                target_path, cimple.models.pkg.BinPkgId(pkg_id.name[len("prev:") :]), prev_snapshot
            )
            return

        pkg_data = cimple_snapshot.bootstrap_bin_pkg_map.get(
            pkg_id, cimple_snapshot.bin_pkg_map.get(pkg_id)
        )

        if pkg_data is None:
            raise RuntimeError(
                f"Requested package {pkg_id} not found in snapshot {cimple_snapshot.name}."
            )
        assert snapshot_models.snapshot_pkg_is_bin(pkg_data)

        if pkg_data.sha256 == "placeholder":
            raise RuntimeError(f"Package {pkg_id.name} is not ready yet and cannot be installed.")

        with tarfile.open(
            cimple.constants.cimple_pkg_dir / pkg_data.tarball_name,
            cimple.tarfile.get_tarfile_mode("r", pkg_data.compression_method),
        ) as tar:
            tar.extractall(target_path, filter=cimple.tarfile.writable_extract_filter)

    def _build_pkg(
        self,
        package_id: pkg_models.SrcPkgId,
        config: pkg_config_models.PkgConfig,
        *,
        pi_path: pathlib.Path,
        cimple_snapshot: cimple.snapshot.core.CimpleSnapshot,
        build_options: PackageBuildOptions,
        bootstrap: bool = False,
    ) -> dict[str, pathlib.Path]:
        # Prepare chroot image
        cimple.logging.info("Preparing image")

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

        deps = self.resolve_dependencies(
            pkg_models.SrcPkgId(config.name),
            config.version,
            pi_path=pi_path,
            is_bootstrap=bootstrap,
        )
        cimple.util.clear_path(deps_dir)
        for dep in deps.build_depends[package_id]:
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
        builtin_variables: dict[str, str] = {
            "cimple_output_dir": output_dir.as_posix(),
            "cimple_build_dir": build_dir.as_posix(),
            "cimple_deps_dir": deps_dir.as_posix(),
            "cimple_parallelism": str(build_options.parallel),
        }
        # TODO: remove hard-coded platform and arch
        builtin_variables.update(
            images.ops.get_image_specific_builtin_variables(
                "windows", "x86_64", config.input.image_type, builtin_variables
            )
        )

        def interpolate_variables(input_str: str):
            return cimple.str_interpolation.interpolate(input_str, builtin_variables)

        # Start execution container
        # TODO: Take container name from platform & arch
        mounts: list[cimple.process.OciMount] = []
        bin_paths: list[pathlib.Path] = []
        for index, extra_path in enumerate(build_options.extra_paths):
            host_path, bin_dir = extra_path.split(",")
            target_path = pathlib.Path("C:/cimple-extra-paths") / str(index)
            container_bin_dir = target_path / bin_dir
            mounts.append(
                cimple.process.OciMount(
                    source=pathlib.Path(host_path), target=target_path, read_only=True
                )
            )
            bin_paths.append(container_bin_dir)

        with tempfile.TemporaryDirectory() as temp_data_dir:
            temp_data_dir_path = pathlib.Path(temp_data_dir)
            rules_file_path = temp_data_dir_path / "rules.json"
            normalized_rules = cimple.models.pkg_config.normalize_rules(
                config.rules,
                default_cwd=build_dir,
                builtin_variables=builtin_variables,
                bin_paths=bin_paths,
            )
            with rules_file_path.open("w") as rules_file:
                rules_file.write(normalized_rules.model_dump_json())

            cimple.logging.debug(
                "Normalized rules file content: %s", normalized_rules.model_dump_json(indent=2)
            )

            container_id = cimple.process.start_container(
                "cimple-windows-x86_64",
                [
                    cimple.process.OciMount(
                        source=build_dir, target=pathlib.Path("C:/cimple-build")
                    ),
                    cimple.process.OciMount(
                        source=output_dir, target=pathlib.Path("C:/cimple-output")
                    ),
                    cimple.process.OciMount(source=deps_dir, target=pathlib.Path("C:/cimple-root")),
                    cimple.process.OciMount(
                        source=temp_data_dir_path,
                        target=pathlib.Path("C:/cimple-data"),
                        read_only=True,
                    ),
                    *mounts,
                ],
            )

            build_process = cimple.process.run_command_in_container(
                container_id,
                ["uv", "run", "cimple", "run-rules", "run", "C:/cimple-data/rules.json"],
            )
            if build_process.returncode != 0:
                raise RuntimeError("Failed to build package")

            cimple.process.stop_container(container_id)

        cimple.logging.info("Build result is available in %s", output_dir)
        return {
            binary_id.name: output_dir / binary_data.output_dir
            if binary_data.output_dir
            else output_dir
            for binary_id, binary_data in config.binaries.items()
        }

    def build_pkg(
        self,
        package_id: pkg_models.SrcPkgId,
        *,
        pi_path: pathlib.Path,
        cimple_snapshot: cimple.snapshot.core.CimpleSnapshot,
        build_options: PackageBuildOptions,
        bootstrap: bool = False,
    ) -> dict[str, pathlib.Path]:
        package_version = cimple_snapshot.get_src_pkg(package_id).version
        config = pkg_config_models.load_pkg_config(pi_path, package_id, package_version)

        cimple.logging.info("Building package %s-%s", package_id.name, package_version)

        # NOTE: package ID has to be provided separately because bootstrap packages have
        # different package IDs (`bootstrap:` variant + normal variant), but they share the
        # same config file
        return self._build_pkg(
            package_id,
            config,
            cimple_snapshot=cimple_snapshot,
            pi_path=pi_path,
            build_options=build_options,
            bootstrap=bootstrap,
        )

    def resolve_dependencies(
        self,
        package_id: pkg_models.SrcPkgId,
        package_version: str,
        *,
        pi_path: pathlib.Path,
        is_bootstrap: bool = False,
    ) -> cimple.pkg.core.PackageDependencies:
        config = pkg_config_models.load_pkg_config(pi_path, package_id, package_version)
        # Currently only custom packages are possibly bootstrap packages
        if is_bootstrap:
            build_depends: dict[pkg_models.SrcPkgId, list[pkg_models.BinPkgId]] = {}
            depends: dict[pkg_models.BinPkgId, list[pkg_models.BinPkgId]] = {}

            # Bootstrap packages build depends on packages in the previous snapshot
            build_depends[cimple.models.pkg.bootstrap_src_id(package_id)] = [
                cimple.models.pkg.prev_bin_id(bin_pkg) for bin_pkg in config.build_depends
            ]
            # Normal packages depend on bootstrap versions of their dependencies
            build_depends[package_id] = [
                cimple.models.pkg.bootstrap_bin_id(bin_pkg) for bin_pkg in config.build_depends
            ]

            for bin_pkg, bin_pkg_data in config.binaries.items():
                # Bootstrap packages depend on other bootstrap packages
                depends.update(
                    {
                        cimple.models.pkg.bootstrap_bin_id(bin_pkg): [
                            cimple.models.pkg.bootstrap_bin_id(dep) for dep in bin_pkg_data.depends
                        ]
                    }
                )
                # Normal packages depend on other normal packages
                depends[bin_pkg] = bin_pkg_data.depends
        else:
            depends: dict[pkg_models.BinPkgId, list[pkg_models.BinPkgId]] = {
                bin_pkg: bin_pkg_data.depends for bin_pkg, bin_pkg_data in config.binaries.items()
            }
            build_depends = {package_id: config.build_depends}

        return cimple.pkg.core.PackageDependencies(build_depends=build_depends, depends=depends)
