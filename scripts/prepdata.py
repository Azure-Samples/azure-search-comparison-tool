import argparse
import base64
import os
import json
import random
import string
import time
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import uuid
import redis
import logging
import numpy as np

from openai import AzureOpenAI
#from tenacity import retry, wait_random_exponential, stop_after_attempt
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswParameters,
    SemanticPrioritizedFields,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    ExhaustiveKnnAlgorithmConfiguration
)
from postgres import Postgres

AZURE_OPENAI_SERVICE = os.environ.get("AZURE_OPENAI_SERVICE")
AZURE_OPENAI_DEPLOYMENT_NAME = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_OPENAI_DEPLOYMENT_LARGE_NAME = os.environ.get("AZURE_OPENAI_DEPLOYMENT_LARGE_NAME")
AZURE_SEARCH_SERVICE_ENDPOINT = os.environ.get("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME = os.environ.get("AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME")
AZURE_SEARCH_NHS_COMBINED_INDEX_NAME = os.environ.get("AZURE_SEARCH_NHS_COMBINED_INDEX_NAME")

REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT")
REDIS_PASSWORD = os.environ.get("REDIS_PRIMARYKEY")

POSTGRES_SERVER_NAME = os.environ.get("POSTGRES_SERVER")
POSTGRES_SERVER_ADMIN_NAME = os.environ.get("POSTGRES_SERVER_ADMIN_LOGIN")
POSTGRES_SERVER_ADMIN_PASSWORD = os.environ.get("POSTGRES_SERVER_ADMIN_PASSWORD")

open_ai_token_cache = {}
CACHE_KEY_TOKEN_CRED = "openai_token_cred"
CACHE_KEY_CREATED_TIME = "created_time"

def create_and_populate_search_index_nhs_conditions():
    created = create_search_index_nhs_conditions()
    if created:
        populate_search_index_nhs_conditions()

def create_search_index_nhs_conditions():
    print(f"Ensuring search index {AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME} exists")
    index_client = SearchIndexClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        credential=azure_credential,
    )
    if AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME not in index_client.list_index_names():
        index = SearchIndex(
            name=AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME,
            fields=[
                SimpleField(name="id", key=True, type=SearchFieldDataType.String),
                SearchableField(name="title", type=SearchFieldDataType.String),
                SearchableField(name="description", type=SearchFieldDataType.String),
                SearchField(
                    name="titleVector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,
                    vector_search_profile_name="hnswProfile",
                ),
                SearchField(
                    name="descriptionVector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,
                    vector_search_profile_name="hnswProfile",
                ),
            ],
            vector_search=VectorSearch(
                algorithms=[HnswAlgorithmConfiguration(name="pdfHnsw")],
                profiles=[VectorSearchProfile(name="hnswProfile",
                                                algorithm_configuration_name="pdfHnsw")
                            ]
            ),
            semantic_search=SemanticSearch(
                configurations=[
                    SemanticConfiguration(
                        name="basic-semantic-config",
                        prioritized_fields=SemanticPrioritizedFields(
                            title_field=SemanticField(field_name="title"),
                            content_fields=[
                                SemanticField(field_name="description")
                            ],
                        ),
                    )
                ]
            ),
        )
        print(f"Creating {AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME} search index")
        index_client.create_index(index)
        return True
    else:
        print(f"Search index {AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME} already exists")
        return False

def populate_search_index_nhs_conditions():
    print(f"Populating search index {AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME} with documents")

    with open("data/conditions_1.json", "r", encoding="utf-8") as file:
        items = json.load(file)

    search_client = SearchClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        credential=azure_credential,
        index_name=AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME,
    )

    redis_client = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        ssl=True,
        decode_responses=True
    )

    batched_treated_items = []
    batch_size = 4

    for item in items:

        treated_item = {
            "id": item["id"],
            "title": item["title"],
            "description": item["description"]
        }

        item_key = f"{item['id']}_{AZURE_OPENAI_DEPLOYMENT_NAME}"

        if redis_client.exists(item_key):
            print(f"Document with id {item['id']} already exists in Redis cache, retrieving vectors.")

            cached_item = json.loads(redis_client.get(item_key))
            treated_item["titleVector"] = cached_item["titleVector"]
            treated_item["descriptionVector"] = cached_item["descriptionVector"]
        else:
            print(f"Generating Azure OpenAI embeddings for {item["id"]} ...")

            treated_item["titleVector"] = generate_vectors(item["title"])
            treated_item["descriptionVector"] = generate_vectors(item["description"])
            # Store vectors in Redis
            redis_client.set(item_key, json.dumps({"titleVector": treated_item["titleVector"], "descriptionVector": treated_item["descriptionVector"]}))

        batched_treated_items.append(treated_item)

        if len(batched_treated_items) >= batch_size:

            print(f"Uploading batch of {len(batched_treated_items)} items ...")

            search_client.upload_documents(batched_treated_items)

            batched_treated_items.clear()

    if len(batched_treated_items) >= 0:

        print(f"Uploading final batch of {len(batched_treated_items)} items ...")
        search_client.upload_documents(batched_treated_items)

    print(
        f"Uploaded {len(items[:11])} documents to index {AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME}"
    )

