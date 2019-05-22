import sys
sys.path.insert(0, '.')
from .tools.parseConf import parseConf
from . import conf
parseConf(conf)

import db


if __name__ == '__main__':

    if len(sys.argv) == 1:
        print('Usage:'
              '\n   auto-dataset-creator.py [csv file]')
        exit()

    with db.session_scope() as session:
        with open(sys.argv[1]) as file:
            next(file) #skip first line
            for line in file:
                id, name, siteid, valuetypeid, source, level, measured_by, quality, start, end, timezone, project, comment = line.split(';')
                print(line)
                ts = db.Timeseries(id=id,
                                   name=name,
                                   _site=siteid,
                                   _valuetype=valuetypeid,
                                   _source=source,
                                   level=level,
                                   _measured_by=measured_by,
                                   _quality=quality,
                                   start=start,
                                   end=end,
                                   timezone=timezone,
                                   project=project,
                                   comment=comment)
                session.add(ts)
