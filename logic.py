import json
from datetime import datetime

# Load patient data from JSON database
JSON_DATABASE = 'json_database.json'


def load_patient_data():
    """Load and parse patient data from a JSON file."""
    with open(JSON_DATABASE, 'r', encoding='utf-8') as f:
        return json.load(f)


data = load_patient_data()


def has_hyperlipidemia(resources):
    """Check if a patient's medical records indicate hyperlipidemia."""
    for entry in resources:
        res = entry.get("resource", {})
        if res.get("resourceType") == "Condition":
            code = res.get("code", {})
            if code.get("text") and "hyperlip" in code.get("text").lower():
                return True
            for coding in code.get("coding", []):
                if "hyperlip" in coding.get("display", "").lower():
                    return True
    return False


def get_hyperlipidemia_patients():
    """Return a list of patients diagnosed with hyperlipidemia."""
    hyperlip_patients = []
    patient_resources_map = {}

    for resources in data:
        if not resources:
            continue
        patient_res = resources[0].get("resource", {})
        if patient_res.get("resourceType") != "Patient":
            continue
        patient_id = patient_res.get("id")

        if has_hyperlipidemia(resources):
            full_name = "Unknown"
            if "name" in patient_res and patient_res["name"]:
                name_entry = patient_res["name"][0]
                given = " ".join(name_entry.get("given", []))
                family = " ".join(name_entry.get("family", []))
                full_name = f"{given} {family}"

            hyperlip_patients.append((patient_id, full_name))
            patient_resources_map[patient_id] = resources

    return hyperlip_patients, patient_resources_map


hyperlip_patients, patient_resources_map = get_hyperlipidemia_patients()

# Define target codes for measurements and medications
cholesterol_codes = ["Cholest SerPl-mCnc", "Trigl SerPl-mCnc"]
glucose_codes = ["Glucose SerPl-mCnc", "Glucose Bld-mCnc", "Glucose Ur Strip-mCnc", "Glucose CSF-mCnc",
                 "Glucose p fast SerPl-mCnc"]
hyperlip_med_codes = {"312961", "198211", "262095", "543354", "617318", "859749"}


def get_patient_data(patient_id):
    """Fetch detailed patient data, including lab values and medication orders."""
    data = load_patient_data()
    _, patient_resources_map = get_hyperlipidemia_patients()

    if patient_id not in patient_resources_map:
        return None

    selected_resources = patient_resources_map[patient_id]

    cholesterol_table = []
    glucose_table = []
    medication_table = []

    for entry in selected_resources:
        res = entry.get("resource", {})
        rtype = res.get("resourceType")

        if rtype == "Observation":
            code = res.get("code", {})
            code_text = code.get("text", "")
            if not code_text and "coding" in code and code.get("coding"):
                code_text = code["coding"][0].get("display", "")
            date_str = res.get("effectiveDateTime")
            try:
                date_obj = datetime.fromisoformat(date_str) if date_str else None
            except Exception:
                date_obj = None
            value = res.get("valueQuantity", {}).get("value")
            unit = res.get("valueQuantity", {}).get("unit", "")

            record = {"date": date_obj, "code": code_text, "value": value, "unit": unit}
            if code_text in cholesterol_codes:
                cholesterol_table.append(record)
            elif code_text in glucose_codes:
                glucose_table.append(record)

        elif rtype == "MedicationOrder":
            med_concept = res.get("medicationCodeableConcept", {})
            med_text = med_concept.get("text", "")
            if not med_text and "coding" in med_concept and med_concept.get("coding"):
                med_text = med_concept["coding"][0].get("display", "")
            if "statin" in med_text.lower():
                try:
                    date_str = res.get("dosageInstruction", [])[0].get("timing", {}).get("repeat", {}).get("boundsPeriod", {}).get("start")
                    date_obj = datetime.fromisoformat(date_str) if date_str else None
                except Exception:
                    date_obj = None
                dosage = res.get("dosageInstruction", [])[0].get("text", "") if res.get("dosageInstruction") else ""
                medication_table.append({
                    "date": date_obj,
                    "medication": med_text,
                    "dosage": dosage
                })

    # Sort medication table by date
    medication_table.sort(key=lambda x: (x["date"] is not None, x["date"]))

    return {
        "cholesterol_measurements": cholesterol_table,
        "glucose_measurements": glucose_table,
        "medication_dispenses": medication_table
    }
