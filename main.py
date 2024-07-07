import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from st_files_connection import FilesConnection
from pystac_client import Client
from odc.stac import load
import hmac
from pyproj import CRS

# def check_password():
#     """Returns `True` if the user had a correct password."""

#     def login_form():
#         """Form with widgets to collect user information"""
#         with st.form("Credentials"):
#             st.text_input("Username", key="username")
#             st.text_input("Password", type="password", key="password")
#             st.form_submit_button("Log in", on_click=password_entered)

#     def password_entered():
#         """Checks whether a password entered by the user is correct."""
#         if st.session_state["username"] in st.secrets[
#             "passwords"
#         ] and hmac.compare_digest(
#             st.session_state["password"],
#             st.secrets.passwords[st.session_state["username"]],
#         ):
#             st.session_state["password_correct"] = True
#             del st.session_state["password"]  # Don't store the username or password.
#             del st.session_state["username"]
#         else:
#             st.session_state["password_correct"] = False

#     # Return True if the username + password is validated.
#     if st.session_state.get("password_correct", False):
#         return True

#     # Show inputs for username + password.
#     login_form()
#     if "password_correct" in st.session_state:
#         st.error("😕 User not known or password incorrect")
#     return False

# if not check_password():
#     st.stop()
# Main Streamlit app starts here

# Load custom CSS
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Main Streamlit app starts here
st.set_page_config(page_title="Satellite Visualization App", layout="wide")

# Load the CSS file
load_css("styles.css")

# st.write("Welcome to Satellite Visualization App by Streamlit")

# Display Title
st.title("Satellite Map Portal")
st.markdown("Enter the data below.")

# Initialize session state for date_labels and user_date
if 'date_labels' not in st.session_state:
    st.session_state.date_labels = []

if 'data' not in st.session_state:
    st.session_state.data = None

if 'user_date' not in st.session_state:
    st.session_state.user_date = None

if 'user_date_index' not in st.session_state:
    st.session_state.user_date_index = 0

collections = ["sentinel-2-l2a"]
columns = ['collection', 'start_date', 'end_date', 'min_cloud_cover', 'max_cloud_cover', 'longitude', 'latitude', 'buffer']

# Create an empty DataFrame with these columns
df = pd.DataFrame(columns=columns)

if "mdf" not in st.session_state:
    st.session_state.mdf = pd.DataFrame(columns=df.columns)

# New Data
with st.form(key="test"):
    collection = st.selectbox("collection*", options=collections, index=None)
    start_date = st.date_input(label="start_date*")
    end_date = st.date_input(label="end_date*")
    max_cloud_cover = st.number_input(label="max_cloud_cover*", value=10)
    longitude = st.number_input(label="longitude*", format="%.4f", value=-119.7513)
    latitude = st.number_input(label="latitude*", format="%.4f", value=37.2502)
    buffer = st.number_input(label="buffer (0.01 = 1 km)*", format="%.2f", value=0.01)

    # Mark Mandatory fields
    st.markdown("**required*")

    submit_button_run = st.form_submit_button(label="Run")
    submit_button_list = st.form_submit_button(label="List Available Images")
    submit_button_viz = st.form_submit_button(label="Visualize")

def search_satellite_images(collection="sentinel-2-l2a",
                            bbox=[-120.15, 38.93, -119.88, 39.25],
                            date="2023-06-01/2023-06-30",
                            cloud_cover=(0, 10)):
    try:
        # Debugging statement to check collection
        st.write(f"Searching collection: {collection}")

        # Define the search client
        client = Client.open("https://earth-search.aws.element84.com/v1")
        search = client.search(collections=[collection],
                               bbox=bbox,
                               datetime=date,
                               query=[f"eo:cloud_cover<{cloud_cover[1]}", f"eo:cloud_cover>{cloud_cover[0]}"])

        # Print the number of matched items
        st.write(f"Number of images found: {search.matched()}")

        items = list(search.items())
        if not items:
            st.write("No items found.")
            return None

        # Extract CRS from the first item (adjust as per your metadata)
        item = items[0]
        crs = CRS.from_epsg(32610)  # Example: UTM Zone 10N

        # Define resolution as a single numeric value (e.g., 10 meters per pixel)
        resolution = 10

        # Load data using odc.stac with defined CRS and resolution
        data = load(items, bbox=bbox, crs=crs, resolution=resolution, groupby="solar_day", chunks={})

        st.write(f"Number of days in data: {len(data.time)}")

        return data

    except Exception as e:
        st.error(f"Error during search: {e}")
        return None

def get_bbox_with_buffer(latitude=37.2502, longitude=-119.7513, buffer=0.01):
    min_lat = latitude - buffer
    max_lat = latitude + buffer
    min_lon = longitude - buffer
    max_lon = longitude + buffer

    bbox = [min_lon, min_lat, max_lon, max_lat]
    return bbox

