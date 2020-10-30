"""
Some unit tests for RestSshClient.
"""
from __future__ import print_function
import json
try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path
import sys
import tempfile

import pytest

from jumpssh import exception, SSHSession, RestSshClient

from . import util as tests_util


REMOTE_HOST_IP_PORT = 'remotehost:5000'


@pytest.fixture(scope="module")
def docker_compose_file():
    yield Path("docker-compose_restclient.yaml")


@pytest.mark.flaky
def test_init_from_session(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')
    gateway_session = SSHSession(host=gateway_ip, port=gateway_port, username='user1', password='password1')

    with RestSshClient(gateway_session) as rest_client:
        http_response = rest_client.get('http://' + REMOTE_HOST_IP_PORT)

    assert http_response.status_code == 200
    assert http_response.text == 'Hello, World!'


@pytest.mark.flaky
def test_init_from_host_ip(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')

    with RestSshClient(host=gateway_ip, port=gateway_port,
                       username='user1', password='password1') as rest_client:
        http_response = rest_client.get('http://' + REMOTE_HOST_IP_PORT)

    assert http_response.status_code == 200
    assert http_response.text == 'Hello, World!'


def test_request(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')
    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()
    rest_client = RestSshClient(gateway_session)

    # check not properly formatted uri raise exception
    with pytest.raises(exception.RestClientError) as exc_info:
        rest_client.get('invalid_uri')
    assert 'returned exit status' in str(exc_info.value)

    # test header only
    http_response = rest_client.request(
        'GET',
        'http://' + REMOTE_HOST_IP_PORT,
        document_info_only=True)
    assert http_response.status_code == 200
    assert len(http_response.text) == 0

    # test uri parameters only
    parameters = {'param1': 'value1', 'param2': 'value2'}
    http_response = rest_client.request(
        'GET',
        'http://%s/echo-parameters' % REMOTE_HOST_IP_PORT,
        params=parameters)
    assert http_response.status_code == 200
    # value is a list as each parameter can be specified multiple times with different values
    expected_body = {}
    for key, value in parameters.items():
        expected_body[key] = [value]
    assert http_response.json() == expected_body

    # test headers are properly handled
    http_response = rest_client.request('GET',
                                        'http://%s/echo-headers' % REMOTE_HOST_IP_PORT,
                                        headers={'My-Header': 'My-Value'})
    assert http_response.status_code == 200
    assert 'My-Header' in http_response.json()
    assert http_response.json()['My-Header'] == 'My-Value'


def test_methods(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')
    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()
    rest_client = RestSshClient(gateway_session)

    uri = 'http://%s/echo-method' % REMOTE_HOST_IP_PORT

    # check proper http method is used for each function
    header_name = 'Request-Method'
    if sys.version_info[0] == 2:
        # HTTP header names in the response are all lowercase in Python 2.x.
        header_name = 'request-method'
    assert rest_client.get(uri).headers[header_name] == 'GET'
    assert rest_client.options(uri).headers[header_name] == 'OPTIONS'
    assert rest_client.post(uri).headers[header_name] == 'POST'
    assert rest_client.put(uri).headers[header_name] == 'PUT'
    assert rest_client.patch(uri).headers[header_name] == 'PATCH'
    assert rest_client.delete(uri).headers[header_name] == 'DELETE'
    assert rest_client.head(uri).headers[header_name] == 'HEAD'


def test_basic_auth(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')
    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()
    rest_client = RestSshClient(gateway_session)

    uri = 'http://%s/authentication-required' % REMOTE_HOST_IP_PORT

    # wrong auth param format
    with pytest.raises(exception.RestClientError) as exc_info:
        rest_client.request('GET', uri, auth="invalid_auth_format")
    assert 'Invalid auth parameter' in str(exc_info.value)

    # authentication in error
    http_response = rest_client.request('GET', uri, auth=("wrong_user", "wrong_password"))
    assert http_response.status_code == 401
    assert 'You have to login with proper credentials' in http_response.text

    # authentication in success
    http_response = rest_client.request('GET', uri, auth=("admin", "secret"))
    assert http_response.status_code == 200
    assert http_response.text == "Authentication successful"


def test_request_with_body(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')
    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()
    rest_client = RestSshClient(gateway_session)

    uri = 'http://%s/echo-body' % REMOTE_HOST_IP_PORT

    json_file_content = tests_util.create_random_json(5)

    # test body specified in input
    http_response = rest_client.post(uri, data=json.dumps(json_file_content))
    assert http_response.status_code == 200
    assert http_response.json() == json_file_content

    # test body from local file
    # 1. error raised when local file does not exist
    with pytest.raises(exception.RestClientError) as exc_info:
        rest_client.post(uri, local_file='missing_file')
    assert 'Invalid file path given' in str(exc_info.value)
    # 2. create file locally
    with tempfile.NamedTemporaryFile() as tmp_local_file:
        tmp_local_file.write(json.dumps(json_file_content).encode('utf-8'))
        tmp_local_file.seek(0)

        http_response = rest_client.post(uri, local_file=tmp_local_file.name)
        assert http_response.status_code == 200
        assert http_response.json() == json_file_content

        # check file copied on remote host has been properly removed
        assert not gateway_session.exists(path=tmp_local_file.name)

    # test body from remote file
    remote_file = 'remote_file.json'
    # 1. error raised when remote file does not exist
    with pytest.raises(exception.RestClientError) as exc_info:
        rest_client.post(uri, remote_file=remote_file)
    assert 'Invalid remote file path given' in str(exc_info.value)
    # 2. create file remotely
    gateway_session.file(remote_path=remote_file,
                         content=json.dumps(json_file_content))
    http_response = rest_client.post(uri, remote_file=remote_file)
    assert http_response.status_code == 200
    assert http_response.json() == json_file_content


def test_response_methods(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')
    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()
    rest_client = RestSshClient(gateway_session)

    endpoint = 'http://%s' % REMOTE_HOST_IP_PORT

    # check_for_success
    with pytest.raises(exception.RestClientError):
        rest_client.get(endpoint + '/dummy-uri').check_for_success()

    # is_valid_json_body
    assert rest_client.get(endpoint + '/json').is_valid_json_body() is True
    assert rest_client.get(endpoint + '/').is_valid_json_body() is False

    # json
    with pytest.raises(exception.RestClientError) as exc_info:
        rest_client.get(endpoint + '/').json()
    assert 'http response body is not in a valid json format' in str(exc_info.value)
