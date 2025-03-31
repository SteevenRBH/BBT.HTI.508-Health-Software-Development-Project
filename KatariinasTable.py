import pandas as pd
import json
from datetime import date, datetime

# Our JSON database
JSON_DATABASE = 'json_database.json'

# fullUrl is the full "address" under which all patients are in the "server" (which is now just py database).
fullUrl = "http://tutsgnfhir.com"

with open(JSON_DATABASE, 'rb') as json_file:
    patient_json = json.load(json_file)


"""
List of Patients with diagnosed Hyperlipidemia (check with team code and 
Katariinas code) and related info:

(First check wo has cholesterol measurements from whole patient data, then 
active medication from whole patientdata, then glucose values for those who has 
active medication)

ID      // Diagnose// Lab for cholest // Medication // Lab for glucose

1768562  // YES // Has total cholesterol values x 1
2347217  // YES // Has total cholesterol values x 2 
731673 // YES //
621799 // YES // Has total cholesterol values x 2 //
644201  // CANT FIND THIS ID!! //
8888801  // YES // Has total cholesterol values x 11 // 
2113340  // YES // Has total cholesterol values x 1 // Active hyperlipidemia medication // Glucose SerPl-mCnc x 2
1272431  //YES // Has total cholesterol values x 3 //
1098667  // YES // no lab and med
724111   // YES //
2169591  // YES // Has total cholesterol values x 1 //
2354220 //YES // Has total cholesterol values x 2 //
"""

"""
Patient without diagnosed Hyperlipidemia, but with cholesterol lab results ad/or 
active medication: 

665677 // NO // Has total cholesterol values x 1 //
8888803 // NO // Has total cholesterol values x 3 //
8888804 // NO // Has total cholesterol values x 12 //
1869612 // NO // Has total cholesterol values x 2 //
1137192 // NO // Has total cholesterol values x 6 // Active Hyperlipidemia Medication // Glucose SerPl-mCnc x 2 
1157764 // NO // Has total cholesterol values x 1 //
1288992 // NO // Has total cholesterol values x 1 //

736230 // NO // NO // Active hyperlipidemia medication // NO 
767980 // NO // NO // Active hyperlipidemia medication // Glucose SerPl-mCnc x 1
"""

"""
Patient with values we are interested in:

Patient under has one glocose measurement before statin medication.
767980 // NO // NO // Active hyperlipidemia medication // Glucose SerPl-mCnc x 1

Patient under has started his medication in 2008 and after this, no clucose measurements 
1137192 // NO // Has total cholesterol values x 6 // Active Hyperlipidemia Medication // Glucose SerPl-mCnc x 2 

Patient under has started his medication at the same date as the laboratory values are measured. (or one day earlier)
2113340  // YES // Has total cholesterol values x 1 // Active hyperlipidemia medication // Glucose SerPl-mCnc x 2
"""




def getAllDataForOnePatient(patient_id):
    #From the Moodle-page file. Search all info for the certain ID
    #Return: List, All information related to certain ID
    requesturl = fullUrl + "/Patient/" + patient_id
    for patient in patient_json:
        if patient[0]['fullUrl'] == requesturl:
            patient_info = patient  # ['resource']

            return patient_info


def getDatesAndStatinMedication(patient_id):
    # Get dates and statin medication for one patient
    # Return: Dict, which include list of related items

    statinData = {
        'Date': [],
        'StatinMed': [],
    }

    all_data = getAllDataForOnePatient(patient_id)
    hyperlip_med_codes = {"312961", "198211", "262095", "543354", "617318",
                          "859749"}
    i = 0
    # Go through data
    for item in all_data:
        # Go stops when resource type is MedicationOrder
        if all_data[i]['resource']['resourceType'] == 'MedicationOrder':
            # Go through all medication codes for hyperlipidemia
            for code in hyperlip_med_codes:

                if all_data[i]['resource']['status'] == 'active' and \
                        all_data[i]['resource']['medicationCodeableConcept'][
                            'coding'][0]['code'] == code:
                    statinData['StatinMed'].append(
                        all_data[i]['resource']['medicationCodeableConcept'][
                            'text'])
                    try:
                        statinData['Date'].append(all_data[i]['resource']['dosageInstruction'][0]['timing']['repeat']['boundsPeriod']['start'])
                    except:
                        statinData['Date'].append('no date')

        i += 1

    return statinData


def getDatesAndCholesterolLabresults(patient_id):
    # Get dates and "Cholest SerPl-mCnc" -measurements for one patient
    # Return: Dict, which include list of related items

    cholesterolLabData = {
        'Date': [],
        'Cholesterol': [],
    }

    all_data = getAllDataForOnePatient(patient_id)
    i = 0
    # Go through data
    for item in all_data:
        # Go stops when resource type is Observation
        if all_data[i]['resource']['resourceType'] == 'Observation':
            if all_data[i]['resource']['code']['text'] == 'Cholest SerPl-mCnc':
                cholesterolLabData['Cholesterol'].append(all_data[i]['resource']['valueQuantity']['value'])
                try:
                    cholesterolLabData['Date'].append(all_data[i]['resource']['effectiveDateTime'])
                except:
                    cholesterolLabData['Date'].append('no date')
        i += 1

    return cholesterolLabData


def getDatesAndClucoseLabResults(patient_id):
    # Get dates and "Glucose SerPl-mCnc" -measurements for one patient
    # Return: Dict, which include list of related items

    clucoseLabData = {
        'Date': [],
        'Glucose': [],
    }

    all_data = getAllDataForOnePatient(patient_id)
    i = 0
    # Go through data
    for item in all_data:
        # Go stops when resource type is Observation
        if all_data[i]['resource']['resourceType'] == 'Observation':
            if all_data[i]['resource']['code']['text'] == 'Glucose SerPl-mCnc':
                clucoseLabData['Glucose'].append(
                    all_data[i]['resource']['valueQuantity']['value'])
                try:
                    clucoseLabData['Date'].append(
                        all_data[i]['resource']['effectiveDateTime'])
                except:
                    clucoseLabData['Date'].append('no date')
        i += 1

    return clucoseLabData


#Creates data-frames to create table
df1 = pd.DataFrame(getDatesAndStatinMedication('1137192'))
df2 = pd.DataFrame(getDatesAndCholesterolLabresults('1137192'))
df3 = pd.DataFrame(getDatesAndClucoseLabResults('1137192'))

# Merge the tables on the 'Date' column
merged_df = pd.merge(df1, df2, on='Date', how='outer')  # 'outer' keeps all dates from all tables
merged_df = pd.merge(merged_df, df3, on='Date', how='outer')  # Merge the third table

#Ensures all rows are shown
pd.set_option('display.max_rows', None)  # None will show all rows
pd.set_option('display.max_columns', None)
# Display the merged DataFrame
print(merged_df)