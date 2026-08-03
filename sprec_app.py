import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import uuid

st.set_page_config(page_title="Site LIMS & SPREC Tracker", layout="wide", page_icon="🧬")

# ==========================================
# 1. INITIALIZE SESSION STATE (Database)
# ==========================================
if 'workflows' not in st.session_state:
    st.session_state.workflows = {
        "Workflow A (Standard Serum)": {"sprec": ["SER", "SST", "[PRE]", "C", "A", "A", "[STO]"], "instructions": "30m Room Temp clot. Spin 2000g x 15m. Freeze -80°C."},
        "Workflow B (Standard EDTA Plasma)": {"sprec": ["PL2", "PED", "[PRE]", "C", "A", "A", "[STO]"], "instructions": "Keep at Room Temp. Spin 2000g x 15m. Freeze -80°C."},
        "Workflow C (Cold PK Plasma)": {"sprec": ["PL2", "PED", "[PRE]", "E", "A", "A", "[STO]"], "instructions": "Place on ICE. Spin CHILLED 2000g x 15m. Freeze -80°C."},
        "Workflow D (Urine - No Spin)": {"sprec": ["URN", "CUP", "Z", "N", "N", "N", "[STO]"], "instructions": "Aliquot directly. No centrifugation. Freeze -20°C."}
    }

if 'studies' not in st.session_state:
    st.session_state.studies = {
        "Pfizer Protocol 101": {
            "Biomarker Serum": "Workflow A (Standard Serum)",
            "PK Plasma": "Workflow C (Cold PK Plasma)"
        },
        "Novartis Core": {
            "Safety Plasma": "Workflow B (Standard EDTA Plasma)",
            "Urinalysis": "Workflow D (Urine - No Spin)"
        }
    }

if 'samples' not in st.session_state:
    st.session_state.samples = pd.DataFrame(columns=[
        "Internal_ID", "Sample_Barcode", "Subject_ID", "Study", "Sample_Type",
        "Status", "Draw_Time", "Spin_Time", "Freeze_Time", 
        "SPREC_Code", "Location", "Tracking_Number"
    ])

# ==========================================
# 2. HELPER FUNCTIONS
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
# 3. UI LAYOUT & TABS
# ==========================================
st.title("🧬 Comprehensive Clinical Site LIMS")
st.markdown("**Lifecycle:** Setup ➡️ Translator Demo ➡️ Collection ➡️ Registration ➡️ Processing ➡️ Storage ➡️ Shipment")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "⚙️ 1. Setup", "📖 2. SPREC Translator", "💉 3. Collection", "📥 4. Registration", 
    "🧪 5. Processing", "❄️ 6. Storage", "📦 7. Shipment", "📊 Master Log"
])

# --- TAB 1: SETUP ---
with tab1:
    st.subheader("Map Protocol Sample Types to Internal Workflows")
    col1, col2 = st.columns([1, 1.5])
    with col1:
        new_study = st.text_input("Existing or New Study Name:")
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
        st.write("**Current Study -> Sample Type Mappings:**")
        st.json(st.session_state.studies)

