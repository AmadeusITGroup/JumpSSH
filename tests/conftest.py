try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

import pytest

from . import util as tests_util


def pytest_addoption(parser):
    """Add custom options to pytest command line"""
    # when specified, force rebuild of docker images
    parser.addoption("--rebuild", action="store_true")


@pytest.fixture(scope="module")
def docker_env(docker_compose_file, pytestconfig):
    """Return docker environment as defined by specified docker compose file"""
    # define docker compose options from user input
    options = {
        # user explicitely asked to rebuild docker images (even if they are already built)
        '--build': pytestconfig.getoption("rebuild"),
    }
    docker_compose_env = tests_util.DockerEnv(str(Path("docker") / docker_compose_file), options=options)
    yield docker_compose_env
    docker_compose_env.clean()
