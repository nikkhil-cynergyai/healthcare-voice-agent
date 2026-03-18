PATIENT_DB = {
    "P1023": {
        "name": "john",
        "dob": "2000-12-24",
        "visit": "MRI Scan (Lumbar)",
        "date": "2023-10-15",
        "doctor": "Dr. Smith",
        "location": "City Hospital",
        "total": 2500,
        "insurance": 2200, 
        "copay": 50,
        "balance": 250
    }
}

def get_patient(pid):
    return PATIENT_DB.get(pid)