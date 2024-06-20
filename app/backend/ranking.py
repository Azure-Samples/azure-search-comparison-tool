import numpy as np
import json
import logging
import os, glob

class Ranking:
    def __init__(self):

        self.logger = logging.getLogger(__name__)

        self.ranked_queries = {}

        path = './data/search_queries'
        for filename in glob.glob(os.path.join(path, '*.json')):

            with open(os.path.join(os.getcwd(), filename), 'r') as f: # open in readonly mode

                for item in json.load(f):

                    query = item["query"].lower()

                    rankings = item["rankings"] if "rankings" in item and len(item["rankings"]) > 0 else None

                    if rankings is not None:
                        self.logger.debug(f"Found {len(item["rankings"])} rankings for {query}")
                        self.ranked_queries[query] = item

        self.logger.debug(f"loaded {len(self.ranked_queries)} ranked search queries")

    def hasIdealRanking(self, query: str):
        return query.lower() in self.ranked_queries
    
    def rank_results(self, query: str, results):

        ideal_rankings = self.__get_ideal_rankings(query)

        self.logger.debug("ideal rankings => %s", ideal_rankings)
        
        result_rankings = {}

        for result in results:

            self.logger.debug("result: %s", result)

            result_rankings[result] = ideal_rankings[result] if result in ideal_rankings else 0

        self.logger.debug("result rankings => %s", result_rankings)

        idcg_10 = self.__dcg(list(ideal_rankings.values()))
        dcg_10 = self.__dcg(list(result_rankings.values()))

        ndcg_10 = dcg_10 / idcg_10 if idcg_10 > 0 else 0.0

        idcg_3 = self.__dcg(list(ideal_rankings.values()), k=3)
        dcg_3 = self.__dcg(list(result_rankings.values()), k=3)

        ndcg_3 = dcg_3 / idcg_3 if idcg_3 > 0 else 0.0

        self.logger.debug(f"NDCG@3: {ndcg_3} - NDCG@10: {ndcg_10}")
        
        return {
            "ndcg@3": ndcg_3,
            "ndcg@10": ndcg_10,
            "ideal_rankings": ideal_rankings,
            "result_rankings": result_rankings
        }
    
    def __get_relevance(self, x):
        return x["relevance"]
    
    def __get_ideal_rankings(self, query: str) -> dict | None:

        if query.lower() in self.ranked_queries:

            rks = {}

            for ranking in sorted(
                self.ranked_queries[query.lower()]["rankings"],
                key=self.__get_relevance,
                reverse=True)[:10]:

                rks[ranking["id"]] = ranking["relevance"]

            return rks
            
        self.logger.error(f"did not find result rankings for {query}")

        return None

    def __dcg(self, relevance_scores: list, k = 10):

        # convert to array of floats
        f_relevance_scores = np.asfarray(relevance_scores)[:k]

        if len(f_relevance_scores) < k:

            self.logger.warn("padding relevance scores with zeros")

            i = iter(f_relevance_scores)
            f_relevance_scores = np.asfarray([next(i, 0) for _ in range(k)])

        dcg = 0.0

        for i, score in enumerate(f_relevance_scores):
            gain = score / np.log2(i + 2)

            dcg += gain

        self.logger.info(f"dcg for {f_relevance_scores} => {dcg}")

        return dcg