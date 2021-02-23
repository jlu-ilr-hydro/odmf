"""
Created on 01.10.2012

@author: philkraf
"""

import sys
# import matplotlib
# matplotlib.use('Agg')

import codecs

import os
import pylab as plt
from matplotlib.ticker import MaxNLocator
import matplotlib.figure
import numpy as np
import pandas as pd

from cherrypy.lib.static import serve_fileobj

from datetime import datetime, timedelta
from io import StringIO
from io import BytesIO

import json
from ..tools import Path as OPath
from .markdown import MarkDown
from .. import db
from . import lib as web
from .auth import group, expose_for, users

nan = np.nan


if sys.platform == 'win32':
    matplotlib.rc('font', **{'sans-serif': 'Arial',
                             'family': 'sans-serif'})

markdown = MarkDown()

def asdict(obj):
    """
    Creates a dictionary representation from an object
    """
    if hasattr(obj, '__jdict__'):
        return obj.__jdict__()
    elif (not type(obj) is dict) and hasattr(obj, '__iter__'):
        return [asdict(o) for o in obj]
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        return obj


class PlotError(web.cherrypy.HTTPError):

    def __init__(self, message: str):
        self.message = message
        super().__init__(400, 'odmf-plot: Plot object is malformed, error: ' + message)

    def get_error_page(self, *args, **kwargs):
        from .lib import render
        error = '## Plot object incorrect\n\n' + self.message
        return render('plot.html', error=error).render().encode('utf-8')


class Line:
    """
    Represents a single line of a subplot
    """

    def __init__(self, subplot, valuetype, site, instrument=None, level=None,
                 color='', marker='', linestyle='',
                 transformation=None, aggregatefunction='mean', name=None):
        """
        Create a Line:
        @param subplot: The Subplot to which this line belongs
        @param valuetype: The valuetype id of the line
        @param site: the site id of the line
        @param instrument: the instrument of the line
        @param color: the color of the line (k,b,g,r,y,m,c)
        @param linestyle: the line style (-,--,:,-.)
        @param marker: the marker of the line data points (o,x,+,|,. etc.)
        @param transformation: Not used    
        """
        self.subplot = subplot
        self.marker = marker
        self.color = color
        self.linestyle = linestyle
        self.valuetypeid = valuetype
        self.siteid = site
        self.instrumentid = instrument
        self.level = level
        self.transformation = transformation
        self.aggregatefunction = aggregatefunction
        self.name = name or self.generate_name()

    def generate_name(self):
        """
        Generates a name for the line from its meta data
        """
        with db.session_scope() as session:
            instrument = self.instrument(session)
            valuetype = self.valuetype(session)
            if instrument:
                name = '%s at #%i%s using %s' % (valuetype, self.siteid,
                                                 '(%gm)' % self.level if self.level is not None else '',
                                                 instrument.name)
            else:
                name = '%s at #%i%s' % (valuetype, self.siteid,
                                        '(%gm)' % self.level if self.level is not None else '')
            if self.subplot.plot.aggregate:
                name += ' (%s/%s)' % (self.aggregatefunction,
                                      self.subplot.plot.aggregate)
        return name

    def getdatasets(self, session):
        """
        Loads the datasets for this line
        """
        userlevel = users.current.level if users.current else 0

        datasets = session.query(db.Dataset).filter(
            db.Dataset._valuetype == self.valuetypeid,
            db.Dataset._site == self.siteid,
            db.Dataset.start <= self.subplot.plot.end,
            db.Dataset.end >= self.subplot.plot.start,
            db.Dataset.access <= userlevel
        )
        if self.instrumentid:
            datasets = datasets.filter(db.Dataset._source == self.instrumentid)
        if self.level is not None:
            datasets = datasets.filter(db.Dataset.level == self.level)
        return datasets.order_by(db.Dataset.start).all()

    def load(self, start=None, end=None) -> pd.Series:
        """
        Loads the records into an array
        """
        with db.session_scope() as session:
            start = start or self.subplot.plot.start
            end = end or self.subplot.plot.end
            datasets = self.getdatasets(session)
            if not datasets:
                raise ValueError("No data to compute")
            group = db.DatasetGroup([ds.id for ds in datasets], start, end)
            series = group.asseries(session)
            series.name = self.name

        if self.subplot.plot.aggregate:
            sampler = series.resample(self.subplot.plot.aggregate)
            series = sampler.aggregate(self.aggregatefunction)

        # There were problems with arrays from length 0
        if series.empty:
            raise ValueError("No data to compute")
        return series

    def draw(self, ax, start=None, end=None):
        """
        Draws the line to the matplotlib axis ax
        """
        try:
            data = self.load(start, end)
            # Do the plot
            style = dict(color=self.color or 'k',
                         linestyle=self.linestyle, marker=self.marker)
            data.plot.line(**style, ax=ax, label=self.name)
        except ValueError as e:
            print(e)

    def valuetype(self, session):
        return session.query(db.ValueType).get(
            int(self.valuetypeid)) if self.valuetypeid else None

    def site(self, session):
        return session.query(db.Site).get(int(self.siteid)) if self.siteid else None

    def instrument(self, session):
        return session.query(db.Datasource).get(
            int(self.instrumentid)) if self.instrumentid else None

    def export_csv(self, stream, start=None, end=None):
        """
        Exports the line as csv file
        """
        data = self.load(start, end)
        data.to_csv(stream, encoding='utf-8-sig', index_label='time')

    def __jdict__(self):
        """
        Returns a dictionary of the line
        """
        return dict(valuetype=self.valuetypeid or None,
                    site=self.siteid or None,
                    instrument=self.instrumentid or None,
                    level=self.level,
                    color=self.color, linestyle=self.linestyle, marker=self.marker,
                    transformation=self.transformation,
                    aggregatefunction=self.aggregatefunction, name=self.name)

    def __str__(self):
        """
        Returns a string representation
        """
        return self.name

    def __repr__(self):
        return f"plot.Line({self.valuetypeid}@#{self.siteid},'{self.color}{self.linestyle}{self.marker}')"


