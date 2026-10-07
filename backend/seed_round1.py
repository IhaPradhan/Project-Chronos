import csv
from pathlib import Path

from app.database.connection import get_connection


BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "round1_manifest.csv"

IMAGE_FOLDER = "static/round1"


def seed_round1():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            inserted = 0
            skipped = 0

            for row in reader:
                item_id = int(row["item_id"])
                item_name = row["item_name"].strip()
                image_filename = row["image_filename"].strip()
                correct_era = row["correct_era"].strip().upper()

                image_path = f"/{IMAGE_FOLDER}/{image_filename}"

                # Check whether this item already exists
                cursor.execute(
                    """
                    SELECT item_id
                    FROM round1_items
                    WHERE item_id = ?
                    """,
                    (item_id,)
                )

                existing = cursor.fetchone()

                if existing:
                    skipped += 1
                    continue

                cursor.execute(
                    """
                    INSERT INTO round1_items
                    (
                        item_id,
                        item_name,
                        image_path,
                        correct_era,
                        points_positive,
                        points_negative,
                        is_active
                    )
                    VALUES (?, ?, ?, ?, 2, 1, 1)
                    """,
                    (
                        item_id,
                        item_name,
                        image_path,
                        correct_era
                    )
                )

                inserted += 1

        connection.commit()

        print("Round 1 seeding completed!")
        print("Inserted:", inserted)
        print("Skipped:", skipped)
        print("Total rows processed:", inserted + skipped)

    except Exception as error:
        connection.rollback()
        print("Error while seeding Round 1:")
        print(error)

    finally:
        connection.close()


if __name__ == "__main__":
    seed_round1()