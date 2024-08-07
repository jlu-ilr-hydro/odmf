from datetime import datetime, timedelta
import pandas as pd
from .. import db

class NoDataError(ValueError):
    ...

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


class Line:
    """
    Represents a single line of a subplot
    """

    def __init__(self, subplot, valuetype, site, instrument=None, level=None,
                 color='', marker='', linestyle='-', linewidth=1,
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
        self.linewidth = linewidth
        self.linestyle = linestyle
        self.valuetypeid = valuetype
        self.siteid = site
        self.instrumentid = instrument
        self.level = level
        self.transformation = transformation
        self.aggregatefunction = aggregatefunction
        self.name = name or self.generate_name()
        if not (linestyle or marker):
            raise NoDataError('Lines need either a linestyle or a marker for the creation')

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
        from ..webpage.auth import users
        me = users.current
        start, end = self.subplot.plot.get_time_span()
        datasets = session.query(db.Dataset).filter(
            db.Dataset._valuetype == self.valuetypeid,
            db.Dataset._site == self.siteid,
            db.Dataset.start <= end,
            db.Dataset.end >= start
        )
        if self.instrumentid:
            datasets = datasets.filter(db.Dataset._source == self.instrumentid)
        if self.level is not None:
            datasets = datasets.filter(db.Dataset.level == self.level)
        return [
            ds for ds in datasets.order_by(db.Dataset.start)
            if ds.get_access_level(me) >= ds.access
        ]

    def load(self, start=None, end=None):
        """
        Loads the records into an array
        """
        with db.session_scope() as session:
            plot_timespan = self.subplot.plot.get_time_span()
            end = end or plot_timespan[1]
            start = start or plot_timespan[0]
            datasets = self.getdatasets(session)
            if datasets:
                group = db.DatasetGroup([ds.id for ds in datasets], start, end)
                series = group.asseries(session, self.name)
            else:
                series = pd.Series([])

        if self.subplot.plot.aggregate and not series.empty:
            if self.subplot.plot.aggregate == 'decade':
                from ..tools.exportdatasets import DecadeMonthStart
                sampler = series.resample(DecadeMonthStart())
            else:
                sampler = series.resample(self.subplot.plot.aggregate)
            series = sampler.aggregate(self.aggregatefunction or 'mean')

        series.name = str(self)
        return series

    def valuetype(self, session):
        return session.get(db.ValueType, 
            int(self.valuetypeid)) if self.valuetypeid else None

    def site(self, session):
        return session.get(db.Site, int(self.siteid)) if self.siteid else None

    def instrument(self, session):
        return session.get(db.Datasource, 
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
                    color=self.color, linestyle=self.linestyle, marker=self.marker, linewidth=self.linewidth,
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

    def __init__(self, plot, ylim=None, logsite: int=None, ylabel=None, lines=None):
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
        self.ylabel = ylabel

    def __iter__(self):
        return iter(self.lines)

    def get_logs(self):
        start, end = self.plot.get_time_span()
        with db.session_scope() as session:
            # Get logbook entries for logsite during the plot-time
            logs = session.query(db.Log).filter_by(_site=self.logsite).filter(
                db.Log.time >= start).filter(db.Log.time <= end)
            return [
                (log.time, log.type, str(log))
                for log in logs
            ]

    def get_ylabel(self):
        """
        Gets the label for the y axis of the subplot
        """
        if self.ylabel:
            return self.ylabel
        elif self.lines:
            with db.session_scope() as session:
                l = self.lines[0]
                valuetype = session.get(db.ValueType, l.valuetypeid)
                return f'{valuetype.name} [{valuetype.unit}]'
        else:
            return 'unknown'


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
        if isinstance(start, str):
            if start[0] == '-':
                start = int(start)
            else:
                start = pd.to_datetime(start).to_pydatetime()
        if isinstance(end, str):
            if end[0] == '-':
                end = int(end)
            else:
                end = pd.to_datetime(end).to_pydatetime()
        self.start = start or -90
        self.end = end or -90
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

    def get_time_span(self):
        """
        Returns the time span for the plot
        """
        if isinstance(self.start, int):
            end = datetime.today()
            start = end + timedelta(days=self.start)
            return start, end
        else:
            return (self.start or datetime.today() - timedelta(days=90),
                    self.end or datetime.today())


    def lines(self):

        return [line for sp in self.subplots for line in sp.lines]

    def fontsize(self, em):
        """
        Returns the fontsize relative to the figure height. 1 em equals 1/60 of the height
        """
        return em * self.size[1] / 60

    def __jdict__(self):
        """
        Creates a dictionary with all properties of the plot, the subplots and their lines
        """
        return dict(width=self.size[0], height=self.size[1], columns=self.columns,
                    start=self.start, end=self.end,
                    subplots=asdict(self.subplots),
                    aggregate=self.aggregate,
                    description=self.description)

