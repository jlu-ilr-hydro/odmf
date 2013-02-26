# -*- coding:utf-8 -*-
#!/usr/bin/python

'''
Created on 21.05.2012

@author: philkraf
'''

import db
# Import smtplib for the actual sending function
import smtplib
import sys
# Import the email modules we'll need
from email.mime.text import MIMEText

from datetime import datetime
msgtemplate = u"""
Liebe/r %(you)s,

bis %(due)s sollte "%(job)s" erledigt werden und Du bist dafür eingetragen.
Falls etwas unklar ist, bitte nachfragen. Wenn Du die Aufgabe schon erledigt hast
gehe bitte auf http://fb09-pasig.umwelt.uni-giessen.de:8081/job/%(id)s 
und hake den Job ab.

Danke und Schöne Grüße

%(me)s

P.S.: Diese Nachricht wurde automatisch von der Schwingbach-Datenbank generiert

Dear %(you)s,

the task "%(job)s" in the Schwingbach area was due at %(due)s, and you have been assigned
for it. If you have any questions regarding this task, do not hesitate to ask. If you have already 
finished the tasked, please mark it as done at http://fb09-pasig.umwelt.uni-giessen.de:8081/job/%(id)s.

Thank you,

with kind regards

%(me)s

This mail has been generated automatically from the Schwingbach database 
"""

    

def sendmail(job,s,simulate=False):
    me = job.author.email
    you = job.responsible.email

    msgdata = dict(id=job.id,you=job.responsible.firstname,due=job.due,job=job.name,descr=job.description,
                        me=job.author.firstname)
    msg = msgtemplate % msgdata

    # Create a text/plain message
    msg = MIMEText(msg.encode('utf-8'),'plain','utf-8')
    
    msg['Subject'] = 'Studienlandschaft Schwingbach: %s' % job.name
    msg['From'] = me
    msg['To'] = you
    print (u"    %s->%s: %s" % (job.author.username,job.responsible.username,job.name)).encode('utf-8')
    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    if not simulate:
        s.sendmail(me, [you], msg.as_string())

if __name__=="__main__":
    session = db.Session()
    today = datetime.today()
    simulate = 'test' in sys.argv
    s = smtplib.SMTP('mailout.uni-giessen.de')
    print today.strftime('%d.%m.%Y %H:%M')
    for job in session.query(db.Job).filter(db.Job.done==False,db.Job.due<today):
        sendmail(job,s,simulate)
    s.quit()
