import functools
from typing import Tuple


@functools.lru_cache(8)
def get_file_lines(file_name: str) -> Tuple[str]:
    with open(file_name, "rb") as f:
        return tuple(line.decode("utf-8") for line in f.readlines())
