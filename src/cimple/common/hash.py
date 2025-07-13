import hashlib
import pathlib


def sha256_file(path: pathlib.Path) -> str:
    """
    Returns the hex digest of the SHA256 hash of the given file.
    """
    if not path.is_file():
        raise RuntimeError(f"{path} is not a regular file.")

    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()
