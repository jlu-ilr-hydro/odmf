import io
import json

import cherrypy

from . import root
from . import conf, db, db_session, temp_in_database

class TestAPI:

    def test_login_param(self, root):
        res = root.api.login(username='odmf.admin', password='test')
        assert res.decode('utf-8') == 'OK'

    def test_login_body(self, root):
        txt = 'username=odmf.admin&password=test'
        stream = io.BytesIO(txt.encode('utf-8'))
        stream.seek(0)
        cherrypy.request.headers['Content-Length'] = str(len(stream.getvalue()))
        cherrypy.request.body = stream

        res = root.api.login()

        assert res.decode('utf-8') == 'OK'

    def test_api_index(self, root):
        res = root.api.index()
        data = json.loads(res.decode())

        assert 'api' in data
        assert 'children' in data['api']
        assert 'dataset' in data['api']['children']






