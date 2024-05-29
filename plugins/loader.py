# Standard library imports
import json
import os
import inspect
from multiprocessing import Process
from importlib import import_module

# Local application imports
from utils.sys import config_load
from tree import Tree
from logs import log

CWD = os.path.dirname(os.path.abspath(__file__))


class Loader:
    def __init__(self, path=f"{CWD}/"):
        self.combination = []

        self.CONFIG_FILE = f"{os.path.dirname(CWD)}/core/config.json"

        with open(self.CONFIG_FILE, "r", encoding="utf-8") as file:
            self.config = json.load(file)
            self.config: dict

        self.config["plugins"] = self.get_all_plugins(path)

        self.tree = Tree()

        for plugin in self.config.get("plugins"):
            self.load_commands_from_plugin(plugin.get("manifest"))

        self.architecture = self.load_architecture(self.config.get("plugins"))

        with open(self.CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(self.config, file, ensure_ascii=False, indent=4)

        with open(f"{os.path.dirname(CWD)}/core/data/json/core_commands.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            data["combination"] = self.combination

        with open(f"{os.path.dirname(CWD)}/core/data/json/core_commands.json", "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def get_tree(self):
        return self.tree

    def get_all_plugins(self, path):
        all_directories = [os.path.join(path, d) for d in os.listdir(path)
                           if os.path.isdir(os.path.join(path, d))
                           and not (d.startswith('__') or d.startswith('.'))]

        plugins = []
        for directory in all_directories:
            manifest = self.get_manifest(directory)
            manifest["path"] = directory
            plugins.append(manifest)
        return plugins

    @staticmethod
    def get_manifest(path):
        ArchitectureFile = None
        manifest = {}

        for file in os.listdir(path):
            if file.endswith(".json"):
                manifest = config_load(os.path.join(path, file))
                manifest["manifest"] = os.path.join(path, file)
            if file.endswith(".py"):
                ArchitectureFile = os.path.join(path, file)

        manifest["architecture"] = ArchitectureFile

        return manifest

    def load_commands_from_plugin(self, path_to_manifest):
        with open(path_to_manifest, "r", encoding="utf-8") as file:
            command_tree = json.load(file).get("tree")

        self.load_commands(command_tree.get("commands"))
        self.load_commands_repeat(command_tree.get("repeat"))

        self.combination.extend(command_tree.get("combination"))

    def load_commands(self, commands: list):
        for command in commands:
            equiv = command.get('equivalents', {})
            if equiv:
                for eq in equiv:
                    equiv[equiv.index(eq)] = tuple(eq)
            self.add_command(
                tuple(command['command']),
                command['action'],
                command.get('parameters'),
                command.get('responses', []),
                command.get('synonyms', {}),
                equiv
            )

    # TODO remove hardcoded synthesize parameters and import answers here, or find another solution

    def load_commands_repeat(self, commands_repeat: list):
        for repeat in commands_repeat:
            for key in repeat.get("links"):
                self.add_command(
                    (*repeat.get("command"), key),
                    repeat.get("action"),
                    {repeat.get("parameter"): repeat.get("links").get(key)},
                    [],
                    repeat.get("synonyms"),
                )

    def add_command(self, command: tuple, handler: str, parameters: dict = None, synthesize: list = None,
                    synonyms: dict = None, equivalents: list = None):
        if not synonyms:
            synonyms = {}
        if not synthesize:
            synthesize = []
        if not parameters:
            parameters = {}
        if not equivalents:
            equivalents = []
        self.tree.add_commands(
            {command: {"handler": handler, "parameters": parameters, "synthesize": synthesize, "synonyms": synonyms,
                       "equivalents": equivalents}})

    @staticmethod
    def load_architecture(plugins):
        modules = []

        for plugin in plugins:
            path = plugin.get("architecture")
            start_process = plugin.get("session").get("process")
            try:
                name = ".".join(path.split("/")[-3:])[:-3]
                module = import_module(name)
                if start_process.get("required"):
                    process = Process(target=getattr(module, start_process.get("start"))())
                    process.start()
                modules.append(module)
            except ModuleNotFoundError as e:
                log.debug(f"Plugin {path} failed to load because of the following error: {e}")
        return modules

