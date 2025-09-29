
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import io
import datetime
import json
import glob
import os
from utils import (
    parse_staroddi_dat,
    get_time_range,
    parse_winch_dat,
    parse_acc_file
)

# Force wide layout for Streamlit
st.set_page_config(layout="wide")

st.title("Parse Plot and Offset for Staroddi data and Winch Data")

col1, col2 = st.columns([1,2])

with col1:
    with st.expander("Main Data, ACC & Winch Selection", expanded=True):
        import sqlite3
        # Query sensor_data for available cast_ids
        conn = sqlite3.connect('dredge_remote.db')
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT cast_id FROM sensor_data')
        cast_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        selected_cast_id = st.selectbox("Select Cast ID", cast_ids)

        # Query sensor_data for files for selected cast_id
        conn = sqlite3.connect('dredge_remote.db')
        cursor = conn.cursor()
        cursor.execute('SELECT file_name, file_path FROM sensor_data WHERE cast_id=?', (selected_cast_id,))
        files = cursor.fetchall()
        conn.close()

        # Separate .dat and .acc files
        dat_files = [f for f in files if f[0].lower().endswith('.dat')]
        acc_files = [f for f in files if f[0].lower().endswith('.acc')]

        selected_dat_file = st.selectbox("Select .DAT file", [f[0] for f in dat_files]) if dat_files else None
        selected_acc_file = st.selectbox("Select .ACC file", [f[0] for f in acc_files]) if acc_files else None

        df = None
        acc_df = None
        winch_df = None
        winch_meta = None
        selected_winch = None

        # Load selected .DAT file

        if selected_dat_file:
            dat_file_path = next(f[1] for f in dat_files if f[0] == selected_dat_file)
            # If file_path is just 'sensor_data', join with file name
            full_dat_path = os.path.join(dat_file_path, selected_dat_file) if os.path.isdir(dat_file_path) else os.path.join('sensor_data', selected_dat_file)
            if not os.path.isfile(full_dat_path):
                # Try fallback to sensor_data directory
                full_dat_path = os.path.join('sensor_data', selected_dat_file)
            with open(full_dat_path, 'rb') as dat_file:
                df = parse_staroddi_dat(dat_file)
            st.write("Parsed Data Preview:", df.head())
            min_dt, max_dt = get_time_range(df)
            st.write(f"Main file time range: {min_dt} to {max_dt}")

        # Load selected .ACC file
        if selected_acc_file:
            acc_file_path = next(f[1] for f in acc_files if f[0] == selected_acc_file)
            full_acc_path = os.path.join(acc_file_path, selected_acc_file) if os.path.isdir(acc_file_path) else os.path.join('sensor_data', selected_acc_file)
            if not os.path.isfile(full_acc_path):
                full_acc_path = os.path.join('sensor_data', selected_acc_file)
            with open(full_acc_path, 'rb') as acc_file:
                acc_df = parse_acc_file(acc_file)
            st.write("Parsed ACC Data Preview:", acc_df.head())
        # Winch metadata selection logic
        if df is not None:
            min_dt, max_dt = get_time_range(df)
            # Query winch_data table for overlapping winch files
            import sqlite3
            conn = sqlite3.connect('dredge_remote.db')
            cursor = conn.cursor()
            cursor.execute('SELECT file_name, file_path, start_time, end_time, settings FROM winch_data')
            winch_rows = cursor.fetchall()
            conn.close()

            matches = []
            meta_dict = {}
            for row in winch_rows:
                file_name, file_path, start_time, end_time, settings_json = row
                try:
                    winch_start = pd.to_datetime(start_time)
                    winch_end = pd.to_datetime(end_time)
                    # Check for any overlap
                    if (winch_start <= max_dt) and (winch_end >= min_dt):
                        matches.append(file_name)
                        meta = json.loads(settings_json)
                        meta['file_name'] = file_name
                        meta['file_path'] = file_path
                        meta_dict[file_name] = meta
                except Exception:
                    continue
            if matches:
                selected_winches = st.multiselect("Select overlapping winch files:", matches, default=matches)
                winch_dfs = []
                for winch_file in selected_winches:
                    winch_meta = meta_dict[winch_file]
                    winch_dfs.append(parse_winch_dat(winch_file, winch_meta))
                if winch_dfs:
                    winch_df = pd.concat(winch_dfs, ignore_index=True)
                    st.success(f"Loaded {len(selected_winches)} winch file(s), total rows: {len(winch_df)}.")
                else:
                    winch_df = None
            else:
                st.warning("No matching winch files found in database.")

    with st.expander("Plot Controls", expanded=True):
        if df is not None or acc_df is not None:
            plot_dat = df is not None
            plot_acc = acc_df is not None
            if plot_dat:
                df_down = df.iloc[::100]
                y_col = st.selectbox("Main data Y-axis (downsampled)", [c for c in df_down.columns if c not in ["index", "datetime"]])
            if plot_acc:
                acc_down = acc_df.iloc[::100]
                acc_y_col = st.selectbox("ACC data Y-axis (downsampled)", [c for c in acc_down.columns if c not in ["v1", "date", "time", "datetime"]])
            if winch_df is not None:
                winch_down = winch_df.iloc[::100]
                winch_y_col = st.selectbox("Winch data Y-axis (downsampled)", [c for c in winch_down.columns if c not in ["datetime"]])
            else:
                winch_y_col = None
            downsampled_x_offset = st.number_input("Downsampled Plot X Offset (seconds)", value=0.0, step=0.1)

    with st.expander("High-Resolution Controls", expanded=False):
        if df is not None:
            # Select date for start and end
            start_date = st.date_input("Start date", min_dt.date())
            start_time_str = st.text_input("Start time (HH:MM:SS)", value=min_dt.strftime("%H:%M:%S"))
            end_date = st.date_input("End date", max_dt.date())
            end_time_str = st.text_input("End time (HH:MM:SS)", value=max_dt.strftime("%H:%M:%S"))
            try:
                start_time = datetime.datetime.strptime(start_time_str, "%H:%M:%S").time()
            except ValueError:
                start_time = min_dt.time()
            try:
                end_time = datetime.datetime.strptime(end_time_str, "%H:%M:%S").time()
            except ValueError:
                end_time = max_dt.time()
            start_dt = datetime.datetime.combine(start_date, start_time)
            end_dt = datetime.datetime.combine(end_date, end_time)

            highres_x_offset = st.number_input("High-Res Plot X Offset (seconds)", value=0.0, step=0.1, key="highres_offset")
            y_col_highres = st.selectbox("Main data Y-axis (high-res)", [c for c in df.columns if c not in ["index", "datetime"]], key="y_col_highres")
            if acc_df is not None:
                acc_y_col_highres = st.selectbox(
                    "ACC data Y-axis (high-res)",
                    [c for c in acc_df.columns if c not in ["rownum", "datetime"]],
                    key="acc_y_col_highres"
                )
            else:
                acc_y_col_highres = None
            if winch_df is not None:
                winch_y_col_highres = st.selectbox("Winch data Y-axis (high-res)", [c for c in winch_df.columns if c not in ["datetime"]], key="winch_y_col_highres")
            else:
                winch_y_col_highres = None
            if "show_hires" not in st.session_state:
                st.session_state.show_hires = False

            def trigger_highres():
                st.session_state.show_hires = True

            st.button("Show High-Res Plot", on_click=trigger_highres)

