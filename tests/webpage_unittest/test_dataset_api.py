import io
import json
import cherrypy
import pandas as pd

from . import root
from ..test_db.test_dbdataset import *

def response_to_json(res: bytes):
    return json.loads(res.decode())

class TestDatasetAPI:

    def test_index(self, root, timeseries):
        res = response_to_json(
            root.api.dataset.index('ds1')
        )
        assert res.get('id') == 1

    def test_records(self, root, timeseries, thousand_records):
        res = response_to_json(
            root.api.dataset.records('ds1')
        )
        assert len(res) == 1000

    def test_values(self, root, timeseries, thousand_records):
        timeseries.calibration_offset = 100
        res = response_to_json(
            root.api.dataset.values('ds1')
        )
        assert len(res) == 1000
        # ser = pd.Series(res)
        # assert all(ser > 0)

    def test_values_feather(self, root, timeseries, thousand_records):
        timeseries.calibration_offset = 100
        timeseries.session().commit()
        buf = io.BytesIO()
        buf.write(root.api.dataset.values_feather('ds1'))
        buf.seek(0)
        df = pd.read_feather(buf)
        assert len(df) == 1000
        assert sum(df.value < 0) == 0

    def test_list(self, root, timeseries):
        res = response_to_json(
            root.api.dataset.list()
        )
        assert len(res) == 1
        assert all(url.split('/')[-1][:2] == 'ds' for url in res)

    def test_new(self, root, db, timeseries):
        cherrypy.request.json = dict(
            measured_by='odmf.admin',
            valuetype=1,
            quality=1,
            site=1,
            source=1
        )
        res = root.api.dataset.new().decode()
        assert res == 'ds2'
        with db.session_scope() as session:
            assert db.Dataset.get(session, 2).id == 2

    def test_addrecord(self, root, timeseries):
        res = root.api.dataset.addrecord(
            dsid='ds1',
            value='2.5',
            time='2020-02-20 07:15:00',
        )
        assert res.decode() == '1'
        rec = timeseries.records.first()
        assert rec.value == 2.5

    def test_statistics(self, root, timeseries, thousand_records):
        res = response_to_json(root.api.dataset.statistics('ds1'))
        assert 'n' in res
        assert 'mean' in res
        assert 'std' in res
        assert res['n'] == 1000

    @pytest.mark.parametrize('with_id', [True, False])
    def test_addrecords_feather(self, with_id, root, timeseries):
        import pandas as pd
        df = pd.DataFrame(index=pd.RangeIndex(1, 1001, 1))
        df['dataset'] = 1
        if with_id:
            df['id'] = df.index
        df['value'] = (df.index - 500) * 0.01
        df['time'] = pd.date_range('2022-01-01 12:00:00', '2023-01-03 23:00', freq='h')[:1000]
        df.reset_index(inplace=True)
        stream = io.BytesIO()
        df.to_feather(stream)
        cherrypy.request.body = stream

        res = response_to_json(
            root.api.dataset.addrecords_feather()
        )
        # Check response
        assert res['status'] == 'success'
        assert res['records'] == 1000
        assert res['datasets'] == [1]

        # Check database
        assert timeseries.records.count() == 1000






