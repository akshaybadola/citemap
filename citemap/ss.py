from typing import Optional
import json
import glob
from pathlib import Path
from dataclasses import dataclass

from .util import PathLike


@dataclass
class Author:
    name: str
    authorId: int


@dataclass
class Paper:
    paperId: str
    title: str
    authors: list[str]
    venue: Optional[str] = None
    abstract: Optional[str] = None


def parse_data(data):
    if "details" in data:
        details = data["details"]
    elif "citingPaper" in data:
        details = data["citingPaper"]
    elif "citedPaper" in data:
        details = data["citedPaper"]
    else:
        details = data
    try:
        return Paper(paperId=details["paperId"],
                     title=details.get("title", None),
                     authors=details.get("authors", None),
                     venue=details.get("venue", None),
                     abstract=details.get("abstract", None))
    except Exception:
        return None


def format_entry(entry: Paper) -> str:
    authors = ",".join([x["name"] for x in entry.authors])
    title = entry.title
    venue = entry.venue
    text = f"Title: {title}\nAuthors: {authors}"
    if venue:
        text += f"\nVenue: {venue}"
    return text


class SS:
    def __init__(self, data_dir: PathLike):
        self._data_dir = Path(data_dir)
        self.build_cache()

    def build_cache(self):
        """Build a cache of SS data files.

        Args:
            files: List of files of JSON data


        """
        cache_file = self._data_dir.joinpath("cache")
        if cache_file.exists():
            with open(cache_file) as f:
                self._cache = json.load(f)
        else:
            print("Cache not found. Building")
            cache = {}
            entry_keys = ["paperId", "title", "authors", "venue", "abstract"]
            files = glob.glob(str(self._data_dir.joinpath("*")))
            files = [f for f in files if "metadata" not in f]
            for fname in files:
                with open(fname) as f:
                    entry = json.load(f)
                if "details" in entry:
                    entry = entry["details"]
                cache[entry["paperId"]] = {k: entry[k] for k in entry_keys}
            with open(cache_file, "w") as f:
                json.dump(cache, f)
            print(f"Saved cache file {cache_file}")
            self._cache = cache

    def get_metadata(self, paper_id: str):
        if paper_id not in self._cache:
            return None
        paper_file = self._data_dir.joinpath(paper_id)
        with open(paper_file) as f:
            data = json.load(f)
        return data
