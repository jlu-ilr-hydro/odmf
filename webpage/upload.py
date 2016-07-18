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
from cStringIO import StringIO

from dataimport import ManualMeasurementsImport
from dataimport.base import ImportDescription, LogImportDescription
from dataimport.importlog import LogbookImport
from tools import Path

import conf
datapath = web.abspath('datafiles')
home = web.abspath('.')


class DBImportPage(object):
    exposed = True
    
    def logimport(self, filename, kwargs, import_with_class=LogbookImport):
        """

        :param filename:
        :param kwargs:
        :param import_with_class:
        :return:
        """
        import dataimport.importlog as il

        absfile = web.abspath(filename.strip('/'))
        path = Path(absfile)
        config = None
        if import_with_class == ManualMeasurementsImport:
            config = LogImportDescription.from_file(path.absolute)
            print "path = %s;\nabsfile = %s" % (path, absfile)
        li = import_with_class(absfile, web.user(), config=config)
        logs, cancommit = li('commit' in kwargs)  # TODO: Sometimes this is causing a delay
        # TODO: REFACTORING FOR MAINTAINABILITY

        if 'commit' in kwargs and cancommit:
            raise web.HTTPRedirect('/download?dir=' + escape(path.up()))
        else:
            return web.render('logimport.html', filename=path, logs=logs,
                              cancommit=cancommit, error='')\
                .render('html', doctype='html')

    def mmimport(self, filename, kwargs):
        """

        :param filename:
        :param kwargs:
        :return:
        """
        return self.logimport(filename, kwargs, import_with_class=ManualMeasurementsImport)
        
    def instrumentimport(self, filename, kwargs):
        """
        Loads instrument data using a .conf file
        """

        # Error streams
        errorstream = StringIO()

        # TODO: Major refactoring of this code logic, when to load gaps, etc.
        path = Path(web.abspath(filename.strip('/')))
        print "path = %s" % path
        import dataimport as di
        error = web.markdown(di.checkimport(path.absolute))
        startdate = kwargs.get('startdate')
        enddate = kwargs.get('enddate')
        siteid = web.conv(int, kwargs.get('site'))
        instrumentid = web.conv(int, kwargs.get('instrument'))
        config = di.getconfig(path.absolute)

        if not config:
            errorstream.write("No config available. Please provide a config for"
                              " computing a decent result.")

        if config:
            valuetype = [e.valuetype for e in config.columns]

        if config:
            config.href = Path(config.filename).href

        if startdate:
            startdate = web.parsedate(startdate)

        if enddate:
            enddate = web.parsedate(enddate)

        stats = gaps = datasets = None
        sites = []
        possible_datasets = []

        if startdate and enddate:
            gaps = [(startdate, enddate)]

        if siteid and (instrumentid or config):
            absfile = web.abspath(filename.strip('/'))
            adapter = di.get_adapter(absfile, web.user(), siteid, 
                                     instrumentid, startdate, enddate)
            adapter.errorstream = errorstream
            if 'loadstat' in kwargs:
                stats = adapter.get_statistic()
                startdate = min(v.start for v in stats.itervalues())
                enddate = max(v.end for v in stats.itervalues())
            if 'importdb' in kwargs and startdate and enddate:
                gaps = None
                datasets = di.importfile(absfile, web.user(), siteid,
                                         instrumentid, startdate, enddate)
            else:
                gaps = di.finddateGaps(siteid, instrumentid, valuetype,
                                       startdate, enddate)
                error = adapter.errorstream.getvalue()

            adapter.errorstream.close()
        return web.render('dbimport.html', di=di, error=error,
                          filename=filename, instrumentid=instrumentid,
                          dirlink=path.up(), siteid=siteid, gaps=gaps,
                          stats=stats, datasets=datasets, config=config,
                          #mmimport=isinstance(config, di.mm.ImportManualMeasurementsDescription),
                          sites=sites, possible_datasets=possible_datasets)\
            .render('html', doctype='html')

    @expose_for(group.editor)
    def index(self, filename=None, **kwargs):
        if not filename:
            raise web.HTTPRedirect('/download/')

        from cherrypy import log

        print filename

        print filename.endswith('log.xls')

        print ManualMeasurementsImport.extension_fits_to(filename)

        # else import as instrument file
        if ManualMeasurementsImport.extension_fits_to(filename):
            log("Import with class %s" % ManualMeasurementsImport.__name__)
            return self.mmimport(filename, kwargs)
        # If the file ends with log.xls, import as log list
        elif filename.endswith('log.xls'):
            log("Import with logimport")
            return self.logimport(filename, kwargs)

        else:
            log("Import with instrumentimport")
            return self.instrumentimport(filename, kwargs)



