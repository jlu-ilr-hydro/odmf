from typing import Dict

from .base import ImportDescription, ImportColumn
import typing
from .. import db
import pandas as pd
from ..config import conf

class DataImportError(RuntimeError):
    ...


def new_datasets_from_descr(session, import_description: ImportDescription,
                            user: str, siteid: int, filename: str=None) -> typing.Dict[typing.Any, db.Dataset]:
    """
    Creates new db.Dataset objects in session according to the import_import_description
    This works only for import_descriptions with

    Returns:
         Dictionary mapping columns (id/names) to datasets

    The id's of the datasets are only available after flush/commit of the session
    """

    # Get instrument, user and site object from db
    inst = session.query(db.Datasource).get(import_description.instrument)
    user = session.query(db.Person).get(user)
    site = session.query(db.Site).get(siteid)

    def col_to_dataset(col):
        # Get "raw" as data quality, to use as a default value
        raw = session.query(db.Quality).get(0)
        # Get the valuetype (vt) from db
        vt = session.query(db.ValueType).get(col.valuetype)
        if col.append:
            try:
                ds = session.query(db.Dataset).get(int(col.append))
                _ = ds.id
            except (TypeError, ValueError):
                raise DataImportError(
                    f'{import_description.filename}:{col.name} wants to append data ds:{col.append}. This dataset does not exist')

        else:
            # New dataset with metadata from above
            ds = db.Timeseries(measured_by=user, valuetype=vt, site=site, name=col.name,
                               filename=filename, comment=col.comment, source=inst, quality=raw,
                               start=None, end=None, level=col.level,
                               access=col.access if col.access is not None else 1,
                               # Get timezone from descriptor or, if not present from global conf
                               timezone=import_description.timezone or conf.datetime_default_timezone,
                               project=import_description.project)
        return ds

    return {
        col: col_to_dataset(col)
        for col in import_description.columns
    }

