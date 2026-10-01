from fastapi import APIRouter

from ..services.round1_service import get_round1_items, submit_answer

router = APIRouter()


@router.get("/items")
def get_items():
    return get_round1_items()


@router.post("/submit")
def submit(team_id: int, item_id: int, answer: str):
    result = submit_answer(team_id, item_id, answer)

    return result