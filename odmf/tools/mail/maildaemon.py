"""
A mail daemon thread. Runs together with the website and sends messages when they are due.
"""


import typing
from datetime import datetime, timedelta
from threading import Timer
import logging
from odmf.config import conf
from odmf.db import session_scope, Job, sql, flex_get
from odmf.db.message import Message
from odmf.db.timeseries import DatasetAlarm

logger = logging.getLogger(__name__)

class MailDaemon(Timer):
    """
    The MailDaemon is thread that runs in the background together with the web server. It looks for the
    jobs and other mailing objects and sends messages if needed.
    """
    def __init__(self, interval: int = 3600):
        """
        Create a new MailDaemon
        :param interval: interval between runs in seconds, default is hourly
        """
        super().__init__(interval, None)

    @staticmethod
    def messages(session, date, source) -> int:
        """
        Returns the number of messages fired from a source after the given date. Use to figure out if a message
        is already sent. If no message has sent since it is due the function returns 0
        """
        stmt = sql.select(sql.func.count(Message.id)).where(Message.source == source).where(
            Message.date >= date)
        return session.scalar(stmt)

    @staticmethod
    def handle_jobs():
        """
        Gets all active jobs with a when-list in the mailer and checks if a message is due and not already sent.
        """
        with session_scope() as session:
            # Get all active jobs with a mailer that has a when-list
            stmt = sql.select(Job).where(sql.not_(Job.done)).where(Job.mailer.isnot(None))
            jobs: typing.List[Job] = session.scalars(stmt)

            for job in jobs:
                # Handle "when" messages of jobs
                dates = job.message_dates()
                # if there are due dates left, test if messages have been sent after the latest
                if dates and not MailDaemon.messages(session, max(dates), f'job:{job.id}'):
                    msg = job.as_message()
                    session.add(msg)
                    msg.send()

                # Handle overdue jobs
                yesterday = datetime.now() - timedelta(days=1)
                if (
                        flex_get(job.mailer, 'reminder')
                        and job.due < datetime.now()
                        and 7 < yesterday.hour < 18
                        and not MailDaemon.messages(session, yesterday, f'job:{job.id}')
                ):
                    msg, cc = job.as_overdue_message()
                    session.add(msg)
                    msg.send(*cc)

    def handle_alarms(self):
        """
        Check all active dataset alarms and sent messages if necessary
        """
        with session_scope() as session:
            # Get all active jobs with a mailer that has a when-list
            alarms: typing.List[DatasetAlarm] = session.scalars(
                sql.select(DatasetAlarm).where(DatasetAlarm.active)
            )
            for alarm in alarms:
                date = datetime.now() - timedelta(days=alarm.message_repeat_time)
                if (msg_text := alarm.check()) and not self.messages(session, date, alarm.msg_source()):
                    msg = Message(
                        subject='ODMF:' + str(alarm),
                        topics=[alarm.topic],
                        content=msg_text,
                        source=alarm.msg_source()
                    )
                    session.add(msg)
                    msg.send()

    def run(self):
        """
        Repeats the calls to handle_jobs until the timer expires.
        :return:
        """
        while not self.finished.wait(self.interval):
            logger.info('MailDaemon: Check jobs & alarms')
            self.handle_jobs()
            self.handle_alarms()









