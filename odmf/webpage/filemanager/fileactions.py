import typing
from ...tools import Path
from ...config import conf


class FileAction:
    """
    A file action is an action that can be used with a file. It creates a button in the view of the file

    You can use this class directly with an `action(path: odmf.tools.Path)` function or subclass this class
    and overwrite the `action` function
    """
    title = 'A generic file action'
    name = 'file-action'
    icon = 'file'
    tooltip = 'A generic action on the file'
    access_level = 4

    def __init__(self, title: str='', icon: str='', tooltip: str='', access_level=0, action: typing.Optional[typing.Callable] =None):
        self.title = title or self.title
        self.icon = icon or self.icon
        self.tooltip = tooltip or self.tooltip
        self.access_level = access_level or self.access_level
        if not any((self.title, self.icon)):
            raise ValueError('A FileAction needs either a title or an icon')
        if callable(action):
            self.action = action

    def check(self, path: Path):
        """
        Returns True, if the action can be performed
        :param path:
        :return:
        """
        return True

    def href(self, path: Path):
        return '#'

    def html(self, path: Path):
        is_action_button = 'action-button' if hasattr(self, 'post') else ''
        return f'''
            <a href="{self.href(path)}" class="btn btn-secondary {is_action_button}"
               data-toggle="tooltip" title="{self.tooltip}"
               data-actionid="{self.name}" data-path="{path}">
                    <i class="fas fa-{self.icon}" ></i> {self.title}
            </a>'''

    def __str__(self):
        return self.name



class UnzipAction(FileAction):
    """
    A file action for ZIP-Files to unpack them
    """
    name = 'unzip'
    icon = 'box-open'
    title = 'ZIP'
    tooltip = 'Unzip file content here'
    access_level = 2

    def post(self, path: Path):
        import zipfile
        target_dir = path.absolute.removesuffix('.zip')
        with zipfile.ZipFile(path.absolute) as zf:
            zf.extractall(target_dir)
        return Path(target_dir)


class ConfImportAction(FileAction):
    name ='import-conf'
    icon = 'upload'
    title = 'conf'
    tooltip = 'Import to database with configuration file'
    access_level = 2

    def href(self, path: Path):
        return conf.url('/download/to_db/conf', filename=path.name)

    def check(self, path: Path):
        from ...dataimport import ImportDescription
        try:
            _ = ImportDescription.from_file(path.absolute)
        except IOError:
            return False
        else:
            return True

class LogImportAction(FileAction):
    name ='import-log'
    icon = 'upload'
    title = 'log'
    tooltip = 'Import to database with log table'

    def href(self, path: Path):
        return conf.url('/download/to_db/log', filename=path.name)

    def check(self, path: Path):
        import pandas as pd

        df = pd.read_excel(path.absolute)
        columns = [c.lower() for c in df.columns]
        return all(c in columns for c in 'time|site|dataset|value|logtype|message'.split('|'))
