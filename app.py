import pandas as pd
import streamlit as st
from supabase import create_client, Client

# --- Supabase connection ---
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# --- Data cleaning function ---
def clean_data(df):
    if 'student_name' in df.columns:
        df['student_name'] = df['student_name'].str.lower().str.strip()

    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['Run Year'] = df['timestamp'].dt.year
        df['Date'] = df['timestamp'].dt.date
    else:
        df['timestamp'] = pd.NaT
        df['Run Year'] = None
        df['Date'] = None

    if 'room_number' in df.columns:
        df['room_number'] = df['room_number'].str.lower().str.strip().str.replace(r'\broom\b\s*', '', regex=True)
        df['room_number'] = df['room_number'].str.replace('kindy c', 'kindy')

    df = df.rename(columns={
        'student_name': 'Student Name',
        'room_number': 'Room Number',
        'year': 'Year',
    })

    df = df.drop(columns=[col for col in ['Laps Completed (Sprints / Laps)', 'id'] if col in df.columns])

    if 'Date' in df.columns and df['Date'].notna().any():
        df = df.sort_values(by='Date')

    return df

# --- Load and clean data ---
response = supabase.table('run club').select('*').execute()
df_raw = pd.DataFrame(response.data)
df = clean_data(df_raw)

# --- UI layout ---
st.title('Carnaby Running Club Stats')

view = st.selectbox('View Stats By', ['Student Name', 'Date'], key='view_selector')

st.markdown("<hr style='border-top: 2px solid #082251; margin: 20px 0;'>", unsafe_allow_html=True)

# === VIEW: By Date ===
if view == 'Date':
    st.header('Run Data By Date')
    st.markdown("<hr style='border-top: 2px solid #082251; margin: 20px 0;'>", unsafe_allow_html=True)

    st.subheader('Attendance by Date')
    date_options = df['Date'].dropna().astype(str).unique()
    selected_date = st.selectbox('Select a Date', date_options, key='date_filter')

    # Filter data
    filtered_data = df[df['Date'].astype(str) == selected_date]
    filtered_data['Date'] = pd.to_datetime(filtered_data['Date']).dt.strftime('%d-%m-%Y')

    # Total runs per day
    runs_per_day = df.groupby('Date')['Student Name'].count().reset_index()
    runs_per_day.columns = ['Date', 'Total Runs']
    runs_per_day['Date'] = pd.to_datetime(runs_per_day['Date'])
    runs_per_day = runs_per_day.sort_values(by='Date')
    runs_per_day['Date_Display'] = runs_per_day['Date'].dt.strftime('%Y-%m-%d')
    runs_per_day.set_index('Date_Display', inplace=True)

    st.subheader('Total Runs by Date')
    st.dataframe(runs_per_day[['Total Runs']], hide_index=True, use_container_width=True)

    st.subheader('Total Runs Trend')
    st.line_chart(runs_per_day['Total Runs'], use_container_width=True)

    # Unique runners
    unique_count = len(df['Student Name'].unique())
    st.subheader('Total Unique Runners')
    st.write(f'Number of unique students: {unique_count}')

    # Room-level stats for selected date
    room_stats = (
        filtered_data.groupby(['Year', 'Room Number'])['Student Name']
        .nunique()
        .reset_index()
        .rename(columns={'Student Name': 'Unique Runners'})
        .sort_values(by='Unique Runners', ascending=False)
        .reset_index(drop=True)
    )

    st.subheader('Runners by Year and Room For Selected Date')
    st.dataframe(room_stats, hide_index=True, use_container_width=True)

    # Filter runner list by room
    st.subheader(f'Runners on {selected_date} for Selected Room')
    rooms = filtered_data['Room Number'].sort_values().unique()
    selected_room = st.selectbox('Select a Room', rooms, key='room_filter')
    runners_in_room = filtered_data[filtered_data['Room Number'] == selected_room]
    st.dataframe(runners_in_room, hide_index=True, use_container_width=True)

# === VIEW: By Student Name ===
elif view == 'Student Name':
    st.header('Run Data By Student')
    st.markdown("<hr style='border-top: 2px solid #082251; margin: 20px 0;'>", unsafe_allow_html=True)

    st.subheader('Filter by Run Club Year')
    available_years = sorted(df['Run Year'].dropna().unique(), reverse=True)
    selected_run_year = st.selectbox('Select Run Club Year', available_years, key='run_year_filter')

    df = df[df['Run Year'] == selected_run_year]

    year_options = ['All'] + df['Year'].dropna().sort_values().unique().tolist()
    selected_year = st.selectbox('Select School Year', year_options, key='year_filter')

    top_runners = (
        df.groupby(['Student Name', 'Year', 'Room Number'])
        .size()
        .reset_index(name='Days Run')
        .sort_values(by='Days Run', ascending=False)
    )

    filtered_runners = top_runners if selected_year == 'All' else top_runners[top_runners['Year'] == selected_year]
    min_days = st.slider('Minimum Days Run', min_value=1, max_value=filtered_runners['Days Run'].max(), value=1, key='min_days_filter')
    filtered_runners = filtered_runners[filtered_runners['Days Run'] >= min_days]

    st.subheader(f'Top Runners ({selected_year}, Min {min_days} Days)')
    st.table(filtered_runners)

    unique_count_filtered = len(filtered_runners['Student Name'].unique())
    st.subheader(f'Number of Unique Runners ({selected_year}, Min {min_days} Days)')
    st.write(f'Number of unique students: {unique_count_filtered}')

    selected_student = st.selectbox('Select a Student', df['Student Name'].dropna().unique(), key='student_filter')
    student_data = df[df['Student Name'] == selected_student]
    student_data['Date'] = pd.to_datetime(student_data['Date']).dt.strftime('%d-%m-%Y')

    st.subheader(f'Attendance for {selected_student}')
    st.table(student_data)
