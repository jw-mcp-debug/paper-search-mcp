from typing import List
import requests
import os
from datetime import datetime, timedelta
from ..paper import Paper
from .base import PaperSource
from pypdf import PdfReader

class BioRxivSearcher(PaperSource):
    """Searcher for bioRxiv papers"""
    BASE_URL = "https://api.biorxiv.org/details/biorxiv"

    def __init__(self):
        self.session = requests.Session()
        self.session.proxies = {'http': None, 'https': None}
        self.timeout = 30
        self.max_retries = 3

    # Die API kennt keine Stichwortsuche. Sie filtert über exakte
    # Kategorienamen und ignoriert alles andere stillschweigend: für
    # "machine learning" kamen dieselben Sätze zurück wie für "blubb xyz" —
    # schlicht die zuletzt eingestellten Preprints, ausgewiesen als Treffer
    # zur Anfrage. Deshalb wird hier zusätzlich clientseitig gefiltert, und
    # ein Begriff, der keine Kategorie ist, wird als solcher gemeldet, statt
    # Zufallstreffer auszuliefern.
    MAX_SEITEN = 10

    def search(self, query: str, max_results: int = 10, days: int = 30) -> List[Paper]:
        """
        List bioRxiv papers of a category posted within the last N days.

        This is a category listing, not a keyword search: bioRxiv offers no
        full-text search API. A query that names no category raises ValueError
        naming the categories actually seen — for a keyword search over
        bioRxiv preprints use Europe PMC, which indexes them.

        Args:
            query: Category name (e.g., "cell biology"); spaces and case are
                normalised.
            max_results: Maximum number of papers to return.
            days: Number of days to look back for papers.

        Returns:
            List of Paper objects of that category within the date range.

        Raises:
            ValueError: The query names no bioRxiv category.
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        category = query.strip().lower().replace(' ', '_')

        papers = []
        gesehene_kategorien = set()
        cursor = 0

        for _ in range(self.MAX_SEITEN):
            url = f"{self.BASE_URL}/{start_date}/{end_date}/{cursor}"
            if category:
                url += f"?category={category}"

            collection = self._hole_seite(url)
            if collection is None:
                break

            for item in collection:
                item_kategorie = (item.get('category') or '').lower().replace(' ', '_')
                gesehene_kategorien.add(item_kategorie)
                # Der Serverfilter wird nicht auf Treu und Glauben geglaubt:
                # kommt eine fremde Kategorie zurück, hat er nicht gegriffen.
                if category and item_kategorie != category:
                    continue
                try:
                    date = datetime.strptime(item['date'], '%Y-%m-%d')
                    papers.append(Paper(
                        paper_id=item['doi'],
                        title=item['title'],
                        authors=item['authors'].split('; '),
                        abstract=item['abstract'],
                        url=f"https://www.biorxiv.org/content/{item['doi']}v{item.get('version', '1')}",
                        pdf_url=f"https://www.biorxiv.org/content/{item['doi']}v{item.get('version', '1')}.full.pdf",
                        published_date=date,
                        updated_date=date,
                        source="biorxiv",
                        categories=[item['category']],
                        keywords=[],
                        doi=item['doi']
                    ))
                except Exception as e:
                    print(f"Error parsing bioRxiv entry: {e}")

            if category and not papers and gesehene_kategorien:
                bekannt = ", ".join(sorted(k for k in gesehene_kategorien if k))
                raise ValueError(
                    f"'{query}' ist keine bioRxiv-Kategorie. bioRxiv bietet keine "
                    f"Stichwortsuche, nur Kategorielisten; in den letzten {days} "
                    f"Tagen kamen diese Kategorien vor: {bekannt}. Für eine "
                    f"Stichwortsuche über bioRxiv-Preprints europepmc verwenden, "
                    f"das sie indexiert."
                )

            if len(collection) < 100 or len(papers) >= max_results:
                break
            cursor += 100

        return papers[:max_results]

    def _hole_seite(self, url: str):
        """Holt eine Ergebnisseite; None, wenn die API nicht antwortet."""
        for versuch in range(1, self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.json().get('collection', [])
            except requests.exceptions.RequestException as e:
                if versuch == self.max_retries:
                    print(f"Failed to connect to bioRxiv API after "
                          f"{self.max_retries} attempts: {e}")
                    return None
                print(f"Attempt {versuch} failed, retrying...")
        return None

    def download_pdf(self, paper_id: str, save_path: str) -> str:
        """
        Download a PDF for a given paper ID from bioRxiv.

        Args:
            paper_id: The DOI of the paper.
            save_path: Directory to save the PDF.

        Returns:
            Path to the downloaded PDF file.
        """
        if not paper_id:
            raise ValueError("Invalid paper_id: paper_id is empty")

        pdf_url = f"https://www.biorxiv.org/content/{paper_id}v1.full.pdf"
        tries = 0
        while tries < self.max_retries:
            try:
                # Add User-Agent to avoid potential 403 errors
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = self.session.get(pdf_url, timeout=self.timeout, headers=headers)
                response.raise_for_status()
                os.makedirs(save_path, exist_ok=True)
                output_file = f"{save_path}/{paper_id.replace('/', '_')}.pdf"
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                return output_file
            except requests.exceptions.RequestException as e:
                tries += 1
                if tries == self.max_retries:
                    raise Exception(f"Failed to download PDF after {self.max_retries} attempts: {e}")
                print(f"Attempt {tries} failed, retrying...")
    
    def read_paper(self, paper_id: str, save_path: str = "./downloads") -> str:
        """
        Read a paper and convert it to text format.
        
        Args:
            paper_id: bioRxiv DOI
            save_path: Directory where the PDF is/will be saved
            
        Returns:
            str: The extracted text content of the paper
        """
        pdf_path = f"{save_path}/{paper_id.replace('/', '_')}.pdf"
        if not os.path.exists(pdf_path):
            pdf_path = self.download_pdf(paper_id, save_path)
        
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error reading PDF for paper {paper_id}: {e}")
            return ""