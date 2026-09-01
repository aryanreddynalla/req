from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import json
import re
import uuid
import math

# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="108 AI Emergency Response System",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
HOSPITALS_FILE = BASE_DIR / "hospitals.json"

# In-memory incident storage for prototype
INCIDENTS = {}


# ============================================================
# FILE HELPERS
# ============================================================

def load_hospitals():
    with open(HOSPITALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_hospitals(hospitals):
    with open(HOSPITALS_FILE, "w", encoding="utf-8") as f:
        json.dump(hospitals, f, indent=4)


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


# ============================================================
# SPECIALTY DETECTION
# ============================================================

SPECIALTY_RULES = {
    "cardiology": [
        "chest pain",
        "severe chest pain",
        "chest pressure",
        "pressure in chest",
        "heart attack",
        "heart problem",
        "heart issue",
        "heart pain",
        "cardiac arrest",
        "cardiac",
        "palpitations",
        "difficulty breathing",
        "shortness of breath",
        "breathing difficulty",
        "breathlessness",
        "heavy sweating",
        "sweating heavily"
    ],

    "neurology": [
        "stroke",
        "seizure",
        "seizures",
        "convulsion",
        "fits",
        "slurred speech",
        "cannot speak",
        "can't speak",
        "cannot talk",
        "can't talk",
        "unable to speak",
        "difficulty speaking",
        "difficulty talking",
        "speech problem",
        "one side is weak",
        "weakness on one side",
        "one side weakness",
        "paralysis",
        "paralyzed",
        "paralysed",
        "suddenly confused",
        "sudden confusion",
        "severe dizziness",
        "suddenly dizzy"
    ],

    "orthopedics": [
        "orthopedic",
        "orthopaedic",
        "orthopedics",
        "fracture",
        "fractured",
        "broken bone",
        "broken arm",
        "broken leg",
        "leg injury",
        "arm injury",
        "leg pain",
        "arm pain",
        "knee injury",
        "knee pain",
        "ankle injury",
        "ankle pain",
        "shoulder injury",
        "shoulder pain",
        "hip injury",
        "hip pain",
        "wrist injury",
        "wrist pain",
        "bone injury",
        "joint injury",
        "dislocation",
        "sprain",
        "sprained",
        "cannot walk",
        "can't walk",
        "unable to walk",
        "cannot put weight",
        "can't put weight",
        "fell down",
        "fell",
        "fall",
        "slipped and fell"
    ],

    "pediatrics": [
        "baby",
        "infant",
        "newborn",
        "child",
        "children",
        "kid",
        "my son",
        "my daughter",
        "pediatric",
        "paediatric"
    ],

    "general trauma": [
        "road accident",
        "car accident",
        "bike accident",
        "motorcycle accident",
        "vehicle accident",
        "serious accident",
        "major accident",
        "accident",
        "collision",
        "crash",
        "heavy bleeding",
        "severe bleeding",
        "major bleeding",
        "trauma"
    ],

    "general care": [
        "fever",
        "high fever",
        "vomiting",
        "vomiting badly",
        "body pain",
        "body ache",
        "weakness",
        "very weak",
        "stomach pain",
        "abdominal pain",
        "diarrhea",
        "diarrhoea",
        "not feeling well",
        "feeling unwell",
        "unwell"
    ]
}


SPECIALIST_MAP = {
    "cardiology": "Cardiologist",
    "neurology": "Neurologist",
    "orthopedics": "Orthopedist",
    "pediatrics": "Pediatrician",
    "general care": "General Physician",
    "general trauma": "Emergency Medicine"
}


# ============================================================
# AI-ASSISTED SPECIALTY INFERENCE
# ============================================================

def detect_specialty(text: str) -> str:
    t = normalize(text)

    scores = {
        specialty: 0
        for specialty in SPECIALTY_RULES
    }

    for specialty, keywords in SPECIALTY_RULES.items():
        for keyword in keywords:
            if keyword in t:
                scores[specialty] += 1

    # Extra confidence for orthopedic combinations
    body_parts = [
        "leg", "arm", "knee", "ankle", "bone",
        "joint", "shoulder", "hip", "wrist"
    ]

    injury_terms = [
        "pain", "injury", "injured", "hurt",
        "broken", "fracture", "fall", "fell",
        "sprain", "cannot walk", "can't walk"
    ]

    if (
        any(x in t for x in body_parts)
        and any(x in t for x in injury_terms)
    ):
        scores["orthopedics"] += 8

    # Extra confidence for neurological combinations
    if (
        any(x in t for x in ["speech", "speak", "talk"])
        and any(x in t for x in [
            "weak", "weakness", "one side",
            "stroke", "paralysis", "confusion"
        ])
    ):
        scores["neurology"] += 8

    # Trauma boost
    if any(
        x in t
        for x in [
            "accident",
            "collision",
            "crash",
            "road accident"
        ]
    ):
        scores["general trauma"] += 5

    # Pediatric boost
    if any(
        x in t
        for x in [
            "baby",
            "infant",
            "child",
            "kid",
            "newborn"
        ]
    ):
        scores["pediatrics"] += 6

    best = max(scores, key=scores.get)

    if scores[best] == 0:
        return "general care"

    return best


# ============================================================
# PRIORITY
# ============================================================

def detect_priority(text: str) -> str:
    t = normalize(text)

    critical = [
        "cardiac arrest",
        "heart attack",
        "not breathing",
        "cannot breathe",
        "can't breathe",
        "unconscious",
        "stroke",
        "seizure",
        "heavy bleeding",
        "severe bleeding"
    ]

    high = [
        "severe",
        "serious",
        "urgent",
        "emergency",
        "difficulty breathing",
        "shortness of breath",
        "cannot walk",
        "can't walk"
    ]

    if any(x in t for x in critical):
        return "CRITICAL"

    if any(x in t for x in high):
        return "HIGH"

    return "NORMAL"


# ============================================================
# HOSPITAL SELECTION
# ============================================================

def select_hospital_for_emergency(
    specialty: str,
    location: str
):
    hospitals = load_hospitals()

    required_specialist = SPECIALIST_MAP[specialty]

    eligible = []
    rejected = []

    for hospital in hospitals:

        hospital_location = hospital.get(
            "location",
            ""
        ).strip().lower()

        requested_location = (
            location or "Hyderabad"
        ).strip().lower()

        if hospital_location != requested_location:
            rejected.append({
                "name": hospital["name"],
                "reason": "Hospital is outside the requested location."
            })
            continue

        if not hospital.get("on_duty", False):
            rejected.append({
                "name": hospital["name"],
                "reason": "Hospital is OFF DUTY."
            })
            continue

        if not hospital.get(
            "emergency_available",
            False
        ):
            rejected.append({
                "name": hospital["name"],
                "reason": "Emergency service is set to NO."
            })
            continue

        if not hospital.get(
            "specialists",
            {}
        ).get(
            required_specialist,
            False
        ):
            rejected.append({
                "name": hospital["name"],
                "reason":
                    f"{required_specialist} is OFF DUTY."
            })
            continue

        eligible.append(hospital)

    eligible.sort(
        key=lambda h: float(
            h.get("distance_km", 999)
        )
    )

    if not eligible:
        return None, [], rejected

    selected = eligible[0]

    reasons = [
        "Hospital is ON DUTY",
        "Emergency service is YES",
        f"{required_specialist} is ON DUTY",
        f"Suitable for {specialty.replace('_', ' ').title()}",
        f"Nearest eligible hospital at {selected['distance_km']} km"
    ]

    return selected, eligible, rejected


# ============================================================
# MODELS
# ============================================================

class AnalyzeRequest(BaseModel):
    caller_name: str
    location: str
    description: str


class IncidentCreateRequest(BaseModel):
    caller: str
    location: str
    description: str


class AcceptRequest(BaseModel):
    responder: str


class DispatchRequest(BaseModel):
    ambulance_id: str
    driver_name: str


class DriverStatusRequest(BaseModel):
    status: str


class HospitalDutyRequest(BaseModel):
    on_duty: bool


class EmergencyAvailabilityRequest(BaseModel):
    emergency_available: bool


class DoctorDutyRequest(BaseModel):
    specialist: str
    on_duty: bool


class RouteRequest(BaseModel):
    incident_id: str


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "system":
            "108 AI Emergency Response System",
        "status":
            "online",
        "port":
            8010
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "port": 8010,
        "hospital_count":
            len(load_hospitals()),
        "incident_count":
            len(INCIDENTS)
    }


