import streamlit as st
import openai
from datetime import datetime, date, time
import PyPDF2
import io
import json

# Configuration
OPENROUTER_API_KEY = "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"
client = openai.OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

# Initialize session state
if 'shift_config' not in st.session_state:
    st.session_state.shift_config = {
        'shifts': [],
        'doctors': {},
        'nurses': []
    }

if 'patients' not in st.session_state:
    st.session_state.patients = []

if 'beds' not in st.session_state:
    st.session_state.beds = [{'status': 'free', 'patient': None} for _ in range(20)]

if 'current_stage' not in st.session_state:
    st.session_state.current_stage = "onboarding"

# Helper functions
def parse_prescription(file):
    if file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(file)
        text = "\n".join(page.extract_text() or '' for page in pdf_reader.pages)
        return f"PDF Prescription:\n{text}"
    elif file.type == "text/plain":
        return file.read().decode()
    return "Unsupported file format"

def generate_ai_summary(prompt):
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct:free",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI Error: {str(e)}"

def parse_test_reports(uploaded_files):
    """Process uploaded test reports (PDF/TXT) and extract text content"""
    text_content = []
    for file in uploaded_files:
        try:
            if file.type == "application/pdf":
                pdf_reader = PyPDF2.PdfReader(file)
                text = "\n".join(page.extract_text() or '' for page in pdf_reader.pages)
                text_content.append(f"PDF Report Content:\n{text}")
            elif file.type == "text/plain":
                text_content.append(file.read().decode("utf-8"))
            else:
                text_content.append(f"Unsupported file format: {file.type}")
        except Exception as e:
            text_content.append(f"Error processing {file.name}: {str(e)}")
    return "\n\n".join(text_content)

# Top Metrics
st.markdown("## Emergency Department Dashboard")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("**Active Cases**")
    st.write(len(st.session_state.patients))
with col2:
    st.markdown("**Free Beds**")
    st.write(sum(1 for b in st.session_state.beds if b['status'] == 'free'))
with col3:
    deceased = sum(1 for p in st.session_state.patients if p.get('status') == 'Deceased')
    st.markdown("**Deceased Cases**")
    st.write(deceased)
with col4:
    st.markdown("**Shift Admissions**")
    st.write(len([p for p in st.session_state.patients if p.get('admission_shift') == "Current Shift"]))

# Navigation
page = st.sidebar.selectbox("Navigation", ["Shift Management", "Current Shift"])

if page == "Shift Management":
    st.header("📅 Shift Management")
    
    with st.expander("Configure Shifts"):
        shifts = st.number_input("Number of Shifts", 1, 3, 2)
        shift_config = []
        
        for i in range(shifts):
            st.subheader(f"Shift {i+1}")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(f"Shift Name {i+1}", value=f"Shift {i+1}")
            with col2:
                start = st.time_input(f"Start Time {i+1}", value=time(8 if i==0 else 20))
                end = st.time_input(f"End Time {i+1}", value=time(20 if i==0 else 8))
            
            st.subheader("Doctors")
            chief = st.text_input(f"Chief Doctor {i+1}", value="Dr. Smith")
            reporting = st.text_input(f"Reporting Doctors {i+1}", value="Dr. Johnson, Dr. Williams")
            emergency = st.text_input(f"Emergency Doctors {i+1}", value="Dr. Brown")
            
            st.subheader("Nurses")
            nurses = []
            num_nurses = st.number_input(f"Number of Nurses {i+1}", 1, 10, 3)
            for n in range(num_nurses):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input(f"Nurse {n+1} Name", key=f"nurse_{i}_{n}_name")
                with col2:
                    contact = st.text_input(f"Contact", key=f"nurse_{i}_{n}_contact")
                nurses.append({'name': name, 'contact': contact})
            
            shift_config.append({
                'name': name,
                'timing': f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}",
                'chief': chief,
                'reporting': reporting,
                'emergency': emergency,
                'nurses': nurses
            })
        
        if st.button("Save Shift Configuration"):
            st.session_state.shift_config['shifts'] = shift_config
            st.success("Shift configuration saved!")

    # Display current configuration
    st.header("Current Shift Configuration")
    for shift in st.session_state.shift_config.get('shifts', []):
        st.subheader(shift['name'])
        st.markdown(f"**Timing:** {shift['timing']}")
        st.markdown(f"**Chief Doctor:** {shift['chief']}")
        st.markdown(f"**Reporting Doctors:** {shift['reporting']}")
        st.markdown(f"**Emergency Doctors:** {shift['emergency']}")
        st.markdown("**Nurses:**")
        for nurse in shift['nurses']:
          st.markdown(f"- {nurse['name']} ({nurse['contact']})")
