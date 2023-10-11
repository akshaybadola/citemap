import os
import pytest
from pathlib import Path
import json

from s2cache.semantic_scholar import SemanticScholar
from citemap.ss import PaperFields
from common_pyutil.log import get_stream_logger


@pytest.fixture(scope="session")
def config_dir():
    return Path(__file__).parent.joinpath("config")


@pytest.fixture(scope="session")
def cache():
    cache_file = os.environ.get("CITEMAP_CACHE")
    with open(cache_file) as f:
        _cache = json.load(f)
    return _cache


@pytest.fixture(scope="session")
def s2client():
    config_file = os.environ.get("TEST_S2_CONFIG_FILE")
    logger = get_stream_logger("test-citemap", "debug", "debug")
    client = SemanticScholar(config_file=config_file, logger_name="test-citemap")
    return client


@pytest.fixture
def default_fields():
    return PaperFields()
