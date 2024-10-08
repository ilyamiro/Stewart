import logging
import types
import typing
from typing import Dict, Tuple, Literal, TypedDict, NotRequired, List, Callable

log = logging.getLogger("tree")


class InnerDictType(TypedDict):
    action: str
    parameters: NotRequired[dict]
    synonyms: NotRequired[Dict[str, str]]
    synthesize: NotRequired[List[str]]
    equivalents: NotRequired[List[List[str]]]
    inside_tts: NotRequired[bool]


COMMAND_TYPE = Dict[Tuple[str], InnerDictType]
COMMAND_CALLBACK = Callable[[tuple, dict], None]


class CommandNode:
    def __init__(self, action=None, parameters=None, command=None, synthesize=None, equivalents=None):
        """
        Initializes a CommandNode.

        Parameters:
        - action: The action associated with the command.
        - parameters: Additional parameters associated with the command.
        - synthesize: Speech synthesis information.
        - command: Original command string.
        """
        self.children = {}  # Child nodes, where keys are the next parts of the command
        self.action = action
        self.parameters = parameters
        self.command = command
        self.synthesize = synthesize
        self.equivalents = equivalents


class TreeAPI:
    """
    Represents a trie structure for storing and retrieving voice assistant commands.
    """

    def __init__(self):
        self.__add_command_callbacks__ = []

        self.synonym_map = {}  # Synonym mapping for words with the same meaning

        self.root = CommandNode()

        self.recognizer_string = ""
        # self.__first_words__ = set()

        # self.__inside_tts_list__ = []

    def add_commands_addition_callback(self, func: COMMAND_CALLBACK):
        self.__add_command_callbacks__.append(func)

    def set_synonym(self, command: typing.Union[list, tuple], synonym: str, canonical: str):
        """
        Adds a synonym to the synonym map.

        Parameters:
        - synonym: The synonym word.
        - canonical: The canonical form of the word.
        """
        self.synonym_map[tuple(command)] = {synonym: canonical}

    def __expand_synonyms__(self, command, words):
        """
        Expands synonyms in a list of words based on the synonym map.

        Parameters:
        - words: A list of words.

        Returns:
        - A list of expanded words.
        """
        mapping = self.synonym_map.get(command, None)
        if mapping:
            expanded_words = [mapping.get(word, word) for word in words]
        else:
            expanded_words = command

        return expanded_words

    def add_commands(self, commands: COMMAND_TYPE):
        """
        Adds multiple commands to the CommandTree.

        Parameters:
        - commands: A dictionary where keys are command parts (as tuples) and values are command details.
        """
        for definition, details in commands.items():
            for hook in self.__add_command_callbacks__:
                try:
                    hook(definition, details)
                except Exception as e:
                    log.warning(f"Add command hook {hook.__name__} threw an error: {e}")

            # self.first_words.add(command[0])
            self.recognizer_string += f" {' '.join(definition)}"
            # if details.get("inside_tts"):
            #     self.inside_tts_list.append(command)

            equal_commands = details.get("equivalents")
            if equal_commands:
                for equal in equal_commands:
                    self.add_commands({equal: {"action": details.get("action"),
                                               "parameters": details.get("parameters"),
                                               "synthesize": details.get("synthesize"),
                                               "inside_tts": details.get("inside_tts")}})
            expanded_command = self.__expand_synonyms__(tuple(definition), definition)
            for words in definition:
                if words.split()[0] != words:
                    redone_command = (word for word in words.split())
                    definition = list(definition)
                    for element in redone_command:
                        definition.insert(definition.index(words), element)
                    definition.pop(definition.index(words))
                    self.add_commands({tuple(definition): details})
                    break
            self._add_command_recursive(self.root, tuple(expanded_command), details.get("action"),
                                        details.get("parameters"), details.get("synthesize"))

    def _add_command_recursive(self, node, command, action, parameters=None, synthesize=None):
        """
        Recursive method to add a command to the CommandTree.

        Parameters:
        - node: The current node in the tree.
        - command: The remaining parts of the command (as a tuple).
        - action: The action associated with the command.
        - parameters: Additional parameters associated with the command.
        - synthesize: Speech synthesis information.

        Returns:
        - The current node after adding the command.
        """
        if not command:
            node.action = action
            node.parameters = parameters
            node.command = command  # Assign the original command here
            node.synthesize = synthesize
            return node  # Return the current node

        part = command[0]
        if part not in node.children:
            node.children[part] = CommandNode()

        return self._add_command_recursive(node.children[part], command[1:], action, parameters, synthesize)

    def find_command(self, command):
        """
        Finds a command in the CommandTree.

        Parameters:
        - command: The command to search for (as a list of parts).

        Returns:
        - A tuple containing the action, parameters, synthesize information, and the full command string.
        """
        expanded_command = self.__expand_synonyms__(tuple(command), command)
        # log.info(f"command for searching: {expanded_command}")
        node = self.root
        found_one = 0
        for part in expanded_command:
            if part in node.children:
                found_one += 1
                node = node.children[part]
            else:
                if found_one >= 1 and node.action:
                    return node.action, node.parameters, node.synthesize
                return None  # Command not found

        return node.action, node.parameters, node.synthesize

    def find_children(self, word):
        """
        Finds all children of the specified word in the tree.

        Parameters:
        - word: The word to search for in the tree.

        Returns:
        - A list of all children nodes of the specified word.
        """

        def _find_children_recursive(node, sequence):
            if sequence in node.children.keys():
                return node.children[sequence].children
            children_list = []
            for child in node.children.values():
                children_list.extend(_find_children_recursive(child, sequence))
            return children_list

        children = _find_children_recursive(self.root, word)

        return children if isinstance(children, list) else list(children.keys())


tree = TreeAPI()