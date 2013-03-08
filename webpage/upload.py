# -*- coding:utf-8 -*-

'''
Created on 15.02.2012

@author: philkraf
'''

import lib as web
from os import path as op
import os
from traceback import format_exc as traceback
from genshi import escape, Markup
from auth import group, expose_for
datapath=web.abspath('datafiles')
home = web.abspath('.')
try:
    import grp
    osgroup = gid = grp.getgrnam("users").gr_gid
except ImportError:
    osgroup = None

class Path(object):
    def __init__(self,abspath):
        self.absolute = op.realpath(abspath)
        self.name = op.relpath(self.absolute,datapath).replace('\\','/')
        self.basename=op.basename(self.absolute)
        if op.isdir(self.absolute):
            self.href='/download?dir=%s' % self.name
        else:
            self.href = '/' + op.relpath(self.absolute,home).replace('\\','/')
    def __nonzero__(self):
        return op.exists(self.absolute)
    def __str__(self):
        return self.name
    def formatsize(self):
        size = op.getsize(self.absolute)
        unit = 0
        units = "B KB MB GB".split()
        while size>1024 and unit<3:
            size = size/1024.
            unit +=1
        return "%5.4g %s" % (size,units[unit])
         
    def __cmp__(self,other):
        return cmp(u'%s' % self,u'%s' % other)
    
    def __add__(self,fn):
        return Path(op.join(self.absolute,fn))      
    def setownergroup(self,gid=None):
        gid = gid or osgroup
        if gid and hasattr(os,'chown'):
            os.chown(self.absolute,-1,gid)
        
    def make(self):
        os.makedirs(self.absolute)
    def breadcrumbs(self):
        res = [self]
        p = op.dirname(self.absolute)
        while datapath in p:
            res.insert(0, Path(p))
            p = op.dirname(p)
        return res
    def child(self,filename):
        return Path(op.join(self.absolute,filename))
    def isdir(self):
        return op.isdir(self.absolute)
    def isfile(self):
        return op.isfile(self.absolute)
    def exists(self):
        return op.exists(self.absolute)
    def listdir(self):
        return os.listdir(self.absolute)
    def up(self):
        return op.dirname(self.name)

class DBImportPage(object):
    exposed=True
    
    def logimport(self,filename,kwargs):
        import dataimport.importlog as il
        absfile = web.abspath(filename.strip('/'))
        path=Path(absfile)
        li = il.LogbookImport(absfile,web.user())
        logs,cancommit = li('commit' in kwargs)
        if 'commit' in kwargs and cancommit:
            raise web.HTTPRedirect('/download?dir=' + escape(path.up()))
        else:
            return web.render('logimport.html',filename=path,
                              logs=logs,cancommit=cancommit,
                              error='').render('html',doctype='html')
        
    def datasetimport(self,filename,kwargs):
        import dataimport.importlog as il
        absfile = web.abspath(filename.strip('/'))
        path=Path(absfile)
        ri = il.RecordImport(absfile,web.user())
        logs,cancommit = ri('commit' in kwargs)
        if 'commit' in kwargs and cancommit:
            raise web.HTTPRedirect('/download?dir=' + escape(path.up()))
        else:
            return web.render('logimport.html',filename=path,
                              logs=logs,cancommit=cancommit,
                              error='').render('html',doctype='html')
    
    def instrumentimport(self,filename,kwargs):
        path = Path(web.abspath(filename.strip('/')))
        import dataimport as di
        startdate = kwargs.get('startdate')
        enddate = kwargs.get('enddate')
        siteid = web.conv(int,kwargs.get('site'))
        instrumentid = web.conv(int,kwargs.get('instrument'))
        config=di.getconfig(path.absolute)
        if config:
            config.href = Path(config.filename).href
        if startdate:
            startdate = web.parsedate(startdate)
        if enddate:
            enddate = web.parsedate(enddate)
        stats = gaps = datasets = None
        if startdate and enddate:
            gaps=[(startdate,enddate)]
        if siteid and (instrumentid or config):
            absfile = web.abspath(filename.strip('/'))
            if 'loadstat' in kwargs:
                stats = di.importfilestats(absfile, web.user(), siteid, instrumentid, startdate, enddate)
                startdate = min(v.start for v in stats.itervalues())
                enddate = max(v.end for v in stats.itervalues())
            if 'importdb' in kwargs and startdate and enddate:
                gaps=None
                datasets=di.importfile(absfile, web.user(), siteid, instrumentid, startdate, enddate)
            else:
                gaps = di.finddateGaps(siteid, instrumentid, startdate, enddate) 
                    

        error=''        
        return web.render('dbimport.html',di=di,error=error,filename=filename,instrumentid=instrumentid,dirlink=path.up(),
                          siteid=siteid,gaps=gaps,stats=stats,datasets=datasets,config=config).render('html',doctype='html')

    @expose_for(group.editor)
    def index(self,filename=None,**kwargs):
        if not filename:
            raise web.HTTPRedirect('/download/')
        
        # If the file ends with log.xls, import as log list
        if filename.endswith('log.xls'):
            return self.logimport(filename, kwargs)
        # if the file starts with dataset-, import as single dataset
        elif 'dataset-' in filename:
            return self.datasetimport(filename, kwargs)
        # else import as instrument file
        else:
            return self.instrumentimport(filename, kwargs)


            


class DownloadPage(object):
    exposed=True
    to_db = DBImportPage()
    @expose_for(group.logger)
    def index(self,dir='',error='',**kwargs):
        path = Path(op.join(datapath,dir))
        print path.absolute,datapath,dir
        files=[]
        directories=[]
        if path.isdir():            
            for fn in path.listdir():
                if not fn.startswith('.'):
                    child = path.child(fn)
                    if child.isdir():
                        directories.append(child)
                    elif child.isfile():
                        files.append(child)    
            files.sort()
            directories.sort()
        else:
            error='%s is not a valid directory'
        return web.render('download.html',error=error,files=files,directories=directories,
                      curdir=path).render('html',doctype='html')

    @expose_for(group.editor)
    def upload(self,dir,datafile,**kwargs):
        error=''
        fn=''
        if datafile:
            path=Path(op.join(datapath,dir))
            if not path:
                path.make()
            fn = path + datafile.filename
            if fn and not 'overwrite' in kwargs:
                error="'%s' exists already, if you want to overwrite the old version, check allow overwrite" % fn.name
            else:
                try:
                    fout = file(fn,'wb')
                    while True:
                        data = datafile.file.read(8192)
                        if not data:
                            break
                        fout.write(data)
                    fout.close()
                    fn.setownergroup()
                except:
                    error=traceback()
        if "uploadimport" in kwargs and not error:
            url= '/download/to_db?filename='+escape(fn.href)
        else:
            url = '/download?dir='+escape(dir)
            if error: url+='&error='+escape(error)
        raise web.HTTPRedirect(url)
    @expose_for(group.editor)
    def newfolder(self,dir,newfolder):
        error=''
        if newfolder:
            try:
                path=Path(op.join(datapath,dir,newfolder))
                if not path:
                    path.make()
                    path.setownergroup()
                else:
                    error="Folder %s exists already!" % newfolder
            except:
                error=traceback()
        else:
            error='Forgotten to give your new folder a name?'
        url = '/download?dir='+escape(dir)
        if error: url+='&error='+escape(error)
        return self.index(dir=dir,error=error)

    
 
        
            
    
if __name__=='__main__':
    class Root:
        download=DownloadPage()
    web.start_server(Root(), autoreload=False, port=8081)

        
        
