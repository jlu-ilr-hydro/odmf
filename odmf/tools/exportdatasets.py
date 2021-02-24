'''
Exports the climate datasets as one table with multiple columns

Created on 05.06.2013

@author: kraft-p
'''

import pandas as pd
import typing

def _merge_sparse(index: pd.DatetimeIndex, series: typing.List[pd.Series], tolerance: pd.Timedelta) -> pd.DataFrame:
    """
    Applies the 'pandas.DataFrame.merge_asof' function to merge all the series using the given 'index' and 'tolerance'

    Parameters
    ----------
    index
        The target index of the merge
    series
        A list of heterogeneous timeseries
    tolerance
        The tolerance of the merge

    Returns
    -------
    pd.DataFrame

    """
    df = pd.DataFrame(index=index)
    for s in series:
        df = pd.merge_asof(df, s, left_index=True, right_index=True, tolerance=tolerance, direction='nearest')
    return df


def _merge_interpolation(
        index: pd.DatetimeIndex,
        series: typing.List[pd.Series],
        method: str,
        limit: typing.Optional[int] = None
) -> pd.DataFrame:
    """
    For each of the series extend the index with the target index, interpolate over the gaps with
    'interpolation_method' and 'interpolation_limit' and select from the result the values at the target index

    Parameters
    ----------
    index
        The target index as produced by _make_timeindex
    series
        A list of series
    method
        An interpolation method name: 'nearest', 'zero', 'slinear', 'quadratic', 'cubic': Passed to
          `scipy.interpolate.interp1d`. These methods use the numerical
          values of the index.
    limit
        Maximum length of gaps to be filled


    """
    df = pd.DataFrame(index=index)

    for s in series:
        union_index = df.index.union(s.index).unique()
        single_index_series = s[~s.index.duplicated()]
        padded_series = single_index_series.reindex(union_index)
        padded_series.interpolate(method, inplace=True, limit=limit, limit_area='inside')
        df[s.name] = padded_series.reindex(df.index)
    return df


def _make_intersection_timeindex(series: typing.List[pd.Series], tolerance: pd.Timedelta) -> pd.DatetimeIndex:
    """
    Creates a new index from the DatetimeIndex of the series, where all series (using the tolerance) have data.
    A short tolerance produces often an empty index, long tolerances can lead to data loss
    """
    union_df = _merge_sparse(series[0].index, series, tolerance)
    take = ~pd.isna(union_df).any(axis=1)
    return union_df[take].index


def _make_timeindex(series: typing.List[pd.Series], timeindexsource: typing.Union[str, int], tolerance: pd.Timedelta) -> pd.DatetimeIndex:
    """
    Creates a new timeindex based on the indices of the series and the 'timeindexsource'

    Parameters
    ----------
    series
        A list of time series
    timeindexsource
        see merge_series

    tolerance
        Tolerance for 'intersect'

    Returns
    -------

    """
    if timeindexsource == 'union':
        result = series[0].index
        return result.union_many(s.index for s in series)

    elif timeindexsource == 'intersection':
        return _make_intersection_timeindex(series, tolerance)

    elif type(timeindexsource) is int:
        return series[timeindexsource].index

    else:
        # interprete timeindexsource as frequency for a regular grid
        freq = pd.Timedelta(timeindexsource)
        start = min(s.index.min() for s in series).floor(freq)
        end = max(s.index.max() for s in series).ceil(freq)
        return pd.date_range(start, end, freq=freq)


def merge_series(
        series: typing.List[pd.Series],
        timeindexsource,
        tolerance: typing.Union[pd.Timedelta, str, None]=None,
        interpolation_method=None, interpolation_limit=None) -> pd.DataFrame:
    """
    Merges multiple time series to a dataframe using different techniques to merge the time indices


    Parameters
    ----------
    series: List of pd.Series
        List of time series

    timeindexsource: str, int

        - union - use all time steps, regularized to "tolerance"
        - intersection - use only timesteps where every series has data
        - int - use index of the series at the position indicated by the int
        - a pandas timestep (or text representation) for the frequency of a regular grid

    tolerance
        a pandas timestep (or text representation) of the allowed tolerance between indices

    interpolation_name : str, default 'nearest'
        Interpolation technique to use. One of:

        - 'nearest', 'zero', 'slinear', 'quadratic', 'cubic': Passed to
          `scipy.interpolate.interp1d`. These methods use the numerical
          values of the index.

    interpolation_limit: int
        Limits the number of NaN entries to be interpolated

    Returns
    -------
    pandas.DataFrame

    """
    if not series:
        raise ValueError('At least one series needed to create a dataframe')
    for i, s in enumerate(series):
        s.name = s.name or f'column_{i}'

    tolerance = pd.Timedelta(tolerance)
    index = _make_timeindex(series, timeindexsource, tolerance)
    index = index[~index.duplicated(keep='first')]

    if not interpolation_method:
        return _merge_sparse(index, series, tolerance)
    else:
        return _merge_interpolation(index, series, interpolation_method, interpolation_limit)


if __name__ == '__main__':
    import numpy as np
    np.random.seed(1)
    t0 = pd.Timestamp('2020-01-01', 'Min')

    def make_rnd_series(size, i):
        return pd.Series(
            np.random.uniform(0, 1, size),
            t0 + t0.freq * np.random.uniform(0, 5 * size, size).astype(int),
            name=f's{i}'
        ).sort_index()
    series = [make_rnd_series(1000, i) for i in range(10)]
    df = merge_series(
        series, '5Min', '20Min',
        interpolation_method='linear'
    )
    import io
    buf = io.BytesIO()
    df.to_parquet(buf, index=True)
    del df
    buf.seek(0)
    df2 = pd.read_parquet()
    print(df2)
