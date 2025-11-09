import os
import requests
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
import io

load_dotenv()
API_BASE = os.environ.get('API_BASE_URL', 'http://localhost:8000')

st.set_page_config(page_title="SHL Assessment Recommender", layout="wide")

with st.sidebar:
    st.header("Settings")
    api_base = st.text_input("API Base URL", value=API_BASE)
    col_h1, col_h2 = st.columns([1, 1])
    with col_h1:
        if st.button("Check API Health", use_container_width=True):
            try:
                r = requests.get(f"{api_base}/health", timeout=10)
                if r.ok and r.json().get('status') == 'healthy':
                    st.success("Healthy")
                else:
                    st.warning("Unhealthy response")
            except Exception as e:
                st.error(f"Health error: {e}")
    with col_h2:
        st.write("")

st.title("SHL Assessment Recommender")
st.caption("Recommend SHL assessments from a job description or natural language query. Returns 5–10 assessments, balanced across types when applicable.")

col_top1, col_top2 = st.columns([3,1])
with col_top1:
    query = st.text_area("Enter job description or query:", height=220, placeholder="e.g., Java developer who collaborates well; problem solving; teamwork")
with col_top2:
    k = st.number_input("Recommendations (5–10)", min_value=5, max_value=10, value=10, step=1)

if st.button("Get Recommendations", type="primary"):
    if not query.strip():
        st.warning("Please enter a query.")
    else:
        with st.spinner("Fetching recommendations..."):
            try:
                resp = requests.post(f"{api_base}/recommend", json={"query": query}, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                recs = data.get('recommended_assessments', [])
                if not recs:
                    st.info("No recommendations yet. Try crawling the catalog first.")
                else:
                    st.subheader("Recommendations")
                    rows = []
                    for r in recs[:k]:
                        rows.append({
                            'URL': r.get('url'),
                            'Adaptive Support': r.get('adaptive_support'),
                            'Description': r.get('description'),
                            'Duration (min)': r.get('duration'),
                            'Remote Support': r.get('remote_support'),
                            'Test Type': ", ".join(r.get('test_type') or []),
                        })
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    # Per-query CSV download in required evaluation format
                    eval_rows = [{"Query": " ".join(query.split()).strip(), "Assessment_url": r.get('url')} for r in recs[:k]]
                    eval_df = pd.DataFrame(eval_rows, columns=["Query", "Assessment_url"])
                    csv_buf = io.StringIO()
                    eval_df.to_csv(csv_buf, index=False)
                    st.download_button(
                        label="Download CSV for this query",
                        data=csv_buf.getvalue(),
                        file_name="predictions_single_query.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
            except Exception as e:
                st.error(f"Error: {e}")
