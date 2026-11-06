import io

import pandas as pd
import pytz

from odmf.tools.exportdatasets import export_dataframe


def test_export_dataframe_excel_accepts_timezone_aware_data():
    timezone = pytz.timezone('Europe/Berlin')
    index = pd.DatetimeIndex([
        timezone.localize(pd.Timestamp('2021-05-10 00:00:00')),
    ])
    data = pd.DataFrame({
        'value': [5.0],
        'measured_at': index,
    }, index=index)

    stream = io.BytesIO()
    export_dataframe(stream, data, 'xlsx', index_label='time')

    assert stream.getbuffer().nbytes > 0
    stream.seek(0)
    exported = pd.read_excel(stream, index_col='time')
    assert exported.index.tz is None
    assert exported.measured_at.iloc[0] == pd.Timestamp('2021-05-10 00:00:00')
