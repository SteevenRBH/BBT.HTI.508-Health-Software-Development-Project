import json
from datetime import datetime, timedelta

# --- Constants ---

JSON_DATABASE = 'json_database.json'

# LOINC measurement codes
CHOLESTEROL = {"Cholest SerPl-mCnc"}

GLUCOSE = {
    "Glucose SerPl-mCnc",
    "Glucose Bld-mCnc",
    "Glucose Ur Strip-mCnc",
    "Glucose CSF-mCnc",
    "Glucose p fast SerPl-mCnc"
}

# SNOMED codes for metabolic conditions
HYPERLIPIDEMIA_CODES = {
    "55822004",     # SNOMED code for hyperlipidemia
    "267432004"     # SNOMED code for pure hypercholesterolemia
}

DIABETES_CODES = {
    "327051000000109",  # SNOMED code for diabetes mellitus
    "44054006",         # SNOMED code for Type 1 diabetes mellitus
    "44054105"          # SNOMED code for Type 2 diabetes mellitus
}

# RxNorm codes for medications
HYPERLIP_MED_CODES = {"312961", "198211", "262095", "543354", "617318", "859749"}


def load_patient_data():
    """
    Loads patient data from a JSON database file and returns a Python object.
    """
    with open(JSON_DATABASE, 'r', encoding='utf-8') as f:
        return json.load(f)


def patient_exists(fhir_data, patient_id_to_check=None):
    """
    Checks if a patient with a given ID exists in the provided FHIR data. Also collects
    and returns a set of all existing patient IDs extracted from the FHIR data.

    Parameters:
        fhir_data: list
            A list where each element contains resources from FHIR data. Each resource
            is expected to be a dictionary with a "resource" key containing a nested
            dictionary.
        patient_id_to_check: int
            The ID of the patient to check for existence in the FHIR data.

    Returns:
        tuple
            A tuple where the first element is a boolean indicating whether the patient
            ID exists in the FHIR data, and the second element is a set containing all
            patient IDs found in the FHIR data.
    """
    existing_patients = set()
    for patient_resources in fhir_data:
        for entry in patient_resources:
            resource = entry["resource"]
            if resource["resourceType"] == "Patient":
                patient_id = resource["id"]
                if patient_id:
                    existing_patients.add(int(patient_id))
    return patient_id_to_check in existing_patients, existing_patients


def has_disorder(fhir_data, patient_id, disorder):
    """
    Check if a patient has a metabolic disorder based on their Condition resources.

    :param fhir_data: List containing FHIR JSON database (list of patient resource lists).
    :param patient_id: ID of the patient to check.
    :param disorder: The metabolic disorder to check.
    :return: True if the patient has the specified disorder, False otherwise.
    :return: Datetime of the diagnosis if the patient has the specified disorder, None otherwise.
    """
    for patient_resources in fhir_data:
        for entry in patient_resources:
            resource = entry["resource"]
            if (resource["resourceType"] == "Condition" and
                    resource["patient"]["reference"] == f"Patient/{patient_id}"):
                coding_list = resource["code"]["coding"]
                for coding in coding_list:
                    code = coding["code"]
                    display = coding["display"].lower()
                    if disorder.lower() == "hyperlipidemia":
                        if code in HYPERLIPIDEMIA_CODES or "hyperlipidemia" in display:
                            return True, resource["onsetDateTime"]
                    elif disorder.lower() == "diabetes":
                        if code in DIABETES_CODES or "diabetes" in display:
                            return True, resource["onsetDateTime"]
    return False, None


def get_patients_with_disorder(fhir_data, disorder):
    """
    Build a list of patients with a specific disorder.

    :param fhir_data: List of FHIR resource entries.
    :param disorder: The disorder to check for (e.g., 'hyperlipidemia').
    :return: List of patient IDs diagnosed with the disorder.
    """
    # All available patient IDs
    _, existing_patients = patient_exists(fhir_data)

    # Patients diagnosed with the specified disorder
    patient_ids = set()
    for patient_id in existing_patients:
        diagnosed, _ = has_disorder(fhir_data, patient_id, disorder)
        if diagnosed:
            patient_ids.add(patient_id)

    return list(patient_ids)


def get_measurements(fhir_data, patient_id, lab_assay):
    """
    Returns the observations for a given set of laboratory tests.

    :param fhir_data: FHIR JSON structure.
    :param patient_id: ID of the patient whose measurements are to extract.
    :param lab_assay: The laboratory assay to check for (e.g., 'cholesterol').
    :return: Dictionary mapping measurement code to {date: [value, unit]}.
    """
    measurement_codes = {}

    if lab_assay.lower() == "cholesterol":
        measurement_codes = CHOLESTEROL
    elif lab_assay.lower() == "glucose":
        measurement_codes = GLUCOSE

    measurement_data = {code: {} for code in measurement_codes}

    for patient_resources in fhir_data:
        for entry in patient_resources:
            resource = entry["resource"]
            if (resource["resourceType"] == "Observation" and
                    resource["subject"]["reference"] == f"Patient/{patient_id}"):
                display_code = resource["code"]["coding"][0]["display"]
                if display_code in measurement_codes:
                    date = datetime.fromisoformat(resource["effectiveDateTime"])
                    value = resource["valueQuantity"]["value"]
                    unit = resource["valueQuantity"]["unit"]
                    if value is not None:
                        if date not in measurement_data[display_code]:
                            measurement_data[display_code][date] = []
                        measurement_data[display_code][date].append({"value": value, "unit": unit})

    return measurement_data


