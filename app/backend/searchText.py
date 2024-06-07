import logging
from typing import Any
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import QueryType, QueryCaptionType, QueryAnswerType, VectorizedQuery
from ranking import Ranking
from results import Results

class SearchText:
    def __init__(self, 
                search_client: SearchClient,
                results: Results,
                semantic_configuration_name="my-semantic-config",
                vector_field_names="titleVector,contentVector"):
        self.search_client = search_client
        self.semantic_configuration_name = semantic_configuration_name
        self.vector_field_names = vector_field_names
        self.ranking = Ranking()
        self.logger = logging.getLogger(__name__)
        self.results = results

        self.approach = {
             "text": "Text Only (BM25)",
             "vec": "Vectors Only (ANN)",
             "hs": "Vectors + Text (Hybrid Search)",
             "hssr": "Hybrid + Semantic Reranking"
        }

    async def search(
        self,
        query: str,
        use_vector_search: bool = False,
        use_hybrid_search: bool = False,
        use_semantic_ranker: bool = False,
        use_semantic_captions: bool = False,
        select: str | None = None,
        k: int | None = None,
        filter: str | None = None,
        query_vector: list[float] | None = None,
        data_set: str = "sample",
        approach: str = "undefined"
    ):

        # Vectorize query
        query_vector = query_vector if use_vector_search else None

        # Set text query for no-vector, semantic and 'Hybrid' searches
        query_text = (
            query
            if not use_vector_search or use_hybrid_search or use_semantic_ranker
            else None
        )

        # Semantic ranker options
        query_type = QueryType.SEMANTIC if use_semantic_ranker else QueryType.SIMPLE

        semantic_configuration = (
            self.semantic_configuration_name
            if use_semantic_ranker
            else None
        )

        # Semantic caption options
        query_caption = QueryCaptionType.EXTRACTIVE if use_semantic_captions else None
        query_answer = QueryAnswerType.EXTRACTIVE if use_semantic_captions else None
        highlight_pre_tag = "<b>" if use_semantic_captions else None
        highlight_post_tag = "</b>" if use_semantic_captions else None

        vector_queries = (
            [VectorizedQuery(vector=query_vector,fields=self.vector_field_names)]
            if use_vector_search
            else None
        )

        # ACS search query
        search_results = await self.search_client.search(
            query_text,
            vector_queries = vector_queries,
            top=k,
            select=select,
            filter=filter,
            query_type=query_type,
            semantic_configuration_name=semantic_configuration,
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

            if data_set == "sample":
                results.append(
                    {
                        "@search.score": r["@search.score"],
                        "@search.reranker_score": r["@search.reranker_score"],
                        "@search.captions": captions,
                        "id": r["id"],
                        "title": r["title"],
                        "titleVector": r["titleVector"],
                        "content": r["content"],
                        "contentVector": r["contentVector"],
                        "category": r["category"],
                    }
                )
            elif data_set == "conditions":
                results.append(
                    {
                        "@search.score": r["@search.score"],
                        "@search.reranker_score": r["@search.reranker_score"],
                        "@search.captions": captions,
                        "id": r["id"],
                        "title": r["title"],
                        "content": r["description"],
                        "titleVector": r["titleVector"],
                        "descriptionVector": r["descriptionVector"],
                    }
                )

                self.logger.debug(f"{r["@search.score"]} - {r["id"]}")

        if can_calc_ncdg and data_set == "conditions":

            ordered_result_ids = []

            for result in results:
                ordered_result_ids.append(result["id"])
                
            ranking_result = self.ranking.rank_results(query, ordered_result_ids)

            self.logger.info(f"{self.approach[approach]}  => NDCG:{ranking_result}")

            self.results.add(query, approach, ranking_result)

        return {
            "results": results,
        }
