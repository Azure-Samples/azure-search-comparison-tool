import requests
from azure.search.documents import SearchClient


class SearchImages:
    def __init__(
        self,
        search_client: SearchClient,
        embedding_deployment: str,
        visionAi_endpoint: str,
        visionAi_api_version: str,
        visionAi_key: str,
    ):
        self.search_client = search_client
        self.embedding_deployment = embedding_deployment
        self.visionAi_endpoint = visionAi_endpoint
        self.visionAi_api_version = visionAi_api_version
        self.visionAi_key = visionAi_key

    def search(self, search_text: str):
        query_vector = self.embed_query(search_text)

        search_results = self.search_client.search(
            search_text,
            vector=query_vector,
            top_k=3,
            vector_fields="imageVector",
            select=["title,imageUrl"],
        )

        return {
            "results": list(search_results),
            "queryVector": query_vector,
            "semanticAnswers": search_results.get_answers(),
        }

    def embed_query(self, query: str):
        response = requests.post(
            f"{self.visionAi_endpoint}computervision/retrieval:vectorizeText",
            params={"api-version": self.visionAi_api_version},
            headers={
                "Content-Type": "application/json",
                "Ocp-Apim-Subscription-Key": self.visionAi_key,
            },
            json={"text": query},
        )

        if response.status_code != 200:
            raise Exception(response.json())

        return response.json()["vector"]
