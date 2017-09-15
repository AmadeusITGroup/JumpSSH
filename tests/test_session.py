"""
Some unit tests for SSHSession.
"""
from __future__ import print_function
import errno
import json
import logging
try:
    import unittest.mock as mock
except ImportError:
    import mock
import os
import socket
import time

import paramiko
import pytest

from jumpssh import util, exception, SSHSession

from . import util as tests_util


logging.basicConfig()


@pytest.fixture(scope="module")
def docker_env():
    my_docker_env = tests_util.DockerEnv()
    my_docker_env.start_host('image_sshd', 'gateway')
    my_docker_env.start_host('image_sshd', 'remotehost')
    my_docker_env.start_host('image_sshd', 'remotehost2')
    yield my_docker_env  # provide the fixture value
    print("teardown docker_env")
    my_docker_env.clean()


def test_unknown_host():
    with pytest.raises(exception.ConnectionError) as excinfo:
        SSHSession(host='unknown_host', username='my_user').open()
    assert type(excinfo.value.__cause__) == socket.gaierror

    with pytest.raises(exception.ConnectionError) as excinfo:
        SSHSession(host='unknown_host', username='my_user').open(retry=2, retry_interval=2)
    assert type(excinfo.value.__cause__) == socket.gaierror


def test_active_close_session(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')

    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()
    assert gateway_session.is_active()

    # open an already active session should be harmless
    gateway_session.open()
    assert gateway_session.is_active()

    remotehost_ip, remotehost_port = docker_env.get_host_ip_port('remotehost')
    remotehost_session = gateway_session.get_remote_session(host=tests_util.get_host_ip(), port=remotehost_port,
                                                            username='user1', password='password1')
    assert remotehost_session.is_active()

    # check that gateway session is well closed
    gateway_session.close()
    assert not gateway_session.is_active()
    # remote session is also automatically closed
    assert not remotehost_session.is_active()

    # closing a closed session does nothing
    gateway_session.close()

    # running command on an inactive session will automatically open the session
    assert gateway_session.run_cmd('ls').exit_code == 0


def test_active_close_session_with_context_manager(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')

    with SSHSession(host=gateway_ip, port=gateway_port,
                    username='user1', password='password1') as gateway_session:
        assert gateway_session.is_active()

        remotehost_ip, remotehost_port = docker_env.get_host_ip_port('remotehost')
        remotehost_session = gateway_session.get_remote_session(host=tests_util.get_host_ip(), port=remotehost_port,
                                                                username='user1', password='password1')
        assert remotehost_session.is_active()

    # check that gateway session is well closed
    assert not gateway_session.is_active()

    # remote session is also automatically closed
    assert not remotehost_session.is_active()

    # try reopening same session
    gateway_session.open()

    assert gateway_session.is_active()

    assert gateway_session.get_exit_code('ls') == 0


def test_ssh_connection_error(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')

    # open first ssh session to gateway
    gateway_session1 = SSHSession(host=gateway_ip, port=gateway_port,
                                  username='user1', password='password1').open()

    # modify password from session 1
    gateway_session1.run_cmd('echo "user1:newpassword" | sudo -S chpasswd')

    # try to open 2nd session
    with pytest.raises(exception.ConnectionError) as excinfo:
        SSHSession(host=gateway_ip, port=gateway_port, username='user1', password='password1').open()
    assert type(excinfo.value.__cause__) == paramiko.ssh_exception.AuthenticationException

    # set back correct password from session 1
    gateway_session1.run_cmd('echo "user1:password1" | sudo -S chpasswd')

    # try again to open 2nd session
    gateway_session2 = SSHSession(host=gateway_ip, port=gateway_port,
                                  username='user1', password='password1').open()
    assert gateway_session2.is_active()


def test_run_cmd(docker_env, capfd):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')

    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()
    assert gateway_session.is_active()

    # basic successful command
    (exit_code, output) = gateway_session.run_cmd('hostname')
    assert exit_code == 0
    assert output == 'gateway.example.com'

    # successful list command
    gateway_session.run_cmd(['cd /etc', 'ls'])

    # wrong command
    (exit_code, output) = gateway_session.run_cmd('dummy commmand', raise_if_error=False)
    assert exit_code == 127

    with pytest.raises(exception.RunCmdError) as excinfo:
        gateway_session.run_cmd('dummy commmand')
    assert excinfo.value.exit_code == 127
    assert excinfo.value.command == 'dummy commmand'

    # wrong command type
    with pytest.raises(TypeError):
        gateway_session.run_cmd({'key': 'value'})

    # standard output is empty by default (without continuous_output flag)
    gateway_session.run_cmd('ls -lta /')
    out, err = capfd.readouterr()
    assert len(out) == 0

    # display continuous output on stdout while command is running
    gateway_session.run_cmd('ls -lta /', continuous_output=True)
    out, err = capfd.readouterr()
    assert len(out) > 0


def test_run_cmd_sudo(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')

    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()

    # run command as user2
    assert gateway_session.run_cmd('whoami', username='user2').output == 'user2'

    # run bash builtins commands with sudo (here command 'source')
    gateway_session.file(remote_path='/home/user2/ssh_setenv', use_sudo=True, owner='user2',
                         content='MY_VAR=variable_set')
    gateway_session.run_cmd('source /home/user2/ssh_setenv', username='user2')


def test_run_cmd_silent(docker_env, caplog):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')

    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()

    # run command and check full command is logged
    text = 'text with public and private data'
    cmd = "echo '%s'" % text
    assert gateway_session.run_cmd(cmd).output == text
    assert cmd in caplog.text

    # check nothing is logged when silent is True
    text = 'another text with public and private data'
    cmd = "echo '%s'" % text
    assert gateway_session.run_cmd(cmd, silent=True).output == text
    assert cmd not in caplog.text

    # check data is concealed when silent is a list
    text = 'a third text with public and private data'
    cmd = "echo '%s'" % text
    assert gateway_session.run_cmd(cmd, silent=['third', 'private data']).output == text
    assert cmd not in caplog.text
    assert 'a XXXXXXX text with public and XXXXXXX' in caplog.text

    # check data is concealed when silent is a list with regexp
    text = 'another text   to   test    regexp'
    cmd = "echo '%s'" % text
    assert gateway_session.run_cmd(cmd, silent=['\s+']).output == text
    assert cmd not in caplog.text
    assert 'anotherXXXXXXXtextXXXXXXXtoXXXXXXXtestXXXXXXXregexp' in caplog.text


def test_run_cmd_success_exit_code(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')

    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()

    # check invalid type for parameter
    with pytest.raises(TypeError):
        gateway_session.run_cmd('hostname', success_exit_code={'key': 'value'})

    # valid command with custom success exit code should raise RunCmdError
    with pytest.raises(exception.RunCmdError) as exc_info:
        gateway_session.run_cmd('hostname', success_exit_code=3)
    assert exc_info.value.exit_code == 0
    assert exc_info.value.success_exit_code == [3]

    # dummy command should not raise error as exit code 127 is valid too
    # and test also that list is supported
    gateway_session.run_cmd('dummy commmand', success_exit_code=[0, 127])
    gateway_session.run_cmd('hostname', success_exit_code=[0, 127])


def test_run_cmd_retry(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')

    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()

    with pytest.raises(exception.RunCmdError) as exc_info:
        gateway_session.run_cmd('dummy commmand', retry=2, retry_interval=1)
    assert exc_info.value.runs_nb == 3

    # prepare command that append a character in file at each new run
    temporary_filename1 = util.id_generator(size=7)
    cmd = "echo -n 'p' >> {0} && grep 'pppp' {0}".format(temporary_filename1)

    # command should still raise exception after 2 retries(=3 runs) as we except 4 p
    with pytest.raises(exception.RunCmdError) as exc_info:
        gateway_session.run_cmd(cmd, retry=2, retry_interval=1)
    assert exc_info.value.runs_nb == 3

    # same command should work fine with 3 retries(=4 runs)
    temporary_filename2 = util.id_generator(size=8)
    cmd = cmd.replace(temporary_filename1, temporary_filename2)
    result = gateway_session.run_cmd(cmd, retry=3, retry_interval=1)

    # by default no history kept
    assert len(result.result_list) == 0

    # check history is kept when requested
    temporary_filename3 = util.id_generator(size=8)
    cmd = cmd.replace(temporary_filename2, temporary_filename3)
    result = gateway_session.run_cmd(cmd, retry=3, retry_interval=1, keep_retry_history=True)
    assert len(result.result_list) == 4


def test_run_cmd_interrupt_remote_command(docker_env, monkeypatch, caplog):
    """Test behavior of run_cmd when user hit Contrl-C while a command is being executed remotely"""
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')
    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()

    mock_input = '__builtin__.raw_input' if util.PY2 else 'builtins.input'

    # 1. if user request to interrupt remote command
    with pytest.raises(KeyboardInterrupt):
        # raise KeyboardInterrupt while command is running
        with mock.patch('select.select', side_effect=KeyboardInterrupt('Fake Ctrl-C')):
            # request to terminate remote command simulating the user entering "Y" in the terminal
            monkeypatch.setattr(mock_input, lambda x: "Y")
            gateway_session.run_cmd('sleep 30')

    # check command is no longer running on remote host
    assert gateway_session.get_exit_code('ps aux | grep -v grep | grep "sleep 30"') == 1

    # 2. user request to NOT interrupt remote command
    with pytest.raises(KeyboardInterrupt):
        # raise KeyboardInterrupt while command is running
        with mock.patch('select.select', side_effect=KeyboardInterrupt('Fake Ctrl-C')):
            # request to terminate remote command simulating the user entering "N" in the terminal
            monkeypatch.setattr(mock_input, lambda x: "N")
            gateway_session.run_cmd('sleep 40')

    # check command is still running on remote host
    assert gateway_session.get_exit_code('ps aux | grep -v grep | grep "sleep 40"') == 0

    # 3. user press enter (default value of util.yes_no_query used), we expect remote command to be stopped
    with pytest.raises(KeyboardInterrupt):
        # raise KeyboardInterrupt while command is running
        with mock.patch('select.select', side_effect=KeyboardInterrupt('Fake Ctrl-C')):
            # send empty string simulating the user pressing enter in the terminal
            monkeypatch.setattr(mock_input, lambda x: '')
            gateway_session.run_cmd('sleep 50')

    # check command is no longer running on remote host
    assert gateway_session.get_exit_code('ps aux | grep -v grep | grep "sleep 50"') == 1

    # 4. user press Contrl-C twice, check remote command is still running
    with pytest.raises(KeyboardInterrupt):
        # raise KeyboardInterrupt while command is running
        with mock.patch('select.select', side_effect=KeyboardInterrupt('Fake Ctrl-C')):
            # user press a second time Contrl-C
            with mock.patch(mock_input, side_effect=KeyboardInterrupt('2nd Fake Ctrl-C')):
                gateway_session.run_cmd('sleep 60')

    # check command is still running on remote host
    assert gateway_session.get_exit_code('ps aux | grep -v grep | grep "sleep 60"') == 0

    # 5. user press Contrl-C once but take time to answer if remote must be closed or not, and channel is closed
    # so we cannot terminate remote command but remote command finished its execution
    with pytest.raises(KeyboardInterrupt):
        # raise KeyboardInterrupt while command is running
        with mock.patch('select.select', side_effect=KeyboardInterrupt('Fake Ctrl-C')):
            # request to terminate remote command simulating the user entering "Y" in the terminal
            # but user answered after 4s while command finished after 3s so underline channel is already closed
            # and command still successfully run
            monkeypatch.setattr(mock_input, lambda x: time.sleep(4) or "Y")
            gateway_session.run_cmd('sleep 3')
    assert 'Remote command execution already finished with exit code' in caplog.text

    # 6. user press Contrl-C once but take time to answer if remote must be closed or not, and channel is closed
    # so we cannot terminate remote command and channel does't not have more information about remote command execution
    with pytest.raises(KeyboardInterrupt):
        # raise KeyboardInterrupt while command is running
        with mock.patch('select.select', side_effect=KeyboardInterrupt('Fake Ctrl-C')):
            # request to terminate remote command simulating the user entering "Y" in the terminal
            # but user answered after 4s while command finished after 3s so underline channel is already closed
            monkeypatch.setattr('paramiko.channel.Channel.recv_exit_status', lambda x: -1)
            gateway_session.run_cmd('sleep 3')
    assert 'Unable to terminate remote command because channel is closed.' in caplog.text


def test_get_cmd_output(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')
    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()

    assert gateway_session.get_cmd_output('hostname') == 'gateway.example.com'


def test_get_exit_code(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')

    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()
    assert gateway_session.get_exit_code('ls') == 0
    assert gateway_session.get_exit_code('dummy commmand') == 127


def test_input_data(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')

    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()

    commands = ['read -p "Requesting user input value?" my_var',
                'echo $my_var']

    # without input given, command will hang until timeout is reached
    with pytest.raises(exception.TimeoutError):
        gateway_session.run_cmd(commands, timeout=5)

    # with input given, command should run correctly and return the value entered
    assert gateway_session.get_cmd_output(commands,
                                          input_data={'Requesting user input value': 'dummy_value'}
                                          ).split()[-1] == "dummy_value"


def test_get_remote_session(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')
    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()

    remotehost_ip, remotehost_port = docker_env.get_host_ip_port('remotehost')
    remotehost_session = gateway_session.get_remote_session(host=tests_util.get_host_ip(),
                                                            port=remotehost_port,
                                                            username='user1',
                                                            password='password1')

    # run basic command on remote host
    assert remotehost_session.get_cmd_output('hostname') == 'remotehost.example.com'

    # request twice the same remote session just return the existing one
    assert gateway_session.get_remote_session(host=tests_util.get_host_ip(),
                                              port=remotehost_port,
                                              username='user1',
                                              password='password1') == remotehost_session

    # request another remote session to another host while an existing one already exists
    remotehost2_ip, remotehost2_port = docker_env.get_host_ip_port('remotehost2')
    remotehost2_session = gateway_session.get_remote_session(host=tests_util.get_host_ip(),
                                                             port=remotehost2_port,
                                                             username='user1',
                                                             password='password1')
    # check that new session is active
    assert remotehost2_session.is_active()
    assert remotehost2_session.get_cmd_output('hostname') == 'remotehost2.example.com'

    # check that previous session from gateway is still active
    assert remotehost_session.is_active()
    assert remotehost_session.get_cmd_output('hostname') == 'remotehost.example.com'

    # close a remote session and check we can still request ssh session with same parameters
    remotehost2_session.close()
    assert not remotehost2_session.is_active()
    remotehost2_session = gateway_session.get_remote_session(host=tests_util.get_host_ip(),
                                                             port=remotehost2_port,
                                                             username='user1',
                                                             password='password1')
    assert remotehost2_session.is_active()

    # close gateway session and check all child sessions are automatically closed
    gateway_session.close()
    assert not remotehost_session.is_active()
    assert not remotehost2_session.is_active()

    # get remote session from closed session should automatically open gateway session first
    # then return remote session
    remotehost_session = gateway_session.get_remote_session(host=tests_util.get_host_ip(),
                                                            port=remotehost_port,
                                                            username='user1',
                                                            password='password1')
    assert gateway_session.is_active()
    assert remotehost_session.is_active()


def test_handle_big_json_files(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')
    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()

    remotehost_ip, remotehost_port = docker_env.get_host_ip_port('remotehost')
    remotehost_session = gateway_session.get_remote_session(host=tests_util.get_host_ip(),
                                                            port=remotehost_port,
                                                            username='user1',
                                                            password='password1')
    # generate big json file on remotehost
    remote_path = '/tmp/dummy.json'
    dummy_json = tests_util.create_random_json(50000)
    remotehost_session.file(remote_path=remote_path, content=json.dumps(dummy_json))

    # read file from remote and check json is valid and identical to source
    dummy_json_from_remote = json.loads(remotehost_session.get_cmd_output('cat %s' % remote_path))
    assert dummy_json == dummy_json_from_remote


def test_exists(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')

    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()

    assert not gateway_session.exists('/home/user1/non_existing_file')

    gateway_session.run_cmd('touch /home/user1/existing_file')
    assert gateway_session.exists('/home/user1/existing_file')

    gateway_session.run_cmd('rm /home/user1/existing_file')
    assert not gateway_session.exists('/home/user1/existing_file')

    # create file visible only by user2
    gateway_session.run_cmd(['sudo mkdir /etc/user2_private_dir',
                             'sudo touch /etc/user2_private_dir/existing_file',
                             'sudo chown user2:user2 /etc/user2_private_dir',
                             'sudo chmod 600 /etc/user2_private_dir'])

    # check it is not visible by user1 by default
    assert not gateway_session.exists('/etc/user2_private_dir/existing_file')

    # check it is readable with root access
    assert gateway_session.exists('/etc/user2_private_dir/existing_file', use_sudo=True)

    # cleanup
    gateway_session.run_cmd('sudo rm -rf /etc/user2_private_dir')


def test_put(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')
    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()

    remotehost_ip, remotehost_port = docker_env.get_host_ip_port('remotehost')
    remotehost_session = gateway_session.get_remote_session(host=tests_util.get_host_ip(),
                                                            port=remotehost_port,
                                                            username='user1',
                                                            password='password1')
    # exception is raised when local file does not exist
    local_path = 'missing_folder/missing_path'
    with pytest.raises(IOError) as excinfo:
        remotehost_session.put(local_path=local_path, remote_path='/tmp/my_file')
    assert excinfo.value.errno == errno.ENOENT
    assert excinfo.value.strerror == "Local file '%s' does not exist" % local_path

    # create random file locally
    local_path = os.path.join(os.path.dirname(__file__), 'random_file')
    dummy_json = tests_util.create_random_json()
    with open(local_path, 'wb') as random_file:
        random_file.write(json.dumps(dummy_json).encode('utf-8'))
    try:
        # copy file on remote session
        remote_path = '/tmp/random_file'
        assert remotehost_session.exists(remote_path) is False
        remotehost_session.put(local_path=local_path, remote_path=remote_path)
        assert remotehost_session.exists(remote_path) is True

        # copy file on remote session as user2 with specific file permissions
        remote_path = '/tmp/random_file2'
        assert remotehost_session.exists(remote_path) is False
        remotehost_session.put(local_path=local_path, remote_path=remote_path, owner='user2', permissions='600')
        assert remotehost_session.exists(remote_path) is True
        assert remotehost_session.get_cmd_output(
            "ls -l %s | awk '{print $3}'" % remote_path) == 'user2'
        assert remotehost_session.get_cmd_output(
            "stat -c '%a %n' " + remote_path + " | awk '{print $1}'") == '600'
    finally:
        os.remove(local_path)


def test_get(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')
    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()

    remotehost_ip, remotehost_port = docker_env.get_host_ip_port('remotehost')
    remotehost_session = gateway_session.get_remote_session(host=tests_util.get_host_ip(),
                                                            port=remotehost_port,
                                                            username='user1',
                                                            password='password1')

    # create random file on remote host and ensure it is properly there
    remote_path = "remote_file"
    remotehost_session.file(remote_path=remote_path, content=json.dumps(tests_util.create_random_json()))
    assert remotehost_session.exists(remote_path)

    # download that file in local folder
    local_folder = '/tmp/'
    remotehost_session.get(remote_path=remote_path, local_path=local_folder)
    local_file_path = os.path.join(local_folder, os.path.basename(remote_path))
    assert os.path.isfile(local_file_path)
    os.remove(local_file_path)

    # download that file locally specifying local filename
    local_file_path = '/tmp/downloaded_file_' + util.id_generator(size=20)
    remotehost_session.get(remote_path=remote_path, local_path=local_file_path)
    os.remove(local_file_path)

    # get remote file from location not accessible from current user
    local_folder = '/tmp/'
    restricted_remote_path = os.path.join('/etc', remote_path)
    remotehost_session.run_cmd('sudo mv %s %s' % (remote_path, restricted_remote_path))
    remotehost_session.get(remote_path=restricted_remote_path, local_path=local_folder, use_sudo=True)
    local_file_path = os.path.join(local_folder, os.path.basename(remote_path))
    assert os.path.isfile(local_file_path)
    os.remove(local_file_path)


def test_file(docker_env):
    gateway_ip, gateway_port = docker_env.get_host_ip_port('gateway')
    gateway_session = SSHSession(host=gateway_ip, port=gateway_port,
                                 username='user1', password='password1').open()

    remotehost_ip, remotehost_port = docker_env.get_host_ip_port('remotehost')
    remotehost_session = gateway_session.get_remote_session(host=tests_util.get_host_ip(),
                                                            port=remotehost_port,
                                                            username='user1',
                                                            password='password1')
    file_content = json.dumps(tests_util.create_random_json())

    # create file in a location with root access needed should fail by default
    with pytest.raises(IOError) as excinfo:
        remotehost_session.file(remote_path='/etc/a_file', content=file_content)
    assert excinfo.value.errno == errno.EACCES
    assert excinfo.value.strerror == 'Permission denied'

    # do same command with root access
    remotehost_session.file(remote_path='/etc/a_file', content=file_content, use_sudo=True)
