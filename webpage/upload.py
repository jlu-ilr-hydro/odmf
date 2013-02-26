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
from auth import users, require, member_of, has_level, group, expose_for

datapath=web.abspath('datafiles')
home = web.abspath('.')


class Path(object):
    def __init__(self,abspath):
        self.absolute = op.realpath(abspath)
        self.name = op.relpath(self.absolute,datapath).replace('\\','/')
        self.basename=op.basename(self.absolute)
        if op.isdir(self.absolute):
            self.href='/download?dir=%s' % self.name
        else:
            self.href = '/' + op.relpath(self.absolute,home).replace('\\','/')
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

class DownloadPage(object):
    exposed=True
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
            path=op.realpath(op.join(datapath,dir))
            if not op.exists(path):
                os.makedirs(path)
            fn = os.path.join(path,str(datafile.filename))
            if op.exists(fn):
                short=op.relpath(fn, datapath)
                error="'%s' exists already, please use another filename or another directory" % short
            else:
                try:
                    fout = file(fn,'wb')
                    while True:
                        data = datafile.file.read(8192)
                        if not data:
                            break
                        fout.write(data)
                    fout.close()
                    os.system('chown :users ' + fn)
                except:
                    error=traceback()
        if "uploadimport" in kwargs and not error:
            url= '/download/to_db?filename='+escape(fn)
        else:
            url = '/download?dir='+escape(dir)
            if error: url+='&error='+escape(error)
        raise web.HTTPRedirect(url)
    @expose_for(group.editor)
    def newfolder(self,dir,newfolder):
        error=''
        if newfolder:
            try:
                path=op.realpath(op.join(datapath,dir,newfolder))
                if not op.exists(path):
                    os.makedirs(path)
                else:
                    error="Folder %s exists already!" % newfolder
            except:
                error=traceback()
        else:
            error='Forgotten to give your new folder a name?'
        url = '/download?dir='+escape(dir)
        if error: url+='&error='+escape(error)
        return self.index(dir=dir,error=error)

    @expose_for(group.supervisor)
    def to_db(self,filename=None,**kwargs):
        if not filename:
            raise web.HTTPRedirect('.')
        # If the file ends with log.xls, import as log list
        if filename.endswith('log.xls'):
            import dataimport.importlog as il
            absfile = web.abspath(filename.strip('/'))
            path=Path(absfile)
            li = il.LogbookImport(absfile,web.user())
            logs,cancommit = li('commit' in kwargs)
            return web.render('logimport.html',filename=path,
                              logs=logs,cancommit=cancommit,
                              error='').render('html',doctype='html')

        # if it doesn't import as instrument file
        else:
            import dataimport as di
            startdate = kwargs.get('startdate')
            enddate = kwargs.get('enddate')
            siteid = web.conv(int,kwargs.get('site'))
            instrumentid = web.conv(int,kwargs.get('instrument'))
            if startdate:
                startdate = web.parsedate(startdate)
            if enddate:
                enddate = web.parsedate(enddate)
            stats = gaps = datasets = None
            
            if startdate and enddate:
                gaps=[(startdate,enddate)]
            if siteid and instrumentid:
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
            return web.render('dbimport.html',di=di,error=error,filename=filename,instrumentid=instrumentid,
                              siteid=siteid,gaps=gaps,stats=stats,datasets=datasets).render('html',doctype='html')
    
 
        
            
    
if __name__=='__main__':
    class Root:
        download=DownloadPage()
    web.start_server(Root(), autoreload=False, port=8081)

        
        
