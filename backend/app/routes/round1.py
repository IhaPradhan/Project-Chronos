from fastapi import APIRouter

from ..services.round1_service import get_round1_items, submit_answer

router = APIRouter()


@router.get("/items")
def get_items():
    return get_round1_items()


@router.post("/submit")
def submit(item_id: str, answer: str):
    result = submit_answer(item_id, answer)

    if result is None:
        return {"error": "Invalid item_id"}

    return result