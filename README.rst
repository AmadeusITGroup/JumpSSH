.. image:: https://secure.travis-ci.org/AmadeusITGroup/JumpSSH.png
    :target: http://travis-ci.org/AmadeusITGroup/JumpSSH

.. image:: https://coveralls.io/repos/AmadeusITGroup/JumpSSH/badge.png?branch=master
    :target: https://coveralls.io/r/AmadeusITGroup/JumpSSH?branch=master

`JumpSSH` is a module for Python 2.6+/3.3+ that can be used to run commands on remote servers through a gateway.

It is based on `paramiko library <http://www.paramiko.org>`_.
It provides the ability to execute commands on hosts that are not directly accessible but only through one or more servers.
Script does not need to be uploaded on a remote server and can be run locally.

Several authentication methods are supported (password, ssh key).

Commands can be run through several jump servers before reaching the remote server.
No need to establish a session for each command, a single ssh session can run as many command as you want, including parallel queries, and you will get result for each command independently.

So, why another python library to setup remote server through ssh ? Here is a quick comparison with the most known existing python libraries
 - Paramiko: provide very good implementation of SSHv2 protocol in python but with a low level api a bit complex
 - Ansible: require more configuration and understanding to start.
   Moreover, support of bastion host is done with modification of local ssh config to use ProxyCommand, and this is needed for each bastion host.
 - Fabric: use of jump server is much easier than Ansible thanks to 'env.gateway' parameter, but does not allow jump through several servers.
   Moreover, you don't have a single module that support both python 2.6 and more recent versions (2 non compatible python modules)


Installation
------------
To install JumpSSH, simply:

.. code:: bash

    $ pip install jumpssh


Examples
--------
establish ssh session with a remote host through a gateway:

.. code:: python

    >>> from jumpssh import SSHSession

    # establish ssh connection between your local machine and the jump server
    >>> gateway_session = SSHSession('gateway.example.com',
    ...                              'my_user', password='my_password').open()

    # from jump server, establish connection with a remote server
    >>> remote_session = gateway_session.get_remote_session('remote.example.com',
    ...                                                     password='my_password2')


run commands on remote host:

.. code:: python

    # command will be executed remotely and output will be returned locally and printed
    >>> print(remote_session.get_cmd_output('ls -lta'))
    total 28
    drwxr-xr-x. 412 root    root    12288 Mar 21 14:25 ..
    drwx------.   2 my_user my_user    28 Mar  6 19:25 .ssh
    drwx------.   3 my_user my_user    70 Mar  6 19:25 .
    -rw-r--r--.   1 my_user my_user    18 Jul 12  2016 .bash_logout
    -rw-r--r--.   1 my_user my_user   193 Jul 12  2016 .bash_profile
    -rw-r--r--.   1 my_user my_user   231 Jul 12  2016 .bashrc

    # get exit code of the remotely executed command (here to check if a package is installed)
    >>> remote_session.get_exit_code('yum list installed package_name')
    0

remote rest api usage:

.. code:: python

    # calling rest api on remote host that is only accessible from the gateway
    >>> from jumpssh import RestSshClient
    >>> rest_client = RestSshClient(gateway_session)

    # syntax is similar to requests library (http://docs.python-requests.org)
    >>> http_response = rest_client.get('http://remote.example.com/helloworld')
    >>> http_response.status_code
    200
    >>> http_response.text
    u'Hello, World!'

remote files operations:

.. code:: python

    # check if remote path exists
    >>> remote_session.exists('/path/to/a/file')
    True

    # copy file from local machine to remote host through gateway
    >>> remote_session.put('/local/path/to/a/file', '/remote/path/to/the/file')

    # create file on remote host from local content
    >>> remote_session.file('/remote/path/to/the/file',
    ...                     content='remote file content', permissions='600')

    # download remote file on local machine from remote host through gateway
    >>> remote_session.get('/remote/path/to/the/file', '/local/path/')


Tests
-----
jumpssh tests require docker, check `docker documentation <https://docs.docker.com>`_ for how to install it depending on your OS.
it also requires few python packages. To install them, run:

.. code:: bash

    $ pip install -r requirements_dev.txt

To run the test suite, clone the repository and run:

.. code:: bash

    $ python setup.py test

or simply:

.. code:: bash

    $ tox
