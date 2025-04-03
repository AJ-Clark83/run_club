import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta, timezone
import time

# --- App settings ---
st.set_page_config(page_title="Run Club Entry", initial_sidebar_state="collapsed")

# --- Supabase connection ---
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# --- Timezone and date setup ---
now = datetime.now(timezone(timedelta(hours=8)))
today_str = now.strftime('%Y-%m-%d')

# --- Dynamic cutoff date (Jan 1 this year) ---
CUTOFF_DATE = datetime(now.year, 1, 1)

# --- Fetch room numbers for a year (with timestamp cutoff) ---
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

# --- Fetch students for year + room (with timestamp cutoff) ---
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

# --- Insert student attendance into Supabase ---
def add_student(student_name, year, room_number):
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    clean_name = student_name.strip().lower()
    supabase.table('run club').insert({
        'student_name': clean_name,
        'year': year,
        'room_number': room_number,
        'timestamp': timestamp
    }).execute()

# --- Streamlit UI ---

st.title("Run Club Registration")

# --- Year selection ---
year_options = [""] + ['Kindy', 'PP', '1', '2', '3', '4', '5', '6']
year = st.selectbox(
    'Select Year:',
    year_options,
    index=year_options.index(st.session_state.get('year_select', "")),
    key='year_select'
)

# --- Room selection ---
room_numbers = get_room_numbers(year) if year else []
room_numbers.append('Other')
room_numbers = [""] + room_numbers
room_choice = st.selectbox('Select Room Number:', room_numbers, key='room_select')

# --- Room input logic ---
room_number = ""
if room_choice == 'Other':
    room_number_input = st.text_input('Enter Room Number:', key='room_other')
    if room_number_input:
        room_number_upper = room_number_input.upper()
        is_valid = (
            room_number_input.isdigit() or
            (len(room_number_upper) == 1 and room_number_upper in ['A', 'B', 'C', 'D']) or
            room_number_upper in ['PP1', 'PP2', 'PP3', 'PP4']
        )
        if not is_valid:
            st.error("Please enter a valid room: a number, A–D, or PP1–PP4.")
            st.stop()
        room_number = room_number_upper
else:
    room_number = room_choice if room_choice else ""

# --- Student selection ---
student_name = ""
if year and room_number:
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

# --- Submit button ---
if st.button('Submit'):
    if student_name and year and room_number:
        result = supabase.table('run club').select('id', 'timestamp') \
            .eq('student_name', student_name.strip().lower()) \
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

            # Reset form fields to blank defaults
            for key in ['year_select', 'room_select', 'room_other', 'student_select', 'student_other']:
                st.session_state.pop(key, None)

            time.sleep(0.5)
            st.rerun()
    else:
        st.error("Please fill in all required fields.")
