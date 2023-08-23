import os
from pathlib import Path
import json
from pytest import fixture


@fixture(scope="session")
def config_dir():
    return Path(__file__).parent.joinpath("config")


@fixture(scope="session")
def cache():
    cache_file = os.environ.get("CITEMAP_CACHE")
    with open(cache_file) as f:
        _cache = json.load(f)
    return _cache
