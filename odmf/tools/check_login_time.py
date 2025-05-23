import re
import pandas as pd


def parse_access_log(fn='access.log'):
    """
    Reads the access log and returns a dataframe
    :param fn:
    :return:
    """
    pattern = re.compile(r'([0-9\.]*) - (.*?) \[(.*?)\] \"(.*?)\" ([0-9]*) ([0-9\-]*) \"(.*?)\" \"(.*?)\"')
    names = 'ip','user','date','request','status', 'content_length', 'uri', 'browser'

    with open(fn) as f:
        df = pd.DataFrame(
            [
                dict(
                    zip(names, pattern.match(l).groups())
                ) for l in f
            ]
        )
    df['date'] = pd.to_datetime(df['date'], format='%d/%b/%Y:%H:%M:%S')
    return df

def deactivate_old_users(access:pd.DataFrame, critical_time:str = '365d'):
    """
    Deactivates any user who did not login for a year
    :param access: parsed access log
    :param critical_time: Timespan
    """
    from odmf import db
    crit_date = pd.to_datetime() - pd.to_timedelta(critical_time)
    access = access[access['date'] >= crit_date]
    with db.session_scope() as session:
        inactive_users = session.query(~db.Person.username.in_(access.user.unique()))
        for user in inactive_users:
            user.active = False

