from ...tools import Path
from .. import lib as web
import re
from ...config import conf

from ..markdown import MarkDown

markdown = MarkDown()


class BaseFileHandler:

    def __init__(self, pattern: str = ''):
        self.pattern = re.compile(pattern)

    def matches(self, path: Path):
        """
        Checks if a path matches the file pattern
        """
        return bool(self.pattern.match(path.absolute))

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
    def __init__(self, pattern: str = r'.*\.plot'):
        super().__init__(pattern)

    def render(self, source) -> str:
        return '\n<pre>\n' + source + '\n</pre>\n'

    def to_html(self, path) -> str:
        """
        redirects to plot using the plot file
        """
        raise web.redirect(conf.root_url + '/plot', f=str(path))


class MarkDownFileHandler(TextFileHandler):

    def __init__(self, pattern: str=r'.*\.(md|wiki)'):
        super().__init__(pattern)

    def render(self, source) -> str:
        return markdown(source)

class ExcelFileHandler(BaseFileHandler):

    def __init__(self, pattern: str=r'.*\.xls?'):
        super().__init__(pattern)


    def to_html(self, path) -> str:
        import pandas as pd
        with open(path.absolute, 'rb') as f:
            df = pd.read_excel(f)
            html = df.to_html(classes=['table'])
            return html

class PdfFileHandler(BaseFileHandler):

    def __init__(self, pattern: str=r'.*\.pdf'):
        super().__init__(pattern)

    def to_html(self, path) -> str:
        return f'''
        <object id="pdf-iframe" data="{path.href.replace('download', 'datafiles')}" type="application/pdf"></iframe>
        '''


