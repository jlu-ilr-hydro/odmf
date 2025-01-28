# Parse conf.py in the root directory and check for validity
#
# A more detailed explanation of a valid configuration can be found
#  in the documentation
#

import yaml
from pathlib import Path
import sys
import os

from logging import getLogger
from . import prefix, __version__

logger = getLogger(__name__)


class ConfigurationError(RuntimeError):
    pass


def static_locations(*from_config):

    paths = [Path(__file__).parent / 'static'] + [Path(p) for p in from_config]
    filtered = []
    [
        filtered.append(str(p)) for p in paths if p and p.exists() and str(p) not in filtered
    ]
    return filtered



class Configuration:
    """
    The configuration class. Change the configuration by providing a config.yml in the home directory

    Mandatory fields are defined as (...), optional as None or with a default value
    """
    datetime_default_timezone = 'Europe/Berlin'
    database_url = 'sqlite://'
    static = [prefix]
    media_image_path = 'webpage/media'
    nav_background = '/media/gladbacherhof.jpg'
    nav_left_logo = '/media/lfe-logo.png'
    manual_measurements_pattern = '(.+\\/)*datafiles\\/lab\\/([a-zA-Z0-9]+\\/)*.*\\.(xls|xlsx)$'
    map_default = {'lat': 50.5, 'lng': 8.55, 'type': 'hybrid', 'zoom': 15}
    utm_zone = '32N'
    upload_max_size = 25000000
    server_port = 8080
    google_maps_api_key = ''
    # woftester_receiver_mail = ['philipp.kraft@umwelt.uni-giessen.de']
    # woftester_sender_mail = 'woftester@umwelt.uni-giessen.de'
    # cuahsi_wsdl_endpoint = 'http://fb09-pasig.umwelt.uni-giessen.de/wof/index.php/cuahsi_1_1.asmx?WSDL'
    mailer_config = None
    root_url = ''
    datafiles = './datafiles'
    preferences = './preferences'
    description = 'A server for data-management for quantitative field research'
    user = os.environ.get('USER') or os.environ.get('USERNAME')
    session_key = '#!35625/Schwingbach?Benutzer'


    def to_dict(self):
        return {
            k: v
            for k, v in vars(self).items()
            if (
                    not callable(v)
                    and not k.startswith('_')
                    and type(v) is not property
            )
        }

    def update(self, conf_dict: dict):

        unknown_keys = []
        for k in conf_dict:
            if hasattr(self, k):
                setattr(self, k, conf_dict[k])
            else:
                unknown_keys.append(k)
        if unknown_keys:
            logger.warning(f'Your configuration contains unknown keys: {",".join(unknown_keys)}')
        self.root_url = self.root_url.strip().rstrip('/')
        return self

    def __init__(self, **kwargs):

        vars(self).update({
            k: v
            for k, v in vars(type(self)).items()
            if not k.startswith('_') and not callable(v)
        })

        self.update(kwargs)
        self.static = static_locations(self.home, *self.static)

    @property
    def home(self):
        return str(Path(prefix).absolute())

    def abspath(self, relative_path: Path):
        """
        Returns a pathlib.Path from the first fitting static location
        :param relative_path: A relative path to a static ressource
        """
        for static_home in reversed(self.static):
            p = Path(static_home) / relative_path
            if p.exists():
                return p.absolute()
        raise FileNotFoundError(f'{relative_path} not found in the static resources')

    def to_yaml(self, stream=sys.stdout):
        """
        Exports the current configuration to a yaml file
        :param stream: A stream to write to
        """
        d = self.to_dict()
        yaml.safe_dump(d, stream)

    def google_maps_api(self, callback: str):
        return f'https://maps.googleapis.com/maps/api/js?key={self.google_maps_api_key}&callback={callback}'

    def url(self, *uri, **query):
        uri = '/'.join((str(s) for s in uri))
        if query:
            uri += '?' + '&'.join(f'{k}={v}' for k, v in query.items() if v)
        if uri.startswith('/'):
            return self.root_url + uri
        else:
            return self.root_url + '/' + uri

    @property
    def version(self):
        return __version__


def load_config(path=prefix):
    conf_file = Path(path) / 'config.yml'
    logger.debug('Found config file:' + str(conf_file.absolute()))
    if not conf_file.exists():
        logger.info(f'{conf_file.absolute().as_posix()} not found, using empty config')
        conf_dict = {}
    else:
        with conf_file.open() as f:
            conf_dict = yaml.safe_load(f) or {}
        logger.debug(f'loaded {conf_file.resolve()}')
    return Configuration(**conf_dict)


conf = load_config()
