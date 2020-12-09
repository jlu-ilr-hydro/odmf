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
from .. import db
from ..dataimport import importlog
from ..dataimport import pandas_import as pi
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


def logimport(filename, kwargs):
    """

    :param filename:
    :param kwargs:
    :param import_with_class:
    :return:
    """

    t0 = time.time()

    path = Path(filename.strip('/'))

    error = di.checkimport(path.absolute)
    if error:
        raise web.redirect(path.parent().href, error=error)
    try:
        li = importlog.LogbookImport(path.absolute, web.user())
        logs, cancommit = li('commit' in kwargs)

    except importlog.LogImportError as e:
        raise web.redirect(path.parent().href, error=str(e))

    t1 = time.time()

    log("Imported in %.2f s" % (t1 - t0))

    if 'commit' in kwargs and cancommit:
        di.savetoimports(path.absolute, web.user(), ["_various_as_its_manual"])
        raise web.redirect(path.parent().href, error=error)
    else:
        return web.render(
            'logimport.html', filename=path, logs=logs,
            cancommit=cancommit, error=error
        ).render()

def instrumentimport(filename, kwargs):
    """
    Loads instrument data using a .conf file

    Wheter 'loadstat' or 'impordb' is in kwargs, the method returns the import page with the stats or with a commit
    message

    :param filename:
    :param kwargs: May contain a force value, to import even if the file has been uploaded before
    """

    t0 = time.time()

    # Error streams
    errorstream = StringIO()

    # TODO: Major refactoring of this code logic, when to load gaps, etc.
    path = Path(filename.strip('/'))
    # Check if the file has already been uploaded
    error = di.checkimport(path.absolute)

    if error and not kwargs.get('force'):
        raise web.redirect(path.parent().href, error=error)

    errorstream.write(error)
    config = di.getconfig(path.absolute)

    if not config:
        raise web.redirect(
            conf.root_url + f'/download/{web.escape(path.up())}',
            error='No config available. Please provide a config for computing a decent result.'
        )
    else:

        valuetype = [e.valuetype for e in config.columns]
        config.href = Path(config.filename).href

        adapter = di.get_adapter(
            path.absolute, web.user(),
            siteid=None, instrumentid=None
        )

        adapter.errorstream = errorstream
        stats = adapter.get_statistic()
        startdate = min(v.start for v in stats.values())
        enddate = max(v.end for v in stats.values())


        t1 = time.time()

        log("Imported in %.2f s" % (t1 - t0))

    return web.render(
        'dbimport.html',
        config=config,
        stats=stats,
        error=errorstream.getvalue(),
        filename=filename,
        dirlink=path.up(),
        startdate=startdate, enddate=enddate
    ).render()


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


