import typing
import re
import yaml
import pandas as pd
from ....tools import Path
from ....config import conf


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

    def href(self, path: Path, **kwargs):
        return '#'

    def html(self, path: Path, **kwargs) -> str:
        is_action_button = 'action-button' if hasattr(self, 'post') else ''
        return f'''
            <a href="{self.href(path, **kwargs)}" class="btn btn-secondary {is_action_button}"
               data-bs-toggle="tooltip" title="{self.tooltip}"
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

    def href(self, path: Path, **kwargs):
        return conf.url('/download/to_db/conf', filename=path.name, **kwargs)

    def check(self, path: Path, **kwargs):
        from ....dataimport import ImportDescription
        try:
            descr = ImportDescription.from_file(path.absolute)
            with path.to_pythonpath().open('rb') as f:
                f.read(100)
        except IOError:
            return False
        else:
            return True

class LogImportAction(FileAction):
    """
    Lets the user import a log like sheet, without any description file
    """
    name ='import-log'
    icon = 'upload'
    title = 'log'
    tooltip = 'Import to database with log table'

    def href(self, path: Path, **kwargs):
        return conf.url('/download/to_db/log', filename=path.name, **kwargs)

    def check(self, path: Path, **kwargs):
        df = pd.read_excel(path.absolute, sheet_name=kwargs.get('sheet',0), nrows=1)
        columns = [c.lower() for c in df.columns]
        return all(c in columns for c in 'time|site|dataset|value|logtype|message'.split('|'))

class LabImportAction(FileAction):
    """
    Moves the user to a page for import sheets from a lab instrument. Uses a .labimport yaml file to describe the content
    """

    name ='import-lab'
    icon = 'flask'
    title = 'lab'
    tooltip = 'Import to database using .labimport file'

    def href(self, path: Path, **kwargs):
        return conf.url('/download/to_db/lab', filename=path.name, **kwargs)

    def check(self, path: Path, **kwargs):
        try:
            fn = path.glob_up('*.labimport')
            with open(fn.absolute) as f:
                lab_imports = yaml.safe_load(f)
            return 'driver' in lab_imports and 'columns' in lab_imports
        except (OSError, ValueError):
            return False

class RecordImportAction(FileAction):
    """
    A file action for files that can be imported as records to the database. Checks if the file has a .recordimport description file
    """

    name ='import-record'
    icon = 'cloud-arrow-up'
    title = 'record'
    tooltip = 'Import to database from a record table'

    def href(self, path: Path, **kwargs):
        return conf.url('/download/to_db/record', filename=path.name, **kwargs)

    def check(self, path: Path, **kwargs):
        try:
            if re.match(r'.*\.parquet$', path.name, re.IGNORECASE):
                import pyarrow.dataset as ds
                df = ds.dataset(path.absolute).scanner().head(1).to_pandas()
            elif re.match(r'.*\.xls.?$', path.name, re.IGNORECASE):
                df = pd.read_excel(path.absolute, nrows=1, sheet_name=kwargs.get('sheet',0))
            elif re.match(r'.*\.csv$', path.name, re.IGNORECASE):
                df = pd.read_csv(path.absolute, nrows=1, sep=None, engine='python')
            if len(df):
                columns = [c.lower() for c in df.columns]
                return all(c in columns for c in 'time|dataset|value'.split('|'))
            else:
                return False
                
        except Exception as e:
            return False
