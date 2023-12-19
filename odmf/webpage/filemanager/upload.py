# -*- coding:utf-8 -*-

'''
Created on 15.02.2012

@author: philkraf
'''

from .. import lib as web
import datetime
import os
import shutil
from traceback import format_exc as traceback
from io import StringIO, BytesIO
import cherrypy
from cherrypy.lib.static import serve_file
from urllib.parse import urlencode
from ..auth import Level, expose_for, is_member, users
from ...tools import Path

from ...config import conf

from .dbimport import DbImportPage
from . import filehandlers as fh
from . import file_auth as fa


def write_to_file(dest, src):
    """
    Write data of src (file in) into location of dest (filename)

    :param dest:  filename on the server system
    :param src: file contents input buffer
    :return:
    """
    with open(os.open(dest, os.O_CREAT | os.O_WRONLY, 0o770), 'wb') as fout:
        while True:
            data = src.read(8192)
            if not data:
                break
            fout.write(data)


class DownloadPageError(cherrypy.HTTPError):
    def __init__(self, path: Path, status:int , message: str):
        super().__init__(status=status, message=message)
        self.message = message
        self.path = path

    def get_error_page(self, *args, **kwargs):

        error = f'Problem with {self.path}: {self.message}'
        modes = fa.check_children(self.path, users.current)

        text = web.render(
            'download.html',
            error=error, success='', modes=modes, Mode=fa.Mode,
            files=[],
            directories=[],
            curdir=self.path,
            content='',
            max_size=conf.upload_max_size
        ).render()

        return text.encode('utf-8')


class HTTPFileNotFoundError(DownloadPageError):
    def __init__(self, path: Path):
        super().__init__(path, status=404, message=f'not found')


def goto(dir, error=None, msg=None):
    return web.redirect(f'{conf.root_url}/download/{dir}'.strip('.'), error=error or '', msg=msg or '')



