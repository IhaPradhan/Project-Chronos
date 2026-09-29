# Temporary Round 2 file data
# Actual files/content will be added after the event specification is finalized.

ROUND2_FILES = [
    {
        "id": "alpha",
        "filename": "PROJECT_ALPHA",
        "file_type": "LOG",
        "required_fragment": None,
        "content": "Project Alpha evidence will be added here."
    },
    {
        "id": "beta",
        "filename": "PROJECT_BETA",
        "file_type": "REPORT",
        "required_fragment": None,
        "content": "Project Beta evidence will be added here."
    },
    {
        "id": "gamma",
        "filename": "PROJECT_GAMMA",
        "file_type": "LOG",
        "required_fragment": None,
        "content": "Project Gamma evidence will be added here."
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

def get_file_by_id(file_id, team_fragments):
    # Find the requested file
    for file in ROUND2_FILES:
        if file["id"] == file_id:

            # Check if the team is allowed to access it
            if not is_file_unlocked(file, team_fragments):
                return None

            # Return the file content
            return file

    # File does not exist
    return None
