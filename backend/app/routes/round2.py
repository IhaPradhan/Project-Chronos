from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..services.gemini_service import ask_gemini
from ..services.round2_service import (
    get_files_for_team, get_file_by_id, get_team_evidence, get_team_case,
    get_team_state, reserve_ai_question, save_ai_response, submit_culprit,
)

router = APIRouter(prefix="/api/round2", tags=["Round 2"])


class AIQuestionRequest(BaseModel):
    team_id: int = Field(..., ge=1)
    question: str = Field(..., min_length=1, max_length=500)


class CulpritSubmissionRequest(BaseModel):
    team_id: int = Field(..., ge=1)
    culprit: str = Field(..., min_length=1, max_length=100)


@router.get("/files")
def get_files(team_id: int = Query(..., ge=1)):
    # TODO(auth): replace this compatibility lookup with the authenticated team context.
    team_fragments: list[str] = []
    return get_files_for_team(team_fragments)


@router.get("/files/{file_id}")
def get_file(file_id: str, team_id: int = Query(..., ge=1)):
    # TODO(auth): replace this compatibility lookup with the authenticated team context.
    team_fragments: list[str] = []
    file = get_file_by_id(file_id, team_fragments)
    if file is None:
        raise HTTPException(status_code=404, detail="File not found or access denied")
    return file


@router.get("/ai/status")
def ai_status(team_id: int = Query(..., ge=1)):
    state = get_team_state(team_id)
    return {"team_id": team_id, "questions_used": state["ai_questions"],
            "questions_remaining": max(0, 3 - state["ai_questions"]),
            "ai_points_remaining": state["ai_points"]}


@router.post("/ai/ask")
async def ai_ask(body: AIQuestionRequest):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail={"code": "empty_question", "message": "Question cannot be blank."})
    # The current evidence API is team-fragment based. Authentication must supply these fragments.
    team_fragments: list[str] = []
    evidence = get_team_evidence(body.team_id, team_fragments)
    if not evidence:
        raise HTTPException(status_code=403, detail={"code": "evidence_locked", "message": "Round 2 evidence is not unlocked."})
    reservation = reserve_ai_question(body.team_id)
    if reservation is None:
        state = get_team_state(body.team_id)
        raise HTTPException(status_code=429, detail={"code": "ai_limit_reached", "message": "No AI questions remain.",
            "questions_remaining": max(0, 3 - state["ai_questions"]), "ai_points_remaining": state["ai_points"]})
    question_number, points_charged, points_remaining = reservation
    case = get_team_case(body.team_id) or {}
    answer, fallback = await ask_gemini(question, evidence, case.get("culprit"))
    save_ai_response(body.team_id, question_number, question, answer, fallback)
    return {"team_id": body.team_id, "question_number": question_number,
            "answer": answer, "used_fallback": fallback,
            "points_charged": points_charged, "ai_points_remaining": points_remaining,
            "questions_remaining": 3 - question_number}


@router.post("/culprit/submit")
def culprit_submit(body: CulpritSubmissionRequest):
    result = submit_culprit(body.team_id, body.culprit.strip())
    error = result.get("error")
    if error == "case_not_configured":
        raise HTTPException(status_code=503, detail={"code": error, "message": "No answer key is configured for this team."})
    if error == "invalid_candidate":
        raise HTTPException(status_code=422, detail={"code": error, "message": "Select a valid candidate for this case."})
    if error == "already_submitted":
        raise HTTPException(status_code=409, detail={"code": error, "message": "A culprit has already been submitted."})
    state = get_team_state(body.team_id)
    return {"team_id": body.team_id, "submitted": True, "correct": result["correct"],
            "score_awarded": result["score_awarded"], "round2_score": result["round2_score"],
            "ai_points_remaining": state["ai_points"], "questions_used": state["ai_questions"]}
