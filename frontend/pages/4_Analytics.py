import sys
from datetime import datetime
import matplotlib.pyplot as plt

sys.path.insert(0, "frontend")

from api_client import api_client
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Resume Shortlisting - Analytics",
    page_icon="📊",
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
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
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
    st.session_state.current_page = "analytics"

st.markdown('<p class="main-header">📈 Hiring Analytics Dashboard</p>', unsafe_allow_html=True)

try:
    jobs_data = api_client.list_jobs(page_size=100)
    jobs = jobs_data.get("jobs", [])
    
    if not jobs:
        st.warning("No jobs found. Please create a job first.")
    else:
        job_options = {f"{j['job_id']} - {j['title']}": j for j in jobs}
        
        selected_job_key = st.selectbox(
            "Select Job for Analytics",
            options=list(job_options.keys())
        )
        selected_job = job_options[selected_job_key]
        
        st.markdown("---")
        
        # Fetch evaluations
        try:
            evals_data = api_client.list_evaluations(selected_job['job_id'])
            evaluations = evals_data.get("evaluations", [])
            
            if not evaluations:
                st.info("No evaluations found for this job. Run evaluations first.")
            else:
                # Summary metrics
                total_evals = len(evaluations)
                avg_score = sum(e['match_score'] for e in evaluations) / total_evals
                ok_count = sum(1 for e in evaluations if e['status'] == 'OK to Proceed')
                not_ok_count = sum(1 for e in evaluations if e['status'] == 'Not OK')
                pending_count = sum(1 for e in evaluations if e['status'] == 'Pending')
                
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Total Candidates", total_evals)
                with col2:
                    st.metric("Average Score", f"{avg_score:.1f}%")
                with col3:
                    st.metric("Approved", ok_count)
                with col4:
                    st.metric("Rejected", not_ok_count)
                with col5:
                    st.metric("Pending", pending_count)
                
                st.markdown("---")
                
                # Charts
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### Status Distribution")
                    status_counts = {
                        'OK to Proceed': ok_count,
                        'Not OK': not_ok_count,
                        'Pending': pending_count
                    }
                    fig, ax = plt.subplots(figsize=(6, 6))
                    explode = [0.05] * len(status_counts)  # Separate slices slightly
                    ax.pie(status_counts.values(), autopct='%1.1f%%', explode=explode, startangle=90)
                    ax.axis('equal')  # Equal aspect ratio ensures pie is drawn as a circle
                    ax.legend(status_counts.keys(), loc="center left", bbox_to_anchor=(1, 0.5))
                    plt.tight_layout()
                    st.pyplot(fig)
                
                with col2:
                    st.markdown("### Match Score Distribution")
                    scores = [e['match_score'] for e in evaluations]
                    fig, ax = plt.subplots()
                    ax.hist(scores, bins=10, edgecolor='black')
                    ax.set_xlabel('Match Score (%)')
                    ax.set_ylabel('Number of Candidates')
                    ax.set_title('Score Distribution')
                    st.pyplot(fig)
                
                # Time series if dates are available
                st.markdown("### Evaluation Trends Over Time")
                try:
                    dates = [datetime.fromisoformat(e['evaluated_at'].replace('Z', '+00:00')) for e in evaluations if e.get('evaluated_at')]
                    if dates:
                        date_counts = {}
                        for date in dates:
                            date_str = date.strftime('%Y-%m-%d')
                            date_counts[date_str] = date_counts.get(date_str, 0) + 1
                        
                        sorted_dates = sorted(date_counts.items())
                        x_dates, y_counts = zip(*sorted_dates)
                        
                        fig, ax = plt.subplots()
                        ax.plot(x_dates, y_counts, marker='o')
                        ax.set_xlabel('Date')
                        ax.set_ylabel('Evaluations Completed')
                        ax.set_title('Daily Evaluation Activity')
                        plt.xticks(rotation=45)
                        st.pyplot(fig)
                    else:
                        st.info("No evaluation timestamps available for trend analysis.")
                except Exception as e:
                    st.warning(f"Could not generate time series: {e}")
        
        except Exception as e:
            st.error(f"Failed to load analytics: {e}")
            
except Exception as e:
    st.error(f"Failed to load jobs: {e}")

# Footer
st.caption("Resume Shortlisting System v1.0 - Analytics")
