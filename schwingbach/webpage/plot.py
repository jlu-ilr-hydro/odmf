'''
Created on 01.10.2012

@author: philkraf
'''
import sys
import matplotlib
import codecs
matplotlib.use('Agg', warn=False)
if sys.platform=='win32':
    matplotlib.rc('font', **{'sans-serif' : 'Arial',
                           'family' : 'sans-serif'})
import os
import pylab as plt
import numpy as np
import db
from traceback import format_exc as traceback
from datetime import datetime, timedelta
from cStringIO import StringIO

t0 = datetime(1,1,1)
nan = np.nan
def date2num(t):
    """
    Converts a datetime to a number 
    """
    if t is None:
        return nan
    else:
        return (t-t0).total_seconds()/86400 + 1.0    
def asdict(obj):
    """
    Creates a dictionary representation from an object
    """
    if hasattr(obj,'__jdict__'):
        return obj.__jdict__()
    elif (not type(obj) is dict) and hasattr(obj,'__iter__'):
        return [asdict(o) for o in obj]
    elif hasattr(obj,'isoformat'):
        return obj.isoformat()
    else:
        return obj
class Line(object):
    """
    Represents a single line of a subplot
    """
    def __init__(self,subplot,valuetype,site,instrument=None,style='',
                 transformation=None):
        """
        Create a Line:
        @param subplot: The Subplot to which this line belongs
        @param valuetype: The valuetype id of the line
        @param site: the site id of the line
        @param intrument: the instrument of the line
        @param style: the style of the line. See pylab.plot for details
        @param transformation: Not used    
        """
        self.subplot=subplot
        self.style=style
        session=db.Session()
        self.valuetype=session.query(db.ValueType).get(int(valuetype)) if valuetype else None
        self.site=session.query(db.Site).get(int(site)) if site else None
        self.instrument = session.query(db.Datasource).get(int(instrument)) if instrument else None
        session.close()
        self.transformation=transformation
    def getcachename(self,t_or_v):
        plot = self.subplot.plot
        path = plot.getpath()
        spno = self.subplot.position
        lineno = self.subplot.lines.index(self)
        return '%s.sp%i.l%i.%s.npy' % (path,spno,lineno,t_or_v)
    def getdatasets(self,session):
        """
        Loads the datasets for this line
        """
        datasets = session.query(db.Dataset).filter(db.Dataset.valuetype==self.valuetype,
                                                    db.Dataset.site==self.site)
        if self.instrument:
            datasets=datasets.filter(db.Dataset.source == self.instrument)
        return datasets.order_by(db.Dataset.start).all()
    def killcache(self):
        for s in 'tv':
            if os.path.exists(self.getcachename(s)):
                os.remove(self.getcachename(s))
    def load(self,startdate=None,enddate=None,usecache=False):
        """
        Loads the records into an array
        """
        if usecache and os.path.exists(self.getcachename('t')) and os.path.exists(self.getcachename('v')):
            t=np.fromfile(self.getcachename('t'))
            v=np.fromfile(self.getcachename('v'))
            if not (len(t)==0 or len(v)!=len(t)):
                print ".../\./\|\...load from cache<-" + os.path.basename(self.getcachename('?'))
        else:
            print ".../\./\|\...load from database->" + os.path.basename(self.getcachename('?'))
            session=db.Session()
            error=''
            start=self.subplot.plot.startdate
            end=self.subplot.plot.enddate
            try:
                datasets=self.getdatasets(session)
                group = db.DatasetGroup([ds.id for ds in datasets], start, end)
                t,v = group.asarray(session)
                t.tofile(self.getcachename('t'))
                v.tofile(self.getcachename('v'))
            except Exception as e:
                raise e
            finally:
                session.close()
        print "size(v)=", v.size,"mean(v)=",v[np.isnan(v)==False].mean(),"std(v)=",v[np.isnan(v)==False].std()
        print "size(t)=", t.size,"min(t)=",plt.num2date(t.min()),"max(t)=",plt.num2date(t.max())
        return t,v
    def draw(self,ax,startdate=None,enddate=None):
        """
        Draws the line to the matplotlib axis ax
        """
        t,v = self.load(startdate,enddate,True)
        # Do the plot 
        label = u'%s at site %s' % (self.valuetype.name,self.site)
        if self.style:
            ax.plot_date(t,v,self.style,label=label)
        else:
            ax.plot_date(t,v,c=self.color,marker=self.marker,ls=self.line,label=label)
    
    def export_csv(self,stream,startdate=None,enddate=None):
        """
        Exports the line as csv file
        """
        t,v = self.load(startdate, enddate, True)
        t0 = plt.date2num(datetime(1899,12,30))
        stream.write(codecs.BOM_UTF8)
        stream.write('Time,' + unicode(self.valuetype).encode('UTF-8') + '\n') 
        for t,v in zip(t-t0,v):
            stream.write('%f,%f\n' % (t,v))
        
    def __jdict__(self):
        """
        Returns a dictionary of the line
        """
        return dict(valuetype=self.valuetype.id if self.valuetype else None,
                    site=self.site.id if self.site else None,
                    instrument=self.instrument.id if self.instrument else None,
                    style=self.style,transformation=self.transformation)
    @classmethod
    def fromdict(cls,subplot,d):
        """
        Creates the line element from a dictionary (for loading from session)
        """
        return cls(subplot,valuetype=d.get('valuetype'),site=d.get('site'),instrument=d.get('instrument'),style=d.get('style'),
                   transformation=d.get('transformation'))
    def __str__(self):
        """
        Returns a string representation
        """
        if self.instrument:
            return '%s at %s using %s (%s)' % (self.valuetype, self.site,self.instrument,self.style)
        else:
            return '%s at %s (%s)' % (self.valuetype, self.site,self.style)
    def __repr__(self):
        return "plot.Line(%s@%s,'%s')" % (self.valuetype,self.site,self.style)
    
