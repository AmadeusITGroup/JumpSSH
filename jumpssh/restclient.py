# external import
import os
import json
import logging
import re
try:
    from urllib import quote_plus  # Python2
except ImportError:
    from urllib.parse import quote_plus  # Python3
try:
    from httplib import HTTPResponse as http_HTTPResponse  # Python2
except ImportError:
    from http.client import HTTPResponse as http_HTTPResponse  # Python3
try:
    from StringIO import StringIO as FakeSocketParam  # Python2
except ImportError:
    from io import BytesIO as FakeSocketParam  # Python3

from . import exception, SSHSession

logger = logging.getLogger(__name__)

# list of ANSI escape sequence based on http://ascii-table.com/ansi-escape-sequences-vt-100.php
ANSI_REGEX = r'\x1b(' \
             r'(\[\??\d+[hl])|' \
             r'([=<>a-kzNM78])|' \
             r'([\(\)][a-b0-2])|' \
             r'(\[\d{0,2}[ma-dgkjqi])|' \
             r'(\[\d+;\d+[hfy]?)|' \
             r'(\[;?[hf])|' \
             r'(#[3-68])|' \
             r'([01356]n)|' \
             r'(O[mlnp-z]?)|' \
             r'(/Z)|' \
             r'(\d+)|' \
             r'(\[\?\d;\d0c)|' \
             r'(\d;\dR))'


class RestSshClient(object):
    def __init__(
            self,
            ssh_session=None,
            **kwargs
    ):
        """

        :param ssh_session:
        :param host:
        :param username:
        :param kwargs:
        """
        if ssh_session:
            self.ssh_session = ssh_session
        else:
            self.ssh_session = SSHSession(host=kwargs.pop('host'),
                                          username=kwargs.pop('username'), **kwargs)

        self.host = self.ssh_session.host
        self.username = self.ssh_session.username

    def __enter__(self):
        self.ssh_session.open()
        return self

    def __exit__(self, *args):
        self.ssh_session.close()

    def __repr__(self):
        return '%s(host=%s, username=%s, ssh_session=%s)' \
               % (self.__class__.__name__, self.host, self.username, repr(self.ssh_session))

    def request(self, method, uri, **kwargs):
        """Perform http request and send back http response.

        :param method: http method.
        :param uri: remote URL to target.
        :param params: (optional) Dictionary to be sent in the query string.
        :param data: (optional) Content to send in the body of the http request.
        :param headers: (optional) Dictionary of HTTP Headers to send with the http request.
        :param remote_file: (optional) File on the remote host with content to send in the body of the http request.
        :param local_file: (optional) Local file with content to send in the body of the http request.
        :param document_info_only: (optional) if True, only HTTP Headers are returned in http response (default=False).
        :param auth: (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
        :param verify: (optional) whether the SSL cert will be verified.
        :param silent: if True, does not log the command run (useful if sensitive information are used in command)
        :return: :class:`HTTPResponse <HTTPResponse>` object
        :rtype: restclient.HTTPResponse

        Usage::

          >>> from jumpssh import RestSshClient
          >>> with RestSshClient(host='gateway.example.com', username='my_user') as rest_client:
          >>> ... http_response = rest_client.request('GET', 'http://remote.example.com')
          >>> ... http_response.status_code
          200
        """

        # build curl command
        # force usage of http 1.0 as chunked transfer encoding not yet supported here
        cmd = 'curl -is --http1.0 '

        # disable verification of SSL cert
        if not kwargs.get('verify', True):
            cmd += "-k "

        # only return status code and headers (no body)
        if kwargs.get('document_info_only'):
            cmd += "-I "

        # basic authentication
        if kwargs.get('auth'):
            auth = kwargs.get('auth')
            if len(auth) != 2:
                raise exception.RestClientError("Invalid auth parameter. "
                                                "Tuple with 2 elements (user, password) is expected.")
            cmd += "-u %s:%s " % (auth[0], auth[1])

        # specify http method
        cmd += '-X %s ' % method.upper()

        # build headers list
        if kwargs.get('headers'):
            headers = kwargs.get('headers')
            for key, value in headers.items():
                cmd += '-H "%s:%s" ' % (key, value)

        # add targeted uri
        cmd += '"%s' % uri

        # add uri parameters
        if kwargs.get('params'):
            params = kwargs.get('params')
            if any(params):
                cmd += '?'
                cmd += '&'.join(['%s=%s' % (quote_plus(key), quote_plus(value)) for key, value in params.items()])

        # close quotes around uri with params
        cmd += '" '

        # build body
        if kwargs.get('local_file'):
            local_file = kwargs.get('local_file')
            if not os.path.exists(local_file) or not os.path.isfile(local_file):
                raise exception.RestClientError("Invalid file path given '%s'" % local_file)
            sftp_client = self.ssh_session.get_sftp_client()
            file_name = os.path.basename(local_file)
            sftp_client.put(local_file, file_name)
            cmd += '-d @%s ' % file_name
        elif kwargs.get('remote_file'):
            remote_file = kwargs.get('remote_file')
            if not self.ssh_session.exists(remote_file):
                raise exception.RestClientError("Invalid remote file path given '%s' on host '%s'"
                                                % (remote_file, self.ssh_session.host))
            cmd += '-d @%s ' % remote_file
        elif kwargs.get('data'):
            data = kwargs.get('data')
            cmd += "-d '%s' " % data.replace("'", "\'")

        # execute remote http query and get raw response
        exit_code, output = self.ssh_session.run_cmd(
            cmd,
            # do not raise exception if error code different from 0 as some queries can be successful
            # with other exit codes
            raise_if_error=False,
            # propagate 'silent' parameter to run_cmd
            silent=kwargs.get('silent', False))

        # check exit code has a proper value
        # most of successful commands will return exit code 0
        # except when using HEAD http method as file transfer is shorter or larger than expected
        # curl is returning exit code 18 : CURLE_PARTIAL_FILE (18)
        if exit_code != 0 and not (exit_code == 18 and method.upper() == 'HEAD'):
            raise exception.RestClientError(
                '"Remote command ({command})" returned exit status ({exit_code}): {error}'.format(
                    exit_code=exit_code, command=cmd, error=output)
            )

        # cleanup file copied once rest query has been done
        if kwargs.get('local_file'):
            sftp_client.remove(file_name)

        # return structured http response
        return HTTPResponse(output)

    def get(self, uri, **kwargs):
        r"""Sends a GET request.

        :param uri: URL of the http request.
        :param \**kwargs: Optional arguments that :func:`~request` takes.
        :return: :class:`HTTPResponse <HTTPResponse>` object
        :rtype: restclient.HTTPResponse
        """
        return self.request('get', uri, **kwargs)

    def options(self, uri, **kwargs):
        r"""Sends a OPTIONS request.

        :param uri: URL of the http request.
        :param \**kwargs: Optional arguments that :func:`~request` takes.
        :return: :class:`HTTPResponse <HTTPResponse>` object
        :rtype: restclient.HTTPResponse
        """
        return self.request('options', uri, **kwargs)

    def head(self, uri, **kwargs):
        r"""Sends a HEAD request.

        :param uri: URL of the http request.
        :param \**kwargs: Optional arguments that :func:`~request` takes.
        :return: :class:`HTTPResponse <HTTPResponse>` object
        :rtype: restclient.HTTPResponse
        """
        return self.request('head', uri, **kwargs)

    def post(self, uri, **kwargs):
        r"""Sends a POST request.

        :param uri: URL of the http request.
        :param \**kwargs: Optional arguments that :func:`~request` takes.
        :return: :class:`HTTPResponse <HTTPResponse>` object
        :rtype: restclient.HTTPResponse
        """
        return self.request('post', uri, **kwargs)

    def put(self, uri, **kwargs):
        r"""Sends a PUT request.

        :param uri: URL of the http request.
        :param \**kwargs: Optional arguments that :func:`~request` takes.
        :return: :class:`HTTPResponse <HTTPResponse>` object
        :rtype: restclient.HTTPResponse
        """
        return self.request('put', uri, **kwargs)

    def patch(self, uri, **kwargs):
        r"""Sends a PATCH request.

        :param uri: URL of the http request.
        :param \**kwargs: Optional arguments that :func:`~request` takes.
        :return: :class:`HTTPResponse <HTTPResponse>` object
        :rtype: restclient.HTTPResponse
        """
        return self.request('patch', uri, **kwargs)

    def delete(self, uri, **kwargs):
        r"""Sends a DELETE request.

        :param uri: URL of the http request.
        :param \**kwargs: Optional arguments that :func:`~request` takes.
        :return: :class:`HTTPResponse <HTTPResponse>` object
        :rtype: restclient.HTTPResponse
        """
        return self.request('delete', uri, **kwargs)


