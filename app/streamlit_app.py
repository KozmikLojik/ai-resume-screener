import os

import requests
import streamlit as st

st.set_page_config(page_title="AI Resume Screener", layout="centered")
st.title("AI Resume Screener")
st.markdown("### Upload a resume and compare it with a job description")

api_url = os.getenv("RESUME_API_URL", "http://127.0.0.1:8000").rstrip("/") + "/match"
resume_file = st.file_uploader("Resume (PDF)", type=["pdf"])
job_description = st.text_area("Job description", height=200)

if st.button("Match resume", type="primary"):
    if not resume_file or not job_description.strip():
        st.warning("Upload a PDF resume and enter a job description.")
    else:
        with st.spinner("Analyzing the resume…"):
            files = {"resume": (resume_file.name, resume_file.getvalue(), "application/pdf")}
            try:
                response = requests.post(
                    api_url,
                    files=files,
                    data={"job_description": job_description},
                    timeout=(5, 90),
                )
                response.raise_for_status()
                score = float(response.json()["match_score"])
                if not 0 <= score <= 100:
                    raise ValueError("The API returned an invalid score.")
            except requests.HTTPError as error:
                detail = error.response.json().get("detail", "The resume could not be analyzed.")
                st.error(detail)
            except (requests.RequestException, ValueError, KeyError) as error:
                st.error(f"Could not analyze the resume: {error}")
            else:
                st.metric("Resume match", f"{score:.1f}%")
                st.caption("This score is an automated similarity estimate, not a hiring recommendation.")
