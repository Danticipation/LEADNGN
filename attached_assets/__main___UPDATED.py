"""
Example usage for MirrorBot command line arguments:

python -m mirrorbot --help
"""

import sys


def get_mirrorbot_version():
    """
    Return the version of the current package.
    """
    from mirrorbot import __version__

    return __version__


if __name__ == '__main__':
    if '--version' in sys.argv:
        print(get_mirrorbot_version())
    elif '--help' in sys.argv:
        print('usage: mirrorbot [--version, --help]')
        print('  --version: Print the version of MirrorBot')
        print('  --help: Print this help message')
        print()
        print('Documentation at https://docs.mirrorbot.us')
