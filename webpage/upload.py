'''
Created on 15.02.2012

@author: philkraf
'''

import lib
from os import path as op
import os
from traceback import format_exc as traceback
from genshi import escape

datapath=lib.abspath('datafiles')
home = lib.abspath('.')


class Path(object):
    def __init__(self,abspath):
        self.absolute = op.realpath(abspath)
        self.href = '/' + op.relpath(self.absolute, home).replace('\\','/')
        if op.isdir(self.absolute):
            self.href=self.href.replace('datafiles','download')
        self.name = op.relpath(self.absolute,datapath).replace('\\','/')
        self.basename=op.basename(abspath)
    def __str__(self):
        return self.name
    def __cmp__(self,other):
        return cmp(str(self),str(other))

class DownloadPage(object):
    exposed=True  
    @lib.expose
    @lib.output('download.html')    
    def default(self,directory='',error='',datafile=None,newname=None, **kwargs):
        path = op.join(datapath,directory)
        files=[]
        error=''
        directories=[]
        for fn in os.listdir(path):
            abspath = op.join(path,fn)
            if op.isdir(abspath):
                directories.append(Path(abspath))
            elif op.isfile(abspath):
                files.append(Path(abspath))    

        if datafile:
            if not op.exists(path):
                os.makedirs(path)
            if newname:
                fn = os.path.join(path,newname)
            else:
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
                fout.close()
        return lib.render(error=error,files=files,directories=directories,curdir=directory)
    
    
    
if __name__=='__main__':
    class Root:
        download=DownloadPage()
    lib.start_server(Root(), autoreload=False, port=8081)

        
        
