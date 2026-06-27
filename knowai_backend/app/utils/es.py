from typing import Any

from elasticsearch import AsyncElasticsearch, NotFoundError

from app.config import settings

COURSES_INDEX = "courses"

COURSES_INDEX_MAPPING: dict[str, Any] = {
    "settings": {
        "analysis": {
            "analyzer": {
                "smart_text": {
                    "type": "standard",
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "course_id": {"type": "integer"},
            "title": {
                "type": "text",
                "analyzer": "standard",
                "search_analyzer": "standard",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "description": {"type": "text", "analyzer": "standard"},
            "cover": {"type": "keyword"},
            "category": {"type": "keyword"},
            "teacher_name": {"type": "text", "analyzer": "standard"},
            "price_min": {"type": "float"},
            "sales": {"type": "integer"},
            "rating": {"type": "float"},
            "status": {"type": "keyword"},
            "created_at": {"type": "date"},
        }
    },
}


def get_es_client() -> AsyncElasticsearch:
    return AsyncElasticsearch(settings.elasticsearch_url)


async def ensure_courses_index(es: AsyncElasticsearch) -> None:
    if not await es.indices.exists(index=COURSES_INDEX):
        await es.indices.create(index=COURSES_INDEX, body=COURSES_INDEX_MAPPING)


async def index_course_document(es: AsyncElasticsearch, document: dict[str, Any]) -> None:
    await ensure_courses_index(es)
    await es.index(index=COURSES_INDEX, id=document["course_id"], document=document)


async def delete_course_document(es: AsyncElasticsearch, course_id: int) -> None:
    try:
        await es.delete(index=COURSES_INDEX, id=course_id)
    except NotFoundError:
        return


async def search_courses(
    es: AsyncElasticsearch,
    keyword: str | None,
    category: str | None,
    min_price: float | None,
    max_price: float | None,
    sort: str,
    page: int,
    size: int,
) -> dict[str, Any]:
    filters: list[dict[str, Any]] = [{"term": {"status": "published"}}]
    if category:
        filters.append({"term": {"category": category}})
    price_range: dict[str, float] = {}
    if min_price is not None:
        price_range["gte"] = min_price
    if max_price is not None:
        price_range["lte"] = max_price
    if price_range:
        filters.append({"range": {"price_min": price_range}})

    must: list[dict[str, Any]] = []
    if keyword:
        must.append(
            {
                "multi_match": {
                    "query": keyword,
                    "fields": ["title^3", "description", "teacher_name"],
                }
            }
        )

    body: dict[str, Any] = {
        "query": {"bool": {"filter": filters, "must": must or [{"match_all": {}}]}},
        "from": (page - 1) * size,
        "size": size,
        "highlight": {"fields": {"title": {}}},
    }

    sort_map: dict[str, list[dict[str, dict[str, str]]]] = {
        "sales_desc": [{"sales": {"order": "desc"}}],
        "price_asc": [{"price_min": {"order": "asc"}}],
        "price_desc": [{"price_min": {"order": "desc"}}],
        "rating_desc": [{"rating": {"order": "desc"}}],
        "newest": [{"created_at": {"order": "desc"}}],
    }
    body["sort"] = sort_map.get(sort, sort_map["sales_desc"])
    return await es.search(index=COURSES_INDEX, body=body)
