import typer
import typing

import cimple.pkg as pkg
import cimple.common.image as image

app = typer.Typer()


@app.command(name="build-pkg")
def build_pkg():
    pkg.build_pkg()


@app.command()
def build():
    print("building")


@app.command()
def clean(target: str):
    if target == "all":
        image.clean_images()

    if target == "images":
        image.clean_images()
    elif target != "all":
        print(f"Unknown target: {target}. Supported targets: images.")


def main():
    app()
