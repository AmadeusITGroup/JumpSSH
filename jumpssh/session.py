# external import
from __future__ import print_function
import collections
import datetime
import errno
from io import StringIO
import logging
import os
import re
import select
import time

import paramiko

from . import util, exception

logger = logging.getLogger(__name__)

SSH_PORT = 22


class SSHSession(object):
    """Establish SSH session with a remote host

    :param host: name or ip of the remote host
    :param username: user to be used for remote ssh session
    :param proxy_transport:
        :class:`paramiko.transport.Transport <paramiko.transport.Transport>` object for an SSH connection
        used to establish ssh session between 2 remotes hosts
    :param private_key_file: local path to a private key file to use if key needed for authentication
        and not present in standard path (~/.ssh/)
    :param port: port to connect to the remote host (default 22)
    :param password: password to be used for authentication with remote host
    :param missing_host_key_policy: set policy to use when connecting to servers without a known host key.
        This parameter is a class **instance** of type
        :class:`paramiko.client.MissingHostKeyPolicy <paramiko.client.MissingHostKeyPolicy>`, not a **classes** itself

    Usage::

        >>> from jumpssh import SSHSession
        >>> gateway_session = SSHSession('gateway.example.com', 'my_user', password='my_password')
    """
    def __init__(
            self,
            host,
            username,
            proxy_transport=None,
            private_key_file=None,
            port=SSH_PORT,
            password=None,
            missing_host_key_policy=None,
            compress=False
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.retry_nb = 0
        self.proxy_transport = proxy_transport
        self.private_key_file = private_key_file
        self.compress = compress
        self.ssh_remote_sessions = {}

        self.ssh_client = paramiko.client.SSHClient()
        self.ssh_transport = None

        # automatically accept unknown host keys by default
        if not missing_host_key_policy:
            missing_host_key_policy = paramiko.AutoAddPolicy()
        self.ssh_client.set_missing_host_key_policy(missing_host_key_policy)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        self.close()

    def __repr__(self):
        return '%s(host=%s, username=%s, port=%s, private_key_file=%s, proxy_transport=%s)' \
               % (self.__class__.__name__, self.host, self.username, self.port,
                  self.private_key_file, repr(self.proxy_transport))

    def is_active(self):
        """ Check if connection with remote host is still active

        An inactive SSHSession cannot run command on remote host

        :return: True if current session is still active, else False
        :rtype: bool

        Usage::
            >>> from jumpssh import SSHSession
            >>> with SSHSession('gateway.example.com', 'my_user', password='my_password') as ssh_session:
            >>> ... ssh_session.is_active()
            True
            >>> ssh_session.is_active()
            False
        """
        return self.ssh_client and self.ssh_client.get_transport() and self.ssh_client.get_transport().is_active()

    def open(self, retry=0, retry_interval=10):
        """Open session with the remote host

        :param retry: number of retry to establish connection with remote host (-1 for infinite retry)
        :param retry_interval: number of seconds between each retry
        :return: same SSHSession opened

        Usage::
            >>> from jumpssh import SSHSession
            >>> ssh_session = SSHSession('gateway.example.com', 'my_user', password='my_password').open()
            >>> ssh_session.is_active()
            True
        """
        # session is already active, nothing more to do
        if self.is_active():
            return

        while True:
            try:
                # if `proxy_transport` is given it will open a remote ssh session from current ssh session
                if self.proxy_transport:
                    # open a `direct-tcpip` channel passing
                    # the destination hostname:port and the local hostname:port
                    dest_addr = (self.host, self.port)
                    local_addr = ('localhost', SSH_PORT)
                    ssh_channel = self.proxy_transport.open_channel("direct-tcpip", dest_addr, local_addr)
                    hostname = 'localhost'
                    port = SSH_PORT
                # else it will be a direct ssh session from local machine
                else:
                    ssh_channel = None
                    hostname = self.host
                    port = self.port

                # connect to the host
                self.ssh_client.connect(hostname=hostname,
                                        port=port,
                                        username=self.username,
                                        sock=ssh_channel,
                                        key_filename=self.private_key_file,
                                        password=self.password,
                                        compress=self.compress)

                # no exception raised => connected to remote host
                break

            except Exception as ex:
                # negative retry value means infinite retry
                if retry < 0 or self.retry_nb < retry:
                    logger.warning("ssh to '%s:%s' still not possible (attempt %d): %s.\nKeep retrying..."
                                   % (self.host, self.port, self.retry_nb, repr(ex)))
                    self.retry_nb += 1
                    time.sleep(retry_interval)
                else:
                    raise exception.ConnectionError("Unable to connect to '%s:%s' with user '%s'"
                                                    % (self.host, self.port, self.username), original_exception=ex)

        # Get the client's transport
        self.ssh_transport = self.ssh_client.get_transport()

        logger.info("Successfully connected to '%s:%s'" % (self.host, self.port))
        return self

    def close(self):
        """ Close connection with remote host

        Usage::
            >>> from jumpssh import SSHSession
            >>> ssh_session = SSHSession('gateway.example.com', 'my_user', password='my_password').open()
            >>> ssh_session.is_active()
            True
            >>> ssh_session.close()
            >>> ssh_session.is_active()
            False
        """
        if hasattr(self, 'ssh_remote_sessions') and self.ssh_remote_sessions:
            for remote_session in self.ssh_remote_sessions.values():
                remote_session.close()
        if hasattr(self, 'ssh_client') and self.is_active():
            logger.debug("Closing connection to '%s:%s'..." % (self.host, self.port))
            self.ssh_client.close()
            # clear local host keys as they may not be valid for next connection
            self.ssh_client.get_host_keys().clear()

    def run_cmd(
            self,
            cmd,
            username=None,
            raise_if_error=True,
            continuous_output=False,
            silent=False,
            timeout=None,
            input_data=None,
            success_exit_code=0,
            retry=0,
            retry_interval=5,
            keep_retry_history=False
    ):
        """ Run command on the remote host and return result locally

        :param cmd: command to execute on remote host
               cmd can be a str or a list of str
        :param username: user used to execute the command (sudo privilege needed)
        :param raise_if_error:
            if True, raise SSHException when exit code of the command is different from 0
            else just return exit code and command output
        :param continuous_output: if True, print output all along the command is running
        :param silent:
            if True, does not log the command run (useful if sensitive information are used in command)
            if parameter is a list, all strings of the command matching an item of the list will be concealed
            in logs (regexp supported)
        :param timeout: length in seconds after what a TimeoutError exception is raised
        :param input_data:
            key/value dictionary used when remote command expects input from user
            when key is matching command output, value is sent
        :param success_exit_code: integer or list of integer considered as a success exit code for command run
        :param retry: number of retry until exit code is part of successful exit code list (-1 for infinite retry) or
            RunCmdError exception is raised
        :param retry_interval: number of seconds between each retry
        :param keep_retry_history: if True, all retries results are kept and accessible in return result
            default is False as we don't want to save by default all output for all retries especially for big output
        :raises TimeoutError: if command run longer than the specified timeout
        :raises TypeError: if `cmd` parameter is neither a string neither a list of string
        :raises SSHException: if current SSHSession is already closed
        :raises RunCmdError: if exit code of the command is different from 0 and raise_if_error is True
        :return: a class inheriting from collections.namedtuple containing mainly `exit_code` and `output`
            of the remotely executed command
        :rtype: RunCmdResult

        Usage::
            >>> from jumpssh import SSHSession
            >>> with SSHSession('gateway.example.com', 'my_user', password='my_password') as ssh_session:
            >>> ...     ssh_session.run_cmd('hostname')
            RunSSHCmdResult(exit_code=0, output=u'gateway.example.com')
        """
        user = self.username

        # check type of command parameter is valid
        try:
            string_type = basestring
        except NameError:
            string_type = str
        if isinstance(cmd, list):
            cmd = " && ".join(cmd)
        elif not isinstance(cmd, string_type):
            raise TypeError("Invalid type for cmd argument '%s'" % type(cmd))

        # success_exit_code must be int or list of int
        if isinstance(success_exit_code, int):
            success_exit_code = [success_exit_code]
        elif not isinstance(success_exit_code, list):
            raise TypeError("Invalid type for success_exit_code argument '%s'" % type(success_exit_code))

        my_cmd = cmd
        if username:
            user = username
            # need to run full command with shell to support shell builtins commands (source, ...)
            my_cmd = 'sudo su - %s -c "%s"' % (user, cmd.replace('"', '\\"'))

        # check session is still active before running a command, else try to open it
        if not self.is_active():
            self.open()

        # conceal text from command to be logged if requested with silent parameter
        cmd_for_log = cmd
        if isinstance(silent, list):
            for pattern in silent:
                cmd_for_log = re.sub(pattern=pattern, repl='XXXXXXX', string=cmd_for_log)

        if silent is not True:
            logger.debug("Running command '%s' on '%s' as %s..." % (cmd_for_log, self.host, user))

        # keep track of all results for each run to make them available in response object
        result_list = []

        # retry command until exit_code in success code list or max retry nb reached
        retry_nb = 0
        while True:
            channel = self.ssh_transport.open_session()

            # raise error rather than blocking the call
            channel.setblocking(0)

            # Forward local agent
            paramiko.agent.AgentRequestHandler(channel)
            # Commands executed after this point will see the forwarded agent on the remote end.

            channel.set_combine_stderr(True)
            channel.get_pty()
            channel.exec_command(my_cmd)

            # prepare timer for timeout
            start = datetime.datetime.now()
            start_secs = time.mktime(start.timetuple())

            output = StringIO()
            try:
                # wait until command finished running or timeout is reached
                while True:
                    got_chunk = False
                    readq, _, _ = select.select([channel], [], [], timeout)
                    for c in readq:
                        if c.recv_ready():
                            data = channel.recv(len(c.in_buffer)).decode('utf-8')
                            output.write(data)
                            got_chunk = True

                            # print output all along the command is running
                            if not silent and continuous_output and len(data) > 0:
                                print(data)

                            if input_data and channel.send_ready():
                                # We received a potential prompt.
                                for pattern in input_data.keys():
                                    # pattern text matching current output => send input data
                                    if re.search(pattern, data):
                                        channel.send(input_data[pattern] + '\n')

                    # remote process has exited and returned an exit status
                    if not got_chunk and channel.exit_status_ready() and not channel.recv_ready():
                        channel.shutdown_read()  # indicate that we're not going to read from this channel anymore
                        channel.close()
                        break  # exit as remote side is finished and our buffers are empty

                    # Timeout check
                    if timeout:
                        now = datetime.datetime.now()
                        now_secs = time.mktime(now.timetuple())
                        et_secs = now_secs - start_secs
                        if et_secs > timeout:
                            raise exception.TimeoutError(
                                "Timeout of %ds reached when calling command '%s'. "
                                "Increase timeout if you think the command was still running successfully."
                                % (timeout, cmd_for_log))
            except KeyboardInterrupt:
                # if channel still active, forward Ctrl-C to remote host if requested by user
                if self.is_active() and util.yes_no_query("Terminate remote command '%s'?" % cmd_for_log,
                                                          default=True,
                                                          interrupt=False):
                    # channel has been closed pending response from user, we don't have access to remote server anymore
                    if channel.closed:
                        exit_code = channel.recv_exit_status()
                        if exit_code == -1:
                            logger.warning("Unable to terminate remote command because channel is closed.")
                        else:
                            logger.info("Remote command execution already finished with exit code %s" % exit_code)
                    else:
                        # forward Ctrl-C to remote host
                        channel.send('\x03')
                        channel.close()
                raise

            exit_code = channel.recv_exit_status()
            output_value = output.getvalue().strip()

            # keep result of all runs is result, not only the last one
            if keep_retry_history:
                result_list.append(RunSSHCmdResult(exit_code=exit_code, output=output_value))

            if exit_code in success_exit_code:
                # command ran successfully, no retry needed
                break
            else:
                if retry < 0 or retry_nb < retry:
                    retry_nb += 1
                    time.sleep(retry_interval)
                    continue
                # max retry reached and exception must be raised
                elif raise_if_error:
                    raise exception.RunCmdError(exit_code=exit_code,
                                                success_exit_code=success_exit_code,
                                                command=cmd_for_log,
                                                error=output_value,
                                                runs_nb=retry_nb+1)
                else:
                    # command ended in error but max retry already reached and no exception must be raised
                    break

        # return result of run command + all information used to run the command
        return RunCmdResult(exit_code=exit_code,
                            output=output_value,
                            result_list=result_list,
                            command=cmd_for_log,
                            success_exit_code=success_exit_code,
                            runs_nb=retry_nb+1)

    def get_cmd_output(self, cmd, **kwargs):
        """ Return output of remotely executed command

            Support same parameters than `run_cmd` method

        :param cmd: remote command to execute
        :return: output of remotely executed command
        :rtype: str

        Usage::
            >>> from jumpssh import SSHSession
            >>> with SSHSession('gateway.example.com', 'my_user', password='my_password') as ssh_session:
            >>> ... ssh_session.get_cmd_output('hostname'))
            u'gateway.example.com'
        """
        return self.run_cmd(cmd=cmd, **kwargs).output

    def get_exit_code(self, cmd, **kwargs):
        """ Return exit code of remotely executed command

            Support same parameters than `run_cmd` method

        :param cmd: remote command to execute
        :return: exit code of remotely executed command
        :rtype: int

        Usage::
            >>> from jumpssh import SSHSession
            >>> with SSHSession('gateway.example.com', 'my_user', password='my_password') as ssh_session:
            >>> ... ssh_session.get_exit_code('ls')
            0
            >>> ... ssh_session.get_exit_code('dummy_command')
            127
        """
        return self.run_cmd(cmd=cmd, raise_if_error=False, **kwargs).exit_code

    def get_remote_session(
            self,
            host,
            username=None,
            retry=0,
            private_key_file=None,
            port=SSH_PORT,
            password=None,
            retry_interval=10
    ):
        """ Establish connection with a remote host from current session

        :param host: name or ip of the remote host
        :param username: user to be used for remote ssh session
        :param retry: retry number to establish connection with remote host (-1 for infinite retry)
        :param private_key_file: local path to a private key file to use if key needed for authentication
        :param port: port to connect to the remote host (default 22)
        :param password: password to be used for authentication with remote host
        :param retry_interval: number of seconds between each retry
        :return: session object of the remote host
        :rtype: SSHSession

        Usage::

            # open session with remote host
            >>> from jumpssh import SSHSession
            >>> ssh_session = SSHSession('gateway.example.com', 'my_user', password='my_password').open()

            # get remote session using same user than current session and same authentication method
            >>> remote_session = ssh_session.get_remote_session('remote.example.com')

            # get remote session with specific user and password
            >>> remote_session = ssh_session.get_remote_session('remote.example.com',
            ...                                                 username='other_user',
            ...                                                 password='other_user_password')

            # retry indefinitely to connect to remote host until success
            >>> remote_session = ssh_session.get_remote_session('remote.example.com', retry=-1)
        """
        # check session is still active before using it as a jump server, else try to open it
        if not self.is_active():
            self.open()

        # get user to be used for remote ssh session (default : same user than parent session)
        user = self.username
        if username:
            user = username

        # build remote session key to identify this session among others
        session_key = ('%s_%s_%s' % (host, port, user)).lower()

        remote_session = self.ssh_remote_sessions.get(session_key)
        if remote_session:
            # if same session already active, just return it
            if remote_session.is_active():
                return remote_session
            else:
                # if same session exists but not usable, cleanup object
                del self.ssh_remote_sessions[session_key]

        logger.info("Connecting to '%s:%s' through '%s' with user '%s'..." % (host, port, self.host, user))
        remote_session = SSHSession(host=host,
                                    username=user,
                                    proxy_transport=self.ssh_transport,
                                    private_key_file=private_key_file,
                                    port=port,
                                    password=password).open(retry=retry,
                                                            retry_interval=retry_interval)

        # keep reference to opened session, to be able to reuse it later
        self.ssh_remote_sessions[session_key] = remote_session

        return remote_session

    def get_sftp_client(self):
        """ See documentation for available methods on paramiko.sftp_client at :
            http://docs.paramiko.org/en/latest/api/sftp.html

        :return: paramiko SFTP client object.
        :rtype: paramiko.sftp_client.SFTPClient

        Usage::
            # open session with remote host
            >>> from jumpssh import SSHSession
            >>> ssh_session = SSHSession('gateway.example.com', 'my_user', password='my_password').open()

            # get sftp client
            >>> sftp_client = ssh_session.get_sftp_client()
        """
        return paramiko.sftp_client.SFTPClient.from_transport(self.ssh_transport)

    def exists(
            self,
            path,
            use_sudo=False
    ):
        """ Check if path exists on the remote host

        :param path: remote path to check for existence
        :param use_sudo: if True, allow to check path current user doesn't have access by default
        :return: True, if specified `path` exists on the remote host else False
        :rtype: bool

        Usage::
            >>> with SSHSession('gateway.example.com', 'my_user', password='my_password') as ssh_session:
            >>> ... ssh_session.exists('/path/to/remote/file')
            False
            >>> ... ssh_session.exists('/home/other_user/.ssh', use_sudo=True)
            True
        """
        # cannot use sftp as sudo is not possible
        cmd = "ls %s" % path
        if use_sudo:
            cmd = 'sudo ' + cmd
        return self.get_exit_code(cmd, silent=True) == 0

    def put(self,
            local_path,
            remote_path,
            use_sudo=False,
            owner=None,
            permissions=None,
            username=None,
            ):
        """ Upload a file to the remote host

        :param local_path: path of the local file to upload
        :param remote_path: destination folder in which to upload the local file
        :param use_sudo: allow to upload a file in location with restricted permissions
        :param owner: user that will own the copied file on the remote host
            syntax : `user:group` or simply `user` if same than group
        :param permissions: permissions to apply on the remote file (chmod format)
        :param username: sudo user
        :raise IOError: if local file `local_path` does not exist

        Usage::

            # copy local file on remote host
            >>> ssh_session.put(local_path='/path/to/local/file', remote_path='/path/to/remote/file')

            # copy local file on remote host in a remote path needing sudo permission
            >>> ssh_session.put(local_path='/path/to/local/file', remote_path='/path/to/remote/file', use_sudo=True)

            # copy local file on remote host with specific owner and permissions
            >>> ssh_session.put(local_path='/path/to/local/file', remote_path='/path/to/remote/file',
            ...                 owner='root', permissions='600')
        """
        if not os.path.isfile(local_path):
            raise IOError(errno.ENOENT, "Local file '%s' does not exist" % local_path)

        logger.debug("Copy local file '%s' on remote host '%s' in '%s' as '%s'"
                     % (local_path, self.host, remote_path, self.username))

        # create file remotely
        with open(local_path, 'rb') as local_file:
            self.file(remote_path=remote_path, content=local_file.read(),
                      use_sudo=use_sudo, owner=owner, permissions=permissions, username=username, silent=True)

    def get(self,
            remote_path,
            local_path,
            use_sudo=False,
            username=None
            ):
        """Download a file from the remote host

        :param remote_path: remote path of the file to download
        :param local_path: local path where to download the file
        :param use_sudo: allow to download a file from a location current user does not have access
        :param username: sudo user

        Usage::

            # download remote file in local directory
            >>> ssh_session.get(remote_path='/path/to/remote/file', local_path='/local/folder')

            # donload remote file from a path not accessible by current user
            >>> ssh_session.get(local_path='/path/to/local/file', remote_path='/path/to/remote/file', use_sudo=True)
        """
        copy_path = remote_path
        remote_filename = os.path.basename(remote_path)
        sudo_username = username if username else 'root' if use_sudo else None

        # copy first remote file in a temporary location accessible from current user
        if use_sudo:
            copy_path = "/tmp/%s" % util.id_generator(size=15)
            copy_command = "cp %s %s" % (remote_path, copy_path)
            self.run_cmd(copy_command, silent=True, username=sudo_username)

        # if local download path is a directory, local filename will be same as remote
        if os.path.isdir(local_path):
            local_path = os.path.join(local_path, remote_filename)

        sftp_client = self.get_sftp_client()
        try:
            with open(local_path, mode='w') as local_file:
                with sftp_client.file(copy_path) as remote_file:
                    local_file.write(remote_file.read().decode('utf-8'))
        finally:
            if use_sudo:
                # cleanup temporary file
                self.run_cmd('rm %s' % copy_path, silent=True, username=sudo_username)

    def file(
            self,
            remote_path,
            content,
            use_sudo=False,
            owner=None,
            permissions=None,
            username=None,
            silent=False
    ):
        """ Method to create a remote file with the specified `content`

        :param remote_path: destination folder in which to copy the local file
        :param content: content of the file
        :param use_sudo: allow to copy file in location with restricted permissions
        :param owner: user that will own the file on the remote host
        :param permissions: permissions to apply on the remote file (chmod format)
        :param username: sudo user
        :param silent: disable logging

        Usage::

            # create file on remote host and with specified content at the specified path
            >>> ssh_session.file(remote_path='/path/to/remote/file', content='file content')

            # create file on remote host and with specified content at the specified path needing sudo permissions
            >>> ssh_session.file(remote_path='/path/to/remote/file', content='file content', use_sudo=True)

            # create file on remote host and with specified content at the specified path
            # with specified owner and permissions
            >>> ssh_session.file(remote_path='/path/to/remote/file', content='file content',
            ...                 owner='other_user', permissions='700')
        """
        if not silent:
            logger.debug("Create file '%s' on remote host '%s' as '%s'" % (remote_path, self.host, self.username))
        sftp_client = self.get_sftp_client()

        copy_path = remote_path
        if use_sudo:
            # copy local file on remote host in temporary dir
            copy_path = "/tmp/%s" % util.id_generator(size=15)

        # create file remotely
        with sftp_client.file(copy_path, mode='w+') as remote_file:
            remote_file.write(content)

        # mv this file in the final destination
        if use_sudo:
            move_command = "mv %s %s" % (copy_path, remote_path)
            self.run_cmd(move_command, silent=True, username=username or 'root')

        # file will be owned by the specified user
        if owner:
            full_owner = owner
            if ':' not in owner:
                full_owner = '{0}:{0}'.format(owner)
            self.run_cmd("sudo chown %s %s" % (full_owner, remote_path), silent=True)

        if permissions:
            self.run_cmd("sudo chmod %s %s" % (permissions, remote_path), silent=True)


RunSSHCmdResult = collections.namedtuple('RunSSHCmdResult', 'exit_code output')


class RunCmdResult(RunSSHCmdResult):
    """Result of a command run with SSHSession

    :param exit_code: exit code of the run command (last run exit_code in case of retries)
    :param output: output of the command run  (last run output only in case of retries)
    :param command: the command run
    :param result_list: list of RunSSHCmdResult, 1 item for each retry
    :param success_exit_code: list of integer considered as a success exit code for command run
    :param runs_nb: number of times the command has been run

    Usage::

        >>> result = ssh_session.run_cmd('hostname')

        # access to both exit_code and command output using tuple
        >>> (exit_code, output) = result

        # access directly to single attributes
        >>> result.exit_code
        0

        >>> result.output
        u'gateway.example.com'

        >>> result.command
        'hostname'

    """
    def __new__(cls, exit_code, output, result_list, command, success_exit_code, runs_nb):
        self = super(RunCmdResult, cls).__new__(cls, exit_code, output)
        self.result_list = result_list
        self.command = command
        self.success_exit_code = success_exit_code
        self.runs_nb = runs_nb
        return self
