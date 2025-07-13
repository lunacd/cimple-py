import pathlib
import typing

import typer

import cimple.common as common
import cimple.images as images
import cimple.pkg as pkg
import cimple.snapshot as snapshot

app = typer.Typer()


@app.command(name="build-pkg")
def build_pkg(pkg_path: pathlib.Path):
    pkg.build_pkg(pkg_path)


@app.command()
def build():
    print("building")


@app.command()
def clean(target: str):
    if target == "all":
        common.image.clean_images()

    if target == "images":
        common.image.clean_images()
    elif target != "all":
        print(f"Unknown target: {target}. Supported targets: images.")


@app.command()
def build_image(
    name: str,
    target_path: typing.Annotated[str, typer.Option()],
    msys_path: typing.Annotated[str | None, typer.Option()] = None,
):
    if name == "windows-bootstrap_msys-x86_64":
        assert msys_path is not None, "msys_path must be provided for windows-bootstrap-msys-x86_64"
        images.windows_bootstrap_msys_x86_64.make_image(
            pathlib.Path(msys_path), pathlib.Path(target_path)
        )


@app.command(name="snapshot")
def snapshot_cmd(
    from_snapshot: typing.Annotated[str, typer.Option("--from")],
    add: typing.Annotated[list[str], typer.Option()],
    pkg_index: typing.Annotated[str, typer.Option()],
):
    def parse_pkg_id(pkg_str: str) -> pkg.PkgId:
        segments = pkg_str.split("=")
        if len(segments) != 2:
            raise RuntimeError(
                f"{pkg_str} is not a valid package ID. Pass in <pkg name>=<pkg version>"
            )

        return pkg.PkgId(name=segments[0], version=segments[1])

    add_pkgs = [parse_pkg_id(pkg_str) for pkg_str in add] if len(add) > 0 else []

    # TODO: handle removal

    snapshot.ops.add(
        from_snapshot=from_snapshot, packages=add_pkgs, pkg_index_path=pathlib.Path(pkg_index)
    )


def main():
    app()
