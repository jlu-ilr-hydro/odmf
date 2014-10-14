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
from matplotlib.ticker import MaxNLocator
import numpy as np
import db
from traceback import format_exc as traceback
from datetime import datetime, timedelta
from cStringIO import StringIO
import time
from base64 import b64encode
from pandas import to_datetime, TimeGrouper
import json
from glob import iglob
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
    def __init__(self,subplot,valuetype,site,instrument=None,level=None,style='',
                 transformation=None,usecache=False,aggregatefunction='mean'):
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
        self.level = level
        session.close()
        self.transformation=transformation
        self.usecache = usecache
        self.aggregatefunction=aggregatefunction
    def getdatasets(self,session):
        """
        Loads the datasets for this line
        """
        datasets = session.query(db.Dataset).filter(db.Dataset.valuetype==self.valuetype,
                                                    db.Dataset.site==self.site, 
                                                    db.Dataset.start<self.subplot.plot.enddate,
                                                    db.Dataset.end>self.subplot.plot.startdate,
                                                    )
        if self.instrument:
            datasets=datasets.filter(db.Dataset.source == self.instrument)
        if not self.level is None:
            datasets=datasets.filter(db.Dataset.level == self.level)
        return datasets.order_by(db.Dataset.start).all()
    def getcachename(self,t_or_v):
        plot = self.subplot.plot
        path = plot.getpath()
        spno = self.subplot.position
        lineno = self.subplot.lines.index(self)
        return '%s.sp%i.l%i.%s.npy' % (path,spno,lineno,t_or_v)
    def hascache(self):
        if not self.usecache: return False
        now = time.time()
        tname = self.getcachename('t')
        vname = self.getcachename('v')
        return (os.path.exists(tname) and 
                os.path.exists(vname) and
                now - os.path.getmtime(tname) < 600)
    def killcache(self):
        for s in 'tv':
            if os.path.exists(self.getcachename(s)):
                os.remove(self.getcachename(s))
    def aggregate(self):
        session=db.Session()
        error=''
        start=self.subplot.plot.startdate
        end=self.subplot.plot.enddate
        # Get values from session as a pandas.Series
        try:
            datasets=self.getdatasets(session)
            group = db.DatasetGroup([ds.id for ds in datasets], start, end)
            series = group.asseries(session)
        finally:
            session.close()
        # Change series.index to datetime64 type
        t0 = plt.date2num(datetime(1970,1,1))
        series.index = to_datetime((series.index.values - t0),unit='D')
        # Use pandas resample mechanism for aggregation
        aggseries = series.resample(self.subplot.plot.aggregate,self.aggregatefunction)
        # Rip series index and values appart and convert the datetime64 index (in ns) back to matplotlib value
        t = aggseries.index.values.astype(float)/(24*60*60*1e9) + t0
        v = aggseries.values
        return t,v
    def load(self,startdate=None,enddate=None):
        """
        Loads the records into an array
        """
        if self.subplot.plot.aggregate:
            return self.aggregate()
        else:
            if self.hascache():
                print 'Load from cache'
                t=np.fromfile(self.getcachename('t'))
                v=np.fromfile(self.getcachename('v'))
                if not (len(t)==0 or len(v)!=len(t)):
                    print ".../\./\|\...load from cache<-" + os.path.basename(self.getcachename('?'))
                    return t,v
            print ".../\./\|\...load from database->" + os.path.basename(self.getcachename('?'))
            session=db.Session()
            error=''
            start=self.subplot.plot.startdate
            end=self.subplot.plot.enddate
            try:
                datasets=self.getdatasets(session)
                group = db.DatasetGroup([ds.id for ds in datasets], start, end)
                t,v = group.asarray(session)
            finally:
                session.close()
            if self.usecache:
                t.tofile(self.getcachename('t'))
                v.tofile(self.getcachename('v'))
            print 'Load complete'
            #except Exception as e:
            #    raise e
            #finally:
            print "size(v)=", v.size,"mean(v)=",v[np.isnan(v)==False].mean(),"std(v)=",v[np.isnan(v)==False].std()
            print "size(t)=", t.size,"min(t)=",plt.num2date(t.min()),"max(t)=",plt.num2date(t.max())
            return t,v
    def draw(self,ax,startdate=None,enddate=None):
        """
        Draws the line to the matplotlib axis ax
        """
        try:
            t,v = self.load(startdate,enddate)
            # Do the plot 
            label = unicode(self)
            ax.plot_date(t,v,self.style or 'k-',label=label)
        except ValueError:
            print 'Zero-size Array'

    
    def export_csv(self,stream,startdate=None,enddate=None):
        """
        Exports the line as csv file
        """
        t,v = self.load(startdate, enddate)
        # Epoch for excel dates
        stream.write(codecs.BOM_UTF8)
        stream.write('Time,' + unicode(self.valuetype).encode('UTF-8') + '\n') 
        for t,v in zip(plt.num2date(t),v):
            stream.write('%f,%f\n' % (t,v))
    def export_json(self,stream,startdate=None,enddate=None):
        t,v = self.load(startdate, enddate)
        # Unix-Epoch 
        t0 = plt.date2num(datetime(1970,1,1))
        # Flot expects ms since epoch -> (t-t0)*24*60*60*1000
        stream.write('[')
        for T,V in zip((t-t0)*24*60*60*1000,v):
            stream.write('[%f,%f],' % (T,V))
        stream.write('[null,null]]')
        
            
    def __jdict__(self):
        """
        Returns a dictionary of the line
        """
        return dict(valuetype=self.valuetype.id if self.valuetype else None,
                    site=self.site.id if self.site else None,
                    instrument=self.instrument.id if self.instrument else None,
                    level=self.level,
                    style=self.style,transformation=self.transformation, 
                    usecache=self.usecache, aggregatefunction=self.aggregatefunction )
    @classmethod
    def fromdict(cls,subplot,d):
        """
        Creates the line element from a dictionary (for loading from session)
        """
        return cls(subplot,valuetype=d.get('valuetype'),site=d.get('site'),instrument=d.get('instrument'),style=d.get('style'),
                   transformation=d.get('transformation'),level=d.get('level'),usecache=d.get('usecache',False),
                   aggregatefunction=d.get('aggregatefunction','mean')
                   )
    def __unicode__(self):
        """
        Returns a string representation
        """
        res = u''
        if self.instrument:
            res = u'%s at #%i%s using %s' % (self.valuetype, self.site.id,
                                                 '(%gm)' % self.level if not self.level is None else '',
                                                 self.instrument.name)
        else:
            res = u'%s at #%i%s' % (self.valuetype, self.site.id,
                                      '(%gm)' % self.level if not self.level is None else '')
        if self.subplot.plot.aggregate:
            res += ' (%s/%s)' % (self.aggregatefunction,self.subplot.plot.aggregate)
        return res
    def __str__(self):
        return unicode(self).encode('utf-8',errors='replace')
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
    def addline(self,valuetype,site,instrument=None,level=None,style='',usecache=False,aggfunc='mean'):
        """
        Adds a line to the subplot
        @param valuetype: the id of a valuetype
        @param site: the id of a site
        @param instrument: the id of an instrument (can be omitted)
        @param style: the style of the line, eg 'o-k' for black line with circle markers 
        """
        self.lines.append(Line(self,valuetype=valuetype,site=site,instrument=instrument,level=level,style=style,usecache=usecache,aggregatefunction=aggfunc))
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
        ax.yaxis.set_major_locator(MaxNLocator(prune='upper'))
        ax.tick_params(axis='both', which='major', labelsize=8)

        ax.grid()
        ax.legend(loc=0,prop=dict(size=9))
        if self.lines:
            l=self.lines[0]
            plt.ylabel(u'%s [%s]' % (l.valuetype.name,l.valuetype.unit),fontsize=self.plot.args.get('ylabelfs','small'))
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
    def __init__(self,size=(6.0,4.8),columns=1,rows=1,startdate=None,enddate=None,**kwargs):
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
        self.newlineprops = None
        self.args=kwargs
        self.aggregate = ''
        self.description = ''
    def getpath(self):
        username = web.user() or 'nologin'
        return web.abspath('preferences/plots/' + username + '.' + self.name)
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
                              figsize=self.size,dpi=100,sharex=True)
        for sp in self.subplots:
            sp.draw(fig)
        fig.subplots_adjust(top=0.975,bottom=0.1,hspace=0.0)
        if was_interactive:
            plt.ion()
            plt.draw()
        elif format:
            io = StringIO()
            fig.savefig(io,format=format)
            plt.close('all')
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
                    subplots=asdict(self.subplots),newlineprops = asdict(self.newlineprops),
                    aggregate=self.aggregate,description=self.description)
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
        res.newlineprops = d.get('newlineprops')
        res.aggregate = d.get('aggregate','')
        res.description = d.get('description','')
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
    def save(self,fn):
        d = asdict(self)
        try:
            open(self.absfilename(fn),'wb').write(web.as_json(d))
        except:
            return traceback()
    @classmethod
    def load(cls,fn):
        fp = open(cls.absfilename(fn))
        plot = Plot.fromdict(json.load(fp))
        return plot
    @classmethod
    def listdir(cls):
        return [os.path.basename(fn).rsplit('.')[0]
                for fn in iglob(cls.absfilename('*'))
                ]
    @classmethod
    def killfile(cls,fn):
        if os.path.exists(cls.absfilename(fn)):
            os.remove(cls.absfilename(fn))
        else:
            return "File %s does not exist" % fn
    @classmethod
    def absfilename(cls,fn):
        return web.abspath('preferences/plots/'+fn+'.plot')
        
   
