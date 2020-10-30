from __future__ import print_function
import os
from setuptools import setup

ROOT = os.path.dirname(__file__)

# retrieve package information
about = {}
with open(os.path.join(ROOT, 'jumpssh', '__version__.py')) as version_file:
    exec(version_file.read(), about)

with open(os.path.join(ROOT, 'README.rst')) as readme_file:
    readme = readme_file.read()

setup(
    name=about['__title__'],
    version=about['__version__'],

    author=about['__author__'],
    author_email=about['__author_email__'],
    maintainer=about['__maintainer__'],
    maintainer_email=about['__maintainer_email__'],

    description=about['__description__'],
    long_description=readme,
    # long_description_content_type='text/markdown',
    url=about['__url__'],
    download_url=about['__download_url__'],
    license=about['__license__'],
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
    platforms='Unix; MacOS X',

    install_requires=[
        'paramiko'
    ],
)
