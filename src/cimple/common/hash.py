import hashlib
import typing

if typing.TYPE_CHECKING:
    import pathlib


def hash_file(path: pathlib.Path, sha_type: typing.Literal["sha256", "sha512"]) -> str:
    """
    Returns the hex digest of the SHA256 hash of the given file.
    """
    if not path.is_file():
        raise RuntimeError(f"{path} is not a regular file.")

    with path.open("rb") as f:
        return hashlib.file_digest(f, sha_type).hexdigest()


def hash_bytes(b: bytes, sha_type: typing.Literal["sha256", "sha512"]) -> str:
    """
    Returns the hex digest of the SHA256 hash of the given string.
    """
    return hashlib.new(sha_type, b).hexdigest()
