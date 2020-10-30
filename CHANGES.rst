1.6.5 (11/03/2020)
------------------
- [Bug] :issue:`152`: Remove pkg_info.json file and replace it with python file to avoid access issue at runtime

1.6.4 (08/24/2020)
------------------
- [Bug] :issue:`109`: Fix automated session closure handled by python garbage collection
- [Bug] :issue:`120`: Fix get_remote_session not respecting 'timeout' parameter
- [Bug] :issue:`139`: Fix run_cmd raising AuthenticationException if no agent is running
- [Improvement][Tests]: use flaky package to automatically rerun flaky tests

1.6.3 (03/12/2020)
------------------
- [Improvement]: remove pytest-runner from setup_requires as this is deprecated for security reasons, see https://github.com/pytest-dev/pytest-runner
- [Improvement]: use only fixed test dependencies in requirements_dev.txt

1.6.1 (04/08/2019)
------------------
- [Bug] :issue:`51`: 'get' file was failing if the remote file is binary. Thanks to :user:`pshaobow` for the report.
- [Feature]: Ability to use any parameter of `paramiko.client.SSHClient.connect` in `get_remote_session`, was forgotten during implementation of :issue:`43`.
- [Improvement]: tests migrated to docker-compose to setup docker environment

1.5.1 (01/14/2019)
------------------
- [Feature] :issue:`43`: Ability to use any parameter of paramiko.client.SSHClient.connect in SSHSession.

1.4.1 (03/31/2018)
------------------
- [Bug] :issue:`33`: Fix download of file owned by root with `SSHSession.get`
- [Bug] : Automatically open closed session when calling SSHSession.put. Thanks to :user:`fmaupas` for the fix.

1.4.0 (01/29/2018)
------------------
- [Feature] :issue:`29`: Expose compression support from Paramiko (inherited from SSH).
  Thanks to :user:`fmaupas` for the contribution.

1.3.2 (12/17/2017)
------------------
- [Bug] :issue:`23`: do not print `byte` but `str` in continuous output when running command with python3.
  Thanks to :user:`nicholasbishop` for the report.

1.3.1 (09/15/2017)
------------------
- fix interruption of remote command when transport channel is already closed

1.3.0 (09/14/2017)
------------------
- allow to conceal part of the command run in logs specifying list of pattern in silent parameter (regexp format)
  For example, if a password is specified in command you may want to conceal it in logs but still want to log the
  rest of the command run
- ability to customize success exit code when calling run_cmd so that an exit code different from 0 do not raise
  any exception. Success exit code can be an int or even a list of int if several exit codes are considered a success.
- ability to retry remote command until success or max retry is reached
- ability to forward Ctrl-C to remote host in order to interrupt remote command before stopping local script

1.2.1 (07/27/2017)
------------------
- reduce logging level of some logs
- propagate missing 'silent' parameter in restclient module to run_cmd to control logging 

1.2.0 (07/24/2017)
------------------
- automatically open inactive session when running command on it
- automatically open inactive jump session when requesting remote session

1.1.0 (07/20/2017)
------------------
- Each ssh session can be used as a jump server to access multiple remote sessions in parallel. Only 1 remote
  session per jump server was allowed before.
- ability to customize retry interval when opening a ssh session

1.0.2 (07/14/2017)
------------------
- Fix run of shell builtins commands (source, ...) when impersonating another user as they cannot be executed
  without the shell and by default, sudo do not run shell

1.0.1 (06/11/2017)
------------------
- Fix BadHostKeyException raised by paramiko when reusing same ssh session object to connect to a different
  remote host having same IP than previous host (just TCP port is different)

1.0.0 (05/24/2017)
------------------
- First release