# --- TAB 2: SPREC TRANSLATOR DEMO (NEW SECTION) ---
with tab2:
    st.subheader("Interactive SPREC 3.0 Translator (Fluids)")
    st.write("Train your staff on how a Sponsor's Lab Manual translates into a 7-element SPREC code.")
    
    st.info('**Mock Sponsor Instruction:**\n"Collect blood into a Lavender K2EDTA tube. Place immediately on crushed ice. Spin within 30 minutes at 2000g for 15 mins in a refrigerated centrifuge (4°C). Do not double spin. Freeze immediately at -80°C."')
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        el1 = st.selectbox("1. Fluid Type", ["PL1 (Plasma, Single Spin)", "PL2 (Plasma, Double Spin)", "SER (Serum)", "URN (Urine)"])
        el2 = st.selectbox("2. Primary Container", ["PED (Potassium EDTA)", "SST (Serum Separator)", "HEP (Heparin)", "CUP (Urine Cup)"])
    with c2:
        el3 = st.selectbox("3. Pre-Centrifugation (Draw to Spin)", ["E (<2h, 2-8°C / on ice)", "A (<2h, Room Temp)", "B (2-4h, Room Temp)", "C (4-8h, Room Temp)"])
        el4 = st.selectbox("4. 1st Centrifugation", ["E (10-15m, 2-8°C, 1000-3000g)", "A (10-15m, RT, 1000-3000g)", "B (10-15m, RT, >3000g)", "N (No spin)"])
    with c3:
        el5 = st.selectbox("5. 2nd Centrifugation", ["A (No 2nd spin)", "B (10-15m, RT, >3000g)", "N (No spin)"])
        el6 = st.selectbox("6. Post-Centrifugation Delay", ["A (<1h to freeze)", "B (1-2h to freeze)", "N (Not applicable)"])
    with c4:
        el7 = st.selectbox("7. Storage Temperature", ["C (-85 to -60°C)", "Q (-35 to -18°C)", "A (Liquid Nitrogen)"])

    # Extract just the codes (the first 3 letters of the selection)
    code = f"{el1[:3]}-{el2[:3]}-{el3[:1]}-{el4[:1]}-{el5[:1]}-{el6[:1]}-{el7[:1]}"
    
    st.divider()
    st.markdown(f"<h2 style='text-align: center; color: #1f77b4;'>Generated SPREC Code: {code}</h2>", unsafe_allow_html=True)
    if code == "PL1-PED-E-E-A-A-C":
        st.success("✅ **Perfect Match!** You correctly translated the mock sponsor instruction into SPREC.")
    else:
        st.warning("Try to match the mock instruction above to get the perfect SPREC code (Hint: PL1-PED-E-E-A-A-C).")

# --- TAB 3: COLLECTION (Clinic View) ---
with tab3:
    st.subheader("Clinic: Collect Samples from Patient")
    c_study = st.selectbox("Select Study:", options=list(st.session_state.studies.keys()), key="coll_study")
    available_types = list(st.session_state.studies[c_study].keys())
    
    c_subj = st.text_input("Subject ID:", key="coll_subj")
    c_types = st.multiselect("Select Sample Types Collected at this visit:", options=available_types)
    c_time = st.time_input("Exact Collection (Draw) Time:")
    
    if st.button("Log Collection"):
        if c_subj and c_types:
            for s_type in c_types:
                internal_uid = str(uuid.uuid4())[:8]
                new_row = pd.DataFrame([{
                    "Internal_ID": internal_uid, "Sample_Barcode": "Pending Lab Intake", 
                    "Subject_ID": c_subj, "Study": c_study, "Sample_Type": s_type,
                    "Status": "Collected", "Draw_Time": c_time, "Spin_Time": None,
                    "Freeze_Time": None, "SPREC_Code": "Pending", "Location": "In Transit to Lab", 
                    "Tracking_Number": ""
                }])
                st.session_state.samples = pd.concat([st.session_state.samples, new_row], ignore_index=True)
            st.success("Samples logged. Tubes are en route to lab.")
            time.sleep(1)
            st.rerun()

# --- TAB 4: REGISTRATION (Lab Intake) ---
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
                        st.success(f"Tube registered! Base SPREC applied.")
                        time.sleep(1)
                        st.rerun()