elif page == "Current Shift":
    st.header("Current Shift Management")
    
    # Modified patient onboarding to remove form boxes
    if st.session_state.current_stage == "onboarding":
        st.subheader("Patient Onboarding")
        
        name = st.text_input("Patient Name")
        contact = st.text_input("Contact Number")
        address = st.text_input("Address")
        emergency_contact = st.text_input("Emergency Contact")
        prescriptions = st.file_uploader("Upload Prescriptions", type=["pdf", "txt"])
        assigned_nurse = st.selectbox("Duty Nurse", 
            [n['name'] for shift in st.session_state.shift_config['shifts'] 
             for n in shift['nurses']])
        
        st.subheader("Vital Signs")
        heart_rate = st.number_input("Heart Rate (bpm)", 40, 200, 80)
        bp = st.text_input("Blood Pressure (mmHg)", "120/80")
        temp = st.number_input("Temperature (°C)", 35.0, 42.0, 37.0)
        oxygen = st.number_input("O₂ Saturation (%)", 70, 100, 98)
        
        if st.button("Next"):
            patient_data = {
                'name': name,
                'contact': contact,
                'address': address,
                'emergency_contact': emergency_contact,
                'vitals': {
                    'heart_rate': heart_rate,
                    'bp': bp,
                    'temp': temp,
                    'oxygen': oxygen
                },
                'nurse': assigned_nurse,
                'prescription': parse_prescription(prescriptions) if prescriptions else None,
                'admission_shift': "Current Shift"  # Added admission shift tracking
            }
            st.session_state.current_patient = patient_data
            st.session_state.current_stage = "incident_description"
            st.rerun()


    elif st.session_state.current_stage == "incident_description":
        st.header("📝 Incident Description")
        patient = st.session_state.current_patient
        
        prompt = f"""Generate incident description based on:
        Patient: {patient['name']}
        Vital Signs: {json.dumps(patient['vitals'])}
        Prescriptions: {patient['prescription']}
        Respond in narrative format as observed by nurse."""
        
        ai_description = generate_ai_summary(prompt)
        
        with st.form("incident_form"):
            incident = st.text_area("Incident Description", value=ai_description, height=300)
            
            
            if st.form_submit_button("Generate Evaluation ➡️"):
                st.session_state.current_patient.update({
                    'incident': incident,
                    
                })
                st.session_state.current_stage = "ai_evaluation"
                st.rerun()

    elif st.session_state.current_stage == "ai_evaluation":
        st.header("🩺 AI Medical Evaluation")
        patient = st.session_state.current_patient
        
        prompt = f"""Perform complete medical evaluation for:
        Patient: {patient['name']}
        Vital Signs: {json.dumps(patient['vitals'])}
        Incident: {patient['incident']}
        Prescription History: {patient['prescription']}
        
        Include:
        1. Preliminary Diagnosis
        2. Physical Examination Summary
        3. Recommended Tests"""
        
        evaluation = generate_ai_summary(prompt)
        
        with st.form("eval_form"):
            st.text_area("AI Evaluation", value=evaluation, height=300)
            if st.form_submit_button("Proceed to Treatment ➡️"):
                st.session_state.current_patient['evaluation'] = evaluation
                st.session_state.current_stage = "treatment_plan"
                st.rerun()

    elif st.session_state.current_stage == "treatment_plan":
        st.header("💊 Treatment Planning")
        patient = st.session_state.current_patient
        
        prompt = f"""Generate treatment plan based on:
        {patient['evaluation']}
        Include medication, procedures, and follow-up recommendations."""
        
        treatment = generate_ai_summary(prompt)
        
        with st.form("treatment_form"):
            st.session_state.current_patient['treatment'] = st.text_area("AI Treatment Plan", 
                                                                        value=treatment, 
                                                                        height=300)
            tests = st.file_uploader("Upload Test Results", 
                                    type=["pdf", "txt","png"], 
                                    accept_multiple_files=True)
            
            if st.form_submit_button("Analyze Results ➡️"):
                test_results = parse_test_reports(tests) if tests else "No test results"
                st.session_state.current_patient['test_results'] = test_results
                st.session_state.current_stage = "final_report"
                st.rerun()

    elif st.session_state.current_stage == "final_report":
        st.header("📑 Final Medical Report")
        patient = st.session_state.current_patient
        
        prompt = f"""Generate final medical report including:
        1. Patient Summary
        2. Diagnostic Results
        3. Treatment Protocol
        4. Discharge Criteria
        5. Follow-up Schedule
        6. Red Flags Monitoring
        7. Classify the severity Group
        
        Base this on:
        {patient['evaluation']}
        {patient['treatment']}
        Test Results: {patient['test_results']}"""
        
        final_report = generate_ai_summary(prompt)
        
        with st.form("final_form"):
            st.text_area("Complete Medical Report", value=final_report, height=400)
            
            if st.form_submit_button("Complete Admission"):
                bed_index = next(i for i, bed in enumerate(st.session_state.beds) 
                            if bed['status'] == 'free')
                
                full_record = {
                    **st.session_state.current_patient,
                    'admission_time': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'status': 'Admitted',
                    'bed': bed_index+1,
                    'final_report': final_report
                }
                
                st.session_state.patients.append(full_record)
                st.session_state.beds[bed_index] = {
                    'status': 'occupied',
                    'patient': full_record
                }
                
                st.session_state.current_stage = "onboarding"
                st.session_state.current_patient = None
                st.success("Patient admission completed!")
                st.rerun()
    # Bed Management Display
  # Add to session state initialization
    # Bed Management Display
    if 'show_beds' not in st.session_state:
        st.session_state.show_beds = False

    toggle_label = '➕ Show Bed Status' if not st.session_state.show_beds else '➖ Hide Bed Status'
    if st.button(toggle_label, key='toggle_beds'):
        st.session_state.show_beds = not st.session_state.show_beds

    if st.session_state.show_beds:
        st.subheader("Bed Status")
        cols = st.columns(5)
        for i, bed in enumerate(st.session_state.beds):
            with cols[i%5]:
                status = "Free" if bed['status'] == 'free' else "Occupied"
                st.markdown(f"**Bed {i+1}**")
                st.write(status)
                if st.button("Details", key=f"bed_{i}"):
                    st.session_state.selected_bed = i

        if 'selected_bed' in st.session_state:
            bed = st.session_state.beds[st.session_state.selected_bed]
            if bed['patient']:
                st.subheader(f"Bed {st.session_state.selected_bed+1} Details")
                patient = bed['patient']
                with st.expander("Full Record"):
                    st.json(patient)