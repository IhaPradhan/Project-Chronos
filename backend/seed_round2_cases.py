import json
from pathlib import Path

from app.database.connection import get_connection

# Run from: Project-Chronos/backend
#
# Expected case files:
# Project-Chronos/
# ├── backend/
# │   └── seed_round2_cases.py
# └── round2_cases_batch1/
#     ├── R2-01/
#     ├── R2-02/
#     └── ...

CASES_DIR = Path(__file__).resolve().parents[1] / "round2_cases_all_24"


def create_round2_case_tables(connection):
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS round2_cases (
            case_id TEXT PRIMARY KEY,
            case_code TEXT NOT NULL UNIQUE,
            archetype TEXT NOT NULL,
            incident TEXT NOT NULL,
            culprit TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS round2_case_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            file_id TEXT NOT NULL,
            timeline_tag TEXT NOT NULL,
            filename TEXT NOT NULL,
            content_text TEXT NOT NULL,

            FOREIGN KEY (case_id)
                REFERENCES round2_cases(case_id)
                ON DELETE CASCADE,

            UNIQUE(case_id, file_id)
        );

        CREATE TABLE IF NOT EXISTS round2_case_suspects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            suspect_name TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,

            FOREIGN KEY (case_id)
                REFERENCES round2_cases(case_id)
                ON DELETE CASCADE,

            UNIQUE(case_id, suspect_name),
            UNIQUE(case_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS round2_team_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            case_id TEXT NOT NULL,
            assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (team_id)
                REFERENCES teams(team_id)
                ON DELETE CASCADE,

            FOREIGN KEY (case_id)
                REFERENCES round2_cases(case_id)
                ON DELETE CASCADE,

            UNIQUE(team_id),
            UNIQUE(team_id, case_id)
        );
        """
    )


def load_case(case_dir):
    with open(case_dir / "case.json", "r", encoding="utf-8") as f:
        case = json.load(f)

    files = {
        "alpha": ("future", case["player_files"]["alpha"]),
        "beta": ("present", case["player_files"]["beta"]),
        "gamma": ("past", case["player_files"]["gamma"]),
    }

    loaded_files = []

    for file_id, (timeline_tag, filename) in files.items():
        content = (case_dir / filename).read_text(encoding="utf-8")

        loaded_files.append(
            {
                "file_id": file_id,
                "timeline_tag": timeline_tag,
                "filename": filename,
                "content_text": content,
            }
        )

    return case, loaded_files


def seed_cases(connection):
    if not CASES_DIR.exists():
        raise FileNotFoundError(
            f"Could not find {CASES_DIR}. "
            "Extract round2_cases_batch1 next to the backend directory."
        )

    case_dirs = sorted(
        p
        for p in CASES_DIR.iterdir()
        if p.is_dir() and p.name.startswith("R2-")
    )

    if not case_dirs:
        raise RuntimeError(
            f"No R2-* case folders found in {CASES_DIR}"
        )

    for case_dir in case_dirs:
        case, files = load_case(case_dir)

        # Insert/update case
        connection.execute(
            """
            INSERT INTO round2_cases
                (case_id, case_code, archetype, incident, culprit)
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(case_id) DO UPDATE SET
                case_code = excluded.case_code,
                archetype = excluded.archetype,
                incident = excluded.incident,
                culprit = excluded.culprit
            """,
            (
                case["case_id"],
                case["case_id"],
                case["archetype"],
                case["incident"],
                case["culprit"],
            ),
        )

        # Insert/update Alpha, Beta, Gamma
        for file_data in files:
            connection.execute(
                """
                INSERT INTO round2_case_files
                    (
                        case_id,
                        file_id,
                        timeline_tag,
                        filename,
                        content_text
                    )
                VALUES (?, ?, ?, ?, ?)

                ON CONFLICT(case_id, file_id) DO UPDATE SET
                    timeline_tag = excluded.timeline_tag,
                    filename = excluded.filename,
                    content_text = excluded.content_text
                """,
                (
                    case["case_id"],
                    file_data["file_id"],
                    file_data["timeline_tag"],
                    file_data["filename"],
                    file_data["content_text"],
                ),
            )

        # Insert/update four suspects
        for candidate in case["candidates"]:
            connection.execute(
                """
                INSERT INTO round2_case_suspects
                    (
                        case_id,
                        suspect_name,
                        user_id,
                        role
                    )
                VALUES (?, ?, ?, ?)

                ON CONFLICT(case_id, suspect_name) DO UPDATE SET
                    user_id = excluded.user_id,
                    role = excluded.role
                """,
                (
                    case["case_id"],
                    candidate["name"],
                    candidate["user_id"],
                    candidate["role"],
                ),
            )

    return [p.name for p in case_dirs]


def assign_cases_to_teams(connection):
    """
    Assign seeded cases to existing teams.

    Existing assignments are preserved.
    New teams receive cases in deterministic rotation.
    """

    # IMPORTANT:
    # The real Project Chronos database uses teams.team_id,
    # not teams.id.
    teams = connection.execute(
        """
        SELECT team_id, team_name
        FROM teams
        ORDER BY team_id
        """
    ).fetchall()

    cases = connection.execute(
        """
        SELECT case_id
        FROM round2_cases
        ORDER BY case_id
        """
    ).fetchall()

    if not cases:
        return []

    case_ids = [row["case_id"] for row in cases]
    assignments = []

    for index, team in enumerate(teams):

        # Check whether this team already has a case.
        existing = connection.execute(
            """
            SELECT case_id
            FROM round2_team_cases
            WHERE team_id = ?
            """,
            (team["team_id"],),
        ).fetchone()

        if existing:
            assignments.append(
                (
                    team["team_id"],
                    team["team_name"],
                    existing["case_id"],
                    "existing",
                )
            )
            continue

        # Assign cases in rotation.
        case_id = case_ids[index % len(case_ids)]

        connection.execute(
            """
            INSERT INTO round2_team_cases
                (team_id, case_id)
            VALUES (?, ?)
            """,
            (
                team["team_id"],
                case_id,
            ),
        )

        assignments.append(
            (
                team["team_id"],
                team["team_name"],
                case_id,
                "new",
            )
        )

    return assignments


def main():
    connection = get_connection()

    try:
        print("creating round 2 case tables...")
        create_round2_case_tables(connection)

        print("loading round 2 cases...")
        seeded = seed_cases(connection)

        print("assigning cases to teams...")
        assignments = assign_cases_to_teams(connection)

        connection.commit()

        print()
        print("round 2 cases seeded successfully.")
        print(f"cases loaded: {', '.join(seeded)}")

        print()
        print("team assignments:")

        if not assignments:
            print(
                "  no teams exist yet; "
                "assignments will be created when teams exist."
            )
        else:
            for team_id, team_name, case_id, status in assignments:
                print(
                    f"  team {team_id} ({team_name}) "
                    f"-> {case_id} [{status}]"
                )

        print()
        print("verification:")

        case_count = connection.execute(
            """
            SELECT COUNT(*) AS n
            FROM round2_cases
            """
        ).fetchone()["n"]

        file_count = connection.execute(
            """
            SELECT COUNT(*) AS n
            FROM round2_case_files
            """
        ).fetchone()["n"]

        suspect_count = connection.execute(
            """
            SELECT COUNT(*) AS n
            FROM round2_case_suspects
            """
        ).fetchone()["n"]

        assignment_count = connection.execute(
            """
            SELECT COUNT(*) AS n
            FROM round2_team_cases
            """
        ).fetchone()["n"]

        print(f"  cases:       {case_count}")
        print(f"  files:       {file_count}")
        print(f"  suspects:    {suspect_count}")
        print(f"  assignments: {assignment_count}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()