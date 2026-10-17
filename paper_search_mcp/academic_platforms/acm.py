"""ACM Digital Library connector — keyless, served from OpenAlex.

Since 1 January 2026 the ACM Digital Library is entirely open access, and ACM
offers no public search API, so the API key this connector used to wait for
does not exist. (The skeleton it replaces raised NotImplementedError even with
a key.) Search runs over OpenAlex restricted to ACM's DOI prefix (``10.1145``),
which covers every ACM-published work.

Upstream (#123/#128) took the same prefix route over Crossref. Measured
2026-10-17 on four computer-science queries, top 8 each: Crossref carried an
abstract for 2 of 32 hits, OpenAlex for 30 of 32. ACM deposits abstracts with
Crossref for journal articles but hardly ever for proceedings, and proceedings
(CHI, SIGCSE, RecSys …) are most of what ACM publishes. Restricting Crossref to
journal articles brings the abstracts back and loses exactly those papers.

No downloads: retrieval left this server in 0.7.0, and dl.acm.org answers
scripted PDF requests with a Cloudflare challenge anyway.
"""

from __future__ import annotations

from typing import List

from .openalex import OpenAlexSearcher
from ..paper import Paper

ACM_DOI_PREFIX = "10.1145"


class ACMSearcher(OpenAlexSearcher):
    """ACM Digital Library search via OpenAlex's DOI-prefix filter."""

    PAGE_URL_TEMPLATE = "https://dl.acm.org/doi/{doi}"

    def search(self, query: str, max_results: int = 10, filter: str = "") -> List[Paper]:
        prefix = f"doi_starts_with:{ACM_DOI_PREFIX}"
        filter = (filter or "").strip()
        papers = super().search(
            query, max_results=max_results,
            filter=f"{prefix},{filter}" if filter else prefix,
        )
        for paper in papers:
            paper.source = "acm"
            if paper.doi:
                paper.url = self.PAGE_URL_TEMPLATE.format(doi=paper.doi)
        return papers
