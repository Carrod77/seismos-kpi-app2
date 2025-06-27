
import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
@st.cache_resource
def init_firestore():
    cred = credentials.Certificate("seismoskpi-firebase-adminsdk-fbsvc-16d14ae4a5.json")
    firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firestore()

# Load existing jobs
@st.cache_data(ttl=10)
def load_jobs():
    jobs_ref = db.collection("jobs")
    docs = jobs_ref.stream()
    return {doc.id: doc.to_dict() for doc in docs}

jobs_data = load_jobs()

st.title("Seismos KPI Editor")

mode = st.radio("Mode", ["Edit Existing Job", "Create New Job"])

if mode == "Create New Job":
    st.subheader("Create a New Job")
    new_job_id = st.text_input("Job ID")
    operator = st.text_input("Operator")
    pad = st.text_input("Pad Name")
    num_wells = st.number_input("Number of Wells", min_value=1, step=1)

    well_data = {}
    for i in range(num_wells):
        col1, col2 = st.columns(2)
        with col1:
            well_name = st.text_input(f"Well {i+1} Name", key=f"name_{i}")
        with col2:
            total_stages = st.number_input(f"Stages for Well {i+1}", key=f"stage_{i}", min_value=1, step=1)
        if well_name:
            well_data[well_name] = int(total_stages)

    if st.button("Create Job"):
        if new_job_id and operator and pad and well_data:
            db.collection("jobs").document(new_job_id).set({
                "operator": operator,
                "pad": pad,
                "wells": well_data,
                "stage_log": {}
            })
            st.success(f"Job {new_job_id} created successfully.")
        else:
            st.warning("Please fill out all fields.")

elif mode == "Edit Existing Job" and jobs_data:
    job_ids = list(jobs_data.keys())
    selected_job = st.selectbox("Select Job", job_ids)
    selected_job_data = jobs_data[selected_job]
    wells = list(selected_job_data.get("wells", {}).keys())

    selected_well = st.selectbox("Select Well", wells)

    uploaded_file = st.file_uploader("Upload KPI Excel for selected well", type=["xlsx", "xlsm"])
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file, sheet_name="KPI")
            required_cols = ["Stage", "Start Time", "End Time"]
            if not all(col in df.columns for col in required_cols):
                st.error("KPI sheet must contain: Stage, Start Time, End Time")
            else:
                new_stage_log = {}
                for _, row in df.iterrows():
                    stage = int(row["Stage"])
                    start = pd.to_datetime(row["Start Time"])
                    end = pd.to_datetime(row["End Time"])
                    duration = (end - start).total_seconds() / 3600
                    new_stage_log[f"{selected_well}_stage_{stage}"] = {
                        "stage": stage,
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                        "duration_hr": round(duration, 2),
                        "well": selected_well
                    }

                # Update Firestore
                doc_ref = db.collection("jobs").document(selected_job)
                doc_data = doc_ref.get().to_dict()
                doc_data["stage_log"].update(new_stage_log)
                doc_ref.set(doc_data)
                st.success(f"Uploaded {len(new_stage_log)} stages to {selected_well}")
        except Exception as e:
            st.error(f"Error reading Excel: {e}")
    else:
        st.info("Please upload an Excel file.")
