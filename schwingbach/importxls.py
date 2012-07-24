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
        time%=1.0
        date=round(date)
    return t0 + timedelta(date+time)

def row_to_record(row,dataset,id):
    rec=db.Record(id=id,dataset=dataset)
    rec.time = get_time(row[0].value,row[1].value)
    try:
        rec.value = float(row[2].value)
    except ValueError, TypeError:
        rec.value = None
    if row[3].value:
        rec.sample = row[3].value
    comment=(', '.join([unicode(c.value) for c in row[4:] if c.value])).strip()
    if comment:
        rec.comment = comment
    return rec
        
                

def readvalues(xlsfilename):
    wb = xlrd.open_workbook(xlsfilename)
    sheet = wb.sheet_by_index(0)
    
    id = int(sheet.cell_value(3,1))
    
    session = db.Session()
    ds = session.query(db.Dataset).get(id)
    if not ds:
        sys.stderr.write('Dataset %i not found in database. File %s is not imported\n' % (id,xlsfilename))
        return None
    id = 1
    for row in range(16,sheet.nrows):
        try:
            rec = row_to_record(sheet.row(row),ds,id)
            session.add(rec)
            id += 1
        except:
            sys.stderr.write('Line %i: ' % (id+16))
            sys.stderr.write(traceback()+'\n')
            exit()
    print "%i records saved to dataset #%i %s" % (id-1,ds.id, ds.name)
    session.commit()
    session.close()
    
if __name__ == '__main__':
    
    if not (len(sys.argv)>1 and os.path.exists(sys.argv[1])):
        print "Usage: importxls.py <filename>"
    else:
        readvalues(sys.argv[1])