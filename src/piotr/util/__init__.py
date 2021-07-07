import os
from piotr.exceptions import SudoRequired

def confirm(message):
    """
    Ask user to enter Y or N (case-insensitive).
    :return: True if the answer is Y.
    :rtype: bool
    """
    answer = ""
    while answer not in ["y", "n"]:
        answer = input("%s ? [Y/N] " % message).lower()
    return answer == "y"

def enforce_root():
    """
    Make sure user has root powers through sudo.
    """
    if os.geteuid() != 0:
        raise SudoRequired()
