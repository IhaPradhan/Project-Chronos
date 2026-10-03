# Project Chronos — Round 1 API Contract

## 1. Base URL

Local development:

```text
http://127.0.0.1:8000
```

Round 1 prefix:

```text
/api/round1
```

---

## 2. GET Round 1 Items

### Endpoint

```http
GET /api/round1/items
```

### Purpose

Fetch the Round 1 technology items to display.

### Response

```json
[
  {
    "id": 101,
    "image": "/images/technology_101.png"
  },
  {
    "id": 102,
    "image": "/images/technology_102.png"
  }
]
```

### Fields

| Field | Type | Meaning |
|---|---|---|
| `id` | integer | Unique item ID |
| `image` | string | Image path/URL |

### Important

Frontend must **not** receive or store:

- `correct_era`
- `points_positive`
- `points_negative`

Do not hard-code the number of items. Render whatever the API returns.

---

## 3. POST Submit Answer

### Endpoint

```http
POST /api/round1/submit
```

### Parameters

```text
team_id
item_id
answer
```

Example:

```text
/api/round1/submit?team_id=12&item_id=101&answer=PAST
```

Valid answers:

```text
PAST
PRESENT
FUTURE
```

The backend handles validation and normalizes the answer.

---

## 4. Successful Submission Response

Example:

```json
{
  "item_id": 101,
  "answer": "PAST",
  "is_correct": true,
  "points_awarded": 2.0,
  "round1_completed": false,
  "auth_code": null,
  "next_round": null
}
```

| Field | Type | Meaning |
|---|---|---|
| `item_id` | integer | Submitted item |
| `answer` | string | Selected classification |
| `is_correct` | boolean | Whether answer is correct |
| `points_awarded` | number | Points awarded |
| `round1_completed` | boolean | Whether Round 1 is complete |
| `auth_code` | string/null | Authentication code after completion |
| `next_round` | string/null | Next round after completion |

---

## 5. Scoring

Backend is the source of truth.

```text
Correct answer → +2
Wrong answer   → -1
```

Frontend must **not** calculate or modify the score.

---

## 6. Duplicate Submission

An item can only be submitted once per team.

If already submitted:

```json
{
  "error": "This item has already been submitted."
}
```

Frontend should prevent further submission for that item.

---

## 7. Error Responses

### Invalid category

```json
{
  "error": "Invalid category. Use PAST, PRESENT, or FUTURE."
}
```

### Invalid item

```json
{
  "error": "Invalid item_id."
}
```

### Invalid team

```json
{
  "error": "Invalid team_id."
}
```

---

## 8. Round 1 Completion

When all required active items have been submitted, backend marks the team:

```text
ROUND1_COMPLETED
```

Example completion response:

```json
{
  "item_id": 125,
  "answer": "FUTURE",
  "is_correct": true,
  "points_awarded": 2.0,
  "round1_completed": true,
  "auth_code": "X7K2PQ",
  "next_round": "ROUND2"
}
```

Frontend should then:

1. Show the completion/result screen.
2. Display the authentication code.
3. Proceed to Round 2 only after backend confirmation.

---

## 9. Authentication Code

The backend generates and stores the authentication code.

Frontend must **not**:

- generate the code
- hard-code the code
- guess the code

It only displays the `auth_code` returned after completion.

---

## 10. Frontend Responsibilities

Frontend handles:

- Displaying technology images
- PAST / PRESENT / FUTURE buttons
- User interactions
- Sending submissions
- Showing correct/wrong feedback
- Showing returned points
- Showing progress
- Showing the completion screen
- Displaying the authentication code
- Moving to Round 2 after backend confirmation

---

## 11. Backend Responsibilities

Backend handles:

- Correct-answer validation
- Scoring
- Duplicate protection
- Database submissions
- Team validation
- Round 1 completion
- Team state
- Authentication-code generation
- Round progression

Backend is the **source of truth**.

---

## 12. Frontend Must NOT

Do not:

- Hard-code correct answers
- Hard-code scores
- Hard-code the number of items
- Generate authentication codes
- Assume `team_id = 1`
- Decide completion independently
- Change the official score
- Invent undocumented API fields

Use the IDs returned by the backend.

---

## 13. Suggested Submission Flow

```text
Fetch items
    ↓
Display items
    ↓
Player selects PAST / PRESENT / FUTURE
    ↓
POST team_id + item_id + answer
    ↓
Backend validates
    ↓
Backend calculates +2 / -1
    ↓
Backend saves submission
    ↓
Frontend displays result
    ↓
Continue until completed
    ↓
Backend returns auth_code
    ↓
Display auth_code
    ↓
Proceed to Round 2
```

---

## 14. Final Round 1 Content

Current final event specification:

```text
PAST     → 9
PRESENT  → 10
FUTURE   → 6
TOTAL    → 25
```

However, frontend should **not assume 25**. It should render the items returned by the API.

The larger image pool/random assignment will be handled by the backend.

---

## 15. Timing

Round 1 completion time is recorded by the backend and is used for tie-breaking.

Frontend timer/UI may be added during integration, but backend timestamps remain authoritative.

---

## 16. Final Clue

After successfully completing Round 1, the team receives:

> "The timeline was not broken at the point of failure. Find the system that changed first."

The exact API delivery of this clue will be finalized during integration.

---

## 17. Current API Summary

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/round1/items` | Get Round 1 items |
| POST | `/api/round1/submit` | Submit classification |

### Submit parameters

```text
team_id
item_id
answer
```

### Valid answers

```text
PAST
PRESENT
FUTURE
```

### Scoring

```text
Correct → +2
Wrong   → -1
```

### Completion

```text
round1_completed → true
auth_code        → generated by backend
next_round       → ROUND2
```

---

## 18. Integration Rule

Frontend:

```text
Display → Ask → Send → Receive → Display
```

Backend:

```text
Validate → Score → Store → Decide → Respond
```

If frontend and backend disagree, the backend response is authoritative.
