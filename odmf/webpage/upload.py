# -*- coding:utf-8 -*-

'''
Created on 15.02.2012

@author: philkraf
'''
import time

from . import lib as web

import os
from traceback import format_exc as traceback
from io import StringIO, BytesIO
from cherrypy import log, request, HTTPError, InternalRedirect
import chardet
from cherrypy.lib.static import serve_file
from urllib.parse import urlencode
from .auth import group, expose_for

from .. import dataimport as di
from ..dataimport import ManualMeasurementsImport

from ..dataimport.importlog import LogbookImport
from ..tools import Path

from ..config import conf

datapath = conf.abspath('datafiles')

#
# Shared utility
#


def write_to_file(dest, src):
    """
    Write data of src (file in) into location of dest (filename)

    :param dest:  filename on the server system
    :param src: file contents input buffer
    :return:
    """

    fout = open(dest, 'wb')
    while True:
        data = src.read(8192)
        if not data:
            break
        fout.write(data)
    fout.close()


@web.expose
class DBImportPage(object):
    @staticmethod
    def logimport(filename, kwargs, import_with_class=LogbookImport):
        """

        :param filename:
        :param kwargs:
        :param import_with_class:
        :return:
        """
        
        t0 = time.time()

        absfile = conf.abspath(filename.strip('/'))
        path = Path(absfile)

        error = web.markdown(di.checkimport(path.absolute))

        config = None
        if import_with_class == ManualMeasurementsImport:
            config = ManualMeasurementsImport.from_file(path.absolute)
            print("path = %s;\nabsfile = %s" % (path, absfile))

        from cherrypy import log
        log("Import with class %s" % import_with_class.__name__)

        li = import_with_class(absfile, web.user(), config=config)
        # TODO: Sometimes this is causing a delay
        logs, cancommit = li('commit' in kwargs)
        # TODO: REFACTORING FOR MAINTAINABILITY

        t1 = time.time()

        log("Imported in %.2f s" % (t1 - t0))

        if 'commit' in kwargs and cancommit:
            di.savetoimports(absfile, web.user(), ["_various_as_its_manual"])
            raise web.HTTPRedirect('/download?dir=' + web.escape(path.up()))
        else:
            return web.render('logimport.html', filename=path, logs=logs,
                              cancommit=cancommit, error=error)\
                .render()

    @staticmethod
    def mmimport(filename, kwargs):
        """
        Imports a manual measurement
        :param filename:
        :param kwargs:
        :return:
        """
        return DBImportPage.logimport(filename, kwargs, import_with_class=ManualMeasurementsImport)

    @staticmethod
    def instrumentimport(filename, kwargs):
        """
        Loads instrument data using a .conf file

        Wheter 'loadstat' or 'impordb' is in kwargs, the method returns the import page with the stats or with a commit
        message

        :param filename:
        :param kwargs:
        """

        t0 = time.time()

        # Error streams
        errorstream = StringIO()

        # TODO: Major refactoring of this code logic, when to load gaps, etc.
        path = Path(conf.abspath(filename.strip('/')))
        print("path = %s" % path)
        error = web.markdown(di.checkimport(path.absolute))
        startdate = kwargs.get('startdate')
        enddate = kwargs.get('enddate')
        siteid = web.conv(int, kwargs.get('site'))
        instrumentid = web.conv(int, kwargs.get('instrument'))
        config = di.getconfig(path.absolute)
        stats = gaps = datasets = sites = possible_datasets = None

        if not config:
            errorstream.write("No config available. Please provide a config for"
                              " computing a decent result.")
        else:
            valuetype = [e.valuetype for e in config.columns]
            config.href = Path(config.filename).href
            if startdate:
                startdate = web.parsedate(startdate) or None
            if enddate:
                enddate = web.parsedate(enddate) or None


            sites = []
            possible_datasets = []

            if startdate and enddate:
                gaps = [(startdate, enddate)]

            if siteid and (instrumentid or config):
                absfile = conf.abspath(filename.strip('/'))
                adapter = di.get_adapter(absfile, web.user(), siteid,
                                         instrumentid, startdate, enddate)
                adapter.errorstream = errorstream
                if 'loadstat' in kwargs:
                    stats = adapter.get_statistic()
                    startdate = min(v.start for v in stats.values())
                    enddate = max(v.end for v in stats.values())
                if 'importdb' in kwargs and startdate and enddate:
                    gaps = None
                    datasets = di.importfile(absfile, web.user(), siteid,
                                             instrumentid, startdate, enddate)
                else:
                    gaps = di.finddateGaps(siteid, instrumentid, valuetype,
                                           startdate, enddate)
                    error = adapter.errorstream.getvalue()

                adapter.errorstream.close()

            t1 = time.time()

            log("Imported in %.2f s" % (t1 - t0))

        return web.render('dbimport.html', di=di, error=error,
                          filename=filename, instrumentid=instrumentid,
                          dirlink=path.up(), siteid=siteid, gaps=gaps,
                          stats=stats, datasets=datasets, config=config,
                          sites=sites, possible_datasets=possible_datasets)\
            .render()

    @expose_for(group.editor)
    def index(self, filename=None, **kwargs):
        if not filename:
            raise web.HTTPRedirect('/download/')

        # the lab import only fits on CFG_MANNUAL_MEASUREMENTS_PATTERN
        if ManualMeasurementsImport.extension_fits_to(filename):
            log("Import with labimport ( %s )" %
                ManualMeasurementsImport.__name__)
            return self.mmimport(filename, kwargs)
        # If the file ends with log.xls, import as log list
        elif filename.endswith('log.xls'):
            log("Import with logimport")
            return self.logimport(filename, kwargs)
        # else import as instrument file
        else:
            log("Import with instrumentimport")
            return self.instrumentimport(filename, kwargs)


