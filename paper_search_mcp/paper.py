# paper_search_mcp/paper.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional

# Source-specific fields worth keeping in the serialized output.
EXTRA_KEYS = ('journal', 'container_title', 'venue', 'publisher', 'isbn', 'open_access')
MAX_AUTHORS = 3
MAX_CATEGORIES = 3


def _is_doi_url(url: str, doi: str) -> bool:
    """True if the URL is just the DOI resolver link for this DOI."""
    normalized = (url or '').strip().lower().rstrip('/')
    for prefix in ('https://doi.org/', 'http://doi.org/', 'https://dx.doi.org/', 'http://dx.doi.org/'):
        if normalized.startswith(prefix):
            return normalized[len(prefix):] == doi.strip().lower().rstrip('/')
    return False


@dataclass
class Paper:
    """Standardized paper format with core fields for academic sources"""
    # 核心字段（必填，但允许空值或默认值）
    paper_id: str              # Unique identifier (e.g., arXiv ID, PMID, DOI)
    title: str                 # Paper title
    authors: List[str]         # List of author names
    abstract: str              # Abstract text
    doi: str                   # Digital Object Identifier
    published_date: Optional[datetime]   # Publication date
    pdf_url: str               # Direct PDF link
    url: str                   # URL to paper page
    source: str                # Source platform (e.g., 'arxiv', 'pubmed')

    # 可选字段
    updated_date: Optional[datetime] = None        # Last updated date
    categories: Optional[List[str]] = None         # Subject categories
    keywords: Optional[List[str]] = None           # Keywords
    citations: int = 0                             # Citation count
    references: Optional[List[str]] = None         # List of reference IDs/DOIs
    extra: Optional[Dict] = None                   # Source-specific extra metadata

    def __post_init__(self):
        """Post-initialization to handle default values"""
        if self.authors is None:
            self.authors = []
        if self.categories is None:
            self.categories = []
        if self.keywords is None:
            self.keywords = []
        if self.references is None:
            self.references = []
        if self.extra is None:
            self.extra = {}

    def _format_authors(self) -> str:
        """Join the author names, capping runaway lists.

        Hyperauthorship papers carry hundreds of names, which can cost more
        than a thousand tokens for a single result without helping anyone
        judge the paper.
        """
        authors = [author for author in (self.authors or []) if author]
        if len(authors) <= MAX_AUTHORS:
            return '; '.join(authors)
        return '; '.join(authors[:MAX_AUTHORS]) + f' u. a. (n={len(authors)})'

    def _compact_extra(self) -> Dict:
        """Keep the source-specific fields that help judge a paper."""
        extra = self.extra or {}
        compact = {}
        for key in EXTRA_KEYS:
            value = extra.get(key)
            if value not in ('', [], {}, None):
                compact[key] = value
        return compact

    def to_dict(self) -> Dict:
        """Convert paper to dictionary format for serialization.

        Every field is paid for in the model's context on every call, so
        anything that carries no information is left out: empty fields, a URL
        that only restates the DOI, a paper_id identical to the DOI, and the
        day-level precision of a publication date that is used for filtering
        by year.
        """
        doi = self.doi or ''
        data = {
            'paper_id': self.paper_id,
            'title': self.title,
            'authors': self._format_authors(),
            'abstract': self.abstract,
            'doi': doi,
            'published_date': str(self.published_date.year) if self.published_date else '',
            'pdf_url': self.pdf_url,
            'url': self.url,
            'source': self.source,
            'updated_date': str(self.updated_date.year) if self.updated_date else '',
            'categories': '; '.join((self.categories or [])[:MAX_CATEGORIES]),
            'keywords': '; '.join(self.keywords or []),
            'citations': self.citations,
            'references': '; '.join(self.references or []),
            'extra': self._compact_extra(),
        }

        if doi:
            if _is_doi_url(data['url'], doi):
                data['url'] = ''
            if (data['paper_id'] or '').strip().lower() == doi.strip().lower():
                data['paper_id'] = ''

        return {key: value for key, value in data.items() if value not in ('', [], {}, None, 0)}