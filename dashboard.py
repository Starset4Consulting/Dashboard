import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import json

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

# Load survey responses along with user phone numbers
def load_survey_responses():
    engine = connect_db()
    query = """
    SELECT sr.id, sr.responses, sr.survey_id, u.phone_number, sr.location, sr.voice_recording_path 
    FROM survey_responses sr
    JOIN users u ON sr.user_id = u.id
    """
    responses = pd.read_sql_query(query, engine)
    return responses

# Function to map responses with correct questions
def map_responses_to_questions(survey_questions, raw_response):
    # Ensure the response is in dictionary format
    if isinstance(raw_response, str):
        response_data = eval(raw_response)
    else:
        response_data = raw_response

    # Correct the numbering mismatch by iterating through the questions
    mapped_responses = {}
    for idx, question in enumerate(survey_questions):
        q_id = str(idx)  # Match the response number with the question index
        if q_id in response_data:
            mapped_responses[question['text']] = response_data[q_id]

    return mapped_responses

# # Function to display the responses table
# def display_responses_table(filtered_responses, survey_questions):
#     st.subheader("Responses Table")
    
#     # Ensure the required columns exist
#     if 'id' not in filtered_responses.columns or 'phone_number' not in filtered_responses.columns:
#         st.error("Required columns 'id' or 'phone_number' are missing in the responses.")
#         return
    
#     # Create a new DataFrame to hold the mapped responses
#     table_data = []
    
#     for index, row in filtered_responses.iterrows():
#         # Map the responses to questions
#         mapped_responses = map_responses_to_questions(survey_questions, row['responses'])
        
#         # Create a dictionary with the user id and responses
#         response_dict = {'Response_id': row['id'], 'Phone Number': row['phone_number']}
#         response_dict.update(mapped_responses)

#         # Append the response data to the table
#         table_data.append(response_dict)
    
#     # Convert the list of dictionaries to a DataFrame
#     responses_df = pd.DataFrame(table_data)
    
#     # Display the DataFrame in a table
#     st.dataframe(responses_df)

# Function to analyze responses for a selected question
def analyze_question_responses(selected_question, filtered_responses, survey_questions):
    option_counts = {}

    # Loop through the filtered responses and analyze the selected question
    for index, row in filtered_responses.iterrows():
        try:
            # Map the responses correctly to the questions
            mapped_responses = map_responses_to_questions(survey_questions, row['responses'])

            # Get the answer for the selected question
            if selected_question in mapped_responses:
                selected_option = mapped_responses[selected_question]

                # Count the occurrences of each answer
                if selected_option in option_counts:
                    option_counts[selected_option] += 1
                else:
                    option_counts[selected_option] = 1
        except Exception as e:
            st.write(f"Error processing response for row {index}: {row['responses']}")
            continue

    return option_counts

# 3. Location-Based Analysis
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

def aggregate_selected_options(filtered_responses):
    option_counts = {}

    # Loop through each row in the filtered responses
    for index, row in filtered_responses.iterrows():
        try:
            # Check if the response is a string, otherwise skip eval
            if isinstance(row['responses'], str):
                responses = eval(row['responses'])  # Assuming the responses are stored as JSON-like strings
            else:
                responses = row['responses']  # If already parsed

            # Go through each response and count the selections
            for key, selected_option in responses.items():
                if selected_option in option_counts:
                    option_counts[selected_option] += 1
                else:
                    option_counts[selected_option] = 1
        except Exception as e:
            st.write(f"Error decoding responses for row {index}: {row['responses']}")
            continue  # Skip the row if there's an error

    return option_counts

# Function to generate the Streamlit dashboard
def main():
    st.set_page_config(page_title="Starset Consultancy Services - Survey Dashboard", layout="wide")

    # Sidebar and logo header
    st.sidebar.image('logo.png', use_column_width=True)  # Add your company logo here
    st.sidebar.title("Starset Consultancy Services")

    st.title("Survey Data Dashboard")
    
    # Load data from the database
    users = load_users()
    surveys = load_surveys()
    responses = load_survey_responses()

    # Create a filter for selecting surveys and users
    survey_filter = st.sidebar.selectbox("Select Survey", surveys['name'].unique())
    
    # Filter the responses based on the selected survey
    filtered_survey_id = surveys[surveys['name'] == survey_filter].iloc[0]['id']
    filtered_responses = responses[responses['survey_id'] == filtered_survey_id]

    # Get the questions for the selected survey
    survey_questions_str = surveys[surveys['name'] == survey_filter].iloc[0]['questions']
    survey_questions_str = survey_questions_str.replace('true', 'True').replace('false', 'False')  # Ensure valid Python booleans
    survey_questions = eval(survey_questions_str)  # Parse the questions from JSON

    # Extract question texts for the dropdown
    question_list = [q['text'] for q in survey_questions]  # Assuming 'text' field holds question text
    selected_question = st.sidebar.selectbox("Select Question to Analyze", question_list)

    # Display user and survey info
    st.write(f"### Showing Responses for Survey: {survey_filter}")
    

    # Parse the responses and display in a table format
    # Safeguard eval() with checks
    filtered_responses['responses'] = filtered_responses['responses'].apply(
        lambda x: eval(x) if isinstance(x, str) else x
    )
    
    # Set response_id as the index for the displayed DataFrame
    filtered_responses.set_index('id', inplace=True)

    # Display the relevant columns including phone_number
    st.dataframe(filtered_responses[['phone_number', 'responses', 'location', 'voice_recording_path']])

    # Analyze responses for the selected question
    option_counts = analyze_question_responses(selected_question, filtered_responses, survey_questions)

    st.write(f"### Analyzing Question: {selected_question}")
    # Display the analysis results
    if option_counts:
        option_df = pd.DataFrame(list(option_counts.items()), columns=['Option', 'Count'])
        
        # Create a bar chart to show the distribution of responses for the selected question
        bar_chart = px.bar(option_df, x='Option', y='Count', 
                           labels={'Option': 'Survey Options', 'Count': 'Number of Responses'})
        st.plotly_chart(bar_chart)
    else:
        st.write("No responses found for this question.")

    # Display the responses table
    # display_responses_table(filtered_responses, survey_questions)

    # Show location-based analysis
    location_based_analysis(filtered_responses)

    # Show footer with copyright information
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align:center;">&copy; Starset Consultancy Services 2024</p>',
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
