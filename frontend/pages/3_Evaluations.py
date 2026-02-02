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

try:
    jobs_data = api_client.list_jobs(page_size=100)
    jobs = jobs_data.get("jobs", [])

    job_options = {f"{j['job_id']} - {j['title']}": j for j in jobs}
    selected_job_key = st.selectbox("Select Job", options=list(job_options.keys()))
    selected_job = job_options[selected_job_key]

    st.markdown("---")

    evals_data = api_client.list_evaluations(selected_job['job_id'])
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
