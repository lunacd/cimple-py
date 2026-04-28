# Container Filesystem Layout

## Windows

- `C:\cimple`: The cimple source code. This will change once cimple is re-implemented in C++.
- `C:\cimple-root`: The cimple sysroot. This is where all build dependencies are installed.
- `C:\cimple-build`: The package build directory. This usually maps to the `pkg_build` directory in local cimple store.
- `C:\cimple-output`: The package build output directory. This usually maps to the `pkg_output` directory in local
  cimple store.
- `C:\cimple-data`: The primary mechanism for sharing data between the host and the container.
    - `C:\cimple-data\rules.json`: The rules used to build the package, with the following schema:

      ```json
      [
        {
          "env": {
            "env_name":  "env_value"
          },
          "rule": ["build_command", "arg1", "arg2"],
          "cwd": "working_directory (nullable)"
        }
      ]
      ```

- `C:\cimple-extra-paths\[name]`: Used to mount pre-existing dependencies on the host system into the container. This is
  ONLY used to bootstrap package index for a platform where it's necessary to rely on pre-existing dependencies on the
  host.