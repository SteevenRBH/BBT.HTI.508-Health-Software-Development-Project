from flask import Flask, jsonify, render_template
from datetime import datetime
import json

# Sovelluksen alustus ja HTML-frontin kansio
app = Flask(__name__, template_folder=".")

# JSON-tietokannan sijainti
JSON_DATABASE = 'json_database.json'

# Ladataan potilasdata
with open(JSON_DATABASE, 'r', encoding='utf-8') as f:
    fhir_data = json.load(f)

# Määritellään hyperlipidemiaa kuvaavat koodit (ICD-10 ja SNOMED)
hyperlipidemia_codes = {
    "E78", "E78.0", "E78.1", "E78.2", "E78.3", "E78.4", "E78.5", "E78.6", "E78.7", "E78.8", "E78.9",
    "55822004"
}

# Mittaus- ja lääkekoodit
cholesterol_codes = ["Cholest SerPl-mCnc", "Trigl SerPl-mCnc"]
glucose_codes = [
    "Glucose SerPl-mCnc", "Glucose Bld-mCnc", "Glucose Ur Strip-mCnc",
    "Glucose CSF-mCnc", "Glucose p fast SerPl-mCnc"
]
hyperlip_med_codes = {"312961", "198211", "262095", "543354", "617318", "859749"}

# Rakennetaan potilaskartta (id -> resurssit)
patient_resources_map = {}
for patient_resources in fhir_data:
    for entry in patient_resources:
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            patient_id = resource.get("id", "")
            if patient_id:
                patient_resources_map[patient_id] = patient_resources

# Tarkistetaan onko potilaalla hyperlipidemiaa
def has_hyperlipidemia(fhir_data, patient_id):
    for patient_resources in fhir_data:
        for entry in patient_resources:
            resource = entry.get("resource", {})
            if resource.get("resourceType") == "Condition" and resource.get("patient", {}).get("reference") == f"Patient/{patient_id}":
                coding_list = resource.get("code", {}).get("coding", [])
                if isinstance(coding_list, list):
                    for coding in coding_list:
                        if coding.get("code") in hyperlipidemia_codes or "hyperlipidemia" in coding.get("display", "").lower():
                            return True
    return False

# Hae kaikki hyperlipidemia-potilaat
def get_patients_with_hyperlipidemia():
    return [pid for pid in patient_resources_map if has_hyperlipidemia(fhir_data, pid)]

# --- API-REITIT ---

# Etusivu: palauttaa HTML-frontin
@app.route("/")
def home():
    return render_template("frontend.html")

# Palauttaa potilas-ID:t joilla on hyperlipidemia
@app.route("/api/patients", methods=["GET"])
def get_patients():
    hyperlip_patients = get_patients_with_hyperlipidemia()
    return jsonify(hyperlip_patients), 200

# Palauttaa yksittäisen potilaan mittaus- ja lääkitystiedot
@app.route("/api/patient/<patient_id>", methods=["GET"])
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

        # Käsitellään mittaushavainnot
        if rtype == "Observation":
            code = res.get("code", {})
            code_text = code.get("text") or (code.get("coding", [{}])[0].get("display", ""))
            date_str = res.get("effectiveDateTime")
            try:
                date_obj = datetime.fromisoformat(date_str) if date_str else None
            except Exception:
                date_obj = None
            value = res.get("valueQuantity", {}).get("value")
            unit = res.get("valueQuantity", {}).get("unit", "")

            if code_text in cholesterol_codes:
                cholesterol_table.append({"date": date_obj, "code": code_text, "value": value, "unit": unit})
            elif code_text in glucose_codes:
                glucose_table.append({"date": date_obj, "code": code_text, "value": value, "unit": unit})

        # Käsitellään lääkitystiedot
        elif rtype in ["MedicationDispense", "MedicationAdministration"]:
            med_concept = res.get("medicationCodeableConcept", {})
            med_text = med_concept.get("text") or (med_concept.get("coding", [{}])[0].get("display", ""))
            if "statin" in med_text.lower():
                date_str = res.get("whenHandedOver") or res.get("effectiveDateTime")
                try:
                    date_obj = datetime.fromisoformat(date_str) if date_str else None
                except Exception:
                    date_obj = None
                medication_dispense_table.append({"date": date_obj, "medication": med_text})

    return jsonify({
        "cholesterol_measurements": cholesterol_table,
        "glucose_measurements": glucose_table,
        "medication_dispenses": medication_dispense_table
    }), 200

# Sovelluksen käynnistys
if __name__ == "__main__":
    app.run(debug=True)

















'''
# TODO: Create a local webserver and add the HTTP requests from a GUI

from flask import Flask, render_template, jsonify
from logic import get_hyperlipidemia_patients, get_patient_data

app = Flask(__name__, template_folder=".")

@app.route("/")
def home():
    return render_template("frontend.html")  # Serve frontend.html

# API to Get List of Patients with Hyperlipidemia
@app.route("/api/patients", methods=["GET"])
def get_patients():
    hyperlip_patients, _ = get_hyperlipidemia_patients()
    return jsonify(hyperlip_patients), 200

# API: Get Patient Data by ID
@app.route("/api/patient/<patient_id>", methods=["GET"])
def api_get_patient_data(patient_id):
    patient_data = get_patient_data(patient_id)
    if patient_data is None:
        return jsonify({"error": "Patient not found or does not have Hyperlipidemia."}), 404
    return jsonify(patient_data), 200

if __name__ == "__main__":
    app.run(debug=True)'''
