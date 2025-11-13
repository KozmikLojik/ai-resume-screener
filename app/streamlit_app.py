import streamlit as st
import requests
import PyPDF2
from io import BytesIO

st.set_page_config(page_title="AI Resume Screener", layout="centered")
st.title("AI Resume Screener")
st.markdown("### *Upload Resume + Paste JD → Get Match %*")

# API URL (change after deployment)
API_URL = "http://localhost:8000/match"  # Change to Render URL later

col1, col2 = st.columns(2)

with col1:
    resume_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
with col2:
    jd_text = st.text_area("Paste Job Description", height=200)

if st.button("Match Resume", type="primary"):
    if resume_file and jd_text:
        with st.spinner("Analyzing..."):
            files = {"resume": (resume_file.name, resume_file.getvalue(), "application/pdf")}
            data = {"job_description": jd_text}
            try:
                response = requests.post(API_URL, files=files, data=data)
                if response.status_code == 200:
                    score = response.json()["match_score"]
                    st.success(f"Match Score: **{score}%**")
                    if score > 80:
                        st.balloons()
                    elif score > 60:
                        st.info("Moderate match")
                    else:
                        st.warning("Low match")
                else:
                    st.error("API Error")
            except:
                st.error("Cannot connect to API. Run `python run_api.py` first.")
    else:
        st.warning("Please upload resume and paste JD")