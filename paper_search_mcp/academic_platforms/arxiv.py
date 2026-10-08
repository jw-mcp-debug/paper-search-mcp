# paper_search_mcp/sources/arxiv.py
from typing import List
from datetime import datetime
from threading import Lock
from xml.etree import ElementTree
import logging
import re
import requests
import feedparser
import time
from ..paper import Paper
from ..utils import extract_doi
from .base import PaperSource
from pypdf import PdfReader
import os

logger = logging.getLogger(__name__)

# Rate-limit serialization, 406 recovery and the pass-through of structured
# queries follow upstream openags/paper-search-mcp #119 (from #81 by @visez),
# #125 and #115.


class ArxivSearcher(PaperSource):
    """Searcher for arXiv papers.

    The arXiv terms of use ask for at most one request every three seconds
    from a single connection (https://info.arxiv.org/help/api/tou.html). The
    lock and the timestamp are class attributes, so every instance and every
    worker thread in the process shares them. Without the lock, two sessions
    on the HTTP server could both read an old timestamp and fire together.
    Pacing across processes is not covered.
    """
    BASE_URL = "https://export.arxiv.org/api/query"
    MIN_INTERVAL_SEC = 3.0  # arXiv terms of use
    MAX_ATTEMPTS = 3
    RETRYABLE_STATUS_CODES = frozenset((429, 500, 502, 503, 504))
    _request_lock = Lock()
    _last_request_at = 0.0  # monotonic seconds; 0.0 = no request yet

    _FIELD_PREFIX_RE = re.compile(r"(?:^|\s)(ti|au|abs|co|jr|cat|rn|id|all):", re.IGNORECASE)
    _BOOLEAN_OP_RE = re.compile(r"(?:^|\s)(AND|OR|ANDNOT)(?:\s|$)")
    _ENTRY_ID_RE = re.compile(
        r"https?://arxiv\.org/abs/(?:[0-9]{4}\.[0-9]{4,5}|"
        r"[a-z-]+(?:\.[A-Z]{2})?/[0-9]{7})(?:v[0-9]+)?"
    )

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'paper-search-mcp/1.0 (mailto:openags@example.com)',
            'Accept': 'application/atom+xml, application/xml;q=0.9, */*;q=0.8',
        })

    @classmethod
    def _pace_locked(cls):
        """Sleep just long enough to respect the rate limit; hold the lock."""
        elapsed = time.monotonic() - cls._last_request_at
        if cls._last_request_at > 0 and elapsed < cls.MIN_INTERVAL_SEC:
            time.sleep(cls.MIN_INTERVAL_SEC - elapsed)
        cls._last_request_at = time.monotonic()

    @staticmethod
    def _is_rate_limited(response) -> bool:
        """arXiv answers a soft rate limit with HTTP 200 and 'Rate exceeded.'."""
        return (response.content or b"")[:64].strip().lower().startswith(b"rate exceeded")

    @classmethod
    def _build_search_query(cls, query: str) -> str:
        """AND the words of a plain multi-word query.

        arXiv binds only the first word of `all:machine learning` to `all:`
        and ORs the rest, so the result set is larger than for either word
        pair form. Upstream quotes the words as one phrase instead; that is
        too strict for the multi-concept queries an agent writes —
        `"deskilling artificial intelligence"` finds nothing, the AND form
        28 papers. Queries that already use quotes, field prefixes or
        boolean operators are passed through unchanged.
        """
        normalized = " ".join((query or "").split())
        if (
            '"' in normalized
            or cls._FIELD_PREFIX_RE.search(normalized)
            or cls._BOOLEAN_OP_RE.search(normalized)
        ):
            return normalized
        return " AND ".join(f"all:{word}" for word in normalized.split(" "))

    @classmethod
    def _is_usable_406_feed(cls, response) -> bool:
        """Accept a 406 only if it carries a complete, nonempty arXiv feed.

        arXiv intermittently sends valid results with status 406 (upstream
        issue #121). feedparser tolerates malformed XML and HTML, so parsing
        alone proves nothing; an empty feed cannot prove a successful search.
        """
        try:
            root = ElementTree.fromstring(response.content)
            if root.tag != "{http://www.w3.org/2005/Atom}feed":
                return False
            feed = feedparser.parse(response.content)
            if feed.bozo or feed.version != "atom10" or not feed.entries:
                return False
            if not re.fullmatch(r"https?://arxiv\.org/api/\S+", feed.feed.get("id", "")):
                return False
            if int(feed.feed.get("opensearch_totalresults", "0")) < len(feed.entries):
                return False
            for entry in feed.entries:
                if not cls._ENTRY_ID_RE.fullmatch(entry.get("id", "")):
                    return False
                if not all(entry.get(field, "").strip() for field in ("title", "summary")):
                    return False
                if not entry.get("authors") or not entry.get("tags"):
                    return False
                cls._paper_from_entry(entry)
            return True
        except (ElementTree.ParseError, ValueError, TypeError, AttributeError, KeyError):
            return False

    def _request(self, params):
        """Run one paced request sequence; raise unless it yields a feed.

        Every failure raises. Returning an empty list here would read as
        "arXiv has nothing on this", which is a different statement from
        "arXiv did not answer".
        """
        response = None
        failure = None
        with self._request_lock:
            for attempt in range(self.MAX_ATTEMPTS):
                last = attempt == self.MAX_ATTEMPTS - 1
                self._pace_locked()
                try:
                    response = self.session.get(self.BASE_URL, params=params, timeout=30)
                except requests.RequestException as exc:
                    failure = f"request failed: {exc}"
                    if not last:
                        time.sleep((attempt + 1) * 1.5)
                    continue

                if response.status_code == 200:
                    if not self._is_rate_limited(response):
                        return response
                    failure = "rate limited: 'Rate exceeded.'"
                    if not last:
                        time.sleep((attempt + 1) * 5.0)  # arXiv asks for a slower cadence
                    continue

                if response.status_code == 406:
                    if self._is_usable_406_feed(response):
                        return response
                    failure = "HTTP 406 without a usable arXiv feed"
                elif response.status_code in self.RETRYABLE_STATUS_CODES:
                    failure = f"HTTP {response.status_code}"
                else:
                    raise requests.RequestException(
                        f"arXiv search failed: HTTP {response.status_code}"
                    )
                if not last:
                    time.sleep((attempt + 1) * 1.5)

        raise requests.RequestException(
            f"arXiv search failed after {self.MAX_ATTEMPTS} attempts: {failure}"
        )

    def search(self, query: str, max_results: int = 10, sort_by: str = 'relevance', sort_order: str = 'descending') -> List[Paper]:
        params = {
            'search_query': self._build_search_query(query),
            'max_results': max_results,
            'sortBy': sort_by,
            'sortOrder': sort_order,
        }
        response = self._request(params)

        feed = feedparser.parse(response.content)
        papers = []
        for entry in feed.entries:
            try:
                papers.append(self._paper_from_entry(entry))
            except Exception as e:
                logger.warning("Error parsing arXiv entry: %s", e)
        return papers

    @staticmethod
    def _paper_from_entry(entry) -> Paper:
        authors = [author.name for author in entry.authors]
        published = datetime.strptime(entry.published, '%Y-%m-%dT%H:%M:%SZ')
        updated = datetime.strptime(entry.updated, '%Y-%m-%dT%H:%M:%SZ')
        pdf_url = next((link.href for link in entry.links if link.type == 'application/pdf'), '')

        # Try to extract DOI from entry.doi or links or summary
        doi = entry.get('doi', '') or extract_doi(entry.summary) or extract_doi(entry.id)
        for link in entry.links:
            if link.get('title') == 'doi':
                doi = doi or extract_doi(link.href)

        return Paper(
            # Legacy identifiers carry the archive: hep-th/9901001, not 9901001.
            paper_id=entry.id.split('/abs/', 1)[-1],
            title=entry.title,
            authors=authors,
            abstract=entry.summary,
            url=entry.id,
            pdf_url=pdf_url,
            published_date=published,
            updated_date=updated,
            source='arxiv',
            categories=[tag.term for tag in entry.tags],
            keywords=[],
            doi=doi
        )

    def download_pdf(self, paper_id: str, save_path: str) -> str:
        pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
        response = requests.get(pdf_url)
        os.makedirs(save_path, exist_ok=True)
        output_file = f"{save_path}/{paper_id}.pdf"
        with open(output_file, 'wb') as f:
            f.write(response.content)
        return output_file

    def read_paper(self, paper_id: str, save_path: str = "./downloads") -> str:
        """Read a paper and convert it to text format.
        
        Args:
            paper_id: arXiv paper ID
            save_path: Directory where the PDF is/will be saved
            
        Returns:
            str: The extracted text content of the paper
        """
        # First ensure we have the PDF
        pdf_path = f"{save_path}/{paper_id}.pdf"
        if not os.path.exists(pdf_path):
            pdf_path = self.download_pdf(paper_id, save_path)
        
        # Read the PDF
        try:
            reader = PdfReader(pdf_path)
            text = ""
            
            # Extract text from each page
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            print(f"Error reading PDF for paper {paper_id}: {e}")
            return ""

