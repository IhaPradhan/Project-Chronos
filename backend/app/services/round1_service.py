TEST_ITEMS = [
    {
        "id": "r1_test_01",
        "technology": "Floppy Disk",
        "category": "PAST",
    },
    {
        "id": "r1_test_02",
        "technology": "Smartphone",
        "category": "PRESENT",
    },
    {
        "id": "r1_test_03",
        "technology": "Quantum Computer",
        "category": "FUTURE",
    },
]


def get_round1_items():
    return TEST_ITEMS
def submit_answer(item_id, answer):
    for item in TEST_ITEMS:
        if item["id"] == item_id:
            is_correct = answer.upper() == item["category"]

            if is_correct:
                points = 2
            else:
                points = -1

            return {
                "item_id": item_id,
                "answer": answer.upper(),
                "is_correct": is_correct,
                "points_awarded": points,
            }

    return None