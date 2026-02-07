import typing

import typer

import cimple.constants
import cimple.logging
import cimple.models.stream
import cimple.snapshot.core
import cimple.snapshot.ops
import cimple.stream

if typing.TYPE_CHECKING:
    import pathlib

stream_app = typer.Typer()


@stream_app.command()
def update(
    stream: str,
    pkg_index: typing.Annotated[pathlib.Path, typer.Option()],
    parallel: typing.Annotated[int, typer.Option(help="Number of parallel jobs", default=1)],
):
    """
    Update stream snapshot based on the latest stream config.
    """
    # Load stream data to determine the current snapshot
    cimple.logging.info("Loading stream data")
    stream_data_path = cimple.constants.cimple_stream_dir / f"{stream}.json"
    if not stream_data_path.exists():
        raise RuntimeError(f"Stream {stream} does not exist in cimple store!")
    stream_data = cimple.models.stream.StreamData.model_validate_json(stream_data_path.read_text())

    # Load current snapshot
    cimple.logging.info("Loading current snapshot")
    snapshot = cimple.snapshot.core.load_snapshot(stream_data.latest_snapshot)

    # Load stream config
    cimple.logging.info("Loading stream config")
    stream_config = cimple.stream.load_stream_config(pkg_index, stream)

    # Resolve changes
    cimple.logging.info("Resolving snapshot changes from stream config")
    pkg_changes, bootstrap_changes = cimple.stream.resolve_snapshot_changes(
        stream_config=stream_config, current_snapshot=snapshot
    )

    # Process changes
    cimple.logging.info("Processing snapshot changes")
    cimple.snapshot.ops.process_changes(
        origin_snapshot=snapshot,
        pkg_changes=pkg_changes,
        bootstrap_changes=bootstrap_changes,
        pkg_index_path=pkg_index,
        parallel=parallel,
    )

    # Dump updated snapshot
    cimple.logging.info("Committing updated snapshot")
    snapshot.dump_snapshot()
