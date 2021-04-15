"""
A backend to create plots with matplotlib

Each backend needs to implement the function to_image(plot, format, dpi) and to_html(plot).
"""
import datetime
import io

from matplotlib.figure import Axes, Figure
from matplotlib.ticker import MaxNLocator
from matplotlib import pyplot as plt

import numpy as np
from .plot import Line, Subplot, Plot


def _draw_series(data, ax: Axes, line: Line):
    """
    Draws the line to the matplotlib axis ax
    """
    # Do the plot
    style = dict(color=line.color or 'k',
                 linestyle=line.linestyle, marker=line.marker, linewidth=line.linewidth)
    data.plot.line(**style, ax=ax, label=line.name)


def _draw_subplot(subplot: Subplot, ax: Axes, start: datetime.datetime, end: datetime.datetime):

    data_series = [
        line.load(start, end)
        for line in subplot.lines
    ]
    for line, data in zip(subplot.lines, data_series):
        _draw_series(data, ax, line)

    if subplot.ylim:
        if np.isfinite(subplot.ylim[0]):
            ax.set_ylim(bottom=subplot.ylim[0])
        if np.isfinite(subplot.ylim[1]):
            ax.set_ylim(top=subplot.ylim[1])

    ax.set_ylabel(subplot.ylabel, fontsize=subplot.plot.fontsize(1.2))

    # Show log book entries for the logsite of this subplot
    # Draw only logs if logsite is a site of the subplot's lines
    if subplot.logsite in [l.siteid for l in subplot.lines]:
        # Traverse logs and draw them
        for logtime, logtype, logtext in subplot.get_logs():
            x = np.datetime64(logtime)
            ax.axvline(x, linestyle='-', color='r',
                       alpha=0.5, linewidth=3)
            ax.text(x, ax.get_ylim()[0], logtype,
                    ha='left', va='bottom', fontsize=subplot.plot.fontsize(0.9))

    ax.set_xlim(subplot.plot.start, subplot.plot.end)

    for xtl in ax.get_xticklabels():
        xtl.set_rotation(15)
    ax.yaxis.set_major_locator(MaxNLocator(prune='upper'))
    ax.tick_params(axis='both', which='major', labelsize=subplot.plot.fontsize(1.1))

    ax.grid()
    ax.legend(loc=0, prop=dict(size=subplot.plot.fontsize(1)))


def _draw_plot(plot: Plot) -> Figure:
    """
    Draws the plot and returns the matplotlib.Figure object with the populated figure
    """
    # calc. number of rows with ceiling division (https://stackoverflow.com/a/17511341/3032680)
    rows = -(-len(plot.subplots) // plot.columns)
    size_inch = plot.size[0] / 100.0, plot.size[1] / 100.0
    fig, axes = plt.subplots(ncols=plot.columns, nrows=rows, squeeze=False,
                             figsize=size_inch, dpi=100, sharex='all')
    for sp, ax in zip(plot.subplots, axes.ravel()):
        _draw_subplot(sp, ax, plot.start, plot.end)

    fig.subplots_adjust(top=0.975, bottom=0.1, hspace=0.0)
    return fig


def to_image(plot, format: str, dpi=100) -> bytes:
    """
    Draws the plot and returns a byte string containing the image
    """
    fig = _draw_plot(plot)
    with io.BytesIO() as buffer:
        fig.savefig(buffer, format=format, dpi=dpi)
        plt.close('all')
        buffer.seek(0)
        return buffer.getvalue()


def to_html(plot):
    """
    Draws the plot to include into an html page, here as svg.
    Alternative could be as an <img> element with base64 data
    """
    svg = to_image(plot, 'svg')
    return svg