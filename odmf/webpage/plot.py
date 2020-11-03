'''
Created on 01.10.2012

@author: philkraf
'''
import sys
import matplotlib
matplotlib.use('Agg')
import codecs

import os
import pylab as plt
from matplotlib.ticker import MaxNLocator
import matplotlib.dates
import numpy as np
import pandas as pd

from traceback import format_exc as traceback
from datetime import datetime, timedelta
from io import StringIO
from io import BytesIO

from pandas import to_datetime
import json
from pathlib import Path

from ..config import conf
from .. import db
from . import lib as web
from .auth import group, expose_for, users

t0 = datetime(1, 1, 1)
nan = np.nan


if sys.platform == 'win32':
    matplotlib.rc('font', **{'sans-serif': 'Arial',
                             'family': 'sans-serif'})


def date2num(t):
    """
    Converts a datetime to a number 
    """
    if t is None:
        return nan
    else:
        return (t - t0).total_seconds() / 86400 + 1.0


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
        user = users.current
        error = '## Plot object incorrect\n\n' + self.message
        return render('plot.html', error=error).render().encode('utf-8')


class Line:
    """
    Represents a single line of a subplot
    """

    def __init__(self, subplot, valuetype, site, instrument=None, level=None,
                 color='', marker='', linestyle='',
                 transformation=None, aggregatefunction='mean'):
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
        session = db.Session()
        self.valuetype = session.query(db.ValueType).get(
            int(valuetype)) if valuetype else None
        self.site = session.query(db.Site).get(int(site)) if site else None
        self.instrument = session.query(db.Datasource).get(
            int(instrument)) if instrument else None
        self.level = level
        session.close()
        self.transformation = transformation
        self.aggregatefunction = aggregatefunction

    def getdatasets(self, session):
        """
        Loads the datasets for this line
        """
        userlevel = users.current.level if users.current else 0
        datasets = session.query(db.Dataset).filter(db.Dataset.valuetype == self.valuetype,
                                                    db.Dataset.site == self.site,
                                                    db.Dataset.start <= self.subplot.plot.enddate,
                                                    db.Dataset.end >= self.subplot.plot.startdate,
                                                    db.Dataset.access <= userlevel
                                                    )
        if self.instrument:
            datasets = datasets.filter(db.Dataset.source == self.instrument)
        if self.level is not None:
            datasets = datasets.filter(db.Dataset.level == self.level)
        return datasets.order_by(db.Dataset.start).all()

    def aggregate(self):
        session = db.Session()
        series = self.load()
        # Use pandas resample mechanism for aggregation
        aggseries = series.resample(
            self.subplot.plot.aggregate, self.aggregatefunction)
        return aggseries

    def load(self) -> pd.Series:
        """
        Loads the records into an array
        """
        with db.session_scope() as session:
            error = ''
            start = self.subplot.plot.startdate
            end = self.subplot.plot.enddate
            datasets = self.getdatasets(session)
            group = db.DatasetGroup([ds.id for ds in datasets], start, end)
            series = group.asseries(session)

        if self.subplot.plot.aggregate:
            sampler = series.resample(self.subplot.plot.aggregate)
            series = sampler.aggregate(self.aggregatefunction)

        # There were problems with arrays from length 0
        if not series:
            raise ValueError("No data to compute")
        return series

    def draw(self, ax, startdate=None, enddate=None):
        """
        Draws the line to the matplotlib axis ax
        """
        try:
            data = self.load(startdate, enddate)
            # Do the plot
            label = str(self)
            style = dict(color=self.color or 'k',
                         linestyle=self.linestyle, marker=self.marker)
            data.plot.line(**style, ax=ax, label=label)
        except ValueError as e:
            print(e)

    def export_csv(self, stream, startdate=None, enddate=None):
        """
        Exports the line as csv file
        """
        data = self.load(startdate, enddate)
        data.name = str(self.valuetype)
        data.to_csv(stream, encoding='utf-8-sig')

    def __jdict__(self):
        """
        Returns a dictionary of the line
        """
        return dict(valuetype=self.valuetype.id if self.valuetype else None,
                    site=self.site.id if self.site else None,
                    instrument=self.instrument.id if self.instrument else None,
                    level=self.level,
                    color=self.color, linestyle=self.linestyle, marker=self.marker,
                    transformation=self.transformation,
                    aggregatefunction=self.aggregatefunction)


    def __str__(self):
        """
        Returns a string representation
        """
        res = ''
        if self.instrument:
            res = '%s at #%i%s using %s' % (self.valuetype, self.site.id,
                                            '(%gm)' % self.level if self.level is not None else '',
                                            self.instrument.name)
        else:
            res = '%s at #%i%s' % (self.valuetype, self.site.id,
                                   '(%gm)' % self.level if self.level is not None else '')
        if self.subplot.plot.aggregate:
            res += ' (%s/%s)' % (self.aggregatefunction,
                                 self.subplot.plot.aggregate)
        return res

    def __repr__(self):
        return "plot.Line(%s@%s,'%s')" % (self.valuetype, self.site, self.color + self.linestyle + self.marker)


