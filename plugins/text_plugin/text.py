import time

import clipman
import pyautogui


clipman.init()


def write(**kwargs):
    to_write = " ".join(kwargs["command"][1:])
    clipman.copy(to_write)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")


def delete_text(**kwargs):
    if kwargs["parameters"]["way"] == "one":
        pyautogui.hotkey("ctrl", "backspace")
    else:
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("backspace")