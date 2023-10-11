import json
from pathlib import Path
from enum import Enum, unique


class Color(Enum):
    pass


Pathlike = Path | str


def linspace(a, b, num_divs):
    delta = (b - a)/(num_divs-1)
    result = [a]
    for i in range(num_divs-1):
        result.append(result[-1] + delta)
    return result


def save_file(data, filename, indent=True, sort=False, oneLine=False):
    f = open(filename, 'w')
    if indent:
        f.write(json.dumps(data, indent=4, sort_keys=sort))
    else:
        f.write(json.dumps(data, sort_keys=sort))
    f.close()


def load_file(filename):
    try:
        file = open(filename)
        t = file.read()
        file.close()
        return json.loads(t)
    except Exception as e:
        print(f"Error occured while opening file {e}")
        return {}
