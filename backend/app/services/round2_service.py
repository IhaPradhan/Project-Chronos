from datetime import datetime, timedelta

from ..database.connection import get_connection


AI_QUESTION_COSTS = [5.0, 5.0, 10.0]
MAX_AI_QUESTIONS = 3
STARTING_AI_POINTS = 20.0
CULPRIT_POINTS = 30.0


def _get_team_case(connection, team_id: int):
    """Get the case assigned to this team, assigning the least-used case if needed."""

    row = connection.execute(
        """
        SELECT
            c.case_id,
            c.case_code,
            c.archetype,
            c.incident,
            c.culprit,
            tc.assigned_at
        FROM round2_team_cases tc
        JOIN round2_cases c
            ON c.case_id = tc.case_id
        WHERE tc.team_id = ?
        LIMIT 1
        """,
        (team_id,),
    ).fetchone()

    if row:
        return row

    row = connection.execute(
        """
        SELECT
            c.case_id,
            c.case_code,
            c.archetype,
            c.incident,
            c.culprit
        FROM round2_cases c
        LEFT JOIN round2_team_cases tc
            ON tc.case_id = c.case_id
        GROUP BY
            c.case_id,
            c.case_code,
            c.archetype,
            c.incident,
            c.culprit
        ORDER BY
            COUNT(tc.id),
            c.case_id
        LIMIT 1
        """
    ).fetchone()

    if row is None:
        return None

    connection.execute(
        """
        INSERT INTO round2_team_cases (team_id, case_id)
        VALUES (?, ?)
        """,
        (team_id, row["case_id"]),
    )

    connection.commit()

    return connection.execute(
        """
        SELECT
            c.case_id,
            c.case_code,
            c.archetype,
            c.incident,
            c.culprit,
            tc.assigned_at
        FROM round2_team_cases tc
        JOIN round2_cases c
            ON c.case_id = tc.case_id
        WHERE tc.team_id = ?
        LIMIT 1
        """,
        (team_id,),
    ).fetchone()


def get_team_case(team_id: int):
    connection = get_connection()

    try:
        return _get_team_case(connection, team_id)

    finally:
        connection.close()


