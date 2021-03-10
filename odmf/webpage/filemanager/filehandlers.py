from ...tools import Path
import re
import pandas
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

    def to_html(self, source) -> str:
        """
        Converts a string to a html text
        Overwrite for different handles
        """
        raise NotImplementedError

    def read_file(self, path: Path):
        """
        Reads the content of a path
        """
        raise NotImplementedError

    def __call__(self, path: Path):
        return self.to_html(self.read_file(path))


class TextFileHandler(BaseFileHandler):
    def __init__(self, pattern: str):
        super().__init__(pattern)

    def to_html(self, source) -> str:
        """
        Converts a string to a html text by creating surrounding pre tags.
        Overwrite for different handles
        """
        return '\n<pre>\n' + source + '\n</pre>\n'

    def read_file(self, path: Path):
        """
        Reads the content of path using a text reader. Overwrite for binary files

        """
        with open(path.absolute) as f:
            return f.read()



class MarkDownFileHandler(TextFileHandler):

    def __init__(self, pattern: str=r'.*\.(md|wiki)'):
        super().__init__(pattern)

    def to_html(self, source) -> str:
        return markdown(source)


class ExcelFileHandler(BaseFileHandler):

    def __init__(self, pattern: str=r'.*\.xls?'):
        super().__init__(pattern)

    def read_file(self, path: Path):
        with open(path.absolute, 'rb') as f:
            return f.read()

    def to_html(self, source) -> str:
        import pandas as pd
        import io
        reader = io.BytesIO()
        reader.write(source)
        reader.seek(0)
        df = pd.read_excel(reader)
        html = df.to_html(classes=['table'])
        return html
