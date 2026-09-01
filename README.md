# AI Emergency Healthcare Routing Assistant — Shareable Prototype

## Project structure

- `backend/api.py` — FastAPI backend, natural-language symptom understanding, specialty inference, hospital matching, alternatives, freshness checks, hospital updates.
- `backend/hospitals.json` — prototype hospital dataset, including Cardiology, Neurology, Orthopedics, General Care, General Trauma and Pediatrics.
- `frontend/index.html` — browser UI for hospital staff dashboard, emergency matching, alternatives and notification simulation.
- `requirements.txt` — Python dependencies.

## Run the project

From the project root:

```bash
python3 -m pip install -r requirements.txt
```

Terminal 1:

```bash
uvicorn backend.api:app --reload
```

Terminal 2:

```bash
python3 -m http.server 5500 --directory frontend
```

Open:

`http://127.0.0.1:5500`

Swagger API documentation:

`http://127.0.0.1:8001/docs`

## Current prototype capabilities

- Natural-language symptom interpretation
- Primary and secondary/context symptom classification
- Cardiology, Neurology, Orthopedics, General Trauma, Pediatrics and General Care routing
- Recommended hospital plus alternatives
- **Rejected-candidate explanation** — nearby facilities that were NOT chosen are shown with the specific reason (doctor off duty, emergency unavailable, or stale data), not just silently dropped
- Doctor-on-duty and emergency availability checks
- 30-minute stale-data rule and dashboard warning
- **Escalation on non-acknowledgement** — after a notification is sent, a 30-second acknowledgement window is shown; if the hospital doesn't acknowledge, the system auto-escalates to the next-ranked alternative (use the "Simulate Hospital Acknowledgement" button to show the acknowledged path instead)
- Hospital operational status updates
- Human confirmation step
- Simulated hospital notification
- **Accuracy test script** (`backend/test_accuracy.py`) — runs 20 sample caller sentences through the specialty classifier; currently 20/20 (100%) on the test set

## Not included

- Traffic API — deferred deliberately: current hospital locations are prototype/demo data without real coordinates, so live ETA data wouldn't be meaningful yet. This is the first integration planned once real, registered hospital locations are onboarded.
- Real 108/112 integration
- Real hospital SMS/WhatsApp integration
- Autonomous medical diagnosis
