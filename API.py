# TODO: Create a local webserver and add the HTTP requests from a GUI

from flask import Flask, jsonify
from logic import get_hyperlipidemia_patients, get_patient_data

app = Flask(__name__)

# Load patient data and mappings
hyperlip_patients, _ = get_hyperlipidemia_patients()

@app.route('/')
def home():
    return "Welcome to the Patient Data API!"

# API to Get List of Patients with Hyperlipidemia
@app.route('/api/patients', methods=['GET'])
def get_patients():
    """Retrieve all patients diagnosed with hyperlipidemia."""
    return jsonify(hyperlip_patients), 200

# API: Get Patient Data by ID
@app.route('/api/patient/<patient_id>', methods=['GET'])
def api_get_patient_data(patient_id):
    """Retrieve patient-specific cholesterol, glucose, and medication dispense records."""
    patient_data = get_patient_data(patient_id)
    if patient_data is None:
        return jsonify({"error": "Patient not found or does not have Hyperlipidemia."}), 404
    return jsonify(patient_data), 200

# Start the Flask application
if __name__ == '__main__':
    app.run(debug=True)