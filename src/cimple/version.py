def semantic_version_compare(v1: str, v2: str) -> int:
    """
    Compare two semantic version strings.
    Returns:
        -1 if v1 < v2
         0 if v1 == v2
         1 if v1 > v2
    """

    v1_parts = list(map(int, v1.split(".")))
    v2_parts = list(map(int, v2.split(".")))

    for part1, part2 in zip(v1_parts, v2_parts):
        if part1 < part2:
            return -1
        if part1 > part2:
            return 1

    if len(v1_parts) < len(v2_parts):
        return -1
    if len(v1_parts) > len(v2_parts):
        return 1

    return 0


def version_compare(v1: str, v2: str) -> int:
    """
    Compare two version strings.
    Returns:
        -1 if v1 < v2
         0 if v1 == v2
         1 if v1 > v2
    """

    [v1_semantic, v1_revision] = v1.split("-")
    [v2_semantic, v2_revision] = v2.split("-")

    semantic_result = semantic_version_compare(v1_semantic, v2_semantic)
    if semantic_result != 0:
        return semantic_result

    # If semantic versions are equal, compare revisions
    return int(v1_revision) - int(v2_revision)
