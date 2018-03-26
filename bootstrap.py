#! /usr/bin/python3

"""
1. `git clone` that script
2. Supply a git repo that will be used as a cloud for your dotfiles.
Your current dotfiles will be moved here or will be deleted.
You'll get symlinks to that repo files instead of them.

"""
import collections
import subprocess
from typing import *
from enum import Enum
import os



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
            print("[{}] {}".format(num, option[0]))
        idx = int(input("> "))
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
                # Command('git config --global user.email "0516480@gmail.com" && git config --global user.name "Mikhail Agranovskiy"',
                #     "Seting up git credentials..."),
                Command('sudo apt install zsh ttf-ancient-fonts curl && chsh -s $(which zsh)',
                        'Installing zsh and fonts...',
                        '''Note: you need to install powerline fonts manually
                         Hint: https://github.com/powerline/fonts'''))

    def get_gui_installer(self):
        return (Command("sudo apt install clipit meld mpv virtual-box unity-tweak-tool gnome-tweak-tool unrar p7zip-full"
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

    def __init__(self, repo: str):
        """
        :param repo: git repo has to be created manually
        """
        self.paths = '''.zsh
                     .zshrc .zshrc_general .zshrc_oh-my-zsh .zsh_history
                     .gitconfig .gitignore_global'''
        self.paths = ["~/" + name for name in self.paths.split()]
        self.repo = repo
        assert(os.path.isdir(self.repo))
        self.backupLocal = "~/dotfilesBackup"

    def __call__(self):
        pass

    def make_links(self, strategy: Strategy):
        """~/{} -> symlink to ~/dotfiles/{}"""

        for path in self.paths:
            # Command('rm -rf {}'.format(self.dotfilesBackupDir))()
            # Command('mv -f {} {}'.format(self.dotfilesDir, self.dotfilesBackupDir))()
            path_in_repo = self.repo + self.path_to_name(path)
            if strategy == self.Strategy.OverwriteRemote:
                Command('mv {} {}'.format(path, self.repo))()
            else:
                Command('mv {} {}'.format(path, self.backupLocal))()
                # TODO: support merge
            Command('ln -s {} {}'.format(path, path_in_repo))()
            # repository had been killed
            Command('cd {} && git add * && git add *.* && git ')()
        print('You can install zsh fonts using "Bootstrap..." option')

    def path_to_name(self, path):
        return path.strip('/').split('/')[-1]


def main():
    repo = "~/dotfiles"
    prompt = Prompt("Main prompt",
                    ("Bootstrap a new machine", Installer()),
                    ("Sync dotfiles", DotfilesSyncer(repo)))
    prompt()


if __name__ == "__main__":
    main()
