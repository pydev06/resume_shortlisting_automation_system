import sys

sys.path.insert(0, "frontend")

import streamlit as st
from api_client import api_client

# Page configuration
st.set_page_config(
    page_title="Resume Shortlisting - Jobs",
    page_icon="📄",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .status-ok {
        background-color: #28a745;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
    }
    .status-not-ok {
        background-color: #dc3545;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
    }
    .status-pending {
        background-color: #ffc107;
        color: black;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .score-high { color: #28a745; font-weight: bold; }
    .score-medium { color: #ffc107; font-weight: bold; }
    .score-low { color: #dc3545; font-weight: bold; }
    @media (max-width: 768px) {
        .main-header { font-size: 1.5rem; margin-bottom: 0.5rem; }
        .metric-card { padding: 0.5rem; margin-bottom: 0.5rem; }
        .stButton button { width: 100% !important; margin-bottom: 0.5rem; }
        .stColumn { width: 100% !important; margin-bottom: 1rem; }
    }
</style>
""", unsafe_allow_html=True)


def get_score_class(score: float) -> str:
    if score >= 70:
        return "score-high"
    elif score >= 50:
        return "score-medium"
    return "score-low"


def format_status_badge(status: str) -> str:
    if status == "OK to Proceed":
        return '<span class="status-ok">✓ OK to Proceed</span>'
    elif status == "Not OK":
        return '<span class="status-not-ok">✗ Not OK</span>'
    return '<span class="status-pending">⏳ Pending</span>'


# Initialize session state
if "current_page" not in st.session_state:
    st.session_state.current_page = "jobs"
if "selected_job" not in st.session_state:
    st.session_state.selected_job = None

# Job creation form state
if "job_title" not in st.session_state:
    st.session_state.job_title = ""
if "job_description" not in st.session_state:
    st.session_state.job_description = ""
if "form_key" not in st.session_state:
    st.session_state.form_key = 0
if "job_success_message" not in st.session_state:
    st.session_state.job_success_message = None
if "job_success_timestamp" not in st.session_state:
    st.session_state.job_success_timestamp = None
if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0
if "form_clear_timestamp" not in st.session_state:
    st.session_state.form_clear_timestamp = None

# Check if form should be cleared after delay
if st.session_state.form_clear_timestamp and time.time() - st.session_state.form_clear_timestamp > 3:
    st.session_state.form_key += 1
    st.session_state.form_clear_timestamp = None

st.markdown('<p class="main-header">📋 Job Management</p>', unsafe_allow_html=True)

# Create Job Section
with st.expander("➕ Create New Job", expanded=False):
    with st.form(key=f"create_job_form_{st.session_state.form_key}"):
        job_title = st.text_input("Job Title", placeholder="e.g., Senior Python Developer")
        job_description = st.text_area(
            "Job Description",
            placeholder="Enter the full job description including required skills, responsibilities, and qualifications...",
            height=200
        )
        
        submitted = st.form_submit_button("Create Job", use_container_width=True)
        
        if submitted:
            if not job_title or not job_description:
                st.error("Please fill in both title and description")
            else:
                try:
                    result = api_client.create_job(job_title, job_description)
                    success_msg = f"Job created successfully! JOBID: {result['job_id']}"
                    st.toast(success_msg, icon="✅")
                    # Auto-clear the form
                    st.session_state.form_key += 1
                    # Close any open edit modal
                    st.session_state.editing_job = None
                except Exception as e:
                    st.error(f"Failed to create job: {e}")

# Show success message outside expander
if st.session_state.job_success_message and st.session_state.job_success_timestamp:
    elapsed = time.time() - st.session_state.job_success_timestamp
    if elapsed <= 3:
        st.success(st.session_state.job_success_message)
    else:
        st.session_state.job_success_message = None
        st.session_state.job_success_timestamp = None

# Search and List Jobs
col1, col2 = st.columns([3, 1])
with col1:
    search_query = st.text_input("🔍 Search jobs", placeholder="Search by title or JOBID...")
with col2:
    page_size = st.selectbox("Per page", [10, 25, 50], index=0)

try:
    jobs_data = api_client.list_jobs(query=search_query if search_query else None, page_size=page_size)
    jobs = jobs_data.get("jobs", [])
    
    if not jobs:
        st.info("No jobs found. Create your first job above!")
    else:
        st.markdown(f"**Showing {len(jobs)} of {jobs_data.get('total', 0)} jobs**")
        
        for job in jobs:
            with st.container():
                col1, col2, col3 = st.columns([1, 4, 2])
                
                with col1:
                    st.markdown(f"**`{job['job_id']}`**")
                
                with col2:
                    st.markdown(f"**{job['title']}**")
                    st.caption(f"Created: {job['created_at'][:10]}")
                
                with col3:
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    with btn_col1:
                        if st.button("📁", key=f"resumes_{job['job_id']}", help="View Resumes"):
                            st.session_state.selected_job = job
                            st.switch_page("pages/2_Resumes.py")
                    with btn_col2:
                        if st.button("✏️", key=f"edit_{job['job_id']}", help="Edit Job"):
                            st.session_state.editing_job = job
                    with btn_col3:
                        if st.button("🗑️", key=f"delete_{job['job_id']}", help="Delete Job"):
                            st.session_state.deleting_job = job['job_id']
                
                st.markdown("---")
        
        # Handle edit modal
        if "editing_job" in st.session_state and st.session_state.editing_job:
            job = st.session_state.editing_job
            st.markdown(f"### Edit Job: {job['job_id']}")
            with st.form("edit_job_form"):
                new_title = st.text_input("Job Title", value=job['title'])
                new_description = st.text_area("Job Description", value=job['description'], height=200)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Save Changes", use_container_width=True):
                        try:
                            api_client.update_job(job['job_id'], title=new_title, description=new_description)
                            st.success("Job updated successfully!")
                            st.session_state.editing_job = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update job: {e}")
                with col2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state.editing_job = None
                        st.rerun()
        
        # Handle delete confirmation
        if "deleting_job" in st.session_state and st.session_state.deleting_job:
            job_id = st.session_state.deleting_job
            st.warning(f"⚠️ Are you sure you want to delete job **{job_id}**? This will also delete all associated resumes and evaluations.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, Delete", type="primary", use_container_width=True):
                    try:
                        api_client.delete_job(job_id)
                        st.success("Job deleted successfully!")
                        st.session_state.deleting_job = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete job: {e}")
            with col2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.deleting_job = None
                    st.rerun()
                    
except Exception as e:
    st.error(f"Failed to load jobs: {e}")

# Footer
st.caption("Resume Shortlisting System v1.0 - Jobs")
