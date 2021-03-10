"""
Created on 01.10.2012

@author: philkraf
"""

import sys

import matplotlib.figure
import numpy as np
import pandas as pd

from cherrypy.lib.static import serve_fileobj
from logging import getLogger

from datetime import datetime
import io
import json
from ..tools import Path as OPath
from ..plot import Plot
from .markdown import MarkDown
from .. import db
from . import lib as web
from .auth import group, expose_for, users

# Try to use plotly, if not available use matplotlib
try:
    from ..plot import draw_plotly as plot_backend
except ImportError:
    from ..plot import draw_mpl as plot_backend
nan = np.nan

logger = getLogger(__name__)

if sys.platform == 'win32':
    matplotlib.rc('font', **{'sans-serif': 'Arial',
                             'family': 'sans-serif'})

markdown = MarkDown()



class PlotError(web.HTTPError):

    def __init__(self, message: str):
        self.message = message
        super().__init__(400, 'odmf-plot: Plot object is malformed, error: ' + message)

    def get_error_page(self, *args, **kwargs):
        from .lib import render
        error = '## Plot object incorrect\n\n' + self.message
        return render('plot.html', plot=None, error=error).render().encode('utf-8')


plotgroup = group.logger



class PlotFileDialog:
    """
    Handles the file dialog of the plot page
    """
    exposed = True

    @expose_for(plotgroup)
    @web.method.get
    def index(self, path=None):
        """
        Shows the file dialog

        Parameters
        ----------
        path
            The path to show, if None defaults to $USER

        """
        p = OPath(path or web.user())
        if not p.islegal():
            raise web.HTTPError(403, 'No access to ' + path)
        if not p.exists():
            p = OPath('.')
        directories, files = p.listdir()
        files = [f for f in files if f.basename.endswith('.plot')]
        res = web.render(
            'plot/filedialog.html',
            path=p,
            directories=directories,
            files=files
        ).render()
        return res

    @expose_for(plotgroup)
    @web.method.post
    def save(self, plot, path):
        """
        Saves a plot object to the given filename

        Usage: $.post('saveplot', {plot: JSON.stringify(window.plot, path: ${path}).fail(seterror);
        """
        if not path:
            path = web.user()
        p = OPath(path)
        if not p.islegal() or not p.parent().exists:
            raise web.HTTPError(403, 'No access to ' + path)
        with open(p.absolute, 'w') as f:
            f.write(plot)
        return str(p.parent()).encode('utf-8')


    @expose_for(plotgroup)
    @web.method.post
    def delete(self, path):
        """
        Deletes a plot file
        """
        p = OPath(path)

        if not p.islegal() or not p.parent().exists:
            raise web.HTTPError(403, 'No access to ' + path)
        else:
            p.delete()
        return str(p.parent()).encode('utf-8')


