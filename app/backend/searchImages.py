import logging
import aiohttp
from azure.search.documents.aio import SearchClient


class SearchImages:
    def __init__(
        self,
        search_client: SearchClient,
        visionAi_endpoint: str,
        visionAi_api_version: str,
        visionAi_key: str,
    ):
        self.search_client = search_client
        self.visionAi_endpoint = visionAi_endpoint
        self.visionAi_api_version = visionAi_api_version
        self.visionAi_key = visionAi_key

    async def search(self, search_text: str):
        query_vector = await self.embed_query(search_text)

        search_results = await self.search_client.search(
            search_text,
            vector=query_vector,
            top_k=3,
            vector_fields="imageVector",
            select=["id,title,imageUrl"],
        )

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
                    "imageUrl": r["imageUrl"],
                }
            )

        return {
            "results": results,
            "queryVector": query_vector,
        }

    async def embed_query(self, query: str):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.visionAi_endpoint}computervision/retrieval:vectorizeText?api-version={self.visionAi_api_version}",
                headers={
                    "Content-Type": "application/json",
                    "Ocp-Apim-Subscription-Key": self.visionAi_key,
                },
                json={"text": query},
            ) as response:
                response_json = await response.json()

                if response.status != 200:
                    raise Exception(response_json)

                return response_json["vector"]
