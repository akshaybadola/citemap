from pathlib import Path
from enum import Enum, unique


class Color(Enum):
    pass


PathLike = Path | str


def linspace(a, b, num_divs):
    delta = (b - a)/(num_divs-1)
    result = [a]
    for i in range(num_divs-1):
        result.append(result[-1] + delta)
    return result
