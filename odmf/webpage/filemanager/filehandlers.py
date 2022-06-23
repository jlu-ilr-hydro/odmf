import pandas as pd

from ...tools import Path
from .. import lib as web
import re
from ...config import conf

from ..markdown import MarkDown

markdown = MarkDown()


class BaseFileHandler:

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


class ExcelFileHandler(BaseFileHandler):

    def to_html(self, path: Path) -> str:

        with open(path.absolute, 'rb') as f:
            df = pd.read_excel(f)
            html = df.to_html(classes=['table'])
            return html


class CsvFileHandler(BaseFileHandler):

    def to_html(self, path: Path) -> str:

        try:
            df = pd.read_csv(path.absolute, sep=None)
            return df.to_html(classes=['table'])
        except:
            with open(path.absolute, 'r') as f:
                return '\n<pre>\n' + f.read() + '\n</pre>\n'

class ParquetFileHandler(BaseFileHandler):

    def to_html(self, path) -> str:

        with open(path.absolute, 'rb') as f:
            df = pd.read_parquet(f)
            html = df.to_html(classes=['table'])
            return html



class ImageFileHandler(BaseFileHandler):

    def to_html(self, path: Path) -> str:
        return f'''
        <img class="handler-generated" src="{path.raw_url}" style="max-width: 100%"/>
        '''


class PdfFileHandler(BaseFileHandler):

    def to_html(self, path) -> str:
        return f'''
        <object id="pdf-iframe" data="{path.raw_url}" type="application/pdf"></iframe>
        '''


class MultiHandler(BaseFileHandler):
    handlers = [
        MarkDownFileHandler(r'\.(md|wiki)$'),
        PlotFileHandler(r'\.plot$'),
        ExcelFileHandler(r'\.xls.?$'),
        CsvFileHandler(r'\.csv$'),
        ParquetFileHandler(r'\.parquet$'),
        PdfFileHandler(r'\.pdf$'),
        ImageFileHandler(r'\.(jpg|jpeg|png|svg|gif)$'),
        TextFileHandler(''),
    ]

    def to_html(self, path: Path) -> str:
        for h in self.handlers:
            if h.matches(path):
                try:
                    return h(path)
                except web.HTTPRedirect:
                    raise
                except UnicodeDecodeError as e:
                    pass
        return None
