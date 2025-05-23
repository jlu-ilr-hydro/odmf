import io
import typing

from charset_normalizer import detect
import pandas as pd


from ...tools import Path
from .. import lib as web
import re
from ...config import conf
from . import fileactions as fa
from ..markdown import MarkDown
from ..auth import Level


markdown = MarkDown()


def load_text_file(path: Path) -> str:
    with open(path.absolute, 'rb') as f:
        # read max 1 MB text
        data = f.read(1024 ** 2)
        for enc in 'utf-8', 'latin1', 'windows-1252', None:
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        else:
            detection = detect(data[:10000])
            if not detection['encoding']:
                raise ValueError(f'{path} is a binary file')
            return data.decode(detection['encoding'])


def load_text_stream(path: Path) -> io.StringIO:
    return io.StringIO(load_text_file(path))


def table_to_html(df: pd.DataFrame, index: bool=True, header=True):
    if header == True:
        header = f'<div class="alert alert-secondary">{len(df)} lines</div>'
    elif header == False:
        header = ''
    classes = ['table table-hover']
    if len(df) > 1000:
        table = df.iloc[:1000].to_html(classes=classes, border=0)
        return header + table + f'<div>... skipping lines 1000 - {len(df)}</div>'
    else:
        return header + df.to_html(classes=classes, border=0, index=index)

def error_msg(msg: str):
    return '<div class="alert alert-danger">' + msg + '</div>'



class BaseFileHandler:
    """
    The base class for file handling. Filehandlers are used by the file manager to display files

    icon: Font-Awesome icon to describe the file type
    actions: Sequence of FileAction objects - actions that can be performed on the file page
    """
    icon = 'file'
    actions: typing.Sequence[fa.FileAction] = ()
    def __init__(self, pattern: str = ''):
        self.pattern = re.compile(pattern, re.IGNORECASE)

    def __getitem__(self, action):
        return {a.name: a for a in self.actions}[action]

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

    def get_action_buttons(self, path: Path):
        for action in self.actions:
            print(action)
            action.check(path)
        return '\n'.join(action.html(path) for action in self.actions if action.check(path))

    def post_action(self, actionname: str, path: str, userlevel: Level):
        for action in self.actions:
            if action.name == actionname:
                if userlevel >= action.access_level:
                    return action.post(path)
                else:
                    raise ValueError('Invalid privileges')



class TextFileHandler(BaseFileHandler):
    icon = 'file-alt'
    actions = fa.ConfImportAction(),
    def __init__(self, pattern: str):
        super().__init__(pattern)

    def render(self, source) -> str:
        return '\n<pre>\n' + source + '\n</pre>\n'

    def to_html(self, path) -> str:
        """
        Converts a string to a html text by creating surrounding pre tags.
        Overwrite for different handles
        """
        source = load_text_file(path)
        return web.render('textfile_editor.html', html=self.render(source), source=source, path=path).render()


class ConfFileHandler(TextFileHandler):
    icon = 'file-import'
    def render(self, source):
        def div(content, *classes):
            classes = ' '.join(classes)
            return f'\n<div class="{classes}">{content}</div>'
        try:
            source = source.replace('\r', '')
            value_sub = div(div('\\1', 'col') + div('= ', 'col') + div('\\2', 'col'), 'row')
            source = re.sub(r'(.*)\=(.*)', value_sub, source)
            source = re.sub(r'^[#;](.*)', div('\\1', 'text-light bg-secondary small ps-2 font-italic'), source, flags=re.M)
            source = re.sub(r'^\s*\[(.*)\]\s*$', r'<h3>[\1]</h3>', source, flags=re.M)
            return source
        except Exception:
            return '\n<pre>\n' + source + '\n</pre>\n'

class SummaryFileHandler(TextFileHandler):
    icon = 'history'
    def render(self, source):
        from ...plot.summary_table import summary
        import yaml
        try:
            summary_content = yaml.safe_load(source)
            time = summary_content['time']
            items = summary_content['items']
            df = summary(time, items)

            return table_to_html(df, index=False, header=f'<h3>Summary over {time}</h3>')
        except Exception as e:
            return error_msg(f'<p>Cannot process summary, check file syntax</p><pre>{e}</pre>') + '\n<pre>\n' + source + '\n</pre>\n'



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


class ExcelFileHandler(BaseFileHandler):

    icon = 'file-excel'
    actions = fa.ConfImportAction(), fa.LogImportAction(), fa.LabImportAction()
    def to_html(self, path: Path) -> str:

        with open(path.absolute, 'rb') as f:
            df = pd.read_excel(f)
            return table_to_html(df)


class CsvFileHandler(BaseFileHandler):

    icon = 'file-csv'
    actions = fa.ConfImportAction(),
    def to_html(self, path: Path) -> str:

        text_io = load_text_stream(path)
        try:
            df = pd.read_csv(text_io, sep=None, engine='python')
            return table_to_html(df)
        except Exception as e:

            return '\n<pre>\n' + text_io.getvalue() + '\n</pre>\n'


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


class DocxFileHandler(BaseFileHandler):

    icon = 'file-word'

    def to_html(self, path: Path):
        try:
            import mammoth as m
            with path.as_path().open('rb') as f:
                conversion = m.convert_to_html(f)
                return conversion.value
        except Exception as e:
            raise web.HTTPError(500, f'Cannot open Word document: {path}')

class ZipFileHandler(BaseFileHandler):

    icon = 'file-archive'
    actions = fa.UnzipAction(),

    def to_html(self, path: Path) -> str:
        try:
            import zipfile
            z = zipfile.ZipFile(path.absolute)
            li = ' '.join(f'<li class="list-group-item"><i class="fas fa-file me-2"></i>{zi.filename}</li>' for zi in z.infolist())
            header = '<h5>Content:</h5>'
            return header + '<ul class="list-group"> ' + li + '</ul>'
        except Exception as e:
            raise web.HTTPError(500, f'Cannot open zipfile: {path}')


class MultiHandler(BaseFileHandler):
    handlers = [
        MarkDownFileHandler(r'\.(md|wiki)$'),
        ConfFileHandler(r'\.conf$'),
        PlotFileHandler(r'\.plot$'),
        ExcelFileHandler(r'\.xls.?$'),
        DocxFileHandler(r'\.docx$'),
        CsvFileHandler(r'\.(csv|dat)$'),
        ParquetFileHandler(r'\.parquet$'),
        PdfFileHandler(r'\.pdf$'),
        ImageFileHandler(r'\.(jpg|jpeg|png|svg|gif)$'),
        ZipFileHandler(r'\.zip$'),
        SummaryFileHandler(r'\.summary$'),
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
