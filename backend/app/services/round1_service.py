from ..database.connection import get_connection
import secrets
import string

def generate_auth_code():
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(6))

def get_round1_items():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT item_id, image_path
            FROM round1_items
            WHERE is_active = 1
            ORDER BY item_id
        """)

        rows = cursor.fetchall()

        return [
            {
                "id": row["item_id"],
                "image": row["image_path"],
            }
            for row in rows
        ]

    finally:
        connection.close()


def submit_answer(team_id, item_id, answer):
    allowed_categories = {"PAST", "PRESENT", "FUTURE"}

    answer = answer.upper().strip()

    if answer not in allowed_categories:
        return {
            "error": "Invalid category. Use PAST, PRESENT, or FUTURE."
        }

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT item_id, correct_era, points_positive, points_negative
            FROM round1_items
            WHERE item_id = ?
              AND is_active = 1
        """, (item_id,))

        item = cursor.fetchone()

        if item is None:
            return {
                "error": "Invalid item_id."
            }
        cursor.execute("""
            SELECT id
            FROM teams
            WHERE id = ?
        """, (team_id,))

        team = cursor.fetchone()

        if team is None:
            return {
                "error": "Invalid team_id."
        }
        

        # Check if this team already submitted this item
        cursor.execute("""
            SELECT id
            FROM round1_submissions
            WHERE team_id = ?
              AND item_id = ?
        """, (team_id, item["item_id"]))

        existing_submission = cursor.fetchone()

        if existing_submission is not None:
            return {
                "error": "This item has already been submitted."
            }

        is_correct = answer == item["correct_era"]

        if is_correct:
            points = item["points_positive"]
        else:
            points = -item["points_negative"]

        # Save the submission in the database
        cursor.execute("""
            INSERT INTO round1_submissions
            (team_id, item_id, selected_era, is_correct, points_awarded)
            VALUES (?, ?, ?, ?, ?)
        """, (
            team_id,
            item["item_id"],
            answer,
            int(is_correct),
            points
        ))

        # Update this team's score
        cursor.execute("""
            UPDATE teams
            SET round1_score = round1_score + ?
            WHERE id = ?
        """, (points, team_id))

        # Check whether all active Round 1 items are completed
        cursor.execute("""
            SELECT COUNT(*)
            FROM round1_items
            WHERE is_active = 1
        """)
        total_items = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT item_id)
            FROM round1_submissions
            WHERE team_id = ?
        """, (team_id,))
        submitted_items = cursor.fetchone()[0]

        round1_completed = submitted_items >= total_items
        auth_code = None

        if round1_completed:
            auth_code = generate_auth_code()

            cursor.execute("""
                UPDATE teams
                SET current_state = 'ROUND1_COMPLETED',
                    round1_completed_at = CURRENT_TIMESTAMP,
                    round1_auth_code = ?
                WHERE id = ?
            """, (auth_code, team_id))

        connection.commit()

        return {
            "item_id": item["item_id"],
            "answer": answer,
            "is_correct": is_correct,
            "points_awarded": points,
            "round1_completed": round1_completed,
            "auth_code": auth_code if round1_completed else None,
            "next_round": "ROUND2" if round1_completed else None,
        }

    finally:
        connection.close()