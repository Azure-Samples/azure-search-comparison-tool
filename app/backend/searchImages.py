
import aiohttp
from azure.search.documents.aio import SearchClient
import base64


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

    async def search(self, query: str, dataType: str):
        match dataType:
            case "text":
                query_vector = await self.embed_query_text(query)
                search_text = query
            case "imageFile":
                query_vector = await self.embed_query_imageFile(query)
                search_text = None
            case "imageUrl":
                query_vector = await self.embed_query_imageUrl(query)
                search_text = None

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

    async def embed_query_text(self, query: str):
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
            
    async def embed_query_imageFile(self, query: str):
        binaryData = base64.b64decode(query.split(",")[1])
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.visionAi_endpoint}computervision/retrieval:vectorizeImage?overload=stream&api-version={self.visionAi_api_version}",
                headers={
                    "Content-Type": "application/octet-stream",
                    "Ocp-Apim-Subscription-Key": self.visionAi_key,
                },
                data=binaryData,
            ) as response:
                response_json = await response.json()

                if response.status != 200:
                    raise Exception(response_json)

                return response_json["vector"]


    async def embed_query_imageUrl(self, query: str):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.visionAi_endpoint}computervision/retrieval:vectorizeImage?api-version={self.visionAi_api_version}",
                headers={
                    "Content-Type": "application/json",
                    "Ocp-Apim-Subscription-Key": self.visionAi_key,
                },
                json={"url": query},
            ) as response:
                response_json = await response.json()

                if response.status != 200:
                    raise Exception(response_json)

                return response_json["vector"]