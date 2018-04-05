#! /usr/bin/python3

"""
1. `git clone` that script
2. Supply a git repo that will be used as a cloud for your dotfiles.
Your current dotfiles will be moved here or will be deleted.
You'll get symlinks to that repo files instead of them.

Under the term of file we mean file a general (not only regular files)

"""

from core import *

import parse
import tempfile
import appdirs

import collections
import subprocess
from typing import *
from enum import Enum
import os
import sys
import json

MODE = "debug"
REPO_DEFAULT_PATH = os.path.expanduser("~/dotfiles")
USER_INSTALL_DIR = os.path.expanduser("~/soft")
state = State('state.json')


class Installer:
    def __init__(self):
        self.prompt = Prompt("UI chooser",
                             ("Bootstrap TUI", self.get_tui_prompt()),
                             ("Bootstrap GUI", self.get_gui_prompt()),
                             ("Perform hooks", self.get_hooks_prompt()))
        self.user_install_dir = USER_INSTALL_DIR

    def __call__(self):
        self.prompt()

    def get_tui_prompt(self):
        return Prompt("TUI installer",
                      ("Install basic TUI programs (tree, tldr, etc.)", self.get_tui_installer()))

    def get_gui_prompt(self):
        return Prompt("GUI installer",
                      ("Install full GUI set", self.get_gui_installer()),
                      ("Install a JetBrains IDE", self.get_jb_installer()),
                      ("Remove trash software", self.get_gui_cleaner()))

    def get_tui_installer(self):
        return (Command("sudo apt install curl wget tree ranger htop vim python-pip python3-pip npm git screen multitail neofetch",
                    "Installing basic tui staff..."),
                Command("sudo apt install pdfgrep trash-cli",
                    "Installing optional tui staff..."),
                Command('sudo npm cache clean -f && sudo npm install -g n && sudo n stable',
                        'Updating npm...'),
                Command("sudo npm install -g tldr --user=$(whoami)",
                    "Installing mann..."),
                Command('sudo apt install zsh fonts-powerline && chsh -s $(which zsh)',
                        'Installing zsh and fonts...'),
                # FIXME: err nearby token (
                Command('sh -c "$(curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"',
                    'Installing oh-my-zsh')
                )

    def get_gui_installer(self):
        return (Command("wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -"
                "echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' | sudo tee /etc/apt/sources.list.d/google-chrome.list"
                "sudo apt update && sudo apt install google-chrome-stable",
                        "Installing chrome...",
                        "Setup scrolling plugin: look at ./hints/chrome-scrolling.jpg"),
                Reminder("Install dropbox manually: https://www.dropbox.com/install"),
                Command("sudo apt-add-repository ppa:webupd8team/terminix && sudo apt update && "
                        "sudo apt install gksu clipit meld mpv virtual-box tilix",
                        "Installing basic gui staff..."),
                Command("sudo apt install wireshark traceroute mtr iperf nmap mininet",
                                     "Installing networking staff..."),
                Command("sudo apt install unity-tweak-tool gnome-tweak-tool unrar p7zip-full "
                        "gimp audacity nautilus-actions samba system-config-samba blueman && "
                        "sudo touch /etc/libuser.conf",
                        "Installing multimedia/laptop stuff..."))

    def get_gui_cleaner(self):
        return Command("sudo apt purge imagemagick gnome-orca aisleriot brasero gnome-mahjongg gnome-mines gnome-sudoku xdiagnose",
                                       "Wiping Ubuntu's rubbish out...")

    def get_hooks_prompt(self):
        return Prompt("Hooks maker",
                      ("Enable X-forwarding in from WSL", Command("echo 'export DISPLAY=127.0.0.1:0' >> ~/.zshrc_local")))

    def get_jb_installer(self):
        def functor():
            link = input("Link or full local path to .tar.gz (e.g. https://download.jetbrains.com/python/pycharm-professional-2017.3.4.tar.gz)\n: ").strip()
            archive_name = link.split('/')[-1]
            install_dir = input("Install dir [{}]: ".format(self.user_install_dir)).strip()
            if install_dir.strip() == "":
                install_dir = self.user_install_dir
            if link.startswith("http"):
                download_dir = tempfile.TemporaryDirectory()
                os.system('cd {} && wget {}'.format(download_dir.name, link))
                archive_path = '{}/{}'.format(download_dir.name, archive_name)
            else:
                archive_path = link
            ide_dir = '{}/{}'.format(install_dir, parse.parse('{}.tar.gz', archive_name)[0])
            if os.system('tar -xzf {} -C {}'.format(archive_path, install_dir)):
                print("Unable to extact", file=sys.stderr)
                return
            print("""Make sure your settings are bootstrapped or you use settings-sync plugin.
Afterwards launch ide with {}/bin/<ide-name>.sh""".format(ide_dir))
        return functor


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
                     .vim .viminfo .vimrc
                     soft/scripts'''.split()
        self.dotfiles = [Path(dotfile) for dotfile in self.dotfiles]
        self.repo_default_path = "~/dotfiles"
        self.backup_local = "~/dotfilesBackupLocal"
        self.backup_remote = "~/dotfilesBackupRemote"
        self.repo = None

    def __call__(self):
        def overwrite_local():
            if not self.git_pull():
                print('Repo needs to be stashed. Exiting...')
                return
            self.register_remotes()

        def overwrite_remote():
            # TODO: what if remote has commits we don't have?
            # we need sort of merge.
            # First of all, we have to pull before committing. But we need keep our changes safe. So where should we pull?
            # Maybe we should stash and launch user-driven merge on unstashing.
            self.export_locals()
            self.git_push()

        self.repo = input("Path to a git repo for dotfiles [{}]: ".format(REPO_DEFAULT_PATH)).strip()
        if self.repo.strip() == "":
            self.repo = REPO_DEFAULT_PATH
        self.repo = os.path.expanduser(self.repo)
        if not os.path.isdir(self.repo):
            print("Invalid path. Aborting...")
            return
        Prompt("",
               ("Overwrite local", overwrite_local),
               ("Overwrite remote", overwrite_remote)
              )()

    def export_locals(self):
        for dotfile in self.dotfiles:
            if not os.path.exists(dotfile.home_location.full):
                continue
            if os.path.islink(dotfile.home_location.full):
                # file could be already moved to repo on previous run
                continue
            if dotfile.internal != '':
                Command('mkdir -p {}'.format(dotfile.repo_location.full_to_parent))()
            if dotfile.fname == '.zsh_history':
                if state['first_run']:
                    Command('cp {} {}'.format(dotfile.home_location.full,
                                              dotfile.repo_location.full_to_parent))()
                continue
            Command('mv {} {}'.format(dotfile.home_location.full,
                                      dotfile.repo_location.full_to_parent))()
            Command('ln -s {} {}'.format(dotfile.repo_location.full,
                                         dotfile.home_location.full_to_parent))()

    def register_remotes(self):
        for dotfile in self.dotfiles:
            if not os.path.exists(dotfile.repo_location.full):
                continue
            if dotfile.fname == '.zsh_history':
                if state['first_run']:
                    Command('cp {} {}'.format(dotfile.repo_location.full,
                                                 dotfile.home_location.full_to_parent))()
                continue
            if os.path.exists(dotfile.home_location.full):
                # TODO: "-p"
                Command('mv {} {}'.format(dotfile.home_location.full, self.backup_local))()
            Command('ln -s {} {}'.format(dotfile.repo_location.full,
                                         dotfile.home_location.full_to_parent))()

    def git_push(self):
        return Command('cd {} && git add -A && git commit -m "iter" && git push origin master'.format(
                self.repo))()

    def git_pull(self):
        return Command('cd {} && git pull origin master'.format(self.repo))()


def main():
    if state['first_run'] and 'n' in input('Please check ignoring for .git in your dotfiles repo [Enter]: '):
        return
    prompt = Prompt("Main prompt",
                    ("Bootstrap a new machine", Installer()),
                    ("Sync dotfiles", DotfilesSyncer()))
    prompt()


if __name__ == "__main__":
    main()
    state.flush()
