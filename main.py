import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from st_files_connection import FilesConnection
from pystac_client import Client
from odc.stac import load
import hmac

def check_password():
    def login_form():
        with st.form("credentials"):
            st.text_input("Username" ,key ="username")
            st.text_input("Password", type="password",key="password")
            st.form_submit_button("Login", on_click=password_entered)
    def password_entered():
        if st.session_state["username"] in st.secrets["passwords"] and hmac.compare_digest(
            st.session_state["password"],
            st.secrets.passwords[st.session_state["username"]]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False
    if st.session_state.get("password_correct", False):  ### the user is logged in.
        return True
    login_form()    #### If the user is not logged in, displays the login form.
    if "password_correct" in st.session_state:
        st.error("😕 User not known or password incorrect")
    return False
if not check_password():
    st.stop()

### Main app start here
st.write("Welcome to satelite visualization app by streamlit ")
st.title("Satelite Map Portal")
st.markdown("Enter the data below")
if 'date_labels' not in st.session_state:
    st.session_state.date_labels = []
if 'data' not in st.session_state:
    st.session_state.data = None
if 'user_date' not in st.session_state:
    st.session_state.user_date = None
if 'user_date_index' not in st.session_state:
    st.session_state.user_date_index = 0
collections = ["sentinel-2-12a"]
columns = ['collections' , 'start_date' ,'end_date', 'min_cloud_cover','max_cloud_cover','longitude','laltitude','buffer']

with st.form(key="test"):
    collection =st.selectbox("collection*",options=collections,index=None)
    stsrt_date = st.date_input(label="start_date*")
    end_date = st.date_input(label="end_date")
    max_cloud_cover = st.number_input(label="max_cloud_cover",value=10)
    longitude = st.number_input(label="longitude*",format="%.4f",value=-119.7513)
    latitude = st.number_input(label="latitude*",format="%.4f",value=37.2502)
    buffer = st.number_input(label="buffer (0.01 = 1 km)*",format="%.2f",value=0.01)
    st.markdown("**required*")

    submit_button_run = st.form_submit_button(label="Run")
    submit_button_list = st.form_submit_button(label="List Available Images")
    submit_button_viz = st.form_submit_button(label="Visualize")






