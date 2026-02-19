from .basehandler import BaseFileHandler, table_to_html, Button
import pandas as pd
from ....tools import Path
from ....config import conf
from . import fileactions as fa



class ExcelFileHandler(BaseFileHandler):

    icon = 'file-excel'
    actions = fa.ConfImportAction(), fa.LogImportAction(), fa.LabImportAction(), fa.RecordImportAction()
    def to_html(self, path: Path, **kwargs) -> str:
        with pd.ExcelFile(path.absolute) as xls:
            buttons = []
            active_sheet = kwargs.get('sheet', xls.sheet_names[0])
            for sheet_name in xls.sheet_names:
                href = f'{path.href}?sheet={sheet_name}'
                buttons.append(Button(href=href, label=sheet_name, icon='table', title=f'View sheet {sheet_name}', active=(sheet_name == active_sheet)))
            
            buttons_html = Button.render_buttons(buttons)
            df = pd.read_excel(xls, sheet_name=active_sheet or xls.sheet_names[0])
            return buttons_html + table_to_html(df)

