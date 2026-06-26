from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query

from app.utils.es import get_es_client, search_courses

router = APIRouter()


@router.get("/courses")
async def search_course_list(
    keyword: str | None = None,
    category: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    sort: Literal["sales_desc", "price_asc", "price_desc", "rating_desc", "newest"] = "sales_desc",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    es = get_es_client()
    try:
        result = await search_courses(es, keyword, category, min_price, max_price, sort, page, size)
    finally:
        await es.close()

    hits = result["hits"]["hits"]
    total = result["hits"]["total"]["value"] if isinstance(result["hits"]["total"], dict) else result["hits"]["total"]
    items = []
    for hit in hits:
        source = hit["_source"]
        items.append(
            {
                "course_id": source["course_id"],
                "title": source["title"],
                "cover": source.get("cover"),
                "price": source.get("price_min", 0.0),
                "teacher_name": source.get("teacher_name", ""),
                "sales": source.get("sales", 0),
                "highlight": hit.get("highlight", {}).get("title", []),
            }
        )
    return {"total": total, "page": page, "size": size, "items": items}
