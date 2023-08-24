from typing import Any
import openai
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType, QueryCaptionType, QueryAnswerType


class SearchText:
    def __init__(self, search_client: SearchClient, embedding_deployment: str):
        self.search_client = search_client
        self.embedding_deployment = embedding_deployment

    def search(
        self,
        query: str,
        use_vector_search: bool = False,
        use_hybrid_search: bool = False,
        use_semantic_ranker: bool = False,
        use_semantic_captions: bool = False,
        select: str | None = None,
        k: int | None = None,
        filter: str | None = None,
        query_vector: list[float] | None = None
    ):
        # Vectorize query
        query_vector = query_vector if use_vector_search else None
        vector_fields = "contentVector" if use_vector_search else None
        k = k if use_vector_search else None

        # Set text query for no-vector, semantic and 'Hybrid' searches
        query_text = (
            query
            if not use_vector_search or use_hybrid_search or use_semantic_ranker
            else None
        )

        # Semantic ranker options
        query_type = QueryType.SEMANTIC if use_semantic_ranker else None
        query_language = "en-us" if use_semantic_ranker else None
        semantic_configuration_name = (
            "my-semantic-config" if use_semantic_ranker else None
        )

        # Semantic caption options
        query_caption = QueryCaptionType.EXTRACTIVE if use_semantic_captions else None
        query_answer = QueryAnswerType.EXTRACTIVE if use_semantic_captions else None
        highlight_pre_tag = "<b>" if use_semantic_captions else None
        highlight_post_tag = "</b>" if use_semantic_captions else None

        # ACS search query
        search_results = self.search_client.search(
            query_text,
            vector=query_vector,
            vector_fields=vector_fields,
            top_k=k,
            select=select,
            filter=filter,
            query_type=query_type,
            query_language=query_language,
            semantic_configuration_name=semantic_configuration_name,
            query_caption=query_caption,
            query_answer=query_answer,
            highlight_pre_tag=highlight_pre_tag,
            highlight_post_tag=highlight_post_tag,
        )

        results = []
        for r in search_results:
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
                    "titleVector": r["titleVector"],
                    "content": r["content"],
                    "contentVector": r["contentVector"],
                    "category": r["category"],
                }
            )

        return {
            "results": results,
            "semanticAnswers": search_results.get_answers(),
        }
