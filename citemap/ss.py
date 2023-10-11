from typing import Optional
import json
import glob
from pathlib import Path
import dataclasses
from dataclasses import dataclass

from .util import Pathlike
from s2cache.semantic_scholar import SemanticScholar
from s2cache.models import PaperData, PaperDetails, Error
from s2cache.util import dump_json

from common_pyutil.monitor import Timer
_timer = Timer()


@dataclass
class Author:
    name: str
    authorId: int


@dataclass
class PaperEntry:
    paperId: str
    title: str
    authors: list[str]
    year: str
    venue: Optional[str] = None
    abstract: Optional[str] = None
    citationCount: Optional[int] = None
    influentialCitationCount: Optional[int] = None


@dataclass
class PaperFields:
    paperId: bool = False
    title: bool = True
    authors: bool = True
    venue: bool = True
    year: bool = True
    abstract: bool = False
    citationCount: bool = False
    influentialCitationCount: bool = False

    def __iter__(self):
        return iter(self.__dict__.keys())

    def __getitem__(self, k):
        return getattr(self, k)


@dataclass
class CachePaperData:
    paperId: str
    title: str
    authors: list[str]
    venue: str
    year: str
    abstract: str
    citationCount: int
    influentialCitationCount: int
    references: list[str]
    citations: list[str]

    def __post_init__(self):
        self.citationCount = int(self.citationCount)
        self.influentialCitationCount = int(self.influentialCitationCount)


def serialize_dataclass(obj):
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    else:
        return obj


class S2:
    def __init__(self, s2client: SemanticScholar, data_dir: Pathlike,
                 paper_format_fields: PaperFields, fill_width: Optional[int] = 40):
        self._client = s2client
        self._data_dir = Path(data_dir)
        if not self._data_dir.exists():
            self._data_dir.mkdir()
        self._fill_width = fill_width
        self._paper_fields = paper_format_fields
        self._cache: dict[str, Optional[CachePaperData]] = {}
        self._cache_keys = [x.name for x in dataclasses.fields(CachePaperData)]

    def to_cached_data(self, data: PaperData) -> CachePaperData:
        references = self.get_references_from_paper_data(data)
        citations = self.get_citations_from_paper_data(data)
        details = CachePaperData(**{k: v for k, v in dataclasses.asdict(data.details).items()
                                    if k in self._cache_keys})
        details.references = references
        details.citations = citations
        return details

    def get_paper_family(self, paper_id: str) -> Optional[CachePaperData]:
        if paper_id not in self._cache:
            with _timer:
                data = self._client.paper_data(paper_id)
                if not isinstance(data, Error):
                    self._cache[paper_id] = self.to_cached_data(data)
                else:
                    self._cache[paper_id] = None
            print(f"Fetched paper with {paper_id} in {_timer.time} seconds")
        return self._cache[paper_id]

    def get_paper_data(self, paper_id: str) -> Optional[CachePaperData]:
        if paper_id not in self._cache:
            try:
                with _timer:
                    maybe_data = self._client.paper_data(paper_id)
                    data = PaperData(**dataclasses.asdict(maybe_data))
                print(f"Fetched paper with {paper_id} in {_timer.time} seconds")
                self._cache[paper_id] = self.to_cached_data(data)
                return self._cache[paper_id]
            except Exception:
                if isinstance(maybe_data, Error):
                    print(f"Got error for {paper_id}\n{maybe_data}")
                self._cache[paper_id] = None
        return self._cache[paper_id]

    def parse_data(self, data):
        entry = {}
        try:
            for k, v in dataclasses.asdict(self._paper_fields).items():
                if v:
                    entry[k] = getattr(data, k)
            return PaperEntry(**entry)
        except Exception as err:
            print(f"Error {err} while parsing data")
            return None

    def fill(self, str_list: list[str], join_str: str,
             width: Optional[int] = 40):
        """Fill a list of strings as a paragraph of maximum width

        Args:
            str_list: List of strings
            join_str: The stringt join them with
            width: Fill width

        :code:`join_str` is used to join the words. The strings in the list
        themselves are joined with newline,


        """
        result = []
        temp = ""
        width = self._fill_width or width
        for x in str_list:
            temp += f"{x}{join_str} "
            if len(temp) > 40:
                result.append(temp)
                temp = ""
        if temp:
            result.append(temp)
        if len(result) == 1:
            return result[0]
        return "\n  ".join(result)

    def format_entry(self, entry: PaperEntry, fields: Optional[list[str]] = None) -> str:
        """Format a :class:`PaperEntry` entry as text block

        Args:
            entry: The paper to format


        """
        fields = fields or self._paper_fields  # type: ignore
        text = []
        for k, v in dataclasses.asdict(entry).items():
            if v and k in fields and fields[k]:  # type: ignore
                if k == "authors":
                    filled = self.fill([x["name"] for x in v], ",")
                else:
                    filled = self.fill(str(v).split(" "), "")
                text.append(f"{k.capitalize()}: {filled}")
        return "\n".join(text)

    def get_citations_from_paper_data(self, paper_data: PaperData):
        return [paper['citingPaper']['paperId']
                for paper in paper_data.citations.data]

    def get_references_from_paper_data(self, paper_data: PaperData):
        return [paper['citedPaper']['paperId']
                for paper in paper_data.references.data]

    def load_or_build_citation_cache(self, force: bool = False):
        """Build a cache of citation data.

        The data is fetched from :class:`SemanticScholar` and only
        the :code:`paperId`s of references and citations are stored
        in this cache.

        Args:
            force: Update or force rebuild the cache


        """
        cache_file = self._data_dir.joinpath("cache")
        if cache_file.exists():
            with open(cache_file) as f:
                cache = json.load(f)
            for k, v in cache.items():
                self._cache[k] = CachePaperData(**v)
        else:
            print("Cache not found. Building")
            paper_ids = self._client.all_papers
            for i, paper_id in enumerate(paper_ids):
                try:
                    maybe_data = self._client.paper_data(paper_id)
                    data = PaperData(**dataclasses.asdict(maybe_data))
                except Exception:
                    if isinstance(maybe_data, Error):
                        print(f"Got error for {paper_id}\n{maybe_data}")
                        continue
                self._cache[paper_id] = self.to_cached_data(data)
                print(f"{i} out of {len(paper_ids)} done")
        with open(self._data_dir.joinpath("cache"), "w") as f:
            dump_json(self._cache, f)

    # def get_metadata(self, paper_id: str):
    #     if paper_id not in self._cache:
    #         return None
    #     paper_file = self._data_dir.joinpath(paper_id)
    #     with open(paper_file) as f:
    #         data = json.load(f)
    #     return data
