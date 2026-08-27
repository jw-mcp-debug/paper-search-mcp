# paper_search_mcp/academic_platforms/dblp.py
from typing import List, Optional, Dict, Any
from datetime import datetime
import requests
import logging
import xml.etree.ElementTree as ET
import time
from bs4 import BeautifulSoup

from ..paper import Paper
from ..utils import extract_doi
from .base import PaperSource

logger = logging.getLogger(__name__)


class DBLPUnavailable(RuntimeError):
    """Raised when the dblp API could not be queried at all.

    Distinguishes an unreachable or rate-limited source from a query that
    legitimately returned no results. `search_papers` reports raised
    exceptions in its `errors` mapping, so this reaches the client instead
    of being flattened into a zero-hit result.
    """


class DBLPSearcher(PaperSource):
    """Searcher for dblp computer science bibliography.

    dblp throttles per client IP: it answers with 429 and a Retry-After
    header, then with 503, and finally drops connections outright. Requests
    are paced to stay below that threshold.
    """

    BASE_URL = "https://dblp.org/search/publ/api"
    HTML_SEARCH_URL = "https://dblp.org/search/publ"

    # dblp API returns XML by default
    DEFAULT_FORMAT = "xml"

    MIN_INTERVAL_SEC = 1.5   # pacing between two dblp requests
    MAX_RETRY_AFTER_SEC = 10  # longer waits are reported as unavailable instead

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'paper-search-mcp/1.0 (https://github.com/openags/paper-search-mcp)',
            'Accept': 'application/xml, application/json'
        })
        self._last_call_at = 0.0  # monotonic seconds; 0.0 = no call yet

    def _pace(self):
        """Sleep just long enough to keep below the dblp rate limit."""
        elapsed = time.monotonic() - self._last_call_at
        if self._last_call_at > 0 and elapsed < self.MIN_INTERVAL_SEC:
            time.sleep(self.MIN_INTERVAL_SEC - elapsed)
        self._last_call_at = time.monotonic()

    @classmethod
    def _retry_delay(cls, response, attempt: int) -> Optional[float]:
        """Delay before the next attempt, or None if waiting is pointless."""
        retry_after = response.headers.get('Retry-After', '').strip()
        if retry_after.isdigit():
            delay = float(retry_after)
            return delay if delay <= cls.MAX_RETRY_AFTER_SEC else None
        return (attempt + 1) * 2.0

    def search(self, query: str, max_results: int = 10, **kwargs) -> List[Paper]:
        """
        Search dblp for computer science publications.

        Args:
            query: Search query string
            max_results: Maximum results to return (default: 10)
            **kwargs: Additional parameters:
                - year: Filter by publication year
                - venue: Filter by conference/journal venue
                - author: Filter by author name

        Returns:
            List of Paper objects
        """
        papers = []

        try:
            # Prepare parameters for dblp API
            params = {
                'q': query,
                'format': self.DEFAULT_FORMAT,
                'h': min(max_results, 1000)  # dblp supports up to 1000 results
            }

            # Add optional filters
            if 'year' in kwargs:
                year = kwargs['year']
                if isinstance(year, str) and '-' in year:
                    # Handle year range like "2020-2023"
                    year_range = year.split('-')
                    if len(year_range) == 2:
                        params['q'] = f"{query} year:{year_range[0]}:{year_range[1]}"
                else:
                    params['q'] = f"{query} year:{year}"

            if 'venue' in kwargs:
                params['q'] = f"{query} venue:{kwargs['venue']}"

            if 'author' in kwargs:
                params['q'] = f"{query} author:{kwargs['author']}"

            logger.debug(f"Searching dblp with query: {params['q']}")

            response = None
            for attempt in range(3):
                self._pace()
                try:
                    response = self.session.get(self.BASE_URL, params=params, timeout=30)
                except requests.RequestException as exc:
                    # dblp drops connections once a client is blocked
                    if attempt == 2:
                        raise DBLPUnavailable(f"dblp API request failed: {exc}") from exc
                    time.sleep((attempt + 1) * 2.0)
                    continue

                if response.status_code == 200:
                    break

                # 429 is dblp's rate limit and was previously not retried at all
                if response.status_code == 429 or response.status_code >= 500:
                    delay = self._retry_delay(response, attempt)
                    if delay is not None and attempt < 2:
                        logger.warning(
                            "dblp returned %s, retrying in %.1fs", response.status_code, delay
                        )
                        time.sleep(delay)
                        continue

                raise DBLPUnavailable(
                    f"dblp API returned HTTP {response.status_code}"
                )

            if response is None or response.status_code != 200:
                status = response.status_code if response is not None else "no response"
                raise DBLPUnavailable(f"dblp API unavailable (HTTP {status})")

            # A throttling or error page can be well-formed XML, so the parser
            # alone cannot tell it apart from an empty result set.
            content_type = response.headers.get('Content-Type', '')
            if content_type and 'xml' not in content_type and 'json' not in content_type:
                raise DBLPUnavailable(
                    f"dblp answered with Content-Type {content_type!r} instead of XML"
                )

            # Parse XML response
            try:
                root = ET.fromstring(response.content)
            except ET.ParseError as exc:
                # A 200 that is not XML means dblp answered with something else
                # (error page, throttling notice) — not an empty result set.
                raise DBLPUnavailable(f"dblp returned an unparseable response: {exc}") from exc

            # dblp XML structure: result > hits > hit > info
            hits = root.findall('.//hit')

            for hit in hits:
                try:
                    paper = self._parse_dblp_hit(hit)
                    if paper:
                        papers.append(paper)
                        if len(papers) >= max_results:
                            break
                except Exception as e:
                    logger.warning(f"Error parsing dblp hit: {e}")
                    continue

            logger.info(f"Found {len(papers)} papers from dblp for query: {query}")

            if papers:
                return papers

            # The API answered, it just had nothing parseable. Only here is an
            # empty result the truth, so the HTML fallback may fill in silently.
            logger.warning("dblp API returned no parseable results, attempting HTML fallback")
            return self._search_html_fallback(query=query, max_results=max_results)

        except DBLPUnavailable:
            raise
        except requests.RequestException as e:
            raise DBLPUnavailable(f"dblp API request error: {e}") from e
        except Exception as e:
            raise DBLPUnavailable(f"unexpected error in dblp search: {e}") from e

    def _search_html_fallback(self, query: str, max_results: int) -> List[Paper]:
        """Fallback search via dblp HTML endpoint when API is unavailable."""
        papers: List[Paper] = []
        try:
            self._pace()
            response = self.session.get(
                self.HTML_SEARCH_URL,
                params={'q': query},
                timeout=30,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            entries = soup.select('.publ-list .entry')
            for entry in entries:
                try:
                    title_elem = entry.select_one('.title')
                    if not title_elem:
                        continue
                    title = title_elem.get_text(' ', strip=True)
                    if not title:
                        continue

                    doi = ''
                    paper_url = ''
                    details_link = entry.select_one('li.details a[href]')
                    ee_link = entry.select_one('li.ee a[href]')
                    if details_link and details_link.get('href'):
                        paper_url = details_link['href']
                    if ee_link and ee_link.get('href'):
                        ee_href = ee_link['href']
                        extracted = extract_doi(ee_href)
                        if extracted:
                            doi = extracted
                        if not paper_url:
                            paper_url = ee_href

                    year_str = ''
                    year_elem = entry.select_one('.year')
                    if year_elem:
                        year_str = year_elem.get_text(strip=True)
                    published_date = None
                    if year_str.isdigit():
                        published_date = datetime(int(year_str), 1, 1)

                    authors: List[str] = []
                    for node in entry.select('[itemprop="author"] [itemprop="name"], [itemprop="author"]'):
                        text = node.get_text(' ', strip=True)
                        if text and text not in authors and len(text) < 120:
                            authors.append(text)

                    entry_id = entry.get('id') or f"dblp_{hash(title) & 0xffffffff:08x}"

                    papers.append(Paper(
                        paper_id=entry_id,
                        title=title,
                        authors=authors,
                        abstract='',
                        doi=doi,
                        published_date=published_date,
                        pdf_url='',
                        url=paper_url or f"https://dblp.org/search/publ?q={query}",
                        source='dblp',
                        extra={
                            'venue': '',
                            'year': year_str,
                            'pages': '',
                            'volume': '',
                            'type': '',
                            'key': entry_id,
                            'fallback': 'html',
                        }
                    ))
                    if len(papers) >= max_results:
                        break
                except Exception as exc:
                    logger.warning("Error parsing dblp HTML entry: %s", exc)
                    continue
        except Exception as exc:
            logger.error("dblp HTML fallback failed: %s", exc)

        return papers

    def _parse_dblp_hit(self, hit: ET.Element) -> Optional[Paper]:
        """Parse a dblp hit element into a Paper object."""
        try:
            # Extract basic information from info element
            info = hit.find('info')
            if info is None:
                return None

            # Extract title
            title_elem = info.find('title')
            if title_elem is None:
                return None

            title = title_elem.text.strip() if title_elem.text else ""
            if not title:
                return None

            # Extract authors
            authors = []
            author_elems = info.findall('authors/author')
            for author_elem in author_elems:
                author_name = author_elem.text.strip() if author_elem.text else ""
                if author_name:
                    authors.append(author_name)

            # Extract venue (conference/journal)
            venue_elem = info.find('venue')
            venue = venue_elem.text.strip() if venue_elem is not None and venue_elem.text else ""

            # Extract year
            year_elem = info.find('year')
            year_str = year_elem.text.strip() if year_elem is not None and year_elem.text else ""

            # Extract pages
            pages_elem = info.find('pages')
            pages = pages_elem.text.strip() if pages_elem is not None and pages_elem.text else ""

            # Extract volume
            volume_elem = info.find('volume')
            volume = volume_elem.text.strip() if volume_elem is not None and volume_elem.text else ""

            # Extract URL (dblp key)
            url_elem = info.find('url')
            dblp_url = url_elem.text.strip() if url_elem is not None and url_elem.text else ""

            # Extract DOI from ee elements (electronic edition)
            doi = ""
            ee_elems = info.findall('ee')
            for ee_elem in ee_elems:
                ee_text = ee_elem.text.strip() if ee_elem.text else ""
                if 'doi.org' in ee_text:
                    doi = ee_text.split('doi.org/')[-1]
                    break
                elif ee_text.startswith('10.'):
                    doi = ee_text
                    break

            # If no DOI found in ee, try to extract from other fields
            if not doi:
                # Check if there's a DOI field directly
                doi_elem = info.find('doi')
                if doi_elem is not None and doi_elem.text:
                    doi = doi_elem.text.strip()

            # Construct publication date from year
            published_date = None
            if year_str and year_str.isdigit():
                try:
                    published_date = datetime(int(year_str), 1, 1)
                except ValueError:
                    pass

            # Construct paper ID (use dblp key if available, otherwise generate)
            paper_id = ""
            if dblp_url:
                # Extract dblp key from URL: e.g., "rec/conf/sigmod/2023" from URL
                paper_id = dblp_url.split('/')[-1] if '/' in dblp_url else dblp_url

            if not paper_id:
                # Generate ID from title and authors
                paper_id = f"dblp_{hash(title) & 0xffffffff:08x}"

            # Construct PDF URL - dblp doesn't provide direct PDF links
            # but we can try to find PDF through other sources
            pdf_url = ""

            # Construct abstract (dblp doesn't provide abstracts)
            abstract = ""

            # Create Paper object
            return Paper(
                paper_id=paper_id,
                title=title,
                authors=authors,
                abstract=abstract,
                doi=doi,
                published_date=published_date,
                pdf_url=pdf_url,
                url=dblp_url if dblp_url else f"https://dblp.org/{paper_id}",
                source='dblp',
                extra={
                    'venue': venue,
                    'year': year_str,
                    'pages': pages,
                    'volume': volume,
                    'type': info.get('type', 'article'),
                    'key': info.get('key', ''),
                }
            )

        except Exception as e:
            logger.warning(f"Error parsing dblp hit data: {e}")
            return None

    def download_pdf(self, paper_id: str, save_path: str) -> str:
        """
        Download PDF for a dblp paper.

        Note: dblp doesn't provide direct PDF access.
        This method tries to find PDF through DOI or other sources.

        Args:
            paper_id: dblp paper identifier
            save_path: Directory to save the PDF

        Returns:
            Path to the saved PDF file

        Raises:
            NotImplementedError: dblp doesn't support direct PDF downloads
        """
        raise NotImplementedError(
            "dblp doesn't provide direct PDF access. "
            "Use DOI to download from other sources (Crossref, publisher sites, etc.)."
        )

    def read_paper(self, paper_id: str, save_path: str = "./downloads") -> str:
        """
        Download and extract text from a dblp paper.

        Args:
            paper_id: dblp paper identifier
            save_path: Directory where PDF is/will be saved

        Returns:
            Extracted text content of the paper

        Raises:
            NotImplementedError: dblp doesn't support direct paper reading
        """
        raise NotImplementedError(
            "dblp doesn't provide direct paper content access. "
            "Use DOI to access content from other sources."
        )


# For testing
if __name__ == "__main__":
    import sys

    searcher = DBLPSearcher()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "machine learning"

    print(f"Searching dblp for: {query}")
    papers = searcher.search(query, max_results=5)

    print(f"Found {len(papers)} papers:")
    for i, paper in enumerate(papers):
        print(f"\n{i+1}. {paper.title}")
        print(f"   Authors: {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}")
        print(f"   DOI: {paper.doi}")
        print(f"   Year: {paper.extra.get('year', 'N/A')}")
        print(f"   Venue: {paper.extra.get('venue', 'N/A')}")
        print(f"   URL: {paper.url}")