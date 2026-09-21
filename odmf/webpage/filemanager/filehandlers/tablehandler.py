
import io
import typing

from charset_normalizer import detect
import pandas as pd

from .basehandler import BaseFileHandler
from ... import lib as web

from ....tools import Path
import re
from . import fileactions as fa
from ...auth import Level

class TableFileHandler(BaseFileHandler):
    icon = 'table'
    actions = fa.ConfImportAction(), fa.LogImportAction(), fa.LabImportAction(), fa.RecordImportAction(), fa.TableProfileAction(),

    def __init__(self, pattern: str):
        super().__init__(pattern)

    def load_table(self, path: Path, **kwargs) -> pd.DataFrame:
        """
        Loads a table file (csv, xlsx, parquet) into a pandas dataframe
        :param path:
        :param kwargs:
        :return:
        """
        if re.match(r'.*\.parquet$', path.name, re.IGNORECASE):
            import pyarrow.dataset as ds
            df = pd.read_parquet(path.absolute, **kwargs)
        elif re.match(r'.*\.xls.?$', path.name, re.IGNORECASE):
            sheet_name = kwargs.pop('sheet', 0)
            df = pd.read_excel(path.absolute, sheet_name=sheet_name, **kwargs)
        elif re.match(r'.*\.?sv$', path.name, re.IGNORECASE):
            df = pd.read_csv(path.absolute, sep=None, engine='python', **kwargs)
        return df

    def to_html(self, path: Path, **kwargs) -> str:
        """
        Converts a pandas dataframe to a html table.
        Overwrite for different handles
        """
        nrows = int(kwargs.pop('nrows', 100))
        offset = int(kwargs.pop('offset', 0))
        df = self.load_table(path, **kwargs)
        totrows = len(df)
        df_page = df.iloc[offset:offset+nrows]
        classes = ['table table-hover table-group-divider table-sm']
        df_html = df_page.to_html(classes=classes, border=0, index=True)
        stat_html = df.describe(include='all').T.to_html(classes=classes, border=0, index=True)

        return web.render(
            'filemanager/table.html', 
            path=path,
            df_html=df_html, 
            stat_html=stat_html, 
            totrows=totrows, 
            nrows=nrows, 
            offset=offset
        ).render()

        

    
    

