import json

import pytest
import cherrypy
import datetime
from pathlib import Path
import re
from ..test_db import db, session, temp_in_database
from . import root, conf

def test_config():
    from odmf.config import conf
    assert conf.description == '******** TEST *********'



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

    def test_index_login_new_job(self, root, db, session):
        cherrypy.request.login = 'odmf.admin'
        with temp_in_database(
                db.Job(
                    _author='odmf.admin', _responsible='odmf.admin', id=1, name='test-job',
                    due=datetime.datetime.today()
                ), session
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
        import odmf.webpage.auth as auth
        with pytest.raises(auth.HTTPAuthError) as redirect_info:
            cherrypy.request.method = 'POST'
            root.login(frompage='/', username='nobody', password='bla')
        assert cherrypy.request.login != 'odmf.admin'

    def test_login_wrong_pw(self, root):
        import odmf.webpage.auth as auth
        with pytest.raises(auth.HTTPAuthError) as redirect_info:
            cherrypy.request.method = 'POST'
            root.login(frompage='/', username='odmf.admin', password='bla')
        assert cherrypy.request.login != 'odmf.admin'

    def test_login_ok_from_map(self, root):
        with pytest.raises(cherrypy.HTTPRedirect) as redirect_info:
            cherrypy.request.method = 'POST'
            root.login(frompage='/map', username='odmf.admin', password='test')
        assert redirect_info.value.urls[0].endswith('/map')
        assert cherrypy.request.login == 'odmf.admin'

    def test_login_ok_from_login(self, root):
        with pytest.raises(cherrypy.HTTPRedirect) as redirect_info:
            cherrypy.request.method = 'POST'
            root.login(frompage=None, username='odmf.admin', password='test')
        assert redirect_info.value.urls[0].endswith('/login')
        assert cherrypy.request.login == 'odmf.admin'

    @pytest.mark.skip('do not unit test logout, cannot expire session out of a running server')
    def test_logout(self, root):
        cherrypy.request.login = 'odmf.admin'
        cherrypy.request.method = 'POST'
        res = root.login(logout=True)
        assert cherrypy.request.login != 'odmf.admin'
        assert 'About' in res


@pytest.fixture()
def markdown_file(conf):
    p = Path(conf.home) / 'test.md'
    p.write_text('\n'.join([
        'ds:1000',
        'file:x/y/z',
        'file:/x/y/z',
        'site:1',
        'user:odmf.admin',
        'https://127.0.0.1:8081',
        '--> ==> <-- <==',
        '!fa-map',
        ]))
    yield p
    p.unlink(missing_ok=True)


class TestMarkDown:

    def test_markdown_simple(self, conf, markdown_file, root):
        md_text = markdown_file.read_text()
        html_text = root.markdown('test.md').accumulate_str()
        assert f'href="{conf.root_url}/dataset/1000/"' in html_text
        assert f'href="{conf.root_url}/site/1"' in html_text
        assert f'href="{conf.root_url}/download/x/y/z"' in html_text
        assert f'href="{conf.root_url}/user/odmf.admin"' in html_text
        assert '<a href="https://127.0.0.1:8081">127.0.0.1:8081</a>' in html_text
        assert 'class="fas fa-map"' in html_text

    def test_markdown_bytes(self, conf, markdown_file):
        md_text = markdown_file.read_bytes()
        from odmf.webpage.lib import markdown
        html_text = markdown(md_text).accumulate_str()
        assert f'href="{conf.root_url}/dataset/1000/"' in html_text
        assert f'href="{conf.root_url}/site/1"' in html_text
        assert f'href="{conf.root_url}/download/x/y/z"' in html_text
        assert f'href="{conf.root_url}/user/odmf.admin"' in html_text
        assert '<a href="https://127.0.0.1:8081">127.0.0.1:8081</a>' in html_text
        assert 'class="fas fa-map"' in html_text

    def test_markdown_missing_file(self, root):
        with pytest.raises(FileNotFoundError):
            _ = root.markdown('bla.md')

    def test_markdown_page(self, conf, markdown_file, root):
        t = markdown_file.read_text()
        md_text = root.markdownpage(t, 'test')
        assert f'href="{conf.root_url}/dataset/1000/"' in md_text
        assert f'href="{conf.root_url}/site/1"' in md_text
        assert f'href="{conf.root_url}/download/x/y/z"' in md_text
        assert f'href="{conf.root_url}/user/odmf.admin"' in md_text


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
