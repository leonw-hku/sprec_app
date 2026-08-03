import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import uuid

st.set_page_config(page_title="Site LIMS & Compliance Engine", layout="wide", page_icon="🧬")

# ==========================================
# 1. INITIALIZE SESSION STATE (Database)
# ==========================================
if 'workflows' not in st.session_state:
    st.session_state.workflows = {
        "Workflow A (Standard Serum)": {"sprec": ["SER", "SST", "[PRE]", "C", "A", "A", "[STO]"], "instructions": "30m Room Temp clot. Spin 2000g x 15m. Freeze -80°C."},
        "Workflow B (Standard EDTA Plasma)": {"sprec": ["PL2", "PED", "[PRE]", "C", "A", "A", "[STO]"], "instructions": "Keep at Room Temp. Spin 2000g x 15m. Freeze -80°C."},
        "Workflow C (Cold PK Plasma)": {"sprec": ["PL2", "PED", "[PRE]", "E", "A", "A", "[STO]"], "instructions": "Place on ICE. Spin CHILLED 2000g x 15m. Freeze -80°C."}
    }

if 'studies' not in st.session_state:
    st.session_state.studies = {
        "Pfizer Protocol 101": {"Biomarker Serum": "Workflow A (Standard Serum)", "PK Plasma": "Workflow C (Cold PK Plasma)"},
        "Novartis Core": {"Safety Plasma": "Workflow B (Standard EDTA Plasma)"}
    }

# NEW: Staff Database and Training Matrix
if 'staff' not in st.session_state:
    st.session_state.staff = ["Manager (You)", "Tech John (Senior)", "Tech Sarah (New Hire)"]
    st.session_state.training_matrix = {
        "Manager (You)": ["Workflow A (Standard Serum)", "Workflow B (Standard EDTA Plasma)", "Workflow C (Cold PK Plasma)"],
        "Tech John (Senior)": ["Workflow A (Standard Serum)", "Workflow B (Standard EDTA Plasma)", "Workflow C (Cold PK Plasma)"],
        "Tech Sarah (New Hire)": ["Workflow A (Standard Serum)"] # Sarah only knows Workflow A so far
    }

if 'samples' not in st.session_state:
    st.session_state.samples = pd.DataFrame(columns=[
        "Internal_ID", "Sample_Barcode", "Subject_ID", "Study", "Sample_Type",
        "Status", "Draw_Time", "Spin_Time", "Freeze_Time", 
        "SPREC_Code", "Location", "Action_By"
    ])

# ==========================================
# 2. SIMULATED LOGIN (Sidebar)
# ==========================================
st.sidebar.title("🔐 User Login")
current_user = st.sidebar.selectbox("Current User:", options=st.session_state.staff)
st.sidebar.success(f"Logged in as: **{current_user}**")
st.sidebar.divider()
st.sidebar.info("💡 **Manager Note:** Techs can only process samples if they have been trained on the specific Site Workflow SOP.")

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def calculate_pre_delay(draw_t, spin_t):
    if not draw_t or not spin_t: return "Z"
    today = date.today()
    dt_draw = datetime.combine(today, draw_t)
    dt_spin = datetime.combine(today, spin_t)
    if dt_spin < dt_draw: dt_spin = dt_spin.replace(day=today.day + 1)
    diff_hrs = (dt_spin - dt_draw).total_seconds() / 3600
    if diff_hrs < 2: return "A"
    elif 2 <= diff_hrs < 4: return "B"
    else: return "C"

def get_storage_code(temp):
    if temp == "-80°C": return "C"
    elif temp == "-20°C": return "Q"
    elif temp == "LN2": return "A"
    else: return "Z"

# ==========================================
# 4. UI LAYOUT & TABS
# ==========================================
st.title("🧬 LIMS & Automated Delegation Matrix")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "⚙️ 1. Setup Studies", "👥 2. Staff & DOA Training", "💉 3. Clinic", 
    "📥 4. Lab Intake", "🧪 5. Bench Processing", "❄️ 6. Storage", "📊 Master Log"
])

