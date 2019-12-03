"""
A sample file to demonstrate how a new record should be posted to the database
"""

import requests
import datetime

base_url = 'http://fb09-pasig.umwelt.uni-giessen.de:8081/api'
username = 'philipp'
password = 'xxx'


class AuthorizationError(RuntimeError):
    def __init__(self, username):
        super().__init__(f'User "{username}": password wrong or user does not exist')


def make_url(append=None):
    uri = base_url
    if append:
        uri += '/' + append
    return uri


def login(username, password):
    session = requests.Session()
    url = make_url('login')
    r = session.post(url, data={'username': username, 'password': password})
    if 200 <= r.status_code < 300:
        return session
    else:
        session.close()
        raise AuthorizationError(username)


def post_record(dataset_id: int, time: datetime.datetime, value: float,
                sample=None, comment=None, http_session=None):
    http_session = http_session or login(username, password)
    url = make_url('dataset/addrecord')
    http_session.put(url,
                     data=dict(
                         dsid=int(dataset_id),
                         value=value,
                         time=time.isoformat(),
                         sample=str(sample),
                         comment=str(comment)
                     ))
