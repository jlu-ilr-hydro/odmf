# !/usr/bin/env python
# -*- coding:utf-8 -*-
'''
Created on 12.02.2012

@author: philkraf
'''
import sys
sys.path.append('.')
import os
from glob import glob


print("Starting schwingbachserver using {}".format(sys.executable))

if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3")

# System checks !before project imports
from odmf import conf
if conf:
    # Check for mandatory attributes
    print("✔ Config is valid")
else:
    print("Error in config validation")
    exit(1)


# Start with project imports
from odmf.webpage import Root
from odmf.webpage import lib

# Make autoreload
autoreload = 'noreload' not in sys.argv
print("autoreload =", autoreload)

print("Kill session lock files")
for fn in glob('webpage/sessions/*.lock'):
    os.remove(fn)

# Create the URL root object
root = Root()

# Start the server
lib.start_server(root, autoreload=autoreload, port=conf.server_port)
