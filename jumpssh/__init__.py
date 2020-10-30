import sys

from jumpssh.__version__ import __version__  # noqa: F401
from jumpssh.exception import SSHException, ConnectionError, RestClientError, RunCmdError, TimeoutError
from jumpssh.session import SSHSession
from jumpssh.restclient import RestSshClient

if sys.version_info < (2, 6):
    raise RuntimeError('You need Python 2.6+ for this module.')


__all__ = ['SSHException',
           'ConnectionError',
           'RestClientError',
           'RunCmdError',
           'TimeoutError',
           'SSHSession',
           'RestSshClient']
