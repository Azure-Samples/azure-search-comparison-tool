import os
import time
import logging
import openai
from flask import Flask, request, jsonify
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

from searchText import SearchText
from searchImages import SearchImages

# Replace these with your own values, either in environment variables or directly here
AZURE_OPENAI_SERVICE = os.environ.get("AZURE_OPENAI_SERVICE")
AZURE_OPENAI_DEPLOYMENT_NAME = (
    os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME") or "embedding"
)
AZURE_VISIONAI_ENDPOINT = os.environ.get("AZURE_VISIONAI_ENDPOINT")
AZURE_VISIONAI_KEY = os.environ.get("AZURE_VISIONAI_KEY")
AZURE_VISIONAI_API_VERSION = (
    os.environ.get("AZURE_VISIONAI_API_VERSION") or "2023-02-01-preview"
)
AZURE_SEARCH_SERVICE_ENDPOINT = os.environ.get("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_TEXT_INDEX_NAME = os.environ.get("AZURE_SEARCH_TEXT_INDEX_NAME")
AZURE_SEARCH_IMAGE_INDEX_NAME = os.environ.get("AZURE_SEARCH_IMAGE_INDEX_NAME")


# Use the current user identity to authenticate with Azure OpenAI, Cognitive Search and AI Vision (no secrets needed, just use 'az login' locally, and managed identity when deployed on Azure).
# If you need to use keys, use separate AzureKeyCredential instances with the keys for each service.
# If you encounter a blocking error during a DefaultAzureCredntial resolution, you can exclude the problematic credential by using a parameter (ex. exclude_shared_token_cache_credential=True).
azure_credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)

# Used by the OpenAI SDK
openai.api_type = "azure"
openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
openai.api_version = "2023-05-15"

# Comment these two lines out if using keys, set your API key in the OPENAI_API_KEY environment variable instead
openai.api_type = "azure_ad"
openai_token = azure_credential.get_token(
    "https://cognitiveservices.azure.com/.default"
)
openai.api_key = openai_token.token

# Set up clients for Cognitive Search
search_client_text = SearchClient(
    endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
    index_name=AZURE_SEARCH_TEXT_INDEX_NAME,
    credential=azure_credential,
)
search_client_images = SearchClient(
    endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
    index_name=AZURE_SEARCH_IMAGE_INDEX_NAME,
    credential=azure_credential,
)

app = Flask(__name__)


@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def static_file(path):
    return app.send_static_file(path)

@app.route("/embedQuery", methods=["POST"])
def embed_query():
    try:
       query=request.json["query"]
       response = openai.Embedding.create(input=query, engine=AZURE_OPENAI_DEPLOYMENT_NAME)
       return response["data"][0]["embedding"], 200
    except Exception as e:
        logging.exception("Exception in /embedQuery")
        return jsonify({"error": str(e)}), 500

@app.route("/searchText", methods=["POST"])
def search_text():
    if not request.json:
        return jsonify({"error": "request must be json"}), 400
    try:
        vector_search = (
            request.json["vectorSearch"] if request.json.get("vectorSearch") else False
        )
        hybrid_search = (
            request.json["hybridSearch"] if request.json.get("hybridSearch") else False
        )
        select = request.json["select"] if request.json.get("select") else None
        k = request.json["k"] if request.json.get("k") else 10
        filter = request.json["filter"] if request.json.get("filter") else None
        use_semantic_ranker = (
            request.json["useSemanticRanker"]
            if request.json.get("useSemanticRanker")
            else False
        )
        use_semantic_captions = (
            request.json["useSemanticCaptions"]
            if request.json.get("useSemanticCaptions")
            else False
        )
        query_vector = (
            request.json["queryVector"] if request.json.get("queryVector") else None
        )

        r = SearchText(search_client_text, AZURE_OPENAI_DEPLOYMENT_NAME).search(
            query=request.json["query"],
            use_vector_search=vector_search,
            use_hybrid_search=hybrid_search,
            use_semantic_ranker=use_semantic_ranker,
            use_semantic_captions=use_semantic_captions,
            select=select,
            k=k,
            filter=filter,
            query_vector=query_vector
        )

        return jsonify(r), 200
    except Exception as e:
        logging.exception("Exception in /searchText")
        return jsonify({"error": str(e)}), 500


@app.route("/searchImages", methods=["POST"])
def search_images():
    if not request.json:
        return jsonify({"error": "request must be json"}), 400
    try:
        r = SearchImages(
            search_client_images,
            AZURE_OPENAI_DEPLOYMENT_NAME,
            AZURE_VISIONAI_ENDPOINT,
            AZURE_VISIONAI_API_VERSION,
            AZURE_VISIONAI_KEY,
        ).search(request.json["query"])

        return jsonify(r), 200
    except Exception as e:
        logging.exception("Exception in /searchImages")
        return jsonify({"error": str(e)}), 500


@app.before_request
def ensure_openai_token():
    global openai_token
    if openai_token.expires_on < time.time() + 60:
        openai_token = azure_credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        )
        openai.api_key = openai_token.token


if __name__ == "__main__":
    app.run()
