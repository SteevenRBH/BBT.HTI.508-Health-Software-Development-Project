import json
from datetime import datetime
from flask import Flask, jsonify

app = Flask(__name__)

JSON_DATABASE = 'json_database.json'

with open(JSON_DATABASE, 'r', encoding='utf-8') as f:
    data = json.load(f)


#  Determine if patient has Hyperlipidemia

def has_hyperlipidemia(resources):
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


# Build a list of patients with Hyperlipidemia
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
        # Get patient name
        full_name = "Unknown"
        if "name" in patient_res and patient_res["name"]:
            name_entry = patient_res["name"][0]
            given = " ".join(name_entry.get("given", []))
            family = " ".join(name_entry.get("family", []))
            full_name = f"{given} {family}"
        hyperlip_patients.append((patient_id, full_name))
        patient_resources_map[patient_id] = resources


# Define target codes for measurements and medications

cholesterol_codes = ["Cholest SerPl-mCnc", "Trigl SerPl-mCnc"]
glucose_codes = ["Glucose SerPl-mCnc", "Glucose Bld-mCnc",
                 "Glucose Ur Strip-mCnc", "Glucose CSF-mCnc", "Glucose p fast SerPl-mCnc"]
hyperlip_med_codes = {"312961", "198211", "262095", "543354", "617318", "859749"}


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
