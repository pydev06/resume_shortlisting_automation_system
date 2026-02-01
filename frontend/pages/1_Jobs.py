import sys

sys.path.insert(0, "frontend")

import streamlit as st
from api_client import api_client

# -------------------------------------------------
# Page configuration
# -------------------------------------------------
st.set_page_config(
    page_title="Resume Shortlisting - Jobs",
    page_icon="📄",
    layout="wide"
)

# -------------------------------------------------
# Custom CSS
# -------------------------------------------------
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    @media (max-width: 768px) {
        .main-header { font-size: 1.5rem; }
        .stButton button { width: 100% !important; }
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Session State Defaults
# -------------------------------------------------
defaults = {
    "current_page": "jobs",
    "selected_job": None,
    "form_key": 0,
    "editing_job_id": None,
    "confirm_delete_job_id": None,
    "success_msg": None,
}

for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# -------------------------------------------------
# Toast
# -------------------------------------------------
if st.session_state.success_msg:
    st.toast(st.session_state.success_msg, icon="✅")
    st.session_state.success_msg = None

# -------------------------------------------------
# Header
# -------------------------------------------------
st.markdown('<p class="main-header">📋 Job Management</p>', unsafe_allow_html=True)

# -------------------------------------------------
# Create Job
# -------------------------------------------------
with st.expander("➕ Create New Job"):
    with st.form(key=f"create_job_form_{st.session_state.form_key}"):
        job_title = st.text_input("Job Title", placeholder="e.g., Senior Python Developer")
        job_description = st.text_area(
            "Job Description",
            height=200,
            placeholder="Enter the full job description"
        )

        submitted = st.form_submit_button("Create Job", use_container_width=True)

        if submitted:
            if not job_title or not job_description:
                st.error("Please fill in both title and description")
            else:
                try:
                    result = api_client.create_job(job_title, job_description)
                    st.session_state.success_msg = (
                        f"Job created successfully! JOBID: {result['job_id']}"
                    )
                    st.session_state.form_key += 1
                    st.session_state.editing_job_id = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to create job: {e}")

st.markdown("---")

# -------------------------------------------------
# Search & Page Size
# -------------------------------------------------
c1, c2 = st.columns([3, 1])
with c1:
    search_query = st.text_input("🔍 Search jobs", placeholder="Search by title or JOBID")
with c2:
    page_size = st.selectbox("Per page", [10, 25, 50], index=0)

# -------------------------------------------------
# Job List
# -------------------------------------------------
try:
    jobs_data = api_client.list_jobs(
        query=search_query if search_query else None,
        page_size=page_size
    )
    jobs = jobs_data.get("jobs", [])

    if not jobs:
        st.info("No jobs found. Create your first job above!")
    else:
        st.markdown(f"**Showing {len(jobs)} of {jobs_data.get('total', 0)} jobs**")

        for job in jobs:
            with st.container():

                # ============ EDIT MODE ============
                if st.session_state.editing_job_id == job["job_id"]:
                    st.markdown(f"**Editing `{job['job_id']}`**")

                    title = st.text_input(
                        "Title",
                        job["title"],
                        key=f"title_{job['job_id']}"
                    )
                    desc = st.text_area(
                        "Description",
                        job["description"],
                        height=120,
                        key=f"desc_{job['job_id']}"
                    )

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Save", use_container_width=True):
                            try:
                                api_client.update_job(
                                    job["job_id"],
                                    title=title,
                                    description=desc
                                )
                                st.success("Job updated successfully!")
                                st.session_state.editing_job_id = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to update job: {e}")

                    with c2:
                        if st.button("Cancel", use_container_width=True):
                            st.session_state.editing_job_id = None
                            st.rerun()

                # ============ VIEW MODE ============
                else:
                    c1, c2, c3 = st.columns([1, 4, 2])

                    with c1:
                        st.markdown(f"**`{job['job_id']}`**")

                    with c2:
                        st.markdown(f"**{job['title']}**")
                        st.caption(f"Created: {job['created_at'][:10]}")

                    with c3:
                        b1, b2, b3 = st.columns(3)

                        with b1:
                            if st.button("📁", key=f"res_{job['job_id']}"):
                                st.session_state.selected_job = job
                                st.switch_page("pages/2_Resumes.py")

                        with b2:
                            if st.button("✏️", key=f"edit_{job['job_id']}"):
                                st.session_state.editing_job_id = job["job_id"]
                                st.session_state.confirm_delete_job_id = None
                                st.rerun()

                        with b3:
                            if st.button("🗑️", key=f"del_{job['job_id']}"):
                                st.session_state.confirm_delete_job_id = job["job_id"]

                # ============ INLINE DELETE CONFIRM ============
                if st.session_state.confirm_delete_job_id == job["job_id"]:
                    st.warning(
                        "⚠️ Are you sure you want to delete this job?\n\n"
                        "This will also delete all associated resumes and evaluations."
                    )

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(
                            "Yes, Delete",
                            type="primary",
                            key=f"confirm_{job['job_id']}",
                            use_container_width=True
                        ):
                            api_client.delete_job(job["job_id"])
                            st.success("Job deleted successfully!")
                            st.session_state.confirm_delete_job_id = None
                            st.rerun()

                    with c2:
                        if st.button(
                            "Cancel",
                            key=f"cancel_{job['job_id']}",
                            use_container_width=True
                        ):
                            st.session_state.confirm_delete_job_id = None
                            st.rerun()

                st.markdown("---")

except Exception as e:
    st.error(f"Failed to load jobs: {e}")

# -------------------------------------------------
# Footer
# -------------------------------------------------
st.caption("Resume Shortlisting System v1.0 — Jobs")
