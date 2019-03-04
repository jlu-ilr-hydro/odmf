#!/usr/bin/env python3
# Basic tests covering calls and login behaviour

import requests

# credentials
# see documention 'Tests'
user = 'admin'
password = '1234'

# schiwngbach installation
url = 'http://localhost:8081'
site = lambda s: url + s

# TODO: login behaviour with selenium or splinter
# all pages without login
pages = ['/map', '/login', '/wiki/publications', '/wiki']
# all pages with login
pages += ['/plot', '/site', '/picture', '/dataset/last', '/valuetype', '/instrument', '/download', '/project',
          '/calendar', '/user', '/job', '/admin', '/log']


error = False
errors = ""
# using the session object for using the login cookie
with requests.Session() as s:

    # login
    s.post(site('/login'), data={'username': user, 'password': password})

    # fetching all possible pages
    for page in pages:
        response = s.get(site(page))
        if response.status_code is not 200:
            msg = "Failed " + page + " with status " + repr(response.status_code)
            print(msg)
            error = True
            errors += "\t* " + msg + "\n"
        else:
            print("Page\t" + page + " ... Done [with " + str((len(response.content) * 32)) + " bytes]")

    # logout
    s.post(site('/user/logout'))

if error:
    print("\n#################################\n\tError summary\n#################################")
    print("Failing tests: \n" + errors)