"""
A sample file to demonstrate how a new record should be posted to the database
"""
import typing

import pandas as pd
import io
import json
import requests
import datetime
import yaml
import sys

from logging import getLogger

logger = getLogger('odmf-client')

base_url = 'http://127.0.0.1:8081/test'
username = 'philipp'
password = '37554'

class AuthorizationError(RuntimeError):
    def __init__(self, username):
        super().__init__(f'User "{username}": password wrong or user does not exist')


class APIError(RuntimeError):
    ...


class APIMethod:

    def __init__(self, client,  doc: str, http_methods: typing.List[str], parameters: dict, children: typing.Dict[str, dict], url: str, **kwargs):
        self.url = url
        self.doc = doc
        self.http_methods = [hm.upper() for hm in http_methods]
        self.parameters = parameters
        self.children = children
        self.client: APIclient = client

    def __dir__(self) -> typing.Iterable[str]:
        return list(self.__dict__) + list(self.children)

    def __str__(self):
        return self.url.split('/')[-1]

    def __getattr__(self, item):
        if item in self.children:
            return APIMethod(self.client, **self.children[item])
        else:
            raise AttributeError(f'{item} is not a submethod of {self}')

    def translate_response(self, r):
        """
        Translates the API response to appropriate Python objects
        parquet -> Dataframe
        JSON -> dictionary / list
        unknown -> str
        """
        mime = r.headers['Content-Type']
        if 'json' in mime:
            return r.json()
        elif self.url.endswith('parquet') and 'octet-stream' in mime or 'parquet' in mime:
            stream = io.BytesIO(r.content)
            df = pd.read_parquet(stream)
            return df
        else:
            return r.content

    def handle_error(self, r):
        if 'json' in r.headers['Content-Type']:
            data = r.json()
            raise APIError(
                '\n\n'.join(
                    (f'{self.url} failed with error {r.status_code}',
                     data.get('text', ''),
                     data.get('traceback', '')
                     )
                )
            )
        else:
            raise APIError(
                f'{self.url} failed with error {r.status_code}\n\n'
                f'{r.content}'
            )

    def __call__(self, data=None, **kwargs):
        if 'POST' in self.http_methods:
            if data is not None:
                r = self.client.post(self.url, data=data, params=kwargs)
            else:
                r = self.client.post(self.url, data=kwargs)
        elif 'GET' in self.http_methods:
            r = self.client.get(self.url, params=kwargs)
        elif 'PUT' in self.http_methods:
            r = self.client.request('PUT', self.url, data=data, params=kwargs)
        else:
            raise ValueError(f'{self.url} does not accept a POST, GET or PUT method')
        if 200 <= r.status_code < 300:
            logger.info(f'{self.url} success')
            return self.translate_response(r)
        elif 400 <= r.status_code < 600:
            logger.error(f'{self.url} failed: {r.status_code}')
            self.handle_error(r)
        else:
            logger.error(f'{self.url} failed:  {r.status_code}')
            raise APIError(f'Unknown status_code: {r.status_code}')


class APIclient:
    """
    A client to handle the ODMF-REST-API. To be used as a context:

    >>> with APIclient(apiurl='...', username='...', password='...') as odmfapi:
    >>>     yaml.dump(odmfapi(), sys.stdout, default_flow_style=False)
    """

    def serialize(self, obj):
        if isinstance(obj, typing.Mapping) or isinstance(obj, typing.List):
            return json.dumps(obj)
        elif isinstance(obj, pd.DataFrame):
            stream = io.BytesIO()
            obj.to_parquet(stream)
            return stream.getvalue()
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        else:
            return obj

    def href(self, suburl=''):
        return self.apiurl.rstrip('/') + '/' + suburl.strip('/')

    def request(self, method, url, **kwargs) -> requests.Response:
        return self.session.request(method, self.href(url), **kwargs)

    def post(self, url='', data=None, **kwargs) -> requests.Response:
        if isinstance(data, dict):
            for k in data:
                data[k] = self.serialize(data[k])
        else:
            data = self.serialize(data)
        return self.request('POST', url, data=data, **kwargs)

    def get(self, url='/api', params=None, **kwargs) -> requests.Response:
        if params:
            for k in params:
                params[k] = self.serialize(params[k])
        return self.request('GET', url, params=params, **kwargs)


    @property
    def api(self) -> APIMethod:
        r = self.get('api')
        data = r.json()['api']
        return APIMethod(self, **data)

    def login(self):
        r = self.post('/api/login', data={'username': username, 'password': password})
        if 200 <= r.status_code < 300:
            logger.info(f'Login as {username} succeceeded {self.apiurl}')
            return self
        else:
            logger.error(f'Login {username} failed at {self.apiurl}')
            raise AuthorizationError(username)

    def __init__(self, apiurl: str, username: str, password: str):
        self.session = requests.Session()
        self.apiurl = apiurl
        self.username = username
        self.password = password

    def __enter__(self):
        return self.login()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()


if __name__ == '__main__':
    with APIclient(base_url, username, password) as client:
        print(client.api)
        client.api.upload('bla'.encode(), targetpath='test.txt')



