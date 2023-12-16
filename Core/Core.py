import json
import os
import random
import threading

import pyautogui
from Audio.synthesizer import Synthesizer
from Audio.recognition import Voice
from Database.Data import Data
from PluginSystem.Plugin_system import PluginOperation, PluginInfo
from Command_System import *

import importlib.util

from LogSystem import core_logger

pyautogui.FAILSAFE = False


class Core:
    def __init__(self):
        core_logger.debug("Core execution started")

        # Initializing main supportive classes
        self.synthesizer = Synthesizer()
        self.recognition = Voice()
        self.data = Data()
        self.command_tree = CommandTree()

        # plugin system handling
        self.plugin_system = PluginOperation()
        self.__plugins_register__()

        # handling variables
        self.__handle_variables__()

        # plugins installation
        self.__plugins_load__()
        self.__install_plugins__()

        self.__registered_commands_update__()

        core_logger.debug("Core loading ended")

        self.said_word = ""
        self.power = False

    def start(self):
        thread = threading.Thread(target=self.__speech_recognition__)
        thread.start()

    def __handle_variables__(self):
        # opening config file
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/config.json") as file:
            config = json.load(file)
        # setting config variables to use as attributes inside a class
        for key, data in config.items():
            self.__setattr__(key, data)
        # setting other required arguments, that are not supposed to be changed by user
        self.loaded_plugins = []
        self.log_dict: dict[str: str] = {}
        self.plugin_ref: dict[str: dict] = {}
        self.plugin_enable: dict[str: bool] = {}
        self.multi_handle_answers = ["Конечно, сэр", "Выполняю, сэр", "Есть, сэр"]
        self.default_answers = ["Я тут, сэр", "Слушаю вас, сэр", "Что-то хотели, сэр?", "Всегда к вашим услугам, сэр",
                                "Я весь внимание, сэр", "Добрый день, сэр!"]
        core_logger.debug("Config parameters imported")

    def __speech_recognition__(self):
        core_logger.debug("Speech recognition started")
        while True:
            # iterating through speech recognition generator
            for data in self.recognition.listen():
                # setting recognized data as an attribute for access to the current data in outer field in class
                self.said_word = data
                # logging
                self.log("user", data)
                # checking if the application is enabled
                if self.power:
                    # removing trigger word from data for it no to bother the main command processin
                    request = self.__remove_trigger_word__(data)
                    if request != "-":
                        self.__handle_input__(request)

    def __handle_input__(self, request):
        if not request:
            thread = threading.Thread(target=self.synthesizer.say, args=[random.choice(self.default_answers)])
            thread.start()
        else:
            total = self.__multihandle__(request)
            if len(total) == 1:
                result = self.command_tree.find_command(total[0])
                if result:
                    if result[2]:
                        thread = threading.Thread(target=self.synthesizer.say, args=[random.choice(result[2])])
                        thread.start()
                    result = list(result)
                    result.extend([total[0], request])
                    self.__synthesis_handler__(result)
            elif len(total) > 1:
                thread = threading.Thread(target=self.synthesizer.say, args=[random.choice(self.multi_handle_answers)])
                thread.start()
                said = False
                for command in total:
                    result = self.command_tree.find_command(command)

                    if result:
                        result = list(result)
                        result.extend([total[0], request])
                        output = getattr(self, result[0])(parameters=result[1], command=result[3], request=result[4])
                        if output and not said:
                            said = True
                            choiced = random.choice(self.multi_handle_answers)
                            thread = threading.Thread(target=self.synthesizer.say,
                                                      args=[choiced])
                            thread.start()
                            self.log("assistant", choiced)

    def __synthesis_handler__(self, request):
        @self.__say_dec__(request[2])
        def __send_handler_request__():
            return getattr(self, request[0])(parameters=request[1], command=request[3], request=request[4])

        __send_handler_request__()

    def __say_dec__(self, synthesis):
        def decorator(func):
            def wrapper():
                if synthesis:
                    self.log("assistant", synthesis)
                to_say = func()
                if to_say is not None and not synthesis:
                    choiced = to_say if not isinstance(to_say, list) else random.choice(to_say)
                    self.log("assistant", choiced)
                    thread = threading.Thread(target=self.synthesizer.say,
                                              args=[choiced])
                    thread.start()

            return wrapper

        return decorator

    def __install_plugins__(self):
        for plugin in self.loaded_plugins:
            plugin_instance = plugin()
            if plugin_instance.info.type == "voice":
                plugin_instance.__add_commands__()
                self.plugin_enable[plugin_instance.info.name] = True
                self.default_answers.extend(plugin_instance.default_answers)
                self.multi_handle_answers.extend(plugin_instance.multi_handle_answers)
                for handler in plugin_instance.handlers:
                    self.__setattr__(handler, plugin_instance.__getattribute__(handler))
                core_logger.debug(f"Voice plugin {plugin_instance.info.name} has been set")
            elif plugin_instance.info.type == "command":
                plugin_instance.__add_commands__()
                self.plugin_enable[plugin_instance.info.name] = True
                self.command_tree.add_commands(plugin_instance.command_tree)
                self.plagin_commands(plugin_instance.info.name, plugin_instance.command_tree)
                self.__register_commands__(plugin_instance.command_tree)
                for handler in plugin_instance.handlers:
                    self.__setattr__(handler, plugin_instance.__getattribute__(handler))
                for var in plugin_instance.variables.keys():
                    self.__setattr__(var, plugin_instance.variables[var])
                core_logger.debug(f"Command Plugin {plugin_instance.info.name} has been set")
        self.set_plugins_status()

    def disable_plagin(self, name):
        if self.plugin_enable[name]:
            self.plugin_enable[name] = False
            with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/commands.json", "r") as file:
                data = json.load(file)
                data: dict
            for command in self.plugin_ref[name].keys():
                self.command_tree.delete_command(command)
                to_remove = " ".join(command)
                if data[to_remove]:
                    del data[to_remove]
            with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/commands.json", "w") as file:
                json.dump(data, file, ensure_ascii=False)
            self.set_plugins_status()

    def enable_plugin(self, name):
        if not self.plugin_enable[name]:
            self.plugin_enable[name] = True
            self.__register_commands__(self.plugin_ref[name])
            self.__registered_commands_update__()
            self.set_plugins_status()

    def set_plugins_status(self):
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/config.json", "r") as file:
            data = json.load(file)
        data["plugins_status"] = self.plugin_enable
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/config.json", "w") as file:
            json.dump(data, file, ensure_ascii=False)

    @staticmethod
    def __register_commands__(commands: dict):
        updated_commands = {}
        for element in commands.keys():
            updated_commands[" ".join(element)] = commands[element]
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/commands.json", "r") as file:
            data = json.load(file)
            data: dict
        data.update(updated_commands)
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/commands.json", "w") as file:
            json.dump(data, file, ensure_ascii=False)

    def __registered_commands_update__(self):
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/commands.json", "r") as file:
            data = json.load(file)
            data: dict
        updated_commands = {}
        for element in data.keys():
            updated_commands[tuple(element.split())] = data[element]
        self.command_tree.add_commands(updated_commands)

    def __remove_trigger_word__(self, request):
        for word in self.trigger_words:
            if word in request:
                request = " ".join(request.split(word)[1:])[1:]
                return request
        return "-"

    def log(self, author, text):
        self.log_dict[author] = text

    def log_dump(self):
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/log.txt", "a") as file:
            file.write(self.log_dict.__str__())

    def plagin_commands(self, name, commands):
        self.plugin_ref[name] = commands

    def __multihandle__(self, request):
        list_of_commands = []
        current_command = []
        split_request = request.split()
        for word in split_request:
            if word in self.command_tree.first_words:
                if current_command:
                    list_of_commands.append(current_command)
                if word in ["найди", "поиск", "найти", "напиши", "запиши"]:
                    current_command = split_request[split_request.index(word):]
                    list_of_commands.append(current_command)
                    current_command = []
                    break
                current_command = [word]
            else:
                if current_command and word != "и":
                    current_command.append(word)
                elif not current_command and word != "и":
                    current_command = [word]
        if current_command:
            list_of_commands.append(current_command)
        return list_of_commands

    def __plugins_load__(self):
        for plugin in self.plugins:
            self.plugin_system: PluginOperation
            self.loaded_plugins.append(self.plugin_system.__plugin_load__(plugin["name"]))
            core_logger.info(f"Plugin {plugin['name']} was successfully loaded")

    def __plugins_register__(self):
        core_logger.debug("Started plugin registering")
        plugin_path = f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Plugin"
        for plugin in os.listdir(plugin_path):
            if os.path.isdir(f"{plugin_path}/{plugin}") and not plugin.startswith("__"):
                self.plugin_system: PluginOperation
                spec = importlib.util.spec_from_file_location("main", f"{plugin_path}/{plugin}/main.py")
                plugin_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plugin_module)
                plugin_instance = plugin_module.Main()
                with open(f"{plugin_path}/{plugin}/config.json", "r") as file:
                    data = json.load(file)
                    plugin_instance.info = PluginInfo(*data.values())
                self.plugin_system.register_plugin(plugin_instance)


if __name__ == "__main__":
    stewart = Core()
    stewart.start()
