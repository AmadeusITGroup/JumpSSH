from __future__ import print_function
import json
from setuptools import setup

with open('jumpssh/pkg_info.json') as fp:
    _pkg_info = json.load(fp)

with open('README.rst') as readme_file:
    readme = readme_file.read()

setup(
    name="jumpssh",
    version=_pkg_info['version'],

    author='Amadeus IT Group',
    author_email='opensource@amadeus.com',
    maintainer='Thibaud Castaing',
    maintainer_email='t-cas@users.noreply.github.com',

    description="Python library for remote ssh calls through a gateway.",
    long_description=readme,
    url="https://github.com/AmadeusITGroup/JumpSSH",
    download_url="https://pypi.python.org/pypi/jumpssh",
    license='MIT license',
    classifiers=[
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Testing',
        'Topic :: System',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Shells',
        'Topic :: System :: Software Distribution',
        'Topic :: Terminals',

        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Operating System :: MacOS',

        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],

    packages=['jumpssh'],
    package_data={'': ['pkg_info.json']},
    platforms='Unix; MacOS X',

    install_requires=[
        'paramiko'
    ],
    test_suite='tests',
    setup_requires=[
        'pytest-runner'
    ],
    tests_require=[
        'docker',
        'docker-compose',
        'pytest',
        'pytest-catchlog',
        'mock'
    ]
)