def get_team_evidence(team_id: int):
    connection = get_connection()

    try:
        case = _get_team_case(connection, team_id)

        if case is None:
            return []

        rows = connection.execute(
            """
            SELECT
                file_id,
                timeline_tag,
                filename,
                content_text
            FROM round2_case_files
            WHERE case_id = ?
            ORDER BY
                CASE timeline_tag
                    WHEN 'past' THEN 1
                    WHEN 'present' THEN 2
                    WHEN 'future' THEN 3
                    ELSE 4
                END,
                file_id
            """,
            (case["case_id"],),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def get_round2_files():
    """Compatibility helper: return all case evidence files."""

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                file_id,
                case_id,
                timeline_tag,
                filename,
                content_text
            FROM round2_case_files
            ORDER BY case_id, file_id
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def get_files_for_team(team_id: int):
    return get_team_evidence(team_id)


def get_file_by_id(file_id: str, team_id: int):
    connection = get_connection()

    try:
        case = _get_team_case(connection, team_id)

        if case is None:
            return None

        row = connection.execute(
            """
            SELECT
                file_id,
                timeline_tag,
                filename,
                content_text
            FROM round2_case_files
            WHERE case_id = ?
              AND file_id = ?
            LIMIT 1
            """,
            (case["case_id"], file_id),
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()


def get_team_suspects(team_id: int):
    connection = get_connection()

    try:
        case = _get_team_case(connection, team_id)

        if case is None:
            return []

        rows = connection.execute(
            """
            SELECT
                suspect_name,
                user_id,
                role
            FROM round2_case_suspects
            WHERE case_id = ?
            ORDER BY id
            """,
            (case["case_id"],),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def get_team_state(team_id: int):
    connection = get_connection()

    try:
        team = connection.execute(
            """
            SELECT
                id AS team_id,
                team_name,
                current_state,
                round2_score,
                round2_started_at,
                round2_completed_at
            FROM teams
            WHERE id = ?
            """,
            (team_id,),
        ).fetchone()

        if team is None:
            return None

        chat_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM round2_chat_messages
            WHERE team_id = ?
            """,
            (team_id,),
        ).fetchone()[0]

        points_spent = connection.execute(
            """
            SELECT COALESCE(SUM(points_deducted), 0)
            FROM round2_chat_messages
            WHERE team_id = ?
            """,
            (team_id,),
        ).fetchone()[0]

        submission = connection.execute(
            """
            SELECT
                suspect_identified,
                is_correct,
                points_awarded,
                ai_points_remaining,
                round2_total_score,
                submitted_at
            FROM round2_submissions
            WHERE team_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (team_id,),
        ).fetchone()

        return {
            "team_id": team["team_id"],
            "team_name": team["team_name"],
            "current_state": team["current_state"],
            "r2_score": team["round2_score"] or 0.0,
            "r2_start_time": team["round2_started_at"],
            "r2_end_time": (
                (
                    datetime.strptime(
                        team["round2_started_at"],
                        "%Y-%m-%d %H:%M:%S",
                    )
                    + timedelta(minutes=20)
                ).strftime("%Y-%m-%d %H:%M:%S")
                if team["round2_started_at"]
                else None
            ),
            "ai_questions_used": chat_count,
            "ai_questions_remaining": max(
                0,
                MAX_AI_QUESTIONS - chat_count,
            ),
            "ai_points_remaining": max(
                0.0,
                STARTING_AI_POINTS - float(points_spent),
            ),
            "submission": dict(submission) if submission else None,
        }

    finally:
        connection.close()


def start_round2(team_id: int):
    connection = get_connection()

    try:
        team = connection.execute(
            """
            SELECT
                id AS team_id,
                current_state,
                round2_started_at,
                round2_completed_at
            FROM teams
            WHERE id = ?
            """,
            (team_id,),
        ).fetchone()

        if team is None:
            return None

        if team["current_state"] == "ROUND_2_COMPLETED":
            return {
                "success": False,
                "error": "Round 2 has already been completed.",
            }

        # already active — do not reset the timer
        if team["current_state"] == "ROUND_2_ACTIVE":
            return {
                "success": True,
                "already_started": True,
                "r2_start_time": team["round2_started_at"],
                "r2_end_time": (
                    (
                        datetime.strptime(
                            team["round2_started_at"],
                            "%Y-%m-%d %H:%M:%S",
                        )
                        + timedelta(minutes=20)
                    ).strftime("%Y-%m-%d %H:%M:%S")
                    if team["round2_started_at"]
                    else None
                ),
            }

        connection.execute(
            """
            UPDATE teams
            SET
                current_state = 'ROUND_2_ACTIVE',
                round2_started_at = CURRENT_TIMESTAMP,
                round2_completed_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (team_id,),
        )

        connection.commit()

        row = connection.execute(
            """
            SELECT
                round2_started_at,
                round2_completed_at
            FROM teams
            WHERE id = ?
            """,
            (team_id,),
        ).fetchone()

        r2_start_time = row["round2_started_at"]
        r2_end_time = (
            (
                datetime.strptime(
                    r2_start_time,
                    "%Y-%m-%d %H:%M:%S",
                )
                + timedelta(minutes=20)
            ).strftime("%Y-%m-%d %H:%M:%S")
            if r2_start_time
            else None
        )

        return {
            "success": True,
            "already_started": False,
            "r2_start_time": r2_start_time,
            "r2_end_time": r2_end_time,
        }

    finally:
        connection.close()


def reserve_ai_question(team_id: int):
    state = get_team_state(team_id)

    if state is None:
        return None

    questions_used = state["ai_questions_used"]

    if questions_used >= MAX_AI_QUESTIONS:
        return {
            "allowed": False,
            "reason": "AI question limit reached.",
            "question_number": questions_used + 1,
            "points_deducted": 0.0,
            "points_remaining": state["ai_points_remaining"],
        }

    cost = AI_QUESTION_COSTS[questions_used]

    if state["ai_points_remaining"] < cost:
        return {
            "allowed": False,
            "reason": "Not enough AI points remaining.",
            "question_number": questions_used + 1,
            "points_deducted": 0.0,
            "points_remaining": state["ai_points_remaining"],
        }

    return {
        "allowed": True,
        "reason": None,
        "question_number": questions_used + 1,
        "points_deducted": cost,
        "points_remaining": state["ai_points_remaining"] - cost,
    }


def save_ai_response(
    team_id: int,
    question_number: int,
    user_prompt: str,
    ai_response: str,
    points_deducted: float,
):
    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO round2_chat_messages (
                team_id,
                question_number,
                user_prompt,
                ai_response,
                points_deducted
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                team_id,
                question_number,
                user_prompt,
                ai_response,
                points_deducted,
            ),
        )

        connection.commit()

    finally:
        connection.close()


def get_conversation(team_id: int):
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                question_number,
                user_prompt,
                ai_response,
                points_deducted,
                created_at
            FROM round2_chat_messages
            WHERE team_id = ?
            ORDER BY question_number
            """,
            (team_id,),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def submit_culprit(team_id: int, suspect: str):
    connection = get_connection()

    try:
        case = _get_team_case(connection, team_id)

        if case is None:
            return {
                "success": False,
                "error": "No Round 2 case assigned.",
            }

        existing = connection.execute(
            """
            SELECT id
            FROM round2_submissions
            WHERE team_id = ?
            LIMIT 1
            """,
            (team_id,),
        ).fetchone()

        if existing:
            return {
                "success": False,
                "error": "Round 2 submission already made.",
            }

        suspect_row = connection.execute(
            """
            SELECT suspect_name
            FROM round2_case_suspects
            WHERE case_id = ?
              AND LOWER(suspect_name) = LOWER(?)
            LIMIT 1
            """,
            (case["case_id"], suspect),
        ).fetchone()

        if suspect_row is None:
            return {
                "success": False,
                "error": "Invalid suspect.",
            }

        selected_suspect = suspect_row["suspect_name"]

        is_correct = (
            selected_suspect.strip().lower()
            == case["culprit"].strip().lower()
        )

        culprit_points = CULPRIT_POINTS if is_correct else 0.0

        chat_points = connection.execute(
            """
            SELECT COALESCE(SUM(points_deducted), 0)
            FROM round2_chat_messages
            WHERE team_id = ?
            """,
            (team_id,),
        ).fetchone()[0]

        ai_points_remaining = max(
            0.0,
            STARTING_AI_POINTS - float(chat_points),
        )

        round2_total_score = culprit_points + ai_points_remaining

        connection.execute(
            """
            INSERT INTO round2_submissions (
                team_id,
                suspect_identified,
                is_correct,
                points_awarded,
                ai_points_remaining,
                round2_total_score
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                team_id,
                selected_suspect,
                int(is_correct),
                culprit_points,
                ai_points_remaining,
                round2_total_score,
            ),
        )

        connection.execute(
            """
            UPDATE teams
            SET
                round2_score = ?,
                current_state = 'ROUND_2_COMPLETED',
                round2_completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                round2_total_score,
                team_id,
            ),
        )

        connection.commit()

        return {
            "success": True,
            "submitted": True,
        }

    finally:
        connection.close()