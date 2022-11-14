import os


def env_var(key: str) -> str:
    """Get an environment variable and raise a helpful exception if it's not set"""

    if (value := os.environ.get(key, None)) is None:
        raise RuntimeError(
            f"Failed to find ${key}. Ensure it is set as " f"an environment variable"
        )
    return value
