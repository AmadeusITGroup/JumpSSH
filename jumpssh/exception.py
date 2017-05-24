
class SSHException(Exception):
    """Generic exception for jumpssh

    Allow to chain exceptions keeping track of origin exception
    """
    def __init__(self, msg, original_exception=None):
        message = msg
        if original_exception:
            message += ": %s" % original_exception
        super(SSHException, self).__init__(message)
        self.__cause__ = original_exception
        self.__suppress_context__ = True


class ConnectionError(SSHException):
    """Exception raised when unable to establish SSHSession with remote host"""
    pass


class TimeoutError(SSHException):
    """Exception raised when remote command execution reached specified timeout"""
    pass


class RestClientError(SSHException):
    """Exception raised when error occurs during rest ssh calls"""
    pass


class RunCmdError(SSHException):
    """Exception raised when remote command return a non-zero exit code

    :ivar int exit_code: The error code from the run command.
    :ivar str command: The command that is generating this exception.
    :ivar str error: The error captured from the command output.
    """
    def __init__(self, exit_code, command, error):
        super(RunCmdError, self).__init__('Command (%s) returned non-zero exit status (%s): %s'
                                          % (command, exit_code, error))
        self.exit_code = exit_code
        self.command = command
        self.error = error
