# !/usr/bin/env python
# -*- coding:utf-8 -*-
'''
Created on 12.02.2012

@author: philkraf
'''
import sys
import os
from glob import glob


print(sys.executable)


# System checks !before project imports
if not os.path.isfile('conf.py'):
    raise RuntimeError('Consider providing a configuration file at \'conf.py\'!')
else:
    import conf

    # TODO: outsource mandatory config items
    if conf.CFG_DATABASE_NAME is '' \
        or conf.CFG_DATABASE_USERNAME is '' \
        or conf.CFG_DATABASE_PASSWORD is '' \
        or conf.CFG_DATABASE_HOST is '':
        raise RuntimeError('Server cannot start! There are mandatory config attributes which are empty.')

# Start with project imports
from webpage import Root, HeapyPage
from webpage import lib

# Make autoreload
autoreload = 'noreload' not in sys.argv
print("autoreload =", autoreload)

print("Kill session lock files")
for fn in glob('webpage/sessions/*.lock'):
    os.remove(fn)

# Create the URL root object
root = Root()

# Create a heapy page to view memory usage
if 'heapy' in sys.argv:
    print("Load heapy")
    from guppy import hpy
    hp = hpy()
    hp.setrelheap()
    root.heapy = HeapyPage(hp)

#config="server.conf"

# Start the server
lib.start_server(root, autoreload=autoreload, port=8081)
