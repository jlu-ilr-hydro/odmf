'''
Created on 21.05.2012

@author: philkraf
'''

import db

if __name__=="__main__":
    session = db.Session()
    for job in session.query(db.Job):
        job.send_mail()