# ============================================================
# HOSPITALS
# ============================================================

@app.get("/hospitals")
def get_hospitals():
    return load_hospitals()


@app.put("/hospitals/{hospital_id}/duty")
def update_hospital_duty(
    hospital_id: int,
    request: HospitalDutyRequest
):
    hospitals = load_hospitals()

    for hospital in hospitals:
        if hospital["id"] == hospital_id:

            hospital["on_duty"] = request.on_duty

            save_hospitals(hospitals)

            return {
                "success": True,
                "hospital": hospital
            }

    raise HTTPException(
        status_code=404,
        detail="Hospital not found."
    )


@app.put("/hospitals/{hospital_id}/emergency")
def update_emergency_availability(
    hospital_id: int,
    request: EmergencyAvailabilityRequest
):
    hospitals = load_hospitals()

    for hospital in hospitals:
        if hospital["id"] == hospital_id:

            hospital[
                "emergency_available"
            ] = request.emergency_available

            save_hospitals(hospitals)

            return {
                "success": True,
                "hospital": hospital
            }

    raise HTTPException(
        status_code=404,
        detail="Hospital not found."
    )


@app.put("/hospitals/{hospital_id}/doctor")
def update_doctor_duty(
    hospital_id: int,
    request: DoctorDutyRequest
):
    hospitals = load_hospitals()

    for hospital in hospitals:
        if hospital["id"] == hospital_id:

            specialists = hospital.get(
                "specialists",
                {}
            )

            if request.specialist not in specialists:
                raise HTTPException(
                    status_code=400,
                    detail="Specialist not found."
                )

            specialists[
                request.specialist
            ] = request.on_duty

            hospital["specialists"] = specialists

            save_hospitals(hospitals)

            return {
                "success": True,
                "hospital": hospital
            }

    raise HTTPException(
        status_code=404,
        detail="Hospital not found."
    )