# --- TAB 5: PROCESSING (Bench) ---
with tab5:
    st.subheader("Lab: Process Samples (Centrifugation)")
    pending_proc = st.session_state.samples[st.session_state.samples["Status"] == "Registered"]
    
    if pending_proc.empty: st.info("No samples currently waiting for processing.")
    else:
        proc_options = pending_proc["Sample_Barcode"].tolist()
        proc_samp = st.selectbox("Select Barcode to Process:", options=proc_options)
        
        idx = st.session_state.samples.index[st.session_state.samples["Sample_Barcode"] == proc_samp][0]
        row_data = st.session_state.samples.loc[idx]
        wf_name = st.session_state.studies[row_data['Study']][row_data['Sample_Type']]
        
        st.info(f"**Instructions for {row_data['Sample_Type']}:**\n{st.session_state.workflows[wf_name]['instructions']}")
        
        if "URN" in row_data["SPREC_Code"]:
            st.warning("Urine sample. No centrifugation required.")
            if st.button("Mark as Processed (No Spin)"):
                st.session_state.samples.at[idx, "Status"] = "Processed"
                st.rerun()
        else:
            spin_t = st.time_input("Centrifuge Start Time:", key=f"spin_{proc_samp}")
            if st.button("Complete Processing"):
                pre_code = calculate_pre_delay(row_data["Draw_Time"], spin_t)
                st.session_state.samples.at[idx, "Spin_Time"] = spin_t
                st.session_state.samples.at[idx, "SPREC_Code"] = row_data["SPREC_Code"].replace("[PRE]", pre_code)
                st.session_state.samples.at[idx, "Status"] = "Processed"
                st.success("Processed!")
                time.sleep(1)
                st.rerun()

# --- TAB 6: STORAGE (Freezer) ---
with tab6:
    st.subheader("Lab: Store Samples in Freezer")
    pending_store = st.session_state.samples[st.session_state.samples["Status"] == "Processed"]
    
    if pending_store.empty: st.info("No samples currently waiting for storage.")
    else:
        store_samp = st.selectbox("Select Barcode to Store:", options=pending_store["Sample_Barcode"].tolist())
        idx = st.session_state.samples.index[st.session_state.samples["Sample_Barcode"] == store_samp][0]
        
        freeze_t = st.time_input("Time placed in Freezer:")
        temp = st.selectbox("Freezer Temperature:", ["-80°C", "-20°C", "LN2"])
        box_loc = st.text_input("Freezer Box Location:")
        
        if st.button("Store Sample"):
            if box_loc:
                sto_code = get_storage_code(temp)
                st.session_state.samples.at[idx, "Freeze_Time"] = freeze_t
                st.session_state.samples.at[idx, "SPREC_Code"] = st.session_state.samples.at[idx, "SPREC_Code"].replace("[STO]", sto_code)
                st.session_state.samples.at[idx, "Location"] = box_loc
                st.session_state.samples.at[idx, "Status"] = "Stored"
                st.success("Sample Stored!")
                time.sleep(1)
                st.rerun()

# --- TAB 7: SHIPMENT (Dispatch) ---
with tab7:
    st.subheader("Ship Samples to Central Lab")
    pending_ship = st.session_state.samples[st.session_state.samples["Status"] == "Stored"]
    
    if pending_ship.empty: st.info("No stored samples available to ship.")
    else:
        selected_to_ship = st.multiselect("Select Barcodes for Manifest:", options=pending_ship["Sample_Barcode"].tolist())
        tracking = st.text_input("Courier Tracking Number:")
        if st.button("Generate Manifest & Ship"):
            if selected_to_ship and tracking:
                for b_code in selected_to_ship:
                    idx = st.session_state.samples.index[st.session_state.samples["Sample_Barcode"] == b_code][0]
                    st.session_state.samples.at[idx, "Status"] = "Shipped"
                    st.session_state.samples.at[idx, "Tracking_Number"] = tracking
                    st.session_state.samples.at[idx, "Location"] = "Shipped"
                st.success("Samples shipped!")
                time.sleep(1)
                st.rerun()

# --- TAB 8: MASTER LOG ---
with tab8:
    st.subheader("📋 Master Sample Audit Trail")
    if st.session_state.samples.empty: st.write("Database is empty.")
    else:
        display_df = st.session_state.samples.drop(columns=["Internal_ID"])
        def color_status(val):
            colors = {"Collected": "red", "Registered": "orange", "Processed": "blue", "Stored": "purple", "Shipped": "green"}
            return f'color: {colors.get(val, "black")}; font-weight: bold;'
        st.dataframe(display_df.style.map(color_status, subset=['Status']), use_container_width=True, hide_index=True)
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Master Manifest (CSV)", data=csv, file_name='master_sample_log.csv', mime='text/csv')
