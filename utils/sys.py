import logging
import os
import subprocess
import sys
import json
import ctypes
from importlib.util import find_spec


def loggers_off():
    """
    Disables all logs produced by imported modules
    """
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    for logger in loggers:
        logger.setLevel(logging.ERROR)


def install(package: str, output: bool = True, auto_upgrade: bool = True):
    """
    Function for installing specified packages inside a python script

    :param package: name of the package to install from PyPi
    :param output: surpasses console output if set False
    :param auto_upgrade: upgrades the package to the last available version if the package is already installed
    """
    packages_installed = installed(package)
    # running a commands using the same environment
    if not (packages_installed and not auto_upgrade):
        subprocess.run(
            args=[sys.executable, "-m", "pip", "install", "-U", package],
            stdout=subprocess.DEVNULL if not output else None,  # DEVNULL surpasses console output
            stderr=subprocess.STDOUT
        )
    if not (packages_installed and not auto_upgrade):
        logging.info(
            f"{package} {'installation succeeded, tests were not run' if not packages_installed else 'was already installed, updated successfully, tests were not run'}")
    else:
        logging.info(f"{package} is already installed")


def installed(name: str) -> bool:
    """
    A function for checking if the specified package is installed in venv
    :param name: name of the package
    :return: True if package is installed False otherwise
    """
    return False if not find_spec(name) else True


def run(*args, stdout: bool = False):
    subprocess.run(
        args,
        stdout=subprocess.DEVNULL if not stdout else None,
        stderr=subprocess.STDOUT
    )


def config_load(path: str) -> dict:
    """
    Loads config
    """
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data


def config_dump(path: str, data):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            json.dump(data, path, ensure_ascii=False)


def get_capslock_state():
    """
    Get capslock state: ON/OFF
    :return:
    """
    if sys.platform.startswith("win"):
        hllDll = ctypes.WinDLL("User32.dll")
        VK_CAPITAL = 0x14
        return hllDll.GetKeyState(VK_CAPITAL)
    elif sys.platform == "linux":
        capslock_state = subprocess.check_output("xset q | awk '/LED/{ print $10 }' | grep -o '.$'", shell=True).decode(
            "ascii")
        return True if capslock_state[0] == "1" else False


def clear():
    if sys.platform.startswith("win"):
        os.system("cls")
    else:
        print("\033c")




