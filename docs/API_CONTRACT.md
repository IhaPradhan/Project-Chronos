# CHRONOS Round 2 API contract

Base path: `/api/round2`. JSON requests and responses. `team_id` is an integer in the current scaffold; when team authentication is integrated, derive it from the authenticated session rather than trusting a client-supplied ID.

## Ask the Analyst AI

- **Endpoint:** `/api/round2/ai/ask`
- **Method:** `POST`
- **Request body:**

```json
{"team_id": 101, "question": "Compare the Alpha modification time with Gamma access records."}
```

- **Success response (`200`):**

```json
{
  "team_id": 101,
  "question_number": 1,
  "answer": "Compare the first configuration change with the incident time, then check the access history around that point.",
  "used_fallback": false,
  "points_charged": 5,
  "ai_points_remaining": 15,
  "questions_remaining": 2
}
```

`answer` is generated from server-loaded, unlocked Alpha/Beta/Gamma evidence only. The client cannot submit or override evidence context. If Gemini times out or fails, the endpoint returns `200` with the predefined hint and `used_fallback: true`; the question is still charged. Total provider budget is capped at approximately 6 seconds, with at most one short retry for transient failures.

## Get AI question budget

- **Endpoint:** `/api/round2/ai/status?team_id=101`
- **Method:** `GET`
- **Response (`200`):**

```json
{"team_id":101,"questions_used":1,"questions_remaining":2,"ai_points_remaining":15}
```

Budget: starts at 20; question 1 costs 5, question 2 costs 5, and question 3 costs 10. The charge is committed atomically on the backend before calling Gemini.

## Submit Round 2 culprit

- **Endpoint:** `/api/round2/culprit/submit`
- **Method:** `POST`
- **Request body:**

```json
{"team_id":101,"culprit":"Sigma"}
```

- **Success response (`200`):**

```json
{
  "team_id":101,
  "submitted":true,
  "correct":true,
  "score_awarded":30,
  "round2_score":30,
  "ai_points_remaining":15,
  "questions_used":1
}
```

A wrong but valid candidate returns `200`, `correct: false`, and `score_awarded: 0`. The answer key is loaded only from server-side `ROUND2_CASES_JSON`, keyed by team ID, and is never returned. A team can submit once.

## Errors / status codes

| Status | Code / meaning | Applies to |
|---|---|---|
| `200` | Success; includes `used_fallback` for AI provider failure | AI ask, status, culprit submission |
| `404` | File missing or access denied | Existing file endpoint |
| `409` | `already_submitted` — team already submitted a culprit | Culprit submission |
| `422` | Validation error, blank question, or `invalid_candidate` | All request validation; culprit submission |
| `429` | `ai_limit_reached` — three questions used / no budget | AI ask |
| `403` | `evidence_locked` — team has not unlocked evidence | AI ask |
| `503` | `case_not_configured` — no server-side answer key for team | Culprit submission |

FastAPI's standard validation response may use its standard `detail` array for malformed bodies. Application errors use `detail.code` and `detail.message`.

## Configuration and integration notes

- Set `GEMINI_API_KEY` in the backend environment; never put it in the browser.
- Optional `GEMINI_MODEL` defaults to `gemini-2.5-flash`.
- Set `ROUND2_CASES_JSON`, e.g. `{"101":{"culprit":"Sigma","candidates":["Omega","Sigma","Delta"],"evidence":{"alpha":{"filename":"future_audit.log","content":"..."},"beta":{"filename":"incident_report.txt","content":"..."},"gamma":{"filename":"access_history.log","content":"..."}}}}`. Use actual team-specific case data; do not expose this variable to the frontend. If `evidence` is omitted, the scaffold's shared placeholder evidence is used.
- Optional `CHRONOS_ROUND2_DB` selects the SQLite state database path. Default: `chronos_round2.sqlite3` in the backend working directory.
- Include this router in the FastAPI application and install `httpx` if it is not already present.
- The supplied evidence service still contains placeholder Alpha/Beta/Gamma content. Replace those canonical records with Hrucha's approved evidence source before live play.
- The current scaffold uses a `team_id` request field/query parameter and empty team fragments because the supplied files do not include the authentication integration. Bind the team ID and unlocked fragments to the authenticated team before deployment; otherwise callers could impersonate another team.
