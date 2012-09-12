#!/usr/bin/python
'''
Created on 23.05.2012

@author: philkraf
'''

import os
import sys
from datetime import datetime,timedelta
import db
import xlrd
from traceback import format_exc as traceback

t0 = datetime(1899,12,30)

def get_time(date,time):
    if not time:
        return t0 + timedelta(date)
    else:
        if time>1.000001:
            time=time-int(time)
        date=int(date)
    return t0 + timedelta(date+time)

def row_to_record(row,dataset,id,rangeok=[-1e308,1e308]):
    rec=db.Record(id=id,dataset=dataset)
    rec.time = get_time(row[0].value,row[1].value)
    try:
        rec.value = float(row[2].value)
        if rec.value>max(rangeok) or rec.value<min(rangeok):
            rec.value=None
    except ValueError, TypeError:
        rec.value = None
    if row[3].value:
        rec.sample = row[3].value
    comment=(', '.join([unicode(c.value) for c in row[4:] if c.value])).strip()
    if comment:
        rec.comment = comment
    return rec
        
                

def readvalues(xlsfilename,killoldrecords=False,rangeok=[-1e308,1e308]):
    wb = xlrd.open_workbook(xlsfilename)
    sheet = wb.sheet_by_index(0)
    
    id = int(sheet.cell_value(3,1))
    error=False
    session = db.Session()
    ds = session.query(db.Dataset).get(id)
    if not ds:
        sys.stderr.write('Dataset %i not found in database. File %s is not imported\n' % (id,xlsfilename))
        return None
    if killoldrecords:
        records = ds.records
        count=records.delete()
        print count,"records deleted from dataset",ds.id
        session.commit()
    id = 1
    for row in range(16,sheet.nrows):
        try:
            rec = row_to_record(sheet.row(row),ds,id,rangeok)
            session.add(rec)
            id += 1
        except:
            sys.stderr.write(traceback())
            sys.stderr.write('Line %i: ' % (id+16))
            error = True
            break
    print "%i records saved to dataset #%i %s" % (id-1,ds.id, ds.name)
    if not error:
        session.commit()
    else:
        session.commit()
    session.close()
    
if __name__ == '__main__':
    
    if not (len(sys.argv)>1 and os.path.exists(sys.argv[1])):
        print "Usage: importxls.py <filename>"
    else:
        readvalues(sys.argv[1])
