'''
Exports the climate datasets as one table with multiple columns

Created on 05.06.2013

@author: kraft-p
'''
import codecs
from datetime import datetime, timedelta
import pandas as pd
import typing
import matplotlib.dates
t0 = datetime(1, 1, 1)


def num2date(t):
    return t0 + timedelta(days=t)


def _make_intersection_timeindex(series: typing.List[pd.Series], tolerance: str) -> pd.DatetimeIndex:
    ...


def _make_timeindex(series: typing.List[pd.Series], timeindexsource: typing.Union[str, int], tolerance: str) -> pd.DatetimeIndex:

    if timeindexsource == 'union':
        result = series[0].index
        return result.union_many(s.index for s in series)

    elif timeindexsource == 'intersection':
        return _make_intersection_timeindex(series, tolerance)

    elif type(timeindexsource) is int:
        return series[timeindexsource].index

    else:
        # interprete timeindexsource as frequency for a regular grid
        freq = timeindexsource
        start = min(s.index.min() for s in series).floor(freq)
        end = max(s.index.max() for s in series).ceil(freq)
        return pd.date_range(start, end, freq=freq)


def merge_series(
        series: typing.List[pd.Series],
        timeindexsource: typing.Union[str, int],
        tolerance: typing.Union[pd.Timedelta, str, None]=None,
        interpolation=None) -> pd.DataFrame:
    """
    Merges multiple time series to a dataframe using different techniques to merge the time indices


    Parameters
    ----------
    series
        List of time series

    timeindexsource
        Indicator of what to use for the timeindex:

        * "union" - use all time steps, regularized to "tolerance"
        * "intersection" - use only timesteps where every series has data
        * int - use index of the series at the position indicated by the int
        * a pandas timestep (or text representation) for the frequency of a regular grid

    tolerance
        a pandas timestep (or text representation) of the allowed tolerance between indices

    interpolation : str, default 'nearest'
        Interpolation technique to use. One of:

        * 'index', 'values': use the actual numerical values of the index.
        * 'pad': Fill in NaNs using existing values.
        * 'nearest', 'zero', 'slinear', 'quadratic', 'cubic': Passed to
          `scipy.interpolate.interp1d`. These methods use the numerical
          values of the index.  Both 'polynomial' and 'spline' require that
          you also specify an `order` (int), e.g.
          ``df.interpolate(method='polynomial', order=5)``.


    Returns
    -------

    """
    if not series:
        raise ValueError('At least one series needed to create a dataframe')
    tolerance = pd.Timedelta(tolerance)
    index = _make_timeindex(series, timeindexsource, tolerance)
    df = pd.DataFrame(index=index)
    if not interpolation:
        for s in series:
            df = pd.merge_asof(df, s, left_index=True, right_index=True, tolerance=tolerance, direction='nearest')
    else:
        for s in series:
            ...


def exportLines(fout, lines, tolerance=60):
    """
    Exports multiple lines from a plot as a table with each line as a column
    To align the values in the rows a tolerance is chosen, by which measure
    times may differ, but should still be combined in the same row.
    """
    # Make sure the tolerance is > 0
    tolerance = max(tolerance, 0.01)

    # prepare the output file, Excel needs the BOM to recognize csv files with
    # UTF-8
    fout.write(codecs.BOM_UTF8.decode('utf-8'))

    # simplify fileoutput
    def writeline(line):
        fout.write(','.join((str(s)
                             if s else '') for s in line) + '\n')

    # Write headers
    fout.write('time,')
    writeline(lines)
    fout.write('\n')

    # Load all time and value arrays for the lines. This is a huge memory
    # consumer
    tvpairs = [l.load() for l in lines]
    # Create counters, holding the position of a line point
    counters = [0] * len(tvpairs)
    # Last time step
    told = 0.0
    # Hold the data of the current line
    linedata = []
    # Loop on with the counters until all data is consumed
    while any(c < len(tv[0]) for c, tv in zip(counters, tvpairs)):
        # Get the current time step
        t = min(tv[0][c] for c, tv in zip(counters, tvpairs) if c < len(tv[0]))
        # If the current time step is past the tolerance time in seconds
        if t - told >= tolerance / 86400.:
            # Get the datetime
            time = matplotlib.dates.num2date(t).strftime("%Y-%m-%d %H:%M:%S")
            # Save the current linedata to the file
            if linedata:
                writeline(linedata)
            # Make a new linedata
            linedata = [time] + ([None] * len(lines))
            # Current t gets the old time
            told = t

        # Populate the linedata for each line
        for i in range(len(lines)):
            # Check if there is data left and the current data is inside the
            # tolerance time
            if (counters[i] < len(tvpairs[i][0]) and
                    tvpairs[i][0][counters[i]] - t < tolerance):
                # Get the value
                linedata[i + 1] = tvpairs[i][1][counters[i]]
                # Move on with counter
                counters[i] += 1
