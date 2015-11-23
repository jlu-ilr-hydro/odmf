# -*- coding:utf-8 -*-
'''
Created on 13.07.2012

@author: philkraf
'''

import base
import os.path
#import importpressure as _ip
#import importclimate as _ic
import db
import textimport as _ti
import xls as _xl
from base import finddateGaps, findStartDate, savetoimports, checkimport

# This list hast to be a 'python-list' since the order or the adapters is
# necessary for the implementation
_adapters = [
    _xl.XlsImport,  # xls files
    _ti.TextImport  # default
    ]

# TODO: Seperate the part of get_adapter where the adapter is chosen from where the adapter is called

def get_adapter(filename, user, siteid, instrumentid, startdate=None,
                enddate=None):

    for adapter in _adapters:
        if adapter.extension_fits_to(filename):
            print "[LOG] - Using %s for importing" % adapter.__name__
            return adapter(filename, user, siteid, instrumentid, startdate,
                           enddate)

    raise RuntimeError("No adapter available for file extension ", instrumentid)

# TODO: Ist das jetzt so noch aktuell?
def available_adapters():
    session = db.Session()
    q=session.query(db.Datasource).filter(db.Datasource.id.in_(_adapters.keys()))
    res=q.all()
    session.close()
    return res

def getconfig(filename):

    for adapter in _adapters:
        if adapter.extension_fits_to(filename):
            print "[LOG] - Using %s for extract config" % adapter.__name__
            try:
                # Get import description
                importdesc = adapter.get_importdescriptor().from_file(filename)
                return importdesc
            except IOError:
                return None


def importfilestats(filename, user, siteid, instrumentid=None, startdate=None,enddate=None):
    adapter = get_adapter(filename, user, siteid, instrumentid, startdate,enddate)
    return adapter.get_statistic()
    

def importfile(filename, user, siteid, instrumentid, startdate=None, enddate=None):
    "Imports a file using the fitting ImportAdapter for the instrument"
    adapter = get_adapter(filename, user, siteid, instrumentid, startdate, enddate)
    adapter.createdatasets()
    adapter.submit()
    savetoimports(filename,user,adapter.datasets.values())
    return adapter.datasets
