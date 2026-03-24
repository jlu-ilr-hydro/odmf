import io
import json
import cherrypy
import pandas as pd

from . import root
from ..test_db.test_dbdataset import *

def response_to_json(res: bytes):
    return json.loads(res.decode())


@pytest.fixture
def apilogin(root):
    res = root.api.login(username='odmf.admin', password='test')
    assert res.decode('utf-8') == 'OK'
    return root.api

class TestDatasetAPI:

    def test_index(self, root, timeseries):
        res = response_to_json(
            root.api.dataset.index('ds1')
        )
        assert res.get('id') == 1


    def test_records(self, apilogin, timeseries, thousand_records):
        res = response_to_json(
            apilogin.dataset.records('ds1')
        )
        assert len(res) == 1000

    def test_values(self, apilogin, timeseries, thousand_records):
        timeseries.calibration_offset = 100
        res = response_to_json(
            apilogin.dataset.values('ds1')
        )
        assert len(res) == 1000
        # ser = pd.Series(res)
        # assert all(ser > 0)

    def test_values_parquet(self, apilogin, timeseries, thousand_records):
        timeseries.calibration_offset = 100
        timeseries.session().commit()
        buf = io.BytesIO()
        buf.write(apilogin.dataset.values_parquet('ds1'))
        buf.seek(0)
        df = pd.read_parquet(buf)
        assert len(df) == 1000
        assert sum(df.value < 0) == 0

    def test_list(self, apilogin, timeseries):
        res = response_to_json(
            apilogin.dataset.list()
        )
        assert len(res) == 1
        assert res == [1]

    @pytest.mark.skip('tot test deletion, existing timeseries may not be temporary')
    def test_delete(self, apilogin, timeseries):
        apilogin.login(username='odmf.admin', password='test')
        res = response_to_json(apilogin.dataset.delete(dsid=1))
        assert res['status'] == 'success'
        assert apilogin.dataset.list() == '0'


    def test_new(self, apilogin, db, timeseries):
        apilogin.login(username='odmf.admin', password='test')
        data = dict(
            measured_by='odmf.admin',
            valuetype=1,
            quality=1,
            site=1,
            source=1
        )
        res = apilogin.dataset.new(**data).decode()
        assert res == 'ds2'
        with db.session_scope() as session:
            assert db.Dataset.get(session, 2).id == 2

    def test_addrecord(self, apilogin, timeseries):
        apilogin.login(username='odmf.admin', password='test')
        res = apilogin.dataset.addrecord(
            dsid='ds1',
            value='2.5',
            time='2020-02-20 07:15:00',
        )
        assert res.decode() == '1'
        rec = timeseries.records.first()
        assert rec.value == 2.5

    def test_statistics(self, apilogin, timeseries, thousand_records):
        res = response_to_json(apilogin.dataset.statistics('ds1'))
        assert 'n' in res
        assert 'mean' in res
        assert 'std' in res
        assert res['n'] == 1000

    @pytest.mark.parametrize('with_id', [True, False])
    def test_addrecords_parquet(self, with_id, apilogin, timeseries):
        import pandas as pd
        df = pd.DataFrame(index=pd.RangeIndex(1, 1001, 1))
        df['dataset'] = 1
        if with_id:
            df['id'] = df.index
        df['value'] = (df.index - 500) * 0.01
        df['time'] = pd.date_range('2022-01-01 12:00:00', '2023-01-03 23:00', freq='h')[:1000]
        df.reset_index(inplace=True)
        stream = io.BytesIO()
        df.to_parquet(stream)
        stream.seek(0)
        cherrypy.request.body = stream

        res = response_to_json(
            apilogin.dataset.addrecords_parquet()
        )
        # Check response
        assert res['status'] == 'success'
        assert res['records'] == 1000
        assert res['datasets'] == [1]

        # Check database
        assert timeseries.records.count() == 1000

    def test_addrecords_json_withid(self, apilogin, timeseries):
        import datetime, io
        start = datetime.datetime(2022,1,1,12)
        records = [
            dict(
                recid=n,
                value=(n-500) * 0.01,
                time=(start + datetime.timedelta(days=n)).isoformat(),
                dataset=1
            )
            for n in range(1000)
        ]
        buffer = io.BytesIO()
        buffer.write(json.dumps(records).encode('utf-8'))
        buffer.seek(0)
        cherrypy.request.body = buffer

        res = response_to_json(
            apilogin.dataset.addrecords_json()
        )
        # Check response
        assert res['status'] == 'success'
        assert res['records'] == 1000
        assert res['datasets'] == [1]
        # Check database
        assert timeseries.records.count() == 1000

    def test_end_times(self, apilogin, timeseries):
        res = response_to_json(apilogin.dataset.end_times(datasets='1'))
        assert len(res) == 4, f'Expected 4 entries, ds:1, min, max, missing Got {len(res)}'
        assert res['ds:1'] == timeseries.end.isoformat()
        assert res['ds:1'] == res['min'] == res['max']


