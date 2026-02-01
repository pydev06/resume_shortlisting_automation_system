import streamlit as st

import sys

sys.path.insert(0, "frontend")

from api_client import api_client
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Resume Shortlisting - Evaluations",
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
    st.session_state.current_page = "evaluations"
if "selected_job" not in st.session_state:
    st.session_state.selected_job = None
if "export_csv" not in st.session_state:
    st.session_state.export_csv = False
if "csv_data" not in st.session_state:
    st.session_state.csv_data = None

st.markdown('<p class="main-header">📊 Resume Evaluations</p>', unsafe_allow_html=True)

try:
    jobs_data = api_client.list_jobs(page_size=100)
    jobs = jobs_data.get("jobs", [])
    
    if not jobs:
        st.warning("No jobs found. Please create a job first.")
    else:
        job_options = {f"{j['job_id']} - {j['title']}": j for j in jobs}
        
        selected_job_key = st.selectbox(
            "Select Job",
            options=list(job_options.keys())
        )
        selected_job = job_options[selected_job_key]
        
        st.markdown("---")
        
        # Summary metrics
        try:
            summary = api_client.get_evaluation_summary(selected_job['job_id'])
            
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Resumes", summary['total_resumes'])
            with col2:
                st.metric("Evaluated", summary['evaluated'])
            with col3:
                st.metric("OK to Proceed", summary['ok_to_proceed'])
            with col4:
                st.metric("Not OK", summary['not_ok'])
            with col5:
                st.metric("Avg Score", f"{summary['average_score']:.1f}%")
            
        except Exception as e:
            st.warning(f"Could not load summary: {e}")
        
        st.markdown("---")
        
        # Evaluate button
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🔄 Evaluate All Resumes", type="primary", use_container_width=True):
                with st.spinner("Evaluating resumes... This may take a while."):
                    try:
                        results = api_client.evaluate_all_resumes(selected_job['job_id'])
                        st.success(f"✅ Evaluated {len(results)} resumes")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Evaluation failed: {e}")
        
        # Export to CSV
        with col2:
            if st.button("📊 Export to CSV", use_container_width=True):
                try:
                    csv_data = api_client.export_evaluations_csv(selected_job['job_id'], {
                        'status': status_param,
                        'min_score': min_score if min_score > 0 else None,
                        'max_score': max_score if max_score < 100 else None,
                        'min_experience': min_experience if min_experience > 0 else None,
                        'max_experience': max_experience if max_experience < 50 else None,
                        'skills_keyword': skills_keyword,
                        'education_keyword': education_keyword,
                        'sort_by': sort_by,
                        'sort_order': sort_dir
                    })
                    st.session_state.export_csv = True
                    st.session_state.csv_data = csv_data
                    st.success("CSV generated! Download below.")
                except Exception as e:
                    st.error(f"Export failed: {e}")
            
            if st.session_state.export_csv and st.session_state.csv_data:
                st.download_button(
                    label="📥 Download CSV",
                    data=st.session_state.csv_data,
                    file_name=f"evaluations_{selected_job['job_id']}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv"
                )
        
        # Filters
        st.markdown("### Filters")
        with st.expander("Filter Options", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                status_filter = st.selectbox(
                    "Status",
                    ["All", "OK to Proceed", "Not OK", "Pending"]
                )
            with col2:
                min_score = st.number_input("Min Score", 0, 100, 0)
            with col3:
                max_score = st.number_input("Max Score", 0, 100, 100)
            with col4:
                sort_order = st.selectbox("Sort", ["Highest Score", "Lowest Score", "Recent", "Experience (High to Low)", "Experience (Low to High)"])
            
            col5, col6, col7, col8 = st.columns(4)
            with col5:
                min_experience = st.number_input("Min Experience (years)", 0.0, 50.0, 0.0, 0.5)
            with col6:
                max_experience = st.number_input("Max Experience (years)", 0.0, 50.0, 50.0, 0.5)
            with col7:
                skills_keyword = st.text_input("Skills Keyword", placeholder="e.g., Python")
            with col8:
                education_keyword = st.text_input("Education Keyword", placeholder="e.g., Computer Science")
        
        # Map sort options
        sort_by = "match_score"
        sort_dir = "desc"
        if sort_order == "Lowest Score":
            sort_dir = "asc"
        elif sort_order == "Recent":
            sort_by = "evaluated_at"
        elif sort_order == "Experience (High to Low)":
            sort_by = "experience_years"
            sort_dir = "desc"
        elif sort_order == "Experience (Low to High)":
            sort_by = "experience_years"
            sort_dir = "asc"
        
        # List evaluations
        try:
            status_param = None if status_filter == "All" else status_filter
            evals_data = api_client.list_evaluations(
                selected_job['job_id'],
                status=status_param,
                min_score=min_score if min_score > 0 else None,
                max_score=max_score if max_score < 100 else None,
                sort_by=sort_by,
                sort_order=sort_dir
            )
            evaluations = evals_data.get("evaluations", [])
            
            st.markdown(f"### Results ({len(evaluations)} candidates)")
            
            if not evaluations:
                st.info("No evaluations found. Click 'Evaluate All Resumes' to start.")
            else:
                for eval_item in evaluations:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
                        
                        with col1:
                            st.markdown(f"**{eval_item.get('candidate_name') or eval_item['file_name']}**")
                            st.caption(f"📄 {eval_item['file_name']}")
                        
                        with col2:
                            score = eval_item['match_score']
                            score_class = get_score_class(score)
                            st.markdown(f'<span class="{score_class}">{score:.0f}%</span>', unsafe_allow_html=True)
                        
                        with col3:
                            st.markdown(format_status_badge(eval_item['status']), unsafe_allow_html=True)
                        
                        with col4:
                            if st.button("View Details", key=f"view_{eval_item['id']}"):
                                st.session_state.viewing_eval = eval_item
                        
                        # Show justification
                        st.caption(eval_item['justification'])
                        st.markdown("---")
                
                # Detailed view modal
                if "viewing_eval" in st.session_state and st.session_state.viewing_eval:
                    eval_item = st.session_state.viewing_eval
                    st.markdown("---")
                    st.markdown(f"## 📋 Detailed Evaluation: {eval_item.get('candidate_name', eval_item['file_name'])}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("### Match Score")
                        st.markdown(f"# {eval_item['match_score']:.0f}%")
                        st.markdown(format_status_badge(eval_item['status']), unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("### Experience")
                        exp = eval_item.get('experience_years')
                        st.markdown(f"**{exp if exp else 'Not specified'}** years")
                        
                        st.markdown("### Education")
                        st.markdown(eval_item.get('education') or "Not specified")
                    
                    st.markdown("### Justification")
                    st.info(eval_item['justification'])
                    
                    st.markdown("### Skills Extracted")
                    skills = eval_item.get('skills_extracted', [])
                    if skills:
                        st.write(", ".join(skills))
                    else:
                        st.write("No skills extracted")
                    
                    st.markdown("### Previous Roles")
                    roles = eval_item.get('previous_roles', [])
                    if roles:
                        for role in roles:
                            st.write(f"• {role}")
                    else:
                        st.write("No roles found")
                    
                    if st.button("Close Details"):
                        st.session_state.viewing_eval = None
                        st.rerun()
                        
        except Exception as e:
            st.error(f"Failed to load evaluations: {e}")
            
except Exception as e:
    st.error(f"Failed to load jobs: {e}")

# Footer
st.caption("Resume Shortlisting System v1.0 - Evaluations")
