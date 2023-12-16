import sys
from PluginSystem import CommandPlugin, PluginInfo
from LogSystem.Loggers import plugin_system_logger
import subprocess
import os
import json
import pyautogui
from num2words import num2words
import threading


class Main(CommandPlugin):
    def __init__(self):
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Plugin/Linux/config.json", "r") as file:
            data = json.load(file)
            super().__init__(PluginInfo(*data.values()))

        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/data.json") as file:
            self.numbers = json.load(file)["numbers"]

        # os.system(
        #     f"chmod +x {os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/os_scripts/linux_package_manager_check.sh")
        # output = subprocess.check_output(
        #     f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/os_scripts/linux_package_manager_check.sh",
        #     shell=True).decode()[:-1]
        # os.system(f"sudo {output} install xdotool")

    def __add_commands__(self):
        self.__add_command__(("поставь", "громкость",), "volume", {"command": "set"},
                             ["Конечно, сэр", "Сию минуту, сэр"], {})

        self.__add_command__(("выключи", "компьютер"), "power_off", {"way": "off"},
                             [],
                             {'систему': 'компьютер'})

        self.__add_command__(("выключи", "компьютер", "сейчас"), "power_off", {"way": "now"},
                             ["Было честью служить вам, сэр. Надеюсь, вы обо мне не забудете!", "До встречи, сэр!"],
                             {"немедленно": "сейчас"})

        self.__add_command__(("увеличь", "громкость"), "volume", {"command": "up"},
                             ["Есть, сэр", "Конечно, сэр", "Сию минуту", "Выполняю, сэр"],
                             {"увеличь": "прибавь"})

        self.__add_command__(("сделай", "громче"), "volume", {"command": "up"},
                             ["Есть, сэр", "Конечно, сэр", "Сию минуту", "Выполняю, сэр"],
                             {"увеличь": "прибавь"})

        self.__add_command__(("уменьши", "громкость"), "volume", {"command": "down"},
                             ["Есть, сэр", "Конечно, сэр", "Сию минуту", "Выполняю, сэр"],
                             {"уменьши": "понизь"})
        self.__add_command__(("сделай", "тише"), "volume", {"command": "down"},
                             ["Есть, сэр", "Конечно, сэр", "Сию минуту", "Выполняю, сэр"],
                             {"уменьши": "понизь"})

        self.__add_command__(('отмени', 'выключение',), 'power_off', {"way": "on"},
                             ["Остаетесь, сэр?", "Рад, что вы передумали, сэр", "Конечно, рад поработать с вами еще!"],
                             {})
        self.__add_command__(("открой", "проводник"), "system", {"command": "xdg-open ."},
                             ["Открываю системные файлы, сэр", "Открываю проводник, сэр"], {"файлы": "проводник"})
        self.__add_command__(("открой", "файловую", "систему"), "system", {"command": "xdg-open ~/"},
                             ["Открываю системные файлы, сэр", "Открываю проводник, сэр"], {})

    @staticmethod
    def hotkey(**kwargs):
        pyautogui.hotkey(*kwargs["parameters"]["hotkey"])

    def power_off(self, **kwargs):
        if kwargs["parameters"]["way"] == "off":
            found = False
            for word in kwargs["command"]:
                if word in self.numbers:
                    num = self.numbers[word]
                    found = True
                    os.system(f"sudo shutdown -h +{num} /dev/null 2>&1")
                    return f"Выключение компьютера произойдет через {num2words(num, lang='ru')} минут{get_minute_suffix(num)}, сэр"
            if not found:
                os.system("sudo shutdown -h +1 /dev/null 2>&1")
                return f"Выключение компьютера произойдет через одну минуту, сэр"

        elif kwargs["parameters"]["way"] == "now":
            thread2 = threading.Timer(3, os.system, args=["sudo shutdown -h now"])
            thread2.start()
        else:
            os.system("sudo shutdown -c /dev/null 2>&1")
            return "Выключение компьютера отменено"

    @staticmethod
    def system(**kwargs):
        os.system(kwargs["parameters"]["command"])

    def volume(self, **kwargs):
        found = False
        current = os.popen('amixer get Master | grep -oP "\[\d+%\]"').read()
        current = current.split()[0][1:-2]
        for num in self.numbers:
            if num in kwargs["command"]:
                found = True
                if kwargs["parameters"]["command"] == "set":
                    os.system(f"amixer set 'Master' {self.numbers[num]}% /dev/null 2>&1")
                else:
                    os.system(
                        f"amixer set 'Master' {int(current) + self.numbers[num] if kwargs['parameters']['command'] == 'up' else int(current) - self.numbers[num]}% > /dev/null 2>&1")
                break
        if not found:
            os.system(
                f'amixer set "Master" {int(current) + 25 if kwargs["parameters"]["command"] == "up" else int(current) - 25}% > /dev/null 2>&1')
