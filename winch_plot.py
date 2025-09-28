import os
import pandas as pd
import streamlit as st
import json
import plotly.express as px
import datetime

st.title("Winch Data Parser and Plotter")

# File selection
st.subheader("Select Raw Data File and Metadata File")
raw_file = st.file_uploader("Upload Raw Data File", type=["dat", "csv", "txt"])
meta_file = st.file_uploader("Upload Metadata File", type=["json"])

if raw_file and meta_file:
    try:
        # Load metadata
        meta = json.load(meta_file)
        st.write("Loaded Metadata:", meta)

        # Parse raw data file
        delimiter = meta["delimiter"]
        header_lines = meta["header_lines"]
        columns = meta["columns"]
        datetime_code = meta["datetime_code"]

        # Read the raw file
        raw_file.seek(0)  # Reset file pointer
        df = pd.read_csv(raw_file, delimiter=delimiter, skiprows=header_lines, names=columns)
        st.write("Parsed Data Preview:", df.head())

        # Clean column names
        df.columns = df.columns.str.strip()  # Remove leading/trailing whitespace
        st.write("Cleaned Column Names:", df.columns.tolist())

        # Create datetime column
        try:
            full_datetime_code = f"df['datetime'] = {datetime_code}"
            st.write("Executing Datetime Code:", full_datetime_code)
            exec(full_datetime_code)
            st.write("Data with Datetime Column:", df.head())
        except Exception as e:
            st.error(f"Error creating datetime column: {e}")

        # Downsample the data (e.g., take every 100th row)
        downsampled_df = df.iloc[::100, :]
        st.write("Downsampled Data Preview:", downsampled_df.head())

        # Dropdown for selecting the y-axis
        st.subheader("Plot: Datetime vs Selected Column")
        y_axis_column = st.selectbox("Select Y-Axis Column", options=[col for col in downsampled_df.columns if col != "datetime"])

        # Plot using Plotly (downsampled, zoomable)
        fig = px.line(
            downsampled_df,
            x="datetime",
            y=y_axis_column,
            title=f"Datetime vs {y_axis_column} (Downsampled)",
            labels={"datetime": "Datetime", y_axis_column: y_axis_column},
        )
        fig.update_layout(autosize=True, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

        # --- High-Resolution Region Selection ---
        st.subheader("High-Resolution Plot for Selected Region")
        min_dt = df["datetime"].min()
        max_dt = df["datetime"].max()
        st.write(f"Available datetime range: {min_dt} to {max_dt}")

        # Only show date/time inputs for high-res plot
        with st.form("hires_form"):
            start_date = st.date_input("Start date", min_dt.date())
            start_time = st.time_input("Start time", min_dt.time())
            end_date = st.date_input("End date", max_dt.date())
            end_time = st.time_input("End time", max_dt.time())
            submitted = st.form_submit_button("Show High-Res Plot")

        if submitted:
            start_dt = datetime.datetime.combine(start_date, start_time)
            end_dt = datetime.datetime.combine(end_date, end_time)
            mask = (df["datetime"] >= start_dt) & (df["datetime"] <= end_dt)
            df_zoom = df.loc[mask]
            if df_zoom.empty:
                st.warning("No data in selected range.")
            else:
                fig2 = px.line(
                    df_zoom,
                    x="datetime",
                    y=y_axis_column,
                    title=f"High-Res Datetime vs {y_axis_column}",
                    labels={"datetime": "Datetime", y_axis_column: y_axis_column},
                )
                fig2.update_layout(autosize=True, template="plotly_white")
                st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        st.error(f"Error processing files: {e}")