import webpage.lib as web
from webpage.preferences import Preferences
plotgroup = web.group.logger

class PlotPage(object):
    exposed=True
    @web.expose_for(plotgroup)
    def index(self,valuetype=None,site=None,error=''):
        plot=Plot.frompref(createplot=True)
        return web.render('plot.html',plot=plot,error=error).render('html')
    @web.expose_for(plotgroup)
    def loadplot(self,filename):
        try:
            plot = Plot.load(filename)
        except:
            return traceback()
        plot.topref() 
    @web.expose_for(plotgroup)
    def saveplot(self,filename,overwrite=False):
        if not filename:
            return 'No filename given'
        elif filename in Plot.listdir() and not overwrite:
            return 'Filename exists already. Choose another or delete this file'
        else:
            return Plot.frompref().save(filename)
    @web.expose_for(plotgroup)
    def deleteplotfile(self,filename):
        return Plot.killfile(filename)
        
    
    @web.expose_for(plotgroup)
    def listplotfiles(self):
        web.setmime(web.mime.json)
        return web.as_json(Plot.listdir())
    @web.expose_for(plotgroup)
    def describe(self,newdescription):
        try:
            plot = Plot.frompref(True)
            plot.description = newdescription
            plot.topref()
        except:
            return traceback()
                    
    @web.expose_for(plotgroup)
    def image_png(self,**kwargs):
        web.setmime(web.mime.png)
        plot = Plot.frompref()   
        if not plot:
            raise web.HTTPRedirect('/plot?error=No plot available')        
        return plot.draw(format='png')
    @web.expose_for(plotgroup)
    def image_pdf(self,**kwargs):
        web.setmime(web.mime.pdf)
        plot = Plot.frompref()
        if not plot:
            raise web.HTTPRedirect('/plot?error=No plot available')
        return plot.draw(format='pdf')
        
    @web.expose_for(plotgroup)
    def addsubplot(self):
        try:
            plot = Plot.frompref(createplot=True)
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
            plot = Plot.frompref(createplot=True)
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
    def addline(self,subplot,valuetypeid,siteid,instrumentid,level,style,aggfunc='mean'):
        try:
            plot = Plot.frompref(createplot=True)
            spi = int(subplot)
            if spi>len(plot.subplots):
                sp=plot.addtimeplot()
            else:
                sp = plot.subplots[spi-1]
            if valuetypeid and siteid:
                sp.addline(web.conv(int,valuetypeid),web.conv(int,siteid),web.conv(int,instrumentid),web.conv(float,level),style=style,aggfunc=aggfunc)
            else:
                return "You tried to add a line without site or value type. This is not possible"
            plot.newlineprops = None
            plot.topref()
        except:
            return traceback()
    
    @web.expose_for(plotgroup)
    def removeline(self,subplot,line,savelineprops=False):
        plot = Plot.frompref()
        sp = plot.subplots[int(subplot)-1]
        sp.lines[int(line)].killcache()
        if savelineprops:
            plot.newlineprops = sp.lines.pop(int(line))
        else:
            plot.newlineprops = None
            del sp.lines[int(line)]
        plot.topref()
    @web.expose_for(plotgroup)
    def copyline(self,subplot,line):
        plot = Plot.frompref()
        sp = plot.subplots[int(subplot)-1]
        plot.newlineprops = sp.lines[int(line)]
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
    def export_json(self,subplot,line):
        plot = Plot.frompref()
        sp = plot.subplots[int(subplot)-1]
        line = sp.lines[int(line)]
        web.setmime(web.mime.csv)
        io = StringIO()
        line.export_json(io,plot.startdate,plot.enddate)
        io.seek(0)
        return io

    @web.expose_for(plotgroup)
    def exportall_csv(self,tolerance):
        plot = Plot.frompref()
        datasetids=[]
        session=db.Session()
        for sp in plot.subplots:
            for line in sp.lines:
                datasetids.extend(ds.id for ds in line.getdatasets(session))
        session.close()
        stream = StringIO()
        from tools.exportdatasets import exportData
        exportData(stream,datasetids,plot.startdate,plot.enddate,web.conv(float,tolerance,60))
        web.setmime(web.mime.csv)
        return stream.getvalue()            
    @web.expose_for(plotgroup)
    def RegularTimeseries_csv(self,tolerance=12,interpolation=''):
        plot = Plot.frompref()
        datasetids=[]
        session=db.Session()
        lines = []
        for sp in plot.subplots:
            lines.extend(sp.lines)
            for line in sp.lines:
                datasetids.extend(ds.id for ds in line.getdatasets(session))
        session.close()
        stream = StringIO()
        from tools.ExportRegularData import createPandaDfs
        stream.write(codecs.BOM_UTF8)
        createPandaDfs(lines,plot.startdate,plot.enddate,stream,interpolationtime=interpolation,tolerance=float(tolerance)) 
        web.setmime(web.mime.csv)
        return stream.getvalue()   
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
            plot.aggregate = kwargs.get('aggregate','')
            plot.createtime = web.formatdatetime()
            plot.topref()
        except:
            return traceback()

    @web.expose
    # @web.mimetype(web.mime.png)
    def climate(self,enddate=None,days=1,site=47):
        try:
            enddate = web.parsedate(enddate)
        except: 
            enddate = datetime.now()
        days=float(days)
        site=int(site)
        startdate = enddate - timedelta(days=days)
        plot = Plot((6.,9.), columns=1, rows=6, startdate=startdate, enddate=enddate,ylabelfs='8')
        # 1 Temperature (vt=14)
        Tsp=plot.addtimeplot()
        Tsp.addline(14, site, style='r-',usecache=False)
        Tsp.addline(8,site,style='b-',usecache=False) # Water Temperature
        # 2 Rainfall
        plot.addtimeplot().addline(9,site,style='b-',usecache=False)
        # 3 Discharge
        plot.addtimeplot().addline(1,site,style='b-',usecache=False)
        # 4 Radiation
        plot.addtimeplot().addline(11,site,style='r-',usecache=False)
        # 5 rH
        plot.addtimeplot().addline(10,site,style='c-',usecache=False)
        # 6 Windspeed
        plot.addtimeplot().addline(12,site,style='k-',usecache=False)
        
        plot64 = b64encode(plot.draw(format='png'))
        
        return web.render('climateplot.html',climateplot=plot64,plot=plot).render('html')