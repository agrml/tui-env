#! /usr/bin/python3

"""
1. `git clone` that script
2. Supply a git repo that will be used as a cloud for your dotfiles.
Your current dotfiles will be moved here or will be deleted.
You'll get symlinks to that repo files instead of them.

Under the term of file we mean file a general (not only regular files)

"""

import parse

import collections
import subprocess
from typing import *
from enum import Enum
import os

mode = "debug"


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
        print("===...leaving {}===".format(self.name_))


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


class Installer:
    def __init__(self):
        self.prompt = Prompt("UI chooser",
                             ("Bootstrap TUI", self.get_tui_prompt()),
                             ("Bootstrap GUI", self.get_gui_prompt()),
                             ("Perform hooks", self.get_hooks_prompt()))

    def __call__(self):
        self.prompt()

    def get_tui_prompt(self):
        return Prompt("TUI installer",
                      ("Install basic TUI programs (tree, tldr, etc.)", self.get_tui_installer()))

    def get_gui_prompt(self):
        return Prompt("GUI installer",
                      ("Install full GUI set", self.get_gui_installer()),
                      ("Remove trash software", self.get_gui_cleaner()))

    def get_tui_installer(self):
        return (Command("sudo apt install curl wget tree ranger htop  vim python-pip python3-pip npm git screen",
                    "Installing tui staff..."),
                Command("sudo apt install pdfgrep trash-cli",
                    "Installing optional tui staff..."),
                Command("sudo npm install -g tldr --user=$(whoami)",
                    "Installing mann..."),
                Command('sudo apt install zsh ttf-ancient-fonts curl && chsh -s $(which zsh)',
                        'Installing zsh and fonts...',
                        '''Note: you need to install powerline fonts manually
                         Hint: https://github.com/powerline/fonts'''),
                Command('sh -c "$(curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"',
                    'Installing oh-my-zsh'))

    def get_gui_installer(self):
        return (Command("wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -"
                "echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' | sudo tee /etc/apt/sources.list.d/google-chrome.list"
                "sudo apt update && sudo apt install google-chrome-stable",
                        "Installing chrome..."),
                Command("sudo apt install clipit meld mpv virtual-box unity-tweak-tool gnome-tweak-tool unrar p7zip-full"
                        "tilix", "Installing base pack..."),
                Command("sudo apt install wireshark traceroute mtr iperf nmap mininet",
                                     "Installing networking staff..."),
                Command("sudo apt install gimp audacity nautilus-actions system-config-samba blueman" +
                        "sudo apt install samba && sudo touch /etc/libuser.conf",
                        "Installing multimedia/laptop stuff..."))

    def get_gui_cleaner(self):
        return Command("sudo apt purge gedit imagemagick transmission-gtk transmission-common "
                                       "gnome-orca aisleriot brasero gnome-mahjongg gnome-mines gnome-sudoku xdiagnose",
                                       "Wiping Ubuntu's rubbish out...")

    def get_hooks_prompt(self):
        return Prompt("Hooks maker",
                      ("Enable X-forwarding in from WSL", Command("echo 'export DISPLAY=127.0.0.1:0' >> ~/.zshrc_local")))


class DotfilesSyncer:
    class Strategy(Enum):
        OverwriteRemote = 1
        OverwriteLocal = 2
        # `extend` and `force` should also differ.
        # But it's unclear what should `extend`, so we implement `force` for overwriting remote
        # and `extend` for overwriting local: if file doesn't exist in repo, it will be kept in system

        # step 0. We support only copying from a fully customized working Ubuntu
        # and bootstrapping only a new Ubuntu (we overwrite if it happens, but we dont delete manually)

    def __init__(self):
        # TODO: test oh-my-zsh/...
        self.dotfiles = '''.oh-my-zsh/custom
                     .zshrc .zshrc_general .zshrc_oh-my-zsh .zsh_history
                     .gitconfig .gitignore_global
                     .vim .viminfo .vimrc'''.split()
        self.dotfiles = [Path(dotfile) for dotfile in self.dotfiles]
        self.repo_default_path = "~/dotfiles"
        self.backup_local = "~/dotfilesBackupLocal"
        self.backup_remote = "~/dotfilesBackupRemote"

    def __call__(self):
        self.repo = input("Path to a git repo where dotfiles will be stored [{}]: ".format(self.repo_default_path))
        if self.repo.strip() == "":
            self.repo = self.repo_default_path
        self.repo = os.path.expanduser(self.repo)
        if not os.path.isdir(self.repo):
            print("Invalid path. Aborting...")
            return

        option = input("[1] OverwriteLocal\n[2] OverwriteRemote\n> ").strip()
        if option == "1":
            self.git_pull()
            self.get_remotes()
        elif option == "2":
            self.export_locals()
            self.git_push()
        else:
            return

    def export_locals(self):
        for dotfile in self.dotfiles:
            if not os.path.exists(dotfile.home.full):
                continue
            if dotfile.internal != '':
                Command('mkdir -p {}'.format(dotfile.repo.full_to_parent))()
            Command('mv {} {}'.format(dotfile.home.full,
                                      dotfile.repo.full_to_parent))()
            Command('ln -s {} {}'.format(dotfile.repo.full,
                                          dotfile.home.full_to_parent))()

    def get_remotes(self):
        for dotfile in self.dotfiles:
            if not os.path.exists(dotfile.repo.full):
                continue
            if os.path.exists(dotfile.home.full):
                # TODO: "-p"
                Command('mv {} {}'.format(dotfile.home.full, self.backup_local))()
            Command('ln -s {} {}'.format(dotfile.repo.full,
                                          dotfile.home.full_to_parent))()

    def git_push(self):
        Command(
            'cd {} && git add -A && git commit -m "iter" && git push origin master'.format(
                self.repo))()

    def git_pull(self):
        Command('cd {} && git pull origin master'.format(self.repo))()


class Path:
    class Helper:
        def __init__(self):
            self.full = ''
            self.full_to_parent = ''

    def __init__(self, path: str):
        self.home = self.Helper()
        self.repo = self.Helper()
        self.home.full = os.path.expanduser('~/' + path)
        self.repo.full = os.path.expanduser('~/dotfiles/' + path)
        if '/' in path:
            reversed_paths = parse.parse('{}/{}', path[::-1])
            self.internal = reversed_paths[1][::-1]
            self.fname = reversed_paths[0][::-1]
            self.home.full_to_parent = os.path.expanduser('~/{}'.format(self.internal))
            self.repo.full_to_parent = os.path.expanduser('~/dotfiles/{}'.format(self.internal))
        else:
            self.internal = ''
            self.fname = path
            self.home.full_to_parent = os.path.expanduser('~')
            self.repo.full_to_parent = os.path.expanduser('~/dotfiles')


def main():
    prompt = Prompt("Main prompt",
                    ("Bootstrap a new machine", Installer()),
                    ("Sync dotfiles", DotfilesSyncer()))
    prompt()


if __name__ == "__main__":
    main()
