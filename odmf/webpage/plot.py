"""
Created on 01.10.2012

@author: philkraf
"""

import sys

import matplotlib.figure
import numpy as np
import pandas as pd

from traceback import format_exc as traceback

from logging import getLogger

from datetime import datetime, timedelta

import json
from ..tools import Path as OPath
from ..config import conf
from ..plot import Plot, NoDataError
from .markdown import MarkDown
from .. import db
from . import lib as web
from .auth import Level, expose_for, users

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


def to_datetime(start, end):
    if isinstance(start, str):
        if start[0] == '-':
            start = datetime.today() + timedelta(days=int(start))
        else:
            start = pd.to_datetime(start).to_pydatetime()
    if isinstance(start, int):
        start = datetime.today() + timedelta(days=int(start))
    if isinstance(end, str):
        if end[0] == '-':
            end = datetime.today()
        else:
            end = pd.to_datetime(start).to_pydatetime()
    if isinstance(end, int):
        end = datetime.today()
    return start, end


class PlotError(web.HTTPError):

    def __init__(self, message: str):
        self.message = message
        super().__init__(400, 'odmf-plot: Plot object is malformed, error: ' + message)

    def get_error_page(self, *args, **kwargs):
        from .lib import render
        error = '## Plot object incorrect\n\n' + self.message
        return render('plot.html', plot=None, error=error).render().encode('utf-8')


plotgroup = Level.logger


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
        from .filemanager import file_auth as fa
        p = OPath(path or web.user())
        user = users.current
        if not p.islegal():
            raise web.HTTPError(403, 'No access to ' + path)
        if not p.exists():
            p = OPath('.')
        directories, files = p.listdir()
        directories = [d for d in directories
                       if fa.check_directory(d, user) >= fa.Mode.read]
        files = [f for f in files if f.basename.endswith('.plot')]
        mode = fa.check_directory(p, user)
        res = web.render(
            'plot/filedialog.html',
            path=p,
            directories=directories,
            files=files,
            can_write=mode >= fa.Mode.write
        ).render()
        return res

    @expose_for(plotgroup)
    @web.method.post
    def save(self, plot, path):
        """
        Saves a plot object to the given filename

        Usage: $.post('saveplot', {plot: JSON.stringify(window.plot, path: ${path}).fail(seterror);
        """
        from .filemanager import file_auth as fa
        if not path:
            path = web.user()
        p = OPath(path)
        if not all((
                p.islegal(),
                p.parent().exists,
                fa.check_directory(p.parent(), users.current) >= fa.Mode.write
        )):
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


@web.show_in_nav_for(1, 'chart-line')
class PlotPage(object):
    filedialog = PlotFileDialog()

    @expose_for(plotgroup)
    @web.method.get
    def index(self, f=None, j=None, autoreload=False, error=''):
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
        p = None
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
                if p:
                    plot['path'] = str(p.parent())
                autoreload = True
            except json.JSONDecodeError as e:
                error = '\n'.join(f'{i:3} | {l}' for i, l in enumerate(j.split('\n'))) + f'\n\n {e}'
                plot = None

        return web.render('plot.html', plot=plot, autoreload=autoreload, error=error.replace("'", r"\'")).render()

    @expose_for(plotgroup)
    @web.method.get
    def property(self):
        return web.render('plot/property.html').render()

    @expose_for(plotgroup)
    @web.method.post
    def export(self, plot, fileformat, timeindex, tolerance, grid, interpolation_method, interpolation_limit):
        """
        Parameters
        ----------
        plot: The plot as JSON
        fileformat: csv, xlsx, pickle, tsv, json, parquet
        tolerance: in seconds
        timeindex: as_first, all_timesteps, regular

        Returns
        -------

        """
        from ..tools.exportdatasets import merge_series, serve_dataframe
        if fileformat not in ('xlsx', 'csv', 'tsv', 'pickle', 'json', 'msgpack', 'parquet'):
            raise web.HTTPError(500, 'Unknown fileformat: ' + fileformat)
        plot_dict = web.json.loads(plot)
        plot: Plot = Plot(**plot_dict)
        start, end = plot.get_time_span()
        lines = [line for lines in plot.subplots for line in lines]
        series = [line.load(start, end) for line in lines]
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
            raise web.redirect(conf.url('/plot'), error=str(e))

        plotname = plot.name or f'export-{datetime.now():%Y-%m-%d_%H-%M}'

        return serve_dataframe(dataframe, f'{plotname}.{fileformat}', index_label='time')

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
            if not plot.subplots:
                raise NoDataError('Nothing to plot, add a subplot')
            svg = plot_backend.to_html(plot)
        except NoDataError as e:
            raise web.AJAXError(400, str(e)) from e
        except Exception as e:
            if users.current.is_member('admin'):
                msg = str(e) + '\n\n```\n' + traceback() + '\n```\n'
            else:
                msg = str(e)
            raise web.AJAXError(500, message=msg)
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
    def linedatasets_json(self,valuetype, site, instrument, level, start, end):
        with db.session_scope() as session:
            valuetype = web.conv(int, valuetype)
            site = web.conv(int, site)
            level = web.conv(float, level)
            instrument = web.conv(int, instrument)
            start, end = to_datetime(start, end)
            me = users.current
            datasets = session.query(db.Dataset).filter(
                db.Dataset._valuetype == valuetype,
                db.Dataset._site == site,
                db.Dataset.start <= end,
                db.Dataset.end >= start
            )
            if not pd.isnull(instrument):
                datasets = datasets.filter(db.Dataset._source == instrument)
            if not pd.isnull(level):
                datasets = datasets.filter(db.Dataset.level == level)
            datasets =  [
                ds for ds in datasets.order_by(db.Dataset.start)
                if ds.get_access_level(me) >= ds.access
            ]
            return web.json_out(datasets)

