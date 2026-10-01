from .connection import get_connection

def create_tables():
    connection = get_connection()

    try:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_name TEXT NOT NULL,
                member_1_name TEXT NOT NULL,
                member_2_name TEXT NOT NULL,
                current_state TEXT,
                round1_score INTEGER DEFAULT 0,
                round1_auth_code TEXT,
                round2_score INTEGER DEFAULT 0,
                round3_score INTEGER DEFAULT 0,
                total_score INTEGER DEFAULT 0,
                round1_started_at TEXT,
                round1_completed_at TEXT,
                round2_started_at TEXT,
                round2_completed_at TEXT,
                round3_started_at TEXT,
                round3_completed_at TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS team_fragments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                fragment TEXT,
                unlocked_at TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(id)
            );

            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                round INTEGER,
                reference_id TEXT,
                answer TEXT,
                is_correct INTEGER,
                points_awarded INTEGER,
                submitted_at TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(id)
            );

            CREATE TABLE IF NOT EXISTS round1_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                image_path TEXT NOT NULL,
                correct_era TEXT NOT NULL CHECK(correct_era IN ('PAST', 'PRESENT', 'FUTURE')),
                clue_text TEXT,
                points_positive FLOAT DEFAULT 2.0,
                points_negative FLOAT DEFAULT 1.0,
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS round1_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                selected_era TEXT NOT NULL CHECK(selected_era IN ('PAST', 'PRESENT', 'FUTURE')),
                is_correct INTEGER NOT NULL,
                points_awarded FLOAT NOT NULL,
                submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                FOREIGN KEY (item_id) REFERENCES round1_items(item_id)
            );

            CREATE TABLE IF NOT EXISTS hints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                round INTEGER,
                hint_level INTEGER,
                points_deducted INTEGER,
                created_at TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(id)
            );

            CREATE TABLE IF NOT EXISTS investments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                option_id TEXT,
                allocation INTEGER,
                submitted_at TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(id)
            );

            CREATE TABLE IF NOT EXISTS game_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER,
                event_type TEXT,
                event_data TEXT,
                created_at TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(id)
            );
        """)

        
        connection.commit()
    finally:
        connection.close()
