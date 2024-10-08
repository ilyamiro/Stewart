# Standart library imports
import logging
import random
import threading
import time
import os
import json
import inspect
from datetime import datetime
from pathlib import Path

# Third-party imports
from playsound import playsound
import g4f.Provider
from g4f.client import Client as GPTClient

# Local imports
from audio.output import ttsi
from utils import *
from tree import Tree
from data.constants import CONFIG_FILE, PROJECT_FOLDER

from api.app import AppAPI


log = logging.getLogger("app")


class App:
    """
    Main running instance of an application behind the GUI (plan)
    For further reference, VA = Voice Assistant
    """

    def __init__(self, api: AppAPI):
        self.api = api

    @staticmethod
    def init_decorator(func):
        """Sound effect decorator for initializing"""

        def wrapper(self, *args, **kwargs):
            # <!--------------- pre-init: start ---------------!>
            self.api.__run_pre_init_callbacks__()

            self.config = filter_lang_config(load_yaml(CONFIG_FILE), self.api.lang)
            self.lang = self.api.lang

            log.info("Configuration file loaded")

            # play sounds
            if self.config["startup"]["sound-enable"]:
                playsound(self.config["startup"]["sound-path"], block=False)
            if self.config["startup"]["voice-enable"]:
                ttsi.say(parse_config_answers(self.config[f"startup"]["answers"]))

            cleanup(f"{PROJECT_FOLDER}/data/music", 10)

            # <!--------------- pre-init: end ---------------!>

            func(self, *args, **kwargs)

            # <!--------------- post-init: start ---------------!>
            self.api.__run_post_init_callbacks__()

            # <!--------------- post-init: end ---------------!>

        return wrapper

    @init_decorator
    def initialize(self):
        log.debug("App initialization started")

        self.trigger_timed_needed = self.config["trigger"]["trigger-mode"] != "disabled"

        # data tree initializing
        self.tree = Tree()
        self.tree_init()

        log.info("Data tree initialized")

        # history of requests
        self.history = []

        if not self.config["text-mode"]:
            from audio.input import STT

            # voice recognition
            self.stt = STT(self.api.lang)

            # restricting recognition by adding grammar made of commands
            if self.config["speech"]["speech-mode-restricted"]:
                self.grammar_recognition_restricted_create()
                self.stt.recognizer = self.stt.set_grammar(f"{PROJECT_FOLDER}/data/grammar/grammar-{self.lang}.txt",
                                                           self.stt.create_new_recognizer())

            log.debug("Speech to text instance initialized")

        self.recognition_thread = None
        self.running = True

        self.api.__save_config__()

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
            self.api.say(parse_config_answers(self.config[f"answers"]["default"]))
        else:
            # update the history of requests to base some commands on the previous requests
            self.history_update(request)
            # checking whether the request contains multiple commands
            total = self.api.__command_processor__(request)
            if len(total) == 1:
                # if there is only one command, process it
                self.process_command(total[0], request)
            elif len(total) > 1:
                # if there are multiple commands, we can't play multiple audios at once as they would overlap.
                # so, we just play a confirmative phrase, like "Doing that now, sir" or else.
                if all(command not in self.tree.api.inside_tts_list for command in total):
                    # if one of the commands itself produces some sound,
                    # then it could interfere with the confirmation phrase,
                    # so we check for this flag "inside_tts" to decide whether
                    # it would interfere and whether the multi confirmation sound should be played
                    ttsi.say(parse_config_answers(self.config[f"answers"]["multi"]))
                # processing each command separately
                for command in total:
                    self.process_command(command, request, multi=True)
            elif not total:
                self.api.__no_command_callback__(request)
                # If something was said by user after the trigger word, but no commands were recognized,
                # then this phrase is being sent to gpt model for answering if it's enabled

    def process_command(self, command, full, multi: bool = False):
        # process the input command and find the corresponding parameters
        # if self.config["ssm"]["enable"]:
        #     command = self.get_similar_command(command)
        result = self.tree.api.find_command(command)
        log.info(f"Execution parameters: {result}")
        if result and not all(element is None for element in result):  # if the command was found, process it
            result = list(result)  # find_command returns a tuple which is immutable
            result.extend([command, full])  # a list can be extended
            if result[2] and not multi:
                # if the command specifies an answer and only one command is being processed, use the TTS engine.
                ttsi.say(parse_config_answers(result[2]))

            self.do(result)

    def recognition(self):
        """
        Voice recognition
        """
        while self.running:
            if self.config["text-mode"]:
                # clear()
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
        """
        Removes trigger words from the input
        """
        for trigger in self.config["trigger"][f"triggers"]:
            if trigger in request:
                request = " ".join(request.split(trigger)[1:])[1:]
                return request
        return "blank"

    def trigger_counter(self, times):
        trigger_word_countdown_thread = threading.Timer(times, self.trigger_timed_needed)
        trigger_word_countdown_thread.start()
        log.info("Trigger countdown started")

    def trigger_change(self):
        self.trigger_timed_needed = True
        log.info("Trigger countdown ended")

    def tree_init(self):
        commands = self.config["commands"]
        commands_repeat = self.config["commands-repeat"]

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
                equiv,
                command.get("inside_tts", False)
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
                    synonyms: dict = None, equivalents: list = None, inside_tts: bool = False):
        self.tree.api.add_commands(
            {com: {"action": action, "parameters": parameters, "synthesize": synthesize, "synonyms": synonyms,
                   "equivalents": equivalents, "inside_tts": inside_tts}})

    def history_update(self, request):
        """
        Update history of requests
        """
        timestamp = datetime.now().isoformat()  # Get a timestamp
        new_event = {"timestamp": timestamp, "request": request}

        if len(self.history) > self.config.get("max-history-length"):
            self.history.pop(0)

        self.history.append(new_event)

    def do(self, request):
        """
        Start the action thread
        """
        func = self.find_exec(request[0])
        thread = threading.Thread(target=func,
                                  kwargs={"parameters": request[1], "command": request[3],
                                          "request": request[4]})
        thread.start()

    def find_exec(self, name):
        """
        Find a module that has a function that corresponds to an action that has to be done
        """
        if name in self.api.__search_functions__.keys():
            log.info(f"Action found: {name}")
            return self.api.__search_functions__.get(name)
        elif name in dir(self):
            return getattr(self, name)

    def grammar_recognition_restricted_create(self):
        """
        Creates a file of words that are used in commands
        This file is used for a vosk speech-to-text model to speed up the recognition speed and quality
        """
        with open(f"{PROJECT_FOLDER}/data/grammar/grammar-{self.lang}.txt", "w") as file:
            file.write('["' + " ".join(self.config['trigger'].get(f"triggers").get(self.lang)))
            file.write(self.config["speech"].get(f"restricted-add-line").get(self.lang))
            file.write(self.tree.api.recognizer_string + '"]')

    # below methods are actions that need access to the main app instance
    # <!--------------------------------------------------------------------!>

    def grammar_restrict(self, **kwargs):
        """
        An action function inside an app class that enables or disables 'improved but limited' speech recognition
        """
        match kwargs["parameters"]["way"]:
            case "on":
                self.stt.recognizer = self.stt.create_new_recognizer()
            case "off":
                self.stt.recognizer = self.stt.set_grammar(
                    f"{PROJECT_FOLDER}/data/grammar/grammar-{self.lang}.txt",
                    self.stt.create_new_recognizer())

    def repeat(self, **kwargs):
        """
        An action function inside an app class that repeat an action performed the last time
        """
        self.handle(self.history[-1].get("request"))

    def stop(self, **kwargs):
        self.running = False