# ============================================================
# ANALYZE
# ============================================================

@app.post("/analyze")
def analyze(request: AnalyzeRequest):

    specialty = detect_specialty(
        request.description
    )

    priority = detect_priority(
        request.description
    )

    specialist = SPECIALIST_MAP[
        specialty
    ]

    return {
        "success": True,
        "caller": request.caller_name,
        "location": request.location,
        "description": request.description,
        "specialty": specialty,
        "specialist": specialist,
        "priority": priority
    }


# ============================================================
# CREATE INCIDENT
# ============================================================

@app.post("/incidents")
def create_incident(
    request: IncidentCreateRequest
):

    specialty = detect_specialty(
        request.description
    )

    priority = detect_priority(
        request.description
    )

    specialist = SPECIALIST_MAP[
        specialty
    ]

    selected, eligible, rejected = (
        select_hospital_for_emergency(
            specialty,
            request.location
        )
    )

    incident_id = (
        "INC-" +
        uuid.uuid4().hex[:8].upper()
    )

    hospital_name = (
        selected["name"]
        if selected
        else None
    )

    distance = (
        selected["distance_km"]
        if selected
        else None
    )

    reasons = []

    if selected:
        reasons = [
            "Hospital is ON DUTY",
            "Emergency service is YES",
            f"{specialist} is ON DUTY",
            f"Suitable for {specialty.replace('_', ' ').title()}",
            f"Nearest eligible hospital at {distance} km"
        ]

    incident = {
        "incident_id": incident_id,
        "caller": request.caller,
        "location": request.location,
        "description": request.description,
        "emergency": specialty,
        "specialty": specialty,
        "specialist": specialist,
        "priority": priority,
        "hospital": hospital_name,
        "distance_km": distance or 0,
        "selection_reasons": reasons,
        "rejected_hospitals": rejected,
        "status": "CREATED",
        "responder": None,
        "ambulance_id": None,
        "driver": None,
        "driver_status": None,
        "eta_minutes": None,
        "traffic": None,
        "hospital_acknowledged": False
    }

    INCIDENTS[incident_id] = incident

    return {
        "success": True,
        "incident": incident
    }


