import random
import sys
from dataclasses import dataclass, asdict
from LogSystem.Loggers import plugin_system_logger

import os
import json
import importlib.util


@dataclass
class PluginInfo:
    name: str
    author: str
    type: str
    path: str
    platform: str
    about: str


class Plugin:
    def __init__(self, info: PluginInfo):
        self.info = info


class CommandPlugin(Plugin):
    """ class for adding new commands"""

    def __init__(self, info):
        self.command_tree: dict[tuple, dict] = {}
        self.handlers: list[str] = []
        self.variables: dict = {}
        super().__init__(info)

    def __add_command__(self, command: tuple, handler: str, parameters: dict, synthesize: list, synonyms: dict):
        if synonyms is None:
            synonyms = {}
        self.command_tree[command] = {"handler": handler, "parameters": parameters, "synthesize": synthesize,
                                      "synonyms": synonyms}

        if handler not in self.handlers:
            self.handlers.append(handler)

    def __set_variable__(self, var, val):
        self.variables[var] = val

class VoicePlugin(Plugin):
    """
    class for handling trigger word requests
    """

    def __init__(self, info):
        self.handlers: list[str] = []
        self.default_answers: list[str] = []
        self.multi_handle_answers: list[str] = []
        super().__init__(info)

    def __add_reaction__(self, reaction: str, handler: str = "default"):
        self.default_answers.append(reaction)
        if handler != "default":
            self.handlers.append(handler)

    def __add_multihandle__(self, reaction: str, handler: str = "default"):
        self.multi_handle_answers.append(reaction)
        if handler != "default":
            self.handlers.append(handler)


class PluginOperation:
    @staticmethod
    def register_plugin(plugin: Plugin):
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/config.json", "r") as file:
            data = json.load(file)
        __info__ = asdict(plugin.info)
        if __info__ not in data["plugins"] and os.path.exists(
                f'{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/{__info__["path"]}'):
            data["plugins"].append(__info__)
            with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/config.json", "w") as file:
                json.dump(data, file, ensure_ascii=False)
                plugin_system_logger.info(f"Plugin {__info__['name']} has been registered")
        else:
            plugin_system_logger.info(f"Plugin {__info__['name']} is already registered")

    @staticmethod
    def __check_plugin__(name: str, check: str):
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/config.json", "r") as file:
            data = json.load(file)
        for plugin in data["plugins"]:
            if plugin["name"] == name:
                prm = plugin[check]
                plugin_system_logger.info(f"Plugin's named {name} parameter {check} is equal to {prm}")
                return prm

    @staticmethod
    def unregister_plugin(name: str):
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/config.json", "r") as file:
            data = json.load(file)
        for plugin in data["plugins"]:
            if plugin["name"] == name:
                data["plugins"].remove(plugin)
                break
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/config.json", "w") as file:
            json.dump(data, file, ensure_ascii=False)
            plugin_system_logger.debug(f"Plugin {name} was successfully unregistered")

    @staticmethod
    def __plugin_load__(name):
        with open(f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/Database/config.json", "r") as file:
            data = json.load(file)
        plugin_info = None
        for go in data["plugins"]:
            if go["name"] == name:
                plugin_info = go
                plugin_system_logger.info(f"Plugin {plugin_info['name']} is going to be loaded to the core")
                break
        if plugin_info:
            spec = importlib.util.spec_from_file_location("main",
                                                          f"{os.path.abspath(os.path.join(os.getcwd(), os.pardir))}/{plugin_info['path']}/main.py")
            plugin_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_module)
            return plugin_module.Main
        else:
            plugin_system_logger.error("Plugin not found")