class Subplot:
    """
    Represents a subplot of the plot
    """

    def __init__(self, plot, position=1, ylim=None, logsite:int=None, lines=None):
        """
        Create the subplot with Plot.addtimeplot
        """
        self.plot = plot
        self.position = position
        self.lines = []
        if lines:
            for l in lines:
                self.addline(**l)
        self.ylim = ylim
        self.logsite = logsite

    def addline(self, valuetype, site, instrument=None, level=None,
                color='k', linestyle='-', marker='',
                aggfunc='mean'):
        """
        Adds a line to the subplot
        @param valuetype: the id of a valuetype
        @param site: the id of a site
        @param instrument: the id of an instrument (can be omitted)
        @param color: the color of the line (k,b,g,r,y,m,c)
        @param linestyle: the line style (-,--,:,-.)
        @param marker: the marker of the line data points (o,x,+,|,. etc.)
        @param aggfunc: Type of aggregation function (mean,max,min) 
        """
        self.lines.append(Line(self, valuetype=valuetype, site=site, instrument=instrument, level=level,
                               color=color, linestyle=linestyle, marker=marker,
                               aggregatefunction=aggfunc))
        return self

    def get_sites(self):
        return dict((line.site.id, str(line.site)) for line in self.lines)

    def draw(self, figure):
        """
        Draws the subplot on a matplotlib figure
        """
        ax = figure.axes[self.position - 1]
        plt.sca(ax)
        for l in self.lines:
            l.draw(ax, self.plot.startdate, self.plot.enddate)
        if self.ylim:
            if np.isfinite(self.ylim[0]):
                plt.ylim(ymin=self.ylim[0])
            if np.isfinite(self.ylim[1]):
                plt.ylim(ymax=self.ylim[1])

        # Show log book entries for the logsite of this subplot

        # Get all site-ids of this subplot
        sites = self.get_sites()
        # Draw only logs if logsite is a site of the subplot's lines
        if self.logsite in sites:
            # open session - trying the new scoped_session
            with db.session_scope() as session:
                # Get logbook entries for logsite during the plot-time
                logs = session.query(db.Log).filter_by(_site=self.logsite).filter(
                    db.Log.time >= self.plot.startdate).filter(db.Log.time <= self.plot.enddate)
                # Traverse logs and draw them
                for log in logs:
                    x = plt.date2num(log.time)
                    plt.axvline(x, linestyle='-', color='r',
                                alpha=0.5, linewidth=3)
                    plt.text(x, plt.ylim()[0], log.type,
                             ha='left', va='bottom', fontsize=8)
        plt.xlim(date2num(self.plot.startdate), date2num(self.plot.enddate))
        plt.xticks(rotation=15)
        ax.yaxis.set_major_locator(MaxNLocator(prune='upper'))
        ax.tick_params(axis='both', which='major', labelsize=8)

        ax.grid()
        ax.legend(loc=0, prop=dict(size=9))
        if self.lines:
            l = self.lines[0]
            plt.ylabel('%s [%s]' % (l.valuetype.name, l.valuetype.unit),
                       fontsize=self.plot.args.get('ylabelfs', 'small'))

    def __jdict__(self):
        """
        Returns a dictionary with the properties of this plot
        """
        return dict(lines=asdict(self.lines),
                    ylim=self.ylim, position=self.position,
                    logsite=self.logsite)



