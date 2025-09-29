import pandas as pd
import io
import os
import json

def parse_staroddi_dat(file):
    lines = file.read().decode("latin1").splitlines()
    data_start = next(i for i, line in enumerate(lines) if line and line[0].isdigit())
    colnames = ["index", "datetime", "temp", "press", "tilt_x", "tilt_y", "tilt_z", "EAL", "roll"]
    df = pd.read_csv(
        io.StringIO('\n'.join(lines[data_start:])),
        sep="\t",
        names=colnames,
        header=None,
        na_values="____",
        decimal=",",
    )
    df["datetime"] = df["datetime"].str.replace(",", ".", regex=False)
    for col in ["temp", "press", "tilt_x", "tilt_y", "tilt_z", "EAL", "roll"]:
        df[col] = df[col].astype(str).str.replace(",", ".", regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce")
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
    df["datetime"] = pd.to_datetime(df[['year', 'month', 'day', 'hour', 'minute', 'second']])
    return df

def parse_acc_file(file):
    lines = file.read().decode("latin1").splitlines()
    data_start = next(i for i, line in enumerate(lines) if line and line[0].isdigit())
    colnames = ["rownum", "datetime", "g", "x_acc", "y_acc", "z_acc"]
    df = pd.read_csv(
        io.StringIO('\n'.join(lines[data_start:])),
        sep="\t",
        names=colnames,
        header=None,
        na_values="____"
    )
    df["datetime"] = df["datetime"].astype(str).str.replace(",", ".", regex=False)
    df["datetime"] = pd.to_datetime(df["datetime"], format="%d.%m.%Y %H:%M:%S.%f", errors="coerce")
    for col in ["g", "x_acc", "y_acc", "z_acc"]:
        df[col] = df[col].astype(str).str.replace(",", ".", regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
