# -*- coding:utf-8 -*-
# !/usr/bin/python

'''
Created on 21.05.2012

@author: philkraf
'''

from . import db
# Import smtplib for the actual sending function
import sys
# Import the email modules we'll need
from .tools.mail import EMail, send
from datetime import datetime
msgtemplate = """
Liebe/r %(you)s,

bis %(due)s sollte "%(job)s" erledigt werden und Du bist dafür eingetragen. Wenn der Job noch warten kann,
ändere doch einfach das Datum (due).
Falls etwas unklar ist, bitte nachfragen. Wenn Du die Aufgabe schon erledigt hast
gehe bitte auf http://fb09-pasig.umwelt.uni-giessen.de:8081/job/%(id)s
und hake den Job ab.

Danke und Schöne Grüße

%(me)s

P.S.: Diese Nachricht wurde automatisch von der Schwingbach-Datenbank generiert

Dear %(you)s,

the task "%(job)s" in the Schwingbach area was due at %(due)s, and you have been assigned
for it. If the job can wait, please change the due date. If you have any questions regarding this task, do not hesitate to ask. If you have already
finished the tasked, please mark it as done at http://fb09-pasig.umwelt.uni-giessen.de:8081/job/%(id)s.

Thank you,

with kind regards

%(me)s

This mail has been generated automatically from the Schwingbach database
"""


if __name__ == "__main__":
    session = db.Session()
    today = datetime.today()
    print(today.strftime('%d.%m.%Y %H:%M'))
    mails = []
    for job in session.query(db.Job).filter(db.Job.done is False, db.Job.due < today):
        if job.is_due():
            if job.description:
                job.parse_description(action='due')
            subject = 'Studienlandschaft Schwingbach: %s' % job.name
            msgdata = dict(id=job.id, you=job.responsible.firstname, due=job.due, job=job.name, descr=job.description,
                           me=job.author.firstname)
            msg = msgtemplate % msgdata
            mails.append(EMail(job.author.email, [
                         job.responsible.email], subject, msg))
            print(("    %s->%s: %s" % (job.author.username,
                                       job.responsible.username, job.name)).encode('utf-8'))
    send(mails)
