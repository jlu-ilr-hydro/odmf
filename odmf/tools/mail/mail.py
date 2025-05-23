'''
Created on 20.03.2013

@author: kraft-p
'''
import smtplib
from email.message import EmailMessage
from email.headerregistry import Address
import yaml
import logging

logger = logging.getLogger(__name__)


class EmailError(Exception):
    ...

class Mailer:
    """
    Reads the email configuration file and sends it to the given receivers. Uses STARTTLS.

    The email-config file must be in the same directory as the config.yml and named email.yml

    Example:
    ~~~~~~~~~~~~~~~~~~~~
    server: smtp.gmail.com
    port: 587
    login: <USERNAME or EMAIL>
    password: <PASSWORD>
    email: <EMAIL>
    name: odmf: no reply
    ~~~~~~~~~~~~~~~~~~~

    Usage:

    >>> with Mailer(
    >>>         server='smtp.gmail.com', port='587',
    >>>         login='test@example.com', password='1234',
    >>>         email='me@example.com', name='ODMF'
    >>>     ) as mailer:
    >>>         mailer.send(
    >>>             subject='ODMF: Your job is due',
    >>>             body='Eat your vegetables!',
    >>>             receivers=['<EMAIL>', '<EMAIL>']
    >>>         )
    """
    def __init__(self, filename=None, **kwargs):
        if filename:
            with open(filename) as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}
        self.config.update(kwargs)
        self.server = None

    def start(self):
        self.server =  smtplib.SMTP(self.config['server'], self.config.get('port', 587))
        self.server.starttls()
        self.server.login(self.config['login'], self.config['password'])
        return self

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.server.quit()
        self.server = None

    def send(self, subject, body, receivers):
        if not self.server:
            raise EmailError("No server started, use as: with Mailer('email.yml') as mailer: mailer.send_mail(subject, body, *receivers)")
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = Address(self.config.get('name', 'odmf: no reply'),
                              addr_spec=self.config.get('email', self.config['login']))
        msg['To'] = ','.join(receivers)
        logging.debug('Sending email to %s', ', '.join(receivers))

        self.server.send_message(msg)
        logger.info('Email sent to %s', ', '.join(receivers))

