# -*- coding:utf-8 -*-
'''
Created on 13.07.2012

@author: philkraf
'''

import base
import importpressure as _ip
import importclimate as _ic
import db
from base import finddateGaps, findStartDate
_adapters = {1 : _ip.OdysseyImport,
             2:  _ip.DiverImport,
             19: _ic.ClimateImporterDat,
             }
def get_adapter(filename, user, siteid, instrumentid, startdate=None,enddate=None):
    adapterClass = _adapters.get(instrumentid)
    if adapterClass:
        adapter = adapterClass(filename, user, siteid, instrumentid, startdate, enddate)
        return adapter
    else:
        raise RuntimeError("No adapter available for intrument %i", instrumentid)
def available_adapters():
    session = db.Session()
    q=session.query(db.Datasource).filter(db.Datasource.id.in_(_adapters.keys()))
    res=q.all()
    session.close()
    return res


def importfilestats(filename, user, siteid, instrumentid, startdate=None,enddate=None):
    adapter = get_adapter(filename, user, siteid, instrumentid, startdate,enddate)
    return adapter.get_statistic()
    

def importfile(filename, user, siteid, instrumentid, startdate=None, enddate=None):
    "Imports a file using the fitting ImportAdapter for the instrument"
    adapter = get_adapter(filename, user, siteid, instrumentid, startdate,enddate)
    adapter.createdatasets()
    adapter.submit()
    return adapter.datasets
