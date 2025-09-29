import os
import json
import pandas as pd
import streamlit as st
import sqlite3

def w_import():
    SAVE_DIR = "winch_data"
    os.makedirs(SAVE_DIR, exist_ok=True)

    st.title("Winch File Ingestion")

    uploaded_file = st.file_uploader("Upload Winch File")  # accept any extension
    cruise_name = st.text_input("Cruise Name")

    if uploaded_file is not None:
        # Number of header lines to skip
        header_lines = st.number_input("Number of header lines to skip", min_value=0, value=0, step=1)

        # Select delimiter
        delimiter_options = [
            ("Comma (,)", ","),
            ("Tab (\\t)", "\t"),
            ("Pipe (|)", "|"),
            ("Space ( )", " "),
            ("Semicolon (;)", ";"),
            ("Whitespace (\\s+)", r"\s+")
        ]
        delimiter_label = st.selectbox("Select Delimiter", [label for label, _ in delimiter_options])
        delimiter = next(value for label, value in delimiter_options if label == delimiter_label)

        # Custom delimiter
        custom_delim = st.text_input("Custom delimiter (optional)", "")
        if custom_delim:
            delimiter = custom_delim

        # Preview raw
        uploaded_file.seek(0)
        df_preview = pd.read_csv(uploaded_file, delimiter=delimiter, skiprows=header_lines, nrows=20, header=None)
        st.write("Raw Preview (first 20 rows):", df_preview)

        # Column renaming
        st.subheader("Rename Columns")
        colnames_input = st.text_area(
            "Enter column names as a Python list (e.g., ['year', 'month', 'day', ...])",
            value="[]"
        )
        try:
            colnames = eval(colnames_input)  # Convert string input to a Python list
            if len(colnames) != len(df_preview.columns):
                st.warning("The number of column names does not match the number of columns in the file.")
            else:
                df_preview.columns = colnames
                st.write("Preview with renamed columns:", df_preview)
        except Exception as e:
            st.error(f"Error parsing column names: {e}")

        # Datetime column creation
        st.subheader("Create Datetime Column")
        st.markdown(
            "Use the DataFrame `df` in your code. For example:\n"
            "`pd.to_datetime(df[['year', 'month', 'day', 'hour', 'minute', 'second']])`"
        )
        datetime_code = st.text_area(
            "Enter the Python code for creating the datetime column",
            value="pd.to_datetime(df[['year', 'month', 'day', 'hour', 'minute', 'second']])"
        )

        try:
            if datetime_code.strip():
                # Read the entire dataset
                uploaded_file.seek(0)  # Reset file pointer
                df = pd.read_csv(uploaded_file, delimiter=delimiter, skiprows=header_lines, names=colnames)

                # Validate and execute the user-provided code
                exec(f"df['datetime'] = {datetime_code}")
                st.write("Preview with datetime column (first 20 rows):", df.head())

                # Calculate start and end datetimes for the full dataset
                start_datetime = df['datetime'].min()
                end_datetime = df['datetime'].max()
                st.write(f"Start Datetime: {start_datetime}")
                st.write(f"End Datetime: {end_datetime}")
            else:
                start_datetime = None
                end_datetime = None
        except Exception as e:
            st.error(f"Error creating datetime column: {e}")
            start_datetime = None
            end_datetime = None

        # Save file + metadata
        if st.button("Ingest File"):
            file_path = os.path.join(SAVE_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Prepare settings as JSON string
            settings = json.dumps({
                "delimiter": delimiter,
                "header_lines": header_lines,
                "columns": colnames,
                "datetime_code": datetime_code
            })

            # Insert metadata into winch_data table
            conn = sqlite3.connect("dredge_remote.db")
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO winch_data (
                    file_name, file_path, cruise, start_time, end_time, settings
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                uploaded_file.name,
                SAVE_DIR,
                cruise_name,
                str(start_datetime),
                str(end_datetime),
                settings
            ))
            conn.commit()
            conn.close()

            st.success(f"File and metadata saved!\n- {file_path}\n- Database entry created.")
