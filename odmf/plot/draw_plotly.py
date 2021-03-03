"""
A stub for a plotting backend producing interactive plots with plotly

Each backend needs to implement the function to_image(plot, format, dpi) and to_html(plot).
"""

from plotly.subplots import make_subplots
import plotly.graph_objects as go
import io
from . import Plot, Line
from ..config import conf

def _draw_line(line: Line, start, end) -> go.Scatter:

    data = line.load(start, end)
    mode = ''
    linestyle = None
    marker = None
    if line.linestyle:
        mode = 'lines'
        dash_dict = {'-': 'solid', ':': 'dot', '.': 'dot', '--': 'dash', '-.': 'dashdot'}
        linestyle = {'color': line.color, 'dash': dash_dict[line.linestyle]}
    if line.marker:
        mode = 'lines+markers' if mode else 'markers'
        marker = {'color': line.color, 'symbol': line.marker}

    return go.Scatter(x=data.index, y=data, mode=mode, line=linestyle, marker=marker, name=line.name)


def _make_figure(plot: Plot) -> go.Figure:
    rows = -(-len(plot.subplots) // plot.columns)
    fig = make_subplots(rows, plot.columns, shared_xaxes=True)
    subplot_positions = sum(([i] * len(sp.lines) for i, sp in enumerate(plot.subplots)), [])
    rows = [1 + i // plot.columns for i in subplot_positions]
    cols = [1 + i % plot.columns for i in subplot_positions]
    fig.add_traces(
        [
            _draw_line(l, plot.start, plot.end)
            for l in plot.lines()
        ],
        rows=rows,
        cols=cols
    )
    fig.update_layout(width=plot.size[0], height=plot.size[1], template='none')
    return fig


def to_image(plot: Plot, format: str) -> bytes:
    """
    Draws the plot and returns a byte string containing the image
    """
    fig = _make_figure(plot)
    return fig.to_image(format=format)


def to_html(plot: Plot)->bytes:
    """
    Draws the plot to include into an html page, here as svg.
    Alternative could be as an <img> element with base64 data
    """
    fig = _make_figure(plot)
    return fig.to_html(include_plotlyjs=conf.root_url + '/media/lib/plotly.min.js').encode('utf-8')
