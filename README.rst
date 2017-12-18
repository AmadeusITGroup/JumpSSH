=======
JumpSSH
=======

.. image:: https://secure.travis-ci.org/AmadeusITGroup/JumpSSH.svg?branch=master
    :target: http://travis-ci.org/AmadeusITGroup/JumpSSH

.. image:: https://coveralls.io/repos/AmadeusITGroup/JumpSSH/badge.svg?branch=master
    :target: https://coveralls.io/r/AmadeusITGroup/JumpSSH?branch=master

.. image:: https://badge.fury.io/py/jumpssh.svg
    :target: https://badge.fury.io/py/jumpssh

.. image:: https://readthedocs.org/projects/jumpssh/badge?version=latest
    :target: https://jumpssh.readthedocs.io?badge=latest

.. image:: https://sonarcloud.io/api/badges/gate?key=amadeusitgroup_jumpssh&template=FLAT
    :target: https://sonarcloud.io/dashboard?id=amadeusitgroup_jumpssh

.. image:: https://sonarcloud.io/api/badges/measure?key=amadeusitgroup_jumpssh&metric=bugs&template=FLAT
    :target: https://sonarcloud.io/dashboard?id=amadeusitgroup_jumpssh

.. image:: https://sonarcloud.io/api/badges/measure?key=amadeusitgroup_jumpssh&metric=vulnerabilities&template=FLAT
    :target: https://sonarcloud.io/dashboard?id=amadeusitgroup_jumpssh


:JumpSSH:          Python module to run commands on remote servers
:Copyright:        Copyright (c) 2017 Amadeus sas
:Maintainer:       Thibaud Castaing <thibaud.castaing@amadeus.com>
:License:          `MIT <https://github.com/AmadeusITGroup/JumpSSH/blob/master/LICENSE>`_
:Documentation:    https://jumpssh.readthedocs.io
:Development:      https://github.com/AmadeusITGroup/JumpSSH

What
----
`JumpSSH` is a module for Python 2.7+/3.4+ that can be used to run commands on remote servers through a gateway.

It is based on `paramiko library <http://www.paramiko.org>`_.
It provides the ability to execute commands on hosts that are not directly accessible but only through one or
more servers.
Script does not need to be uploaded on a remote server and can be run locally.

Several authentication methods are supported (password, ssh key).

Commands can be run through several jump servers before reaching the remote server.
No need to establish a session for each command, a single ssh session can run as many command as you want,
including parallel queries, and you will get result for each command independently.

So, why another python library to setup remote server through ssh ? Here is a quick comparison with the most known existing python libraries
 - Paramiko: provide very good implementation of SSHv2 protocol in python but with a low level api a bit complex
 - Ansible: require more configuration and understanding to start.
   Moreover, support of bastion host is done with modification of local ssh config to use ProxyCommand, and this is
   needed for each bastion host.
 - Fabric: use of jump server is much easier than Ansible thanks to 'env.gateway' parameter, but does not allow jump through several servers.

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
jumpssh tests require docker, check `docker documentation <https://docs.docker.com>`_ for how to install it
depending on your OS.
it also requires few python packages. To install them, run:

.. code:: bash

    $ pip install -r requirements_dev.txt

To run the test suite, clone the repository and run:

.. code:: bash

    $ python setup.py test

or simply:

.. code:: bash

    $ tox


Contributing
------------

Bug Reports
^^^^^^^^^^^
Bug reports are hugely important! Before you raise one, though,
please check through the `GitHub issues <https://github.com/AmadeusITGroup/JumpSSH/issues>`_,
both open and closed, to confirm that the bug hasn't been reported before.

Feature Requests
^^^^^^^^^^^^^^^^
If you think a feature is missing and could be useful in this module, feel free to raise a feature request through the
`GitHub issues <https://github.com/AmadeusITGroup/JumpSSH/issues>`_

Code Contributions
^^^^^^^^^^^^^^^^^^
When contributing code, please follow `this project-agnostic contribution guide <http://contribution-guide.org/>`_.