if __name__ == "__main__":
    # 测试 ArxivSearcher 的功能
    searcher = ArxivSearcher()
    
    # 测试搜索功能
    print("Testing search functionality...")
    query = "machine learning"
    max_results = 5
    try:
        papers = searcher.search(query, max_results=max_results)
        print(f"Found {len(papers)} papers for query '{query}':")
        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper.title} (ID: {paper.paper_id})")
    except Exception as e:
        print(f"Error during search: {e}")
    
    # 测试 PDF 下载功能
    if papers:
        print("\nTesting PDF download functionality...")
        paper_id = papers[0].paper_id
        save_path = "./downloads"  # 确保此目录存在
        try:
            os.makedirs(save_path, exist_ok=True)
            pdf_path = searcher.download_pdf(paper_id, save_path)
            print(f"PDF downloaded successfully: {pdf_path}")
        except Exception as e:
            print(f"Error during PDF download: {e}")

    # 测试论文阅读功能
    if papers:
        print("\nTesting paper reading functionality...")
        paper_id = papers[0].paper_id
        try:
            text_content = searcher.read_paper(paper_id)
            print(f"\nFirst 500 characters of the paper content:")
            print(text_content[:500] + "...")
            print(f"\nTotal length of extracted text: {len(text_content)} characters")
        except Exception as e:
            print(f"Error during paper reading: {e}")