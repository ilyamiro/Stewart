from logging import Logger
import logging
from rich.logging import RichHandler


class BaseLogger(Logger):
    """
    Class for Stewart logging system
    """

    def __init__(self, name, level=logging.NOTSET, ):
        super().__init__(name, level)
        self._setup_logger()

    def _setup_logger(self):
        # Create a handler and set the formatter
        handler = RichHandler()
        self.addHandler(handler)


core_logger = BaseLogger("Core")
plugin_system_logger = BaseLogger("Plugins")
database_logger = BaseLogger("Database")
gui_logger = BaseLogger("Graphical Interface")
synthesis_logger = BaseLogger("Synthesis")
recognition_logger = BaseLogger("Speech-recognition")

