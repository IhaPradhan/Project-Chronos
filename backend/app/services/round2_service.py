# Temporary Round 2 file data
# Actual files/content will be added after the event specification is finalized.

ROUND2_FILES = [
    {
        "id": "file_001",
        "filename": "LOG_001",
        "file_type": "LOG",
        "required_fragment": None,
        "content": "Round 2 log content will be added here."
    },
    {
        "id": "file_002",
        "filename": "MEMO_001",
        "file_type": "MEMO",
        "required_fragment": None,
        "content": "Round 2 memo content will be added here."
    },
    {
        "id": "file_003",
        "filename": "RECORD_001",
        "file_type": "RECORD",
        "required_fragment": None,
        "content": "Round 2 record content will be added here."
    }
]


def get_round2_files():
    # Return the available Round 2 files
    return ROUND2_FILES
def is_file_unlocked(file, team_fragments):
    # If no fragment is required, the file is available
    if file["required_fragment"] is None:
        return True

    # Check if the required fragment belongs to the team
    return file["required_fragment"] in team_fragments

def get_files_for_team(team_fragments):
    # Store the files with their locked/unlocked status
    files = []

    for file in ROUND2_FILES:
        unlocked = is_file_unlocked(file, team_fragments)

        files.append({
            "id": file["id"],
            "filename": file["filename"],
            "file_type": file["file_type"],
            "unlocked": unlocked
        })

    return files
