# -*- coding:utf-8 -*-

'''
Created on 15.02.2012

@author: philkraf
'''

import lib as web
from os import path as op
import os
from traceback import format_exc as traceback
from genshi import escape

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
        return "%0.1f %s" % (size,units[unit])
         
    def __cmp__(self,other):
        return cmp(str(self),str(other))

class DownloadPage(object):
    exposed=True  
    @web.expose
    def index(self,dir='',error='',**kwargs):
        path = op.join(datapath,dir)
        relpath = op.relpath(path, datapath)
        files=[]
        error=''
        directories=[]
        if op.isdir(path):            
            for fn in os.listdir(path):
                if not fn.startswith('.'):
                    abspath = op.join(path,fn)
                    if op.isdir(abspath):
                        directories.append(Path(abspath))
                    elif op.isfile(abspath):
                        files.append(Path(abspath))    
            files.sort()
            directories.sort()
        else:
            error='%s is not a valid directory'
        return web.render('download.html',error=error,files=files,directories=directories,
                      curdir=relpath).render('html',doctype='html')
    @web.expose
    def upload(self,dir,datafile):
        error=''
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
                except:
                    error=traceback()
        url = '/download?dir='+escape(dir)
        if error: url+='&error='+escape(error)
        raise web.HTTPRedirect(url)
    
    
if __name__=='__main__':
    class Root:
        download=DownloadPage()
    web.start_server(Root(), autoreload=False, port=8081)

        
        
