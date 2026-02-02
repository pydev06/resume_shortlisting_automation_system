import streamlit as st
import sys

sys.path.insert(0, "frontend")

from api_client import api_client

# Page configuration
st.set_page_config(
    page_title="Resume Shortlisting - Evaluations",
    page_icon="📄",
    layout="wide"
)

# -----------------------
# Tooltip help texts
# -----------------------
MATCH_SCORE_HELP = """
**Match Score**
An AI-generated percentage indicating how well the resume matches the job description.

Calculated using:
• Skill relevance  
• Experience alignment  
• Education match  
• Keyword overlap  

👉 Best for **quick shortlisting decisions**.
"""

COMPOSITE_SCORE_HELP = """
**Composite Score**
A weighted score used for ranking and tie-breaking.

Includes:
• Experience score  
• Education score  
• Skills quality  
• Keyword density  

👉 Best for **final ranking**.
"""

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
    .score-high { color: #28a745; font-weight: bold; }
    .score-medium { color: #ffc107; font-weight: bold; }
    .score-low { color: #dc3545; font-weight: bold; }
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


st.markdown('<p class="main-header">📊 Resume Evaluations</p>', unsafe_allow_html=True)

# Clear invalid viewing_eval from session state
if ("viewing_eval" in st.session_state and 
    (st.session_state.viewing_eval is None or 
     not isinstance(st.session_state.viewing_eval, dict) or 
     'match_score' not in st.session_state.viewing_eval)):
    del st.session_state.viewing_eval

try:
    jobs_data = api_client.list_jobs(page_size=100)
    jobs = jobs_data.get("jobs", [])

    job_options = {f"{j['job_id']} - {j['title']}": j for j in jobs}
    selected_job_key = st.selectbox("Select Job", options=list(job_options.keys()))
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
            sort_order = st.selectbox("Sort", ["Highest Score", "Lowest Score", "Recent", "Experience (High to Low)", "Experience (Low to High)", "Composite Score (High to Low)", "Composite Score (Low to High)"])
        
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
    elif sort_order == "Composite Score (High to Low)":
        sort_by = "composite_score"
        sort_dir = "desc"
    elif sort_order == "Composite Score (Low to High)":
        sort_by = "composite_score"
        sort_dir = "asc"
    
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
                status_param = None if status_filter == "All" else status_filter
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
            
        if st.session_state.get('export_csv') and st.session_state.get('csv_data'):
            st.download_button(
                label="📥 Download CSV",
                data=st.session_state.csv_data,
                file_name=f"evaluations_{selected_job['job_id']}.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_csv"
            )
    
    st.markdown("---")
    
    # List evaluations with filters
    status_param = None if status_filter == "All" else status_filter
    evals_data = api_client.list_evaluations(
        selected_job['job_id'],
        status=status_param,
        min_score=min_score if min_score > 0 else None,
        max_score=max_score if max_score < 100 else None,
        sort_by=sort_by,
        sort_order=sort_dir
    )
    evaluations = evals_data.get("evaluations", []) if evals_data else []
    evaluations = [e for e in evaluations if e is not None]  # Filter out None items

    st.markdown(f"### Results ({len(evaluations)} candidates)")

    if not evaluations:
        st.info("No evaluations found. Click 'Evaluate All Resumes' to start.")
    else:
        for eval_item in evaluations:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 2])

                with col1:
                    st.markdown(f"**{eval_item.get('candidate_name', eval_item['file_name'])}**")
                    st.caption(f"📄 {eval_item['file_name']}")

                with col2:
                    st.markdown("**Match Score**", help=MATCH_SCORE_HELP)
                    score = eval_item['match_score']
                    score_class = get_score_class(score)
                    st.markdown(
                        f'<span class="{score_class}">{score:.0f}%</span>',
                        unsafe_allow_html=True
                    )

            with col3:
                st.markdown(format_status_badge(eval_item['status']), unsafe_allow_html=True)

            with col4:
                col4a, col4b = st.columns([1.5, 1])
                with col4a:
                    if eval_item.get('ranking_breakdown'):
                        composite = eval_item['ranking_breakdown'].get('composite_score')
                        st.markdown("**Composite Score**", help=COMPOSITE_SCORE_HELP)
                        st.caption(f"🏆 {composite:.1f}%")
                    else:
                        st.caption("📊 No ranking data")
                
                with col4b:
                    if st.button("View Details", key=f"view_{eval_item['id']}"):
                        st.session_state.viewing_eval = eval_item
                        st.rerun()

            st.caption(eval_item['justification'])
            st.markdown("---")

    # -----------------------
    # Detailed view
    # -----------------------
    if ("viewing_eval" in st.session_state and 
        st.session_state.viewing_eval is not None and 
        isinstance(st.session_state.viewing_eval, dict) and 
        'match_score' in st.session_state.viewing_eval):
        
        eval_item = st.session_state.viewing_eval

        st.markdown(f"## 📋 Detailed Evaluation")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🎯 Match Score", help=MATCH_SCORE_HELP)
            st.markdown(f"# {eval_item['match_score']:.0f}%")
            st.markdown(format_status_badge(eval_item['status']), unsafe_allow_html=True)

            if eval_item.get('ranking_breakdown'):
                rb = eval_item['ranking_breakdown']
                st.markdown("### 🏆 Composite Score", help=COMPOSITE_SCORE_HELP)
                st.markdown(f"**{rb.get('composite_score', 0):.1f}%**")

                st.markdown("### Ranking Breakdown")
                st.write(f"💼 Experience: {rb.get('experience_score', 0):.1f}%")
                st.write(f"🎓 Education: {rb.get('education_score', 0):.1f}%")
                st.write(f"⚡ Skills Quality: {rb.get('skills_quality_score', 0):.1f}%")
                st.write(f"🔍 Keyword Density: {rb.get('keyword_density_score', 0):.1f}%")

        with col2:
            st.markdown("### Experience")
            st.write(eval_item.get('experience_years', "Not specified"))

            st.markdown("### Education")
            st.write(eval_item.get('education', "Not specified"))

        if st.button("Close Details"):
            st.session_state.viewing_eval = None
            st.rerun()

except Exception as e:
    st.error(f"Error loading evaluations: {e}")

st.caption("Resume Shortlisting System v1.0 - Evaluations")
