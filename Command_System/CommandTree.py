class CommandNode:
    """
    Represents a node in the trie structure for voice assistant commands.
    """

    def __init__(self, handler=None, parameters=None, synthesize=None, command=None):
        """
        Initializes a CommandNode.

        Parameters:
        - handler: The action associated with the command.
        - parameters: Additional parameters associated with the command.
        - synthesize: Speech synthesis information.
        - command: Original command string.
        """
        self.children = {}  # Child nodes, where keys are the next parts of the command
        self.handler = handler
        self.parameters = parameters
        self.synthesize = synthesize
        self.command = command


class CommandTree:
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

    def delete_command(self, command):
        """
        Deletes a command from the CommandTree.

        Parameters:
        - command: The command to be deleted (as a list of parts).
        """
        expanded_command = self.expand_synonyms(command)
        self._delete_command_recursive(self.root, expanded_command)

    def _delete_command_recursive(self, node, command):
        """
        Recursive method to delete a command from the CommandTree.

        Parameters:
        - node: The current node in the trie.
        - command: The remaining parts of the command (as a list).

        Returns:
        - True if the command was deleted, False otherwise.
        """
        if not command:
            # If the command is empty, we've reached the end of the command
            # and can remove the handler and related information.
            node.handler = None
            node.parameters = None
            node.synthesize = None
            return True

        part = command[0]
        if part in node.children:
            # Recursively traverse the tree until the end of the command is reached.
            if self._delete_command_recursive(node.children[part], command[1:]):
                # If the child node returns True, it means the command was deleted,
                # so we can remove the child node if it's not needed.
                if not node.children[part].handler and not node.children[part].children:
                    del node.children[part]
                return True

        return False

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
                for synonim in synonyms:
                    self.add_synonym(synonim, synonyms[synonim])
            expanded_command = self.expand_synonyms(command)
            self._add_command_recursive(self.root, tuple(expanded_command), details.get("handler"),
                                        details.get("parameters"), details.get("synthesize"))

    def _add_command_recursive(self, node, command, handler, parameters=None, synthesize=None):
        """
        Recursive method to add a command to the CommandTree.

        Parameters:
        - node: The current node in the trie.
        - command: The remaining parts of the command (as a tuple).
        - handler: The action associated with the command.
        - parameters: Additional parameters associated with the command.
        - synthesize: Speech synthesis information.

        Returns:
        - The current node after adding the command.
        """
        if not command:
            node.handler = handler
            node.parameters = parameters
            node.synthesize = synthesize
            node.command = command  # Assign the original command here
            return node  # Return the current node

        part = command[0]
        if part not in node.children:
            node.children[part] = CommandNode()

        return self._add_command_recursive(node.children[part], command[1:], handler, parameters, synthesize)

    def find_command(self, command):
        """
        Finds a command in the CommandTree.

        Parameters:
        - command: The command to search for (as a list of parts).

        Returns:
        - A tuple containing the handler, parameters, synthesize information, and the full command string.
        """
        expanded_command = self.expand_synonyms(command)
        node = self.root
        found_one = 0
        result_handler, result_parameters, result_synthesize = None, None, None
        for part in expanded_command:
            if part in node.children:
                found_one += 1
                node = node.children[part]
                if node.synthesize:
                    result_synthesize = node.synthesize
            else:
                if found_one >= 1 and node.handler:
                    return node.handler, node.parameters, result_synthesize
                return None  # Command not found

        return node.handler, node.parameters, result_synthesize

    def get_child_commands(self, command):
        """
        Returns all child commands of the given command.

        Parameters:
        - command: The command to get child commands for (as a list of parts).

        Returns:
        - A list of tuples, each containing a child command and its details (handler, parameters, synthesize).
        """
        expanded_command = self.expand_synonyms(command)
        node = self.root

        for part in expanded_command:
            if part in node.children:
                node = node.children[part]
            else:
                return []  # Command not found

        return self._get_all_child_commands(node)

    def _get_all_child_commands(self, node):
        """
        Recursive method to get all child commands of a given node.

        Parameters:
        - node: The current node in the trie.

        Returns:
        - A list of tuples, each containing a child command and its details (handler, parameters, synthesize).
        """
        child_commands = []

        for part, child_node in node.children.items():
            child_command = [part] + self._get_command_suffix(child_node)
            child_handler = child_node.handler
            child_parameters = child_node.parameters
            child_synthesize = child_node.synthesize
            child_commands.append((child_command, child_handler, child_parameters, child_synthesize))

            # Recursively get child commands for each child node
            child_commands.extend(self._get_all_child_commands(child_node))

        return child_commands

    def _get_command_suffix(self, node):
        """
        Helper method to get the command suffix for a given node.

        Parameters:
        - node: The current node in the trie.

        Returns:
        - A list of command parts representing the suffix of the command.
        """
        if not node.children:
            return []
        else:
            child_part = next(iter(node.children.keys()))
            return [child_part] + self._get_command_suffix(node.children[child_part])

#
# my_command_tree = CommandTree()
# # commands_to_add = {
#     ("turn", "on", "lights"): {"handler": "turn_on_lights", "parameters": {"room": "living_room"}, "synthesize": "Lights are now on."},
#     ("turn", "off", "lights"): {"handler": "turn_off_lights", "parameters": {"room": "bedroom"}, "synthesize": "Lights are now off."},
#     ("increase", "volume"): {"handler": "increase_volume", "parameters": {"level": "medium"}, "synthesize": "Volume increased."},
#     ("decrease", "volume"): {"handler": "decrease_volume", "parameters": {"level": "low"}, "synthesize": "Volume decreased."},
#     ("play", "music"): {"handler": "play_music", "parameters": {"genre": "pop"}, "synthesize": "Now playing music."},
# }
#
# # Add the commands to the CommandTree
# my_command_tree.add_commands(commands_to_add)
# print(my_command_tree.find_command(("turn", "on")))
# print(my_command_tree.get_child_commands(("turn", )))
# commands_to_add = {
#     ("turn", "on", "lights"): {"handler": "turn_on_lights", "parameters": {"room": "living_room"}, "synthesize": "Lights are now on."},
#     ("turn", "off", "lights"): {"handler": "turn_off_lights", "parameters": {"room": "bedroom"}, "synthesize": "Lights are now off."},
#     ("increase", "volume"): {"handler": "increase_volume", "parameters": {"level": "medium"}, "synthesize": "Volume increased."},
#     ("decrease", "volume"): {"handler": "decrease_volume", "parameters": {"level": "low"}, "synthesize": "Volume decreased."},
#     ("play", "music"): {"handler": "play_music", "parameters": {"genre": "pop"}, "synthesize": "Now playing music."},
# }
#
# my_command_tree.add_commands(commands_to_add)
#
# # Showcase of get_child_commands in a tree-like structure
