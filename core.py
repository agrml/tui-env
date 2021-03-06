from global_variables import *

import appdirs
import parse

import os
import subprocess
from enum import Enum
from typing import *
import collections


class Path:
    class Helper:
        def __init__(self):
            self.full = ''
            self.full_to_parent = ''

    repo_location = REPO_DEFAULT_PATH

    def __init__(self, path: str):
        self.home_location = self.Helper()
        self.repo_location = self.Helper()
        self.home_location.full = os.path.expanduser('~/' + path)
        self.repo_location.full = os.path.expanduser('{}/{}'.format(Path.repo_location, path))
        if '/' in path:
            reversed_paths = parse.parse('{}/{}', path[::-1])
            self.internal = reversed_paths[1][::-1]
            self.fname = reversed_paths[0][::-1]
            self.home_location.full_to_parent = os.path.expanduser('~/{}'.format(self.internal))
            self.repo_location.full_to_parent = os.path.expanduser('{}/{}'.format(Path.repo_location, self.internal))
        else:
            self.internal = ''
            self.fname = path
            self.home_location.full_to_parent = os.path.expanduser('~')
            self.repo_location.full_to_parent = os.path.expanduser(Path.repo_location)


class Dconf:
    repo_location = REPO_DEFAULT_PATH

    def __init__(self, dconf_path: str):
        self.dconf_path = dconf_path
        self.in_repo_dconf_dir = '{}/{}'.format(Dconf.repo_location, DCONF_REPO_DIR)
        self.in_repo_path = '{}/{}.dconf'.format(self.in_repo_dconf_dir, dconf_path.replace('/', '-'))

    def dump(self):
        if not os.path.exists(self.in_repo_dconf_dir):
            os.mkdir(self.in_repo_dconf_dir)
        Command('dconf dump {} > {}'.format(self.dconf_path, self.in_repo_path))()

    def load(self):
        if not os.path.exists(self.in_repo_path):
            Exception('Unable to read file from path {}'.format(self.in_repo_path))
        Command('dconf load {} < {}'.format(self.dconf_path, self.in_repo_path),
                'Overwriting dconf entry...')()


class Command:
    """
    Wraps a command to be executed and an explanation
    """

    class Mode(Enum):
        Interactive = 1
        Silent = 2

    mode = Mode.Interactive

    def __init__(self, command: str, explanation: str=None, postprint: str=None):
        self.command_ = command
        self.explanation_ = explanation
        self.postprint_ = postprint

    def __call__(self):
        if self.explanation_ is not None:
            print("Explanation:", self.explanation_)
        print("Processing command:", self.command_)
        if Command.mode == Command.Mode.Silent or input('Confirm [Y/n]: ') in ('y', 'Y', ''):
            subprocess.call('/bin/bash -c \"' + self.command_ + '\"', shell=True)
        if self.postprint_ is not None:
            print(self.postprint_)


class Reminder:
    def __init__(self, note: str):
        self.note_ = note

    def __call__(self):
        print("Note: {}".format(self.note_))


class Prompt:
    """
    Ask user what he wishes.
    name -- name of the prompt
    *args -- ((option name, option)). An option have to be another prompt or an action.
    """

    def __init__(self, name: str, *args: Tuple[str, Callable or Tuple], greeting="Choose a mode:"):
        self.name_ = name
        self.greeting_ = greeting
        self.options_ = list(args)

    def add_option(self, description: str, callback: Callable):
        self.options_.append((description, callback))

    def __call__(self):
        if self.name_ != "":
            print("===Entering {}...===".format(self.name_))
            print(self.greeting_)
        for num, option in enumerate(self.options_):
            print("[{}] {}".format(num + 1, option[0]))
        idx = int(input("> ")) - 1
        cmd = self.options_[idx][1]
        if isinstance(cmd, collections.Iterable):
            [item() for item in cmd]
        else:
            cmd()
        if self.name_ != "":
            print("===...leaving {}===".format(self.name_))