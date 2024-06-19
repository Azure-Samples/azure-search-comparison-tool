import os
import time
import logging
import gzip
import json
import logging.config
import yaml
import redis
import hashlib
from openai import AzureOpenAI
from io import BytesIO
from quart import Quart, request, jsonify, Blueprint, current_app
from azure.identity.aio import DefaultAzureCredential
from azure.search.documents.aio import SearchClient

from results import Results
from approaches import Approaches
from searchText import SearchText
from nhsSearch import AlgoliaSiteSearch

# config keys
CONFIG_OPENAI_SERVICE = "openai_service"
CONFIG_OPENAI_CLIENT = "openai_client"
CONFIG_OPENAI_TOKEN_CREATED_TIME = "openai_token_created_at"
CONFIG_CREDENTIAL = "azure_credential"
CONFIG_SEARCH_CONDITIONS_INDEX = "search_conditions"
CONFIG_SEARCH_COMBINED_INDEX = "search_combined"
CONFIG_INDEX_CONDITIONS = "index_conditions"
CONFIG_ALGOLIA_SEARCH = "algolia_search"
CONFIG_REDIS_CLIENT = "redis_client"

dataSetConfigDict = {
     "conditions": CONFIG_SEARCH_CONDITIONS_INDEX,
     "combined": CONFIG_SEARCH_COMBINED_INDEX
}

bp = Blueprint("routes", __name__, static_folder="static")

@bp.route("/", defaults={"path": "index.html"})
@bp.route("/<path:path>")
async def static_file(path):
    return await bp.send_static_file(path)


@bp.route("/approaches", methods=["GET"])
def get_approaches():
    return Approaches("./data/approaches.json").get_approaches()

@bp.route("/embedQuery", methods=["POST"])
async def embed_query():
    try:
        request_json = await request.get_json()
        query = request_json["query"]
        approach = request_json["approach"]

        a = Approaches("./data/approaches.json").get(approach)

        deployment_name = a["open_ai_deployment_name"]

        redis_client = current_app.config[CONFIG_REDIS_CLIENT]

        query_hash = int(hashlib.sha256(query.encode('utf-8')).hexdigest(), 16) % 10**8

        key = f"search_{query_hash}_{deployment_name}"

        if redis_client.exists(key):
            
            cache_item = json.loads(redis_client.get(key))

            print(f"matched {key} for query {query}")

            return cache_item["embedding"], 200

        openai_client = current_app.config[CONFIG_OPENAI_CLIENT]

        response = openai_client.embeddings.create(
            input = query,
            model = deployment_name
        )

        redis_client.set(key, json.dumps({"query": query, "deployment": deployment_name, "embedding": response.data[0].embedding }))

        return response.data[0].embedding, 200
    except Exception as e:
        logging.exception("Exception in /embedQuery")
        return jsonify({"error": str(e)}), 500

@bp.route("/searchText", methods=["POST"])
async def search_text():
    if not request.is_json:
        return jsonify({"error": "request must be json"}), 400
    try:
        request_json = await request.get_json()

        approach = request_json["approach"]
        query = request_json["query"]

        if approach == "algolia":

            r = current_app.config[CONFIG_ALGOLIA_SEARCH].search(query)

            return jsonify(r), 200

        else:
            k = request_json["k"] if request_json.get("k") else 10

            use_semantic_captions = (
                request_json["useSemanticCaptions"]
                if request_json.get("useSemanticCaptions")
                else False
            )

            query_vector = (
                request_json["queryVector"] if request_json.get("queryVector") else None
            )

            data_set = request_json["dataSet"] if request_json.get("dataSet") else "conditions"
            indexConfig = dataSetConfigDict[data_set]

            r = await current_app.config[indexConfig].search(
                query=query,
                use_semantic_captions=use_semantic_captions,
                k=k,
                query_vector=query_vector,
                approach=approach
            )

            return jsonify(r), 200
    except Exception as e:
        logging.exception("Exception in /searchText")
        return jsonify({"error": str(e)}), 500

@bp.before_request
async def ensure_openai_token():

    if current_app.config[CONFIG_OPENAI_TOKEN_CREATED_TIME] + 300 < time.time():

        azure_credential = current_app.config[CONFIG_CREDENTIAL]
        openai_service = current_app.config[CONFIG_OPENAI_SERVICE]

        logging.info("Refreshing OpenAI token")

        current_app.config[CONFIG_OPENAI_CLIENT] = await get_openai_client(azure_credential, openai_service)