def delete_search_index(name: str):
    print(f"Deleting search index {name}")
    index_client = SearchIndexClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        credential=azure_credential,
    )
    index_client.delete_index(name)

def generate_vectors(text):

    client = AzureOpenAI(
        api_key = get_openai_key(),  
        api_version = "2024-02-01",
        azure_endpoint = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com" 
    )

    response = client.embeddings.create(
        input = text,
        model = AZURE_OPENAI_DEPLOYMENT_NAME  # model = "deployment_name".
    )

    return response.data[0].embedding

def generate_text_embeddings(
        client: AzureOpenAI,
        text: any,
        openai_deployment_name = AZURE_OPENAI_DEPLOYMENT_NAME):
    
    response = client.embeddings.create(
        input = text,
        model = openai_deployment_name)

    print(f"generated {len(response.data)} embeddings")

    embeddings = np.array([item.embedding for item in response.data])

    return np.concatenate(embeddings).tolist()
    
def get_text_embeddings(
        redis_client,
        openai_client,
        text_property_names: list,
        vector_property_names: list,
        item,
        deployment_name: str):

    if (len(text_property_names) != len(vector_property_names)):
        raise Exception("The number of text property names must equal the number of vector property names") 

    item_key = f"{item["id"]}_{deployment_name}"

    if redis_client.exists(item_key):
        print(f"Document with id {item["id"]} already exists in Redis cache, retrieving vectors.")

        cached_item = json.loads(redis_client.get(item_key))

        for vector_property_name in vector_property_names:
            if vector_property_name in cached_item:
                item[vector_property_name] = cached_item[vector_property_name]
    else:
        print(f"Generating Azure OpenAI embeddings for {item["id"]} ...")

        redis_obj = {}

        for idx, text_property_name in enumerate(text_property_names):

            print(f"{idx} {text_property_name}")

            if text_property_name in item:

                text = item[text_property_name] if item[text_property_name] is str else " ".join(item[text_property_name])

                embeddings = generate_text_embeddings(openai_client, text, deployment_name)

                vector_property_name = vector_property_names[idx]

                item[vector_property_name] = embeddings

                redis_obj[vector_property_name] = embeddings

        # Store vectors in Redis
        redis_client.set(item_key, json.dumps(redis_obj))

def generate_azuresearch_id():
    id = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode("utf-8")
    if id[0] == "_":
        first_char = random.choice(string.ascii_letters + string.digits)
        id = first_char + id[1:]
    return id

def get_openai_key():

    if (not CACHE_KEY_CREATED_TIME in open_ai_token_cache) or open_ai_token_cache[CACHE_KEY_CREATED_TIME] + 300 < time.time():

        openai_token = azure_credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        )

        open_ai_token_cache[CACHE_KEY_CREATED_TIME] = time.time()
        open_ai_token_cache[CACHE_KEY_TOKEN_CRED] = openai_token
    else:
        openai_token = open_ai_token_cache[CACHE_KEY_TOKEN_CRED]

    return openai_token.token

def publish_results_db_schema():

    print('Ensuring postgres results db schema exists')

    try:
        db = Postgres(f"postgresql://{POSTGRES_SERVER_ADMIN_NAME}:{quote_plus(POSTGRES_SERVER_ADMIN_PASSWORD)}@{POSTGRES_SERVER_NAME}.postgres.database.azure.com:5432/postgres?sslmode=require")

        sql_file = open('./scripts/results_schema.sql','r')

        with db.get_cursor() as cursor:
            cursor.execute(sql_file.read())

    except Exception as e:
        logging.exception(str(e))
    

