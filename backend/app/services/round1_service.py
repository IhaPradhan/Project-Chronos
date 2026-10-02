from ..database.connection import get_connection
import secrets
import string


ROUND1_CLUE = (
    "The timeline was not broken at the point of failure. "
    "Find the system that changed first."
)


def generate_auth_code():
    """
    Generate a unique 6-character authentication code.
    """
    characters = string.ascii_uppercase + string.digits

    connection = get_connection()

    try:
        cursor = connection.cursor()

        while True:
            code = ''.join(
                secrets.choice(characters)
                for _ in range(6)
            )

            cursor.execute("""
                SELECT id
                FROM teams
                WHERE round1_auth_code = ?
            """, (code,))

            if cursor.fetchone() is None:
                return code

    finally:
        connection.close()


def get_round1_items(team_id):
    """
    Get the 25 items assigned to a team.

    If the team has no assignment yet:
    - Select 1 random PAST item
    - Select 1 random PRESENT item
    - Select 1 random FUTURE item
    - Select 22 additional random items
    - Save the assignment permanently
    - Start the Round 1 timer

    If the team already has an assignment:
    - Return the same 25 items
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Check that the team exists
        cursor.execute("""
            SELECT id, current_state
            FROM teams
            WHERE id = ?
        """, (team_id,))

        team = cursor.fetchone()

        if team is None:
            return {
                "error": "Invalid team_id."
            }

        # Check whether this team already has assigned items
        cursor.execute("""
            SELECT COUNT(*)
            FROM round1_team_items
            WHERE team_id = ?
        """, (team_id,))

        assigned_count = cursor.fetchone()[0]

        # ---------------------------------------------------------
        # CREATE NEW ASSIGNMENT
        # ---------------------------------------------------------
        if assigned_count == 0:

            # Get one random item from each era
            cursor.execute("""
                SELECT item_id
                FROM round1_items
                WHERE is_active = 1
                  AND correct_era = 'PAST'
                ORDER BY RANDOM()
                LIMIT 1
            """)
            past_item = cursor.fetchone()

            cursor.execute("""
                SELECT item_id
                FROM round1_items
                WHERE is_active = 1
                  AND correct_era = 'PRESENT'
                ORDER BY RANDOM()
                LIMIT 1
            """)
            present_item = cursor.fetchone()

            cursor.execute("""
                SELECT item_id
                FROM round1_items
                WHERE is_active = 1
                  AND correct_era = 'FUTURE'
                ORDER BY RANDOM()
                LIMIT 1
            """)
            future_item = cursor.fetchone()

            if not past_item or not present_item or not future_item:
                return {
                    "error": "Not enough items available from all three eras."
                }

            # Store the guaranteed items
            guaranteed_items = [
                past_item["item_id"],
                present_item["item_id"],
                future_item["item_id"]
            ]

            for item_id in guaranteed_items:
                cursor.execute("""
                    INSERT INTO round1_team_items
                    (team_id, item_id)
                    VALUES (?, ?)
                """, (team_id, item_id))

            # Select remaining 22 random items
            cursor.execute("""
                SELECT item_id
                FROM round1_items
                WHERE is_active = 1
                  AND item_id NOT IN (?, ?, ?)
                ORDER BY RANDOM()
                LIMIT 22
            """, (
                guaranteed_items[0],
                guaranteed_items[1],
                guaranteed_items[2]
            ))

            remaining_items = cursor.fetchall()

            # Make sure we actually obtained 22 more items
            if len(remaining_items) != 22:
                connection.rollback()

                return {
                    "error": "Not enough active Round 1 items to create a set of 25."
                }

            for row in remaining_items:
                cursor.execute("""
                    INSERT INTO round1_team_items
                    (team_id, item_id)
                    VALUES (?, ?)
                """, (team_id, row["item_id"]))

            # Start Round 1 only after successful assignment
            cursor.execute("""
                UPDATE teams
                SET current_state = 'ROUND1_ACTIVE',
                    round1_started_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (team_id,))

            connection.commit()

        # ---------------------------------------------------------
        # RETURN ASSIGNED ITEMS
        # ---------------------------------------------------------

        cursor.execute("""
            SELECT r.item_id, r.image_path
            FROM round1_items r
            INNER JOIN round1_team_items t
                ON r.item_id = t.item_id
            WHERE t.team_id = ?
              AND r.is_active = 1
            ORDER BY RANDOM()
        """, (team_id,))

        rows = cursor.fetchall()

        return [
            {
                "id": row["item_id"],
                "image": row["image_path"]
            }
            for row in rows
        ]

    finally:
        connection.close()


