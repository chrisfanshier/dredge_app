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

# Force wide layout for Streamlit
st.set_page_config(layout="wide")

def parse_staroddi_dat(file):
    # Read all lines with correct encoding
    lines = file.read().decode("latin1").splitlines()
    # Find where data starts (first line starting with a digit)
    data_start = next(i for i, line in enumerate(lines) if line and line[0].isdigit())
    # Set column names (adjust as needed)
    colnames = ["index", "datetime", "temp", "press", "tilt_x", "tilt_y", "tilt_z", "EAL", "roll"]
    # Read data into DataFrame
    df = pd.read_csv(
        io.StringIO('\n'.join(lines[data_start:])),  # <-- add comma here
        sep="\t",
        names=colnames,
        header=None,
        na_values="____",
        decimal=",",
    )
    # Replace comma with dot in numeric columns and in datetime
    df["datetime"] = df["datetime"].str.replace(",", ".", regex=False)
    for col in ["temp", "press", "tilt_x", "tilt_y", "tilt_z", "EAL", "roll"]:
        df[col] = df[col].astype(str).str.replace(",", ".", regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Parse datetime column
    df["datetime"] = pd.to_datetime(df["datetime"], format="%d.%m.%Y %H:%M:%S.%f", errors="coerce")
    return df

def get_time_range(df):
    return df["datetime"].min(), df["datetime"].max()

def parse_winch_dat(file_path, meta):
    colnames = meta["columns"]
    delimiter = meta["delimiter"]
    header_lines = meta["header_lines"]
    df = pd.read_csv(
        os.path.join(meta["file_path"], meta["file_name"]),
        delimiter=delimiter,
        skiprows=header_lines,
        names=colnames,
        header=None,
        na_values="____"
    )
    # Create datetime column
    df["datetime"] = pd.to_datetime(df[['year', 'month', 'day', 'hour', 'minute', 'second']])
    return df

def parse_acc_file(file):
    lines = file.read().decode("latin1").splitlines()
    # Find where data starts (first line starting with a digit)
    data_start = next(i for i, line in enumerate(lines) if line and line[0].isdigit())
    # The actual data columns (based on your sample)
    colnames = ["rownum", "datetime", "g", "x_acc", "y_acc", "z_acc"]
    # Read the data
    df = pd.read_csv(
        io.StringIO('\n'.join(lines[data_start:])),
        sep="\t",
        names=colnames,
        header=None,
        na_values="____"
    )
    # Fix the datetime: replace comma with dot for milliseconds
    df["datetime"] = df["datetime"].astype(str).str.replace(",", ".", regex=False)
    df["datetime"] = pd.to_datetime(df["datetime"], format="%d.%m.%Y %H:%M:%S.%f", errors="coerce")
    # Replace comma with dot in all numeric columns and convert
    for col in ["g", "x_acc", "y_acc", "z_acc"]:
        df[col] = df[col].astype(str).str.replace(",", ".", regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

st.title("Parse Plot and Offset for Staroddi data and Winch Data")

col1, col2 = st.columns([1,2])

with col1:
    with st.expander("Main Data, ACC & Winch Selection", expanded=True):
        dat_file = st.file_uploader("Select a .dat file", type=["dat"])
        acc_file = st.file_uploader("Select an .acc file", type=["acc"])
        df = None
        acc_df = None
        winch_df = None
        winch_meta = None
        selected_winch = None
        if dat_file:
            df = parse_staroddi_dat(dat_file)
            st.write("Parsed Data Preview:", df.head())
            min_dt, max_dt = get_time_range(df)
            st.write(f"Main file time range: {min_dt} to {max_dt}")
        if acc_file:
            acc_df = parse_acc_file(acc_file)
            st.write("Parsed ACC Data Preview:", acc_df.head())
        # Winch metadata selection logic
        if df is not None:
            min_dt, max_dt = get_time_range(df)
            meta_folder = st.text_input("Winch metadata folder (JSONs):", value="./winch_metadata")
            if meta_folder and os.path.isdir(meta_folder):
                meta_files = glob.glob(os.path.join(meta_folder, "*.json"))
                matches = []
                meta_dict = {}
                for meta_path in meta_files:
                    with open(meta_path, "r") as f:
                        meta = json.load(f)
                    try:
                        winch_start = pd.to_datetime(meta["start_datetime"])
                        winch_end = pd.to_datetime(meta["end_datetime"])
                        # Check for any overlap
                        if (winch_start <= max_dt) and (winch_end >= min_dt):
                            matches.append(meta["file_name"])
                            meta_dict[meta["file_name"]] = meta
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
                    st.warning("No matching winch files found in metadata folder.")
            else:
                st.info("Enter a valid folder path containing winch JSON metadata files.")

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