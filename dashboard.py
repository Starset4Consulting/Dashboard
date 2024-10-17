import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import pytz
from datetime import datetime

# Initialize the database connection
def connect_db():
    # PostgreSQL connection string
    db_url = f"postgresql://aimim_user:fhH2YntIUtHxicimP5M6RCpcu3AOmJMx@dpg-cs10b0a3esus7399aghg-a.singapore-postgres.render.com:5432/aimim"
    engine = create_engine(db_url)
    return engine

# Load user data
def load_users():
    engine = connect_db()
    users = pd.read_sql_query("SELECT id, phone_number, username FROM users", engine)
    return users

# Load survey data
def load_surveys():
    engine = connect_db()
    surveys = pd.read_sql_query("SELECT id, name, questions FROM surveys", engine)
    return surveys

# Load survey responses along with user phone numbers and timestamp
def load_survey_responses():
    engine = connect_db()
    query = """
    SELECT sr.id, sr.responses, sr.survey_id, u.phone_number, sr.location, sr.voice_recording_path, sr.response_timestamp 
    FROM survey_responses sr
    JOIN users u ON sr.user_id = u.id
    """
    responses = pd.read_sql_query(query, engine)
    return responses

# Function to map responses with correct questions
def map_responses_to_questions(survey_questions, raw_response):
    if isinstance(raw_response, str):
        response_data = eval(raw_response)
    else:
        response_data = raw_response

    mapped_responses = {}
    for idx, question in enumerate(survey_questions):
        q_id = str(idx)  # Match the response number with the question index
        if q_id in response_data:
            mapped_responses[question['text']] = response_data[q_id]

    return mapped_responses

# Function to analyze responses for a selected question
def analyze_question_responses(selected_question, filtered_responses, survey_questions):
    option_counts = {}

    for index, row in filtered_responses.iterrows():
        try:
            mapped_responses = map_responses_to_questions(survey_questions, row['responses'])
            if selected_question in mapped_responses:
                selected_option = mapped_responses[selected_question]
                if selected_option in option_counts:
                    option_counts[selected_option] += 1
                else:
                    option_counts[selected_option] = 1
        except Exception as e:
            st.write(f"Error processing response for row {index}: {row['responses']}")
            continue

    return option_counts

def location_based_analysis(responses):
    if 'location' in responses.columns:
        locations = responses['location'].dropna().apply(eval)
        latitudes = locations.apply(lambda x: x.get('latitude', None))
        longitudes = locations.apply(lambda x: x.get('longitude', None))
        location_df = pd.DataFrame({'latitude': latitudes, 'longitude': longitudes})
        location_df = location_df.dropna()
        if not location_df.empty:
            st.subheader("Location-Based Analysis")
            fig = px.scatter_mapbox(location_df, lat="latitude", lon="longitude", zoom=5, height=400)
            fig.update_layout(mapbox_style="open-street-map")
            st.plotly_chart(fig)

# Function to convert UTC to IST
def convert_to_ist(utc_timestamp):
    utc_time = pd.to_datetime(utc_timestamp, utc=True)
    ist_timezone = pytz.timezone('Asia/Kolkata')
    ist_time = utc_time.tz_convert(ist_timezone)
    return ist_time

# Function to generate the Streamlit dashboard
def main():
    st.set_page_config(page_title="Starset Consultancy Services - Survey Dashboard", layout="wide")

    # Sidebar and logo header
    st.sidebar.image('logo.png', use_column_width=True)
    st.sidebar.title("Starset Consultancy Services")

    st.title("Survey Data Dashboard")

    # Load data from the database
    users = load_users()
    surveys = load_surveys()
    responses = load_survey_responses()

    # Convert 'response_timestamp' to IST
    responses['response_timestamp'] = responses['response_timestamp'].apply(convert_to_ist)

    # Create a filter for selecting surveys and users
    survey_filter = st.sidebar.selectbox("Select Survey", surveys['name'].unique())

    # Filter the responses based on the selected survey
    filtered_survey_id = surveys[surveys['name'] == survey_filter].iloc[0]['id']
    filtered_responses = responses[responses['survey_id'] == filtered_survey_id]

    # Add a phone number filter to the sidebar
    phone_filter = st.sidebar.selectbox("Select Phone Number", users['phone_number'].unique())
    filtered_responses = filtered_responses[filtered_responses['phone_number'] == phone_filter]

    # Get the questions for the selected survey
    survey_questions_str = surveys[surveys['name'] == survey_filter].iloc[0]['questions']
    survey_questions_str = survey_questions_str.replace('true', 'True').replace('false', 'False')
    survey_questions = eval(survey_questions_str)

    # Extract question texts for the dropdown
    question_list = [q['text'] for q in survey_questions]
    selected_question = st.sidebar.selectbox("Select Question to Analyze", question_list)

    st.write(f"### Showing Responses for Survey: {survey_filter}")

    # Pagination variables
    rows_per_page = 100000000000000000000000000000000000000000000000000000000000000
    page_number = st.sidebar.number_input("Page Number", min_value=1, max_value=(len(filtered_responses) // rows_per_page) + 1, step=1)

    # Calculate starting and ending indices for the current page
    start_idx = (page_number - 1) * rows_per_page
    end_idx = start_idx + rows_per_page

    # Display the relevant columns including phone_number and response timestamp
    st.write(f"Displaying rows {start_idx + 1} to {min(end_idx, len(filtered_responses))} of {len(filtered_responses)}")
    filtered_responses.set_index('id', inplace=True)
    st.dataframe(filtered_responses[['phone_number', 'responses', 'location', 'voice_recording_path', 'response_timestamp']].iloc[start_idx:end_idx])

    # Analyze responses for the selected question
    option_counts = analyze_question_responses(selected_question, filtered_responses, survey_questions)

    st.write(f"### Analyzing Question: {selected_question}")
    if option_counts:
        option_df = pd.DataFrame(list(option_counts.items()), columns=['Option', 'Count'])
        bar_chart = px.bar(option_df, x='Option', y='Count', labels={'Option': 'Survey Options', 'Count': 'Number of Responses'})
        st.plotly_chart(bar_chart)
    else:
        st.write("No responses found for this question.")

    # Show location-based analysis
    location_based_analysis(filtered_responses)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<p style="text-align:center;">&copy; Starset Consultancy Services 2024</p>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
