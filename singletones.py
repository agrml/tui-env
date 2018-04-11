from global_variables import *
from core import *

import parse
import tempfile

from typing import *
from enum import Enum
import os
import sys
import json


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Installer(metaclass=Singleton):
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
        return (Command("sudo add-apt-repository ppa:dawidd0811/neofetch && sudo apt update && "
                "sudo apt install curl wget tree ranger htop vim python-pip python3-pip npm git screen multitail neofetch",
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
                    'Installing oh-my-zsh'),
                Command('sudo apt-get install apt-transport-https ca-certificates curl software-properties-common && '
                        'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add - && '
                        'sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" && '
                        'sudo apt-get update; sudo apt-get install docker-ce',
                        'Installing Docker...')
                )

    def get_gui_installer(self):
        return (Command("wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add - && "
                "echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' | sudo tee /etc/apt/sources.list.d/google-chrome.list &&"
                "sudo apt update; sudo apt install google-chrome-stable",
                        "Installing chrome...",
                        "Setup scrolling plugin: look at ./hints/chrome-scrolling.jpg"),
                Reminder("Install dropbox manually: https://www.dropbox.com/install"),
                Command("sudo apt-add-repository ppa:webupd8team/terminix && sudo apt update && "
                        "sudo apt install gksu tilix clipit meld mpv virtual-box",
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


class DotfilesSynchronizer(metaclass=Singleton):
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
        def toPaths(s: str):
            return [Path(dotfile) for dotfile in s.split()]

        self.dotfiles = '''.oh-my-zsh/custom
                     .zshrc .zshrc_general .zshrc_oh-my-zsh .zsh_history
                     .gitconfig .gitignore_global
                     .vim .viminfo .vimrc
                     soft/scripts'''
        self.dotfiles = toPaths(self.dotfiles)
        self.dconfs = [Dconf("/com/gexperts/Tilix/")]
        self.backup_local = "~/dotfilesBackupLocal"
        self.backup_remote = "~/dotfilesBackupRemote"
        self.repo = None
        self.state = State()

    def set_repo(self):
        self.repo = REPO_DEFAULT_PATH
        print("Path to a git repo for dotfiles is set to [{}]: ".format(self.repo))
        if self.repo.strip() == "":
            self.repo = REPO_DEFAULT_PATH
        self.repo = os.path.expanduser(self.repo)
        Path.repo_location = self.repo
        Dconf.repo_location = self.repo
        if not os.path.isdir(self.repo):
            print("Invalid path. Aborting...")
            return

    def __call__(self):
        def overwrite_local():
            if not self.git_pull() and 'y' not in input('Repo seems needing to be stashed. Continue anyway? [N/y]: '):
                return
            self.register_remotes()

        def overwrite_remote():
            # TODO: what if remote has commits we don't have?
            # we need sort of merge.
            # First of all, we have to pull before committing. But we need keep our changes safe. So where should we pull?
            # Maybe we should stash and launch user-driven merge on unstashing.
            self.export_locals()
            self.git_push()

        if self.repo is None:
            self.set_repo()
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
                if self.state['first_run']:
                    Command('cp {} {}'.format(dotfile.home_location.full,
                                              dotfile.repo_location.full_to_parent))()
                continue
            Command('mv {} {}'.format(dotfile.home_location.full,
                                      dotfile.repo_location.full_to_parent))()
            Command('ln -s {} {}'.format(dotfile.repo_location.full,
                                         dotfile.home_location.full_to_parent))()
        for dconf in self.dconfs:
            dconf.dump()

    def register_remotes(self):
        for dotfile in self.dotfiles:
            if not os.path.exists(dotfile.repo_location.full):
                continue
            if dotfile.fname == '.zsh_history':
                if self.state['first_run']:
                    Command('cp {} {}'.format(dotfile.repo_location.full,
                                                 dotfile.home_location.full_to_parent))()
                continue
            if os.path.exists(dotfile.home_location.full):
                # TODO: "-p"
                Command('mv {} {}'.format(dotfile.home_location.full, self.backup_local))()
            # FIXME: links `soft/scripts` to `~` with name `soft`
            Command('ln -s {} {}'.format(dotfile.repo_location.full,
                                         dotfile.home_location.full_to_parent))()
        for dconf in self.dconfs:
            dconf.load()

    def git_push(self):
        if self.repo is None:
            self.set_repo()
        return Command('cd {} && git add -A && git commit -m "iter" && git push origin master'.format(
                self.repo))()

    def git_pull(self):
        if self.repo is None:
            self.set_repo()
        return Command('cd {} && git pull origin master'.format(self.repo))()


class State(metaclass=Singleton):
    def __init__(self):
        self.path = '{}/{}'.format(appdirs.user_config_dir(PROJECT_NAME), STATE_FILE_NAME)
        if not os.path.exists(self.path):
            default_config = {'first_run': True}
            self.config = default_config
        else:
            with open(self.path, 'r') as f:
                self.config = json.load(f)

    def __getitem__(self, item):
        return self.config[item]

    def __setitem__(self, key, value):
        self.config[key] = value

    def flush(self):
        dirname = os.path.dirname(self.path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(self.path, 'w') as f:
            json.dump(self.config, f)