class Subplot:
    """
    Represents a subplot of the plot
    """

    def __init__(self, plot, ylim=None, logsite: int=None, lines=None):
        """
        Create the subplot with Plot.addtimeplot
        """
        self.plot = plot
        self.lines = [
            Line(self, **ldict)
            for ldict in lines
        ]
        self.ylim = ylim
        self.logsite = logsite


    def draw(self, ax: matplotlib.figure.Axes):
        """
        Draws the subplot on a matplotlib figure
        """
        for l in self.lines:
            l.draw(ax, self.plot.start, self.plot.end)

        if self.ylim:
            if np.isfinite(self.ylim[0]):
                ax.set_ylim(bottom=self.ylim[0])
            if np.isfinite(self.ylim[1]):
                ax.set_ylim(top=self.ylim[1])

        with db.session_scope() as session:

            if self.lines:
                l = self.lines[0]
                valuetype = session.query(db.ValueType).get(l.valuetypeid)
                ax.set_ylabel('%s [%s]' % (valuetype.name, valuetype.unit),
                           fontsize=self.plot.fontsize(1.2))

            # Show log book entries for the logsite of this subplot
            # Draw only logs if logsite is a site of the subplot's lines
            if self.logsite in [l.siteid for l in self.lines]:

                # Get logbook entries for logsite during the plot-time
                logs = session.query(db.Log).filter_by(_site=self.logsite).filter(
                    db.Log.time >= self.plot.start).filter(db.Log.time <= self.plot.end)
                # Traverse logs and draw them
                for log in logs:
                    x = np.datetime64(log.time)
                    ax.axvline(x, linestyle='-', color='r',
                                alpha=0.5, linewidth=3)
                    ax.text(x, plt.ylim()[0], log.type,
                             ha='left', va='bottom', fontsize=self.plot.fontsize(0.9))
        ax.set_xlim(self.plot.start, self.plot.end)
        for xtl in ax.get_xticklabels():
            xtl.set_rotation(15)
        ax.yaxis.set_major_locator(MaxNLocator(prune='upper'))
        ax.tick_params(axis='both', which='major', labelsize=self.plot.fontsize(1.1))

        ax.grid()
        ax.legend(loc=0, prop=dict(size=self.plot.fontsize(1)))

    def __jdict__(self):
        """
        Returns a dictionary with the properties of this plot
        """
        return dict(lines=asdict(self.lines),
                    ylim=self.ylim, logsite=self.logsite)


