import numpy as np
import json
import logging

class Ranking:
    def __init__(self):

        self.logger = logging.getLogger(__name__)

        with open("data/rankings.json", "r", encoding="utf-8") as file:
            self.input_data = json.load(file)

            self.logger.debug(f"loaded {len(self.input_data)} ranking queries")

    def hasIdealRanking(self, query: str):

        for item in self.input_data:
            if item["query"].lower() == query.lower():
                return True
            
        return False
    
    def rank_results(self, query: str, results):

        ideal_rankings = self.__get_ideal_rankings(query)

        self.logger.debug("ideal rankings => %s", ideal_rankings)
        
        result_rankings = {}

        for result in results:

            result_rankings[result] = ideal_rankings[result] if result in ideal_rankings else 0

        self.logger.debug("result rankings => %s", result_rankings)

        actual_dcg_3 = self.__dcg(list(result_rankings.values()),3)
        ideal_dcg_3 = self.__dcg(list(ideal_rankings.values()),3)

        actual_dcg_5 = self.__dcg(list(result_rankings.values()),5)
        ideal_dcg_5 = self.__dcg(list(ideal_rankings.values()),5)

        actual_dcg_10 = self.__dcg(list(result_rankings.values()),10)
        ideal_dcg_10 = self.__dcg(list(ideal_rankings.values()),10)

        # Calculate the Normalized Discounted Cumulative Gain (NDCG).
        ndcg_result_3 = actual_dcg_3 / ideal_dcg_3 if ideal_dcg_3 > 0 else 0.0
        ndcg_result_5 = actual_dcg_5 / ideal_dcg_5 if ideal_dcg_5 > 0 else 0.0
        ndcg_result_10 = actual_dcg_10 / ideal_dcg_10 if ideal_dcg_10 > 0 else 0.0

        self.logger.debug(f"NDCG@3:{ndcg_result_3} actual dcg:{actual_dcg_3} ideal dcg:{ideal_dcg_3}")
        self.logger.debug(f"NDCG@5:{ndcg_result_5} actual dcg:{actual_dcg_5} ideal dcg:{ideal_dcg_5}")
        self.logger.debug(f"NDCG@10:{ndcg_result_10} actual dcg:{actual_dcg_10} ideal dcg:{ideal_dcg_10}")

        return {
            "ndcg": ndcg_result_5,
            "ndcg@3": ndcg_result_3,
            "ndcg@10": ndcg_result_10,
            "ideal_rankings": ideal_rankings,
            "result_rankings": result_rankings
        }
    
    def __get_ideal_rankings(self, query: str):

        for item in self.input_data:
            if item["query"].lower() == query.lower():

                rks = {}

                for ranking in item["rankings"]:
                    rks[ranking["id"]] = ranking["relevance"]

                return rks
            
        self.logger.error(f"did not find result rankings for {query}")

        return None

    def __dcg(self, relevance_scores, k: int):
        """
        Calculate the Discounted Cumulative Gain (DCG) for a given ranking.
        :param relevance_scores: List of relevance scores in the ranked order.
        :param k: Number of results to consider (cut-off at position k).
        :return: DCG value.
        """

        relevance_scores = np.asfarray(relevance_scores)[:k]

        if relevance_scores.size:
            return np.sum((2**relevance_scores - 1) / np.log2(np.arange(2, relevance_scores.size + 2)))
        
        return 0.0