class HTTPResponse:
    def __init__(self, http_response_str):
        httplib_HTTPResponse = self.__parse_response(http_response_str)
        self.headers = {}
        self.status_code = httplib_HTTPResponse.status
        self.reason = httplib_HTTPResponse.reason
        # to get full response body from httplib, force read of full payload, and manually override length
        received_length = httplib_HTTPResponse.length
        httplib_HTTPResponse.length = None
        self.text = httplib_HTTPResponse.read().strip().decode('utf-8')
        httplib_HTTPResponse.length = received_length

        for key, value in httplib_HTTPResponse.getheaders():
            self.headers[key] = value

    def __parse_response(self, str_response):
        class FakeSocket(FakeSocketParam):
            def makefile(self, *args, **kw):
                return self

        # remove double '\r' as http.client only searching for the following sequences
        # to identify end of headers list : (b'\r\n', b'\n', b'')
        # so this is failing when receiving for example b'\r\r\n'
        # the change python made to break it in 2.7.13 can be seen here
        # https://fossies.org/diffs/Python/2.7.12_vs_2.7.13/Lib/httplib.py-diff.html
        raw_response = str_response.replace('\r\r\n', '\r\n')

        # make sure any unexpected ansi character added in headers are removed as preventing proper parsing of response
        socket_response = raw_response.split('\n\n', 1)
        if len(socket_response) == 1:
            header = socket_response[0]
            body = ''
        else:
            header, body = socket_response
        ansi_escape = re.compile(ANSI_REGEX, flags=re.IGNORECASE)
        socket_response = ansi_escape.sub('', header) + '\n\n' + body

        socket = FakeSocket(socket_response.encode('utf-8'))
        response = http_HTTPResponse(socket)
        response.begin()
        return response

    def check_for_success(self):
        if self.status_code not in [200, 201]:
            raise exception.RestClientError("http error received: %s" % self)

    def is_valid_json_body(self):
        try:
            json.loads(self.text)
        except ValueError:
            return False
        return True

    def json(self, **kwargs):
        try:
            return json.loads(self.text, **kwargs)
        except ValueError:
            raise exception.RestClientError("http response body is not in a valid json format : %s" + self.text)

    def __str__(self):
        result = "%s %s\n" % (self.status_code, self.reason)
        try:
            result += json.dumps(json.loads(self.text), indent=4, sort_keys=True)
        except ValueError:
            result += self.text
        return result