if submit_button_run:
    new_df = pd.DataFrame(
        [
            {
                "collection": collection,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "max_cloud_cover": max_cloud_cover,
                "longitude": longitude,
                "latitude": latitude,
                "buffer": buffer,
            }
        ]
    )
    
    if st.session_state.mdf.empty:
        st.session_state.mdf = new_df
    else:
        st.session_state.mdf = pd.concat([st.session_state.mdf, new_df], axis=0, ignore_index=True)

    st.dataframe(st.session_state.mdf)
    st.success("Your request successfully submitted!")

    data = search_satellite_images(collection=collection,
                                   date=f"{start_date}/{end_date}",
                                   cloud_cover=(0, max_cloud_cover),
                                   bbox=get_bbox_with_buffer(latitude=latitude, longitude=longitude, buffer=buffer))
    st.session_state.data = data

    if data is not None:
        date_labels = []
        # Determine the number of time steps
        numb_days = len(data.time)
        # Iterate through each time step
        for t in range(numb_days):
            scl_image = data[["scl"]].isel(time=t).to_array()
            dt = pd.to_datetime(scl_image.time.values)
            year = dt.year
            month = dt.month
            day = dt.day
            date_string = f"{year}-{month:02d}-{day:02d}"
            date_labels.append(date_string)
        
        st.session_state.date_labels = date_labels

if submit_button_list:
    user_date = st.selectbox("Available Images*", options=st.session_state.date_labels, index=None)
    if user_date:
        st.session_state.user_date = user_date
        st.session_state.user_date_index = user_date.index()

def count_classified_pixels(data, num):
    scl_image = data[["scl"]].isel(time=num).to_array()

    # Count the classified pixels 
    count_saturated = np.count_nonzero(scl_image == 1)        # Saturated or defective
    count_dark = np.count_nonzero(scl_image == 2)             # Dark Area Pixels
    count_cloud_shadow = np.count_nonzero(scl_image == 3)     # Cloud Shadows
    count_vegetation = np.count_nonzero(scl_image == 4)       # Vegetation
    count_soil = np.count_nonzero(scl_image == 5)             # Bare Soils
    count_water = np.count_nonzero(scl_image == 6)            # Water
    count_clouds_low = np.count_nonzero(scl_image == 7)       # Clouds Low Probability / Unclassified
    count_clouds_med = np.count_nonzero(scl_image == 8)       # Clouds Medium Probability
    count_clouds_high = np.count_nonzero(scl_image == 9)      # Clouds High Probability
    count_clouds_cirrus = np.count_nonzero(scl_image == 10)   # Cirrus
    count_clouds_snow = np.count_nonzero(scl_image == 11)     # Snow

    counts = {
        'Dark/Bright': count_cloud_shadow + count_dark + count_clouds_low + count_clouds_med + count_clouds_high + count_clouds_cirrus + count_clouds_snow + count_saturated,
        'Vegetation': count_vegetation,
        'Bare Soil': count_soil,
        'Water': count_water,
    }

    return counts

if submit_button_viz:
    if st.session_state.data is None:
        st.error("No data loaded. Please run the search first.")
    elif st.session_state.user_date_index is None:
        st.error("No date selected or invalid index.")
    else:
        try:
            # Check if user_date_index is within valid range
            if st.session_state.user_date_index < 0 or st.session_state.user_date_index >= len(st.session_state.data.time):
                st.error("Invalid date index.")
            else:
                date_string_title = "Sentinel-2 Image over AOI"
                fig, axs = plt.subplots(nrows=1, ncols=2, figsize=(16, 8))

                rgb = st.session_state.data[["red", "green", "blue"]].isel(time=st.session_state.user_date_index).to_array()
                rgb.plot.imshow(robust=True, ax=axs[0])
                axs[0].axis('off')  # Hide the axes ticks and labels
                axs[0].set_title(date_string_title)

                # Preparing data for pie chart
                counts = count_classified_pixels(st.session_state.data, st.session_state.user_date_index)
                labels = list(counts.keys())
                values = list(counts.values())
                colors = ['DarkGrey', 'chartreuse', 'DarkOrange', 'cyan']
                explode = (0.3, 0.1, 0.1, 0.1)  # Exploding the first slice

                # Plotting the pie chart
                axs[1].pie(values, labels=labels, colors=colors, autopct='%1.0f%%', startangle=140, explode=explode)
                axs[1].legend(labels, loc='best', bbox_to_anchor=(1, 0.5))
                axs[1].axis('equal')  # Ensure the pie chart is a circle
                axs[1].set_title('Distribution of Classes')

                # Display the figure in Streamlit
                st.pyplot(fig)

        except Exception as e:
            st.error(f"Error during visualization: {e}")
