from __future__ import print_function
import os
import random

from compose.cli.main import TopLevelCommand, project_from_options

from jumpssh import util as jumpssh_util


class DockerEnv(object):
    def __init__(self, docker_compose_file):
        self.docker_compose_file = docker_compose_file
        project = project_from_options(os.path.dirname(__file__), self.options)
        self.cmd = TopLevelCommand(project)
        self.cmd.up(self.options)

    @property
    def options(self):
        return {
            "--project-name": "jumpssh",
            "--file": [self.docker_compose_file],
            "--no-deps": False,
            "--abort-on-container-exit": False,
            "SERVICE": "",
            "--remove-orphans": False,
            "--no-recreate": True,
            "--force-recreate": False,
            "--build": False,
            '--no-build': False,
            '--no-color': False,
            "--rmi": "none",
            "--volumes": "",
            "--follow": False,
            "--timestamps": False,
            "--tail": "all",
            "--always-recreate-deps": True,
            "--scale": [],
            "--detach": True,
        }

    def get_host_ip_port(self, name='gateway', private_port=22):
        service = self.cmd.project.get_service(name=name)
        container = service.get_container(number=1)
        host_ip, host_port = container.get_local_port(port=private_port, protocol='tcp').split(':', 1)
        return host_ip, int(host_port)

    def clean(self):
        self.cmd.logs(self.options)
        self.cmd.down(self.options)


def create_random_json(size=1000):
    random.seed()
    dummy_json = {}
    for i in range(size):
        random_key = jumpssh_util.id_generator(size=15)
        random_value = jumpssh_util.id_generator(size=100)
        dummy_json[random_key] = random_value
    return dummy_json


def create_random_binary(size_kb=1):
    return os.urandom(size_kb * 1024)
