import pytest
import io
import json

import cherrypy
from pathlib import Path

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

    @pytest.mark.skip('do not test upload, somehow the directories in the test environment do not behave as expected')
    def test_api_upload(self, conf, root):
        test_txt = conf.datafiles + '\n' + ('blä blübb' * 10 + '\n') * 20
        cherrypy.request.body = io.BytesIO(test_txt.encode('utf-8'))

        res = root.api.upload('text.txt')

        assert res.decode('utf-8') == 'OK'

        from odmf.tools import Path as OPath
        p = Path(conf.datafiles) / 'text.txt'
        assert p.exists()
        res_txt = p.read_text('utf-8')
        assert res_txt == test_txt








