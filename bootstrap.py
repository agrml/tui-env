#! /usr/bin/python3

"""
Environment bootstrapper

Find more in README.md.
"""

from singletones import *

import argparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--push', action='store_true', help='git push dotfiles repo')
    parser.add_argument('--pull', action='store_true', help='git pull dotfiles repo')
    args = parser.parse_args()
    if args.push:
        DotfilesSynchronizer().git_push()
        return
    if args.pull:
        DotfilesSynchronizer().git_pull()
        return

    state = State()
    if state['first_run'] and 'n' in input('Please check ignoring for .git in your dotfiles repo [Enter]: '):
        return
    prompt = Prompt("Main prompt",
                    ("Install soft", Installer()),
                    ("Sync dotfiles", DotfilesSynchronizer()))
    prompt()
    state.flush()


if __name__ == "__main__":
    main()
