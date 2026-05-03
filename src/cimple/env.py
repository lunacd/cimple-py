import os


def merge_env(base: dict[str, str] | os._Environ, override: dict[str, str]) -> dict[str, str]:
    """
    Merge two environment variable dictionaries, with `override` taking precedence.
    """
    merged = base.copy()

    for key, value in override.items():
        if key == "PATH" and key in merged:
            merged["PATH"] = os.pathsep.join([value, base["PATH"]])
        else:
            merged[key] = value

    return merged
