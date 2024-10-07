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
    # Join users and survey_responses on user_id to get phone numbers
    query = """
    SELECT sr.*, u.phone_number 
    FROM survey_responses sr
    JOIN users u ON sr.user_id = u.id
    """
    responses = pd.read_sql_query(query, engine)
    return responses

# Aggregate selected options
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
    filtered_responses = responses[responses['survey_id'] == surveys[surveys['name'] == survey_filter].iloc[0]['id']]

    # Display user and survey info
    st.write(f"### Showing Responses for Survey: {survey_filter}")

    # Parse the responses and display in a table format
    # Safeguard eval() with checks
    filtered_responses['responses'] = filtered_responses['responses'].apply(
        lambda x: eval(x) if isinstance(x, str) else x
    )
    
    # Display the relevant columns including phone_number
    st.dataframe(filtered_responses[['phone_number', 'responses', 'location', 'voice_recording_path']])

    # Aggregate selected options
    option_counts = aggregate_selected_options(filtered_responses)

    # Display option analysis
    if option_counts:
        st.subheader("Survey Option Analysis")
        option_df = pd.DataFrame(list(option_counts.items()), columns=['Option', 'Count'])
        
        # Create a pie chart to show the distribution of responses
        pie_chart = px.pie(option_df, names='Option', values='Count', title="Selected Options Distribution")
        st.plotly_chart(pie_chart)
    else:
        st.write("No valid responses found.")

    # Generate analysis/graphs if location data exists
    if not filtered_responses.empty and 'location' in filtered_responses.columns:
        # Safely handle location values
        locations = filtered_responses['location'].apply(lambda loc: eval(loc) if isinstance(loc, str) and loc != 'Unknown' else None)

        # Filter out None values (in case of missing or "Unknown" locations)
        valid_locations = [loc for loc in locations if loc]

        if valid_locations:
            latitudes = [loc['latitude'] for loc in valid_locations if loc]
            longitudes = [loc['longitude'] for loc in valid_locations if loc]

            # Create a DataFrame for locations
            location_df = pd.DataFrame({
                'latitude': latitudes,
                'longitude': longitudes
            })

            # Plot the locations on a map
            st.subheader("Response Locations")
            fig = px.scatter_mapbox(location_df, lat="latitude", lon="longitude", zoom=5, height=400)
            fig.update_layout(mapbox_style="open-street-map")
            st.plotly_chart(fig)
        else:
            st.write("No valid locations found.")

    # Show footer with copyright information
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align:center;">&copy; Starset Consultancy Services 2024</p>',
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
