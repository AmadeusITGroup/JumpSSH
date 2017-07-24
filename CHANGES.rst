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
