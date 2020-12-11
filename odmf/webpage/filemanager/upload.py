# -*- coding:utf-8 -*-

'''
Created on 15.02.2012

@author: philkraf
'''

from odmf.webpage import lib as web

import os
from traceback import format_exc as traceback
from io import StringIO, BytesIO
from cherrypy import request, HTTPError
from cherrypy.lib.static import serve_file
from urllib.parse import urlencode
from ..auth import group, expose_for
from ...tools import Path

from ...config import conf

from .dbimport import DbImportPage



def write_to_file(dest, src):
    """
    Write data of src (file in) into location of dest (filename)

    :param dest:  filename on the server system
    :param src: file contents input buffer
    :return:
    """
    with open(os.open(dest, os.O_CREAT | os.O_WRONLY, 0o770), 'w') as fout:
        while True:
            data = src.read(8192)
            if not data:
                break
            fout.write(data)


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
        path = Path(uri)
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
            path = Path(dir).absolute
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
        path = Path(dir / 'index.html')
        s = s.replace('\r', '')
        open(path.absolute, 'w').write(s)
        return web.markdown(s)

    @expose_for()
    @web.method.get
    def getindex(self, dir):
        index = Path(dir, 'index.html')
        io = StringIO()
        if index.exists():
            text = open(index.absolute).read()
            io.write(text)

        imphist = Path(dir, '.import.hist')

        if imphist.exists():
            io.write('\n')
            for l in open(imphist):
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
                    path = Path(dir, newfolder).absolute()
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
        path = Path(dir, filename).absolute
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

