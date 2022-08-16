import typing

import pandas as pd

from ...tools import Path
from .. import lib as web
import re
from ...config import conf

from ..markdown import MarkDown

markdown = MarkDown()


class BaseFileHandler:
    """
    The base class for file handling. Filehandlers are used by the file manager to display files

    icon: Font-Awesome icon to describe the file type
    """
    icon = 'file'
    def __init__(self, pattern: str = ''):
        self.pattern = re.compile(pattern, re.IGNORECASE)

    def matches(self, path: Path):
        """
        Checks if a path matches the file pattern
        """
        return bool(self.pattern.search(path.absolute))

    def to_html(self, path) -> str:
        """
        Converts a string to a html text
        Overwrite for different handles
        """
        raise NotImplementedError

    def __call__(self, path: Path):
        return self.to_html(path)


class TextFileHandler(BaseFileHandler):
    icon = 'file-alt'
    def __init__(self, pattern: str):
        super().__init__(pattern)

    def render(self, source) -> str:
        return '\n<pre>\n' + source + '\n</pre>\n'

    def to_html(self, path) -> str:
        """
        Converts a string to a html text by creating surrounding pre tags.
        Overwrite for different handles
        """
        with open(path.absolute) as f:
            source = f.read()
        return web.render('textfile_editor.html', html=self.render(source), source=source, path=path).render()


class PlotFileHandler(BaseFileHandler):
    icon = 'chart-line'
    def render(self, source) -> str:
        return '\n<pre>\n' + source + '\n</pre>\n'

    def to_html(self, path) -> str:
        """
        redirects to plot using the plot file
        """
        raise web.redirect(conf.root_url + '/plot', f=str(path))


class MarkDownFileHandler(TextFileHandler):
    def render(self, source) -> str:
        return markdown(source)


def table_to_html(df: pd.DataFrame):
    header = f'<div class="alert alert-secondary">{len(df)} lines</div>'
    classes = ['table table-hover']
    if len(df) > 1000:
        table = df.iloc[:1000].to_html(classes=classes, border=0)
        return header + table + f'<div>... skipping lines 1000 - {len(df)}</div>'
    else:
        return header + df.to_html(classes=classes, border=0)


class ExcelFileHandler(BaseFileHandler):

    icon = 'file-excel'

    def to_html(self, path: Path) -> str:

        with open(path.absolute, 'rb') as f:
            df = pd.read_excel(f)
            return table_to_html(df)


class CsvFileHandler(BaseFileHandler):

    icon = 'file-csv'

    def to_html(self, path: Path) -> str:

        try:
            df = pd.read_csv(path.absolute, sep=None)
            return table_to_html(df)
        except:
            with open(path.absolute, 'r') as f:
                return '\n<pre>\n' + f.read() + '\n</pre>\n'

class ParquetFileHandler(BaseFileHandler):

    icon = 'table'
    def to_html(self, path) -> str:

        with open(path.absolute, 'rb') as f:
            df = pd.read_parquet(f)
            return table_to_html(df)


class ImageFileHandler(BaseFileHandler):

    icon = 'file-image'

    def to_html(self, path: Path) -> str:
        return f'''
        <img class="handler-generated" src="{path.raw_url}" style="max-width: 100%"/>
        '''


class PdfFileHandler(BaseFileHandler):

    icon = 'file-pdf'
    def to_html(self, path: Path) -> str:
        return f'''
        <object id="pdf-iframe" data="{path.raw_url}" type="application/pdf" >
            <a href="{path.raw_url}" class="btn btn-primary">Download</a>
        </object>
        '''

class ZipFileHandler(BaseFileHandler):

    icon = 'file-archive'

    def to_html(self, path: Path) -> str:
        try:
            import zipfile
            z = zipfile.ZipFile(path.absolute)
            li = ' '.join(f'<li class="list-group-item"><i class="fas fa-file mr-2"></i>{zi.filename}</li>' for zi in z.infolist())
            header = '<h5>Content:</h5>'
            return header + '<ul class="list-group"> ' + li + '</ul>'
        except Exception as e:
            raise web.HTTPError(500, f'Cannot open zipfile: {path}')


class MultiHandler(BaseFileHandler):
    handlers = [
        MarkDownFileHandler(r'\.(md|wiki)$'),
        PlotFileHandler(r'\.plot$'),
        ExcelFileHandler(r'\.xls.?$'),
        CsvFileHandler(r'\.csv$'),
        ParquetFileHandler(r'\.parquet$'),
        PdfFileHandler(r'\.pdf$'),
        ImageFileHandler(r'\.(jpg|jpeg|png|svg|gif)$'),
        ZipFileHandler(r'\.zip$'),
        TextFileHandler(''),
    ]

    def __getitem__(self, path: Path) -> typing.Optional[BaseFileHandler]:
        for h in self.handlers:
            if h.matches(path):
                try:
                    return h
                except web.HTTPRedirect:
                    raise
                except UnicodeDecodeError as e:
                    pass
        return None

    def to_html(self, path: Path) -> str:
        if handler := self[path]:
            return handler.to_html(path)
