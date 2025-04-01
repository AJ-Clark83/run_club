import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta, timezone
import time

# Connect to Supabase
url = "https://bomtlnyvgkqsrigvclaj.supabase.co"
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# Set timezone
now = datetime.now(timezone(timedelta(hours=8)))
today_str = now.strftime('%Y-%m-%d')

# Set filter cutoff date for active rooms/students
CUTOFF_DATE = datetime(2025, 1, 1)

# Helper: fetch room numbers for a year, with timestamp >= 2025
def get_room_numbers(year):
    result = supabase.table('run club').select('room_number', 'timestamp').eq('year', year).execute()
    rooms = set()
    for entry in result.data:
        ts = entry.get('timestamp')
        room = entry.get('room_number')
        if ts and room:
            try:
                ts_dt = datetime.fromisoformat(ts)
                if ts_dt >= CUTOFF_DATE:
                    rooms.add(room)
            except:
                pass
    return sorted(rooms)

# Helper: fetch students for year + room, with timestamp >= 2025
def get_students(year, room_number):
    result = supabase.table('run club').select('student_name', 'timestamp') \
        .eq('year', year).eq('room_number', room_number).execute()
    students = set()
    for entry in result.data:
        ts = entry.get('timestamp')
        name = entry.get('student_name')
        if ts and name:
            try:
                ts_dt = datetime.fromisoformat(ts)
                if ts_dt >= CUTOFF_DATE:
                    students.add(name)
            except:
                pass
    return sorted(students)

# Helper: insert runner attendance
def add_student(student_name, year, room_number):
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    supabase.table('run club').insert({
        'student_name': student_name,
        'year': year,
        'room_number': room_number,
        'timestamp': timestamp
    }).execute()

# --- Streamlit UI ---

st.title("Run Club Registration")

# Year selection
year = st.selectbox('Select Year:', ['Kindy', 'PP', 1, 2, 3, 4, 5, 6], key='year_select')

# Room selection
room_numbers = get_room_numbers(year)
room_numbers.append('Other')
room_choice = st.selectbox('Select Room Number:', room_numbers, key='room_select')

if room_choice == 'Other':
    room_number = st.text_input('Enter Room Number (numbers only):', key='room_other')
    if room_number and not room_number.isdigit():
        st.error("Please enter a valid room number (digits only).")
        st.stop()
else:
    room_number = room_choice

# Student selection
student_name = ""
if room_number:
    existing_students = get_students(year, room_number)

    if existing_students:
        student_options = [""] + existing_students + ["Other"]
        student_choice = st.selectbox('Select Student:', student_options, index=0, key='student_select')

        if student_choice == "Other":
            student_name = st.text_input('Enter Student Name:', key='student_other')
        elif student_choice:
            student_name = student_choice
    else:
        student_name = st.text_input('Enter Student Name:', key='student_other')

# Submit button
if st.button('Submit'):
    if student_name:
        # Check if student already registered today
        result = supabase.table('run club').select('id', 'timestamp') \
            .eq('student_name', student_name) \
            .eq('year', year) \
            .eq('room_number', room_number).execute()

        already_registered_today = any(
            entry.get('timestamp', '').startswith(today_str) for entry in result.data
        )

        if already_registered_today:
            st.warning(f"{student_name} has already been registered today.")
        else:
            add_student(student_name, year, room_number)
            st.success(f"{student_name} has been registered!")

            # Reset form fields
            for key in ['year_select', 'room_select', 'room_other', 'student_select', 'student_other']:
                if key in st.session_state:
                    del st.session_state[key]

            time.sleep(2)
            st.rerun()
    else:
        st.error("Please enter a student name.")
