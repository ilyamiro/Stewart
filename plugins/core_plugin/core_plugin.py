import subprocess as sp
import os
import random
import threading
import webbrowser as wb
from datetime import datetime


import psutil
import screen_brightness_control as sbc
from pymouse import PyMouse
from num2words import num2words
import pyautogui
import clipman


from utils.text import *
from utils.sys import *

from audio import tts


mouse = PyMouse()

obj = config_load("data/obj.json")


def cpu_load(**_):
    tts.say(f"Ваш процессор загружен на {num2words(psutil.cpu_percent(0.2), lang='ru')} процента, сэр")


def random_number(**kwargs):
    num = find_num_in_list(kwargs["command"])
    if isinstance(num, tuple):
        tts.say(num2words(random.randint(min(num), max(num)), lang='ru') + ", сэр")
    else:
        tts.say("Назовите два числ+а, сэр")


def quote(**_):
    random_ = random.choice(list(obj.get("quotes").keys()))
    tts.say(f"Как говорил {random_}, {obj.get('quotes')[random_]}")


def scroll(**kwargs):
    match kwargs["parameters"]["way"]:
        case "up":
            mouse.wheel(1)
        case "down":
            mouse.wheel(-1)


def subprocess(**kwargs):
    sp.run(
        kwargs["parameters"]["command"],
        stdout=sp.DEVNULL,
        stderr=sp.STDOUT,
    )


def num_key(**kwargs):
    num = find_num_in_list(kwargs["command"])
    if num:
        pyautogui.press(kwargs["parameters"]["key"], presses=num)
    else:
        pyautogui.press(kwargs["parameters"]["key"])


def num_hotkey(**kwargs):
    num = find_num_in_list(kwargs["command"])
    if num:
        for i in range(num):
            pyautogui.hotkey(*kwargs["parameters"]["hotkey"])
    else:
        pyautogui.press(*kwargs["parameters"]["hotkey"])


def click(self, **kwargs):
    num = find_num_in_list(kwargs["command"])
    if num:
        self.mouse.click(*self.mouse.position(), n=num)
    else:
        self.mouse.click(*self.mouse.position())


def system(**kwargs):
    os.system(kwargs.get("parameters").get("command"))


def hotkey(**kwargs):
    pyautogui.hotkey(*kwargs["parameters"]["hotkey"])


def key(**kwargs):
    pyautogui.press(kwargs["parameters"]["key"])


def move(**kwargs):
    way = kwargs["parameters"]["way"]
    num = find_num_in_list(kwargs["command"])
    x_cur, y_cur = mouse.position()
    match way:
        case "up":
            mouse.move(y=y_cur - num if num else y_cur - 500, x=x_cur)
        case "down":
            mouse.move(y=y_cur + num if num else y_cur + 500, x=x_cur)
        case "right":
            mouse.move(y=y_cur, x=x_cur + num if num else x_cur + 500)
        case "left":
            mouse.move(y=y_cur, x=x_cur - num if num else x_cur - 500)


def webbrowser(**kwargs):
    wb.open(kwargs["parameters"]["url"])


def brightness(**kwargs):
    num = find_num_in_list(kwargs["command"])
    if num:
        if kwargs["parameters"]["command"] == "set":
            sbc.set_brightness(num)
        else:
            sbc.set_brightness(
                sbc.get_brightness()[0] + (+num if kwargs["parameters"]["command"] == "up" else -num))
    else:
        sbc.set_brightness(sbc.get_brightness()[0] + (+25 if kwargs["parameters"]["command"] == "up" else -25))


def battery_percentage(**_):
    tts.say(
        f"Ваша батарея заряжена на {num2words(int(psutil.sensors_battery().percent), lang='ru')} процентов. " + random.choice(
            ["Кабель зарядки подключен", "Питание от сети активно",
             "Зарядное устройство подключено"]) if psutil.sensors_battery().power_plugged else "" + ", сэр")


def ram_load(**_):
    tts.say(
        f"Ваша оперативная память загружена на {num2words(psutil.virtual_memory().percent, lang='ru')} процента, сэр")


def power_off(**kwargs):
    if kwargs["parameters"]["way"] == "off":
        num = find_num_in_list(kwargs["command"])
        if num:
            tts.say(
                f"Выключение компьютера произойдет через {num2words(num, lang='ru')} минут{get_minute_suffix(num)}, сэр")
            os.system(f'shutdown -h +{num} /dev/null 2>&1')
        else:
            msg = "Выключение компьютера произойдет через одну минуту, сэр"
            os.system(f'sudo shutdown -h +1 /dev/null 2>&1')
            tts.say(msg)
    elif kwargs["parameters"]["way"] == "now":
        thread = threading.Timer(2.5, os.system, args=["sudo shutdown now"])
        thread.start()
    else:
        tts.say("Выключение компьютера отменено")
        os.system("sudo shutdown -c /dev/null 2>&1")


def power_reload(**kwargs):
    if kwargs["parameters"]["way"] == "off":
        num = find_num_in_list(kwargs["command"])
        if num:
            tts.say(
                f"Перезагрузка компьютера произойдет через {num2words(num, lang='ru')} минут{get_minute_suffix(num)}, сэр")
            os.system(f'shutdown -r -h +{num} /dev/null 2>&1')
        else:
            msg = "Перезагрузка компьютера произойдет через одну минуту, сэр"
            os.system(f'sudo shutdown -r -h +1 /dev/null 2>&1')
            tts.say(msg)
    elif kwargs["parameters"]["way"] == "now":
        thread = threading.Timer(2.5, os.system, args=["sudo shutdown -r now"])
        thread.start()
    else:
        tts.say("Перезагрузка компьютера отменена")
        os.system("sudo shutdown -c /dev/null 2>&1")


def capslock(**_):
    if get_capslock_state():
        tts.say("Капслок уже включен, сэр")
    else:
        tts.say("Выполнил, сэр")
        pyautogui.press("capslock")
