'''
Created on 20.03.2013

@author: kraft-p
'''
import smtplib
from email.mime.text import MIMEText

def send(mails):
    s = smtplib.SMTP('mailout.uni-giessen.de')
    for mail in mails:
        msg = MIMEText(mail.text.encode('utf-8'),'plain','utf-8')
        msg['Subject'] = mail.subject
        msg['From'] = mail.author
        msg['To'] = mail.receivers[0]
        s.sendmail(mail.author,mail.receivers,msg.as_string())
    s.quit()


class EMail(object):
    def __init__(self,author,receivers,subject,text):
        self.author=author
        self.receivers = receivers
        self.subject=unicode(subject)
        self.text=unicode(text)
    def send(self):
        send([self])

        