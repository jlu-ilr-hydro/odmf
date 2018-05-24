'''
Created on 15.10.2012

@author: philkraf
'''
from math import sqrt

import db


class Match:
    def __init__(self, time, target, source, dt):
        self.target = target
        self.time = time
        self.source = source
        self.dt = dt

    def delta(self):
        return self.source - self.target


class CalibrationSource:
    def __init__(self, datasetids, start=None, end=None):
        self.datasets = datasetids
        self.start = start
        self.end = end

    def records(self, session):
        return session.query(db.Record).filter(db.Record._dataset.in_(self.datasets),
                                               ~db.Record.is_error,
                                               db.Record.time >= self.start,
                                               db.Record.time <= self.end)


class Calibration:
    def __len__(self):
        return len(self.matches)

    def __init__(self, target=None, source=None, limit=3600):
        self.target = target
        self.source = source
        self.matches = []
        if target and source:
            sourcerecords = self.source.records(self.target.session())
            for sr in sourcerecords:
                # Change the time of source record from source timezone to the target timezone
                time = sr.time - \
                    sr.dataset.tzinfo.utcoffset(
                        sr.time) + self.target.tzinfo.utcoffset(sr.time)
                tv, dt = target.findvalue(time)
                if dt <= limit:
                    self.matches.append(Match(sr.time, tv, sr.calibrated, dt))
        self.slope = 1.0
        self.offset = 0.0
        self.meanoffset = 0.0
        self.r2 = 0.0
        self.rmse = 0.0
        self.rmse_lr = 0.0
        self.rmse_off = 0.0
        self.target_mean = 0.0
        self.source_mean = 0.0
        self.source_std = 0.0
        self.target_std = 0.0
        self.refresh()

    def __iter__(self):
        for m in self.matches:
            yield dict(t=m.time, source=m.source, target=m.target,
                       lr=m.target * self.slope + self.offset,
                       off=m.target + self.meanoffset,
                       dt=m.dt,
                       )

    def refresh(self):
        if len(self.matches) > 1:
            self.target_mean = self.source_mean = 0.0
            n = float(len(self))
            for m in self.matches:
                self.target_mean += m.target / n
                self.source_mean += m.source / n
            cov = var_s = var_t = se = 0.0
            for m in self.matches:
                cov += (m.target - self.target_mean) * \
                    (m.source - self.source_mean)
                var_s += (m.source - self.source_mean)**2
                var_t += (m.target - self.target_mean)**2
                se += (m.target - m.source)**2
            self.meanoffset = self.source_mean - self.target_mean
            self.slope = cov / var_t
            self.offset = self.source_mean - self.slope * self.target_mean
            self.target_std = sqrt(var_t)
            self.source_std = sqrt(var_s)
            self.rmse = sqrt(se / n)
            se_lr = se_off = 0.0
            for m in self.matches:
                se_lr += ((m.target * self.slope + self.offset) - m.source)**2
                se_off += (m.target + self.meanoffset - m.source)**2
            self.rmse_lr = sqrt(se_lr / n)
            self.rmse_off = sqrt(se_off / n)
            # Variant:
            # self.slope = cov/var_s
            # self.offset = self.target_mean - self.slope * self.source_mean
            try:
                self.r2 = cov**2 / (var_s * var_t)
            except ZeroDivisionError:
                self.r2 = 0.0

        elif len(self.matches) == 1:
            self.meanoffset = self.offset = self.matches[0].delta()
            self.slope = 1.0
            self.r2 = 0.0
        else:
            self.slope = 1.0
            self.offset = 0.0
            self.meanoffset = 0.0
            self.r2 = 0.0