@web.show_in_nav_for(0, 'chart-line')
class PlotPage(object):
    filedialog = PlotFileDialog()

    @expose_for(plotgroup)
    @web.method.get
    def index(self, f=None, j=None, error=''):
        """
        Shows the plot page

        Parameters
        ----------
        f
            Filename to a plot file
        j
            JSON text representation of a plot
        error
            an error message

        Returns
        -------
            Plot page
        """
        plot = None
        if not j and f:
            try:
                if f[0] == '~' and web.user():
                    f = web.user() + f[1:]
                p = OPath(f or '')
                if p.exists() and p.islegal():
                    with open(p.absolute) as f:
                        j = f.read()
                else:
                    j = None
            except IOError as e:
                error = str(e)
                j = None
        if j:
            try:
                plot = json.loads(j)
            except json.JSONDecodeError as e:
                error = '\n'.join(f'{i:3} | {l}' for i, l in enumerate(j.split('\n'))) + f'\n\n {e}'
                plot = None

        return web.render('plot.html', plot=plot, error=error.replace("'", r"\'")).render()

    @expose_for(plotgroup)
    @web.method.get
    def property(self):
        return web.render('plot/property.html').render()

    @expose_for(plotgroup)
    @web.method.post
    def export(self, plot, fileformat, timeindex, tolerance, grid, interpolation_method, interpolation_limit):
        """
        TODO: Compare to exportall_csv and RegularExport

        Parameters
        ----------
        plot: The plot as JSON
        fileformat: csv, xlsx, pickle, tsv, json
        tolerance: in seconds
        timeindex: as_first, all_timesteps, regular

        Returns
        -------

        """
        from ..tools.exportdatasets import merge_series, export_dataframe
        if fileformat not in ('xlsx', 'csv', 'tsv', 'pickle', 'json', 'msgpack'):
            raise web.HTTPError(500, 'Unknown fileformat: ' + fileformat)
        plot_dict = web.json.loads(plot)
        plot: Plot = Plot(**plot_dict)
        lines = [line for lines in plot.subplots for line in lines]
        series = [line.load(plot.start, plot.end) for line in lines]
        # Convert timeindex to int if possible
        timeindex = web.conv(int, timeindex, timeindex)
        # If timeindex is 'regular', replace with time grid
        if timeindex == 'regular':
            timeindex = grid
        try:
            tolerance = pd.Timedelta(tolerance or '0s')
            interpolation_limit = web.conv(int, interpolation_limit)
            dataframe = merge_series(
                series, timeindex, tolerance,
                interpolation_method, interpolation_limit
            )
        except Exception as e:
            raise web.redirect(url='/plot', error=str(e))

        buffer = io.BytesIO()
        mime = web.mime.get(fileformat, web.mime.binary)
        buffer = export_dataframe(buffer, dataframe, fileformat)
        plotname = plot.name or f'export-{datetime.now():%Y-%m-%d_%H-%M}'
        buffer.seek(0)
        return serve_fileobj(
            buffer,
            str(mime),
            'attachment',
            plotname + '.' + fileformat
        )

    @expose_for(plotgroup)
    @web.method.post
    @web.json_in()
    def figure(self, **kwargs):
        """
        POST: Creates html code to display the plot

        Usage: $.post(odmf_ref('/plot/figure'), plot)
                .done($('#plot').html(result))
                .fail(seterror)
        """
        plot_data = web.cherrypy.request.json
        try:
            plot = Plot(**plot_data)
            svg = plot_backend.to_html(plot)
        except Exception as e:
            raise web.AJAXError(500, message=str(e))
        caption = '<div class="container">' + markdown(plot.description) + '</div>'
        return svg + caption.encode('utf-8')

    @expose_for(plotgroup)
    @web.method.post
    def image(self, format, plot):
        web.mime.set(format)
        plot_dict = web.json.loads(plot)
        plot: Plot = Plot(**plot_dict)
        return plot_backend.to_image(plot, format)


    @expose_for(plotgroup)
    @web.mime.json
    def linedatasets_json(self, subplot, line, plot):
        plot_dict = web.json.loads(plot)
        plot: Plot = Plot(**plot_dict)
        line = plot.subplots[int(subplot) - 1].lines[int(line)]
        with db.session_scope() as session:
            userlevel = users.current.level if users.current else 0
            datasets = line.getdatasets(session, userlevel)
            return web.json_out(datasets)

    @expose_for(plotgroup)
    @web.method.post
    def export_csv(self, plot, subplot, line):
        # jplot, sp_no, line_no = web.cherrypy.request.json
        jplot = json.loads(plot)
        plot: Plot = Plot(**jplot)
        sp = plot.subplots[int(subplot) - 1]
        line = sp.lines[int(line)]
        filename = ''.join(c if (c.isalnum() or c in '.-_') else '_' for c in line.name) + '.csv'
        buffer = io.StringIO()
        line.export_csv(io, plot.start, plot.end)
        buffer.seek(0)
        return serve_fileobj(buffer, str(web.mime.csv), 'attachment', filename)



