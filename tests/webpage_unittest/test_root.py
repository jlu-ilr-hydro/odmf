import json

import pytest
import cherrypy
import datetime
from contextlib import contextmanager
from pathlib import Path
import re
from . import conf, db, db_session

@contextmanager
def temp_in_database(obj, session):
    """
    Adds the ORM-object obj to the session and commits it to the database.
    After usage the object is deleted from the session and is commited again
    """
    session.add(obj)
    session.commit()
    yield obj
    session.delete(obj)
    session.commit()


def test_config():
    from odmf.config import conf
    assert conf.description == '******** TEST *********'


@pytest.fixture()
def root(db):
    from cherrypy.lib.sessions import RamSession
    cherrypy.session = RamSession()
    cherrypy.request.login = None
    from odmf.webpage.root import Root
    return Root()


class TestIndex:

    def test_index_no_login(self, root):
        map_html = root.index()
        assert map_html.startswith('<!DOCTYPE html>')
        assert 'id="map_canvas"' in map_html

    def test_index_login_no_job(self, root):
        cherrypy.request.login = 'odmf.admin'
        map_html = root.index()
        assert map_html.startswith('<!DOCTYPE html>')
        assert 'id="map_canvas"' in map_html

    def test_index_login_new_job(self, root, db, db_session):
        cherrypy.request.login = 'odmf.admin'
        with temp_in_database(
                db.Job(
                    _author='odmf.admin', _responsible='odmf.admin', id=1, name='test-job',
                    due=datetime.datetime.today()
                ), db_session
        ):
            with pytest.raises(cherrypy.HTTPRedirect):
                _ = root.index()


class TestLogin:

    def test_login_no_pw(self, root):
        result = root.login(frompage='/', username='odmf.admin', password=None)
        assert 'About' in result
        assert cherrypy.request.login != 'odmf.admin'

    def test_login_no_user(self, root):
        result = root.login(frompage='/', username='odmf.admin', password=None)
        assert 'About' in result
        assert cherrypy.request.login != 'odmf.admin'

    def test_login_bad_user(self, root):
        with pytest.raises(cherrypy.HTTPRedirect) as redirect_info:
            root.login(frompage='/', username='nobody', password='bla')
        error = redirect_info.value.urls[0].split('?')[-1]
        assert error.startswith('error=')
        assert 'not+found' in error
        assert cherrypy.request.login != 'odmf.admin'

    def test_login_wrong_pw(self, root):
        with pytest.raises(cherrypy.HTTPRedirect) as redirect_info:
            root.login(frompage='/', username='odmf.admin', password='bla')
        error = redirect_info.value.urls[0].split('?')[-1]
        assert error.startswith('error=')
        assert cherrypy.request.login != 'odmf.admin'

    def test_login_ok_from_map(self, root):
        with pytest.raises(cherrypy.HTTPRedirect) as redirect_info:
            root.login(frompage='/map', username='odmf.admin', password='test')
        assert redirect_info.value.urls[0].endswith('/map')
        assert cherrypy.request.login == 'odmf.admin'

    def test_login_ok_from_login(self, root):
        with pytest.raises(cherrypy.HTTPRedirect) as redirect_info:
            root.login(frompage=None, username='odmf.admin', password='test')
        assert redirect_info.value.urls[0].endswith('/login')
        assert cherrypy.request.login == 'odmf.admin'

    def test_logout(self, root):
        cherrypy.request.login = 'odmf.admin'
        res = root.login(logout=True)
        assert cherrypy.request.login != 'odmf.admin'
        assert 'About' in res


@pytest.fixture()
def markdown_file(conf):
    p = Path(conf.home) / 'test.md'
    p.write_text('\n'.join([
        'ds1000',
        'file:x/y/z',
        'site #1',
        'user:odmf.admin',
        'https://127.0.0.1:8081',
        '--> ==> <-- <==',
        '!fa-map',
        'video:https://127.0.0.1:8081/video'
        ]))
    yield p
    p.unlink(missing_ok=True)


class TestMarkDown:

    def test_markdown_simple(self, markdown_file, root):

        md_text = root.markdown('test.md').accumulate_str()
        assert 'href="/dataset/1000/"' in md_text
        assert 'href="/site/1"' in md_text
        assert 'href="/download/x/y/z"' in md_text
        assert 'href="/user/odmf.admin"' in md_text

    def test_markdown_missing_file(self, root):
        with pytest.raises(FileNotFoundError):
            _ = root.markdown('bla.md')

    def test_markdown_page(self, markdown_file, root):
        t = markdown_file.read_text()
        md_text = root.markdownpage(t, 'test')
        assert 'href="/dataset/1000/"' in md_text
        assert 'href="/site/1"' in md_text
        assert 'href="/download/x/y/z"' in md_text
        assert 'href="/user/odmf.admin"' in md_text


class TestRessources:

    def test_ressources_json(self, root):
        test = root.resources(format='json')
        import json
        data = json.loads(test)
        assert len(data) > 10
        assert all('doc' in v for v in data.values())

    @pytest.mark.parametrize('fmt', ['json', 'xlsx', 'tsv', 'csv', 'html'])
    def test_ressources(self, root, fmt):
        test = root.resources(format=fmt)
        assert len(test) > 100

def test_showjson(root):
    d = {'a': 'a', 'b': 'b'}
    text = root.showjson(**d)
    data = json.loads(text)
    assert data == d

def test_robots_txt(root):
    text = root.robots_txt()
    assert 'Disallow: /' in text


class TestStatic:
    def test_media_dir(self, root):
        html = root.media.index()
        assert html.startswith('<ul>')

    def test_media_favicon(self, root):
        html = root.media.index('ilr-favicon.png').input.read()
        assert len(html) == 878

    def test_media_missing(self, root):
        with pytest.raises(cherrypy.HTTPError):
            root.media.index('xxxxx.xyz')

    def test_media_dir_forbidden(self, root):
        root.media.listdir = False
        with pytest.raises(cherrypy.HTTPError):
            root.media.index()
        root.media.listdir = True

    def test_media_illegal_path(self, root):
        with pytest.raises(cherrypy.HTTPError) as e:
            root.media.index('../templates')
        assert e.value.code == 403


    def test_cp_dispatch(self, root):
        path = 'media/js/plot.js'
        root.media._cp_dispatch(path.split('/'))
        out_path = cherrypy.request.params['path']
        assert out_path == path