with col2:
    # Downsampled plot with its own offset
    if df is not None or acc_df is not None:
        fig = make_subplots(
            rows=3 if (df is not None and acc_df is not None and winch_df is not None) else
                  2 if ((df is not None and acc_df is not None) or (df is not None and winch_df is not None) or (acc_df is not None and winch_df is not None)) else
                  1,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=tuple(
                filter(None, [
                    f"Main Data: {y_col}" if df is not None else None,
                    f"ACC Data: {acc_y_col}" if acc_df is not None else None,
                    f"Winch Data: {winch_y_col}" if winch_df is not None and winch_y_col is not None else None
                ])
            )
        )
        row = 1
        if df is not None:
            df_offset = df.copy()
            df_offset["datetime"] = df_offset["datetime"] + pd.to_timedelta(downsampled_x_offset, unit="s")
            df_down = df_offset.iloc[::100]
            fig.add_trace(
                go.Scatter(x=df_down["datetime"], y=df_down[y_col], name=f"Main: {y_col}", mode="lines"),
                row=row, col=1
            )
            # Invert y-axis if "press" is selected
            if y_col == "press":
                fig.update_yaxes(autorange="reversed", row=row, col=1)
            row += 1
        if acc_df is not None:
            acc_offset = acc_df.copy()
            acc_offset["datetime"] = acc_offset["datetime"] + pd.to_timedelta(downsampled_x_offset, unit="s")
            acc_down = acc_offset.iloc[::100]
            fig.add_trace(
                go.Scatter(x=acc_down["datetime"], y=acc_down[acc_y_col], name=f"ACC: {acc_y_col}", mode="lines"),
                row=row, col=1
            )
            row += 1
        if winch_df is not None and winch_y_col is not None:
            winch_down = winch_df.iloc[::100]
            fig.add_trace(
                go.Scatter(x=winch_down["datetime"], y=winch_down[winch_y_col], name=f"Winch: {winch_y_col}", mode="lines"),
                row=row, col=1
            )
        fig.update_layout(height=600, template="plotly_white", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # High-res plot with its own offset and selectors
        if st.session_state.show_hires:
            df_highres_offset = df.copy()
            df_highres_offset["datetime"] = df_highres_offset["datetime"] + pd.to_timedelta(highres_x_offset, unit="s")
            mask = (df_highres_offset["datetime"] >= start_dt) & (df_highres_offset["datetime"] <= end_dt)
            df_zoom = df_highres_offset.loc[mask]

            # ACC high-res offset and mask
            if acc_df is not None:
                acc_highres_offset = acc_df.copy()
                acc_highres_offset["datetime"] = acc_highres_offset["datetime"] + pd.to_timedelta(highres_x_offset, unit="s")
                mask_acc = (acc_highres_offset["datetime"] >= start_dt) & (acc_highres_offset["datetime"] <= end_dt)
                acc_zoom = acc_highres_offset.loc[mask_acc]
            else:
                acc_zoom = None

            if winch_df is not None and winch_y_col_highres is not None:
                winch_zoom = winch_df[(winch_df["datetime"] >= start_dt) & (winch_df["datetime"] <= end_dt)]
            else:
                winch_zoom = None

            if df_zoom.empty and (acc_zoom is None or acc_zoom.empty):
                st.warning("No data in selected range.")
            else:
                # Count how many plots to show
                n_rows = sum([
                    not df_zoom.empty,
                    acc_zoom is not None and not acc_zoom.empty,
                    winch_zoom is not None and not winch_zoom.empty
                ])
                subplot_titles = []
                if not df_zoom.empty:
                    subplot_titles.append(f"Main Data: {y_col_highres}")
                if acc_zoom is not None and not acc_zoom.empty:
                    subplot_titles.append(f"ACC Data: {acc_y_col_highres}")
                if winch_zoom is not None and not winch_zoom.empty:
                    subplot_titles.append(f"Winch Data: {winch_y_col_highres if winch_y_col_highres else ''}")

                fig2 = make_subplots(rows=n_rows, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                                     subplot_titles=tuple(subplot_titles))
                row = 1
                if not df_zoom.empty:
                    y_data = df_zoom[y_col_highres]
                    fig2.add_trace(go.Scatter(x=df_zoom["datetime"], y=y_data, mode="lines", name=y_col_highres), row=row, col=1)
                    # Set yaxis to inverted if "press"
                    if y_col_highres == "press":
                        fig2.update_yaxes(autorange="reversed", row=row, col=1)
                    row += 1
                if acc_zoom is not None and not acc_zoom.empty:
                    fig2.add_trace(go.Scatter(x=acc_zoom["datetime"], y=acc_zoom[acc_y_col_highres], mode="lines", name=acc_y_col_highres), row=row, col=1)
                    row += 1
                if winch_zoom is not None and not winch_zoom.empty:
                    fig2.add_trace(go.Scatter(x=winch_zoom["datetime"], y=winch_zoom[winch_y_col_highres], mode="lines", name=winch_y_col_highres), row=row, col=1)

                fig2.update_xaxes(showspikes=True, spikemode="across", spikecolor="red", spikesnap="cursor")
                fig2.update_layout(title="High-Res Plot", template="plotly_white", height=600 + 200 * (n_rows-2), showlegend=False,
                                   hovermode="x unified")
                st.plotly_chart(fig2, use_container_width=True)

                # --- Export CSV buttons ---
                st.markdown("### Export high-res subset as CSV")
                df_zoom_export = df.copy()
                mask_export = (df_zoom_export["datetime"] + pd.to_timedelta(highres_x_offset, unit="s") >= start_dt) & \
                              (df_zoom_export["datetime"] + pd.to_timedelta(highres_x_offset, unit="s") <= end_dt)
                df_zoom_export = df_zoom_export.loc[mask_export].copy()
                df_zoom_export["original_datetime"] = df_zoom_export["datetime"]
                df_zoom_export["offset_datetime"] = df_zoom_export["datetime"] + pd.to_timedelta(highres_x_offset, unit="s")
                cols = ["offset_datetime", "original_datetime"] + [c for c in df_zoom_export.columns if c not in ["offset_datetime", "original_datetime"]]
                dat_csv = df_zoom_export[cols].to_csv(index=False)
                st.download_button(
                    label="Download .dat subset CSV",
                    data=dat_csv,
                    file_name="highres_dat_subset.csv",
                    mime="text/csv"
                )
                if acc_zoom is not None and not acc_zoom.empty:
                    acc_zoom_export = acc_df.copy()
                    mask_acc_export = (acc_zoom_export["datetime"] + pd.to_timedelta(highres_x_offset, unit="s") >= start_dt) & \
                                      (acc_zoom_export["datetime"] + pd.to_timedelta(highres_x_offset, unit="s") <= end_dt)
                    acc_zoom_export = acc_zoom_export.loc[mask_acc_export].copy()
                    acc_zoom_export["original_datetime"] = acc_zoom_export["datetime"]
                    acc_zoom_export["offset_datetime"] = acc_zoom_export["datetime"] + pd.to_timedelta(highres_x_offset, unit="s")
                    cols_acc = ["offset_datetime", "original_datetime"] + [c for c in acc_zoom_export.columns if c not in ["offset_datetime", "original_datetime"]]
                    acc_csv = acc_zoom_export[cols_acc].to_csv(index=False)
                    st.download_button(
                        label="Download .acc subset CSV",
                        data=acc_csv,
                        file_name="highres_acc_subset.csv",
                        mime="text/csv"
                    )
                if winch_zoom is not None and not winch_zoom.empty:
                    winch_csv = winch_zoom.to_csv(index=False)
                    st.download_button(
                        label="Download winch subset CSV",
                        data=winch_csv,
                        file_name="highres_winch_subset.csv",
                        mime="text/csv"
                    )