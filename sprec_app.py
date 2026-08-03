import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# 1. MOCK DATABASE (Your "Rosetta Stone")
# ==========================================
# Define standard internal workflows
WORKFLOWS = {
    "Workflow A (Standard Serum)": {
        "instructions": "Allow to clot at Room Temp for 30 mins. Spin at 2000g for 15 mins at RT. Freeze at -80°C.",
        "sprec_base": ["SER", "SST", "[PRE_TIME]", "C", "A", "A", "C"],
        "max_pre_delay_hours": 2.0
    },
    "Workflow B (Standard EDTA Plasma)": {
        "instructions": "Keep at Room Temp. Spin at 2000g for 15 mins at RT. Freeze at -80°C.",
        "sprec_base": ["PL2", "PED", "[PRE_TIME]", "C", "A", "A", "C"],
        "max_pre_delay_hours": 2.0
    },
    "Workflow C (Cold PK EDTA Plasma)": {
        "instructions": "Place on ICE immediately. Spin at 2000g for 15 mins at 4°C (CHILLED). Freeze at -80°C.",
        "sprec_base": ["PL2", "PED", "[PRE_TIME]", "E", "A", "A", "C"],
        "max_pre_delay_hours": 0.5 # Cold PK needs fast processing!
    }
}

# Map Sponsor protocols to your internal workflows
STUDIES = {
    "Pfizer Protocol 101 - Visit 1 (Biomarker)": "Workflow A (Standard Serum)",
    "Pfizer Protocol 101 - Visit 1 (PK)": "Workflow C (Cold PK EDTA Plasma)",
    "Novartis Protocol XYZ - Core Lab": "Workflow B (Standard EDTA Plasma)",
    "Merck Protocol 404 - Safety Labs": "Workflow A (Standard Serum)"
}

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def calculate_pre_delay_code(draw_time, spin_time):
    """Calculates time difference and assigns SPREC Element 3 code."""
    # Combine with today's date to allow datetime math
    today = datetime.today().date()
    draw_dt = datetime.combine(today, draw_time)
    spin_dt = datetime.combine(today, spin_time)
    
    # Handle overnight (if spin time is earlier than draw time)
    if spin_dt < draw_dt:
        spin_dt = spin_dt.replace(day=today.day + 1)
        
    diff_hours = (spin_dt - draw_dt).total_seconds() / 3600
    
    # SPREC Element 3 Logic (Simplified for Demo)
    if diff_hours < 2:
        return "A", diff_hours
    elif 2 <= diff_hours < 4:
        return "B", diff_hours
    else:
        return "C", diff_hours

# Initialize session state to hold our processed samples log
if 'sample_log' not in st.session_state:
    st.session_state.sample_log = []

# ==========================================
# 3. STREAMLIT UI
# ==========================================
st.set_page_config(page_title="SPREC Lab Demo", layout="wide")

st.title("🧪 Site Preanalytical Biospecimen Tracker")
st.markdown("Translate 200 Sponsor manuals into standardized SPREC workflows.")
st.divider()

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("1. Study Intake (Rosetta Stone)")
    # Tech selects the study
    selected_study = st.selectbox("Select Study & Protocol:", options=list(STUDIES.keys()))
    
    # App determines workflow
    assigned_workflow = STUDIES[selected_study]
    workflow_data = WORKFLOWS[assigned_workflow]
    
    st.info(f"**Assigned Internal Workflow:**\n### {assigned_workflow}")
    st.write(f"**Bench Instructions:** {workflow_data['instructions']}")

with col2:
    st.subheader("2. Bench Processing Data")
    
    with st.form("processing_form"):
        sample_id = st.text_input("Sample/Subject ID (e.g., SUBJ-001)")
        
        c1, c2, c3 = st.columns(3)
        with c1: draw_time = st.time_input("Collection (Draw) Time")
        with c2: spin_time = st.time_input("Centrifuge Start Time")
        with c3: freeze_time = st.time_input("Freezer Time")
        
        submitted = st.form_submit_button("Generate SPREC & Log Sample")
        
        if submitted and sample_id:
            # 1. Calculate Delays
            pre_code, diff_hours = calculate_pre_delay_code(draw_time, spin_time)
            
            # 2. Build SPREC Code
            sprec_list = workflow_data["sprec_base"].copy()
            sprec_list[2] = pre_code # Insert calculated pre-delay code
            final_sprec = "-".join(sprec_list)
            
            # 3. Check for Deviations
            is_deviation = diff_hours > workflow_data["max_pre_delay_hours"]
            status = "Deviation" if is_deviation else "Compliant"
            
            # 4. Save to Log
            st.session_state.sample_log.append({
                "Sample ID": sample_id,
                "Study": selected_study,
                "Workflow": assigned_workflow,
                "Draw Time": draw_time.strftime("%H:%M"),
                "Spin Time": spin_time.strftime("%H:%M"),
                "Pre-Delay (Hrs)": round(diff_hours, 2),
                "SPREC Code": final_sprec,
                "Status": status
            })
            
            if is_deviation:
                st.error(f"⚠️ Protocol Deviation! Pre-centrifugation delay was {round(diff_hours,2)} hours. Max allowed for this workflow is {workflow_data['max_pre_delay_hours']} hours.")
            else:
                st.success(f"✅ Sample logged successfully! SPREC Code: **{final_sprec}**")

# ==========================================
# 4. AUDIT TRAIL / DATAFRAME
# ==========================================
st.divider()
st.subheader("📋 Daily Sample Audit Trail (Export for Sponsors)")

if st.session_state.sample_log:
    df = pd.DataFrame(st.session_state.sample_log)
    
    # Highlight deviations in red
    def color_status(val):
        color = 'red' if val == 'Deviation' else 'green'
        return f'color: {color}'
    
    st.dataframe(df.style.map(color_status, subset=['Status']), use_container_width=True)
    
    # Download Button
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Daily Log as CSV",
        data=csv,
        file_name='daily_sprec_log.csv',
        mime='text/csv',
    )
else:
    st.write("No samples processed yet today.")
