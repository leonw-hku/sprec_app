import streamlit as st
import pandas as pd
from datetime import datetime, date
import time

st.set_page_config(page_title="Site LIMS & SPREC Tracker", layout="wide", page_icon="🧬")

# ==========================================
# 1. INITIALIZE SESSION STATE (Database)
# ==========================================
# Pre-defined SPREC internal workflows
if 'workflows' not in st.session_state:
    st.session_state.workflows = {
        "Workflow A (Standard Serum)": {"sprec": ["SER", "SST", "[PRE]", "C", "A", "A", "[STO]"], "instructions": "30m Room Temp clot. Spin 2000g x 15m. Freeze -80°C."},
        "Workflow B (Standard EDTA Plasma)": {"sprec": ["PL2", "PED", "[PRE]", "C", "A", "A", "[STO]"], "instructions": "Keep at Room Temp. Spin 2000g x 15m. Freeze -80°C."},
        "Workflow C (Cold PK Plasma)": {"sprec": ["PL2", "PED", "[PRE]", "E", "A", "A", "[STO]"], "instructions": "Place on ICE. Spin CHILLED 2000g x 15m. Freeze -80°C."}
    }

# Mapping of Sponsor Studies to Workflows
if 'studies' not in st.session_state:
    st.session_state.studies = {
        "Pfizer PK - Visit 1": "Workflow C (Cold PK Plasma)",
        "Novartis Core - Visit 2": "Workflow B (Standard EDTA Plasma)"
    }

# Main Sample Database
if 'samples' not in st.session_state:
    st.session_state.samples = pd.DataFrame(columns=[
        "Sample_ID", "Subject_ID", "Study", "Status", 
        "Draw_Time", "Spin_Time", "Freeze_Time", 
        "SPREC_Code", "Location", "Tracking_Number"
    ])

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def calculate_pre_delay(draw_t, spin_t):
    """Calculates time between draw and spin, returns SPREC code."""
    today = date.today()
    dt_draw = datetime.combine(today, draw_t)
    dt_spin = datetime.combine(today, spin_t)
    if dt_spin < dt_draw: dt_spin = dt_spin.replace(day=today.day + 1)
    
    diff_hrs = (dt_spin - dt_draw).total_seconds() / 3600
    if diff_hrs < 2: return "A"
    elif 2 <= diff_hrs < 4: return "B"
    else: return "C"

def get_storage_code(temp):
    """Returns SPREC storage code."""
    if temp == "-80°C": return "C"
    elif temp == "-20°C": return "Q"
    elif temp == "LN2": return "A"
    else: return "Z"

# ==========================================
# 3. UI LAYOUT & TABS
# ==========================================
st.title("🧬 Clinical Site LIMS: SPREC & Sample Lifecycle")
st.markdown("Track samples through: **Setup ➡️ Registration ➡️ Processing ➡️ Storage ➡️ Shipment**")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "⚙️ 1. Setup", "📝 2. Registration", "🧪 3. Processing", 
    "❄️ 4. Storage", "📦 5. Shipment", "📊 Master Log"
])

# --- TAB 1: SETUP ---
with tab1:
    st.subheader("Map Sponsor Protocols to Internal Workflows")
    col1, col2 = st.columns(2)
    with col1:
        with st.form("add_study_form"):
            new_study = st.text_input("New Study / Protocol Name:")
            assigned_wf = st.selectbox("Assign to Internal Workflow:", options=st.session_state.workflows.keys())
            if st.form_submit_button("Add Study Mapping"):
                if new_study:
                    st.session_state.studies[new_study] = assigned_wf
                    st.success(f"Added {new_study}!")
    with col2:
        st.write("**Current Active Studies (Rosetta Stone):**")
        st.json(st.session_state.studies)