class Subplot(object):
    """
    Represents a subplot of the plot
    """
    def __init__(self,plot,position=1):
        """
        Create the subplot with Plot.addtimeplot
        """
        self.plot=plot
        self.position=position
        self.lines=[]
        self.ylim = None
    def addline(self,valuetype,site,instrument=None,style=''):
        """
        Adds a line to the subplot
        @param valuetype: the id of a valuetype
        @param site: the id of a site
        @param instrument: the id of an instrument (can be omitted)
        @param style: the style of the line, eg 'o-k' for black line with circle markers 
        """
        self.lines.append(Line(self,valuetype=valuetype,site=site,instrument=instrument,style=style))
        self.plot.createtime = web.formatdate()
        return self
    def draw(self,figure):
        """
        Draws the subplot on a matplotlib figure
        """
        ax = figure.axes[self.position-1]
        plt.sca(ax)
        for l in self.lines:
            l.draw(ax,self.plot.startdate,self.plot.enddate)
        if self.ylim:
            if np.isfinite(self.ylim[0]):
                plt.ylim(ymin=self.ylim[0])
            if np.isfinite(self.ylim[1]):
                plt.ylim(ymax=self.ylim[1])
        plt.xlim(date2num(self.plot.startdate),date2num(self.plot.enddate))
        plt.xticks(rotation=15)
        ax.grid()
        ax.legend(loc=0,prop=dict(size=9))
        if self.lines:
            l=self.lines[0]
            plt.ylabel(u'%s [%s]' % (l.valuetype.name,l.valuetype.unit))
    def __jdict__(self):
        """
        Returns a dictionary with the properties of this plot
        """
        return dict(lines=asdict(self.lines),
                    ylim=self.ylim,position=self.position)
    @classmethod
    def fromdict(cls,plot,d):
        """
        Creates a subplot from a property dictionary
        """
        res = cls(plot=plot,position=d.get('position'))
        res.ylim = d.get('ylim')
        if 'lines' in d:
            for ld in d.get('lines'):
                res.lines.append(Line.fromdict(res,ld))
        return res
                   
class Plot(object):
    """
    Represents a full plot (matplotlib figure)
    """
    def __init__(self,size=(6.0,4.8),columns=1,rows=1,startdate=None,enddate=None):
        """
        @param size: A tuple (width,height), the size of the plot in inches (with 100dpi)
        @param columns: number of subplot columns
        @param rows: number of subplot rows
        @param startdate: Date for the beginning x axis
        @param enddate: Date of the end of the x axis 
        """
        self.startdate=startdate or datetime.today() - timedelta(days=365)
        self.enddate=enddate or datetime.today()
        self.size=size
        self.rows, self.columns = rows,columns
        self.subplots=[]
        self.createtime = web.formatdatetime()
        self.name = 'plot'
    def getpath(self):
        return web.abspath('preferences/plots/' + web.user() + '.' + self.name)
    def addtimeplot(self):
        """
        Adds a new subplot to the plot
        """
        sp = Subplot(self,len(self.subplots)+1)
        self.subplots.append(sp)
        if self.rows * self.columns < len(self.subplots):
            self.rows += 1
        self.createtime = web.formatdatetime()
        return sp
    def draw(self,format='png'):
        """
        Draws the plot and returns the png file as a string
        """
        was_interactive=plt.isinteractive()
        plt.ioff()
        fig,axes=plt.subplots(ncols=self.columns, nrows=self.rows,
                              figsize=self.size,dpi=100)
        for sp in self.subplots:
            sp.draw(fig)
        if was_interactive:
            plt.ion()
            plt.draw()
        elif format:
            self.topref()    
            io = StringIO()
            fig.savefig(io,format=format)
            return io.getvalue()
    def killcache(self):
        for sp in self.subplots:
            for l in sp.lines:
                l.killcache()
    def __jdict__(self):
        """
        Creates a dictionary with all properties of the plot, the subplots and their lines
        """
        return dict(size=self.size,rows=self.rows,columns=self.columns,
                    startdate=self.startdate,enddate=self.enddate,
                    subplots=asdict(self.subplots))
    @classmethod
    def fromdict(cls,d):
        """
        Creates the plot from a dictionary
        """
        res = cls(size=d.get('size'),columns=d.get('columns'),rows=d.get('rows'),
                  startdate=d.get('startdate'),enddate=d.get('enddate'))
        if not (type(res.startdate) is datetime or res.startdate is None):
            res.startdate = web.parsedate(res.startdate)
        if not (type(res.enddate) is datetime or res.enddate is None):
            res.enddate = web.parsedate(res.enddate)
        if 'subplots' in d:
            for sd in d.get('subplots'):
                res.subplots.append(Subplot.fromdict(res,sd))
        return res
    @classmethod
    def frompref(cls,createplot=False):
        """
        Gets the plot from the preferences
        """
        pref=Preferences()
        if 'plot' in pref:    
            return cls.fromdict(pref['plot'])
        else:
            if createplot:
                plot=Plot()
                plot.topref()
                return plot
            return
    
    def topref(self):
        """
        Saves the plot to the preferences
        """
        pref = Preferences()
        pref['plot'] = asdict(self)
   
