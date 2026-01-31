import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Resume Shortlisting System",
    page_icon="📄",
    layout="wide"
)

st.title("Resume Shortlisting System")
st.markdown("An internal HR tool for managing job postings, uploading resumes, and automatically evaluating candidates using AI-powered skill extraction and matching.")

st.markdown("### Navigation")
st.write("Use the sidebar to navigate between:")
st.write("- 📋 **Jobs**: Create, edit, and manage job postings")
st.write("- 📁 **Resumes**: Upload and manage candidate resumes")
st.write("- 📊 **Evaluations**: View AI-powered resume evaluations")

st.markdown("### Quick Start")
st.write("1. Start by creating a job posting")
st.write("2. Upload candidate resumes")
st.write("3. Run AI evaluations to shortlist candidates")

# Footer
st.caption("Resume Shortlisting System v1.0")
