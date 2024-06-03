import argparse
import base64
import os
import json
import random
import string
import time
import requests
import uuid
import wget
import pandas as pd
# import zipfile

import openai
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from azure.storage.blob import BlobServiceClient
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
)

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
AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME = os.environ.get("AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME")
AZURE_STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT")
AZURE_STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER")

open_ai_token_cache = {}
CACHE_KEY_TOKEN_CRED = "openai_token_cred"
CACHE_KEY_CREATED_TIME = "created_time"


def create_and_populate_search_index_text():
    created = create_search_index_text()
    if created:
        populate_search_index_text()


def create_search_index_text():
    print(f"Ensuring search index {AZURE_SEARCH_TEXT_INDEX_NAME} exists")
    index_client = SearchIndexClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        credential=azure_credential,
    )
    if AZURE_SEARCH_TEXT_INDEX_NAME not in index_client.list_index_names():
        index = SearchIndex(
            name=AZURE_SEARCH_TEXT_INDEX_NAME,
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
                SearchableField(name="content", type=SearchFieldDataType.String),
                SearchableField(
                    name="category", type=SearchFieldDataType.String, filterable=True
                ),
                SearchField(
                    name="titleVector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,
                    vector_search_configuration="my-vector-config",
                ),
                SearchField(
                    name="contentVector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,
                    vector_search_configuration="my-vector-config",
                ),
            ],
            vector_search=VectorSearch(
                algorithm_configurations=[
                    HnswAlgorithmConfiguration(
                        name="my-vector-config",
                        parameters=HnswParameters(
                            m=4, ef_construction=400, ef_search=500, metric="cosine"
                        ),
                    )
                ]
            ),
            semantic_search=SemanticSearch(
                configurations=[
                    SemanticConfiguration(
                        name="my-semantic-config",
                        prioritized_fields=SemanticPrioritizedFields(
                            title_field=SemanticField(field_name="title"),
                            content_fields=[
                                SemanticField(field_name="content")
                            ],
                            keywords_fields=[
                                SemanticField(field_name="category")
                            ],
                        ),
                    )
                ]
            ),
        )
        print(f"Creating {AZURE_SEARCH_TEXT_INDEX_NAME} search index")
        index_client.create_index(index)
        return True
    else:
        print(f"Search index {AZURE_SEARCH_TEXT_INDEX_NAME} already exists")
        return False

def populate_search_index_text():
    print(f"Populating search index {AZURE_SEARCH_TEXT_INDEX_NAME} with documents")

    with open("data/text-sample.json", "r", encoding="utf-8") as file:
        input_data = json.load(file)

    print(f"Generating Azure OpenAI embeddings...")
    for item in input_data:
        item["titleVector"] = generate_text_embeddings(item["title"])
        item["contentVector"] = generate_text_embeddings(item["content"])

    print(f"Uploading documents...")
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        credential=azure_credential,
        index_name=AZURE_SEARCH_TEXT_INDEX_NAME,
    )
    search_client.upload_documents(input_data)
    print(
        f"Uploaded {len(input_data)} documents to index {AZURE_SEARCH_TEXT_INDEX_NAME}"
    )

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

    print(f"Generating Azure OpenAI embeddings...")
    for item in items:
        item["titleVector"] = generate_text_embeddings(item["title"])
        item["descriptionVector"] = generate_text_embeddings(item["search_description"])

    print(f"Uploading items...")
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        credential=azure_credential,
        index_name=AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME,
    )

    batch_size = 100  
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]  
  
    for batch in batches:  
        search_client.upload_documents(batch) 
    print(
        f"Uploaded {len(items)} documents to index {AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME}"
    )

def delete_search_index(name: str):
    print(f"Deleting search index {name}")
    index_client = SearchIndexClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        credential=azure_credential,
    )
    index_client.delete_index(name)


def before_retry_sleep(retry_state):
    print(
        "Rate limited on the Azure OpenAI embeddings API, sleeping before retrying..."
    )

@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(15),
    before_sleep=before_retry_sleep,
)
def generate_text_embeddings(text):
    refresh_openai_token()
    response = openai.Embedding.create(input=text, engine=AZURE_OPENAI_DEPLOYMENT_NAME)
    return response["data"][0]["embedding"]


# refresh open ai token every 5 minutes
def refresh_openai_token():
    if open_ai_token_cache[CACHE_KEY_CREATED_TIME] + 300 < time.time():
        token_cred = open_ai_token_cache[CACHE_KEY_TOKEN_CRED]
        openai.api_key = token_cred.get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token
        open_ai_token_cache[CACHE_KEY_CREATED_TIME] = time.time()


def generate_azuresearch_id():
    id = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode("utf-8")
    if id[0] == "_":
        first_char = random.choice(string.ascii_letters + string.digits)
        id = first_char + id[1:]
    return id


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

    # Used by the OpenAI SDK
    openai.api_type = "azure"
    openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
    openai.api_version = "2023-05-15"
    openai.api_type = "azure_ad"
    openai_token = azure_credential.get_token(
        "https://cognitiveservices.azure.com/.default"
    )
    openai.api_key = openai_token.token
    open_ai_token_cache[CACHE_KEY_CREATED_TIME] = time.time()
    open_ai_token_cache[CACHE_KEY_TOKEN_CRED] = azure_credential

    # Create text index
    if args.recreate:
        delete_search_index(AZURE_SEARCH_TEXT_INDEX_NAME)
    create_and_populate_search_index_text()

    # Create NHS conditions index
    if args.recreate:
        delete_search_index(AZURE_SEARCH_NHS_CONDITIONS_INDEX_NAME)
    create_and_populate_search_index_nhs_conditions()
 
    print("Completed successfully")
