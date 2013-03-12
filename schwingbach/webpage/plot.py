'''
Created on 01.10.2012

@author: philkraf
'''
import sys
import matplotlib

matplotlib.use('Agg', warn=False)
if sys.platform=='win32':
    matplotlib.rc('font', **{'sans-serif' : 'Arial',
                           'family' : 'sans-serif'})

import pylab as plt
import db
from traceback import format_exc as traceback
from datetime import datetime, timedelta
from cStringIO import StringIO

t0 = datetime(1,1,1)
nan = plt.log(-1)
def date2num(t):
    if t is None:
        return nan
    else:
        return (t-t0).total_seconds()/86400 + 1.0    
def asdict(obj):
    if hasattr(obj,'__jdict__'):
        return obj.__jdict__()
    elif (not type(obj) is dict) and hasattr(obj,'__iter__'):
        return [asdict(o) for o in obj]
    elif hasattr(obj,'isoformat'):
        return obj.isoformat()
    else:
        return obj
class Line(object):
    def __init__(self,subplot,valuetype,site,instrument=None,style='',
                 transformation=None):
        self.subplot=subplot
        self.style=style
        self.t = None
        self.v = None
        session=db.Session()
        self.valuetype=session.query(db.ValueType).get(int(valuetype)) if valuetype else None
        self.site=session.query(db.Site).get(int(site)) if site else None
        self.instrument = session.query(db.Datasource).get(int(instrument)) if instrument else None
        session.close()
        self.transformation=transformation
    def load(self,startdate=None,enddate=None):
        self.v = None
        self.t = None
        session=db.Session()
        error=''
        try:
                
            datasets = session.query(db.Dataset).filter(db.Dataset.valuetype==self.valuetype,
                                                        db.Dataset.site==self.site)
            if self.instrument:
                datasets=datasets.filter(db.Dataset.source == self.instrument)

            # Get records
            records = session.query(db.Record)
            # filter records by dataset
            dsids = [ds.id for ds in datasets]
            records = records.filter(db.Record._dataset.in_(dsids),~db.Record.is_error)
            # Filter records by date
            if startdate:
                records = records.filter(db.Record.time>=startdate)
            if enddate:
                records = records.filter(db.Record.time<=enddate)
            
            # Order records by time
            records=records.order_by(db.Record.time)
            count = records.count()
            
            # Get transformation
            if self.transformation:
                trans = lambda x: eval(self.transformation)
            else:
                trans = lambda x: x
            
            # calibrate a (time,value,dataset) tuple
            calicoeff=dict((ds.id,(ds.calibration_slope,ds.calibration_offset)) for ds in datasets)
            calibrate = lambda r: r[1] * calicoeff[r[2]][0] + calicoeff[r[2]][1]
            
            # Allocate memory for timeseries
            if not self.t or len(self.t)!=count:        
                self.t = plt.zeros(shape=count,dtype=float)
            if not self.v or len(self.v)!=count:
                self.v = plt.zeros(shape=count,dtype=float)
            # Set values in timeseries
            for i,r in enumerate(records.values('time','value','dataset')):
                self.t[i] = date2num(r[0])
                self.v[i] = nan if r[1] is None else calibrate(r) 
            self.v = trans(self.v)    
            
        except:
            error = traceback()
        finally:
            session.close()
        return error
        
    def draw(self,ax,startdate=None,enddate=None):
        if (self.t is None or self.v is None or len(self.t)==0 or len(self.v)!=len(self.t) or 
            date2num(startdate)<self.t[0] or date2num(enddate)>self.t[-1]):
            self.load(startdate,enddate)
        # Do the plot 
        label = u'%s at site %s' % (self.valuetype.name,self.site)
        if self.style:
            ax.plot_date(self.t,self.v,self.style,label=label)
        else:
            ax.plot_date(self.t,self.v,c=self.color,marker=self.marker,ls=self.line,label=label)
    def export_csv(self,stream,startdate=None,enddate=None):
        if (self.t is None or self.v is None or len(self.t)==0 or len(self.v)!=len(self.t) or 
            date2num(startdate)<self.t[0] or date2num(enddate)>self.t[-1]):
            self.load(startdate,enddate)
        t0 = plt.date2num(datetime(1899,12,30))
        stream.write('Time,' + str(self.valuetype) + '\n') 
        for t,v in zip(self.t-t0,self.v):
            stream.write('%f,%f\n' % (t,v))
        
    def __jdict__(self):
        return dict(valuetype=self.valuetype.id if self.valuetype else None,
                    site=self.site.id if self.site else None,
                    instrument=self.instrument.id if self.instrument else None,
                    style=self.style,transformation=self.transformation)
    @classmethod
    def fromdict(cls,subplot,d):
        return cls(subplot,valuetype=d.get('valuetype'),site=d.get('site'),instrument=d.get('instrument'),style=d.get('style'),
                   transformation=d.get('transformation'))
    def __str__(self):
        if self.instrument:
            return '%s at %s using %s (%s)' % (self.valuetype, self.site,self.instrument,self.style)
        else:
            return '%s at %s (%s)' % (self.valuetype, self.site,self.style)
    def __repr__(self):
        return "plot.Line(%s@%s,'%s')" % (self.valuetype,self.site,self.style)
    