def submit_answer(team_id, item_id, answer):
    """
    Submit one classification answer for a Round 1 item.

    Correct answer  -> +2
    Wrong answer    -> -1

    When all 25 assigned items are submitted:
    - Round 1 is completed
    - Completion timestamp is stored
    - Authentication code is generated
    - Final clue is returned
    - Team can proceed to Round 2
    """

    allowed_categories = {
        "PAST",
        "PRESENT",
        "FUTURE"
    }

    answer = answer.upper().strip()

    # Validate category
    if answer not in allowed_categories:
        return {
            "error": "Invalid category. Use PAST, PRESENT, or FUTURE."
        }

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ---------------------------------------------------------
        # CHECK TEAM
        # ---------------------------------------------------------

        cursor.execute("""
            SELECT id, current_state
            FROM teams
            WHERE id = ?
        """, (team_id,))

        team = cursor.fetchone()

        if team is None:
            return {
                "error": "Invalid team_id."
            }

        # ---------------------------------------------------------
        # CHECK ASSIGNED ITEM
        # ---------------------------------------------------------

        cursor.execute("""
            SELECT item_id
            FROM round1_team_items
            WHERE team_id = ?
              AND item_id = ?
        """, (team_id, item_id))

        assigned_item = cursor.fetchone()

        if assigned_item is None:
            return {
                "error": "This item is not assigned to this team."
            }

        # ---------------------------------------------------------
        # CHECK ITEM
        # ---------------------------------------------------------

        cursor.execute("""
            SELECT
                item_id,
                correct_era,
                points_positive,
                points_negative
            FROM round1_items
            WHERE item_id = ?
              AND is_active = 1
        """, (item_id,))

        item = cursor.fetchone()

        if item is None:
            return {
                "error": "Invalid item_id."
            }

        # ---------------------------------------------------------
        # PREVENT DUPLICATE SUBMISSION
        # ---------------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM round1_submissions
            WHERE team_id = ?
              AND item_id = ?
        """, (team_id, item_id))

        existing_submission = cursor.fetchone()

        if existing_submission is not None:
            return {
                "error": "This item has already been submitted."
            }

        # ---------------------------------------------------------
        # CHECK ANSWER
        # ---------------------------------------------------------

        is_correct = answer == item["correct_era"]

        if is_correct:
            points = item["points_positive"]
        else:
            points = -item["points_negative"]

        # ---------------------------------------------------------
        # SAVE SUBMISSION
        # ---------------------------------------------------------

        cursor.execute("""
            INSERT INTO round1_submissions
            (
                team_id,
                item_id,
                selected_era,
                is_correct,
                points_awarded
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            team_id,
            item_id,
            answer,
            int(is_correct),
            points
        ))

        # ---------------------------------------------------------
        # UPDATE SCORE
        # ---------------------------------------------------------

        cursor.execute("""
            UPDATE teams
            SET round1_score = round1_score + ?
            WHERE id = ?
        """, (points, team_id))

        # ---------------------------------------------------------
        # CHECK COMPLETION
        # ---------------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*)
            FROM round1_team_items
            WHERE team_id = ?
        """, (team_id,))

        total_items = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM round1_submissions
            WHERE team_id = ?
        """, (team_id,))

        submitted_items = cursor.fetchone()[0]

        round1_completed = (
            total_items == 25
            and submitted_items >= total_items
        )

        auth_code = None
        clue = None
        completion_time_seconds = None

        # ---------------------------------------------------------
        # ROUND 1 COMPLETED
        # ---------------------------------------------------------

        if round1_completed:

            auth_code = generate_auth_code()
            clue = ROUND1_CLUE

            cursor.execute("""
                UPDATE teams
                SET current_state = 'ROUND1_COMPLETED',
                    round1_completed_at = CURRENT_TIMESTAMP,
                    round1_auth_code = ?
                WHERE id = ?
            """, (auth_code, team_id))

            # Calculate elapsed Round 1 time
            cursor.execute("""
                SELECT
                    CAST(
                        (
                            julianday(round1_completed_at)
                            - julianday(round1_started_at)
                        ) * 86400
                        AS INTEGER
                    ) AS elapsed_seconds
                FROM teams
                WHERE id = ?
            """, (team_id,))

            time_result = cursor.fetchone()

            if time_result:
                completion_time_seconds = time_result["elapsed_seconds"]

        connection.commit()

        # ---------------------------------------------------------
        # RESPONSE
        # ---------------------------------------------------------

        return {
            "item_id": item_id,
            "answer": answer,
            "is_correct": bool(is_correct),
            "points_awarded": points,
            "round1_completed": round1_completed,
            "submitted_items": submitted_items,
            "total_items": total_items,
            "auth_code": auth_code,
            "clue": clue,
            "completion_time_seconds": completion_time_seconds,
            "next_round": "ROUND2" if round1_completed else None
        }

    finally:
        connection.close()


