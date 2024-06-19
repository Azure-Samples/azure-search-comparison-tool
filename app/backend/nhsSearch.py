import re
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, quote_plus
from results import Results
from ranking import Ranking

class AlgoliaSiteSearch:

    def __init__(self, results: Results):

        self.logger = logging.getLogger(__name__)
        self.ranking = Ranking()
        self.results = results

    def search(self, query: str) -> list:

        can_calc_ncdg = self.ranking.hasIdealRanking(query)

        url = f"https://www.nhs.uk/search/results?q={quote_plus(query)}"

        self.logger.debug(url)

        response = requests.get(url)

        if response.status_code == 200:
            self.logger.debug(f"successful search for {query}")
            
            results = self.__process_search_results(response.text)

            self.logger.info("Found %s results for %s", len(results), query)

            if can_calc_ncdg:
                self.evaluate_well_known_search_query(query, results)
            else:
                self.results.persist_results(query, "algolia", results)

            return results

        else:
            self.logger.error(f"Failed to retrieve search results: {response.status_code}")

        return None
    
    def evaluate_well_known_search_query(self, query: str, results: list):
        ordered_result_ids = []

        actual_results = []

        for result in results:
            ordered_result_ids.append(result["id"])
            actual_results.append({"id": result["id"], "score": 0})
            
        ranking_result = self.ranking.rank_results(query, ordered_result_ids)

        self.logger.info(f"Algolia  => NDCG@3:{ranking_result["ndcg@3"]}")

        for key, value in list(ranking_result["result_rankings"].items()):

            result = next((item for item in actual_results if item.get("id") == key), None)

            result["relevance"] = value

            self.logger.debug(result)

        ideal_results = []

        for key, value in list(ranking_result["ideal_rankings"].items()):
            print(f"{key}->{value}")
            ideal_results.append({"id": key, "relevance": value})

        self.results.persist_ranked_results(
            query,
            "algolia",
            ranking_result["ndcg@3"],
            ranking_result["ndcg@10"],
            ideal_results,
            actual_results)

    def __process_search_results(self, results_html: str) -> list:

        soup = BeautifulSoup(results_html, 'html.parser')

        links = soup.find_all(name= 'a', href=re.compile("^/search/click\?id="))

        results = []

        for link in links:

            parsed_uri = urlparse(link["href"])

            query_params = parse_qs(parsed_uri.query)

            inner_uri = urlparse(query_params["url"][0])

            id = inner_uri.path.strip('/').replace("/", "_")

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