# --- TAB 2: REGISTRATION (Intake) ---
with tab2:
    st.subheader("Log a new sample at the collection chair")
    with st.form("registration_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            samp_id = st.text_input("Scan/Type Sample Barcode ID:")
            subj_id = st.text_input("Subject ID:")
        with col2:
            study_sel = st.selectbox("Select Study:", options=st.session_state.studies.keys())
            draw_time = st.time_input("Collection (Draw) Time:")
        
        if st.form_submit_button("Register Sample"):
            if samp_id and subj_id:
                if samp_id in st.session_state.samples["Sample_ID"].values:
                    st.error("Sample ID already exists!")
                else:
                    wf = st.session_state.studies[study_sel]
                    base_sprec = "-".join(st.session_state.workflows[wf]["sprec"])
                    
                    new_row = pd.DataFrame([{
                        "Sample_ID": samp_id, "Subject_ID": subj_id, "Study": study_sel,
                        "Status": "Registered", "Draw_Time": draw_time, "Spin_Time": None,
                        "Freeze_Time": None, "SPREC_Code": base_sprec, "Location": "", "Tracking_Number": ""
                    }])
                    st.session_state.samples = pd.concat([st.session_state.samples, new_row], ignore_index=True)
                    st.success(f"Sample {samp_id} Registered! Ready for processing.")

# --- TAB 3: PROCESSING (Bench) ---
with tab3:
    st.subheader("Process Samples (Centrifugation)")
    # Filter for samples that need processing
    pending_proc = st.session_state.samples[st.session_state.samples["Status"] == "Registered"]
    
    if pending_proc.empty:
        st.info("No samples currently waiting for processing.")
    else:
        proc_samp = st.selectbox("Select Sample to Process:", options=pending_proc["Sample_ID"])
        idx = st.session_state.samples.index[st.session_state.samples["Sample_ID"] == proc_samp][0]
        
        # Display instructions for the tech
        study = st.session_state.samples.at[idx, "Study"]
        wf = st.session_state.studies[study]
        st.info(f"**Instructions for {proc_samp}:** {st.session_state.workflows[wf]['instructions']}")
        
        with st.form("processing_form"):
            spin_t = st.time_input("Centrifuge Start Time:")
            if st.form_submit_button("Complete Processing"):
                draw_t = st.session_state.samples.at[idx, "Draw_Time"]
                pre_code = calculate_pre_delay(draw_t, spin_t)
                
                # Update SPREC and Status
                current_sprec = st.session_state.samples.at[idx, "SPREC_Code"]
                updated_sprec = current_sprec.replace("[PRE]", pre_code)
                
                st.session_state.samples.at[idx, "Spin_Time"] = spin_t
                st.session_state.samples.at[idx, "SPREC_Code"] = updated_sprec
                st.session_state.samples.at[idx, "Status"] = "Processed"
                st.success("Processing complete! SPREC code updated.")
                time.sleep(1)
                st.rerun() # Refresh to move sample out of queue

# --- TAB 4: STORAGE (Freezer) ---
with tab4:
    st.subheader("Store Samples in Freezer")
    pending_store = st.session_state.samples[st.session_state.samples["Status"] == "Processed"]
    
    if pending_store.empty:
        st.info("No samples currently waiting for storage.")
    else:
        store_samp = st.selectbox("Select Sample to Store:", options=pending_store["Sample_ID"])
        idx = st.session_state.samples.index[st.session_state.samples["Sample_ID"] == store_samp][0]
        
        with st.form("storage_form"):
            col1, col2 = st.columns(2)
            with col1:
                freeze_t = st.time_input("Time placed in Freezer:")
                temp = st.selectbox("Freezer Temperature:", ["-80°C", "-20°C", "LN2"])
            with col2:
                box_loc = st.text_input("Freezer/Box Location (e.g., FZ1-BoxA-A1):")
            
            if st.form_submit_button("Store Sample"):
                if box_loc:
                    sto_code = get_storage_code(temp)
                    current_sprec = st.session_state.samples.at[idx, "SPREC_Code"]
                    final_sprec = current_sprec.replace("[STO]", sto_code)
                    
                    st.session_state.samples.at[idx, "Freeze_Time"] = freeze_t
                    st.session_state.samples.at[idx, "SPREC_Code"] = final_sprec
                    st.session_state.samples.at[idx, "Location"] = box_loc
                    st.session_state.samples.at[idx, "Status"] = "Stored"
                    st.success("Sample Stored!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Please enter a box location.")

# --- TAB 5: SHIPMENT (Dispatch) ---
with tab5:
    st.subheader("Ship Samples to Central Lab")
    pending_ship = st.session_state.samples[st.session_state.samples["Status"] == "Stored"]
    
    if pending_ship.empty:
        st.info("No stored samples available to ship.")
    else:
        with st.form("shipment_form"):
            st.write("Select samples to add to manifest:")
            selected_to_ship = st.multiselect("Samples:", options=pending_ship["Sample_ID"].tolist())
            tracking = st.text_input("FedEx/WorldCourier Tracking Number:")
            
            if st.form_submit_button("Generate Manifest & Ship"):
                if selected_to_ship and tracking:
                    for s_id in selected_to_ship:
                        idx = st.session_state.samples.index[st.session_state.samples["Sample_ID"] == s_id][0]
                        st.session_state.samples.at[idx, "Status"] = "Shipped"
                        st.session_state.samples.at[idx, "Tracking_Number"] = tracking
                        st.session_state.samples.at[idx, "Location"] = "Shipped"
                    st.success("Samples marked as shipped!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Select samples and provide a tracking number.")

# --- TAB 6: MASTER LOG ---
with tab6:
    st.subheader("📋 Master Sample Audit Trail")
    if st.session_state.samples.empty:
        st.write("Database is empty.")
    else:
        # Display the dataframe with color-coded statuses
        def color_status(val):
            colors = {"Registered": "orange", "Processed": "blue", "Stored": "purple", "Shipped": "green"}
            return f'color: {colors.get(val, "black")}; font-weight: bold;'
        
        st.dataframe(
            st.session_state.samples.style.map(color_status, subset=['Status']), 
            use_container_width=True, hide_index=True
        )
        
        # Download CSV
        csv = st.session_state.samples.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Download Master Manifest (CSV)", data=csv, file_name='master_sample_log.csv', mime='text/csv')
