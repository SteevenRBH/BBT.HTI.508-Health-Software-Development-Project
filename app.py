import json
from datetime import datetime
from flask import Flask, jsonify

app = Flask(__name__)

JSON_DATABASE = 'json_database.json'

with open(JSON_DATABASE, 'r', encoding='utf-8') as f:
    fhir_data = json.load(f)

#  Determine if patient has Hyperlipidemia
def has_hyperlipidemia(fhir_data, patient_id):
    """
    Check if a patient has hyperlipidemia based on their Condition resources.

    :param fhir_data: List containing FHIR JSON database (list of patient resource lists).
    :param patient_id: ID of the patient to check.
    :return: True if the patient has hyperlipidemia, False otherwise.
    """
    hyperlipidemia_codes = {"E78", "E78.0", "E78.1", "E78.2", "E78.3", "E78.4",
                            "E78.5", "E78.6", "E78.7", "E78.8", "E78.9",
                            "55822004"}  # Both ICD-10 and SNOMED codes

    for patient_resources in fhir_data:
        for entry in patient_resources:
            resource = entry.get("resource", {})
            if resource.get("resourceType") == "Condition" and resource.get("patient", {}).get(
                    "reference") == f"Patient/{patient_id}":
                coding_list = resource.get("code", {}).get("coding", [])
                if isinstance(coding_list, list):
                    for coding in coding_list:
                        if isinstance(coding, dict) and (
                                coding.get("code") in hyperlipidemia_codes or
                                "hyperlipidemia" in coding.get("display", "").lower()):
                            return True
    return False

# Build a dictionary mapping patient ID to resources
patient_resources_map = {}

for patient_resources in fhir_data:
    for entry in patient_resources:
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            patient_id = resource.get("id", "")
            if patient_id:
                patient_resources_map[patient_id] = patient_resources

# Build a list of patients with Hyperlipidemia
def get_patients_with_hyperlipidemia():
    patient_ids = set()

    for patient_id in patient_resources_map:
        if has_hyperlipidemia(fhir_data, patient_id):
            patient_ids.add(patient_id)

    return list(patient_ids)

# Define target codes for measurements and medications
cholesterol_codes = ["Cholest SerPl-mCnc", "Trigl SerPl-mCnc"]
glucose_codes = ["Glucose SerPl-mCnc", "Glucose Bld-mCnc",
                 "Glucose Ur Strip-mCnc", "Glucose CSF-mCnc", "Glucose p fast SerPl-mCnc"]
hyperlip_med_codes = {"312961", "198211", "262095", "543354", "617318", "859749"}

# Precompute the list of hyperlipidemia patients
hyperlip_patients = get_patients_with_hyperlipidemia()

# API
@app.route('/')
def home():
    return "Welcome to the Patient Data API!"


# API to Get Patient Information with Hyperlipidemia

@app.route('/api/patients', methods=['GET'])
def get_patients():
    return jsonify(hyperlip_patients), 200


# API: Get Patient Data by ID
@app.route('/api/patient/<patient_id>', methods=['GET'])
def get_patient_data(patient_id):
    if patient_id not in patient_resources_map:
        return jsonify({"error": "Patient not found or does not have Hyperlipidemia."}), 404

    selected_resources = patient_resources_map[patient_id]

    cholesterol_table = []
    glucose_table = []
    medication_dispense_table = []

    for entry in selected_resources:
        res = entry.get("resource", {})
        rtype = res.get("resourceType")

        # Process Observation resources
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
            if code_text in cholesterol_codes:
                cholesterol_table.append({
                    "date": date_obj,
                    "code": code_text,
                    "value": value,
                    "unit": unit
                })
            elif code_text in glucose_codes:
                glucose_table.append({
                    "date": date_obj,
                    "code": code_text,
                    "value": value,
                    "unit": unit
                })

        # Process MedicationDispense/Administration events
        elif rtype in ["MedicationDispense", "MedicationAdministration"]:
            med_concept = res.get("medicationCodeableConcept", {})
            med_text = med_concept.get("text", "")
            if not med_text and "coding" in med_concept and med_concept.get("coding"):
                med_text = med_concept["coding"][0].get("display", "")
            if "statin" in med_text.lower():
                date_str = res.get("whenHandedOver") or res.get("effectiveDateTime")
                try:
                    date_obj = datetime.fromisoformat(date_str) if date_str else None
                except Exception:
                    date_obj = None
                medication_dispense_table.append({
                    "date": date_obj,
                    "medication": med_text
                })

    return jsonify({
        "cholesterol_measurements": cholesterol_table,
        "glucose_measurements": glucose_table,
        "medication_dispenses": medication_dispense_table
    }), 200


# Start the Flask application
if __name__ == '__main__':
    app.run(debug=True)
