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
        linestyle = {'color': line.color, 'dash': dash_dict[line.linestyle], 'width': line.linewidth}
    if line.marker:
        mode = 'lines+markers' if mode else 'markers'
        symboldict = {'o': 'circle', 'x': 'x-thin', ',': 'line-ns', '+': 'cross-thin', '*': 'asterisk', '.':  'circle'}
        if line.marker in symbols:
            symbol = line.marker
        else:
            symbol = symboldict.get(line.marker, 'circle')

        marker = {'color': line.color, 'symbol': symbol}

    return go.Scatter(x=data.index, y=data, mode=mode, line=linestyle, marker=marker, name=line.name)


def _make_figure(plot: Plot) -> go.Figure:
    rows = -(-len(plot.subplots) // plot.columns)
    fig = make_subplots(rows, plot.columns, shared_xaxes=True)
    subplot_positions = sum(([i] * len(sp.lines) for i, sp in enumerate(plot.subplots)), [])
    rows = [1 + i // plot.columns for i in subplot_positions]
    cols = [1 + i % plot.columns for i in subplot_positions]
    for i, sp in enumerate(plot.subplots):
        row, col = 1 + i // plot.columns, 1 + i % plot.columns
        if sp.ylim:
            fig.update_yaxes(range=list(sp.ylim), row=row, col=col)

    fig.update_yaxes()
    fig.add_traces(
        [
            _draw_line(l, plot.start, plot.end)
            for l in plot.lines()
        ],
        rows=rows,
        cols=cols
    )

    fig.update_yaxes()
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
    return fig.to_html(include_plotlyjs='cdn').encode('utf-8')


symbols = [
    "circle", "circle-open", "circle-dot", "circle-open-dot",
    "square", "square-open", "square-dot", "square-open-dot",
    "diamond", "diamond-open", "diamond-dot", "diamond-open-dot",
    "cross", "cross-open", "cross-dot", "cross-open-dot", "x",
    "x-open", "x-dot", "x-open-dot", "triangle-up",
    "triangle-up-open", "triangle-up-dot", "triangle-up-open-dot",
    "triangle-down", "triangle-down-open", "triangle-down-dot",
    "triangle-down-open-dot", "triangle-left", "triangle-left-open",
    "triangle-left-dot", "triangle-left-open-dot", "triangle-right",
    "triangle-right-open", "triangle-right-dot", "triangle-right-open-dot",
    "triangle-ne", "triangle-ne-open", "triangle-ne-dot",
    "triangle-ne-open-dot", "triangle-se", "triangle-se-open",
    "triangle-se-dot", "triangle-se-open-dot", "triangle-sw", "triangle-sw-open", "triangle-sw-dot", "triangle-sw-open-dot" ,
    "triangle-nw", "triangle-nw-open", "triangle-nw-dot" ,
    "triangle-nw-open-dot", "pentagon", "pentagon-open", "pentagon-dot",
    "pentagon-open-dot", "hexagon", "hexagon-open", "hexagon-dot", "hexagon-open-dot", "hexagon2", "hexagon2-open", "hexagon2-dot", "hexagon2-open-dot", "octagon", "octagon-open",
    "octagon-dot", "octagon-open-dot", "star", "star-open",
    "star-dot", "star-open-dot", "hexagram", "hexagram-open",
    "hexagram-dot", "hexagram-open-dot", "star-triangle-up", "star-triangle-up-open", "star-triangle-up-dot", "star-triangle-up-open-dot" ,
    "star-triangle-down", "star-triangle-down-open", "star-triangle-down-dot",
    "star-triangle-down-open-dot", "star-square", "star-square-open", "star-square-dot", "star-square-open-dot", "star-diamond" ,
    "star-diamond-open", "star-diamond-dot", "star-diamond-open-dot" ,
    "diamond-tall", "diamond-tall-open", "diamond-tall-dot" ,
    "diamond-tall-open-dot", "diamond-wide", "diamond-wide-open" ,
    "diamond-wide-dot", "diamond-wide-open-dot", "hourglass" ,
    "hourglass-open", "bowtie", "bowtie-open", "circle-cross" ,
    "circle-cross-open", "circle-x", "circle-x-open", "square-cross" ,
    "square-cross-open", "square-x", "square-x-open", "diamond-cross",
    "diamond-cross-open", "diamond-x", "diamond-x-open",
    "cross-thin", "cross-thin-open", "x-thin", "x-thin-open",
    "asterisk", "asterisk-open", "hash", "hash-open",
    "hash-dot", "hash-open-dot", "y-up", "y-up-open", "y-down",
    "y-down-open", "y-left", "y-left-open", "y-right", "y-right-open", "line-ew", "line-ew-open", "line-ns", "line-ns-open", "line-ne", "line-ne-open", "line-nw" ,
    "line-nw-open", "arrow-up", "arrow-up-open", "arrow-down" ,
    "arrow-down-open", "arrow-left", "arrow-left-open", "arrow-right" ,
    "arrow-right-open", "arrow-bar-up", "arrow-bar-up-open" ,
    "arrow-bar-down", "arrow-bar-down-open", "arrow-bar-left" ,
    "arrow-bar-left-open", "arrow-bar-right", "arrow-bar-right-open"
]