# --- TAB 1: SETUP ---
with tab1:
    st.subheader("Map Protocol Sample Types to Internal Workflows")
    col1, col2 = st.columns([1, 1.5])
    with col1:
        new_study = st.text_input("New Study Name:")
        new_samp_type = st.text_input("Sample Type (e.g., 'Visit 1 PK'):")
        assigned_wf = st.selectbox("Assign to Internal Workflow:", options=list(st.session_state.workflows.keys()))
        if st.button("Add Mapping to Study"):
            if new_study and new_samp_type:
                if new_study not in st.session_state.studies: st.session_state.studies[new_study] = {}
                st.session_state.studies[new_study][new_samp_type] = assigned_wf
                st.success(f"Added {new_samp_type} to {new_study}!")
                time.sleep(1)
                st.rerun()
    with col2:
        st.write("**Current Rosetta Stone Matrix:**")
        st.json(st.session_state.studies)

# --- TAB 2: STAFF & DOA TRAINING (NEW!) ---
with tab2:
    st.subheader("Automated SOP-to-Study Training Matrix")
    st.markdown("Use this to bypass the 200-study DOA burden. Train staff on SOPs, and let the system map it to the studies.")
    
    selected_staff = st.selectbox("Select Staff Member to view Delegation:", options=st.session_state.staff)
    trained_sops = st.session_state.training_matrix[selected_staff]
    
    st.info(f"**{selected_staff}** is officially trained on the following internal SOPs:\n" + "\n".join([f"- {sop}" for sop in trained_sops]))
    
    # Calculate which studies this unlocks
    unlocked_studies = []
    for study, types in st.session_state.studies.items():
        for s_type, wf in types.items():
            if wf in trained_sops:
                unlocked_studies.append(f"{study} ({s_type})")
    
    st.success(f"✅ Based on SOP training, {selected_staff} is authorized to process the following {len(unlocked_studies)} Sponsor Protocols:")
    st.write(unlocked_studies)
    
    st.button("🖨️ Print Master Training Certificate for PI Signature (Demo)")

# --- TAB 3: COLLECTION ---
with tab3:
    st.subheader("Clinic: Collect Samples from Patient")
    c_study = st.selectbox("Select Study:", options=list(st.session_state.studies.keys()), key="coll_study")
    available_types = list(st.session_state.studies[c_study].keys())
    c_subj = st.text_input("Subject ID:", key="coll_subj")
    c_types = st.multiselect("Select Sample Types Collected:", options=available_types)
    c_time = st.time_input("Exact Collection (Draw) Time:")
    
    if st.button("Log Collection"):
        if c_subj and c_types:
            for s_type in c_types:
                internal_uid = str(uuid.uuid4())[:8]
                new_row = pd.DataFrame([{
                    "Internal_ID": internal_uid, "Sample_Barcode": "Pending Lab", 
                    "Subject_ID": c_subj, "Study": c_study, "Sample_Type": s_type,
                    "Status": "Collected", "Draw_Time": c_time, "Spin_Time": None,
                    "Freeze_Time": None, "SPREC_Code": "Pending", "Location": "In Transit", 
                    "Action_By": current_user
                }])
                st.session_state.samples = pd.concat([st.session_state.samples, new_row], ignore_index=True)
            st.success("Samples logged!")
            time.sleep(1)
            st.rerun()

# --- TAB 4: LAB INTAKE ---
with tab4:
    st.subheader("Lab: Receive and Register Tubes")
    pending_reg = st.session_state.samples[st.session_state.samples["Status"] == "Collected"]
    
    if pending_reg.empty: st.info("No tubes currently waiting for lab intake.")
    else:
        for idx, row in pending_reg.iterrows():
            with st.expander(f"📥 Receive: Subject {row['Subject_ID']} - {row['Sample_Type']} ({row['Study']})"):
                barcode = st.text_input(f"Scan/Type Barcode for this tube:", key=f"bar_{row['Internal_ID']}")
                if st.button("Register Barcode", key=f"btn_{row['Internal_ID']}"):
                    if barcode:
                        wf_name = st.session_state.studies[row['Study']][row['Sample_Type']]
                        base_sprec = "-".join(st.session_state.workflows[wf_name]["sprec"])
                        st.session_state.samples.at[idx, "Sample_Barcode"] = barcode
                        st.session_state.samples.at[idx, "SPREC_Code"] = base_sprec
                        st.session_state.samples.at[idx, "Status"] = "Registered"
                        st.session_state.samples.at[idx, "Location"] = "Lab Bench"
                        st.session_state.samples.at[idx, "Action_By"] = current_user
                        st.success(f"Tube registered!")
                        time.sleep(1)
                        st.rerun()

