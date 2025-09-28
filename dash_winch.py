from dash import Dash, dcc, html
from plotly_resampler import FigureResampler, register_plotly_resampler
import plotly.graph_objects as go
import pandas as pd
import numpy as np

N = 2_000_000
df = pd.DataFrame({
    "t": pd.date_range("2020-01-01", periods=N, freq="s"),
    "y": np.sin(np.linspace(0, 1000, N))
})

app = Dash(__name__)

fig = FigureResampler(go.Figure())
fig.add_trace(go.Scattergl(name="signal"), hf_x=df["t"], hf_y=df["y"])

app.layout = html.Div([
    html.H1("Dynamic downsampling demo"),
    dcc.Graph(id="plot", figure=fig)
])

register_plotly_resampler(app)

if __name__ == "__main__":
    app.run(debug=True)