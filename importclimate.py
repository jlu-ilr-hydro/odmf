#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Jun 28, 2012
@author: Philipp Kraft
"""

from __future__ import division
import sys
import openpyxl
import db
from datetime import datetime,timedelta

class ClimateImporter:
    def getdata(self,cols):
        data=[]
        row=self.firstrow
        cell = self.sheet.cell
        t0 = datetime(2010,1,1) 
        while True:
            if row % 10000 == 0:
                sys.stdout.write('\n%i' % row)
            if row % 1000==0:
                sys.stdout.write('.')
                sys.stdout.flush()
            v=cell(row=row,column=0).value
            if v is None:
                break
            sec = (v-t0).total_seconds()
            d = tuple(cell(row=row,column=c).value for c in cols)
            t =  t0 + timedelta(seconds=round(sec))
            data.append((t,d))
            row+=1
                
        sys.stdout.write('\n%i' % row)
        return data
    def __init__(self,workbookfilename,site,user):
        wb = openpyxl.load_workbook(workbookfilename)
        self.filename=workbookfilename
        self.sheet = wb.worksheets[0]
        self.firstrow = 4 
        self.site=site
        self.user=user
        self.vtcoldict={5:(9,288.,0), # rainfall
                        6:(8,1.,1), # Temperature
                        7:(10,1.,2), # Humidity
                        12:(11,1.,3), # solar radiation
                        15:(12,1.,4), # Wind speed
                        }
        self.data=self.getdata(sorted(self.vtcoldict.keys()))
        
    
    def importcolumn(self,column,name):
        session=db.Session()
        user = session.query(db.Person).get(self.user)
        site = session.query(db.Site).get(self.site)
        vt_id,factor,pos = self.vtcoldict[column]
        valuetype = session.query(db.ValueType).get(vt_id)
        dsid = db.newid(db.Dataset, session)
        ds = db.Dataset(id=dsid,site=site,measured_by=user,valuetype=valuetype,
                        start=self.data[0][0],end=self.data[-1][0],name=name)
        session.add(ds)
        id=0
        for t,d in self.data:
            v = d[pos]
            if not (t is None or v is None):
                session.add(db.Record(dataset=ds,id=id,time=t,value=v*factor))
            id+=1
        session.commit()
        
                
                
        
        
        