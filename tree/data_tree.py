import logging


class CommandNode:
    """
    Represents a node in the trie structure for voice assistant commands.
    """

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


class Tree:
    """
    Represents a trie structure for storing and retrieving voice assistant commands.
    """

    def __init__(self):
        """
        Initializes a CommandTree with a root CommandNode.
        """
        self.root = CommandNode()
        self.synonym_map = {}  # Synonym mapping for words with the same meaning
        self.first_words = set()

    def add_synonym(self, synonym, canonical):
        """
        Adds a synonym to the synonym map.

        Parameters:
        - synonym: The synonym word.
        - canonical: The canonical form of the word.
        """
        self.synonym_map[synonym] = canonical

    def expand_synonyms(self, words):
        """
        Expands synonyms in a list of words based on the synonym map.

        Parameters:
        - words: A list of words.

        Returns:
        - A list of expanded words.
        """

        expanded_words = [self.synonym_map.get(word, word) for word in words]

        return expanded_words

    def add_commands(self, commands):
        """
        Adds multiple commands to the CommandTree.

        Parameters:
        - commands: A dictionary where keys are command parts (as tuples) and values are command details.
        """
        for command, details in commands.items():
            self.first_words.add(command[0])
            synonyms = details.get("synonyms")
            if synonyms:
                for synonim in synonyms.keys():
                    self.add_synonym(synonim, synonyms[synonim])
                    if synonyms[synonim] in self.first_words:
                        self.first_words.add(synonim)
            equal_commands = details.get("equivalents")
            if equal_commands:
                for equal in equal_commands:
                    self.add_commands({equal: {"action": details.get("action"),
                                               "parameters": details.get("parameters"),
                                               "synthesize": details.get("synthesize")}})
            expanded_command = self.expand_synonyms(command)
            for word in command:
                if word.split()[0] != word:
                    com = (a for a in word.split())
                    command = list(command)
                    for el in com:
                        command.insert(command.index(word), el)
                    command.pop(command.index(word))
                    self.add_commands({tuple(command): details})
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
        expanded_command = self.expand_synonyms(command)
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
