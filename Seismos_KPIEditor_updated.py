
import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import datetime

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
# Upload and Process Stage File
# --------------------------
def process_stage_file(file, job_id, selected_well):
    try:
        df = pd.read_excel(file, sheet_name="KPI")
        for _, row in df.iterrows():
            try:
                stage_num = int(row["Stage #"])
                start = pd.to_datetime(row["Start Time"]).isoformat()
                end = pd.to_datetime(row["End Time"]).isoformat()
                duration_hr = float(row["Stage Duration (hr)"])

                db.collection("jobs").document(job_id).update({
                    f"stage_log.{job_id}_{selected_well}_stage{stage_num}": {
                        "well": selected_well,
                        "stage": stage_num,
                        "start": start,
                        "end": end,
                        "duration_hr": duration_hr
                    }
                })
            except Exception as e:
                st.warning(f"Skipping row due to error: {e}")
        st.success("File uploaded and stage log updated.")
    except Exception as e:
        st.error(f"Failed to read Excel: {e}")

# --------------------------
# App UI - Editor
# --------------------------
st.title("Seismos KPI Editor")

# Select Job
jobs_ref = db.collection("jobs")
jobs = [doc.id for doc in jobs_ref.stream()]
selected_job = st.selectbox("Select Job", jobs)

if selected_job:
    job_doc = db.collection("jobs").document(selected_job).get()
    if job_doc.exists:
        job_data = job_doc.to_dict()
        wells = list(job_data.get("wells", {}).keys())
        selected_well = st.selectbox("Select Well", wells)

        uploaded_file = st.file_uploader("Upload Stage Report Excel (KPI Sheet)", type=["xlsx"])

        if uploaded_file and selected_well:
            if st.button("Process File"):
                process_stage_file(uploaded_file, selected_job, selected_well)
    else:
        st.error("Selected job not found.")
else:
    st.info("Please select a job to begin.")
