
import streamlit as st
import pandas as pd
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import io

# --------------------------
# Firebase Setup
# --------------------------
@st.cache_resource
def init_firestore():
    cred = credentials.Certificate("seismoskpi-firebase-adminsdk-fbsvc-16d14ae4a5.json")
    firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firestore()

# --------------------------
# App UI - KPI Editor
# --------------------------
st.title("Seismos KPI Editor")

mode = st.radio("Mode", ["Edit Existing Job", "Create New Job"])

jobs_ref = db.collection("jobs")
jobs_data = {doc.id: doc.to_dict() for doc in jobs_ref.stream()}

if mode == "Edit Existing Job":
    job_ids = list(jobs_data.keys())
    selected_job = st.selectbox("Select Job", job_ids)

    if selected_job:
        job_info = jobs_data[selected_job]
        wells = list(job_info.get("wells", {}).keys())
        selected_well = st.selectbox("Select Well", wells)
else:
    selected_job = st.text_input("Enter New Job ID (e.g. 25-052)")
    operator = st.text_input("Operator Name")
    pad = st.text_input("Pad Name")
    well_count = st.number_input("Number of Wells", min_value=1, step=1)
    wells = {}
    for i in range(well_count):
        well_name = st.text_input(f"Well #{i+1} Name")
        stages = st.number_input(f"Total Stages for {well_name}", min_value=1, step=1)
        if well_name:
            wells[well_name] = stages
    selected_well = st.selectbox("Select Well", list(wells.keys()) if wells else [])

uploaded_file = st.file_uploader("Upload KPI Excel for selected well", type=["xlsx", "xlsm"])

if uploaded_file and selected_job and selected_well:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="KPI", engine="openpyxl")
        df.columns = [col.strip().lower() for col in df.columns]
        required = ["stage", "start time", "end time"]
        if not all(col in df.columns for col in required):
            st.error("KPI sheet must contain: Stage, Start Time, End Time")
        else:
            stage_log = {}
            for _, row in df.iterrows():
                try:
                    stage = int(row["stage"])
                    start = pd.to_datetime(row["start time"])
                    end = pd.to_datetime(row["end time"])
                    duration = (end - start).total_seconds() / 3600
                    stage_id = f"{selected_well}_{stage}"
                    stage_log[stage_id] = {
                        "well": selected_well,
                        "stage": stage,
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                        "duration_hr": round(duration, 2)
                    }
                except:
                    continue

            if mode == "Edit Existing Job":
                jobs_ref.document(selected_job).update({f"stage_log": firestore.ArrayUnion(list(stage_log.values()))})
            else:
                jobs_ref.document(selected_job).set({
                    "operator": operator,
                    "pad": pad,
                    "wells": wells,
                    "stage_log": stage_log
                })

            st.success(f"Uploaded {len(stage_log)} stage records for {selected_well} in job {selected_job}")
    except Exception as e:
        st.error(f"Error reading file: {e}")
