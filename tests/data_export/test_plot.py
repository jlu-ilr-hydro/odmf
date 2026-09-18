import datetime

import pandas as pd
import pytz

from odmf.plot.plot import Plot
from odmf.plot.draw_plotly import _make_figure


def make_plot(start, end):
    return Plot(
        start=start,
        end=end,
        subplots=[
            dict(lines=[dict(
                valuetype=1,
                site=1,
                name='test line',
                color='blue',
            )]),
        ],
    )


def prepare_timeseries(timeseries, record):
    timeseries.timezone = 'Europe/Berlin'
    timeseries.access = 0
    timeseries.start = datetime.datetime(2021, 5, 9)
    timeseries.end = datetime.datetime(2021, 5, 11)
    timeseries.session().commit()
    return record


def test_plot_load_uses_dataset_timezone_with_naive_plot_bounds(timeseries, record):
    timezone = pytz.timezone('Europe/Berlin')
    prepare_timeseries(timeseries, record)
    plot = make_plot(
        datetime.datetime(2021, 5, 10),
        datetime.datetime(2021, 5, 10, 2),
    )

    line = plot.subplots[0].lines[0]
    data = line.load(*plot.get_time_span())

    assert data.index.equals(pd.DatetimeIndex([
        timezone.localize(datetime.datetime(2021, 5, 10)),
    ]))
    assert data.iloc[0] == record.value


def test_plotly_figure_accepts_aware_bounds_and_preserves_local_time(timeseries, record):
    timezone = pytz.timezone('Europe/Berlin')
    prepare_timeseries(timeseries, record)
    plot = make_plot(
        pytz.UTC.localize(datetime.datetime(2021, 5, 9, 22)),
        pytz.UTC.localize(datetime.datetime(2021, 5, 10, 2)),
    )

    figure = _make_figure(plot)

    assert len(figure.data) == 1
    assert figure.data[0].y.tolist() == [record.value]
    assert pd.Timestamp(figure.data[0].x[0]) == timezone.localize(
        datetime.datetime(2021, 5, 10)
    )
