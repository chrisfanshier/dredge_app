from dash import Dash, dcc, html, Input, Output, State
from plotly_resampler import FigureResampler, register_plotly_resampler
import plotly.graph_objects as go
import pandas as pd
import json
import io
import base64

app = Dash(__name__)

uploaded_data = None
uploaded_metadata = None

app.layout = html.Div([
    html.H1("Dash App: File Upload and Dynamic Plotting"),
    html.Div([
        html.Label("Upload Data File:"),
        dcc.Upload(id="upload-data", children=html.Button("Upload Data File"), multiple=False),
        html.Label("Upload Metadata File:"),
        dcc.Upload(id="upload-metadata", children=html.Button("Upload Metadata File"), multiple=False, disabled=True),
    ]),
    html.Div([
        html.Label("Select Y-Axis Variable:"),
        dcc.Dropdown(id="y-axis-dropdown", placeholder="Select a variable"),
    ]),
    dcc.Graph(id="plot"),
])

register_plotly_resampler(app)

@app.callback(
    Output("upload-metadata", "disabled"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
)
def handle_data_upload(data_contents, data_filename):
    global uploaded_data
    if data_contents:
        content_type, content_string = data_contents.split(",")
        decoded = base64.b64decode(content_string)
        uploaded_data = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
        return False
    return True

@app.callback(
    Output("y-axis-dropdown", "options"),
    Input("upload-metadata", "contents"),
    State("upload-metadata", "filename"),
)
def handle_metadata_upload(metadata_contents, metadata_filename):
    global uploaded_metadata, uploaded_data
    if metadata_contents and uploaded_data is not None:
        content_type, content_string = metadata_contents.split(",")
        decoded = base64.b64decode(content_string)
        uploaded_metadata = json.loads(decoded.decode("utf-8"))
        delimiter = uploaded_metadata["delimiter"]
        header_lines = uploaded_metadata["header_lines"]
        columns = uploaded_metadata["columns"]
        datetime_code = uploaded_metadata["datetime_code"]
        uploaded_data = pd.read_csv(
            io.StringIO(uploaded_data.to_csv(index=False)),
            delimiter=delimiter,
            skiprows=header_lines,
            names=columns
        )
        datetime_code = datetime_code.replace("df", "uploaded_data")
        uploaded_data["datetime"] = eval(datetime_code)
        return [{"label": col, "value": col} for col in uploaded_data.columns if col != "datetime"]
    return []

@app.callback(
    Output("plot", "figure"),
    Input("y-axis-dropdown", "value"),
)
def update_plot(y_axis_column):
    if uploaded_data is not None and y_axis_column:
        fig = FigureResampler(go.Figure())
        fig.add_trace(
            go.Scattergl(name=y_axis_column),
            hf_x=uploaded_data["datetime"],
            hf_y=uploaded_data[y_axis_column],
        )
        return fig  # Return the FigureResampler object directly
    return go.Figure()

if __name__ == "__main__":
    app.run(debug=True)