def create_search_index_nhs_combined_data() -> bool:
    index_client = SearchIndexClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        credential=azure_credential,
    )
    if AZURE_SEARCH_NHS_COMBINED_INDEX_NAME not in index_client.list_index_names():
        index = SearchIndex(
            name=AZURE_SEARCH_NHS_COMBINED_INDEX_NAME,
            fields=[
                SimpleField(
                    name="id",
                    type=SearchFieldDataType.String,
                    key=True,
                    filterable=True,
                    sortable=True,
                    facetable=True,
                ),
                SearchableField(name="title", type=SearchFieldDataType.String),
                SearchableField(name="description", type=SearchFieldDataType.String),
                SearchableField(name="short_descriptions", collection=True, type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
                SearchableField(name="content", collection=True, type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
                SearchField(
                    name="title_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=3072,
                    vector_search_profile_name="test-vector-profile"
                ),
                SearchField(
                    name="description_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=3072,
                    vector_search_profile_name="test-vector-profile"
                ),
                SearchField(
                    name="short_descriptions_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=3072,
                    vector_search_profile_name="test-vector-profile"
                ),
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=3072,
                    vector_search_profile_name="test-vector-profile"
                )
            ],
            vector_search=VectorSearch(
                algorithms=[ExhaustiveKnnAlgorithmConfiguration(name="testKnn")],
                profiles=[VectorSearchProfile(
                    name="test-vector-profile",
                    algorithm_configuration_name="testKnn")]
            ),
            semantic_search=SemanticSearch(
                configurations=[
                    SemanticConfiguration(
                        name="martin-test-semantic-config",
                        prioritized_fields=SemanticPrioritizedFields(
                            title_field=SemanticField(field_name="title"),
                            content_fields=[
                                SemanticField(field_name="description"),
                                SemanticField(field_name="short_descriptions")
                            ]
                        ),
                    )
                ]
            ),
        )
        print(f"Creating {AZURE_SEARCH_NHS_COMBINED_INDEX_NAME} search index")
        index_client.create_index(index)
        return True
    else:
        print(f"Search index {AZURE_SEARCH_NHS_COMBINED_INDEX_NAME} already exists")
        return False

def populate_search_index_nhs_combined_data():
    print(f"Populating search index {AZURE_SEARCH_NHS_COMBINED_INDEX_NAME} with documents")

    search_client = SearchClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        credential=azure_credential,
        index_name=AZURE_SEARCH_NHS_COMBINED_INDEX_NAME,
    )

    redis_client = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        ssl=True,
        decode_responses=True
    )

    openai_client = AzureOpenAI(
        api_key = get_openai_key(),  
        api_version = "2024-02-01",
        azure_endpoint = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com" 
    )

    with open("data/conditions_1.json", "r", encoding="utf-8") as file:
        conditions_items = json.load(file)

    with open("data/medicines_1.json", "r", encoding="utf-8") as file:
        medicines_items = json.load(file)

    items = conditions_items + medicines_items

    print(f"loaded {len(conditions_items)} conditions and {len(medicines_items)} medicines and combined into {len(items)} items")

    batched_treated_items = []
    batch_size = 12

    for item in items:

        treated_item = {
            "id": item["id"],
            "title": item["title"],
            "description": item["description"]
        }

        short_descriptions = []
        rich_text_content = []

        all_short_description_text = ""
        all_content = ""

        nbsp = u'\xa0'

        for c in item["content"]:

            short_description = c["value"]["short_description"]

            if len(short_description) > 0:
                short_descriptions.append(short_description)

                if len(all_short_description_text) == 0:
                    all_short_description_text = short_description
                else:
                    all_short_description_text += " " + short_description

            for inner_c in c["value"]["content"]:

                if inner_c["type"] == "richtext":
                    rich_text = inner_c["value"]

                    soup = BeautifulSoup(rich_text, 'html.parser')

                    # print(soup.prettify())

                    # specifically convert non breaking spaces to spaces
                    t2 = soup.get_text(separator=" ").replace('\u00a0', ' ').replace(nbsp, ' ').replace('  ', ' ').replace('"','\\"')

                    t3 = json.loads(f'"{t2}"')
                    
                    # print(t3)

                    rich_text_content.append(t3)

                    if len(all_content) == 0:
                        all_content = t3
                    else:
                        all_content += " " + t3

        print(f"{treated_item["id"]} has {len(short_descriptions)} short descriptions")

        if len(short_descriptions) > 0:
            treated_item["short_descriptions"] = short_descriptions

        if len(rich_text_content) > 0:
            treated_item["content"] = rich_text_content
        
        get_text_embeddings(
            redis_client,
            openai_client,
            text_property_names=["title", "description", "short_descriptions", "content"],
            vector_property_names=["title_vector", "description_vector", "short_descriptions_vector", "content_vector"],
            item=treated_item,
            deployment_name=AZURE_OPENAI_DEPLOYMENT_LARGE_NAME)

        batched_treated_items.append(treated_item)

        if len(batched_treated_items) >= batch_size:

            print(f"Uploading batch of {len(batched_treated_items)} items ...")

            search_client.upload_documents(batched_treated_items)

            batched_treated_items.clear()

    if len(batched_treated_items) > 0:

        print(f"Uploading final batch of {len(batched_treated_items)} items ...")
        search_client.upload_documents(batched_treated_items)

    print(f"Uploaded {len(items)} documents to index 'martin-test-index'")

def create_and_populate_nhs_combined_data_index():
    created = create_search_index_nhs_combined_data()
    if created:
        populate_search_index_nhs_combined_data()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Prepares the required Azure Cognitive Search indexes for the app",
    )
    parser.add_argument(
        "--recreate",
        required=False,
        action="store_true",
        help="Optional. Recreate all the ACS indexes",
    )
    args = parser.parse_args()

    # Use the current user identity to connect to Azure services
    azure_credential = DefaultAzureCredential(
        exclude_shared_token_cache_credential=True
    )

    # Create result db schema
    publish_results_db_schema()

    # Create NHS combined data set index
    if args.recreate:
        delete_search_index(AZURE_SEARCH_NHS_COMBINED_INDEX_NAME)
    create_and_populate_nhs_combined_data_index()

    # Create NHS conditions index
    if args.recreate:
        delete_search_index(AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME)
    create_and_populate_search_index_nhs_conditions()
 
    print("Completed successfully")
