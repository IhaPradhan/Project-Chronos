from fastapi import APIRouter

from ..services.round2_service import get_files_for_team

router = APIRouter(
    prefix="/api/round2",
    tags=["Round 2"]
)


@router.get("/files")
def get_files(team_id: int):
    # Get the team's fragments
    # Temporary: use an empty list until DB integration is finalized
    team_fragments = []

    # Get files and their locked/unlocked status
    return get_files_for_team(team_fragments)
