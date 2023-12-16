import random
from Database.Helper import *

from PluginSystem.Plugin_system import CommandPlugin, PluginInfo
from LogSystem.Loggers import plugin_system_logger
import datetime
import os
import json


class Main(CommandPlugin):
    def __init__(self):
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Plugin/Time/config.json", "r") as file:
            data = json.load(file)
            super().__init__(PluginInfo(*data.values()))

        self.__set_variable__("stopwatch_enabled", False)
        self.__set_variable__("stopwatch_start", None)


    def __add_commands__(self):
        self.__add_command__(("сколько", "времени"), "tell_time", {}, [], {"время": "времени"})
        self.__add_command__(("запусти", "секундомер",), "stopwatch", {"way": "start"},
                             ["Запустил, сэр", "Время пошл+о!", "Секундомер запущен", "Выполнено, сэр"],
                             {"запустить":"запусти"})

        self.__add_command__(("останови", "секундомер",), "stopwatch", {"way": "stop"},
                             [],
                             {"остановить":"останови"})

    @staticmethod
    def tell_time(**kwargs):
        hour = datetime.datetime.now().hour
        minute = datetime.datetime.now().minute
        return f"Сейчас {num2words(hour, lang='ru')} час+{get_hour_suffix(hour)} и {num2words(minute, gender='f', lang='ru')} минут{get_minute_suffix(minute)}"

    def stopwatch(self, **kwargs):
        if kwargs["parameters"]["way"] == "start":
            self.stopwatch_start = datetime.datetime.now()
            self.stopwatch_enabled = True
        if kwargs["parameters"]["way"] == "stop" and self.stopwatch_start is not None and self.stopwatch_enabled:
            self.stopwatch_enabled = False
            self.stopwatch_end = datetime.datetime.now()
            passed = str(self.stopwatch_end - self.stopwatch_start)[:-7].split(":")
            hour, minute, second = int(passed[0]), int(passed[1]), int(passed[2])
            return f"Прошло {num2words(hour, lang='ru') if hour != 0 else ''} {'час' + get_hour_suffix(hour) if hour != 0 else ''}, {num2words(minute, lang='ru') if minute != 0 else ''} {'минут' + get_minute_suffix(minute) if minute != 0 else ''} {num2words(second, lang='ru') if second != 0 else ''} {'секунд' + get_second_suffix(second) if second != 0 else ''}"
        else:
            return random.choice(["Секундомер не запущен", "Секундомер выключен"])