import webpage.lib as web
from webpage.preferences import Preferences
plotgroup = web.group.logger

class PlotPage(object):
    exposed=True
    @web.expose_for(plotgroup)
    def index(self,valuetype=None,site=None):
        plot=Plot.frompref(createplot=True)
        return web.render('plot.html',plot=plot).render('html')
    
    @web.expose_for(plotgroup)
    def image_png(self,**kwargs):
        web.setmime(web.mime.png)
        plot = Plot.frompref()
        return plot.draw()
    @web.expose_for(plotgroup)
    def image_pdf(self,**kwargs):
        web.setmime(web.mime.pdf)
        plot = Plot.frompref()
        return plot.draw(format='pdf')
    
    @web.expose_for(plotgroup)
    def addsubplot(self):
        try:
            plot = Plot.frompref()
            plot.addtimeplot()
            plot.topref()
        except:
            return traceback()
    @web.expose_for(plotgroup)
    def removesubplot(self,subplotid):
        try:
            plot = Plot.frompref()
            id = int(subplotid)
            sp = plot.subplots.pop(id-1)
            for line in sp.lines:
                line.killcache()
            plot.topref()
            return
        except:
            return traceback()
    @web.expose(plotgroup)
    def changeylim(self,subplotid,ymin=None,ymax=None):
        try:
            plot = Plot.frompref()
            id = int(subplotid)
            sp = plot.subplots[id-1]
            try:
                if ymin and ymax:
                    sp.ylim = float(ymin),float(ymax)
                else:
                    sp.ylim = None
            except ValueError:
                sp.ylim=None
                return "%s,%s is not a pair of numbers for ymin and ymax" % (ymin,ymax)
            plot.createtime = web.formatdate()
            plot.topref()
            return
        except:
            return traceback();
    @web.expose_for(plotgroup)
    def addline(self,subplot,valuetypeid,siteid,instrumentid,style):
        try:
            plot = Plot.frompref()
            spi = int(subplot)
            if spi>len(plot.subplots):
                sp=plot.addtimeplot()
            else:
                sp = plot.subplots[spi-1]         
            sp.addline(web.conv(int,valuetypeid),web.conv(int,siteid),web.conv(int,instrumentid),style=style)
            plot.topref()
        except:
            return traceback()
    
    @web.expose_for(plotgroup)
    def removeline(self,subplot,line):
        plot = Plot.frompref()
        sp = plot.subplots[int(subplot)-1]
        sp.lines[int(line)].killcache()
        del sp.lines[int(line)]
        plot.topref()
    @web.expose_for(plotgroup)
    def reloadline(self,subplot,line):
        plot = Plot.frompref()
        sp = plot.subplots[int(subplot)-1]
        line = sp.lines[int(line)]
        line.killcache()
    @web.expose_for(plotgroup)
    def linedatasets_json(self,subplot,line):
        web.setmime(web.mime.json)
        plot=Plot.frompref()
        sp = plot.subplots[int(subplot)-1]
        line = sp.lines[int(line)]
        session = db.Session()
        datasets = line.getdatasets(session)
        res = web.as_json(datasets)
        session.close()
        return res
    @web.expose_for(plotgroup)
    def export_csv(self,subplot,line):
        plot = Plot.frompref()
        sp = plot.subplots[int(subplot)-1]
        line = sp.lines[int(line)]
        web.setmime(web.mime.csv)
        io = StringIO()
        line.export_csv(io,plot.startdate,plot.enddate)
        io.seek(0)
        return io        
    @web.expose_for(plotgroup)
    def clf(self):
        plot = Plot.frompref()
        plot.killcache()
        plot = Plot()
        plot.topref()
    @web.expose_for(plotgroup)
    def changeplot(self,**kwargs):
        try:
            start = web.parsedate(kwargs.get('start'))
            end = web.parsedate(kwargs.get('end'))
            plot = Plot.frompref()
            if start<plot.startdate or end>plot.enddate:
                plot.killcache()
            plot.startdate = start
            plot.enddate = end
            plot.size = float(kwargs.get('width'))/100., float(kwargs.get('height'))/100.
            plot.rows,plot.columns=int(kwargs.get('rows')),int(kwargs.get('columns'))
            plot.createtime = web.formatdatetime()
            plot.topref()
        except:
            return traceback()
        