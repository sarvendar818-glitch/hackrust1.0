from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os

# Start the app
app = FastAPI(title="SchemeAI Backend")

# CORS — lets frontend talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load schemes from JSON file
SCHEMES_PATH = os.path.join(os.path.dirname(__file__), "schemes.json")


def load_schemes():
    with open(SCHEMES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Updated Profile to include new fields
class CitizenProfile(BaseModel):
    name: str
    state: str
    income_monthly: int  # User enters monthly, we convert to annual for matching
    caste: str
    family_size: str
    employment_status: str # Matches "Student", "Farmer", etc.
    is_widow: bool        # Matches "widow_only" flag
    language: str


# The matching algorithm
def match_schemes(profile: CitizenProfile):
    schemes = load_schemes()
    matched = []
    
    # Calculate annual income for comparison
    annual_income = profile.income_monthly * 12

    for scheme in schemes:
        # CHECK 1 — Income within range (Comparing annual to annual)
        if annual_income < scheme["min_income_annual"]:
            continue
        if annual_income > scheme["max_income_annual"]:
            continue

        # CHECK 2 — State matches (or "All States")
        state_ok = (
            "All States" in scheme["states"] or profile.state in scheme["states"]
        )
        if not state_ok:
            continue

        # CHECK 3 — Caste matches
        caste_ok = profile.caste in scheme["caste"]
        if not caste_ok:
            continue

        # CHECK 4 — Widowhood status
        # If a scheme is "widow_only", the person MUST be a widow.
        if scheme["widow_only"] and not profile.is_widow:
            continue
            
        # CHECK 5 — Employment Status
        # We check if the scheme's status is "Any" or if it matches the profile
        status_match = (
            scheme["employment_status"] == "Any" or 
            profile.employment_status.lower() in scheme["employment_status"].lower() or
            "Any" in scheme["employment_status"]
        )
        if not status_match:
            continue

        matched.append(scheme)

    return matched


# POST /match — the main endpoint
@app.post("/match")
async def find_schemes(profile: CitizenProfile):
    results = match_schemes(profile)
    annual_income = profile.income_monthly * 12
    
    return {
        "citizen_name": profile.name,
        "total_schemes": len(results),
        "schemes": [
            {
                "scheme_name": s["name"],
                "ministry": s["ministry"],
                "benefit_amount": s["benefit"],
                "why_eligible": (
                    f"Annual Income ₹{annual_income} (within ₹{s['max_income_annual']} limit), "
                    f"Caste: {profile.caste}, Status: {profile.employment_status}"
                ),
                "category": s["category"],
                "how_to_apply": s["how_to_apply"],
                "widow_specific": s["widow_only"]
            }
            for s in results
        ],
    }


# Health check
@app.get("/")
def root():
    return {"status": "SchemeAI Running ✅"}
