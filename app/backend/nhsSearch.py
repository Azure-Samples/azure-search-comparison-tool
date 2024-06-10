import re
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, quote_plus
from results import Results

class AlgoliaSiteSearch:

    def __init__(self, results: Results):

        self.logger = logging.getLogger(__name__)
        self.results = results

    def search(self, query: str) -> list:

        url = f"https://www.nhs.uk/search/results?q={quote_plus(query)}"

        self.logger.debug(url)

        response = requests.get(url)

        if response.status_code == 200:
            self.logger.debug(f"successful search for {query}")
            
            results = self.__process_search_results(response.text)

            self.logger.info("Found %s results for %s", len(results), query)

            # self.results.persist_results(query, "algolia", results)

            return results

        else:
            self.logger.error(f"Failed to retrieve search results: {response.status_code}")

        return None


    def __process_search_results(self, results_html: str) -> list:

        soup = BeautifulSoup(results_html, 'html.parser')

        links = soup.find_all(name= 'a', href=re.compile("^/search/click\?id="))

        results = []

        for link in links:

            parsed_uri = urlparse(link["href"])

            query_params = parse_qs(parsed_uri.query)

            inner_uri = urlparse(query_params["url"][0])

            id = inner_uri.path.strip('/').split('/')[-1]

            # print(link.text)

            # print(id)

            results.append(
                {
                    "id": id,
                    "title": link.text.strip(),
                    "score": 0,
                    "relevance": 0
                })
        
        return results