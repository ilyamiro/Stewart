# Standart library imports
import logging
import random
import threading
import time
import os
import json
import inspect
from datetime import datetime

# Third-party imports
from playsound import playsound
import g4f.Provider
from g4f.client import Client as GPTClient

# Local imports
from audio.input import STT
from audio.output import ttsi
from utils import *
from tree import Tree
from data.constants import CONFIG_FILE

DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(DIR)

log = logging.getLogger("App")


class App:
    """
    Main running instance of an application behind the GUI (plan)
    For further reference, VA = Voice Assistant
    """

    @staticmethod
    def sound_effect_decorator(func):
        """Sound effect decorator for initializing"""

        def wrapper(self, *args, **kwargs):
            self.config = yaml_load(CONFIG_FILE)
            self.lang = self.config["lang"]["prefix"]
            log.info("Configuration file loaded")

            playsound(f"{os.path.dirname(DIR)}/data/sounds/startup.wav", block=False)
            func(self, *args, **kwargs)
            ttsi.say(parse_config_answers(self.config[f"answers"][self.lang]["startup"]))

        return wrapper

    @sound_effect_decorator
    def __init__(self):
        log.debug("App initialization started")

        self.trigger_timed_needed = self.config["trigger"]["trigger-mode"] != "disabled"

        # data tree initializing
        self.tree = Tree()
        self.tree_init()

        log.info("Data tree initialized")

        # import modules for command processing
        self.modules = import_modules_from_directory(self.config['module']['dir'])

        # history of requests
        self.history = []

        # gpt settings
        self.gpt_history = []
        self.gpt_client = GPTClient()
        self.gpt_provider = getattr(g4f.Provider, self.config["gpt"]["provider"]) if self.config["gpt"][
            "provider"] else None
        self.gpt_model = getattr(g4f.models, self.config["gpt"]["model"])
        self.gpt_start = self.config["gpt"]["start-prompt"][self.lang]

        log.info("Initialized GPT settings and a GPT client")

        # voice recognition
        self.stt = STT(self.lang)

        # restricting recognition by adding grammar made of commands
        self.grammar_recognition_restricted_create()
        self.stt.recognizer = self.stt.set_grammar(f"{os.path.dirname(DIR)}/data/grammar/grammar-{self.lang}.txt",
                                                   self.stt.create_new_recognizer())
        self.recognition_thread = None

        log.debug("Speech to text instance initialized")

        log.debug("Finished app initialization")

    def start(self):
        self.recognition_thread = threading.Thread(target=self.recognition)
        # starting the voice recognition
        self.recognition_thread.start()

        log.debug(f"Recognition thread started with name: {self.recognition_thread.name}")

    def handle(self, request):
        if not request and self.config["trigger"]["trigger-mode"] != "disabled":
            # if the request does not contain anything and the trigger word is required,
            # it means that the user called for VA with a trigger word
            # (that got removed by self.remove_trigger_word)
            # and did not specify the command; therefore, we answer with a default phrase
            ttsi.say(parse_config_answers(self.config[f"answers"][self.lang]["default"]))
        else:
            # update the history of requests to base some commands on the previous requests
            self.history_update(request)
            # checking whether the request contains multiple commands
            total = self.multihandle(request)
            if len(total) == 1:
                # if there is only one command, process it
                self.process_command(total[0], request)
            elif len(total) > 1:
                # if there are multiple commands, we can't play multiple audios at once as they would overlap.
                # so, we just play a confirmative phrase, like "Doing that now, sir" or else.
                ttsi.say(parse_config_answers(self.config[f"answers"][self.lang]["multi"]))
                # processing each command separately
                for command in total:
                    self.process_command(command, request, multi=True)
            elif not total and self.config["gpt"]["state"]:
                # If something was said by user after the trigger word, but no commands were recognized,
                # then this phrase is being sent to gpt model for answering
                answer = gpt_request(request, [*self.gpt_start, *self.gpt_history], self.gpt_client, self.gpt_provider,
                                     self.gpt_model)
                # update the gpt history for making long conversations possible
                self.gpt_history.extend([{"role": "user", "content": request}, {"role": "system", "content": answer}])
                if len(self.gpt_history) >= 10:
                    self.gpt_history = self.gpt_history[2:]
                ttsi.say(answer)

    def multihandle(self, request):
        list_of_commands, current_command = [], []
        split_request = request.split()  # splitting the request string into a list
        for word in split_request:  # iterating over the request list
            if word in self.tree.first_words:
                # if a word is one of the words that commands start with,
                # that we would count that as a start of a command
                if current_command:
                    # if there already is a current command being counted,
                    # the new first words means the new command starts, so we add a last one
                    list_of_commands.append(current_command)
                if word in self.config["command-spec"][f"no-multi-first-words"][self.lang]:
                    # if a word implies any words after it, like Google search,
                    # then everything after that word should be counted as a command itself
                    current_command = split_request[split_request.index(word):]  # get the remaining part of the request
                    list_of_commands.append(current_command)  # add the last command to the list
                    # current_command = []
                    break  # terminate the cycle as there could not be any commands after this one
                current_command = [word]  # as this is the first words appearance,
                # it means the new command should start.
            else:
                # if a current command is not finished:
                if current_command and word != self.config["command-spec"][f"connect-word"][self.lang]:
                    # if a command is not a first word, and it is not a connecting word like "and"
                    # than it could be both a "noise" word, that does not appear in any of the commands,
                    # and a part of the command;
                    last_node = current_command[
                        -1]  # get the last word of a current command to find it's possible continuations
                    left_request_split = split_request[split_request.index(
                        last_node) + 1:]  # getting the remaining part of the request
                    children_unfiltered = self.tree.find_children(
                        last_node)  # finding all the children to the last word of the current command
                    # TODO: if a root node is found, then the function returns a dict rather than a list -> a temporary workaround
                    children = children_unfiltered if isinstance(children_unfiltered, list) else list(
                        children_unfiltered.keys())
                    for child in children:  # iterate over all the children of a last command word to find continuations
                        if child in left_request_split:
                            # if a child is present, and the distance between the last piece of command
                            # and a child is not equal or greater than a max distance
                            # set by configuration file, and if "gap" between the last part of the command
                            # and a child does not contain any first words that would reset the command, we add this child
                            # to a command
                            if (split_request.index(child) - split_request.index(last_node) <= self.config["command-spec"]["max-distance-between-command-words"]+1 and
                                    not any(word in split_request[split_request.index(last_node) + 1:split_request.index(child)] for word in self.tree.first_words)):
                                current_command.append(child)

                elif not current_command and word != self.config["command-spec"][f"connect-word"][self.lang]:
                    pass

        if current_command:
            list_of_commands.append(current_command)
        return list_of_commands

    def grammar_recognition_restricted_create(self):
        """
        Creates a file of words that are used in commands
        This file is used for a vosk speech-to-text model to speed up the recognition speed and quality
        """
        with open(f"{PARENT_DIR}/data/grammar/grammar-{self.lang}.txt", "w") as file:
            file.write('["' + " ".join(self.config['trigger'].get(f"triggers").get(self.lang)))
            file.write(self.config["speech"].get(f"restricted-add-line").get(self.lang))
            file.write(self.tree.recognizer_string + '"]')

    def grammar_restrict(self, **kwargs):
        """
        An action function inside an app class that enables or disables 'improved but limited' speech recognition
        """
        match kwargs["parameters"]["way"]:
            case "on":
                self.stt.create_new_recognizer()
            case "off":
                self.stt.recognizer = self.stt.set_grammar(
                    f"{os.path.dirname(DIR)}/data/grammar/grammar-{self.lang}.txt",
                    self.stt.create_new_recognizer())

    def repeat(self, **kwargs):
        """
        An action function inside an app class that repeat an action performed the last time
        """
        self.handle(self.history[-1].get("request"))

    def recognition(self):
        """
        Voice recognition
        """
        while True:
            if self.config["text-mode"]:
                self.handle(input("Input: "))
            else:
                for word in self.stt.listen():
                    if self.trigger_timed_needed:
                        result = self.remove_trigger_word(word)
                        if result != "blank":
                            if self.config["trigger"]["trigger-mode"] == "timed":
                                self.trigger_timed_needed = False
                                self.trigger_counter(self.config["trigger"]["trigger-time"])
                            self.handle(result)
                    else:
                        self.handle(word)

    def remove_trigger_word(self, request):
        for trigger in self.config["trigger"][f"triggers"][self.lang]:
            if trigger in request:
                request = " ".join(request.split(trigger)[1:])[1:]
                return request
        return "blank"

    def trigger_counter(self, times):
        trigger_word_countdown_thread = threading.Timer(times, self.trigger_change)
        trigger_word_countdown_thread.start()
        log.info("Trigger countdown started")

    def trigger_change(self):
        self.trigger_timed_needed = True
        log.info("Trigger countdown ended")

    def tree_init(self):
        commands = self.config["commands"][self.lang]
        commands_repeat = self.config["commands-repeat"][self.lang]

        for command in commands:
            equiv = command.get(f'equivalents', [])
            if equiv:
                for eq in equiv:
                    equiv[equiv.index(eq)] = tuple(eq)
            self.add_command(
                tuple(command[f"command"]),
                command["action"],
                command.get("parameters", {}),
                command.get(f"responses", {}),
                command.get(f"synonyms", {}),
                equiv
            )

        for repeat in commands_repeat:
            for key in repeat[f"links"]:
                self.add_command(
                    (*repeat.get(f"command"), key),
                    repeat.get("action"),
                    {repeat.get("parameter"): repeat.get(f"links").get(key)},
                    [],
                    repeat.get(f"synonyms"),
                )

    def add_command(self, com: tuple, action: str, parameters: dict = None, synthesize: list = None,
                    synonyms: dict = None, equivalents: list = None):
        self.tree.add_commands(
            {com: {"action": action, "parameters": parameters, "synthesize": synthesize, "synonyms": synonyms,
                   "equivalents": equivalents}})

    def history_update(self, request):
        timestamp = datetime.now().isoformat()  # Get a timestamp
        new_event = {"timestamp": timestamp, "request": request}

        if len(self.history) > self.config.get("max-history-length"):
            self.history.pop(0)

        self.history.append(new_event)

    def process_command(self, command, full, multi: bool = False):
        result = self.tree.find_command(command)

        if not all(element is None for element in result):
            result = list(result)
            result.extend([command, full])
            if result[2] and not multi:
                ttsi.say(parse_config_answers(result[2]))
            self.do(result)

    def do(self, request):
        thread = threading.Thread(target=getattr(self.find_module(request[0]), request[0]),
                                  kwargs={"parameters": request[1], "command": request[3],
                                          "request": request[4]})
        thread.start()

    def find_module(self, name):
        """Find a module that has a function that corresponds to an action that has to be done"""
        for module in self.modules:
            members = inspect.getmembers(module)
            functions = [member[0] for member in members if inspect.isfunction(member[1])]
            if name in functions:
                return module
        if name in dir(self):
            return self