class HTTPFileNotFoundError(HTTPError):
    def __init__(self, path: Path):
        super().__init__(status=404, message=f'{path.href} not found')
        self.path = path

    def get_error_page(self, *args, **kwargs):

        error = f'Resource {self.path.href} not found'

        text = web.render(
            'download.html',
            error=error, message='',
            files=[],
            directories=[],
            curdir=self.path,
            max_size=conf.upload_max_size
        ).render()

        return text.encode('utf-8')


def goto(dir, error, msg):
    web.redirect(f'{conf.root_url}/download/{dir}'.strip('.'), error=error, msg=msg)


@web.show_in_nav_for(0, 'file')
class DownloadPage(object):
    """The file management system. Used to upload, import and find files"""
    to_db = DBImportPage()

    def _cp_dispatch(self, vpath: list):
        request.params['uri'] = '/'.join(vpath)
        vpath.clear()
        return self


    @expose_for(group.guest)
    @web.method.get
    def index(self, uri='.', error='', msg='', _=None):
        path = Path((datapath / uri).absolute())
        directories, files = path.listdir()

        if path.isfile():
            # TODO: Render/edit .md, .conf, .txt files. .csv, .xls also?

            return serve_file(path.absolute)
        elif not (path.islegal() and path.exists()):
            raise HTTPFileNotFoundError(path)
        else:
            return web.render(
                'download.html', error=error, message=msg,
                files=files, directories=directories,
                curdir=path,
                max_size=conf.upload_max_size
            ).render()

    @expose_for(group.editor)
    @web.method.post_or_put
    def upload(self, dir, datafile, **kwargs):
        error = ''
        fn = ''
        if datafile:
            path = Path((datapath / dir).absolute())
            if not path:
                path.make()
            fn = path + datafile.filename
            if not fn.islegal():
                error = "'%s' is not legal"
            if fn and 'overwrite' not in kwargs:
                error = f"'{fn.name}' exists already, if you want to overwrite the old version, check allow overwrite"

            # Buffer file for first check encoding and secondly upload file
            with BytesIO(datafile.file.read()) as filebuffer:

                try:
                    write_to_file(fn.absolute, filebuffer)
                    fn.setownergroup()
                    msg = f'New file: {fn.href}'
                except:
                    error += '\n' + traceback()

        goto(dir, error, msg)

    @expose_for(group.logger)
    @web.method.post
    def saveindex(self, dir, s):
        """Saves the string s to index.html
        """
        path = datapath / dir / 'index.html'
        s = s.replace('\r', '')
        path.write_text(s)
        return web.markdown(s)

    @expose_for()
    @web.method.get
    def getindex(self, dir):
        index = datapath / dir / 'index.html'
        io = StringIO()
        if index.exists():
            text = index.read_text()
            io.write(text)
        imphist = datapath / dir / '.import.hist'
        if imphist.exists():
            io.write('\n')
            for l in imphist.open():
                ls = l.split(',', 3)
                io.write(' * file:%s/%s imported by user:%s at %s into %s\n' %
                         tuple([imphist.up()] + ls))
        return web.markdown(io.getvalue())

    @expose_for(group.editor)
    @web.method.post_or_put
    def newfolder(self, dir, newfolder):
        error = ''
        msg = ''
        if newfolder:
            if ' ' in newfolder:
                error = "The folder name may not include a space!"
            else:
                try:
                    path = Path((datapath / dir / newfolder).absolute())
                    if not path.exists() and path.islegal():
                        path.make()
                        path.setownergroup()
                        msg = f"{path.href} created"
                    else:
                        error = f"Folder {newfolder} exists already"
                except:
                    error = traceback()
        else:
            error = 'Forgotten to give your new folder a name?'

        if not error:
            goto(dir + '/' + newfolder, error, msg)
        else:
            goto(dir, error, msg)

    @expose_for(group.admin)
    @web.method.post_or_delete
    def removefile(self, dir, filename):
        path = Path((datapath / dir / filename).absolute())
        error = msg = ''

        if path.isfile():
            try:
                os.remove(path.absolute)
                msg = f'{filename} deleted'
            except:
                error = "Could not delete the file. A good reason would be a mismatch of user rights on the server " \
                        "file system"
        elif path.isdir():
            if path.isempty():
                try:
                    dirs, files = path.listdir()
                    for f in files:
                        if f.ishidden():
                            os.remove(f.absolute)
                    os.rmdir(path.absolute)
                    msg = f'{filename} removed'
                except (FileNotFoundError, OSError):
                    error = f'Could not delete {path}. Please ask the administrators about this problem.'
            else:
                error = "Cannot remove directory. Not empty."
        else:
            error = "File not found. Is it already deleted?"

        qs = urlencode({'error': error, 'msg': msg})
        url = f'{conf.root_url}/download/{dir}'.strip('.')
        return url + '?' + qs

