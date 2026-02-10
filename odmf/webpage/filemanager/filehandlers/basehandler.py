
import io
import typing

from charset_normalizer import detect
import pandas as pd


from ....tools import Path
import re
from . import fileactions as fa
from ...auth import Level


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
        header = f'<div class="badge text-bg-secondary mb-2">{len(df)} lines</div>'
    elif header == False:
        header = ''
    classes = ['table table-hover table-group-divider table-sm']
    if len(df) > 1000:
        table = df.iloc[:1000].to_html(classes=classes, border=0)
        return header + table + f'<div>... skipping lines 1000 - {len(df)}</div>'
    else:
        return header + df.to_html(classes=classes, border=0, index=index)

def error_msg(msg: str):
    return '<div class="alert alert-danger">' + msg + '</div>'

class Button:
    def __init__(self, href: str, label: str, icon: str='', title: str='', active: bool=False):
        self.href = href
        self.label = label
        self.icon = icon
        self.title = title
        self.active = active
    @classmethod
    def render_buttons(cls, buttons: typing.List['Button']):
        from ... import lib as web
        return web.render('button_group.html', buttons=buttons).render()

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

    def to_html(self, path, **kwargs) -> str:
        """
        Converts a string to a html text
        Overwrite for different handles
        """
        raise NotImplementedError

    def __call__(self, path: Path, **kwargs) -> str:
        return self.to_html(path, **kwargs)

    def get_action_buttons(self, path: Path, **kwargs):
        return '\n'.join(action.html(path, **kwargs) for action in self.actions if action.check(path, **kwargs))

    def post_action(self, actionname: str, path: str, userlevel: Level):
        for action in self.actions:
            if action.name == actionname:
                if userlevel >= action.access_level:
                    return action.post(path)
                else:
                    raise ValueError('Invalid privileges')

