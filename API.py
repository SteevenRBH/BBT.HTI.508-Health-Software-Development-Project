from flask import Flask, render_template, jsonify, request
from logic import get_hyperlipidemia_patients, get_patient_data

app = Flask(__name__, template_folder=".")

# 2113340
@app.route("/")
def home():
    return render_template("frontend.html")


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
        return jsonify({"error": "Patient not found."}), 404
    return jsonify(patient_data), 200


# HTML-rendered view for form-based patient query
@app.route("/patient", methods=["GET"])
def patient_page():
    patient_id = request.args.get("patientId", "").strip()
    if not patient_id:
        return render_template("frontend.html", error="Please enter a Patient ID.")

    patient_data = get_patient_data(patient_id)
    if patient_data is None:
        return render_template("frontend.html", error="Patient not found or does not have Hyperlipidemia.")

    return render_template(
        "frontend.html",
        cholesterol=patient_data["cholesterol_measurements"],
        glucose=patient_data["glucose_measurements"],
        medications=patient_data["medication_dispenses"]
    )


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
