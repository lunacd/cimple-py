---
sidebar_position: 1
---

# Package Index Builtin Variables

## `cimple_output_dir`

Points to a directory where the build process should output its built artifacts.
At the end of a build, all files within this directory will be considered part of the package.

All content produced into this directory must be reproducible.

## `cimple_image_dir`

Points to the root of the unpacked build environment image.
This directory contains the compiler toolchain and select low-level tools and libraries.

## `cimple_build_dir`

Points to the package build tree.
At the start of a build, this directory contains the unpacked and patched original source of the package.