import webbrowser
import subprocess
import pyperclip
import time
from PluginSystem import CommandPlugin, PluginInfo
from LogSystem.Loggers import plugin_system_logger
import screen_brightness_control as sbc
import pyautogui
import os
import json


class Main(CommandPlugin):
    def __init__(self):
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Plugin/Default/config.json", "r") as file:
            data = json.load(file)
            super().__init__(PluginInfo(*data.values()))

        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/data.json") as file:
            self.numbers = json.load(file)["numbers"]

    def __add_commands__(self):
        self.__add_command__(("скажи",), "say_auto", {"parameters": {}},
                             [],
                             {"произнеси": "скажи"})
        self.__add_command__(("увеличь", "яркость"), "brightness", {"command": "up"},
                             ["Есть, сэр", "Конечно, сэр", "Сию минуту", "Выполняю, сэр"],
                             {})

        self.__add_command__(("уменьши", "яркость"), "brightness", {"command": "down"},
                             ["Есть, сэр", "Конечно, сэр", "Сию минуту", "Выполняю, сэр"],
                             {})

        self.__add_command__(("поставь", "яркость",), "brightness", {"command": "set"},
                             ["Есть, сэр", "Конечно, сэр", "Сию минуту", "Выполняю, сэр"],
                             {})
        self.__add_command__(("кликни",), "click", {"parameters": {}},
                             ["Сделал, сэр", "Нажал, сэр", "Конечно, сэр", "Выполнил, сэр"],
                             {"нажми": "кликни", "нажмите": "кликни"})

        self.__add_command__(("подтверди",), "key", {"key": "enter"},
                             ["Без проблем, сэр", "Подтвердил, сэр", "Конечно, сэр", "Выполнил, сэр"],
                             {})
        self.__add_command__(("открой", "браузер"), "browser_open", {},
                             ["Открываю браузер, сэр", "Открываю, сэр", "Конечно, сэр"], {})
        self.__add_command__(("сделай", "скриншот"), "hotkey", {"hotkey": ["shift", "print"]},
                             ["Снимок экрана сделан, сэр", "Сохранено в папке Изображения, сэр", "Конечно, сэр",
                              "Выполняю, сэр"],
                             {})
        self.__add_command__(("напиши",), "write", {"way": "simple"},
                             ["Записываю, сэр", "Конечно, сэр", "Копирую и вставляю, сэр"],
                             {"запиши": "напиши"})
        self.__add_command__(("напечатай",), "write", {"way": "type"},
                             ["Печатаю, сэр", "Пропечатываю символы, сэр"],
                             {"напечатать": "напечатай"})

        self.__add_command__(("удали", "слово"), "write_delete", {"part": "word"},
                             ["Удалил, сэр", "Удаление завершено"],
                             {"удалить": "удали"})

        self.__add_command__(("удали", "последнее", "слово"), "write_delete", {"part": "word"},
                             ["Удалил, сэр", "Удаление завершено"],
                             {"словa": "слово"})

        self.__add_command__(("удали", "текст"), "write_delete", {"part": "text"},
                             ["Удалил, сэр", "Удаление завершено"],
                             {"удалите": "удали"})

        self.__add_command__(("удали", "весь", "текст"), "write_delete", {"part": "text"},
                             ["Удалил, сэр", "Удаление завершено"],
                             {"удалите": "удали"})

        self.__add_command__(("вниз",), "scroll", {"way": "down"}, ["Да, сэр", "Листаю, сэр"], {"низ": "вниз"})
        self.__add_command__(("вверх",), "scroll", {"way": "up"}, ["Да, сэр", "Листаю, сэр"], {"верх": "вверх"})

    @staticmethod
    def say_auto(**kwargs):
        return " ".join(kwargs["request"].split()[1:])

    @staticmethod
    def browser_open(**kwargs):
        webbrowser.open("https://www.google.com/")

    def write_delete(self, **kwargs):
        if kwargs["parameters"]["part"] == "word":
            pyautogui.hotkey("ctrl", "backspace")
        elif kwargs["parameters"]["part"] == "text":
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.05)
            pyautogui.press("backspace")
    @staticmethod
    def write(**kwargs):
        to_write = " ".join(kwargs["command"][1:])
        capslock_state = subprocess.check_output("xset q | awk '/LED/{ print $10 }' | grep -o '.$'", shell=True).decode("ascii")
        capslock_on = True if capslock_state[0] == "3" else False
        if kwargs["parameters"]["way"] == "type":
            for block in to_write:
                pyperclip.copy(block if not capslock_on else block.upper())
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.01)
        else:
            pyperclip.copy(to_write if not capslock_on else to_write.upper())
            pyautogui.hotkey("ctrl", "v")

    def brightness(self, **kwargs):
        found = False
        current = sbc.get_brightness(0)[0]
        for num in self.numbers.keys():
            if num in "".join(kwargs["command"]):
                found = True
                if kwargs["parameters"]["command"] != "set":
                    sbc.set_brightness(
                        int(current) + self.numbers[num] if kwargs["parameters"]['command'] == 'up' else int(current) -
                                                                                                         self.numbers[
                                                                                                             num])
                else:
                    sbc.set_brightness(self.numbers[num])
                break
        if not found:
            sbc.set_brightness(int(current) + 25 if kwargs["parameters"]['command'] == 'up' else int(current) - 25)

    @staticmethod
    def click(**kwargs):
        pyautogui.click()

    @staticmethod
    def key(**kwargs):
        pyautogui.press(kwargs["parameters"]["key"])

    @staticmethod
    def hotkey(**kwargs):
        pyautogui.hotkey(*kwargs["parameters"]["hotkey"])

    @staticmethod
    def scroll(**kwargs):
        match kwargs["parameters"]["way"]:
            case "up":
                pyautogui.scroll(clicks=10)
            case "down":
                pyautogui.scroll(clicks=-10)