def finish_round1(team_id):
    """
    Finish/check Round 1.

    The frontend can call this when the player presses Finish.

    The backend decides whether the team is actually allowed
    to finish. The frontend cannot simply declare completion.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ---------------------------------------------------------
        # CHECK TEAM
        # ---------------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                current_state,
                round1_score,
                round1_started_at,
                round1_completed_at,
                round1_auth_code
            FROM teams
            WHERE id = ?
        """, (team_id,))

        team = cursor.fetchone()

        if team is None:
            return {
                "error": "Invalid team_id."
            }

        # ---------------------------------------------------------
        # CHECK ASSIGNED ITEMS
        # ---------------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*)
            FROM round1_team_items
            WHERE team_id = ?
        """, (team_id,))

        total_items = cursor.fetchone()[0]

        # ---------------------------------------------------------
        # CHECK SUBMISSIONS
        # ---------------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*)
            FROM round1_submissions
            WHERE team_id = ?
        """, (team_id,))

        submitted_items = cursor.fetchone()[0]

        # ---------------------------------------------------------
        # NOT COMPLETE
        # ---------------------------------------------------------

        if submitted_items < total_items:

            return {
                "round1_completed": False,
                "message": "Round 1 is not complete yet.",
                "submitted_items": submitted_items,
                "total_items": total_items,
                "auth_code": None,
                "clue": None,
                "next_round": None
            }

        # ---------------------------------------------------------
        # ALREADY COMPLETED
        # ---------------------------------------------------------

        if team["current_state"] == "ROUND1_COMPLETED":

            completion_time_seconds = None

            if (
                team["round1_started_at"]
                and team["round1_completed_at"]
            ):
                cursor.execute("""
                    SELECT CAST(
                        (
                            julianday(round1_completed_at)
                            - julianday(round1_started_at)
                        ) * 86400
                        AS INTEGER
                    )
                    FROM teams
                    WHERE id = ?
                """, (team_id,))

                result = cursor.fetchone()

                if result:
                    completion_time_seconds = result[0]

            return {
                "round1_completed": True,
                "message": "Round 1 already completed.",
                "submitted_items": submitted_items,
                "total_items": total_items,
                "score": team["round1_score"],
                "auth_code": team["round1_auth_code"],
                "clue": ROUND1_CLUE,
                "completion_time_seconds": completion_time_seconds,
                "next_round": "ROUND2"
            }

        # ---------------------------------------------------------
        # COMPLETE ROUND 1
        # ---------------------------------------------------------

        auth_code = generate_auth_code()

        cursor.execute("""
            UPDATE teams
            SET current_state = 'ROUND1_COMPLETED',
                round1_completed_at = CURRENT_TIMESTAMP,
                round1_auth_code = ?
            WHERE id = ?
        """, (auth_code, team_id))

        connection.commit()

        # Calculate completion time
        cursor.execute("""
            SELECT CAST(
                (
                    julianday(round1_completed_at)
                    - julianday(round1_started_at)
                ) * 86400
                AS INTEGER
            )
            FROM teams
            WHERE id = ?
        """, (team_id,))

        result = cursor.fetchone()

        completion_time_seconds = None

        if result:
            completion_time_seconds = result[0]

        return {
            "round1_completed": True,
            "message": "Round 1 completed successfully.",
            "submitted_items": submitted_items,
            "total_items": total_items,
            "score": team["round1_score"],
            "auth_code": auth_code,
            "clue": ROUND1_CLUE,
            "completion_time_seconds": completion_time_seconds,
            "next_round": "ROUND2"
        }

    finally:
        connection.close()