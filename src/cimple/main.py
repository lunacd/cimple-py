import typer

import cimple.cmd.snapshot
import cimple.images as images

app = typer.Typer()
app.add_typer(cimple.cmd.snapshot.snapshot_app, name="snapshot")


@app.command()
def clean(target: str):
    # TODO: support all of the added directories
    if target == "all":
        images.clean_images()

    if target == "images":
        images.clean_images()
    elif target != "all":
        print(f"Unknown target: {target}. Supported targets: images.")


def main():
    app()
