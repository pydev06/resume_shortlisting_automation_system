import sys
sys.path.insert(0, "frontend")

from api_client import api_client
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Resume Shortlisting System",
    page_icon="📄",
    layout="wide"
)

# Sidebar design
with st.sidebar:
    st.image("https://img.icons8.com/color/48/resume.png")
    st.title("📄 Resume Shortlisting")
    st.caption("AI-Powered HR Tool v1.0")
    st.markdown("---")
    
    st.markdown("**Navigation:**")
    st.page_link("pages/1_Jobs.py", label="📋 Jobs")
    st.page_link("pages/2_Resumes.py", label="📁 Resumes") 
    st.page_link("pages/3_Evaluations.py", label="📊 Evaluations")
    st.page_link("pages/4_Analytics.py", label="📈 Analytics")
    st.markdown("---")
    
    # Delete confirmation popup in sidebar
    if "deleting_job" in st.session_state and st.session_state.deleting_job:
        st.markdown("### Confirm Delete")
        job_id = st.session_state.deleting_job
        st.warning(f"⚠️ Are you sure you want to delete job **{job_id}**? This will also delete all associated resumes and evaluations.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete", type="primary", use_container_width=True, key=f"confirm_{job_id}"):
                try:
                    api_client.delete_job(job_id)
                    st.success("Job deleted successfully!")
                    st.session_state.deleting_job = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete job: {e}")
        with col2:
            if st.button("Cancel", use_container_width=True, key=f"cancel_{job_id}"):
                st.session_state.deleting_job = None
                st.rerun()
        st.markdown("---")
    
    st.markdown("**System Stats:**")
    try:
        jobs = api_client.list_jobs(page_size=1000)['jobs']
        total_jobs = len(jobs)
        st.metric("Total Jobs", total_jobs)
        
        total_resumes = sum(api_client.list_resumes(job['job_id'])['total'] for job in jobs) if jobs else 0
        st.metric("Total Resumes", total_resumes)
        
        total_evals = sum(api_client.list_evaluations(job['job_id'])['total'] for job in jobs) if jobs else 0
        st.metric("Evaluations", total_evals)
    except:
        st.write("Stats loading...")
    
    st.markdown("---")
    st.markdown("**Links:**")
    st.markdown("[GitHub](https://github.com/pydev06/resume_shortlisting_automation_system)")
    st.markdown("[Docs](https://github.com/pydev06/resume_shortlisting_automation_system#readme)")

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
