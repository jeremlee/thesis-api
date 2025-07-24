from pymongo import MongoClient
import asyncio

from app.config import get_settings
from app.executor import _executor


class MongoDBService:
    def __init__(self, uri: str, db_name: str):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

    async def insert_document(self, collection_name: str, document: dict):
        return await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: self.db[collection_name].insert_one(document).inserted_id,
        )

    async def find_document(self, collection_name: str, query: dict):
        return await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: self.db[collection_name].find_one(query),
        )

    async def update_document(
        self, collection_name: str, query: dict, update: dict
    ) -> int:
        return await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: self.db[collection_name]
            .update_one(query, {"$set": update})
            .modified_count,
        )

    async def delete_document(self, collection_name: str, query: dict) -> int:
        return await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: self.db[collection_name].delete_one(query).deleted_count,
        )

    async def insert_many_documents(self, collection_name: str, documents: list):
        return await asyncio.get_running_loop().run_in_executor(
            _executor,
            lambda: self.db[collection_name].insert_many(documents).inserted_ids,
        )


settings = get_settings()
mongdb_service = MongoDBService(
    uri=settings.mongodb_uri, db_name=settings.database_name
)
