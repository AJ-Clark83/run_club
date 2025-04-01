import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta, timezone
import time

# Access credentials from secrets
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]

supabase: Client = create_client(url, key)

# Cutoff datetime for filtering
DATE_CUTOFF = datetime(2025, 1, 1)

# Function to get unique room numbers for a given year after cutoff
def get_room_numbers(year):
    result = supabase.table('run club').select('room_number', 'timestamp').eq('year', year).execute()
    rooms = set()
    for entry in result.data:
        ts_str = entry.get('timestamp')
        room = entry.get('room_number')
        if ts_str and room:
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts >= DATE_CUTOFF:
                    rooms.add(room)
            except Exception:
                pass
    return sorted(rooms)

# Function to fetch students based on year and room after cutoff
def get_students(year, room_number):
    result = supabase.table('run club').select('student_name', 'timestamp').eq('year', year).eq('room_number', room_number).execute()
    students = set()
    for entry in result.data:
        ts_str = entry.get('timestamp')
        name = entry.get('student_name')
        if ts_str and name:
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts >= DATE_CUTOFF:
                    students.add(name)
            except Exception:
                pass
    return sorted(students)

# Function to add new student
def add_student(student_name, year, room_number):
    now = datetime.now(timezone(timedelta(hours=8)))  # UTC+8
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')  # Format for Supabase datetime field
    supabase.table('run club').insert({
        'student_name': student_name,
        'year': year,
        'room_number': room_number,
        'timestamp': timestamp
    }).execute()

# Streamlit UI
st.title('Run Club Registration')

year = st.selectbox('Select Year:', ['Kindy', 'PP', 1, 2, 3, 4, 5, 6])

room_numbers = get_room_numbers(year)

if not room_numbers:
    st.warning("No recent rooms found for this year — please add one.")

room_numbers.append('Other')
room_choice = st.selectbox('Select Room Number:', room_numbers)

if room_choice == 'Other':
    room_number = st.text_input('Enter Room Number (numbers only):')
    if room_number and not room_number.isdigit():
        st.error("Please enter a valid room number (digits only).")
        st.stop()
else:
    room_number = room_choice

if room_number:
    existing_students = get_students(year, room_number)

    if existing_students:
        student_options = [""] + existing_students + ["Other"]
        student_choice = st.selectbox("Select Student:", student_options, index=0)
        if student_choice == "Other":
            student_name = st.text_input('Enter Student Name:')
        elif student_choice:
            student_name = student_choice
        else:
            student_name = ""
    else:
        student_name = st.text_input('Enter Student Name:')

    if st.button('Submit'):
        if student_name:
            if student_name not in existing_students:
                add_student(student_name, year, room_number)
                st.success(f'{student_name} added to the database!')
            else:
                st.success(f'{student_name} has been registered for this session!')
            time.sleep(2)
            st.rerun()
        else:
            st.error('Please enter a student name.')
