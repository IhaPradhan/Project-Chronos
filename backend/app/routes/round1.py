from fastapi import APIRouter

from ..services.round1_service import (
    get_round1_items,
    submit_answer,
    finish_round1
)

router = APIRouter()


@router.get("/items")
def get_items(team_id: int):
    """
    Get the 25 Round 1 images assigned to the team.
    """
    return get_round1_items(team_id)


@router.post("/submit")
def submit(team_id: int, item_id: int, answer: str):
    """
    Submit a classification answer for one image.
    """
    return submit_answer(
        team_id,
        item_id,
        answer
    )


@router.post("/finish")
def finish(team_id: int):
    """
    Finish/check Round 1.

    The backend verifies that all assigned
    items have been submitted before allowing
    the team to proceed to Round 2.
    """
    return finish_round1(team_id)