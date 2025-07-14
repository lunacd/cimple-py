# S3 Data Layout

Cimple keeps its package index stored in a S3 bucket.
The content, when needed and downloaded, will be saved in an identical layout locally to `~/.cimple/share`.
Therefore, the downloaded content within `~/.cimple/share` can be deleted without risk of losing data.

## `/pkg/`

This stores the built binary packages in cimple package index.
The binary tarballs are named as `<package name>-<version>-<revision>-<sha256>.tar.xz`.

## `/snapshot/`

This stores JSON files describing snapshots of the package index.
Those JSON files describes the binary packages available in that snapshot and the dependency relationships between them.

## `/image/`

This stores the build environment images with compiler toolchain and select low-level libraries.

## `/orig/`

This is only relevant if you are building Cimple PI packages.

This stores the original source tarballs used to build binary packages.
