import typer

app = typer.Typer()


@app.command(name="build-pkg")
def build_pkg():
    print("building package")

@app.command()
def build():
    print("building")


def main():
    app()