class Plot:
    """
    Represents a full plot (matplotlib figure)
    """

    def __init__(self, height=None, width=None, columns=None, start=None, end=None, **kwargs):
        """
        @param size: A tuple (width,height), the size of the plot in inches (with 100dpi)
        @param columns: number of subplot columns
        @param start: Date for the beginning x axis
        @param end: Date of the end of the x axis
        """
        self.start = start or datetime.today() - timedelta(days=365)
        self.end = end or datetime.today()
        self.size = (width or 640, height or 480)
        self.columns = columns or 1
        self.subplots = []
        self.name = kwargs.pop('name', '')
        self.aggregate = kwargs.pop('aggregate', '')
        self.description = kwargs.pop('description', '')
        self.subplots = [
            Subplot(self, **spargs)
            for i, spargs in enumerate(kwargs.pop('subplots', []))
        ]

        self.args = kwargs

    def fontsize(self, em):
        """
        Returns the fontsize relative to the figure height. 1 em equals 1/60 of the height
        """
        return em * self.size[1] / 60


    def draw(self) -> matplotlib.figure.Figure:
        """
        Draws the plot and returns the matplotlib.Figure object with the populated figure
        """
        # calc. number of rows with ceiling division (https://stackoverflow.com/a/17511341/3032680)
        rows = -(-len(self.subplots) // self.columns)
        size_inch = self.size[0] / 100.0, self.size[1] / 100.0
        fig, axes = plt.subplots(ncols=self.columns, nrows=rows, squeeze=False,
                                 figsize=size_inch, dpi=100, sharex='all')
        for sp, ax in zip(self.subplots, axes.ravel()):
            sp.draw(ax)
        fig.subplots_adjust(top=0.975, bottom=0.1, hspace=0.0)
        return fig

    def to_image(self, format: str, dpi=100) -> bytes:
        """
        Draws the plot and returns a byte string containing the image
        """
        fig = self.draw()
        with BytesIO() as io:
            fig.savefig(io, format=format, dpi=dpi)
            plt.close('all')
            io.seek(0)
            return io.getvalue()


    def __jdict__(self):
        """
        Creates a dictionary with all properties of the plot, the subplots and their lines
        """
        return dict(width=self.size[0], height=self.size[1], columns=self.columns,
                    start=self.start, end=self.end,
                    subplots=asdict(self.subplots),
                    aggregate=self.aggregate,
                    description=self.description)



#TODO: Define plotgroup
plotgroup = None


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

        if not j:
            try:
                if not f or not web.user():
                    f = '~/plots/default.plot'
                if f[0] == '~' and web.user():
                    f = web.user() + f[1:]
                p = OPath(f or '')
                if p.exists() and p.islegal():
                    with open(p.absolute) as f:
                        j = f.read()
                else:
                    j = '{}'
            except IOError as e:
                error = str(e)
                j = '{}'
        try:
            plot = json.loads(j)
        except json.JSONDecodeError as e:
            error = '\n'.join(f'{i:3} | {l}' for i, l in enumerate(j.split('\n'))) + f'\n\n {e}'
            plot = None

        return web.render('plot.html', plot=plot, error=error).render()

    @expose_for(plotgroup)
    @web.method.get
    def property(self):
        return web.render('plot/property.html').render()

    @expose_for(plotgroup)
    @web.method.get
    def exportdialog(self):
        return web.render('plot/exportdialog.html').render()

    @expose_for(plotgroup)
    @web.method.post
    def export(self, plot, format, method, tolerance, timestep):
        """
        TODO: Compare to exportall_csv and RegularExport

        Parameters
        ----------
        plot: The plot as JSON
        format: csv, excel, json, feather
        tolerance: in seconds
        method: as_first, all_timesteps, regular

        Returns
        -------

        """
        ...

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
        plot = Plot(**plot_data)
        fig = plot.draw()
        import io
        buf = io.BytesIO()
        fig.savefig(buf, format='svg')
        # buf.write(f'<div class="fig-subtitle">{markdown(plot.description)}</div>'.encode('utf-8'))
        html = buf.getvalue()
        return html

    @expose_for(plotgroup)
    @web.method.post
    def image(self, format, plot):
        web.mime.set(format)
        plot_dict = web.json.loads(plot)
        plot: Plot = Plot(**plot_dict)
        return plot.to_image(format)


    @expose_for(plotgroup)
    @web.mime.json
    def linedatasets_json(self, subplot, line, plot):
        plot_dict = web.json.loads(plot)
        plot: Plot = Plot(**plot_dict)
        line = plot.subplots[int(subplot) - 1].lines[int(line)]
        with db.session_scope() as session:
            datasets = line.getdatasets(session)
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
        io = StringIO()
        line.export_csv(io, plot.start, plot.end)
        io.seek(0)
        return serve_fileobj(io, str(web.mime.csv), 'attachment', filename)


    @expose_for(plotgroup)
    @web.mime.csv
    def exportall_csv(self, tolerance):
        plot: Plot = Plot(**web.cherrypy.request.json)
        lines = []
        for sp in plot.subplots:
            lines.extend(sp.lines)
        stream = StringIO()
        from ..tools.exportdatasets import exportLines
        exportLines(stream, lines, web.conv(float, tolerance, 60))
        stream.seek(0)
        return serve_fileobj(stream)

    @expose_for(plotgroup)
    @web.mime.csv
    def RegularTimeseries_csv(self, tolerance=12, interpolation=''):
        plot: Plot = Plot(**web.cherrypy.request.json)
        datasetids = []
        with db.session_scope() as session:
            lines = []
            for sp in plot.subplots:
                lines.extend(sp.lines)
                for line in sp.lines:
                    datasetids.extend(ds.id for ds in line.getdatasets(session))
        stream = StringIO()
        from ..tools.ExportRegularData import createPandaDfs
        # explicit decode() for byte to string
        stream.write(codecs.BOM_UTF8.decode())
        createPandaDfs(lines, plot.start, plot.end, stream,
                       interpolationtime=interpolation, tolerance=float(tolerance))
        return stream.getvalue()