# --- TAB 5: BENCH PROCESSING (WITH COMPLIANCE CHECK) ---
with tab5:
    st.subheader("Lab: Process Samples (Centrifugation)")
    pending_proc = st.session_state.samples[st.session_state.samples["Status"] == "Registered"]
    
    if pending_proc.empty: st.info("No samples waiting for processing.")
    else:
        proc_options = pending_proc["Sample_Barcode"].tolist()
        proc_samp = st.selectbox("Select Barcode to Process:", options=proc_options)
        
        idx = st.session_state.samples.index[st.session_state.samples["Sample_Barcode"] == proc_samp][0]
        row_data = st.session_state.samples.loc[idx]
        wf_name = st.session_state.studies[row_data['Study']][row_data['Sample_Type']]
        
        # --- THE COMPLIANCE CHECK ---
        st.write(f"**Required SOP:** {wf_name}")
        
        if wf_name not in st.session_state.training_matrix[current_user]:
            st.error(f"🛑 GCP COMPLIANCE HALT: **{current_user}** is not trained on **{wf_name}**.")
            st.warning("You are not authorized to process this sample. Please ask a delegated senior tech to log in, or complete the SOP training.")
        else:
            st.success(f"✅ Authorization Confirmed: {current_user} is trained on this SOP.")
            st.info(f"**Instructions:**\n{st.session_state.workflows[wf_name]['instructions']}")
            
            spin_t = st.time_input("Centrifuge Start Time:", key=f"spin_{proc_samp}")
            if st.button("Complete Processing"):
                pre_code = calculate_pre_delay(row_data["Draw_Time"], spin_t)
                st.session_state.samples.at[idx, "Spin_Time"] = spin_t
                st.session_state.samples.at[idx, "SPREC_Code"] = row_data["SPREC_Code"].replace("[PRE]", pre_code)
                st.session_state.samples.at[idx, "Status"] = "Processed"
                st.session_state.samples.at[idx, "Action_By"] = current_user
                st.success("Processed!")
                time.sleep(1)
                st.rerun()

# --- TAB 6: STORAGE ---
with tab6:
    st.subheader("Lab: Store Samples in Freezer")
    pending_store = st.session_state.samples[st.session_state.samples["Status"] == "Processed"]
    
    if pending_store.empty: st.info("No samples waiting for storage.")
    else:
        store_samp = st.selectbox("Select Barcode to Store:", options=pending_store["Sample_Barcode"].tolist())
        idx = st.session_state.samples.index[st.session_state.samples["Sample_Barcode"] == store_samp][0]
        
        freeze_t = st.time_input("Time placed in Freezer:")
        temp = st.selectbox("Freezer Temp:", ["-80°C", "-20°C", "LN2"])
        box_loc = st.text_input("Freezer Box Location:")
        
        if st.button("Store Sample"):
            if box_loc:
                sto_code = get_storage_code(temp)
                st.session_state.samples.at[idx, "Freeze_Time"] = freeze_t
                st.session_state.samples.at[idx, "SPREC_Code"] = st.session_state.samples.at[idx, "SPREC_Code"].replace("[STO]", sto_code)
                st.session_state.samples.at[idx, "Location"] = box_loc
                st.session_state.samples.at[idx, "Status"] = "Stored"
                st.session_state.samples.at[idx, "Action_By"] = current_user
                st.success("Stored!")
                time.sleep(1)
                st.rerun()

# --- TAB 7: MASTER LOG ---
with tab7:
    st.subheader("📋 Master Audit Trail & DOA Log")
    if st.session_state.samples.empty: st.write("Database is empty.")
    else:
        display_df = st.session_state.samples.drop(columns=["Internal_ID"])
        def color_status(val):
            colors = {"Collected": "red", "Registered": "orange", "Processed": "blue", "Stored": "purple"}
            return f'color: {colors.get(val, "black")}; font-weight: bold;'
        st.dataframe(display_df.style.map(color_status, subset=['Status']), use_container_width=True, hide_index=True)