# ============================================================
# GET INCIDENT
# ============================================================

@app.get("/incidents/{incident_id}")
def get_incident(
    incident_id: str
):

    incident = INCIDENTS.get(
        incident_id
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found."
        )

    return {
        "success": True,
        "incident": incident
    }


# ============================================================
# ACCEPT
# ============================================================

@app.post("/incidents/{incident_id}/accept")
def accept_incident(
    incident_id: str,
    request: AcceptRequest
):

    incident = INCIDENTS.get(
        incident_id
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found."
        )

    incident["responder"] = request.responder

    incident["status"] = (
        "RESPONDER_ACCEPTED"
    )

    return {
        "success": True,
        "incident": incident
    }


# ============================================================
# DISPATCH
# ============================================================

@app.post("/incidents/{incident_id}/dispatch")
def dispatch_ambulance(
    incident_id: str,
    request: DispatchRequest
):

    incident = INCIDENTS.get(
        incident_id
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found."
        )

    if not incident.get("hospital"):
        raise HTTPException(
            status_code=409,
            detail="No suitable hospital assigned."
        )

    incident["ambulance_id"] = (
        request.ambulance_id
    )

    incident["driver"] = (
        request.driver_name
    )

    incident["driver_status"] = (
        "ASSIGNED"
    )

    distance = float(
        incident.get(
            "distance_km",
            5
        )
    )

    priority = incident.get(
        "priority",
        "NORMAL"
    )

    if priority == "CRITICAL":
        speed = 45

    elif priority == "HIGH":
        speed = 40

    else:
        speed = 35

    eta = max(
        3,
        round(
            distance / speed * 60
        )
    )

    incident["eta_minutes"] = eta

    incident["traffic"] = (
        "Heavy"
        if priority == "CRITICAL"
        else "Moderate"
    )

    incident["status"] = (
        "AMBULANCE_DISPATCHED"
    )

    return {
        "success": True,
        "incident": incident
    }


# ============================================================
# DRIVER STATUS
# ============================================================

@app.post(
    "/incidents/{incident_id}/driver-status"
)
def update_driver_status(
    incident_id: str,
    request: DriverStatusRequest
):

    incident = INCIDENTS.get(
        incident_id
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found."
        )

    allowed = {
        "ASSIGNED",
        "EN_ROUTE_TO_PATIENT",
        "ARRIVED_AT_PATIENT",
        "PATIENT_PICKED_UP",
        "TRANSPORTING",
        "ARRIVED_AT_HOSPITAL"
    }

    status = request.status.upper().strip()

    if status not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Invalid driver status."
        )

    incident["driver_status"] = status

    if status == "ARRIVED_AT_HOSPITAL":
        incident["status"] = (
            "ARRIVED_AT_HOSPITAL"
        )

    return {
        "success": True,
        "status": status,
        "incident": incident
    }


# ============================================================
# HOSPITAL ACKNOWLEDGEMENT
# ============================================================

@app.post(
    "/incidents/{incident_id}/hospital-ack"
)
def acknowledge_hospital(
    incident_id: str
):

    incident = INCIDENTS.get(
        incident_id
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found."
        )

    incident[
        "hospital_acknowledged"
    ] = True

    incident["status"] = (
        "HOSPITAL_ACKNOWLEDGED"
    )

    return {
        "success": True,
        "incident": incident
    }


# ============================================================
# ROUTING
# ============================================================

@app.post("/route")
def route(
    request: RouteRequest
):

    incident = INCIDENTS.get(
        request.incident_id
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found."
        )

    distance = float(
        incident.get(
            "distance_km",
            5
        )
    )

    eta = incident.get(
        "eta_minutes"
    )

    if eta is None:
        eta = max(
            3,
            round(
                distance / 40 * 60
            )
        )

    return {
        "success": True,
        "incident_id":
            request.incident_id,
        "specialty":
            incident["specialty"],
        "hospital":
            incident["hospital"],
        "origin":
            incident["location"],
        "destination":
            incident["hospital"],
        "distance_km":
            distance,
        "eta_minutes":
            eta,
        "traffic":
            incident.get(
                "traffic",
                "Moderate"
            ),
        "status":
            "Route calculated"
    }


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8010
    )