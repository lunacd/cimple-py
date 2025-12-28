import typer

stream_app = typer.Typer()


@stream_app.command()
def update():
    """
    Update stream snapshot based on the latest stream config.
    """
