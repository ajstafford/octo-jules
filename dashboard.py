import streamlit as st
import pandas as pd
import db
from datetime import datetime
import time

st.set_page_config(page_title="Octo-Jules Dashboard", layout="wide")

st.title("Octo-Jules Automation Dashboard")
st.write("Monitoring the Jules autonomous development loop.")

def get_data():
    conn = db.get_connection()
    try:
        query = "SELECT * FROM sessions ORDER BY created_at DESC"
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()
    return df

# Sidebar for controls
st.sidebar.header("Controls")
if st.sidebar.button("Refresh Data"):
    st.rerun()

auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)

# Main Dashboard
data = get_data()

if data.empty:
    st.info("No sessions recorded in the database yet. Start the orchestrator to see data!")
else:
    # Summary Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sessions", len(data))
    col2.metric("Merged PRs", len(data[data['state'] == 'MERGED']))
    col3.metric("In Progress", len(data[data['state'] == 'IN_PROGRESS']))
    col4.metric("Failed", len(data[data['state'] == 'FAILED']))

    # Status breakdown chart
    st.subheader("Status Overview")
    status_counts = data['state'].value_counts()
    st.bar_chart(status_counts)

    # Detailed Table
    st.subheader("Recent Sessions")
    
    # Format the dataframe for display
    display_df = data.copy()
    
    # Make PR URL clickable if it exists
    def make_clickable(url):
        if url:
            return f'<a href="{url}" target="_blank">View PR</a>'
        return ""

    # Note: Streamlit's st.dataframe doesn't render HTML by default for security, 
    # but we can use st.column_config.LinkColumn in newer versions or just show the table.
    
    st.dataframe(
        display_df,
        column_config={
            "id": "Session ID",
            "issue_number": "Issue #",
            "issue_title": "Title",
            "repo": "Repository",
            "state": "Status",
            "pr_number": "PR #",
            "pr_url": st.column_config.LinkColumn("PR Link"),
            "created_at": "Started",
            "updated_at": "Last Update"
        },
        hide_index=True,
        use_container_width=True
    )

# Auto-refresh logic
if auto_refresh:
    time.sleep(30)
    st.rerun()
