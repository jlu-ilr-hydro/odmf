from .basehandler import Button
from .tablehandler import TableFileHandler
import pandas as pd
from ....tools import Path
from ....config import conf
from . import fileactions as fa



class ExcelFileHandler(TableFileHandler):

    icon = 'file-excel'

    def to_html(self, path: Path, **kwargs) -> str:
        with pd.ExcelFile(path.absolute) as xls:
            buttons = []
            try:
                active_sheet = kwargs.pop('sheet', xls.sheet_names[0])
            except IndexError:
                raise ValueError('Excel file is broken - if you can open the file with Excel, please save it again and try to upload the new file')

            for sheet_name in xls.sheet_names:
                href = f'{path.href}?sheet={sheet_name}'
                buttons.append(Button(href=href, label=str(sheet_name), icon='table', title=f'View sheet {sheet_name}', active=(sheet_name == active_sheet)))
            
            buttons_html = Button.render_buttons(buttons)
            table_html = super().to_html(path, sheet=active_sheet)

            return buttons_html + table_html

