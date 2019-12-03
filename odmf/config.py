# Parse conf.py in the root directory and check for validity
#
# A more detailed explanation of a valid configuration can be found
#  in the documentation
#

import yaml
from pathlib import Path
import sys

from logging import getLogger
logger = getLogger(__name__)


class ConfigurationError(RuntimeError):
    pass


def get_home():
    try:
        return Path(PREFIX)
    except NameError:
        return Path('.')


def find_odmf_static_location():
    """
    Finds the path to the static files of the library

    Looks at the following locations:
     - {sys.prefix}/odmf.static, where {sys.prefix} is the python installation. This is the proper location
     - {__file__}/../../odmf.static: Where {__file__} is the installation location of this config.py file.
       This is for development
     - ./odmf.static is the local installation directory - a fallback solution if the others do not work

    """

    candidates = Path(__file__).parent / 'static', Path('./odmf/static')

    for p in candidates:
        if p.exists():
            if all((p / d).exists() for d in ('templates', 'datafiles', 'media')):
                logger.info(f'odmf.static at {p}/[templates|datafiles|media]')
                return p
            else:
                logger.info(f'{p}, found but not all of templates|datafiles|media exist, searching further\n')
        else:
            logger.info(f'{p} - does not exist\n')

    logger.warning('Did not find the odmf.static directory in the installation or local')



def static_locations(from_config):
    paths = [find_odmf_static_location(), Path('.')] + [Path(p) for p in from_config]
    filtered = []
    [filtered.append(str(p)) for p in paths if p.exists() and p not in filtered]
    return filtered



class Configuration:
    """
    The configuration class. Change the configuration by providing a config.yml in the home directory

    Mandatory fields are defined as (...), optional as None or with a default value
    """
    datetime_default_timezone = 'Europe/Berlin'
    database_type = 'postgres'
    database_name = ...
    database_username = ...
    database_password = ...
    database_host = '127.0.0.1'

    static = ['.']
    media_image_path = 'webpage/media'
    nav_background = '/media/gladbacherhof.jpg'
    nav_left_logo = '/media/lfe-logo.png'
    manual_measurements_pattern = '(.+\\/)*datafiles\\/lab\\/([a-zA-Z0-9]+\\/)*.*\\.(xls|xlsx)$'
    map_default = {'lat': 50.5, 'lng': 8.55, 'type': 'hybrid', 'zoom': 15}
    upload_max_size = 25000000
    server_port = ...
    google_maps_api_key = ...
    woftester_receiver_mail = ['philipp.kraft@umwelt.uni-giessen.de']
    woftester_sender_mail = 'woftester@umwelt.uni-giessen.de'
    cuahsi_wsdl_endpoint = 'http://fb09-pasig.umwelt.uni-giessen.de/wof/index.php/cuahsi_1_1.asmx?WSDL'
    smtp_serverurl = 'mailout.uni-giessen.de'
    head_base = ''

    def __bool__(self):
        return ... not in vars(self).values()

    def to_dict(self):
        return {
            k: v
            for k, v in vars(self).items()
            if not callable(v) and not k.startswith('_')
        }

    def update(self, conf_dict: dict):

        unknown_keys = []
        for k in conf_dict:
            if hasattr(self, k):
                setattr(self, k, conf_dict[k])
            else:
                unknown_keys.append(k)
        if unknown_keys:
            raise ConfigurationError(f'Your configuration contains unknown keys: {",".join(unknown_keys)}')

        return self

    def __init__(self, **kwargs):

        vars(self).update({
            k: v
            for k, v in vars(type(self)).items()
            if not k.startswith('_') and not callable(v)
        })

        self.update(kwargs)

        self.static = static_locations(self.static)

    def abspath(self, relative_path: Path):
        """
        Returns a pathlib.Path from the first fitting static location
        :param relative_path: A relative path to a static ressource
        """
        for static_home in reversed(self.static):
            p = Path(static_home) / relative_path
            if p.exists():
                return p.absolute()
        raise FileNotFoundError(f'{relative_path} not found in the static ressources')

    def to_yaml(self, stream=sys.stdout):
        """
        Exports the current configuration to a yaml file
        :param stream: A stream to write to
        """
        yaml.safe_dump(self.to_dict(), stream)


def load_config():
    conf_file = get_home() / 'config.yml'
    logger.debug('Found config file:', str(conf_file.resolve()))
    if not conf_file.exists():
        logger.warning(f'{conf_file.absolute().as_posix()} '
                   f'not found. Create a template with "odmf configure". Using incomplete configuration')
        conf_dict = {}
    else:
        conf_dict = yaml.safe_load(conf_file.open())
        logger.debug('loaded ', str(conf_file.resolve()))
    conf = Configuration(**conf_dict)
    if not conf:
       logger.warning(', '.join(k for k, v in conf.to_dict().items() if v is ...) + ' are undefined')



def import_module_configuration(conf_module_filename):
    """
    Migration utitlity to create a conf.yaml from the old ODMF 0.x conf.py module configuration

    :param conf_module_filename: The conf.py configuration file
    """
    code = compile(open(conf_module_filename).read(), 'conf.py', 'exec')
    config = {}
    exec(code, config)

    def c(s: str):
        return s.replace('CFG_', '').lower()

    config = {
        c(k): v
        for k, v in config.items()
        if k.upper() == k and k[0] != '_' and not callable(v)
    }

    config['database_type'] = config.pop('database', 'postgres')

    conf = Configuration(**config)

    return conf


conf = load_config()
