PATIENT_DB = {
    "P1023": {
        # ── Personal Info ──
        "name":          "John Carter",
        "dob":           "1985-06-15",
        "phone":         "+1 (555) 234-7890",
        "email":         "john.carter@email.com",
        "address":       "42 Maple Street, Springfield, IL 62701",

        # ── Insurance ──
        "insurance_provider": "BlueCross BlueShield",
        "insurance_id":       "BCB-2023-884729",
        "insurance_group":    "GRP-5521",

        # ── Visit Details ──
        "visit":         "MRI Scan (Lumbar Region)",
        "date":          "2023-10-15",
        "doctor":        "Dr. Emily Smith",
        "department":    "Radiology",
        "location":      "City Hospital — Main Campus, Springfield",
        "room":          "Radiology Suite B, Room 204",
        "admit_time":    "9:30 AM",
        "discharge_time":"12:15 PM",

        # ── Billing ──
        "total":         2500,
        "insurance":     2200,
        "copay":         50,
        "balance":       250,
        "due_date":      "2024-01-15",
        "account_number":"ACC-2023-104729",
        "payment_plan":  "Available — call billing at (555) 100-2000",

        # ── Services Breakdown ──
        "services": [
            {"name": "MRI Scan (Lumbar)",      "cost": 1800},
            {"name": "Radiologist Reading Fee", "cost": 400},
            {"name": "Facility Fee",            "cost": 200},
            {"name": "Contrast Dye",            "cost": 100},
        ],

        # ── Follow-up ──
        "follow_up_doctor": "Dr. Emily Smith",
        "follow_up_date":   "2023-11-01",
        "follow_up_dept":   "Orthopedics",
    }
}


def get_patient(pid: str) -> dict | None:
    return PATIENT_DB.get(pid)