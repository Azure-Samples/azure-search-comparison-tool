import os
import time
import logging
import gzip
import logging.config
import yaml
from openai import AzureOpenAI
from io import BytesIO
from quart import Quart, request, jsonify, Blueprint, current_app
from azure.identity.aio import DefaultAzureCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient

from results import Results
from searchText import SearchText
from indexSchema import IndexSchema
from nhsSearch import AlgoliaSiteSearch

# config keys
CONFIG_OPENAI_SERVICE = "openai_service"
CONFIG_OPENAI_CLIENT = "openai_client"
CONFIG_OPENAI_TOKEN_CREATED_TIME = "openai_token_created_at"
CONFIG_CREDENTIAL = "azure_credential"
CONFIG_EMBEDDING_DEPLOYMENT = "embedding_deployment"
CONFIG_SEARCH_TEXT_INDEX = "search_text"
CONFIG_SEARCH_CONDITIONS_INDEX = "search_conditions"
CONFIG_INDEX = "index"
CONFIG_INDEX_CONDITIONS = "index_conditions"
CONFIG_ALGOLIA_SEARCH = "algolia_search"

dataSetConfigDict = {
     "sample": CONFIG_SEARCH_TEXT_INDEX,
     "conditions": CONFIG_SEARCH_CONDITIONS_INDEX
}

bp = Blueprint("routes", __name__, static_folder="static")

@bp.route("/", defaults={"path": "index.html"})
@bp.route("/<path:path>")
async def static_file(path):
    return await bp.send_static_file(path)


@bp.route("/embedQuery", methods=["POST"])
async def embed_query():
    try:
        request_json = await request.get_json()
        query = request_json["query"]

        openai_client = current_app.config[CONFIG_OPENAI_CLIENT]

        response = openai_client.embeddings.create(
            input = query,
            model = current_app.config[CONFIG_EMBEDDING_DEPLOYMENT]
        )

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

            vector_search = (
                request_json["vectorSearch"] if request_json.get("vectorSearch") else False
            )
            hybrid_search = (
                request_json["hybridSearch"] if request_json.get("hybridSearch") else False
            )
            select = request_json["select"] if request_json.get("select") else None
            k = request_json["k"] if request_json.get("k") else 10
            filter = request_json["filter"] if request_json.get("filter") else None
            use_semantic_ranker = (
                request_json["useSemanticRanker"]
                if request_json.get("useSemanticRanker")
                else False
            )
            use_semantic_captions = (
                request_json["useSemanticCaptions"]
                if request_json.get("useSemanticCaptions")
                else False
            )
            query_vector = (
                request_json["queryVector"] if request_json.get("queryVector") else None
            )

            data_set = request_json["dataSet"] if request_json.get("dataSet") else "sample"
            indexConfig = dataSetConfigDict[data_set]

            r = await current_app.config[indexConfig].search(
                query=query,
                use_vector_search=vector_search,
                use_hybrid_search=hybrid_search,
                use_semantic_ranker=use_semantic_ranker,
                use_semantic_captions=use_semantic_captions,
                select=select,
                k=k,
                filter=filter,
                query_vector=query_vector,
                data_set=data_set,
                approach=approach
            )

            return jsonify(r), 200
    except Exception as e:
        logging.exception("Exception in /searchText")
        return jsonify({"error": str(e)}), 500


@bp.route("/getEfSearch", methods=["GET"])
async def get_efsearch():
    try:
        ef_search = await current_app.config[CONFIG_INDEX].get_efsearch()
        return str(ef_search), 200
    except Exception as e:
        logging.exception("Exception in /getEfSearch")
        return jsonify({"error": str(e)}), 500

@bp.route("/updateEfSearch", methods=["POST"])
async def update_efsearch():
    try:
        request_json = await request.get_json()
        newValue = request_json["efSearch"] if request_json.get("efSearch") else None
        await current_app.config[CONFIG_INDEX_CONDITIONS].update_efsearch(int(newValue))
        ef_search = await current_app.config[CONFIG_INDEX].update_efsearch(int(newValue))
        return str(ef_search), 200
    except Exception as e:
        logging.exception("Exception in /updateEfSearch")
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
    AZURE_OPENAI_DEPLOYMENT_NAME = (
        os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or "embedding"
    )
    AZURE_SEARCH_SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
    AZURE_SEARCH_TEXT_INDEX_NAME = os.getenv("AZURE_SEARCH_TEXT_INDEX_NAME")
    AZURE_SEARCH_CONDITIONS_INDEX_NAME = os.getenv("AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME")

    POSTGRES_SERVER_NAME = os.getenv("POSTGRES_SERVER")
    POSTGRES_USER = os.getenv("POSTGRES_SERVER_ADMIN_LOGIN")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_SERVER_ADMIN_PASSWORD")

    # Use the current user identity to authenticate with Azure OpenAI, Cognitive Search and AI Vision (no secrets needed, just use 'az login' locally, and managed identity when deployed on Azure).
    # If you need to use keys, use separate AzureKeyCredential instances with the keys for each service.
    # If you encounter a blocking error during a DefaultAzureCredential resolution, you can exclude the problematic credential by using a parameter (ex. exclude_shared_token_cache_credential=True).
    azure_credential = DefaultAzureCredential(
        exclude_shared_token_cache_credential=True
    )
    
    openai_client = await get_openai_client(azure_credential, AZURE_OPENAI_SERVICE)

    # Set up clients for Cognitive Search
    search_client_text = SearchClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        index_name=AZURE_SEARCH_TEXT_INDEX_NAME,
        credential=azure_credential,
    )
    search_client_conditions = SearchClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        index_name=AZURE_SEARCH_CONDITIONS_INDEX_NAME,
        credential=azure_credential,
    )
    index_client = SearchIndexClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        credential=azure_credential,
    )

    results = Results(POSTGRES_SERVER_NAME, POSTGRES_USER, POSTGRES_PASSWORD)

    # Store on app.config for later use inside requests
    current_app.config[CONFIG_OPENAI_SERVICE] = AZURE_OPENAI_SERVICE
    # current_app.config[CONFIG_OPENAI_TOKEN] = openai_token
    current_app.config[CONFIG_CREDENTIAL] = azure_credential
    current_app.config[CONFIG_OPENAI_CLIENT] = openai_client
    current_app.config[CONFIG_OPENAI_TOKEN_CREATED_TIME] = time.time()
    current_app.config[CONFIG_EMBEDDING_DEPLOYMENT] = AZURE_OPENAI_DEPLOYMENT_NAME
    current_app.config[CONFIG_ALGOLIA_SEARCH] = AlgoliaSiteSearch(results)
    current_app.config[CONFIG_SEARCH_TEXT_INDEX] = SearchText(search_client_text, results)
    current_app.config[CONFIG_SEARCH_CONDITIONS_INDEX] = SearchText(
        search_client_conditions,
        results,
        semantic_configuration_name="basic-semantic-config",
        vector_field_names="titleVector,descriptionVector")
    current_app.config[CONFIG_INDEX] = IndexSchema(index_client, AZURE_SEARCH_TEXT_INDEX_NAME)
    current_app.config[CONFIG_INDEX_CONDITIONS] = IndexSchema(index_client, AZURE_SEARCH_CONDITIONS_INDEX_NAME)

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