@web.show_in_nav_for(0, 'file')
class DownloadPage(object):
    """The file management system. Used to upload, import and find files"""

    def _cp_dispatch(self, vpath: list):
        cherrypy.request.params['uri'] = '/'.join(vpath)
        vpath.clear()
        return self

    to_db = DbImportPage()
    filehandler = fh.MultiHandler()


    def render_file(self, path, error=None):
        content = ''
        try:
            content = self.filehandler(path)
        except ValueError as e:
            content = f'<div class="alert bg-warning"><h3>{e}</h3></div>'

        except cherrypy.CherryPyException:
            raise

        except Exception as e:
            if error: error += '\n\n'
            error += str(e)
            if is_member(Level.admin):
                error += '\n```\n' + traceback() + '\n```\n'
        return content, error


    @expose_for(Level.logger)
    @web.method.get
    def index(self, uri='.', error='', msg='', serve=False, _=None):
        path = Path(uri)
        modes = fa.check_children(path, users.current)

        if not all((
                path.islegal(),
                path.exists(),
        )):
            raise HTTPFileNotFoundError(path)
        hidden = (path.ishidden() and modes[path]<fa.Mode.admin) or modes[path]==fa.Mode.none
        if hidden:
            content = f'Forbidden access to resource {path} for {users.current.name}'
            error = 'No access'
            files = []
            directories = []
        else:
            content = ''
            directories, files = path.listdir(hidden=modes[path]>=fa.Mode.admin)

        if path.isfile():
            if serve:
                return serve_file(path.absolute, disposition='attachment', name=path.basename)
            else:
                content, error = self.render_file(path, error)

        return web.render(
            'download.html',
            error=error, success=msg,
            modes=modes, Mode=fa.Mode, owner=fa.get_owner(path),
            content = content,
            files=sorted(files),
            directories=sorted(directories),
            handler=self.filehandler,
            curdir=path,
            max_size=conf.upload_max_size
        ).render()


    @expose_for(Level.editor)
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
            path = Path(dir)
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
                        msg.append(f'- {fn.href} uploaded')
                    except Exception as e:
                        error.append(f'- {fn.href} upload failed: {e}')

        raise goto(dir, '\n'.join(error), '\n'.join(msg))

    @expose_for(Level.logger)
    @web.method.post
    def saveindex(self, dir, s):
        """Saves the string s to index.html
        """
        path = Path(dir,  'index.html')
        s = s.replace('\r', '')
        open(path.absolute, 'w').write(s)
        return web.markdown(s)

    @expose_for(Level.logger)
    @web.method.get
    def getindex(self, dir):
        io = StringIO()
        for indexfile in ['README.md', 'index.html']:
            if (index:=Path(dir, indexfile)).exists():
                text = open(index.absolute).read()
                io.write(text)

        imphist = Path(dir, '.import.hist')

        if imphist.exists():
            io.write('\n')
            for l in open(imphist.absolute):
                fn, user, date, ds = l.split(',', 3)
                io.write(f' * file:{dir}/{fn} imported by user:{user} at {date} into {ds}\n')
        return web.markdown(io.getvalue())

    @expose_for(Level.logger)
    @web.method.get
    @web.mime.json
    def listdir(self, dir, pattern=None):
        import re
        path = Path(dir)
        directories, files = path.listdir()
        return web.as_json(
            directories={d.basename: d.href for d in sorted(directories)},
            files={
                f.basename: f.href
                for f in sorted(files)
                if (pattern is None
                    or re.match(pattern, f.basename))
            }
        ).encode('utf-8')

    @expose_for(Level.editor)
    @web.method.post_or_put
    def newfolder(self, dir, newfolder):
        error = ''
        msg = ''
        if newfolder:
            if ' ' in newfolder:
                error = "The folder name may not include a space!"
            else:
                try:
                    path = Path(dir, newfolder)
                    if not path.exists() and path.islegal():
                        path.make()
                        fa.set_owner(path, users.current.name)
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

    @expose_for(Level.editor)
    @web.method.post_or_put
    def newtextfile(self, dir, newfilename):
        if newfilename:
            try:
                path = Path(dir, newfilename)

                if not path.basename.endswith('.wiki') or path.basename.endswith('.md'):
                    path = Path(str(path) + '.wiki')
                if not path.exists() and path.islegal():
                    with open(path.absolute, 'w') as f:
                        f.write(newfilename + '\n' + '=' * len(newfilename) + '\n\n')
                    raise goto(path.name, msg=f"{path.href} created")
                else:
                    raise goto(dir, error=f"File {newfilename} exists already")
            except Exception as e:
                if isinstance(e, cherrypy.HTTPRedirect):
                    raise
                else:
                    raise goto(dir, error=traceback())
        else:
            raise goto(dir, error='Forgotten to give your new file a name?')

    @expose_for(Level.editor)
    @web.method.post_or_delete
    def removefile(self, dir, filename):
        """
        Removes a file from a directory (only for admins)
        """
        path = Path(dir, filename)
        error = msg = ''
        mode = fa.check_directory(path, users.current)
        if mode < fa.Mode.admin:
            raise DownloadPageError(path, 403, 'You need to have admin rights on this directory')
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
                    dirs, files = path.listdir(hidden=True)
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

    @expose_for(Level.editor)
    @web.method.post
    def copyfile(self, dir, filename, newfilename):
        """
        Copies filename in directory to newfilename
        """
        path = Path(dir, filename)
        targetpath = Path(dir, newfilename)
        error = msg = ''
        if not path.islegal():
            error = '{path} is not a legal position'
        elif not targetpath.islegal():
            error = f'{targetpath} not a valid copy destination'
        elif not path.isfile():
            error = f'{path} is not a file'
        elif targetpath.exists():
            error = f'{targetpath} exists already, choose another name'
        else:
            try:
                shutil.copyfile(path.absolute, targetpath.absolute)
                msg = f'{path} copied to {targetpath}'
            except:
                error = "Could not delete the file. A good reason would be a mismatch of user rights on the server " \
                        "file system"
        qs = urlencode({'error': error, 'msg': msg})
        url = f'{conf.root_url}/download/{dir}'.strip('.')
        return url + '?' + qs

    @expose_for(Level.editor)
    @web.method.post
    def create_access_file(self, uri):
        path = Path(uri)
        rule = fa.AccessRule.find_rule(path)
        owner = fa.get_owner(path)
        if rule(users.current, owner)>=fa.Mode.admin:
            rule.save(path)
            raise goto((path / fa.filename))
        else:
            raise DownloadPageError(path, status=403, message='Only admins can create access files')



    @expose_for(Level.editor)
    @web.method.post
    def write_to_file(self, path, text):
        path = Path(path)
        error = msg = ''
        if not path.islegal() or path.isdir():
            raise goto(path, error='Write failed at ' + str(path))

        if path.exists() and path.isfile():
            import shutil
            try:
                shutil.move(path.absolute, path.absolute + f'.{datetime.datetime.now():%Y-%m-%d}.bak')
            except Exception as e:
                raise goto(path, error='Failed to create backup at ' + str(path))

        with open(path.absolute, 'w') as f:
            f.write(text)

    @expose_for()
    @web.method.post
    def action(self, path, actionid: int):
        from ..auth import users, User, Level
        path = Path(path)
        action_id = web.conv(int, actionid)
        handler = self.filehandler[path]
        try:
            action: fh.FileAction = handler.actions[action_id]
        except IndexError:
            raise DownloadPageError('not enough actions available')
        if users.current.level < action.access_level:
            required_group = Level(action.access_level)
            raise DownloadPageError(path, 403,f'you need to be {required_group.name} for {action}')
        newpath = action(path)
        msg = {'msg': f'{action} on {path} successful'}
        return f'{newpath.href}?{urlencode(msg)}'

