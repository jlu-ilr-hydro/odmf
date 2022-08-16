"""
ODMF should not only be tested by its units, but also for its behaviour in the browser

For such integration tests we need to start an ODMF web server and test requests.

There is an "official" way to do this here: https://docs.cherrypy.dev/en/latest/advanced.html#testing-your-application

But I (Philipp) found this way much easier to understand: https://schneide.blog/2017/02/06/integration-tests-with-cherrypy-and-requests/
Can we use their approach with the context manager as a fixture? Context and fixtures are quite similar...
"""

import pytest
import cherrypy
from ..webpage_unittest import root, db_session, conf

@pytest.fixture(scope='package')
def webserver(root):
    cherrypy.tree.mount(root, conf.root_url)
    cherrypy.engine.start()
    cherrypy.engine.wait(cherrypy.engine.states.STARTED)
    yield
    cherrypy.engine.exit()
    cherrypy.engine.block()