def get_medications(fhir_data, patient_id, disorder):
    """
    Returns the medication orders for a given set of medications.

    :param fhir_data: FHIR JSON structure.
    :param patient_id: ID of the patient whose medications are to extract.
    :param disorder: The disorder whose medication is to check for (e.g., 'hyperlipidemia').
    :return: Dictionary mapping medication code to a list of {date, name, dosage}.
    """
    medication_codes = {}

    if disorder.lower() == "hyperlipidemia":
        medication_codes = HYPERLIP_MED_CODES
    elif disorder.lower() == "diabetes":
        medication_codes = HYPERLIP_MED_CODES ########## Update if diabetes medication is included

    medication_data = {code: [] for code in medication_codes}

    for patient_resources in fhir_data:
        for entry in patient_resources:
            resource = entry["resource"]
            if (resource["resourceType"] == "MedicationOrder" and
                    resource["patient"]["reference"] == f"Patient/{patient_id}"):
                code = resource["medicationCodeableConcept"]["coding"][0]["code"]
                display = resource["medicationCodeableConcept"]["coding"][0]["display"]

                if code in medication_codes:
                    try:
                        date_str = resource["dosageInstruction"][0]["timing"]["repeat"]["boundsPeriod"]["start"]
                        date = datetime.fromisoformat(date_str)
                    except (IndexError, KeyError, TypeError):
                        date = None

                    try:
                        dosage_text = resource["dosageInstruction"][0]["text"]
                    except (IndexError, KeyError, TypeError):
                        dosage_text = "No instructions provided"

                    medication_data[code].append({
                        "date": date,
                        "name": display,
                        "dosage": dosage_text
                    })

    return medication_data


def cholest_reference_values(fhir_data, patient_id):
    """
    Calculates reference values for cholesterol measurements based on patient's age at measurement dates.

    Parameters:
        fhir_data (dict): The FHIR data dictionary containing patient and observation information
        patient_id (int): The ID of the patient to analyze

    Returns:
        dict: Dictionary with dates as keys and two-element arrays as values containing reference ranges
              [170, 199] for age < 20 years
              [199, 239] for age >= 20 years
    """
    # Get the patient's birthdate and fetches today's date
    birth_date = None
    today_date = datetime.today()

    for patient_resources in fhir_data:
        for entry in patient_resources:
            resource = entry["resource"]
            if resource["resourceType"] == "Patient" and resource["id"] == f"{patient_id}":
                birth_date = datetime.fromisoformat(resource["birthDate"])
    if birth_date is None:
        return None

    twentieth_birthday = birth_date + timedelta(days=20*365)

    # Get cholesterol measurements
    cholesterol_measurements = get_measurements(fhir_data, patient_id, "Cholesterol")

    # Initialize measurement_dates as empty list
    measurement_dates = []

    # Only process dates if there are actual measurements
    if any(measurements for measurements in cholesterol_measurements.values()):
        for entry in cholesterol_measurements.values():
            for date in entry.keys():
                measurement_dates.append(date)

    all_dates = [birth_date] + [twentieth_birthday] + measurement_dates + [today_date]
    all_dates = sorted(set(all_dates))  # Remove any potential duplicates and ensure ordering

    borderline_values = {}

    for date in all_dates:
        age = (date - birth_date).days / 365
        if age < 20:
            borderline_values[date] = [170, 199]
        else:
            borderline_values[date] = [199, 239]

    return borderline_values


if __name__=="__main__":
### ALL THE CODE BELOW IS FOR TESTING PURPOSES ONLY ###
   # Importing the database
   fhir_data = load_patient_data()

   # Interesting patients
   patient_ID = 736230 # 2113340 #736230 #1137192 #8888804 "8888802 #767980
   # glucose = get_measurements(fhir_data, patient_ID, "Glucose")
   # cholesterol = get_measurements(fhir_data, patient_ID, "Cholesterol")
   # print(glucose)
   # print(cholesterol)

   cholest_reference_values(fhir_data, patient_ID)


#
   hyperlip_patients = get_patients_with_disorder(fhir_data, "hyperlipidemia")
   diabetes_patients = get_patients_with_disorder(fhir_data, "diabetes")
   hyperlip_medication = get_medications(fhir_data, patient_ID, "hyperlipidemia")

   print(hyperlip_patients)
   print(diabetes_patients)
   print(hyperlip_medication)
#
#    for patient_ID in diabetes_patients:
#
#       glucose = get_measurements(fhir_data, patient_ID, GLUCOSE)
   cholesterol = get_measurements(fhir_data, patient_ID, "CHOLESTEROL")
   print(cholesterol)
#
#        hyperlip_medication = get_medications(fhir_data, patient_ID, HYPERLIP_MED_CODES)
#
        # fig = plot_measurements(glucose | cholesterol, hyperlip_medication)
