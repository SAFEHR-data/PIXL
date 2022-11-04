from pathlib import Path


def clear_file(filepath: Path) -> None:
    open(filepath, "w").close()


def string_is_non_empty(string: str) -> bool:
    """Does a string have more than just spaces and newlines"""
    return len(string.split()) > 0