@bp.after_request
async def gzip_response(response):
    accept_encoding = request.headers.get("Accept-Encoding", "")
    if (
        response.status_code < 200
        or response.status_code >= 300
        or len(await response.get_data()) < 500
        or "gzip" not in accept_encoding.lower()
    ):
        return response

    gzip_buffer = BytesIO()
    gzip_file = gzip.GzipFile(mode="wb", compresslevel=6, fileobj=gzip_buffer)
    gzip_file.write(await response.get_data())
    gzip_file.close()
    response.set_data(gzip_buffer.getvalue())
    response.headers["Content-Encoding"] = "gzip"
    response.headers["Content-Length"] = len(await response.get_data())

    return response

@bp.before_app_serving
async def setup_clients():
    # Replace these with your own values, either in environment variables or directly here
    AZURE_OPENAI_SERVICE = os.getenv("AZURE_OPENAI_SERVICE")
    AZURE_SEARCH_SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
    AZURE_SEARCH_CONDITIONS_INDEX_NAME = os.getenv("AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME")
    AZURE_SEARCH_COMBINED_INDEX_NAME = os.getenv("AZURE_SEARCH_NHS_COMBINED_INDEX_NAME")

    POSTGRES_SERVER_NAME = os.getenv("POSTGRES_SERVER")
    POSTGRES_USER = os.getenv("POSTGRES_SERVER_ADMIN_LOGIN")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_SERVER_ADMIN_PASSWORD")

    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = os.getenv("REDIS_PORT")
    REDIS_PASSWORD = os.getenv("REDIS_PRIMARYKEY")

    # Use the current user identity to authenticate with Azure OpenAI, Cognitive Search and AI Vision (no secrets needed, just use 'az login' locally, and managed identity when deployed on Azure).
    # If you need to use keys, use separate AzureKeyCredential instances with the keys for each service.
    # If you encounter a blocking error during a DefaultAzureCredential resolution, you can exclude the problematic credential by using a parameter (ex. exclude_shared_token_cache_credential=True).
    azure_credential = DefaultAzureCredential(
        exclude_shared_token_cache_credential=True
    )

    redis_client = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        ssl=True,
        decode_responses=True
    )
    
    openai_client = await get_openai_client(azure_credential, AZURE_OPENAI_SERVICE)

    # Set up clients for Cognitive Search
    search_client_conditions = SearchClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        index_name=AZURE_SEARCH_CONDITIONS_INDEX_NAME,
        credential=azure_credential,
    )

    search_client_combined = SearchClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        index_name=AZURE_SEARCH_COMBINED_INDEX_NAME,
        credential=azure_credential,
    )

    results = Results(POSTGRES_SERVER_NAME, POSTGRES_USER, POSTGRES_PASSWORD)
    approaches = Approaches("./data/approaches.json")

    # Store on app.config for later use inside requests
    current_app.config[CONFIG_OPENAI_SERVICE] = AZURE_OPENAI_SERVICE
    # current_app.config[CONFIG_OPENAI_TOKEN] = openai_token
    current_app.config[CONFIG_CREDENTIAL] = azure_credential
    current_app.config[CONFIG_REDIS_CLIENT] = redis_client
    current_app.config[CONFIG_OPENAI_CLIENT] = openai_client
    current_app.config[CONFIG_OPENAI_TOKEN_CREATED_TIME] = time.time()
    current_app.config[CONFIG_ALGOLIA_SEARCH] = AlgoliaSiteSearch(results)
    current_app.config[CONFIG_SEARCH_CONDITIONS_INDEX] = SearchText(
        search_client_conditions,
        results,
        approaches)
    current_app.config[CONFIG_SEARCH_COMBINED_INDEX] = SearchText(
        search_client_combined,
        results,
        approaches)

def create_app():
    app = Quart(__name__)
    app.register_blueprint(bp)

    init_logging()

    return app

async def get_openai_client(azure_credential, openai_service_name):
    openai_token = await azure_credential.get_token(
        "https://cognitiveservices.azure.com/.default"
    )
    
    return AzureOpenAI(
        api_key = openai_token.token,  
        api_version = "2024-02-01",
        azure_endpoint = f"https://{openai_service_name}.openai.azure.com" 
    )

def init_logging():

    # Load the config file
    with open('logging_config.yaml', 'rt') as f:
        config = yaml.safe_load(f.read())

    logging.config.dictConfig(config)