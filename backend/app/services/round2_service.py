"""Round 2 evidence access and server-side investigation state for Project CHRONOS.

The case answer is deliberately not part of any API response. Configure cases with
ROUND2_CASES_JSON (see API_CONTRACT.md) or populate CASES in the deployment layer.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

# Replace placeholder content with the approved, team-assigned evidence records.
# Keep the canonical records here/on the server; never accept evidence text from clients.
ROUND2_FILES: list[dict[str, Any]] = [
    {"id": "alpha", "filename": "PROJECT_ALPHA", "file_type": "LOG", "required_fragment": None,
     "content": "Project Alpha evidence will be added here."},
    {"id": "beta", "filename": "PROJECT_BETA", "file_type": "REPORT", "required_fragment": None,
     "content": "Project Beta evidence will be added here."},
    {"id": "gamma", "filename": "PROJECT_GAMMA", "file_type": "LOG", "required_fragment": None,
     "content": "Project Gamma evidence will be added here."},
]

# Example deployment value:
# {"101":{"culprit":"Sigma","candidates":["Omega","Sigma","Delta"]}}
def _load_cases() -> dict[str, dict[str, Any]]:
    raw = os.getenv("ROUND2_CASES_JSON", "{}").strip()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ROUND2_CASES_JSON must be valid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("ROUND2_CASES_JSON must be an object keyed by team ID")
    return value

CASES: dict[str, dict[str, Any]] = _load_cases()


def get_round2_files() -> list[dict[str, Any]]:
    return ROUND2_FILES


def is_file_unlocked(file: dict[str, Any], team_fragments: list[str]) -> bool:
    required = file.get("required_fragment")
    return required is None or required in team_fragments


def get_files_for_team(team_fragments: list[str]) -> list[dict[str, Any]]:
    return [{"id": f["id"], "filename": f["filename"], "file_type": f["file_type"],
             "unlocked": is_file_unlocked(f, team_fragments)} for f in ROUND2_FILES]


def get_file_by_id(file_id: str, team_fragments: list[str]) -> dict[str, Any] | None:
    for file in ROUND2_FILES:
        if file["id"] == file_id and is_file_unlocked(file, team_fragments):
            return dict(file)
    return None


def get_team_evidence(team_id: int | str, team_fragments: list[str]) -> list[dict[str, str]]:
    """Return only unlocked Alpha/Beta/Gamma evidence assigned to this team.

    A team case may provide an ``evidence`` object keyed by alpha/beta/gamma;
    otherwise the shared scaffold records are used until the evidence owner plugs
    in the final team-aware evidence provider.
    """
    allowed = {"alpha", "beta", "gamma"}
    case = get_team_case(team_id) or {}
    assigned = case.get("evidence")
    if isinstance(assigned, dict):
        result = []
        for file_id in ("alpha", "beta", "gamma"):
            item = assigned.get(file_id)
            if isinstance(item, dict) and isinstance(item.get("content"), str):
                result.append({"id": file_id,
                               "filename": str(item.get("filename") or file_id.upper()),
                               "content": item["content"]})
            elif isinstance(item, str):
                result.append({"id": file_id, "filename": file_id.upper(), "content": item})
        return result
    result = []
    for file in ROUND2_FILES:
        if file["id"] in allowed and is_file_unlocked(file, team_fragments):
            result.append({"id": file["id"], "filename": file["filename"], "content": file["content"]})
    return result


def get_team_case(team_id: int | str) -> dict[str, Any] | None:
    case = CASES.get(str(team_id))
    return case if isinstance(case, dict) else None


DB_PATH = Path(os.getenv("CHRONOS_ROUND2_DB", "chronos_round2.sqlite3"))


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=2.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=2000")
    con.execute("""CREATE TABLE IF NOT EXISTS round2_state (
        team_id TEXT PRIMARY KEY,
        ai_questions INTEGER NOT NULL DEFAULT 0,
        ai_points INTEGER NOT NULL DEFAULT 20,
        culprit_submitted INTEGER NOT NULL DEFAULT 0,
        submitted_culprit TEXT,
        culprit_correct INTEGER,
        culprit_score INTEGER NOT NULL DEFAULT 0,
        completed_at TEXT,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS round2_ai_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id TEXT NOT NULL,
        question_number INTEGER NOT NULL,
        question TEXT NOT NULL,
        response TEXT NOT NULL,
        used_fallback INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    return con


def get_team_state(team_id: int | str) -> dict[str, Any]:
    with _connect() as con:
        con.execute("INSERT OR IGNORE INTO round2_state(team_id) VALUES (?)", (str(team_id),))
        row = con.execute("SELECT * FROM round2_state WHERE team_id=?", (str(team_id),)).fetchone()
        return dict(row)


def reserve_ai_question(team_id: int | str) -> tuple[int, int, int] | None:
    """Atomically charge a question before calling Gemini; returns (number, cost, balance)."""
    with _connect() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("INSERT OR IGNORE INTO round2_state(team_id) VALUES (?)", (str(team_id),))
        row = con.execute("SELECT ai_questions, ai_points FROM round2_state WHERE team_id=?",
                          (str(team_id),)).fetchone()
        count, points = int(row[0]), int(row[1])
        if count >= 3:
            con.rollback()
            return None
        cost = (5, 5, 10)[count]
        if points < cost:
            con.rollback()
            return None
        count += 1
        points -= cost
        con.execute("UPDATE round2_state SET ai_questions=?, ai_points=?, updated_at=CURRENT_TIMESTAMP WHERE team_id=?",
                    (count, points, str(team_id)))
        con.commit()
        return count, cost, points


def save_ai_response(team_id: int | str, question_number: int, question: str,
                     response: str, used_fallback: bool) -> None:
    with _connect() as con:
        con.execute("INSERT INTO round2_ai_log(team_id,question_number,question,response,used_fallback) VALUES (?,?,?,?,?)",
                    (str(team_id), question_number, question, response, int(used_fallback)))


def submit_culprit(team_id: int | str, culprit: str) -> dict[str, Any]:
    """Validate and persist a team's one-time Round 2 culprit submission."""
    case = get_team_case(team_id)
    if not case or not isinstance(case.get("culprit"), str) or not case["culprit"].strip():
        return {"error": "case_not_configured"}
    expected = case["culprit"].strip().casefold()
    candidates = case.get("candidates", [])
    if candidates and culprit.casefold() not in {str(c).casefold() for c in candidates}:
        return {"error": "invalid_candidate"}
    with _connect() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("INSERT OR IGNORE INTO round2_state(team_id) VALUES (?)", (str(team_id),))
        row = con.execute("SELECT culprit_submitted FROM round2_state WHERE team_id=?", (str(team_id),)).fetchone()
        if row[0]:
            con.rollback()
            return {"error": "already_submitted"}
        correct = culprit.strip().casefold() == expected
        score = 30 if correct else 0
        con.execute("""UPDATE round2_state SET culprit_submitted=1, submitted_culprit=?,
            culprit_correct=?, culprit_score=?, completed_at=CURRENT_TIMESTAMP,
            updated_at=CURRENT_TIMESTAMP WHERE team_id=?""",
                    (culprit.strip(), int(correct), score, str(team_id)))
        con.commit()
    return {"correct": correct, "score_awarded": score, "round2_score": score}
