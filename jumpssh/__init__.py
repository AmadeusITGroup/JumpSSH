import json
import os
import sys

from jumpssh.exception import SSHException, ConnectionError, RestClientError, RunCmdError, TimeoutError
from jumpssh.session import SSHSession
from jumpssh.restclient import RestSshClient

if sys.version_info < (2, 6):
    raise RuntimeError('You need Python 2.6+ for this module.')

# set package version from config file
with open(os.path.join(os.path.dirname(__file__), 'pkg_info.json')) as fp:
    _info = json.load(fp)
__version__ = _info['version']

__all__ = ['SSHException',
           'ConnectionError',
           'RestClientError',
           'RunCmdError',
           'TimeoutError',
           'SSHSession',
           'RestSshClient']
