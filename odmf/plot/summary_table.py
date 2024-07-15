"""
Calculates a summary table for a specific timespan, starting from the latest date
"""
import typing
import datetime

import numpy as np
import pandas as pd
from .. import db
def summarize_item(
        session, timespan: typing.Optional[pd.Timedelta]=None,
        aggregate: str='mean',
        name:str = '',
        valuetype: typing.Optional[int]=None,
        site: typing.Optional[int]=None,
        level: typing.Optional[float]=None,
        user: typing.Optional[str]=None,
        instrument: typing.Optional[int]=None,
        date: typing.Optional[datetime.datetime]=None,
        type: typing.Optional[str]=None,
        factor: typing.Optional[float]=None,
        **kwargs
):
    """
    Takes a summary item (group of matching datasets) and returns a summary
    :param session: The sqlalchemy session
    :param timespan: Pandas Timespan - the time span to summarize, counts from the last datapoint
    :param aggregate: Aggregation function like mean, max, min, sum, std etc. See func parameter in pandas.Series.agg
    :param name: Name to report. If not given a name is constructed from valuetype, site and level
    :param valuetype: Valuetype id to summarize, should be given
    :param site: Site id
    :param level: Measurement level, important to seperate multiple measured valuetypes at the same site
    :param user: Filter by user, usually left blank
    :param instrument: Source id
    :param date: Additional date filte
    :param type: timeseries or transformed_timeseries
    :return: A dict with name, value, unit, aggregation and n (number of measurements)
    """
    ds_filter = db.Dataset.filter(session, None, valuetype, user, site, date, instrument, type, level)
    if not ds_filter.count():
        return dict(name='No data', value = np.NaN, unit='', aggregation=aggregate, n=0, start = pd.NaT, end=pd.NaT)
    else:
        end = max(ds.end for ds in ds_filter)
        start = min(ds.start for ds in ds_filter)
        if timespan:
            start = max(start, end - timespan)
        vt: db.ValueType = db.ValueType.get(session, valuetype)
        if not name:
            name = f'{vt.name} at site #{site}'
            if level is not None:
                name += f' in {level} m'
        group = db.DatasetGroup([ds.id for ds in ds_filter],start, end)
        series = group.asseries(session)
        factor = factor or 1.0
    return dict(name=name, value=series.agg(aggregate) * factor, unit=vt.unit, aggregation=aggregate, n=len(series), start=start, end=end)

def summary(time: str, items: typing.List[typing.Dict]) -> pd.DataFrame:
    """
    Returns a DataFrame containing the summary for a number of summary items

    :param session: The sqlalchemy session
    :param time: A string to be converted in a pd.TimeDelta, eg. 24H, 7d
    :param items: A list of dicts. Each dict contains dataset filters. `valuetype`, and `site` are necessary, `level` often, too.
                  See help(summarize_item) for more filters.
    :return:
    """

    timespan = pd.Timedelta(time)
    with db.session_scope() as session:
        return pd.DataFrame([
            summarize_item(session, timespan, **item)
            for item in items
        ])


