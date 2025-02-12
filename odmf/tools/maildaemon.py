"""
A mail daemon thread. Runs together with the website and sends messages when they are due.
"""


import typing
from datetime import datetime, timedelta
from threading import Timer
import logging

from odmf.db import session_scope, Job, sql
from odmf.db.message import Message

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

    def messages(self, session, date, source) -> int:
        """
        Returns the number of messages fired from a source after the given date. Use to figure out if a message
        is already sent. If no message has sent since it is due the function returns 0
        """
        stmt = sql.select(sql.func.count(Message.id)).where(Message.source == source).where(
            Message.date >= date)
        return session.scalar(stmt)

    def handle_jobs(self):
        """
        Gets all active jobs with a when-list in the mailer and checks if a message is due and not already sent.
        """
        with session_scope() as session:
            # Get all active jobs with a mailer that has a when-list
            stmt = sql.select(Job).where(~Job.done).where(Job.mailer['when'] != sql.JSON.NULL)
            jobs: typing.List[Job] = session.scalars(stmt)

            for job in jobs:
                when = list(job.mailer.get('when', []))
                # Get all due dates of the job messages (only for int entries)
                dates = [job.due - timedelta(days=days) for days in when if type(days) is int]
                # Filter only the dates that are in the past
                dates = [d for d in dates if d < datetime.now()]
                # if there are due dates left, test if messages have been sent after the latest
                if dates and not self.messages(session, max(dates), f'job:{job.id}'):
                    # get the message
                    msg = job.as_message()
                    session.add(msg)
                    # remove when entry
                    msg.send()

    def run(self):
        """
        Repeats the calls to handle_jobs until the timer expires.
        :return:
        """
        while not self.finished.wait(self.interval):
            self.handle_jobs()









