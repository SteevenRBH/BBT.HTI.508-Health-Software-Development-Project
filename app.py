from flask import Flask, render_template, request, redirect, url_for
from logic import *
from tools import *
from datetime import datetime


# Load data
fhir_data = load_patient_data()

# Create Flask app
app = Flask(__name__)

@app.template_filter('datetime')
def format_datetime(value, format="%Y-%m-%d"):
    if isinstance(value, str):
        value = datetime.strptime(value, format)
    return value.strftime('%B %d, %Y')

@app.template_filter('dictsubcheck')
def dict_has_non_empty_subdicts(value):
    """
    Custom Jinja2 filter to check if a dictionary has at least
    one non-empty sub-dictionary.
    """
    if isinstance(value, dict):
        return any(isinstance(v, dict) and len(v) > 0 for v in value.values())
    return False

@app.route("/", methods=["GET"])
def index():
    # Default values for the plot and no data flag
    patient_id = None
    image_uri = None
    show_ref_vals = True  # Set default to True
    smooth_curves = False  # Set default to False
    show_units = False  # Set default to False
    medications = {}  # Initialize empty medications dictionary

    # Render the index page with all parameters
    return render_template("index.html",
                           patient_id=patient_id,
                           image_uri=image_uri,
                           show_ref_vals=show_ref_vals,
                           smooth_curves=smooth_curves,
                           show_units=show_units,
                           medications=medications)


@app.route("/overview/", methods=["GET", "POST"])
def overview():
    # Get patient_id from the GET request (query string)
    patient_id = request.args.get('patient_id', type=int)

    # Get all toggle values from the request
    show_ref_vals = request.args.get('show_ref_vals', 'true').lower() == 'true'
    smooth_curves = request.args.get('smooth_curves', 'false').lower() == 'true'
    show_units = request.args.get('show_units', 'false').lower() == 'true'

    # Get date limits from request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if patient_id is None:
        return redirect(url_for('index'))

    # Check if patient exists in database
    patient_id_exists, _ = patient_exists(fhir_data, patient_id)
    if not patient_id_exists:
        return render_template("index.html",
                               patient_id=patient_id,
                               patient_not_found=True,
                               show_ref_vals=show_ref_vals,
                               smooth_curves=smooth_curves,
                               show_units=show_units,
                               medications ={})

    # Get diagnosis information
    has_hyperlipidemia, hyperlipidemia_date = has_disorder(fhir_data, patient_id, "hyperlipidemia")
    has_diabetes, diabetes_date = has_disorder(fhir_data, patient_id, "diabetes")

    # Format the diagnosis messages
    hyperlipidemia_msg = (
        f"Hyperlipidemia diagnosed on {datetime.strptime(hyperlipidemia_date.split('T')[0], '%Y-%m-%d').strftime('%B %d, %Y')}"
        if has_hyperlipidemia else "Hyperlipidemia not diagnosed")
    diabetes_msg = (
        f"Diabetes diagnosed on {datetime.strptime(diabetes_date.split('T')[0], '%Y-%m-%d').strftime('%B %d, %Y')}"
        if has_diabetes else "Diabetes not diagnosed")


    # Fetch data for the provided patient ID
    cholesterol = get_measurements(fhir_data, patient_id, "cholesterol")
    glucose = get_measurements(fhir_data, patient_id, "glucose")

    # Combine the data
    measurements = glucose | cholesterol
    medications = get_medications(fhir_data, patient_id, "hyperlipidemia")

    # Get data date limits for default values
    min_date, max_date = get_data_date_limits(measurements, medications)

    # If no dates provided in request but we have data, use the data limits
    if not start_date and not end_date and min_date and max_date:
        start_date = min_date.strftime('%Y-%m-%d')
        end_date = max_date.strftime('%Y-%m-%d')

    # Convert dates to datetime objects if both are provided
    alt_date_limits = None
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            alt_date_limits = [start_dt, end_dt]
        except ValueError:
            alt_date_limits = None

    # Generate reference cholesterol values only if show_ref_vals is True
    cholest_ref = cholest_reference_values(fhir_data, patient_id) if show_ref_vals else None

    # Generate plot URI and check if there is data
    image_uri = generate_plot_uri(measurements, medications, cholest_ref, smooth_curves, show_units, alt_date_limits)

    # Render the overview page with all parameters
    return render_template("index.html",
                       patient_id=patient_id,
                       image_uri=image_uri,
                       patient_not_found=False,
                       show_ref_vals=show_ref_vals,
                       smooth_curves=smooth_curves,
                       show_units=show_units,
                       start_date=start_date,
                       end_date=end_date,
                       hyperlipidemia_msg=hyperlipidemia_msg,
                       diabetes_msg=diabetes_msg,
                       medications=medications)


@app.route('/details/', methods=['GET'])
def details():
    patient_id = request.args.get('patient_id', type=int)
    if not patient_id:
        return render_template('details.html', patient_id=None, patient_not_found=True)

    patient_exists_flag, _ = patient_exists(fhir_data, patient_id)

    if not patient_exists_flag:
        return render_template('details.html', patient_id=patient_id, patient_not_found=True)

    # Fetch cholesterol, glucose measurements and medications
    cholesterol = get_measurements(fhir_data, patient_id, "cholesterol")
    glucose = get_measurements(fhir_data, patient_id, "glucose")
    medications = get_medications(fhir_data, patient_id, "hyperlipidemia")

    # Render the details page with cholesterol data
    return render_template('details.html', patient_id=patient_id, cholesterol=cholesterol,
                           glucose=glucose, medications=medications, patient_not_found=False)

if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple('localhost', 5000, app)
