import logging
from typing import Any
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import QueryType, QueryCaptionType, QueryAnswerType, VectorizedQuery, SearchMode
from ranking import Ranking
from results import Results
from approaches import Approaches

class SearchText:
    def __init__(self, 
                search_client: SearchClient,
                results: Results,
                approaches: Approaches):
        self.search_client = search_client
        self.ranking = Ranking()
        self.logger = logging.getLogger(__name__)
        self.results = results
        self.approaches = approaches

    async def search(
        self,
        query: str,
        use_semantic_captions: bool = False,
        k: int | None = None,
        query_vector: list[float] | None = None,
        approach: str = "text"
    ):
        # get approach config

        approach_config = self.approaches.get(approach)

        use_vector_search = approach_config["use_vector_search"]
        use_hybrid_search = approach_config["use_hybrid_search"] if use_vector_search else False
        use_semantic_ranker = approach_config["use_semantic_ranker"] if use_vector_search else False

        select = approach_config["output_field_names"] if "output_field_names" in approach_config else None

        # Vectorize query
        query_vector = query_vector if use_vector_search else None

        # Set vector field names
        vector_field_names = approach_config["vector_field_names"] if use_vector_search else None

        # Set text query for no-vector, semantic and 'Hybrid' searches
        query_text = (
            query
            if not use_vector_search or use_hybrid_search or use_semantic_ranker
            else None
        )

        # Semantic ranker options
        query_type = QueryType.SEMANTIC if use_semantic_ranker else QueryType.SIMPLE

        search_mode = SearchMode.ALL

        semantic_configuration = approach_config["semantic_configuration_name"] if use_semantic_ranker else None

        scoring_profile_name = approach_config["scoring_profile_name"] if "scoring_profile_name" in approach_config else None

        # Semantic caption options
        query_caption = QueryCaptionType.EXTRACTIVE if use_semantic_captions else None
        query_answer = QueryAnswerType.EXTRACTIVE if use_semantic_captions else None
        highlight_pre_tag = "<b>" if use_semantic_captions else None
        highlight_post_tag = "</b>" if use_semantic_captions else None

        vector_queries = (
            [VectorizedQuery(vector=query_vector,fields=vector_field_names)]
            if use_vector_search
            else None
        )

        # ACS search query
        search_results = await self.search_client.search(
            query_text,
            vector_queries = vector_queries,
            top=k,
            select=select,
            query_type=query_type,
            search_mode=search_mode,
            semantic_configuration_name=semantic_configuration,
            scoring_profile=scoring_profile_name,
            query_caption=query_caption,
            query_answer=query_answer,
            highlight_pre_tag=highlight_pre_tag,
            highlight_post_tag=highlight_post_tag
        )

        can_calc_ncdg = self.ranking.hasIdealRanking(query)

        results = []
        async for r in search_results:
            captions = (
                list(
                    map(
                        lambda c: {"text": c.text, "highlights": c.highlights},
                        r["@search.captions"],
                    )
                )
                if r["@search.captions"]
                else None
            )

            results.append(
                {
                    "@search.score": r["@search.score"],
                    "@search.reranker_score": r["@search.reranker_score"],
                    "@search.captions": captions,
                    "id": r["id"],
                    "title": r["title"],
                    "content": r["description"]
                }
            )

            self.logger.debug(f"{r["@search.score"]} - {r["id"]}")

        if can_calc_ncdg:
            self.evaluate_well_known_search_query(query, approach_config, results)
        else:
            self.store_query_results(query, approach, results)

        return {
            "results": results,
        }
    
    def store_query_results(self, query: str, approach: str, results: list):

        actual_results = []

        for result in results:
            actual_results.append(
                {
                    "id": result["id"],
                    "score": result["@search.score"],
                    "relevance": 0
                })
        
        self.results.persist_results(query, approach, actual_results)
        
    
    def evaluate_well_known_search_query(self, query: str, approach_config, results: list):
        ordered_result_ids = []

        actual_results = []

        for result in results:
            ordered_result_ids.append(result["id"])
            actual_results.append({"id": result["id"], "score": result["@search.score"]})
            
        ranking_result = self.ranking.rank_results(query, ordered_result_ids)

        self.logger.info(f"{approach_config["title"]}  => NDCG@3:{ranking_result["ndcg@3"]}")

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
            approach_config["key"],
            ranking_result["ndcg@3"],
            ranking_result["ndcg@10"],
            ideal_results,
            actual_results)
