# -*- coding: utf-8 -*-
"""
Created on Fri Nov 22 11:29:07 2013

@author: houska-t
"""
import db
from traceback import format_exc as traceback
import sys
import pandas as pd
import numpy as np
import pylab as plt

def createPandaDfs(lines,start, end, fout, interpolationtime=None, tolerance=12):
    '''
    dfs:               Expects a list of Panda Dataframes with Datetime as a sorted Index
    interpolationtime: A setting String with the final Resolution of the Outputfile
    tolerance:         Maximum Timesteps of interpolationtime which will be interpolated 
    '''
    try:
        dfs=[]
        #Loop through Lines
        for line in lines:
            Column_name=str(line.site)[0:3]+str(' - ')+str(line.valuetype)[0:10]
            try:
                Time, Value = line.load(startdate=start,enddate=end,usecache=True)
            except ValueError:
                print 'Leave out zero size array in line '+str(line)
                continue
            #Make Panda Dataframes
            index=pd.Index(plt.num2date(Time),name='Date')
            dfs.append(pd.DataFrame(data=Value,index=index,columns=[Column_name]))
        
        if interpolationtime:
            #Create Regular Timeseries
            reg_time=pd.date_range(start=start, end=end, freq=interpolationtime)
            #append the Panda Dataframes with the Regular Timeseries
            dfs.append(pd.DataFrame(data=np.empty(len(reg_time)),index=reg_time,columns=['reg_time']))
        
        #Make one big Panda Dataframe and interpolate through missing values
        con=pd.concat(dfs)
        sort=con.sort_index()
	print sort.head(10)
	print Column_name
	print tolerance
	print type(tolerance)
        #inter=sort.interpolate(limit=float(tolerance), method='time')
        inter=sort.interpolate(limit=int(tolerance), method='time')
	#Delete duplicates in the Index
        inter['index'] = inter.index
        df=inter.drop_duplicates(cols='index')
        if interpolationtime:
            del df['reg_time']
        del df['index']
        #Select the rows with indices of the last dataframe:
        # if interpolationtime=None: indices of the last line
        #else: indices of reg_time
        reg_df=df.reindex(dfs[-1].index)
        reg_df=reg_df.drop(reg_df.index[:1])
        reg_df.index.name='Date'
        #Export Data to csv
        reg_df.to_csv(fout)
    
    except:
        sys.stderr.write(traceback())
       
