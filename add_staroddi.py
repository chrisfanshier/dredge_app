import streamlit as st
import sqlite3
import os

st.title("Star-Oddi File Ingestion")

uploaded_file = st.file_uploader("Select Star-Oddi file", key="staroddi_file")
cruise = st.text_input("Enter cruise")
cast_id = st.text_input("Enter cast_id")

if st.button("Upload and Save"):
    if uploaded_file and cruise and cast_id:
        # Save file
        file_path = os.path.join("sensor_data", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())


        # Add record to SQLite database
        conn = sqlite3.connect("dredge_remote.db")
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sensor_data (file_path, file_name, cruise, cast_id)
            VALUES (?, ?, ?, ?)
        ''', (file_path, uploaded_file.name, cruise, cast_id))
        conn.commit()
        conn.close()

        st.success("File uploaded and record added to database.")
    else:
        st.error("Please select a file and enter cruise and cast_id.")


