from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase


def serialize_mongo_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    document["id"] = str(document.pop("_id"))
    return document


async def insert_one(db: AsyncIOMotorDatabase, collection_name: str, data: dict[str, Any]) -> str:
    result = await db[collection_name].insert_one(data)
    return str(result.inserted_id)


async def find_one(db: AsyncIOMotorDatabase, collection_name: str, query: dict[str, Any]) -> dict[str, Any] | None:
    document = await db[collection_name].find_one(query)
    return serialize_mongo_document(document)


async def find_by_id(db: AsyncIOMotorDatabase, collection_name: str, document_id: str) -> dict[str, Any] | None:
    document = await db[collection_name].find_one({"_id": ObjectId(document_id)})
    return serialize_mongo_document(document)


async def update_one(
    db: AsyncIOMotorDatabase,
    collection_name: str,
    query: dict[str, Any],
    data: dict[str, Any],
) -> int:
    result = await db[collection_name].update_one(query, {"$set": data})
    return result.modified_count


async def delete_one(db: AsyncIOMotorDatabase, collection_name: str, query: dict[str, Any]) -> int:
    result = await db[collection_name].delete_one(query)
    return result.deleted_count


async def get_collection(db: AsyncIOMotorDatabase, collection_name: str) -> AsyncIOMotorCollection:
    return db[collection_name]
