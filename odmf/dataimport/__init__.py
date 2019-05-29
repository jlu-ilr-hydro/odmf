# -*- coding:utf-8 -*-
'''
Created on 13.07.2012

@author: philkraf
'''

from . import base
from .. import db
from . import textimport as _ti
from . import xls as _xl
from . import mm as _mm
from .base import finddateGaps, findStartDate, savetoimports, checkimport, \
    ImportDescription

from ..dataimport.mm import ManualMeasurementsImport
#, \ImportManualMeasurementsDescription

import re

# This list hast to be a 'python-list' since the order or the adapters is
# necessary for the implementation
# TODO: Implement decent mechanism for adapters
_adapters = [
    #_mm.ManualMeasurementsImport, # for the manual-measurements dir
    _xl.XlsImport,  # xls files
    _ti.TextImport  # default/fallback
]


def get_adapter(filename, user, siteid, instrumentid, startdate=None,
                enddate=None):

    for adapter in _adapters:
        if adapter.extension_fits_to(filename):
            print("[LOG] - Using %s for importing" % adapter.__name__)

            return adapter(filename, user, siteid, instrumentid, startdate,
                           enddate)

    raise RuntimeError(
        "No adapter available for file extension ", instrumentid)


# TODO: Ist das jetzt so noch aktuell?
def available_adapters():
    session = db.Session()
    q = session.query(db.Datasource).filter(db.Datasource.id.in_(_adapters))
    res = q.all()
    session.close()
    return res


def getconfig(filename):

    # TODO: Overthink this first aproach
    try:
        # Get import description
        # if ManualMeasurementsImport.extension_fits_to(filename):
        #    importcls = ImportManualMeasurementsDescription
        # else:
        importcls = ImportDescription

        print("[LOG] - Using %s for extract config" % importcls.__name__)

        return importcls.from_file(filename)
    except IOError:
        return None


def importfilestats(filename, user, siteid, instrumentid=None, startdate=None, enddate=None):
    adapter = get_adapter(filename, user, siteid,
                          instrumentid, startdate, enddate)
    return adapter.get_statistic()


def importfile(filename, user, siteid, instrumentid, startdate=None, enddate=None):
    """

    Imports a file using the fitting ImportAdapter for the instrument

    :param filename:
    :param user:
    :param siteid:
    :param instrumentid:
    :param startdate:
    :param enddate:
    :return:
    """
    adapter = get_adapter(filename, user, siteid,
                          instrumentid, startdate, enddate)
    adapter.createdatasets()
    adapter.submit()
    savetoimports(filename, user, list(adapter.datasets.values()))
    return adapter.datasets