@web.expose
class DbImportPage:
    """
    Class to handle data imports from files
    """

    @expose_for(group.editor)
    def index(self, filename, **kwargs):
        filepath = Path(filename)
        if not filepath.exists():
            raise goto(f'/download/', f'{filepath} not found - cannot import')
        import re
        # If the file ends with log.xls[x], import as log list
        if re.match(r'(.*)_log\.xlsx?$', filename):
            log("Import with logimport")
            return self.as_logimport(filename, **kwargs)
        # else import as instrument file
        else:
            return self.with_config(filename, **kwargs)

    @staticmethod
    def as_logimport(filename, **kwargs):
        path = Path(filename.strip('/'))
        error = di.checkimport(path.absolute)
        if error:
            raise web.redirect(path.parent().href, error=error)
        try:
            li = importlog.LogbookImport(path.absolute, web.user())
            logs, cancommit = li('commit' in kwargs)
        except importlog.LogImportError as e:
            raise web.redirect(path.parent().href, error=str(e))

        if 'commit' in kwargs and cancommit:
            di.savetoimports(path.absolute, web.user(), ["_various_as_its_manual"])
            raise web.redirect(path.parent().href, error=error)
        else:
            return web.render(
                'logimport.html', filename=path, logs=logs,
                cancommit=cancommit, error=error
            ).render()

    @staticmethod
    def with_config(filename, **kwargs):
        """
        Shows dbimport.html with the datafile loaded and ready for import
        """
        path = Path(filename.strip('/'))
        error = di.checkimport(path)
        rawcontent = open(path.absolute, 'rb').read(1024).decode('utf-8', 'ignore')
        try:
            config = di.ImportDescription.from_file(path.absolute)
            df = pi.load_dataframe(config, path)
            stats, startdate, enddate = pi.get_statistics(config, df)
            table = df.to_html(
                float_format=lambda f: f'{f:0.5g}',
                classes=('table', 'thead-dark', 'table-responsive', 'table-striped'),
                border=0,
                max_rows=30
            )

        except pi.DataImportError as e:
            stats, startdate, enddate, table = {}, None, None, ''
            error = str(e)


        return web.render(
            'dbimport.html',
            rawcontent=rawcontent,
            config=config,
            stats=stats,
            error=error,
            table=table,
            filename=filename,
            dirlink=path.up(),
            startdate=startdate, enddate=enddate
        ).render()



    @expose_for(group.editor)
    @web.method.post
    def submit_config(self, filename, siteid, **kwargs):
        path = Path(filename.strip('/'))
        siteid = web.conv(int, siteid)
        user = kwargs.pop('user', web.user())
        config = di.ImportDescription.from_file(path.absolute)
        try:
            with db.session_scope() as session:
                messages = pi.submit(session, config, path, user, siteid)
                di.savetoimports(path.absolute, web.user(), [m.split()[0] for m in messages])

        except pi.DataImportError as e:
            raise web.redirect('..', error=str(e))

        else:
            raise web.redirect(path.parent().href, msg='\n'.join(f' - {msg}' for msg in messages))



def goto(dir, error=None, msg=None):
    return web.redirect(f'{conf.root_url}/download/{dir}'.strip('.'), error=error, msg=msg)


@web.show_in_nav_for(0, 'file')
class DownloadPage(object):
    """The file management system. Used to upload, import and find files"""

    def _cp_dispatch(self, vpath: list):
        request.params['uri'] = '/'.join(vpath)
        vpath.clear()
        return self

    to_db = DbImportPage()

    @expose_for(group.guest)
    @web.method.get
    def index(self, uri='.', error='', msg='', _=None):
        path = Path((datapath / uri).absolute())
        directories, files = path.listdir()

        if path.isfile():
            # TODO: Render/edit .md, .conf, .txt files. .csv, .xls also?

            return serve_file(path.absolute, name=path.basename)
        elif not (path.islegal() and path.exists()):
            raise HTTPFileNotFoundError(path)
        else:
            return web.render(
                'download.html', error=error, message=msg,
                files=sorted(files),
                directories=sorted(directories),
                curdir=path,
                max_size=conf.upload_max_size
            ).render()

    @expose_for(group.editor)
    @web.method.post_or_put
    def upload(self, dir, datafiles, **kwargs):
        """
        Uploads a list of files. Make sure the upload element is like

        <input type="file" multiple="multiple"/>

        Parameters
        ----------
        dir
            The target directory
        datafiles
            The datafiles to upload
        kwargs

        """
        error = []
        msg = []
        # Loop over incoming datafiles. Single files need some special treatment
        for datafile in (list(datafiles) or [datafiles]):
            path = Path((datapath / dir).absolute())
            if not path:
                path.make()
            fn = path + datafile.filename
            if not fn.islegal():
                error.append(f'{fn.name} is not legal')
            elif fn and 'overwrite' not in kwargs:
                error.append(f"'{fn.name}' exists already, if you want to overwrite the old version, check allow overwrite")
            else:
                # Buffer file for first check encoding and secondly upload file
                with BytesIO(datafile.file.read()) as filebuffer:

                    try:
                        write_to_file(fn.absolute, filebuffer)
                        fn.setownergroup()
                        msg.append(f'- {fn.href} uploaded')
                    except Exception as e:
                        error.append(f'- {fn.href} upload failed: {e}')

        raise goto(dir, '\n'.join(error), '\n'.join(msg))


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
                fn, user, date, ds = l.split(',', 3)
                io.write(f' * file:{dir}/{fn} imported by user:{user} at {date} into {ds}\n')
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
            raise goto(dir + '/' + newfolder, error, msg)
        else:
            raise goto(dir, error, msg)

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