class DownloadPage(object):
    exposed=True
    to_db = DBImportPage()

    @expose_for(group.logger)
    def index(self, dir='', error='', **kwargs):
        path = Path(op.join(datapath, dir))
        files = []
        directories = []
        if path.isdir() and path.is_legal:            
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
            error='%s is not a valid directory' % dir
        return web.render('download.html', error=error, files=files,
                          directories=directories, curdir=path,
                          max_size=conf.CFG_UPLOAD_MAX_SIZE)\
            .render('html', doctype='html')

    @expose_for(group.editor)
    def upload(self,dir,datafile,**kwargs):
        error=''
        fn=''
        if datafile:
            path=Path(op.join(datapath,dir))
            if not path:
                path.make()
            fn = path + datafile.filename
            if not fn.is_legal:
                error="'%s' is not legal"
            if fn and not 'overwrite' in kwargs:
                error="'%s' exists already, if you want to overwrite the old version, check allow overwrite" % fn.name
            else:
                try:
                    fout = file(fn.absolute,'wb')
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

    @expose_for(group.logger)
    def saveindex(self,dir,s):
        """Saves the string s to index.html
        """
        path = Path(op.join(datapath,dir,'index.html'))
        s=s.replace('\r','')
        f=file(path.absolute,'wb')
        f.write(s)
        f.close()   
        return web.markdown(s)

    @expose_for()
    def getindex(self,dir):
        index = Path(op.join(datapath,dir,'index.html'))
        io=StringIO()
        if index.exists():
            io.write(file(index.absolute).read())
        imphist = Path(op.join(datapath,dir,'.import.hist'))
        if imphist.exists():
            io.write('\n')
            for l in file(imphist.absolute):
                ls = l.split(',',3)
                io.write(' * file:%s/%s imported by user:%s at %s into %s\n' % tuple([imphist.up()]+ls))
        return web.markdown(io.getvalue())

    @expose_for(group.editor)
    def newfolder(self, dir, newfolder):
        error = ''
        if newfolder:
            if ' ' in newfolder:
                error = "The folder name may not include a space!"
            else:
                try:
                    path = Path(op.join(datapath, dir, newfolder))
                    if not path:
                        path.make()
                        path.setownergroup()
                    else:
                        error = "Folder %s exists already!" % newfolder
                except:
                    error = traceback()
        else:
            error = 'Forgotten to give your new folder a name?'
        url = '/download?dir=' + escape(dir)
        if error: url += '&error=' + escape(error)
        return self.index(dir=dir, error=error)

    # @TODO: Is the usage of a dir post variable safe through foreign access?
    @expose_for(group.admin)
    def removefile(self, dir, filename):
        path = Path(op.join(datapath, filename))
        error = ''

        if path.exists():
            try:
                os.remove(path.absolute)
            except:
                error = "Could not delete the file. A good reason would be a mismatch of user rights on the server " \
                        "file system"
        else:
            error = "File not found. Is it already deleted?"

        return self.index(dir=dir, error=error)

if __name__=='__main__':
    class Root:
        download=DownloadPage()
    web.start_server(Root(), autoreload=False, port=8081)
