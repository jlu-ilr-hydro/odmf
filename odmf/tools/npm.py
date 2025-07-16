"""
This module provides functions to manage npm packages in the static directory.
"""

from nodejs import npm
import os
import contextlib

def get_static_path(*args):
    """
    Returns the path to the static directory.
    """
    return os.path.join(os.path.dirname(__file__), '..', 'static', *args)

@contextlib.contextmanager
def __npm_context():
    d = os.getcwd()
    path = get_static_path()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(d)

def install():
    if os.path.exists(get_static_path('node_modules')):
        return
    else:
        with __npm_context():
            npm.run(['install', '--no-audit', '--no-fund', '--prefer-offline', '--ignore-scripts'])

def update():
    with __npm_context():
        npm.run(['update','--save', '--no-audit', '--no-fund', '--prefer-offline', '--ignore-scripts'])