import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

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
# Load Jobs from Firestore
# --------------------------
@st.cache_data(ttl=10)
def load_jobs():
    jobs_ref = db.collection("jobs")
    docs = jobs_ref.stream()
    jobs = {}
    for doc in docs:
        jobs[doc.id] = doc.to_dict()
    return jobs

jobs_data = load_jobs()

# --------------------------
# App UI - Viewer
# --------------------------
st.title("Seismos KPI Viewer")

if jobs_data:
    job_ids = list(jobs_data.keys())
    selected_job = st.selectbox("Select Job", job_ids)

    if selected_job:
        job_data = jobs_data[selected_job]
        st.subheader(f"Job Summary: {selected_job}")

        # Show Operator and Pad
        st.write(f"**Operator**: {job_data['operator']}")
        st.write(f"**Pad**: {job_data['pad']}")

        wells_info = job_data.get("wells", {})
        total_stages_all = sum(wells_info.values())
        stage_log = job_data.get("stage_log", {})

        # Determine job start date
        all_stages = list(stage_log.values())
        if all_stages:
            start_dates = [datetime.fromisoformat(s["start"]) for s in all_stages]
            job_start = min(start_dates)
            st.write(f"**Job Start**: {job_start.strftime('%Y-%m-%d %H:%M')}")

        # Pad progress summary
        st.markdown("### Pad Progress")
        well_progress = {}
        for entry in stage_log.values():
            well = entry["well"]
            well_progress[well] = well_progress.get(well, 0) + 1

        for well, total in wells_info.items():
            completed = well_progress.get(well, 0)
            st.write(f"**{well}**: {completed}/{total} stages completed")
            st.progress(completed / total if total > 0 else 0)

        pad_completed = sum(well_progress.values())
        st.write(f"**Total Pad Progress**: {pad_completed}/{total_stages_all} stages completed")
        st.progress(pad_completed / total_stages_all if total_stages_all > 0 else 0)

        # Build DataFrame for chart
        chart_data = []
        for stage_id, entry in stage_log.items():
            chart_data.append({
                "Well": entry["well"],
                "Stage": entry["stage"],
                "Start": datetime.fromisoformat(entry["start"]),
                "End": datetime.fromisoformat(entry["end"]),
                "Duration (hr)": entry["duration_hr"]
            })

        if chart_data:
            st.markdown("### Stage Timeline")
            df = pd.DataFrame(chart_data)
            fig = px.timeline(df, x_start="Start", x_end="End", y="Well", color="Stage",
                              title="Stage Timeline per Well", labels={"Stage": "Stage #"})
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No stage data available.")
else:
    st.info("No jobs found.")
