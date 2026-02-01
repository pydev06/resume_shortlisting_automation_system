import sys

sys.path.insert(0, "frontend")

from api_client import api_client
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Resume Shortlisting - Resumes",
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

# Initialize session state
if "current_page" not in st.session_state:
    st.session_state.current_page = "resumes"
if "selected_job" not in st.session_state:
    st.session_state.selected_job = None
if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0

st.markdown('<p class="main-header">📁 Resume Management</p>', unsafe_allow_html=True)

# Job selector
try:
    jobs_data = api_client.list_jobs(page_size=100)
    jobs = jobs_data.get("jobs", [])
    
    if not jobs:
        st.warning("No jobs found. Please create a job first.")
    else:
        job_options = {f"{j['job_id']} - {j['title']}": j for j in jobs}
        
        # Pre-select job if coming from jobs page
        default_index = 0
        if st.session_state.selected_job:
            for i, key in enumerate(job_options.keys()):
                if key.startswith(st.session_state.selected_job['job_id']):
                    default_index = i
                    break
        
        selected_job_key = st.selectbox(
            "Select Job",
            options=list(job_options.keys()),
            index=default_index
        )
        selected_job = job_options[selected_job_key]
        
        st.markdown("---")
        
        # Upload Section
        with st.expander("📤 Upload Resumes", expanded=True):
            uploaded_files = st.file_uploader(
                "Upload resume files (PDF or DOCX)",
                type=["pdf", "docx"],
                accept_multiple_files=True,
                key=f"file_uploader_{st.session_state.upload_key}"
            )
            
            if uploaded_files:
                if st.button("Upload All", type="primary", use_container_width=True):
                    progress = st.progress(0)
                    success_count = 0
                    error_messages = []
                    
                    for i, file in enumerate(uploaded_files):
                        try:
                            api_client.upload_resume(selected_job['job_id'], file)
                            success_count += 1
                        except Exception as e:
                            error_messages.append(f"Failed to upload {file.name}: {e}")
                        progress.progress((i + 1) / len(uploaded_files))
                    
                    if success_count > 0:
                        st.toast(f"Uploaded {success_count} of {len(uploaded_files)} resumes", icon="✅")
                    
                    for error_msg in error_messages:
                        st.error(error_msg)
                    
                    # Clear the file uploader after processing
                    st.session_state.upload_key += 1
        
        # Clear uploader button
        if st.button("🧹 Clear Uploader", use_container_width=True):
            st.session_state.upload_key += 1
            st.rerun()
        
        # ZIP Upload Section
        with st.expander("📦 Upload ZIP Archive", expanded=False):
            zip_file = st.file_uploader(
                "Upload ZIP containing resumes (PDF/DOCX only)",
                type=["zip"],
                key="zip_uploader"
            )
            
            if zip_file and st.button("Upload from ZIP", type="primary", use_container_width=True):
                with st.spinner("Extracting and uploading resumes from ZIP..."):
                    try:
                        result = api_client.upload_zip_resumes(selected_job['job_id'], zip_file)
                        st.toast(f"Successfully uploaded {len(result)} resumes from ZIP!", icon="✅")
                        st.session_state.upload_key += 1
                        st.rerun()
                    except Exception as e:
                        st.error(f"Upload failed: {str(e)}")
        
        st.markdown("---")
        
        # List Resumes
        st.markdown(f"### Resumes for {selected_job['job_id']} - {selected_job['title']}")
        
        try:
            resumes_data = api_client.list_resumes(selected_job['job_id'])
            resumes = resumes_data.get("resumes", [])
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Total: {resumes_data.get('total', 0)} resumes**")
            with col2:
                if resumes and st.button("🗑️ Delete All", type="secondary"):
                    st.session_state.confirm_delete_all = True
            
            if "confirm_delete_all" in st.session_state and st.session_state.confirm_delete_all:
                st.warning("⚠️ Are you sure you want to delete ALL resumes for this job?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Yes, Delete All", type="primary"):
                        try:
                            result = api_client.delete_all_resumes(selected_job['job_id'])
                            st.success(f"Deleted {result.get('count', 0)} resumes")
                            st.session_state.confirm_delete_all = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete resumes: {e}")
                with col2:
                    if st.button("Cancel"):
                        st.session_state.confirm_delete_all = False
                        st.rerun()
            
            if not resumes:
                st.info("No resumes uploaded yet. Upload resumes above!")
            else:
                for resume in resumes:
                    with st.container():
                        col1, col2, col3 = st.columns([4, 2, 1])
                        
                        with col1:
                            st.markdown(f"**{resume['candidate_name'] or resume['file_name']}**")
                            st.caption(f"📄 {resume['file_name']}")
                        
                        with col2:
                            st.caption(f"Uploaded: {resume['upload_timestamp'][:10]}")
                        
                        with col3:
                            if st.button("🗑️", key=f"del_resume_{resume['id']}"):
                                try:
                                    api_client.delete_resume(resume['id'])
                                    st.success("Resume deleted")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed: {e}")
                        
                        st.markdown("---")
                        
        except Exception as e:
            st.error(f"Failed to load resumes: {e}")
            
except Exception as e:
    st.error(f"Failed to load jobs: {e}")

# Footer
st.caption("Resume Shortlisting System v1.0 - Resumes")
