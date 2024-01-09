import io
import typing

import cherrypy
import datetime
from contextlib import contextmanager

import pandas as pd

from .. import lib as web
from ..auth import users, expose_for, Level, has_level
from ... import db
from ...config import conf
from . import BaseAPI, get_help


class SiteAPI(BaseAPI):
    exposed=True
    url = conf.root_url + '/api/site'

    @web.expose
    @web.method.get
    def index(self, siteid: int=None):
        """
        Returns a json representation of a site
        :param siteid:
        """

        web.mime.json.set()
        if siteid is None:
            url, res = get_help(self, self.url)
            return web.json_out(res)
        with db.session_scope() as session:
            if not (site := session.get(db.Site, siteid)):
                raise web.APIError(404, f'#{site} does not exist')
            else:
                return web.json_out(site)