class Subplot(object):
    def __init__(self,plot,position=1):
        self.plot=plot
        self.position=position
        self.lines=[]
        self.ylim = None
    def addline(self,valuetype,site,instrument=None,style=''):
        self.lines.append(Line(self,valuetype=valuetype,site=site,instrument=instrument,style=style))
        self.plot.createtime = web.formatdate()
        return self
    def draw(self,figure):
        ax = figure.axes[self.position-1]
        for l in self.lines:
            l.draw(ax,self.plot.startdate,self.plot.enddate)
        if self.ylim:
            plt.ylim(self.ylim)
        plt.xlim(date2num(self.plot.startdate),date2num(self.plot.enddate))
        ax.grid()
        ax.legend(loc=0)
        if self.lines:
            l=self.lines[0]
            plt.ylabel(u'%s [%s]' % (l.valuetype.name,l.valuetype.unit))
    def __jdict__(self):
        return dict(lines=asdict(self.lines),
                    ylim=self.ylim,position=self.position)
    @classmethod
    def fromdict(cls,plot,d):
        res = cls(plot=plot,position=d.get('position'))
        res.ylim = d.get('ylim')
        if 'lines' in d:
            for ld in d.get('lines'):
                res.lines.append(Line.fromdict(res,ld))
        return res
                   
class Plot(object):
    def __init__(self,size=(6.0,4.8),columns=1,rows=1,startdate=None,enddate=None):
        self.startdate=startdate or datetime.today() - timedelta(days=365)
        self.enddate=enddate or datetime.today()
        self.size=size
        self.rows, self.columns = rows,columns
        self.subplots=[]
        self.createtime = web.formatdatetime()
    def addtimeplot(self):
        sp = Subplot(self,len(self.subplots)+1)
        self.subplots.append(sp)
        if self.rows * self.columns < len(self.subplots):
            self.rows += 1
        self.createtime = web.formatdatetime()
        return sp
    def draw(self,format='png'):
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
    def __jdict__(self):
        return dict(size=self.size,rows=self.rows,columns=self.columns,
                    startdate=self.startdate,enddate=self.enddate,
                    subplots=asdict(self.subplots))
    @classmethod
    def fromdict(cls,d):
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
        pref=Preferences()
        if 'plot' in pref:    
            return cls.fromdict(pref['plot'])
        else:
            if createplot:
                plot=Plot()
                plot.topref()
                return plot
            return
    @classmethod
    def fromsession(cls):
        plot = web.cherrypy.session.get('plot')
        if not plot:
            plot = cls.frompref(createplot=True)
        return plot
    
    def topref(self):
        pref = Preferences()
        pref['plot'] = asdict(self)
    def tosession(self):
        web.cherrypy.session['plot'] = self
        self.topref()    
   
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
        plot = Plot.fromsession()
        return plot.draw()
    @web.expose_for(plotgroup)
    def image_pdf(self,**kwargs):
        web.setmime(web.mime.pdf)
        plot = Plot.fromsession()
        return plot.draw(format='pdf')
    
    @web.expose_for(plotgroup)
    def addsubplot(self):
        try:
            plot = Plot.fromsession()
            plot.addtimeplot()
            plot.topref()
        except:
            return traceback()
    @web.expose_for(plotgroup)
    def removesubplot(self,subplotid):
        try:
            plot = Plot.fromsession()
            id = int(subplotid)
            sp = plot.subplots.pop(id-1)
            plot.tosession()
            return
        except:
            return traceback()
    
    @web.expose_for(plotgroup)
    def addline(self,subplot,valuetypeid,siteid,instrumentid,style):
        try:
            plot = Plot.fromsession()
            spi = int(subplot)
            if spi>len(plot.subplots):
                sp=plot.addtimeplot()
            else:
                sp = plot.subplots[spi-1]         
            sp.addline(web.conv(int,valuetypeid),web.conv(int,siteid),web.conv(int,instrumentid),style=style)
            plot.tosession()
        except:
            return traceback()
    
    @web.expose_for(plotgroup)
    def removeline(self,subplot,line):
        plot = Plot.fromsession()
        sp = plot.subplots[int(subplot)-1]
        del sp.lines[int(line)]
        plot.tosession()
    @web.expose_for(plotgroup)
    def export_csv(self,subplot,line):
        plot = Plot.fromsession()
        sp = plot.subplots[int(subplot)-1]
        line = sp.lines[int(line)]
        web.setmime(web.mime.csv)
        io = StringIO()
        line.export_csv(io,plot.startdate,plot.enddate)
        io.seek(0)
        return io        
    @web.expose_for(plotgroup)
    def clf(self):
        plot = Plot()
        plot.tosession()
    @web.expose_for(plotgroup)
    def changeplot(self,**kwargs):
        try:
            start = web.parsedate(kwargs.get('start'))
            end = web.parsedate(kwargs.get('end'))
            plot = Plot.fromsession()
            plot.startdate = start
            plot.enddate = end
            plot.size = float(kwargs.get('width'))/100., float(kwargs.get('height'))/100.
            plot.rows,plot.columns=int(kwargs.get('rows')),int(kwargs.get('columns'))
            plot.createtime = web.formatdatetime()
            plot.tosession()
        except:
            return traceback()
        