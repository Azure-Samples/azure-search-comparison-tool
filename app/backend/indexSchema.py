from azure.search.documents.indexes.aio import SearchIndexClient

class IndexSchema:
    def __init__(self, index_client: SearchIndexClient, index_name: str):
        self.index_client = index_client
        self.index_name = index_name

    async def get_efsearch(self):
        index_schema = await self.index_client.get_index(self.index_name)
        return index_schema.vector_search.algorithms[0].parameters.ef_search

    async def update_efsearch(self, ef_search: int):
        index_schema = await self.index_client.get_index(self.index_name)
        index_schema.vector_search.algorithms[0].parameters.ef_search = ef_search
        await self.index_client.create_or_update_index(index_schema)
        updated_index_schema = await self.index_client.get_index(self.index_name)
        return updated_index_schema.vector_search.algorithms[0].parameters.ef_search