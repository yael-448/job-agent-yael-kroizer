"""Hand-written harness for the raw Messages API. One file per responsibility."""
from pathlib import Path


def log(module_file: str, msg: str) -> None:
    """Every runtime action is printed with the name of the file that performed it."""
    print(f"[{Path(module_file).name}] {msg}", flush=True)