class Plot(object):
    """
    Represents a full plot (matplotlib figure)
    """

    def __init__(self, size=(600, 480), columns=1, startdate=None, enddate=None, **kwargs):
        """
        @param size: A tuple (width,height), the size of the plot in inches (with 100dpi)
        @param columns: number of subplot columns
        @param startdate: Date for the beginning x axis
        @param enddate: Date of the end of the x axis 
        """
        self.startdate = startdate or datetime.today() - timedelta(days=365)
        self.enddate = enddate or datetime.today()
        self.size = size
        self.columns = columns
        self.subplots = []
        self.name = kwargs.pop('name', '')
        self.aggregate = kwargs.pop('description', '')
        self.description = kwargs.pop('description', '')
        self.subplots = [
            Subplot(self, i + 1, **spargs)
            for i, spargs in enumerate(kwargs.pop('subplots', []))
        ]

        self.args = kwargs



    def draw(self):
        """
        Draws the plot and returns the png file as a string
        """
        # calc. number of rows with ceiling division (https://stackoverflow.com/a/17511341/3032680)
        rows = -(-len(self.subplots) // self.columns)
        size_inch = self.size[0] / 100.0, self.size[1] / 100.0
        fig, axes = plt.subplots(ncols=self.columns, nrows=rows,
                                 figsize=size_inch, dpi=100, sharex='all')
        for sp in self.subplots:
            sp.draw(fig)
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
        return dict(size=self.size, columns=self.columns,
                    startdate=self.startdate, enddate=self.enddate,
                    subplots=asdict(self.subplots),
                    aggregate=self.aggregate,
                    description=self.description)

    def save(self, fn):
        d = asdict(self)
        try:
            self.absfilename(fn).write_text(web.as_json(d))
        except:
            raise PlotError(traceback())

    @classmethod
    def load(cls, fn):
        fp = cls.absfilename(fn).open()
        plot = Plot(json.load(fp))
        return plot

    @classmethod
    def listdir(cls):

        return [
            fn.name.replace(web.user() + '.', '').replace('.plot', '')
            for fn in cls.absfilename().glob(f'{web.user()}.*.plot')
        ]

    @classmethod
    def killfile(cls, fn):
        path = cls.absfilename(fn)
        if path.exists():
            path.unlink()
        else:
            raise PlotError("File %s does not exist" % fn)

    @classmethod
    def absfilename(cls, fn: str=None)->Path:
        username = web.user() or 'nologin'
        plot_dir = os.path.join(conf.datafiles, username, 'plots')
        os.makedirs(plot_dir, exist_ok=True)

        if fn:
            return Path( f'{plot_dir}/{fn}.plot').absolute()
        else:
            return Path( f'{plot_dir}/{fn}.plot').absolute()


plotgroup = group.logger

@web.show_in_nav_for(0, 'chart-line')
class PlotPage(object):

    @expose_for(plotgroup)
    def index(self, valuetype=None, site=None, error=''):
        plot = Plot()
        return web.render('plot.html', plot=plot, error=error).render()

    @expose_for(plotgroup)
    def loadplot(self, filename):
        try:
            return web.as_json(Plot.load(filename))
        except Exception as e:
            raise PlotError(str(e))

    @expose_for(plotgroup)
    @web.method.post
    @web.json_in()
    def saveplot(self):
        """
        Saves a plot object to the given filename

        Usage: $.post('saveplot', [filename, plot]).fail(seterror);
        """
        filename, plot = web.cherrypy.request.json
        plot = Plot(**plot)
        if not filename:
            raise PlotError('Cannot save file: no filename given')
        else:
            return plot.save(filename)

    @expose_for(plotgroup)
    def deleteplotfile(self, filename):
        return Plot.killfile(filename)

    @expose_for(plotgroup)
    @web.mime.json
    def listplotfiles(self):
        return web.json_out(Plot.listdir())


    @expose_for(plotgroup)
    @web.method.post
    @web.json_in()
    def image_d3(self, **kwargs):
        """
        Creates html code with the plot as a d3 object using https://pypi.org/project/mpld3/

        Usage: $.post(odmf_ref('/plot/image.d3'), plot)
                .done($('#plot').html(result))
                .fail(seterror)
        """
        plot_data = web.cherrypy.request.json
        plot = Plot(**plot_data)
        from mpld3 import fig_to_html
        fig = plot.draw()
        html = fig_to_html(fig)
        return html.encode('utf-8')

    @expose_for(plotgroup)
    @web.method.post
    @web.json_in()
    @web.mime.png
    def image_png(self, **kwargs):
        plot: Plot = Plot(**web.cherrypy.request.json)
        return plot.to_image('png')

    @expose_for(plotgroup)
    @web.method.post
    @web.json_in()
    @web.mime.pdf
    def image_pdf(self, **kwargs):
        plot: Plot = Plot(**web.cherrypy.request.json)
        return plot.to_image('pdf')

    @expose_for(plotgroup)
    @web.method.post
    @web.json_in()
    @web.mime.svg
    def image_svg(self, **kwargs):
        plot: Plot = Plot(**web.cherrypy.request.json)
        return plot.to_image('svg')

    @expose_for(plotgroup)
    @web.method.post
    @web.json_in()
    @web.mime.tif
    def image_svg(self, **kwargs):
        plot: Plot = Plot(**web.cherrypy.request.json)
        return plot.to_image('tif')

    @expose_for(plotgroup)
    @web.method.post
    @web.json_in()
    @web.mime.jpg
    def image_jpg(self, **kwargs):
        plot: Plot = Plot(**web.cherrypy.request.json)
        return plot.to_image('jpg')

    @expose_for(plotgroup)
    @web.mime.json
    def linedatasets_json(self, subplot, line):
        plot: Plot = Plot(**web.cherrypy.request.json)
        line = plot.subplots[int(subplot) - 1].lines[int(line)]
        with db.session_scope() as session:
            datasets = line.getdatasets(session)
            return web.json_out(datasets)

    @expose_for(plotgroup)
    @web.mime.csv
    def export_csv(self, subplot, line):
        plot: Plot = Plot(**web.cherrypy.request.json)
        sp = plot.subplots[int(subplot) - 1]
        line = sp.lines[int(line)]
        io = StringIO()
        line.export_csv(io, plot.startdate, plot.enddate)
        io.seek(0)
        return io


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
        return stream.getvalue()

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
        createPandaDfs(lines, plot.startdate, plot.enddate, stream,
                       interpolationtime=interpolation, tolerance=float(tolerance))
        return stream.getvalue()



